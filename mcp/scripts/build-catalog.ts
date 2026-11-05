import { createHash } from "node:crypto";
import { readFile, readdir, writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { record } from "../src/data/normalize";
import {
  aliasKey,
  compare,
  dedupeMedia,
  key,
  safeUrl,
  type Building,
  type Catalog,
  type Media,
} from "../src/data/types";

// RFC 4180 fields, including quoted commas/newlines and doubled quotes.
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (char === '"') {
      if (quoted && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (!quoted && (char === "," || char === "\n")) {
      row.push(cell.replace(/\r$/, ""));
      cell = "";
      if (char === "\n") {
        if (row.some(Boolean)) rows.push(row);
        row = [];
      }
    } else cell += char;
  }
  if (quoted) throw new Error("Unterminated CSV field");
  if (cell || row.length) {
    row.push(cell.replace(/\r$/, ""));
    rows.push(row);
  }
  const headers = rows.shift() ?? [];
  return rows.map((values) =>
    Object.fromEntries(
      headers.map((h, i) => [h.replace(/^\uFEFF/, ""), values[i] ?? ""]),
    ),
  );
}
const extras: Record<string, string[]> = {
  Forbes: ["Maine", "Forbes Main"],
  "99Alexander": ["99 Alexander", "99 Alexander Street"],
  "2Dickinson": ["2 Dickinson", "2 Dickinson Street"],
  "JosÃ© Feliciano": ["José Feliciano", "Feliciano", "Jose Feliciano"],
  "Kwanza Jones": ["Jones"],
  "Murley-Pivirotto": ["Murley", "Murley Pivirotto"],
};
const pdfNames: Record<string, string> = {
  feliciano: "JosÃ© Feliciano",
  jones: "Kwanza Jones",
  murley: "Murley-Pivirotto",
  laughlin1901: "1901",
};
const inputFiles = [
  "RoomInfo_RoomViewer.csv",
  "data-scraping/room_images.json",
  "data-scraping/room_360_images.json",
  "static/assets/js/room_positions.json",
  "static/assets/js/buildings.js",
  "static/pdfs/floor_plans.json",
];

export async function buildCatalog(
  root = fileURLToPath(new URL("../../", import.meta.url)),
): Promise<Catalog> {
  const content = await Promise.all(
    inputFiles.map((p) => readFile(join(root, p), "utf8")),
  );
  const rows = parseCsv(content[0]);
  const images = JSON.parse(content[1]);
  const views = JSON.parse(content[2]);
  const positions = JSON.parse(content[3]);
  const manifest = JSON.parse(content[5]) as Record<string, string[]>;
  const buildings = new Map<string, Building>();
  const mediaFor = (row: Record<string, string>): Media[] => {
    const result: Media[] = [];
    for (const image of [
      ...(images[row.RoomID] ?? []),
      ...(views[row.RoomID] ?? []),
    ]) {
      const url = safeUrl(image.url);
      const type = String(image.type).toLowerCase();
      if (
        !url ||
        !["floor_plan", "room_plan", "thumbnail", "360"].includes(type)
      )
        continue;
      result.push({
        url,
        type: type as Media["type"],
        media_type: ["ACTUAL", "EXAMPLE"].includes(image.mediaType)
          ? image.mediaType
          : "unknown",
        ...(type === "floor_plan" ? { floor: key(row.Floor) } : {}),
      });
    }
    const plan = safeUrl(row.FilePath);
    if (plan)
      result.push({
        url: plan,
        type: "floor_plan",
        media_type: "unknown",
        floor: key(row.Floor),
      });
    return dedupeMedia(result);
  };
  for (const row of rows) {
    const name = row.Hall;
    const building = buildings.get(name) ?? {
      name: name === "JosÃ© Feliciano" ? "José Feliciano" : name,
      aliases: [...new Set([name, `${name} Hall`, ...(extras[name] ?? [])])],
      api_name: name,
      review_name: key(name),
      colleges: [],
      rooms: [],
      plans: [],
    };
    if (!building.colleges.includes(row.College))
      building.colleges.push(row.College);
    const media = mediaFor(row);
    const positionName =
      name === "Kwanza Jones"
        ? "JONES"
        : name === "JosÃ© Feliciano"
          ? "FELICIANO"
          : key(name);
    const coordinates = positions[positionName]?.[key(row.Room)];
    building.rooms.push({
      room_no: key(row.Room),
      record: record(
        {
          room_id: row.ID,
          occupancy: row.Type,
          sq_footage: row.Sqft,
          floor: row.Floor,
          elevator: row.Elevator,
          bathroom: row.Bathroom,
          ac: row.AC,
          res_college: row.College,
        },
        true,
      ),
      media,
      ...(coordinates ? { coordinates } : {}),
    });
    building.plans.push(...media.filter((m) => m.type === "floor_plan"));
    buildings.set(name, building);
  }
  // Parse only the JSON value; never evaluate JavaScript from the asset.
  const geoJson = content[4].match(
    /var buildingData\s*=\s*(\{[^]*\})\s*;?\s*$/,
  )?.[1];
  if (!geoJson)
    throw new Error(
      "buildings.js no longer contains the expected buildingData JSON",
    );
  const features = JSON.parse(geoJson).features as {
    properties: { name?: string };
    geometry?: { type: string; coordinates: unknown };
  }[];
  for (const feature of features) {
    const name = feature.properties.name;
    if (!name || name.includes(",")) continue; // Combined map features are not aliases for one hall.
    const matches = [...buildings.values()].filter((b) =>
      [b.name, ...b.aliases].some((a) => aliasKey(a) === aliasKey(name)),
    );
    if (matches.length === 1) matches[0].aliases.push(name);
  }
  const previewManifestPath = "static/previews/floor-plans.json";
  const previewManifestText = await readFile(
    join(root, previewManifestPath),
    "utf8",
  );
  const previewManifest = JSON.parse(previewManifestText) as Record<
    string,
    { url: string; sha256: string; preview_sha256: string }
  >;
  const pdfPaths: string[] = [];
  for (const dir of (
    await readdir(join(root, "static/pdfs"), { withFileTypes: true })
  ).filter((d) => d.isDirectory())) {
    const target = pdfNames[dir.name] ?? dir.name;
    const building = [...buildings.values()].find(
      (b) => aliasKey(b.api_name) === aliasKey(target),
    );
    if (!building) continue;
    const files = await readdir(join(root, "static/pdfs", dir.name));
    for (const filename of files
      .filter((f) => /^[A-Za-z0-9_-]+\.pdf$/.test(f))
      .sort(compare)) {
      const path = `static/pdfs/${dir.name}/${filename}`;
      pdfPaths.push(path);
      const preview = previewManifest[`/${path}`];
      const digest = createHash("sha256")
        .update(await readFile(join(root, path)))
        .digest("hex");
      if (!preview || preview.sha256 !== digest)
        throw new Error(
          `Missing or stale PDF preview for ${path}; run bun run previews:build.`,
        );
      const previewUrl = new URL(preview.url);
      if (
        previewUrl.origin !== "https://draw.tigerapps.org" ||
        !previewUrl.pathname.startsWith("/static/previews/floor-plans/") ||
        !previewUrl.pathname.endsWith(`-${digest.slice(0, 12)}.png`)
      )
        throw new Error(`Invalid preview URL for ${path}`);
      const previewBytes = await readFile(
        join(root, previewUrl.pathname.slice(1)),
      );
      if (
        createHash("sha256").update(previewBytes).digest("hex") !==
        preview.preview_sha256
      )
        throw new Error(
          `Corrupt PDF preview for ${path}; run bun run previews:build.`,
        );
      building.plans.push({
        url: `https://draw.tigerapps.org/${path}`,
        preview_url: preview.url,
        floor: filename.replace(/\.pdf$/, "").toUpperCase(),
        type: "floor_plan",
        media_type: "unknown",
      });
    }
    for (const floor of manifest[dir.name] ?? []) {
      if (!files.includes(`${floor}.pdf`))
        throw new Error(`Missing manifest target: ${dir.name}/${floor}.pdf`);
    }
  }
  const hash = createHash("sha256");
  content.forEach((c) => hash.update(c));
  hash.update(previewManifestText);
  for (const path of pdfPaths.sort(compare)) {
    hash.update(path);
    hash.update(await readFile(join(root, path)));
  }
  return {
    revision: hash.digest("hex"),
    generated_at: new Date().toISOString(),
    inputs: [...inputFiles, previewManifestPath, ...pdfPaths.sort(compare)],
    buildings: [...buildings.values()]
      .sort((a, b) => compare(a.name, b.name))
      .map((b) => ({
        ...b,
        aliases: [...new Set(b.aliases)].sort(compare),
        colleges: b.colleges.sort(compare),
        plans: dedupeMedia(b.plans),
        rooms: b.rooms.sort((a, b) => compare(a.room_no, b.room_no)),
      })),
  };
}
if (import.meta.main) {
  const catalog = await buildCatalog();
  const output = new URL("../src/generated/catalog.json", import.meta.url);
  await mkdir(fileURLToPath(new URL(".", output)), { recursive: true });
  await writeFile(output, JSON.stringify(catalog));
  console.log(
    `Built ${catalog.buildings.length} buildings, ${catalog.buildings.reduce((n, b) => n + b.rooms.length, 0)} static rooms (${catalog.revision.slice(0, 12)}).`,
  );
}
