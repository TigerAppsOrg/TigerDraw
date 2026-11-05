import { createApp } from "./app";
import { loadCatalog } from "./data/catalog";
import { ApiClient } from "./data/client";
import { RoomService } from "./data/service";

const port = Number(process.env.PORT ?? 3333);
if (!Number.isInteger(port) || port < 1 || port > 65535)
  throw new Error("PORT must be an integer between 1 and 65535.");
const app = createApp(
  new RoomService(
    await loadCatalog(),
    new ApiClient({ baseUrl: process.env.TIGERDRAW_API_BASE }),
  ),
  {
    token: process.env.MCP_ACCESS_TOKEN,
    production: process.env.NODE_ENV === "production",
  },
);
const server = Bun.serve({
  hostname: process.env.HOST ?? "127.0.0.1",
  port,
  fetch: app.fetch,
  maxRequestBodySize: 64 * 1024,
  idleTimeout: 30,
});
let stopping = false;
async function stop() {
  if (stopping) return;
  stopping = true;
  await app.close();
  await server.stop(true);
}
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
