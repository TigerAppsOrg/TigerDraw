import { isIP } from "node:net";

export function assetOrigin(
  value = "https://draw.tigerapps.org",
  production = false,
): string {
  const url = new URL(value);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  )
    throw new Error(
      "TIGERDRAW_ASSET_ORIGIN must be an HTTP(S) origin without a path or credentials.",
    );
  const hostname = url.hostname
    .toLowerCase()
    .replace(/^\[|\]$/g, "")
    .replace(/\.+$/, "");
  if (
    production &&
    (url.protocol !== "https:" ||
      isIP(hostname) !== 0 ||
      hostname === "localhost" ||
      hostname.endsWith(".localhost") ||
      hostname.endsWith(".local") ||
      !hostname.includes("."))
  )
    throw new Error(
      "Production preview URLs require HTTPS and a public hostname; loopback, local, and IP-address origins are not permitted.",
    );
  return url.origin;
}

export function readConfig(env: Record<string, string | undefined>) {
  const production = env.NODE_ENV === "production";
  const token = env.MCP_ACCESS_TOKEN?.trim() ?? "";
  if (production && !token)
    throw new Error("MCP_ACCESS_TOKEN is required in production.");
  const port = Number(env.PORT ?? 3333);
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw new Error("PORT must be an integer between 1 and 65535.");
  return {
    production,
    token,
    port,
    host: env.HOST || "127.0.0.1",
    assetOrigin: assetOrigin(
      env.TIGERDRAW_ASSET_ORIGIN || undefined,
      production,
    ),
    apiBaseUrl: env.TIGERDRAW_API_BASE,
  };
}
