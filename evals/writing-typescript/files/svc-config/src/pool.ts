import type { Config } from "./config.ts";

/** Every database endpoint, primary first, as host:port. */
export function readHosts(config: Config): string[] {
  return [config.db, ...config.db.replicas].map((r) => `${r.host}:${r.port}`);
}
