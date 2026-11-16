export type ActivityEvent =
  | { kind: "created"; id: string; title: string }
  | { kind: "deleted"; id: string; title: string }
  | { kind: "commented"; id: string; author: string; text: string };
