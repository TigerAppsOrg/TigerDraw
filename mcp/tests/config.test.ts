import { expect, test } from "bun:test";
import { readConfig } from "../src/config";
import { RoomService } from "../src/data/service";
import { createApp } from "../src/app";
import { fixtureService } from "./helpers";

const token = "dummy-production-test-token";
test("production requires a token and defaults to public HTTPS preview URLs", async () => {
  expect(() => readConfig({ NODE_ENV: "production" })).toThrow(
    "required in production",
  );
  const config = readConfig({
    NODE_ENV: "production",
    MCP_ACCESS_TOKEN: token,
  });
  expect(config.assetOrigin).toBe("https://draw.tigerapps.org");
  const fixture = await fixtureService();
  const service = new RoomService(
    fixture.catalog,
    fixture.api,
    Date.now,
    config.assetOrigin,
  );
  const plans = service.getFloorPlan({ building: "Blair", floor: "1" }).plans;
  expect(
    plans
      .filter((p) => p.preview_url)
      .every((p) => p.preview_url!.startsWith("https://draw.tigerapps.org/")),
  ).toBe(true);
  const app = createApp(service, config);
  try {
    for (const authorization of ["", "Bearer incorrect-token"])
      expect(
        (
          await app.fetch(
            new Request("https://draw.tigerapps.org/mcp", {
              method: "POST",
              headers: { authorization },
              body: "{}",
            }),
          )
        ).status,
      ).toBe(401);
    const response = await app.fetch(
      new Request("https://draw.tigerapps.org/mcp", {
        method: "POST",
        headers: {
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
          accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
      }),
    );
    expect(response.status).toBe(200);
  } finally {
    await app.close();
  }
});
test("production rejects local or non-HTTPS preview origins", () => {
  for (const origin of [
    "http://draw.tigerapps.org",
    "http://127.0.0.1:3333",
    "https://localhost",
    "https://localhost.",
    "https://preview.localhost.",
    "https://127.1",
    "https://preview.localhost",
    "https://127.0.0.1",
    "https://[::1]",
    "https://0.0.0.0",
    "https://10.0.0.1",
    "https://preview.local",
  ])
    expect(() =>
      readConfig({
        NODE_ENV: "production",
        MCP_ACCESS_TOKEN: token,
        TIGERDRAW_ASSET_ORIGIN: origin,
      }),
    ).toThrow("public hostname");
  expect(
    readConfig({
      NODE_ENV: "production",
      MCP_ACCESS_TOKEN: token,
      TIGERDRAW_ASSET_ORIGIN: "https://cdn.tigerapps.org",
    }).assetOrigin,
  ).toBe("https://cdn.tigerapps.org");
  expect(
    readConfig({ TIGERDRAW_ASSET_ORIGIN: "http://127.0.0.1:3333" }).assetOrigin,
  ).toBe("http://127.0.0.1:3333");
});
test("atomic preview-builder regression checks run without Poppler or credentials", () => {
  const result = Bun.spawnSync(
    [
      "python3",
      "-m",
      "unittest",
      "discover",
      "-s",
      "tests",
      "-p",
      "test_preview_builder.py",
    ],
    { cwd: new URL("..", import.meta.url).pathname },
  );
  if (result.exitCode) throw new Error(result.stderr.toString());
  expect(result.exitCode).toBe(0);
});
