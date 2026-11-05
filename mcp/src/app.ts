import { timingSafeEqual, createHash, randomUUID } from "node:crypto";
import { createMcpHandler } from "@modelcontextprotocol/server";
import { RoomService } from "./data/service";
import { createServer } from "./server";

function authorized(request: Request, token: string): boolean {
  const supplied =
    request.headers.get("authorization")?.match(/^Bearer\s+(\S+)\s*$/i)?.[1] ??
    "";
  return timingSafeEqual(
    createHash("sha256").update(supplied).digest(),
    createHash("sha256").update(token).digest(),
  );
}
export function createApp(
  service: RoomService,
  options: {
    token?: string;
    production?: boolean;
  } = {},
) {
  // Only catalog-listed public PNG previews are served, never arbitrary files.
  const previews = new Set(
    service.catalog.buildings.flatMap((building) =>
      building.plans.flatMap((plan) =>
        plan.preview_url ? [new URL(plan.preview_url).pathname] : [],
      ),
    ),
  );
  const token = options.token?.trim() ?? "";
  if (options.production && !token)
    throw new Error("MCP_ACCESS_TOKEN is required in production.");
  const handler = createMcpHandler(() => createServer(service), {
    legacy: "stateless",
  });
  return {
    async fetch(request: Request): Promise<Response> {
      const url = new URL(request.url);
      if (previews.has(url.pathname)) {
        if (!["GET", "HEAD"].includes(request.method))
          return new Response("Method not allowed", { status: 405 });
        const file = Bun.file(
          new URL(`../../${url.pathname.slice(1)}`, import.meta.url),
        );
        if (!(await file.exists()))
          return new Response("Preview unavailable", { status: 404 });
        return new Response(request.method === "HEAD" ? null : file, {
          headers: {
            "content-type": "image/png",
            "cache-control": "public, max-age=31536000, immutable",
            "x-content-type-options": "nosniff",
          },
        });
      }
      if (url.pathname === "/healthz" && request.method === "GET")
        return Response.json({
          status: "ok",
          catalog_revision: service.catalog.revision,
          buildings: service.catalog.buildings.length,
        });
      if (url.pathname !== "/mcp" && url.pathname !== "/mcp/")
        return new Response("Not found", { status: 404 });
      if (token && !authorized(request, token))
        return Response.json(
          {
            jsonrpc: "2.0",
            id: null,
            error: {
              code: -32001,
              message: "Unauthorized: missing or invalid bearer token.",
            },
          },
          { status: 401, headers: { "www-authenticate": "Bearer" } },
        );
      const requestId = randomUUID();
      const requestHeaders = new Headers(request.headers);
      requestHeaders.set("x-request-id", requestId);
      if (!["POST", "GET", "DELETE"].includes(request.method))
        return new Response("Method not allowed", { status: 405 });
      try {
        if (request.method === "POST") {
          // Limit streamed bodies as well as Content-Length. The SDK receives a
          // fresh Request so modern/legacy classification can read it normally.
          const reader = request.body?.getReader();
          let size = 0;
          const chunks: Uint8Array[] = [];
          if (reader)
            while (true) {
              const next = await reader.read();
              if (next.done) break;
              size += next.value.byteLength;
              if (size > 64 * 1024) {
                await reader.cancel();
                return new Response("Request too large", { status: 413 });
              }
              chunks.push(next.value);
            }
          request = new Request(request.url, {
            method: request.method,
            headers: requestHeaders,
            body: Buffer.concat(chunks),
            signal: request.signal,
          });
        } else {
          request = new Request(request, { headers: requestHeaders });
        }
        const response = await handler.fetch(request);
        response.headers.set("x-request-id", requestId);
        return response;
      } catch {
        return Response.json(
          { error: "MCP request failed" },
          { status: 500, headers: { "x-request-id": requestId } },
        );
      }
    },
    close: () => handler.close(),
  };
}
