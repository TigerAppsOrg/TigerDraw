import { z } from "zod";
import { DataError, type Source } from "./types";

const roomSchema = z.object({
  room_id: z.union([z.string(), z.number()]),
  room_no: z.string().trim().min(1).max(128),
  occupancy: z.union([z.string(), z.number()]).nullable().optional(),
  sq_footage: z.union([z.number(), z.string()]).nullable().optional(),
  floor: z.union([z.string(), z.number()]).nullable().optional(),
  elevator: z
    .union([z.string(), z.boolean(), z.number()])
    .nullable()
    .optional(),
  bathroom: z.string().nullable().optional(),
  ac: z.union([z.string(), z.boolean(), z.number()]).nullable().optional(),
  draw_rank: z.union([z.string(), z.number()]).nullable().optional(),
  num_reviews: z.number().int().nonnegative().nullable().optional(),
  avg_rating: z.number().min(0).max(5).nullable().optional(),
  has_360: z.boolean().nullable().optional(),
  res_college: z.string().nullable().optional(),
});
export const buildingSchema = z.object({
  building: z.string(),
  floors: z.record(z.string(), z.array(roomSchema)),
});
export const imagesSchema = z.object({
  floor_plan: z.string().nullable(),
  room_plan: z.string().nullable(),
  thumbnail: z.string().nullable(),
  views_360: z.array(
    z.object({ url: z.string(), mediaType: z.string().nullable().optional() }),
  ),
});
export type Fetcher = (
  input: string | URL | Request,
  init?: RequestInit,
) => Promise<Response>;
type Cached = { text: string; source: Source; expires: number };
export type ClientOptions = {
  baseUrl?: string;
  fetcher?: Fetcher;
  now?: () => number;
  timeoutMs?: number;
  ttlMs?: number;
  negativeTtlMs?: number;
  maxBytes?: number;
  retries?: number;
};
const routes = new Set(["/api/building_rooms", "/room_images", "/get_reviews"]);

export class ApiClient {
  readonly baseUrl: string;
  private cache = new Map<string, Cached>();
  private inFlight = new Map<string, Promise<Cached>>();
  private options: Required<Omit<ClientOptions, "baseUrl">>;
  constructor(options: ClientOptions = {}) {
    const base = new URL(options.baseUrl ?? "https://draw.tigerapps.org");
    if (
      !["https:", "http:"].includes(base.protocol) ||
      base.username ||
      base.password ||
      base.pathname !== "/" ||
      base.search ||
      base.hash
    )
      throw new Error(
        "TIGERDRAW_API_BASE must be an HTTP(S) origin without credentials or a path.",
      );
    this.baseUrl = base.origin;
    this.options = {
      fetcher: options.fetcher ?? fetch,
      now: options.now ?? Date.now,
      timeoutMs: options.timeoutMs ?? 4000,
      ttlMs: options.ttlMs ?? 300000,
      negativeTtlMs: options.negativeTtlMs ?? 30000,
      maxBytes: options.maxBytes ?? 2 * 1024 * 1024,
      retries: options.retries ?? 1,
    };
  }
  url(route: string, query: Record<string, string>): string {
    if (!routes.has(route))
      throw new Error("Upstream route is not read-only allowlisted");
    const url = new URL(route, this.baseUrl);
    url.search = new URLSearchParams(query).toString();
    return url.href;
  }
  async get<T>(
    route: string,
    query: Record<string, string>,
    schema: z.ZodType<T>,
    deadline = this.options.now() + 10000,
  ): Promise<{ data: T; source: Source }> {
    const url = this.url(route, query);
    let cached = this.cache.get(url);
    const hit = cached && cached.expires > this.options.now();
    if (!hit) {
      let pending = this.inFlight.get(url);
      if (!pending) {
        pending = this.request(url, route === "/get_reviews", deadline);
        this.inFlight.set(url, pending);
        pending.finally(() => this.inFlight.delete(url)).catch(() => {});
      }
      const remaining = deadline - this.options.now();
      if (remaining <= 0)
        throw new DataError(
          "UPSTREAM_ERROR",
          "TigerDraw tool deadline was reached.",
          true,
          url,
        );
      let waitTimer: ReturnType<typeof setTimeout> | undefined;
      try {
        cached = await Promise.race([
          pending,
          new Promise<never>((_, reject) => {
            waitTimer = setTimeout(
              () =>
                reject(
                  new DataError(
                    "UPSTREAM_ERROR",
                    "TigerDraw tool deadline was reached.",
                    true,
                    url,
                  ),
                ),
              remaining,
            );
          }),
        ]);
      } finally {
        clearTimeout(waitTimer);
      }
    }
    try {
      const data = schema.parse(
        route === "/get_reviews" ? cached!.text : JSON.parse(cached!.text),
      );
      // Cache only validated payloads; failures must never become an authoritative absence.
      const empty =
        route === "/api/building_rooms" &&
        Object.values(
          (data as { floors: Record<string, unknown[]> }).floors,
        ).every((rows) => rows.length === 0);
      if (!hit) {
        cached!.expires =
          this.options.now() +
          (empty ? this.options.negativeTtlMs : this.options.ttlMs);
        // Bound cache cardinality and discard oldest entries.
        if (this.cache.size >= 512)
          this.cache.delete(this.cache.keys().next().value!);
        this.cache.set(url, cached!);
      }
      return {
        data,
        source: { ...cached!.source, source_kind: hit ? "cache" : "live" },
      };
    } catch {
      this.cache.delete(url);
      throw new DataError(
        "UPSTREAM_ERROR",
        "TigerDraw returned an unexpected response structure.",
        false,
        url,
      );
    }
  }
  invalidate(route: string, query: Record<string, string>) {
    this.cache.delete(this.url(route, query));
  }
  private async request(
    url: string,
    html: boolean,
    deadline: number,
  ): Promise<Cached> {
    let last: unknown;
    for (let attempt = 0; attempt <= this.options.retries; attempt++) {
      const remaining = deadline - this.options.now();
      if (remaining <= 0) break;
      const controller = new AbortController();
      const timer = setTimeout(
        () => controller.abort(),
        Math.min(remaining, this.options.timeoutMs),
      );
      try {
        const response = await this.options.fetcher(url, {
          method: "GET",
          redirect: "error",
          signal: controller.signal,
          headers: { accept: html ? "text/html" : "application/json" },
        });
        if (!response.ok) {
          const retryable = response.status === 429 || response.status >= 500;
          await response.body?.cancel();
          if (!retryable)
            throw new DataError(
              "UPSTREAM_ERROR",
              `TigerDraw returned HTTP ${response.status}.`,
              false,
              url,
            );
          last = new DataError(
            "UPSTREAM_ERROR",
            `TigerDraw returned HTTP ${response.status}.`,
            true,
            url,
          );
          const retryAfter = response.headers.get("retry-after");
          if (retryAfter && attempt < this.options.retries) {
            const seconds = Number(retryAfter);
            const delay = Number.isFinite(seconds)
              ? seconds * 1000
              : Date.parse(retryAfter) - this.options.now();
            if (
              !Number.isFinite(delay) ||
              delay < 0 ||
              delay >= deadline - this.options.now()
            )
              break;
            await new Promise((resolve) => setTimeout(resolve, delay));
          }
          continue;
        }
        const contentType = response.headers.get("content-type") ?? "";
        if (
          !(html
            ? contentType.includes("text/html")
            : contentType.includes("application/json"))
        ) {
          await response.body?.cancel();
          throw new DataError(
            "UPSTREAM_ERROR",
            "TigerDraw returned an unexpected content type.",
            false,
            url,
          );
        }
        if (
          Number(response.headers.get("content-length")) > this.options.maxBytes
        ) {
          await response.body?.cancel();
          throw new DataError(
            "UPSTREAM_ERROR",
            "TigerDraw response exceeded the size limit.",
            false,
            url,
          );
        }
        const reader = response.body?.getReader();
        let size = 0;
        const chunks: Uint8Array[] = [];
        if (reader) {
          while (true) {
            const next = await reader.read();
            if (next.done) break;
            size += next.value.byteLength;
            if (size > this.options.maxBytes) {
              await reader.cancel();
              throw new DataError(
                "UPSTREAM_ERROR",
                "TigerDraw response exceeded the size limit.",
                false,
                url,
              );
            }
            chunks.push(next.value);
          }
        }
        return {
          text: Buffer.concat(chunks).toString("utf8"),
          source: {
            source: url,
            source_kind: "live",
            retrieved_at: new Date(this.options.now()).toISOString(),
          },
          expires: 0,
        };
      } catch (error) {
        if (error instanceof DataError && !error.retryable) throw error;
        last = error;
      } finally {
        clearTimeout(timer);
      }
    }
    if (last instanceof DataError) throw last;
    throw new DataError(
      "UPSTREAM_ERROR",
      "TigerDraw is unavailable or timed out. Try again later.",
      true,
      url,
    );
  }
}
