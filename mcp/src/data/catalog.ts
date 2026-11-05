import {
  aliasKey,
  compare,
  DataError,
  type Building,
  type Catalog,
  type Source,
} from "./types";

export function findBuilding(catalog: Catalog, input: string): Building {
  const normalized = aliasKey(input);
  const matches = catalog.buildings.filter((b) =>
    [b.name, ...b.aliases].some((a) => aliasKey(a) === normalized),
  );
  if (matches.length !== 1)
    throw new DataError(
      "UNKNOWN_BUILDING",
      `Unknown or ambiguous building '${input}'. Use list_buildings for supported names.`,
    );
  return matches[0];
}
export function staticSource(catalog: Catalog, purpose: Source["purpose"] = "fallback"): Source {
  return {
    source: "TigerDraw/mcp/src/generated/catalog.json",
    source_url: "https://github.com/TigerAppsOrg/TigerDraw",
    source_kind: "static",
    purpose,
    revision: catalog.revision,
  };
}
export async function loadCatalog(
  path = new URL("../generated/catalog.json", import.meta.url),
): Promise<Catalog> {
  const catalog = (await Bun.file(path).json()) as Catalog;
  if (
    !catalog.revision ||
    !Array.isArray(catalog.buildings) ||
    !catalog.buildings.length
  ) {
    throw new Error("Invalid catalog. Run bun run catalog:build.");
  }
  catalog.buildings.sort((a, b) => compare(a.name, b.name));
  return catalog;
}
