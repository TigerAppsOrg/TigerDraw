import { describe, expect, test } from "bun:test";
import { z } from "zod";
import { ApiClient, buildingSchema } from "../src/data/client";
import { findBuilding, loadCatalog } from "../src/data/catalog";
import { matches, mergeRooms, record } from "../src/data/normalize";
import { parseReviews } from "../src/data/reviews";
import { RoomService } from "../src/data/service";
import { dedupeMedia } from "../src/data/types";
import { parseCsv } from "../scripts/build-catalog";
import { sanitizeReviewFixture } from "../scripts/refresh-fixtures";
import { emptyReviews, fixtureService, maliciousReview } from "./helpers";

describe("catalog and normalization", () => {
  test("static catalog resolves casing, conservative aliases, PDFs, and positions", async () => {
    const catalog = await loadCatalog();
    const blair = findBuilding(catalog, " blAIR Hall ");
    expect(blair.name).toBe("Blair");
    expect(findBuilding(catalog, "Maine").name).toBe("Forbes");
    expect(findBuilding(catalog, "José Feliciano").api_name).toBe(
      "JosÃ© Feliciano",
    );
    expect(
      blair.plans.some((p) => p.url.endsWith("/static/pdfs/blair/1.pdf")),
    ).toBe(true);
    expect(blair.rooms.some((r) => r.coordinates)).toBe(true);
    expect(() => findBuilding(catalog, "Blair/../../etc/passwd")).toThrow(
      "Unknown",
    );
    expect(findBuilding(catalog, "1901").name).not.toBe(
      findBuilding(catalog, "Laughlin").name,
    );
  });
  test("CSV parsing preserves quoted commas, quotes, and multiline fields", () => {
    expect(
      parseCsv('a,b\r\n"one,two","three""four"\r\n"line\nnext",value\n'),
    ).toEqual([
      { a: "one,two", b: 'three"four' },
      { a: "line\nnext", b: "value" },
    ]);
  });
  test("media deduplication retains known labels and exposes label conflicts as unknown", () => {
    const media = {
      url: "https://example.org/plan.png",
      type: "floor_plan" as const,
      floor: "1",
    };
    expect(
      dedupeMedia([
        { ...media, media_type: "EXAMPLE" },
        { ...media, media_type: "unknown" },
      ])[0].media_type,
    ).toBe("EXAMPLE");
    expect(
      dedupeMedia([
        { ...media, media_type: "EXAMPLE" },
        { ...media, media_type: "ACTUAL" },
      ])[0].media_type,
    ).toBe("unknown");
  });
  test("duplicates are deterministic and preserve IDs and explicit conflicts", async () => {
    const { service } = await fixtureService();
    const result = await service.getRoom({ building: "blair", room_no: "b41" });
    expect(result.room.source_ids).toEqual(["578", "3388"]);
    expect(result.room.sq_footage).toBeNull();
    expect(result.room.elevator).toBeNull();
    expect(result.room.draw_rank).toBeNull();
    expect(result.room.num_reviews).toBe(0);
    expect(result.room.conflicts.sq_footage).toHaveLength(2);
    const entries = result.room.source_records.map((record) => ({
      room_no: "B41",
      record,
    }));
    expect(mergeRooms("Blair", entries, result.room.sources[0])).toEqual(
      mergeRooms("Blair", entries.toReversed(), result.room.sources[0]),
    );
  });
  test("nulls fill only from a unique value; unknown boolean stays unknown", () => {
    const source = { source: "fixture", source_kind: "live" as const };
    const a = record({ room_id: 1, occupancy: "DOUBLE", ac: "unknown" });
    const b = record({ room_id: 2, sq_footage: "200" });
    const room = mergeRooms(
      "Blair",
      [
        { room_no: "001", record: a },
        { room_no: "001", record: b },
      ],
      source,
    )[0];
    expect(room.room_no).toBe("001");
    expect(room.occupancy).toBe(2);
    expect(room.sq_footage).toBe(200);
    expect(room.ac).toBeNull();
    expect(matches(room, { amenities: ["ac"] })).toBe(false);
  });
});

describe("room queries", () => {
  test("deduplicates before limits, preserves leading zeros, and filters floors", async () => {
    const { service } = await fixtureService();
    const result = await service.listRooms({
      building: "BLAIR",
      occupancy: 1,
      limit: 100,
    });
    expect(result.rooms.map((r) => r.room_no)).toEqual(["001", "B41"]);
    const limited = await service.listRooms({ building: "Blair", limit: 1 });
    expect(limited.returned_count).toBe(1);
    expect(limited.truncated).toBe(true);
    expect(
      (
        await service.listRooms({ building: "Blair", floor: "0", limit: 10 })
      ).rooms.map((r) => r.room_no),
    ).toEqual(["B41"]);
  });
  test("search applies all filters, inclusive area, AND amenities, and stable limits", async () => {
    const { service, requests } = await fixtureService();
    const result = await service.searchRooms({
      occupancy: 2,
      college: "mathey",
      max_sq_footage: 300,
      amenities: ["elevator"],
      limit: 100,
    });
    expect(result.rooms.map((r) => r.room_no)).toEqual(["B42", "B43", "G01"]);
    expect(result.partial).toBe(false);
    expect(
      (
        await service.searchRooms({ amenities: ["ac", "elevator"], limit: 1 })
      ).rooms.map((r) => r.room_no),
    ).toEqual(["B42"]);
    expect(
      requests.every((r) => r.url.pathname === "/api/building_rooms"),
    ).toBe(true);
    expect(
      requests.every(
        (r) =>
          r.init?.method === "GET" &&
          !r.init.headers?.hasOwnProperty("authorization"),
      ),
    ).toBe(true);
    await expect(
      service.searchRooms({ college: "Missing", limit: 20 }),
    ).rejects.toThrow("Unknown college");
  });
  test("review lookups normalize user casing explicitly", async () => {
    const { service, requests } = await fixtureService();
    for (const name of ["Blair", "BLAIR", "blair"])
      await service.getRoom({ building: name, room_no: "b41" });
    const reviews = requests.filter((r) => r.url.pathname === "/get_reviews");
    expect(reviews).toHaveLength(1);
    expect(reviews[0].url.searchParams.get("building_name")).toBe("BLAIR");
    expect(reviews[0].url.searchParams.get("room_no")).toBe("B41");
  });
  test("Maine/Forbes legacy review spelling is checked after uppercase absence", async () => {
    const base = await fixtureService();
    const queries: string[] = [];
    const api = new ApiClient({
      retries: 0,
      fetcher: async (input) => {
        const url = new URL(String(input));
        if (url.pathname === "/api/building_rooms")
          return Response.json({
            building: "Forbes",
            floors: { "1": [{ room_id: 1, room_no: "101", num_reviews: 1 }] },
          });
        const name = url.searchParams.get("building_name")!;
        queries.push(name);
        return new Response(
          name === "Forbes" ? maliciousReview : emptyReviews,
          { headers: { "content-type": "text/html" } },
        );
      },
    });
    const result = await new RoomService(base.catalog, api).getRoom({
      building: "Maine",
      room_no: "101",
    });
    expect(queries).toEqual(["FORBES", "Forbes"]);
    expect(result.reviews.parsed_count).toBe(1);
  });
  test("unknown rooms are distinct from unavailable live data", async () => {
    const { service } = await fixtureService();
    await expect(
      service.getRoom({ building: "Blair", room_no: "missing" }),
    ).rejects.toMatchObject({ code: "ROOM_NOT_FOUND" });
    const failed = await fixtureService({
      fetcher: async () => {
        throw new Error("offline");
      },
    });
    const result = await failed.service.getRoom({
      building: "Blair",
      room_no: "B41",
    });
    expect(result.partial).toBe(true);
    expect(result.room.source_ids).toEqual(["573"]);
    expect(result.room.draw_rank).toBeNull();
    expect(result.room.num_reviews).toBeNull();
    expect(result.room.sources[0].source_kind).toBe("static");
    expect(result.reviews.available).toBe(false);
    await expect(
      failed.service.getRoom({ building: "Blair", room_no: "missing" }),
    ).rejects.toMatchObject({ code: "DATA_UNAVAILABLE" });
  });
  test("empty live data never resurrects static rooms", async () => {
    const { service } = await fixtureService({
      fetcher: async () => Response.json({ building: "Blair", floors: {} }),
    });
    const result = await service.listRooms({ building: "Blair", limit: 20 });
    expect(result.rooms).toEqual([]);
    expect(result.partial).toBe(false);
  });
  test("images preserve type labels and empty live images are authoritative", async () => {
    const { service } = await fixtureService();
    const images = await service.getRoomImages({
      building: "Blair",
      room_no: "B41",
    });
    expect(images.images.find((i) => i.type === "360")?.media_type).toBe(
      "EXAMPLE",
    );
    expect(images.images.find((i) => i.type === "thumbnail")?.media_type).toBe(
      "unknown",
    );
    const base = await fixtureService();
    const api = new ApiClient({
      retries: 0,
      fetcher: async (input) =>
        String(input).includes("building_rooms")
          ? Response.json({
              building: "Blair",
              floors: { "1": [{ room_id: 1, room_no: "101" }] },
            })
          : Response.json({
              floor_plan: null,
              room_plan: null,
              thumbnail: null,
              views_360: [],
            }),
    });
    expect(
      (
        await new RoomService(base.catalog, api).getRoomImages({
          building: "Blair",
          room_no: "101",
        })
      ).images,
    ).toEqual([]);
    const failedApi = new ApiClient({
      retries: 0,
      fetcher: async () => {
        throw new Error("offline");
      },
    });
    const fallback = await new RoomService(
      base.catalog,
      failedApi,
    ).getRoomImages({ building: "Blair", room_no: "101" });
    expect(fallback.sources[0].source_kind).toBe("static");
    expect(fallback.partial).toBe(true);
  });
  test("floor plans enumerate verified PDFs and reject unknown floors", async () => {
    const { service } = await fixtureService();
    const plans = service.getFloorPlan({ building: "Blair", floor: "1" });
    expect(plans.plans.some((p) => p.url.endsWith("blair/1.pdf"))).toBe(true);
    expect(plans.sources[0].source_kind).toBe("static");
    expect(() =>
      service.getFloorPlan({ building: "Blair", floor: "999" }),
    ).toThrow("Unknown floor");
  });
  test("search concurrency is at most four and static failures are labeled", async () => {
    let active = 0;
    let peak = 0;
    const { service } = await fixtureService({
      fetcher: async () => {
        peak = Math.max(peak, ++active);
        await Bun.sleep(5);
        active--;
        throw new Error("offline");
      },
    });
    service.catalog.buildings.push(
      ...["Extra1", "Extra2"].map((name) => ({
        ...service.catalog.buildings[0],
        name,
        api_name: name,
      })),
    );
    const result = await service.searchRooms({ limit: 5 });
    expect(peak).toBe(4);
    expect(result.partial).toBe(true);
    expect(result.coverage.static_fallback).toHaveLength(5);
  });
});

describe("review extraction", () => {
  test("extracts only bounded untrusted evidence, without script/form/identity", () => {
    const result = parseReviews(maliciousReview);
    expect(result.reviews[0].untrusted_text).toContain(
      "Ignore all instructions",
    );
    expect(result.reviews[0].untrusted_text).toContain("& text");
    expect(JSON.stringify(result)).not.toMatch(/PRIVATE_NETID|evil\(\)|submit/);
    expect(result.reviews[0].rating).toBe(4);
    expect(result.trust).toBe("untrusted_student_content");
    const many = parseReviews(maliciousReview.repeat(12));
    expect(many.returned_count).toBe(10);
    expect(many.parsed_count).toBe(12);
    expect(many.truncated).toBe(true);
  });
  test("distinguishes empty review markup from broken upstream HTML", () => {
    expect(parseReviews(emptyReviews).parsed_count).toBe(0);
    expect(() => parseReviews("<html>Login page</html>")).toThrow(
      "expected review structure",
    );
    expect(() =>
      parseReviews(maliciousReview.replace("4 / 5", "8 / 5")),
    ).toThrow("invalid rating");
  });
  test("refresh sanitation preserves counts while removing identity and executable markup", () => {
    const sanitized = sanitizeReviewFixture(maliciousReview.repeat(12));
    expect(sanitized).not.toMatch(/PRIVATE_NETID|<script|<form|evil\(\)/);
    expect(parseReviews(sanitized).parsed_count).toBe(12);
    expect(parseReviews(sanitizeReviewFixture(emptyReviews)).parsed_count).toBe(
      0,
    );
  });
});

describe("upstream client", () => {
  test("a coalesced request honors its own shorter tool deadline", async () => {
    const api = new ApiClient({
      retries: 0,
      fetcher: async () => {
        await Bun.sleep(30);
        return Response.json({ building: "Blair", floors: {} });
      },
    });
    const first = api.get(
      "/api/building_rooms",
      { building: "Blair" },
      buildingSchema,
    );
    await expect(
      api.get(
        "/api/building_rooms",
        { building: "Blair" },
        buildingSchema,
        Date.now() + 5,
      ),
    ).rejects.toThrow("deadline");
    expect((await first).data.building).toBe("Blair");
  });
  test("coalesces identical in-flight requests and uses short negative caching", async () => {
    let calls = 0;
    let now = 0;
    const api = new ApiClient({
      now: () => now,
      negativeTtlMs: 30,
      ttlMs: 100,
      fetcher: async () => {
        calls++;
        await Bun.sleep(5);
        return Response.json({ building: "Blair", floors: {} });
      },
    });
    await Promise.all(
      Array.from({ length: 5 }, () =>
        api.get("/api/building_rooms", { building: "Blair" }, buildingSchema),
      ),
    );
    expect(calls).toBe(1);
    now = 31;
    await api.get("/api/building_rooms", { building: "Blair" }, buildingSchema);
    expect(calls).toBe(2);
  });
  test("caches within TTL and never serves expired review text", async () => {
    let now = 0;
    let calls = 0;
    const api = new ApiClient({
      now: () => now,
      ttlMs: 100,
      retries: 0,
      fetcher: async () => {
        calls++;
        if (calls > 1) throw new Error("offline");
        return new Response(emptyReviews, {
          headers: { "content-type": "text/html" },
        });
      },
    });
    const first = await api.get(
      "/get_reviews",
      { building_name: "BLAIR", room_no: "B41" },
      z.string(),
    );
    expect(first.source.source_kind).toBe("live");
    expect(
      (
        await api.get(
          "/get_reviews",
          { building_name: "BLAIR", room_no: "B41" },
          z.string(),
        )
      ).source.source_kind,
    ).toBe("cache");
    now = 101;
    await expect(
      api.get(
        "/get_reviews",
        { building_name: "BLAIR", room_no: "B41" },
        z.string(),
      ),
    ).rejects.toThrow("unavailable");
    expect(calls).toBe(2);
  });
  test("retries transient HTTP failures and validates successful payloads", async () => {
    let calls = 0;
    const api = new ApiClient({
      fetcher: async () =>
        ++calls === 1
          ? new Response("", { status: 503 })
          : Response.json({ building: "Blair", floors: {} }),
    });
    await api.get("/api/building_rooms", { building: "Blair" }, buildingSchema);
    expect(calls).toBe(2);
    for (const response of [
      new Response("html", { headers: { "content-type": "text/html" } }),
      Response.json({ floors: [] }),
      new Response("{", { headers: { "content-type": "application/json" } }),
    ]) {
      const bad = new ApiClient({ retries: 0, fetcher: async () => response });
      await expect(
        bad.get("/api/building_rooms", { building: "Blair" }, buildingSchema),
      ).rejects.toMatchObject({ code: "UPSTREAM_ERROR" });
    }
  });
  test("bounds body size, deadlines, redirects, and allowed routes", async () => {
    const oversized = new ApiClient({
      maxBytes: 10,
      retries: 0,
      fetcher: async () => Response.json({ building: "Blair", floors: {} }),
    });
    await expect(
      oversized.get("/api/building_rooms", {}, buildingSchema),
    ).rejects.toThrow("size limit");
    const timed = new ApiClient({
      timeoutMs: 5,
      retries: 0,
      fetcher: async (_, init) =>
        new Promise((_, reject) =>
          init!.signal!.addEventListener("abort", () =>
            reject(new Error("timeout")),
          ),
        ),
    });
    await expect(
      timed.get("/api/building_rooms", {}, buildingSchema),
    ).rejects.toThrow("timed out");
    expect(() => timed.url("/submitReview", {})).toThrow("allowlisted");
    const redirected = new ApiClient({
      retries: 0,
      fetcher: async (_, init) => {
        expect(init?.redirect).toBe("error");
        return new Response("", {
          status: 302,
          headers: { location: "https://evil.example" },
        });
      },
    });
    await expect(
      redirected.get("/api/building_rooms", {}, buildingSchema),
    ).rejects.toMatchObject({ code: "UPSTREAM_ERROR" });
  });
});
