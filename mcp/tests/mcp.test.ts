import { expect, test } from "bun:test";
import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { createApp } from "../src/app";
import { boundedResult } from "../src/server";
import { fixtureApp, fixtureService, payload } from "./helpers";

const names = [
  "get_floor_plan",
  "get_room",
  "get_room_images",
  "list_buildings",
  "list_rooms",
  "search_rooms",
];
const headers = {
  "content-type": "application/json",
  accept: "application/json, text/event-stream",
  authorization: "Bearer fixture-token",
};
async function rpc(
  app: ReturnType<typeof createApp>,
  method: string,
  params?: unknown,
  path = "/mcp",
) {
  return app.fetch(
    new Request(`http://localhost${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method,
        ...(params ? { params } : {}),
      }),
    }),
  );
}
async function messages(response: Response) {
  const text = await response.text();
  return response.headers.get("content-type")?.includes("text/event-stream")
    ? text
        .split("\n")
        .filter((l) => l.startsWith("data: "))
        .map((l) => JSON.parse(l.slice(6)))
    : [JSON.parse(text)];
}

test("requires a production token and rejects missing/wrong authentication", async () => {
  const { service } = await fixtureService();
  expect(() => createApp(service, { production: true })).toThrow(
    "required in production",
  );
  const app = createApp(service, { token: "fixture-token" });
  try {
    for (const authorization of ["", "Bearer wrong"]) {
      const response = await app.fetch(
        new Request("http://localhost/mcp", {
          method: "POST",
          headers: { ...headers, authorization },
          body: "{}",
        }),
      );
      expect(response.status).toBe(401);
    }
    expect(
      (await app.fetch(new Request("http://localhost/healthz"))).status,
    ).toBe(200);
    expect(
      (
        await app.fetch(
          new Request("http://localhost/submitReview", { method: "POST" }),
        )
      ).status,
    ).toBe(404);
  } finally {
    await app.close();
  }
});

test("legacy initialize and bare tool listing work on both endpoint spellings", async () => {
  const { app } = await fixtureApp();
  try {
    const init = await rpc(app, "initialize", {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "legacy-test", version: "1" },
    });
    expect(init.status).toBe(200);
    expect((await messages(init))[0].result.serverInfo.name).toBe("tigerdraw");
    for (const path of ["/mcp", "/mcp/"]) {
      const response = await rpc(app, "tools/list", undefined, path);
      const tools = (await messages(response))[0].result.tools;
      expect(tools.map((t: { name: string }) => t.name).sort()).toEqual(names);
      expect(
        tools.every(
          (t: {
            annotations: { readOnlyHint: boolean; destructiveHint: boolean };
            inputSchema: { additionalProperties: boolean };
          }) =>
            t.annotations.readOnlyHint &&
            !t.annotations.destructiveHint &&
            t.inputSchema.additionalProperties === false,
        ),
      ).toBe(true);
    }
    for (const method of ["GET", "DELETE"]) {
      const response = await app.fetch(
        new Request("http://localhost/mcp", { method, headers }),
      );
      expect(response.status).toBe(405);
    }
  } finally {
    await app.close();
  }
});

test("modern SDK negotiation and all six tool calls work without sockets or credentials", async () => {
  const { app } = await fixtureApp();
  const client = new Client(
    { name: "tigerdraw-integration", version: "1" },
    { versionNegotiation: { mode: "auto" } },
  );
  try {
    await client.connect(
      new StreamableHTTPClientTransport(new URL("http://localhost/mcp"), {
        requestInit: { headers: { authorization: "Bearer fixture-token" } },
        fetch: async (input, init) =>
          app.fetch(
            input instanceof Request ? input : new Request(input, init),
          ),
      }),
    );
    expect(client.getProtocolEra()).toBe("modern");
    expect((await client.listTools()).tools.map((t) => t.name).sort()).toEqual(
      names,
    );
    for (const [name, args] of [
      ["list_buildings", {}],
      ["list_rooms", { building: "Blair", occupancy: 2, limit: 2 }],
      ["get_room", { building: "blair", room_no: "b41" }],
      ["get_room_images", { building: "Blair", room_no: "B41" }],
      ["get_floor_plan", { building: "Blair", floor: "1" }],
      ["search_rooms", { college: "Mathey", occupancy: 2, limit: 2 }],
    ] as const) {
      const result = await client.callTool({ name, arguments: args });
      expect(result.isError).not.toBe(true);
      expect(payload(result)).toBeObject();
    }
    const error = await client.callTool({
      name: "get_room",
      arguments: { building: "Blair", room_no: "Missing" },
    });
    expect(error.isError).toBe(true);
    expect(payload(error).error.code).toBe("ROOM_NOT_FOUND");
  } finally {
    await client.close();
    await app.close();
  }
});

test("invalid limits, enums, unknown arguments, and oversized bodies are rejected", async () => {
  const { app } = await fixtureApp();
  try {
    for (const args of [
      { building: "Blair", limit: 101 },
      { building: "Blair", limit: 0 },
      { building: "Blair", write: true },
    ]) {
      const response = await rpc(app, "tools/call", {
        name: "list_rooms",
        arguments: args,
      });
      const message = (await messages(response))[0];
      expect(Boolean(message.error || message.result?.isError)).toBe(true);
    }
    for (const args of [{ amenities: ["pool"] }, { amenities: ["ac", "ac"] }]) {
      const message = (
        await messages(
          await rpc(app, "tools/call", {
            name: "search_rooms",
            arguments: args,
          }),
        )
      )[0];
      expect(Boolean(message.error || message.result?.isError)).toBe(true);
    }
    const response = await app.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers,
        body: "x".repeat(65537),
      }),
    );
    expect(response.status).toBe(413);
  } finally {
    await app.close();
  }
});

test("response budget removes whole entries, keeps valid JSON and truncation metadata", () => {
  const result = boundedResult({
    rooms: Array.from({ length: 100 }, (_, i) => ({
      room_no: String(i),
      notes: "x".repeat(3000),
    })),
    returned_count: 100,
    truncated: false,
    partial: false,
    sources: [{ source: "fixture" }],
  });
  const data = payload(result);
  expect(
    Buffer.byteLength((result.content[0] as { text: string }).text),
  ).toBeLessThanOrEqual(65536);
  expect(data.returned_count).toBe(data.rooms.length);
  expect(data.truncated).toBe(true);
  expect(data.sources).toHaveLength(1);
});
