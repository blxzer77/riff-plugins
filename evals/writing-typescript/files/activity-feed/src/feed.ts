import type { ActivityEvent } from "./events.ts";

/** One line of the activity feed. */
export function describe(event: ActivityEvent): string {
  switch (event.kind) {
    case "created":
      return `Created "${event.title}"`;
    case "deleted":
      return `Deleted "${event.title}"`;
    case "commented":
      return `${event.author} commented: ${event.text}`;
    default:
      return "Unknown activity";
  }
}
