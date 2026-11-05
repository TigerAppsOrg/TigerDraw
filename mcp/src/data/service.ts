import { z } from "zod";
import { ApiClient, buildingSchema, imagesSchema } from "./client";
import { findBuilding, staticSource } from "./catalog";
import {
  collegeKey,
  matches,
  mergeRooms,
  record,
  type Filters,
} from "./normalize";
import { parseReviews } from "./reviews";
import {
  compare,
  DataError,
  dedupeMedia,
  key,
  safeUrl,
  type Building,
  type Catalog,
  type Media,
  type Room,
  type Source,
} from "./types";

type BuildingResult = {
  building: Building;
  rooms: Room[];
  source: Source;
  fallback: boolean;
  warnings: string[];
};
function summarize(room: Room) {
  const { source_records, ...summary } = room;
  return summary;
}
export class RoomService {
  constructor(
    readonly catalog: Catalog,
    readonly api = new ApiClient(),
    private now = Date.now,
  ) {}
  private deadline() {
    return this.now() + 10000;
  }
  listBuildings() {
    const buildings = this.catalog.buildings
      .slice(0, 200)
      .map((b) => ({
        building: b.name,
        aliases: b.aliases,
        colleges: b.colleges,
        static_room_count: new Set(b.rooms.map((r) => r.room_no)).size,
        floor_plan_count: b.plans.length,
        map_url: `${this.api.baseUrl}/map`,
        has_room_coordinates: b.rooms.some((r) => r.coordinates),
      }));
    return {
      buildings,
      returned_count: buildings.length,
      truncated: this.catalog.buildings.length > buildings.length,
      partial: false,
      sources: [staticSource(this.catalog)],
      warnings: [
        "Building inventory and college coverage come from the static catalog; room details are fetched live.",
      ],
    };
  }
  private async buildingRooms(
    building: Building,
    deadline: number,
  ): Promise<BuildingResult> {
    try {
      const { data, source } = await this.api.get(
        "/api/building_rooms",
        { building: building.api_name },
        buildingSchema,
        deadline,
      );
      if (key(data.building) !== key(building.api_name))
        throw new DataError(
          "UPSTREAM_ERROR",
          "TigerDraw returned a different building than requested.",
          false,
          source.source,
        );
      return {
        building,
        rooms: mergeRooms(
          building.name,
          Object.entries(data.floors).flatMap(([floor, rows]) =>
            rows.map((row) => ({
              room_no: row.room_no,
              record: record({ ...row, floor: row.floor ?? floor }),
            })),
          ),
          source,
        ),
        source,
        fallback: false,
        warnings: [],
      };
    } catch (error) {
      if (!building.rooms.length) throw error;
      const source = staticSource(this.catalog);
      return {
        building,
        rooms: mergeRooms(building.name, building.rooms, source),
        source,
        fallback: true,
        warnings: [
          `Live data for ${building.name} is unavailable. Static fallback has no current rankings, review statistics, or image availability.`,
          ...(error instanceof DataError ? [error.message] : []),
        ],
      };
    }
  }
  private collection(
    results: BuildingResult[],
    filters: Filters,
    limit: number,
    failed: string[] = [],
    unqueried: string[] = [],
  ) {
    const rooms = results
      .flatMap((r) => r.rooms)
      .filter((r) => matches(r, filters))
      .sort(
        (a, b) =>
          compare(a.building, b.building) || compare(a.room_no, b.room_no),
      );
    const returned = rooms.slice(0, limit).map(summarize);
    return {
      rooms: returned,
      returned_count: returned.length,
      truncated: rooms.length > limit,
      partial:
        failed.length > 0 ||
        unqueried.length > 0 ||
        results.some((r) => r.fallback),
      coverage: {
        live_or_cached: results
          .filter((r) => !r.fallback)
          .map((r) => r.building.name),
        static_fallback: results
          .filter((r) => r.fallback)
          .map((r) => r.building.name),
        failed,
        unqueried,
      },
      sources: results.map((r) => r.source),
      warnings: [...new Set(results.flatMap((r) => r.warnings))],
    };
  }
  async listRooms(input: Filters & { building: string; limit: number }) {
    const result = await this.buildingRooms(
      findBuilding(this.catalog, input.building),
      this.deadline(),
    );
    return this.collection([result], input, input.limit);
  }
  async searchRooms(input: Filters & { limit: number }) {
    const deadline = this.deadline();
    // Static college metadata is advisory: query all buildings so a stale college
    // assignment cannot silently remove live matches.
    if (
      input.college &&
      !this.catalog.buildings.some((b) =>
        b.colleges.some((c) => collegeKey(c) === collegeKey(input.college!)),
      )
    ) {
      throw new DataError(
        "DATA_UNAVAILABLE",
        `Unknown college '${input.college}'. Use list_buildings for supported colleges.`,
      );
    }
    const buildings = this.catalog.buildings;
    let index = 0;
    const results: BuildingResult[] = [];
    const failed: string[] = [];
    await Promise.all(
      Array.from({ length: Math.min(4, buildings.length) }, async () => {
        while (index < buildings.length && this.now() < deadline) {
          const building = buildings[index++];
          try {
            results.push(await this.buildingRooms(building, deadline));
          } catch {
            failed.push(building.name);
          }
        }
      }),
    );
    if (!results.length)
      throw new DataError(
        "DATA_UNAVAILABLE",
        "No building data is available. Try again later.",
        true,
      );
    results.sort((a, b) => compare(a.building.name, b.building.name));
    return this.collection(
      results,
      input,
      input.limit,
      failed.sort(compare),
      buildings.slice(index).map((b) => b.name),
    );
  }
  private async resolveRoom(
    buildingInput: string,
    roomInput: string,
    deadline: number,
  ) {
    const building = findBuilding(this.catalog, buildingInput);
    const result = await this.buildingRooms(building, deadline);
    const room = result.rooms.find((r) => r.room_no === key(roomInput));
    if (!room) {
      if (result.fallback)
        throw new DataError(
          "DATA_UNAVAILABLE",
          "Live rooms are unavailable and this room is not in the static catalog.",
          true,
        );
      throw new DataError(
        "ROOM_NOT_FOUND",
        `No room '${roomInput}' in ${building.name}. Use list_rooms to find room numbers.`,
        false,
        result.source.source,
      );
    }
    return { building, room, result };
  }
  async getRoom(input: { building: string; room_no: string }) {
    const deadline = this.deadline();
    const { building, room, result } = await this.resolveRoom(
      input.building,
      input.room_no,
      deadline,
    );
    const reviewQuery = {
      building_name: building.review_name,
      room_no: room.room_no,
    };
    const reviewsUrl = this.api.url("/get_reviews", reviewQuery);
    let reviews: Record<string, unknown>;
    try {
      const fetched = await this.api.get(
        "/get_reviews",
        reviewQuery,
        z.string(),
        deadline,
      );
      let parsed;
      try {
        parsed = parseReviews(fetched.data);
      } catch (error) {
        this.api.invalidate("/get_reviews", reviewQuery);
        throw error;
      }
      let source = fetched.source;
      // Flask's legacy Maine alias queries the exact spelling "Forbes".
      if (building.name === "Forbes" && parsed.parsed_count === 0) {
        const legacyQuery = { building_name: "Forbes", room_no: room.room_no };
        try {
          const legacy = await this.api.get(
            "/get_reviews",
            legacyQuery,
            z.string(),
            deadline,
          );
          const legacyParsed = parseReviews(legacy.data);
          if (legacyParsed.parsed_count) {
            parsed = legacyParsed;
            source = legacy.source;
          }
        } catch {
          this.api.invalidate("/get_reviews", legacyQuery);
          room.warnings.push(
            "Legacy Forbes review lookup was unavailable; only uppercase lookup was verified.",
          );
        }
      }
      reviews = { ...parsed, available: true, sources: [source] };
      if (room.num_reviews !== null && room.num_reviews !== parsed.parsed_count)
        room.warnings.push(
          "Review statistics and parsed review count disagree; sources may have changed between requests.",
        );
    } catch {
      reviews = {
        available: false,
        reviews: [],
        returned_count: 0,
        parsed_count: null,
        sources: [{ source: reviewsUrl }],
        warning:
          "Reviews are unavailable; this does not mean there are no reviews.",
      };
    }
    const coordinates = building.rooms.find(
      (r) => r.room_no === room.room_no,
    )?.coordinates;
    return {
      room,
      reviews,
      ...(coordinates
        ? {
            map: {
              coordinates,
              coordinate_order: "latitude,longitude",
              source: staticSource(this.catalog),
              url: `${this.api.baseUrl}/map`,
            },
          }
        : {}),
      partial: result.fallback || !reviews.available,
      warnings: [...result.warnings, ...room.warnings],
      draw_rank_description:
        "Historical average across years per source ID; not current room availability.",
    };
  }
  async getRoomImages(input: { building: string; room_no: string }) {
    const deadline = this.deadline();
    const { building, room, result } = await this.resolveRoom(
      input.building,
      input.room_no,
      deadline,
    );
    let media: Media[] = [];
    let sources: Source[];
    let fallback = false;
    const warnings = [...result.warnings];
    try {
      const fetched = await this.api.get(
        "/room_images",
        { building: building.api_name, room_no: room.room_no },
        imagesSchema,
        deadline,
      );
      for (const type of ["floor_plan", "room_plan", "thumbnail"] as const) {
        const url = safeUrl(fetched.data[type]);
        if (url) media.push({ url, type, media_type: "unknown" });
      }
      for (const image of fetched.data.views_360) {
        const url = safeUrl(image.url);
        if (url)
          media.push({
            url,
            type: "360",
            media_type:
              image.mediaType === "ACTUAL" || image.mediaType === "EXAMPLE"
                ? image.mediaType
                : "unknown",
          });
      }
      sources = [fetched.source];
    } catch {
      media = building.rooms
        .filter((r) => r.room_no === room.room_no)
        .flatMap((r) => r.media);
      sources = [staticSource(this.catalog)];
      fallback = true;
      warnings.push(
        "Live images are unavailable; any returned links are static fallback.",
      );
      if (!media.length)
        throw new DataError(
          "DATA_UNAVAILABLE",
          "Room images are unavailable and no static links exist.",
          true,
        );
    }
    const unique = dedupeMedia(media);
    return {
      building: building.name,
      room_no: room.room_no,
      images: unique.slice(0, 20),
      returned_count: Math.min(unique.length, 20),
      truncated: unique.length > 20,
      partial: result.fallback || fallback,
      sources,
      warnings,
    };
  }
  getFloorPlan(input: { building: string; floor?: string }) {
    const building = findBuilding(this.catalog, input.building);
    const knownFloors = new Set(
      [
        ...building.plans.map((p) => p.floor),
        ...building.rooms.map((r) => r.record.floor),
      ].filter((f): f is string => f !== null && f !== undefined),
    );
    if (input.floor && !knownFloors.has(key(input.floor)))
      throw new DataError(
        "DATA_UNAVAILABLE",
        `Unknown floor '${input.floor}' for ${building.name}. Available floor labels: ${[...knownFloors].sort(compare).join(", ")}.`,
      );
    const plans = building.plans.filter(
      (p) => input.floor === undefined || p.floor === key(input.floor),
    );
    return {
      building: building.name,
      floor: input.floor ? key(input.floor) : null,
      plans: plans.slice(0, 50),
      available: plans.length > 0,
      available_floors: [...new Set(building.plans.map((p) => p.floor))].sort(
        (a, b) => compare(a ?? "", b ?? ""),
      ),
      returned_count: Math.min(plans.length, 50),
      truncated: plans.length > 50,
      partial: false,
      sources: [staticSource(this.catalog)],
      warnings: plans.length
        ? [
            "Floor plans are static assets; their original update dates are unknown.",
          ]
        : ["No floor plan is available for this selection."],
    };
  }
}
