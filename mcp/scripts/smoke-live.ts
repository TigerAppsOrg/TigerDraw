import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { ApiClient, buildingSchema, imagesSchema } from "../src/data/client";
import { parseReviews } from "../src/data/reviews";
import { z } from "zod";

const endpoint = process.env.TIGERDRAW_MCP_URL;
if (endpoint) {
  const client = new Client(
    { name: "tigerdraw-live-smoke", version: "1" },
    { versionNegotiation: { mode: "auto" } },
  );
  try {
    await client.connect(
      new StreamableHTTPClientTransport(new URL(endpoint), {
        requestInit: {
          headers: process.env.MCP_ACCESS_TOKEN
            ? { authorization: `Bearer ${process.env.MCP_ACCESS_TOKEN}` }
            : {},
        },
      }),
    );
    const tools = (await client.listTools()).tools;
    if (tools.length !== 6)
      throw new Error(`Expected six tools; received ${tools.length}`);
    for (const [name, args] of [
      ["list_buildings", {}],
      ["get_room", { building: "Blair", room_no: "B41" }],
      ["get_room_images", { building: "Blair", room_no: "B41" }],
      ["get_floor_plan", { building: "Blair" }],
    ] as const) {
      const result = await client.callTool({ name, arguments: args });
      if (result.isError)
        throw new Error(`${name} failed: ${JSON.stringify(result.content)}`);
      const content = result.content as { text: string }[];
      const data = JSON.parse(content[0].text);
      if (
        name === "get_room" &&
        (data.room.sources.some(
          (s: { source_kind: string }) => s.source_kind === "static",
        ) ||
          !data.reviews.available)
      )
        throw new Error(
          "Room smoke used fallback or unavailable reviews; live verification is incomplete.",
        );
      if (name === "get_room_images" && data.partial)
        throw new Error(
          "Image smoke used fallback; live verification is incomplete.",
        );
      console.log(`${name}: ok`);
    }
  } finally {
    await client.close();
  }
} else {
  const api = new ApiClient({
    baseUrl: process.env.TIGERDRAW_API_BASE,
    retries: 0,
  });
  await api.get("/api/building_rooms", { building: "Blair" }, buildingSchema);
  await api.get(
    "/room_images",
    { building: "Blair", room_no: "B41" },
    imagesSchema,
  );
  const reviews = await api.get(
    "/get_reviews",
    { building_name: "BLAIR", room_no: "B41" },
    z.string(),
  );
  const parsed = parseReviews(reviews.data);
  console.log(
    `Public API schemas verified; BLAIR B41 has ${parsed.parsed_count} parsed reviews. No fixed count asserted.`,
  );
}
