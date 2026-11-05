import { mkdir, writeFile } from "node:fs/promises";
import { z } from "zod";
import { parseDocument, DomUtils } from "htmlparser2";
import { ApiClient, buildingSchema, imagesSchema } from "../src/data/client";
import { parseReviews } from "../src/data/reviews";

// Preserve every review for count regressions, but retain only safe plain-text
// content/date/rating. No reviewer identifiers, scripts, forms, or HTML attributes.
export function sanitizeReviewFixture(html: string): string {
  const doc = parseDocument(html);
  const hasClass = (n: { attribs?: Record<string, string> }, name: string) =>
    (n.attribs?.class ?? "").split(/\s+/).includes(name);
  const items = DomUtils.findAll(
    (n) => hasClass(n, "review-item"),
    doc.children,
  );
  if (!items.length) {
    parseReviews(html);
    return '<div class="no-reviews">There are currently no reviews.</div>';
  }
  const escape = (text: string) =>
    text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  return items
    .map((item) => {
      const outer = DomUtils.getOuterHTML(item);
      const review = parseReviews(outer).reviews[0];
      return `<div class="review-item"><span class="review-date">${escape(review.date ?? "")}</span><div class="review-rating">${review.rating} / 5</div><div class="review-content">${escape(review.untrusted_text)}</div></div>`;
    })
    .join("\n");
}

if (import.meta.main) {
  const api = new ApiClient({
    baseUrl: process.env.TIGERDRAW_API_BASE,
    retries: 0,
  });
  // Capture related samples together. Do not write a partial refresh on failure.
  const rooms = await api.get(
    "/api/building_rooms",
    { building: "Blair" },
    buildingSchema,
  );
  const images = await api.get(
    "/room_images",
    { building: "Blair", room_no: "B41" },
    imagesSchema,
  );
  const uppercase = await api.get(
    "/get_reviews",
    { building_name: "BLAIR", room_no: "B41" },
    z.string(),
  );
  const titlecase = await api.get(
    "/get_reviews",
    { building_name: "Blair", room_no: "B41" },
    z.string(),
  );
  const upperParsed = parseReviews(uppercase.data);
  const titleParsed = parseReviews(titlecase.data);
  const output = new URL("../tests/fixtures/live/", import.meta.url);
  await mkdir(output, { recursive: true });
  const files: Record<string, unknown> = {
    "building-Blair.json": rooms.data,
    "images-Blair-B41.json": images.data,
    "manifest.json": {
      captured_at: new Date().toISOString(),
      synthetic: false,
      room: "Blair B41",
      sources: [
        rooms.source,
        images.source,
        uppercase.source,
        titlecase.source,
      ],
      review_counts: {
        uppercase: upperParsed.parsed_count,
        titlecase: titleParsed.parsed_count,
      },
      review_text_truncated_to: 1000,
      note: "Refreshed after the November 4 cleanup. Counts are captures, not immutable production assertions.",
    },
  };
  for (const [name, data] of Object.entries(files))
    await writeFile(
      new URL(name, output),
      JSON.stringify(data, null, 2) + "\n",
    );
  await writeFile(
    new URL("reviews-BLAIR-B41.html", output),
    sanitizeReviewFixture(uppercase.data),
  );
  await writeFile(
    new URL("reviews-Blair-B41.html", output),
    sanitizeReviewFixture(titlecase.data),
  );
  console.log(
    `Refreshed Blair B41 samples. Review counts: BLAIR=${upperParsed.parsed_count}, Blair=${titleParsed.parsed_count}. Review files before committing them.`,
  );
}
