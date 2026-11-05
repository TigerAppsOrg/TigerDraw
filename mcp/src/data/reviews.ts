import { parseDocument, DomUtils } from "htmlparser2";
import type { AnyNode, Element } from "domhandler";
import { DataError } from "./types";

function hasClass(node: AnyNode, name: string): node is Element {
  return (
    "attribs" in node && (node.attribs.class ?? "").split(/\s+/).includes(name)
  );
}
function text(node: AnyNode): string {
  if ("name" in node && ["script", "style", "form"].includes(node.name))
    return "";
  if (node.type === "text") return node.data;
  return "children" in node
    ? node.children.map(text).join(" ").replace(/\s+/g, " ").trim()
    : "";
}
export function parseReviews(html: string) {
  const document = parseDocument(html, { decodeEntities: true });
  const items = DomUtils.findAll(
    (n) => hasClass(n, "review-item"),
    document.children,
  );
  const empty =
    DomUtils.findAll((n) => hasClass(n, "no-reviews"), document.children)
      .length > 0;
  if (!items.length && !empty)
    throw new DataError(
      "UPSTREAM_ERROR",
      "Review HTML did not contain the expected review structure.",
    );
  const reviews = items.slice(0, 10).map((item) => {
    const content = DomUtils.findOne(
      (n) => hasClass(n, "review-content"),
      item.children,
    );
    const date = DomUtils.findOne(
      (n) => hasClass(n, "review-date"),
      item.children,
    );
    const rating = DomUtils.findOne(
      (n) => hasClass(n, "review-rating"),
      item.children,
    );
    if (!content || !rating)
      throw new DataError(
        "UPSTREAM_ERROR",
        "A review is missing expected fields.",
      );
    const value = Number(
      text(rating).match(/^\s*([0-5](?:\.\d+)?)\s*\/\s*5\s*$/)?.[1],
    );
    if (!Number.isFinite(value) || value > 5)
      throw new DataError("UPSTREAM_ERROR", "A review has an invalid rating.");
    const body = text(content);
    return {
      date: date ? text(date).slice(0, 100) : null,
      rating: value,
      untrusted_text: body.slice(0, 1000),
      truncated: body.length > 1000,
    };
  });
  return {
    reviews,
    returned_count: reviews.length,
    parsed_count: items.length,
    truncated: items.length > 10 || reviews.some((r) => r.truncated),
    trust: "untrusted_student_content",
  };
}
