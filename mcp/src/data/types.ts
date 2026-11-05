export type Source = {
  source: string;
  source_kind: "live" | "cache" | "static";
  purpose?: "reference_asset" | "fallback";
  source_url?: string;
  retrieved_at?: string;
  revision?: string;
};

export type RoomFields = {
  occupancy: number | null;
  sq_footage: number | null;
  floor: string | null;
  elevator: boolean | null;
  bathroom: string | null;
  ac: boolean | null;
  draw_rank: number | null;
  num_reviews: number | null;
  avg_rating: number | null;
  has_360: boolean | null;
  res_college: string | null;
};
export type RoomRecord = RoomFields & { source_id: string | null };
export type Room = RoomFields & {
  building: string;
  room_no: string;
  source_ids: string[];
  source_records: RoomRecord[];
  conflicts: Record<string, { value: unknown; source_ids: string[] }[]>;
  sources: Source[];
  warnings: string[];
};
export type Media = {
  url: string;
  preview_url?: string;
  type: "floor_plan" | "room_plan" | "thumbnail" | "360";
  media_type: "ACTUAL" | "EXAMPLE" | "unknown";
  floor?: string;
};
export type StaticRoom = {
  room_no: string;
  record: RoomRecord;
  media: Media[];
  coordinates?: number[];
};
export type Building = {
  name: string;
  aliases: string[];
  api_name: string;
  review_name: string;
  colleges: string[];
  rooms: StaticRoom[];
  plans: Media[];
  coordinates?: number[];
};
export type Catalog = {
  revision: string;
  generated_at: string;
  inputs: string[];
  buildings: Building[];
};

export class DataError extends Error {
  constructor(
    public code:
      | "UNKNOWN_BUILDING"
      | "ROOM_NOT_FOUND"
      | "DATA_UNAVAILABLE"
      | "UPSTREAM_ERROR",
    message: string,
    public retryable = false,
    public source?: string,
  ) {
    super(message);
  }
}

export const compare = (a: string, b: string) =>
  a.localeCompare(b, "en", { numeric: true }) || a.localeCompare(b);
export const key = (value: string) => value.trim().toUpperCase();
export const aliasKey = (value: string) => key(value).replace(/\s+HALL$/, "");
export function safeUrl(value: unknown): string | undefined {
  if (typeof value !== "string") return;
  try {
    const url = new URL(value);
    if (
      ["https:", "http:"].includes(url.protocol) &&
      !url.username &&
      !url.password
    )
      return url.href;
  } catch {
    /* Invalid upstream URL is omitted. */
  }
}

export function dedupeMedia(items: Media[]): Media[] {
  const groups = new Map<string, Media[]>();
  for (const item of items) {
    const id = JSON.stringify([item.url, item.type, item.floor ?? ""]);
    groups.set(id, [...(groups.get(id) ?? []), item]);
  }
  return [...groups.values()]
    .map((group) => {
      const labels = new Set(
        group.map((m) => m.media_type).filter((label) => label !== "unknown"),
      );
      return {
        ...group[0],
        media_type: labels.size === 1 ? [...labels][0] : "unknown",
      } as Media;
    })
    .sort(
      (a, b) =>
        compare(a.floor ?? "", b.floor ?? "") ||
        compare(a.type, b.type) ||
        compare(a.url, b.url),
    );
}
