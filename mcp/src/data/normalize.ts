import {
  compare,
  key,
  type Room,
  type RoomFields,
  type RoomRecord,
  type Source,
} from "./types";

export function numeric(value: unknown): number | null {
  if (typeof value !== "number" && typeof value !== "string") return null;
  if (String(value).trim() === "") return null;
  const result = Number(value);
  return Number.isFinite(result) && result >= 0 ? result : null;
}
export function boolean(value: unknown): boolean | null {
  if (value === true || value === false) return value;
  if (value === 1 || value === 0) return Boolean(value);
  if (typeof value === "string") {
    if (["YES", "TRUE", "1"].includes(key(value))) return true;
    if (["NO", "FALSE", "0"].includes(key(value))) return false;
  }
  return null;
}
export function label(value: unknown): string | null {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const text = String(value).trim();
  return text && !["UNKNOWN", "NULL", "N/A"].includes(key(text)) ? text : null;
}
export function record(
  raw: Record<string, unknown>,
  isStatic = false,
): RoomRecord {
  const occupancies: Record<string, number> = {
    SINGLE: 1,
    DOUBLE: 2,
    TRIPLE: 3,
    QUAD: 4,
    QUINT: 5,
    "6-PERSON": 6,
  };
  const occ = occupancies[key(String(raw.occupancy))] ?? numeric(raw.occupancy);
  return {
    source_id: label(raw.room_id),
    occupancy: occ && Number.isInteger(occ) ? occ : null,
    sq_footage: numeric(raw.sq_footage),
    floor: label(raw.floor)?.toUpperCase() ?? null,
    elevator: boolean(raw.elevator),
    bathroom: label(raw.bathroom)?.toUpperCase() ?? null,
    ac: boolean(raw.ac),
    res_college: label(raw.res_college),
    draw_rank: isStatic ? null : numeric(raw.draw_rank),
    num_reviews: isStatic ? null : numeric(raw.num_reviews),
    avg_rating: isStatic ? null : numeric(raw.avg_rating),
    has_360: isStatic ? null : boolean(raw.has_360),
  };
}

export function mergeRooms(
  building: string,
  entries: { room_no: string; record: RoomRecord }[],
  source: Source,
): Room[] {
  const grouped = new Map<string, RoomRecord[]>();
  for (const entry of entries) {
    const roomNo = key(entry.room_no);
    const rows = grouped.get(roomNo) ?? [];
    rows.push(entry.record);
    grouped.set(roomNo, rows);
  }
  return [...grouped]
    .sort(([a], [b]) => compare(a, b))
    .map(([room_no, rows]) => {
      rows.sort(
        (a, b) =>
          compare(a.source_id ?? "", b.source_id ?? "") ||
          compare(JSON.stringify(a), JSON.stringify(b)),
      );
      const fields = Object.keys(rows[0]).filter(
        (k) => k !== "source_id",
      ) as (keyof RoomFields)[];
      const values = {} as RoomFields;
      const conflicts: Room["conflicts"] = {};
      for (const field of fields) {
        const candidates = new Map<
          string,
          { value: unknown; source_ids: string[] }
        >();
        for (const row of rows) {
          if (row[field] === null) continue;
          const encoded = JSON.stringify(row[field]);
          const candidate = candidates.get(encoded) ?? {
            value: row[field],
            source_ids: [],
          };
          if (row.source_id && !candidate.source_ids.includes(row.source_id))
            candidate.source_ids.push(row.source_id);
          candidates.set(encoded, candidate);
        }
        Object.assign(values, {
          [field]:
            candidates.size === 1 ? [...candidates.values()][0].value : null,
        });
        if (candidates.size > 1)
          conflicts[field] = [...candidates]
            .sort(([a], [b]) => compare(a, b))
            .map(([, value]) => value);
      }
      return {
        building,
        room_no,
        ...values,
        source_ids: [
          ...new Set(rows.flatMap((r) => (r.source_id ? [r.source_id] : []))),
        ].sort(compare),
        source_records: rows,
        conflicts,
        sources: [source],
        warnings: Object.keys(conflicts).length
          ? [
              `Conflicting source records: ${Object.keys(conflicts).join(", ")}.`,
            ]
          : [],
      };
    });
}

export type Filters = {
  occupancy?: number;
  floor?: string;
  college?: string;
  amenities?: ("ac" | "elevator")[];
  max_sq_footage?: number;
};
export const collegeKey = (value: string) =>
  key(value).replace(/\s+COLLEGE$/, "");
export function matches(room: Room, filters: Filters): boolean {
  return (
    (filters.occupancy === undefined || room.occupancy === filters.occupancy) &&
    (filters.floor === undefined || room.floor === key(filters.floor)) &&
    (filters.college === undefined ||
      (room.res_college !== null &&
        collegeKey(room.res_college) === collegeKey(filters.college))) &&
    (filters.max_sq_footage === undefined ||
      (room.sq_footage !== null &&
        room.sq_footage <= filters.max_sq_footage)) &&
    (filters.amenities ?? []).every((amenity) => room[amenity] === true)
  );
}
