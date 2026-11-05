import { readConfig } from "./config";
import { createApp } from "./app";
import { loadCatalog } from "./data/catalog";
import { ApiClient } from "./data/client";
import { RoomService } from "./data/service";

const config = readConfig(process.env);
const app = createApp(
  new RoomService(
    await loadCatalog(),
    new ApiClient({ baseUrl: config.apiBaseUrl }),
    Date.now,
    config.assetOrigin,
  ),
  {
    token: config.token,
    production: config.production,
  },
);
const server = Bun.serve({
  hostname: config.host,
  port: config.port,
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
