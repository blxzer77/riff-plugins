export interface Replica {
  host: string;
  port: number;
}

export interface Config {
  service: string;
  port: number;
  logLevel: "debug" | "info" | "warn" | "error";
  db: {
    host: string;
    port: number;
    replicas: Replica[];
  };
}

/** Parse the text of config.json. */
export function parseConfig(text: string): Config {
  return JSON.parse(text) as Config;
}
