/**
 * riff web tools for pi.
 *
 * pi has no built-in web search or fetch, so these two tools are the agent's
 * only way to the web. Each call runs the `riff` command (on PATH, configured
 * through ~/.riff/config.json) and returns its stdout; riff merges every
 * configured provider itself, so the tool stays a thin adapter.
 *
 * The session id comes from pi's session manager, so budgets and provider
 * cooldowns are counted per pi session like in every other host.
 */
import { Type } from "typebox";
import type {
  ExecResult,
  ExtensionAPI,
  ExtensionToolContext,
} from "@earendil-works/pi-coding-agent";

/** Runs riff and turns a failure into the text the model should see. */
async function run(
  pi: ExtensionAPI,
  ctx: ExtensionToolContext,
  args: string[],
): Promise<{ content: { type: "text"; text: string }[]; details: Record<string, never>; isError: boolean }> {
  const session = ctx.sessionManager.getSessionId();
  let result: ExecResult;
  try {
    result = await pi.exec("riff", [...args, "--session", session, "--agent", "pi"], {
      timeout: 120_000,
      signal: undefined,
    });
  } catch (error) {
    return {
      content: [{ type: "text", text: `riff could not be started (${String(error)}). Is it on PATH?` }],
      details: {},
      isError: true,
    };
  }
  if (result.code === 0) {
    return { content: [{ type: "text", text: result.stdout }], details: {}, isError: false };
  }
  const reason = result.stderr.trim() || (result.killed ? "timed out" : `exit code ${result.code}`);
  const hint =
    result.code === 3
      ? " Tell the user to run `riff init` and add provider keys, or `riff web doctor`."
      : "";
  return {
    content: [{ type: "text", text: `riff web failed: ${reason}${hint}` }],
    details: {},
    isError: true,
  };
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "web_search",
    label: "Web search",
    description:
      "Search the web through riff, which asks every configured provider and merges the results. " +
      "Results are leads, not sources: fetch a page before quoting it.",
    parameters: Type.Object({
      query: Type.String({ description: "The search query" }),
      allowed_domains: Type.Optional(
        Type.Array(Type.String(), { description: "Only results from these domains" }),
      ),
      blocked_domains: Type.Optional(
        Type.Array(Type.String(), { description: "Never results from these domains" }),
      ),
      max_results: Type.Optional(Type.Number({ description: "How many results, 1-20 (default 8)" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const args = ["web", "search"];
      for (const domain of params.allowed_domains ?? []) args.push("--allow-domain", domain);
      for (const domain of params.blocked_domains ?? []) args.push("--block-domain", domain);
      if (typeof params.max_results === "number") {
        args.push("--limit", String(Math.trunc(params.max_results)));
      }
      // `--` last, so a query that starts with `-` stays a query.
      args.push("--", params.query);
      return run(pi, ctx, args);
    },
  });

  pi.registerTool({
    name: "web_fetch",
    label: "Read a web page",
    description:
      "Read a page's original text through riff, one segment at a time. When the output ends " +
      "with a `riff web fetch … --range N-` command, run that instead of fetching the page again.",
    parameters: Type.Object({
      url: Type.String({ description: "The page URL" }),
      query: Type.Optional(Type.String({ description: "What you are looking for on the page" })),
      range: Type.Optional(
        Type.String({ description: "chars:START-END, START-END or #Heading; omit for the start" }),
      ),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const args = ["web", "fetch", params.url];
      if (params.range) args.push("--range", params.range);
      if (params.query) args.push("--query", params.query);
      return run(pi, ctx, args);
    },
  });
}
