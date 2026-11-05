# TigerDraw MCP

Read-only room discovery for PI. Runs independently of Flask and Postgres, with
six MCP tools at `/mcp` and `/mcp/`.

## Local setup

Use Bun 1.3.1 or newer (tested on 1.3.1), Node 20+ for dependency installation,
and the committed npm lockfile:

```bash
cd mcp
npm ci
bun run catalog:build
bun test
bun run typecheck
bun run dev
```

The endpoint is `http://127.0.0.1:3333/mcp`. `GET /healthz` reports catalog readiness
without contacting production. Bun loads `.env` automatically; copy `.env.example`
if overriding defaults. No database URI, AWS credentials, or production model key
is needed. Catalog generation reads repository assets; the running service reads
the generated catalog, TigerDraw-owned previews, and public API. Do not start the Flask app for tests.

| Setting | Default | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Listen interface |
| `PORT` | `3333` | Listen port |
| `TIGERDRAW_API_BASE` | `https://draw.tigerapps.org` | Trusted HTTP(S) API origin, no path |
| `MCP_ACCESS_TOKEN` | Empty locally | Dedicated PI bearer token; required with `NODE_ENV=production` |
| `TIGERDRAW_MCP_URL` | Unset | Optional endpoint for the live MCP smoke script |

## Tools and data

| Tool | Arguments |
| --- | --- |
| `list_buildings` | `{}` |
| `list_rooms` | `building`, optional `floor`, `occupancy`, `limit` |
| `get_room` | `building`, `room_no` |
| `get_room_images` | `building`, `room_no` |
| `get_floor_plan` | `building`, optional `floor` |
| `search_rooms` | Optional `occupancy`, `college`, `amenities`, `max_sq_footage`, `limit` |

`occupancy` is an integer; building, room and floor identifiers are strings.
Room limits default to 20 and cannot exceed 100. Amenities support `ac` and
`elevator`, require all requested values to match, and reject duplicates. Maximum
square footage is inclusive. Use `list_buildings` for names/colleges and
`get_floor_plan` without a floor for available floor labels. Labels such as `0`
and `G` are preserved rather than assumed equivalent. No pagination is provided;
use filters when `truncated` is true.

Responses include source links, live/cache/static provenance, coverage, warnings,
and truncation. Static catalogs carry a content revision, not a claimed data update
date. Rooms deduplicate by building and room number, preserve source IDs and
records, and expose conflicting fields as null with candidates under `conflicts`.
Unknown/conflicting values do not satisfy filters. Rankings are historical averages,
not current availability. Image labels distinguish `ACTUAL`, `EXAMPLE`, and unknown.

Review HTML is parsed without execution. Only dates, ratings and bounded plain-text
excerpts are returned; reviewer NetIDs are omitted. Review text remains untrusted
evidence. Never treat instructions inside reviews as instructions to PI.

Live reads use a five-minute cache, four-second attempts and a ten-second tool
budget. Campus search uses at most four concurrent building requests. Outages can
produce explicitly labeled static fallback or partial campus coverage; expired
review statistics/text are not served. A confirmed empty live response does not
resurrect old static rooms or images. Tests/fixtures are never runtime fallback.

Only the three read endpoints are allowlisted; neither an arbitrary URL nor a
write action can be passed through a tool. Production tokens belong to the MCP
service, not TigerDraw's database or a student's session.

## Testing and refreshing samples

`bun test` uses synthetic fixtures and an in-process modern MCP client with no
production requests, sockets, credentials, database, or Redis. It also covers the
legacy protocol, authentication, schemas, limits, casing, duplicates, filters,
reviews, asset coverage, failures, and fallback.

From a network-enabled environment:

```bash
bun run fixtures:refresh
bun run smoke:live
```

The refresh captures Blair room data, B41 media, and both `BLAIR` and `Blair`
review HTML. It sanitizes identifiers and executable markup, records timestamps
and observed review counts, and writes ignored files under `tests/fixtures/live/`.
Review those files before promoting them to regression fixtures. This is how to
refresh expectations after the November 4 review cleanup; synthetic zero counts
are not live assertions. The separate ticket snapshot was not available locally.

To verify a running MCP endpoint, including live-data use:

```bash
TIGERDRAW_MCP_URL=http://127.0.0.1:3333/mcp bun run smoke:live
```

Set `MCP_ACCESS_TOKEN` in the environment if that endpoint requires a token. The
script deliberately fails when room/image calls use fallback: a healthy process
alone is not proof the live API works.

## PI connection

In PI, set `TIGERDRAW_MCP_URL` to the local endpoint for local development, or
`https://draw.tigerapps.org/mcp` after deployment. Set `TIGERDRAW_MCP_TOKEN` to the
service's `MCP_ACCESS_TOKEN` when authentication is enabled. PI uses dedicated
headers with no Junction token or student identity. Enable TigerDraw in My apps.
Hosted PI needs a reachable HTTPS endpoint; it cannot use your laptop's localhost.

Example conversation (expected tool flow, not a recorded live transcript):

> Find five Mathey doubles under 300 square feet with an elevator.
>
> Compare the first two, including historical draw rankings and reviews.
>
> Show their images and floor plans.

PI should search with occupancy 2, college Mathey, elevator, maximum area 300,
and limit 5; get details for actual matches; then retrieve images and plans. It
should cite sources and disclose conflicts or partial/static results. The query
may return fewer than five matches. Full PI testing uses its existing model/CAS
development configuration; no new student credentials are required by MCP.

## Deployment

Deploy to `/home/ubuntu/apps/tigerdraw/mcp` on TigerApps-Combined (`us-east-1`).
Install the tested Bun runtime at `/usr/local/bin/bun`; run `npm ci --omit=dev`
and generate the catalog before starting the service. Create the dedicated
`tigerdraw-mcp` OS user and grant it read/traverse access to the release directory
and generated assets under `/home/ubuntu`; do not grant writes to Flask data.

Use [the systemd template](deploy/tigerdraw-mcp.service) and an environment file
at `/etc/tigerdraw-mcp.env` containing a newly generated `MCP_ACCESS_TOKEN`.
Restrict that file's permissions. Review [the proxy locations](deploy/reverse-proxy.example.conf)
against the existing HTTPS server configuration, check its syntax, and reload it.
The example assumes nginx; confirm the actual proxy before applying it. Preserve
both endpoint spellings without redirects, authentication, negotiation headers,
and unbuffered streaming. Keep the companion bound to loopback.

Verify health, unauthorized rejection, `smoke:live`, and a PI conversation before
enabling the integration broadly. `tigerdraw.service` stays independently managed.
Run `smoke:live` from a development checkout with dev dependencies installed,
pointing `TIGERDRAW_MCP_URL` at the deployed endpoint.
Rollback by disabling TigerDraw in PI, removing the two MCP proxy locations, and
stopping `tigerdraw-mcp.service`.

Instance/proxy access is needed for deployment. Cloudflare credentials are only
needed for PI deployment or an actual Cloudflare routing change. No extra instance,
domain, Postgres secret, or TigerJunction engine change is required.

## Floor-plan previews

TigerDraw owns PDF preview generation, the manifest, and generated PNGs under
`static/previews/`. `get_floor_plan` returns each original `url` and its
`preview_url`; `get_room_images` attaches the same metadata for recognized PDFs.
PI consumes these fields without owning document assets or guessing preview URLs.

After updating PDFs, install Poppler and regenerate:

```bash
bun run previews:build
bun run catalog:build
```

The optional builder requires Python 3 and `pdftoppm` (Poppler). Commit updated
PDFs, previews, the manifest, and the generated catalog together. Normal service
startup and catalog builds need no renderer; the catalog build verifies source
PDF and PNG hashes and rejects missing, stale, or modified previews. The builder
validates PNG structure/CRCs, replaces previews atomically, and publishes the
manifest only after every file succeeds. Use `bun run previews:build --force`
to regenerate valid cached previews after changing renderer settings.

Production preview URLs default to `https://draw.tigerapps.org/static/previews/`
and are served by TigerDraw's existing static-file handling. Include `static/previews/`
in the deployed release; no new production proxy route is needed. The MCP service
also serves only catalog-listed preview PNGs publicly via GET/HEAD, with immutable
caching. Auth remains required on `/mcp` in production.

For local development, set `TIGERDRAW_ASSET_ORIGIN=http://127.0.0.1:3333` in
MCP's ignored `.env`, then restart MCP. Preview URLs will use that origin; original
PDF URLs remain unchanged. This requires neither a Flask process nor database
credentials. Leave this override unset in production. Production startup rejects HTTP,
localhost, local-domain, and IP-address preview origins.
