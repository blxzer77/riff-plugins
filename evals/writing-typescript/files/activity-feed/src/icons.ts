import type { ActivityEvent } from "./events.ts";

/** Icon shown next to a feed line. */
export function iconFor(event: ActivityEvent): string {
  switch (event.kind) {
    case "created":
      return "➕";
    case "deleted":
      return "🗑️";
    case "commented":
      return "💬";
    default:
      return "•";
  }
}
