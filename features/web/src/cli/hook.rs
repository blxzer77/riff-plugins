//! `riff hook <event> --agent <name>`: the host-agent hooks (design 7.1).
//!
//! `pretooluse` reads the host's PreToolUse JSON on stdin. A call to the
//! host's built-in web search or fetch is denied with the equivalent
//! `riff web` command in the reason, so the model runs that instead. Anything
//! else, or a web call riff could not serve right now, is let through: riff
//! must never leave the agent with no web access at all.
//!
//! The check reads only `$RIFF_HOME` (config, key files, state); it makes no
//! network request, so the hook stays in the millisecond range.

use std::io::Read;

use serde_json::{Value, json};

/// The agents whose PreToolUse format riff speaks.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Agent {
    ClaudeCode,
    Antigravity,
}

impl Agent {
    pub fn parse(name: &str) -> Option<Self> {
        match name {
            "claude-code" => Some(Self::ClaudeCode),
            "antigravity" => Some(Self::Antigravity),
            _ => None,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::ClaudeCode => "claude-code",
            Self::Antigravity => "antigravity",
        }
    }
}

/// A built-in web call, in riff terms.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum WebCall {
    Search {
        query: String,
        allowed: Vec<String>,
        blocked: Vec<String>,
    },
    Fetch {
        url: String,
        query: Option<String>,
        offset: Option<u64>,
    },
}

/// Recognises the host's built-in web tools and maps their arguments.
/// `None` for every other tool, and for a web call whose arguments riff
/// cannot express (let through rather than guess).
pub fn web_call(agent: Agent, input: &Value) -> Option<WebCall> {
    let strings = |value: Option<&Value>| -> Vec<String> {
        value
            .and_then(Value::as_array)
            .map(|items| {
                items
                    .iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect()
            })
            .unwrap_or_default()
    };
    let text = |value: Option<&Value>| {
        value
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(str::to_string)
    };
    match agent {
        Agent::ClaudeCode => {
            let args = input.get("tool_input")?;
            match input.get("tool_name")?.as_str()? {
                "WebSearch" => Some(WebCall::Search {
                    query: text(args.get("query"))?,
                    allowed: strings(args.get("allowed_domains")),
                    blocked: strings(args.get("blocked_domains")),
                }),
                "WebFetch" => Some(WebCall::Fetch {
                    url: text(args.get("url"))?,
                    query: text(args.get("prompt")),
                    offset: args
                        .get("offset")
                        .and_then(Value::as_u64)
                        .filter(|offset| *offset > 0),
                }),
                _ => None,
            }
        }
        Agent::Antigravity => {
            let call = input.get("toolCall")?;
            let args = call.get("args")?;
            match call.get("name")?.as_str()? {
                "search_web" => Some(WebCall::Search {
                    query: text(args.get("query"))?,
                    allowed: text(args.get("domain")).into_iter().collect(),
                    blocked: Vec::new(),
                }),
                "read_url_content" => Some(WebCall::Fetch {
                    url: text(args.get("Url"))?,
                    query: None,
                    offset: None,
                }),
                _ => None,
            }
        }
    }
}

/// The host's session id, passed on so the suggested command spends the same
/// budget as every other riff call in this conversation.
pub fn session_id(agent: Agent, input: &Value) -> Option<String> {
    let key = match agent {
        Agent::ClaudeCode => "session_id",
        Agent::Antigravity => "conversationId",
    };
    input
        .get(key)
        .and_then(Value::as_str)
        .filter(|id| !id.trim().is_empty())
        .map(str::to_string)
}

/// The shell command equivalent to `call`, every value quoted for `bash -c`.
pub fn riff_command(call: &WebCall, agent: Agent, session: Option<&str>) -> String {
    let quote = crate::runtime::shell_quote;
    let mut words = vec!["riff".to_string(), "web".to_string()];
    match call {
        WebCall::Search {
            query,
            allowed,
            blocked,
        } => {
            words.push("search".to_string());
            for domain in allowed {
                words.push(format!("--allow-domain {}", quote(domain)));
            }
            for domain in blocked {
                words.push(format!("--block-domain {}", quote(domain)));
            }
            if let Some(session) = session {
                words.push(format!("--session {}", quote(session)));
            }
            words.push(format!("--agent {}", agent.name()));
            // Last, after `--`, so a query starting with `-` is not an option.
            words.push("--".to_string());
            words.push(quote(query));
        }
        WebCall::Fetch { url, query, offset } => {
            words.push("fetch".to_string());
            words.push(quote(url));
            if let Some(offset) = offset {
                words.push(format!("--range {offset}-"));
            }
            if let Some(query) = query {
                words.push(format!("--query {}", quote(query)));
            }
            if let Some(session) = session {
                words.push(format!("--session {}", quote(session)));
            }
            words.push(format!("--agent {}", agent.name()));
        }
    }
    words.join(" ")
}

/// Why riff lets a built-in web call through instead of taking it over.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum PassReason {
    Disabled,
    NoConfig(String),
    NoSearchProvider,
    SearchBudgetSpent,
    NoProviderAvailable,
    FetchBudgetSpent,
}

impl PassReason {
    pub fn note(&self, tool: &str) -> String {
        let why = match self {
            Self::Disabled => return String::new(),
            Self::NoConfig(error) => format!("riff is not configured ({error})"),
            Self::NoSearchProvider => "riff has no search provider with a key".to_string(),
            Self::SearchBudgetSpent => "this session's riff search budget is spent".to_string(),
            Self::NoProviderAvailable => {
                "every riff search provider is cooling down or out of budget".to_string()
            }
            Self::FetchBudgetSpent => "this session's riff fetch budget is spent".to_string(),
        };
        format!("riff: {why}; using the built-in {tool}")
    }
}

/// Decides from local state only whether riff can serve `call` right now.
/// Search falls back to the built-in tool when riff could not answer; fetch
/// only when riff's own budget refuses it (fetching does not depend on a
/// provider, so a cooling provider is no reason to give it up).
pub fn availability(call: &WebCall, session: Option<&str>) -> Result<(), PassReason> {
    let config =
        crate::home::load_config(None).map_err(|error| PassReason::NoConfig(error.to_string()))?;
    let web = config.web.clone().unwrap_or_default();
    if !web.intercept_builtin() {
        return Err(PassReason::Disabled);
    }
    let cwd = std::env::current_dir().unwrap_or_default();
    let id = crate::state::SessionId::resolve(session, &cwd, std::time::SystemTime::now());
    let state = crate::state::peek(&id);
    let budget = &state.session.budget;
    match call {
        WebCall::Search { .. } => {
            let usable = crate::web::usable_search_providers(&web);
            if usable.is_empty() {
                return Err(PassReason::NoSearchProvider);
            }
            if budget.search_calls >= web.search().max_per_session() {
                return Err(PassReason::SearchBudgetSpent);
            }
            let now = crate::state::unix_now();
            let down = |until: Option<u64>| until.is_some_and(|until| until > now);
            let ready = usable.iter().any(|name| {
                let spent = web
                    .provider(name)
                    .max_calls_per_session
                    .is_some_and(|limit| {
                        budget.provider_calls.get(*name).copied().unwrap_or(0) >= limit
                    });
                let cooling = state.health.providers.iter().any(|entry| {
                    entry.provider == *name
                        && entry.capability == "search"
                        && down(entry.down_until)
                });
                let service_down = state
                    .health
                    .services
                    .iter()
                    .any(|entry| entry.kind == *name && down(entry.down_until));
                !spent && !cooling && !service_down
            });
            if !ready {
                return Err(PassReason::NoProviderAvailable);
            }
        }
        WebCall::Fetch { .. } => {
            let fetch = web.fetch();
            if budget.fetch_calls >= fetch.max_per_session()
                || budget.fetch_bytes >= fetch.max_bytes_per_session()
            {
                return Err(PassReason::FetchBudgetSpent);
            }
        }
    }
    Ok(())
}

/// The hook's stdout for one PreToolUse input. `None` = print nothing, which
/// Claude Code reads as "no opinion".
pub fn pretooluse(agent: Agent, input: &Value) -> Option<Value> {
    let Some(call) = web_call(agent, input) else {
        return allow(agent, None);
    };
    let session = session_id(agent, input);
    let tool = match (agent, &call) {
        (Agent::ClaudeCode, WebCall::Search { .. }) => "WebSearch",
        (Agent::ClaudeCode, WebCall::Fetch { .. }) => "WebFetch",
        (Agent::Antigravity, WebCall::Search { .. }) => "search_web",
        (Agent::Antigravity, WebCall::Fetch { .. }) => "read_url_content",
    };
    match availability(&call, session.as_deref()) {
        Ok(()) => {
            let command = riff_command(&call, agent, session.as_deref());
            let reason = format!(
                "Use riff for web access instead of the built-in {tool}. Run this shell command, \
                 which does the same thing: {command}"
            );
            Some(deny(agent, &reason))
        }
        Err(PassReason::Disabled) => allow(agent, None),
        Err(pass) => allow(agent, Some(&pass.note(tool))),
    }
}

fn deny(agent: Agent, reason: &str) -> Value {
    match agent {
        Agent::ClaudeCode => json!({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }),
        Agent::Antigravity => json!({"decision": "deny", "reason": reason}),
    }
}

/// Claude Code: no output means "no opinion"; a note goes in
/// `additionalContext` without changing the decision. Antigravity requires a
/// `decision`, and "allow" delegates to the next hook or the default policy.
fn allow(agent: Agent, note: Option<&str>) -> Option<Value> {
    match agent {
        Agent::ClaudeCode => note.map(|note| {
            json!({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": note,
                }
            })
        }),
        Agent::Antigravity => Some(match note {
            Some(note) => json!({"decision": "allow", "reason": note}),
            None => json!({"decision": "allow"}),
        }),
    }
}

pub const HELP: &str = "\
Usage: riff hook pretooluse --agent <claude-code|antigravity>

Reads the host's PreToolUse hook input on stdin and, for a call to the host's
built-in web search or fetch, answers with a denial that names the equivalent
`riff web` command. Other tools, and web calls riff cannot serve right now,
are let through. Set web.interceptBuiltin to false to turn it off.
";

/// `riff hook …`: `args` are the words after `hook`. Never blocks the host's
/// tool call because of riff itself: malformed input is let through with exit
/// 0 and a note on stderr.
pub fn run(args: &[String]) -> i32 {
    let mut agent = None;
    let mut event = None;
    let mut words = args.iter();
    while let Some(word) = words.next() {
        match word.as_str() {
            "-h" | "--help" => {
                print!("{HELP}");
                return 0;
            }
            "--agent" => agent = words.next().map(String::as_str).and_then(Agent::parse),
            flag if flag.starts_with("--agent=") => {
                agent = Agent::parse(&flag["--agent=".len()..]);
            }
            other if event.is_none() && !other.starts_with('-') => event = Some(other.to_string()),
            other => {
                eprintln!("riff hook: unexpected argument `{other}`\n\n{HELP}");
                return super::web::exit::USAGE;
            }
        }
    }
    let (Some(agent), Some("pretooluse")) = (agent, event.as_deref()) else {
        eprintln!("riff hook: expected `pretooluse --agent <claude-code|antigravity>`\n\n{HELP}");
        return super::web::exit::USAGE;
    };
    let mut raw = String::new();
    if std::io::stdin().read_to_string(&mut raw).is_err() {
        eprintln!("riff hook: cannot read stdin; letting the tool call through");
        return emit(allow(agent, None));
    }
    let input = match serde_json::from_str::<Value>(&raw) {
        Ok(input) => input,
        Err(error) => {
            eprintln!("riff hook: invalid hook input ({error}); letting the tool call through");
            return emit(allow(agent, None));
        }
    };
    emit(pretooluse(agent, &input))
}

fn emit(output: Option<Value>) -> i32 {
    if let Some(output) = output {
        println!("{output}");
    }
    0
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_env::{TEST_ENV_LOCK, TempHome};

    fn cc(tool: &str, input: Value) -> Value {
        json!({"session_id": "sess-1", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": input})
    }

    fn ag(tool: &str, args: Value) -> Value {
        json!({"conversationId": "conv-1", "toolCall": {"name": tool, "args": args}, "stepIdx": 3})
    }

    #[test]
    fn built_in_web_tools_map_to_riff_calls() {
        assert_eq!(
            web_call(
                Agent::ClaudeCode,
                &cc(
                    "WebSearch",
                    json!({"query": "tokio select", "allowed_domains": ["docs.rs"], "blocked_domains": ["x.com"]})
                )
            ),
            Some(WebCall::Search {
                query: "tokio select".into(),
                allowed: vec!["docs.rs".into()],
                blocked: vec!["x.com".into()],
            })
        );
        assert_eq!(
            web_call(
                Agent::ClaudeCode,
                &cc(
                    "WebFetch",
                    json!({"url": "https://e.com/a", "prompt": "find X", "offset": 1200})
                )
            ),
            Some(WebCall::Fetch {
                url: "https://e.com/a".into(),
                query: Some("find X".into()),
                offset: Some(1200),
            })
        );
        assert_eq!(
            web_call(
                Agent::Antigravity,
                &ag("search_web", json!({"query": "q", "domain": "docs.rs"}))
            ),
            Some(WebCall::Search {
                query: "q".into(),
                allowed: vec!["docs.rs".into()],
                blocked: Vec::new(),
            })
        );
        assert_eq!(
            web_call(
                Agent::Antigravity,
                &ag("read_url_content", json!({"Url": "https://e.com/"}))
            ),
            Some(WebCall::Fetch {
                url: "https://e.com/".into(),
                query: None,
                offset: None,
            })
        );
    }

    #[test]
    fn other_tools_and_unusable_arguments_are_not_web_calls() {
        assert_eq!(
            web_call(Agent::ClaudeCode, &cc("Bash", json!({"command": "ls"}))),
            None
        );
        assert_eq!(
            web_call(Agent::ClaudeCode, &cc("WebSearch", json!({"query": "  "}))),
            None
        );
        assert_eq!(
            web_call(Agent::ClaudeCode, &cc("WebFetch", json!({}))),
            None
        );
        assert_eq!(
            web_call(
                Agent::Antigravity,
                &ag("run_command", json!({"CommandLine": "ls"}))
            ),
            None
        );
        assert_eq!(web_call(Agent::ClaudeCode, &json!({"tool_name": 3})), None);
    }

    /// The suggested command must be what the model can paste: it parses back
    /// into the same riff call.
    fn reparse(command: &str) -> super::super::web::Command {
        let words = shell_words(command);
        assert_eq!(&words[..2], ["riff", "web"]);
        match super::super::web::parse(&words[2..]).unwrap() {
            super::super::web::Parsed::Run(invocation) => invocation.command,
            other => panic!("{other:?}"),
        }
    }

    /// Enough of POSIX word splitting for what `shell_quote` produces.
    fn shell_words(command: &str) -> Vec<String> {
        let mut words = Vec::new();
        let mut word = String::new();
        let mut in_word = false;
        let mut chars = command.chars();
        while let Some(c) = chars.next() {
            match c {
                '\'' => {
                    in_word = true;
                    for c in chars.by_ref() {
                        if c == '\'' {
                            break;
                        }
                        word.push(c);
                    }
                }
                '\\' => {
                    in_word = true;
                    word.extend(chars.next());
                }
                ' ' => {
                    if in_word {
                        words.push(std::mem::take(&mut word));
                        in_word = false;
                    }
                }
                c => {
                    in_word = true;
                    word.push(c);
                }
            }
        }
        if in_word {
            words.push(word);
        }
        words
    }

    #[test]
    fn the_suggested_command_parses_back_to_the_same_call() {
        let search = WebCall::Search {
            query: "-it's \"quoted\" $HOME".into(),
            allowed: vec!["docs.rs".into()],
            blocked: vec!["x.com".into()],
        };
        let command = riff_command(&search, Agent::ClaudeCode, Some("a b"));
        assert!(
            command.ends_with("--agent claude-code -- '-it'\\''s \"quoted\" $HOME'"),
            "{command}"
        );
        assert_eq!(
            reparse(&command),
            super::super::web::Command::Search {
                query: "-it's \"quoted\" $HOME".into(),
                limit: 8,
                allowed_domains: vec!["docs.rs".into()],
                blocked_domains: vec!["x.com".into()],
            }
        );

        let fetch = WebCall::Fetch {
            url: "https://e.com/a?x=1&y=2".into(),
            query: Some("pin a version".into()),
            offset: Some(50),
        };
        let command = riff_command(&fetch, Agent::Antigravity, None);
        assert_eq!(
            command,
            "riff web fetch 'https://e.com/a?x=1&y=2' --range 50- --query 'pin a version' --agent antigravity"
        );
        assert!(matches!(
            reparse(&command),
            super::super::web::Command::Fetch { url, query: Some(q), range: Some(_) }
                if url == "https://e.com/a?x=1&y=2" && q == "pin a version"
        ));
    }

    fn configure(home: &TempHome, config: &str, keys: &[&str]) {
        std::fs::write(home.path.join("config.json"), config).unwrap();
        std::fs::create_dir_all(home.path.join("keys")).unwrap();
        for key in keys {
            std::fs::write(home.path.join("keys").join(key), "k\n").unwrap();
        }
    }

    const ONLY_EXA: &str = r#"{"web": {"providers": {
        "anysearch": {"enabled": false}, "brave": {"enabled": false}, "deepseek": {"enabled": false},
        "firecrawl": {"enabled": false}, "tavily": {"enabled": false}, "searxng": {"enabled": false}}}}"#;

    fn note(output: &Value) -> &str {
        output["hookSpecificOutput"]["additionalContext"]
            .as_str()
            .unwrap()
    }

    #[test]
    fn a_servable_call_is_denied_with_the_riff_command() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let home = TempHome::new("hook-deny");
        configure(&home, ONLY_EXA, &["exa"]);
        let output =
            pretooluse(Agent::ClaudeCode, &cc("WebSearch", json!({"query": "q"}))).unwrap();
        let hook = &output["hookSpecificOutput"];
        assert_eq!(hook["hookEventName"], "PreToolUse");
        assert_eq!(hook["permissionDecision"], "deny");
        let reason = hook["permissionDecisionReason"].as_str().unwrap();
        assert!(
            reason.contains("riff web search --session sess-1 --agent claude-code -- q"),
            "{reason}"
        );

        let output = pretooluse(
            Agent::Antigravity,
            &ag("read_url_content", json!({"Url": "https://e.com/"})),
        )
        .unwrap();
        assert_eq!(output["decision"], "deny");
        assert!(
            output["reason"]
                .as_str()
                .unwrap()
                .contains("riff web fetch https://e.com/ --session conv-1 --agent antigravity")
        );
    }

    #[test]
    fn non_web_tools_get_no_opinion() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let home = TempHome::new("hook-other");
        configure(&home, ONLY_EXA, &["exa"]);
        assert_eq!(
            pretooluse(Agent::ClaudeCode, &cc("Bash", json!({"command": "ls"}))),
            None
        );
        assert_eq!(
            pretooluse(Agent::Antigravity, &ag("view_file", json!({}))),
            Some(json!({"decision": "allow"}))
        );
    }

    #[test]
    fn riff_lets_the_built_in_tool_through_when_it_cannot_serve() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let search = cc("WebSearch", json!({"query": "q"}));

        // No configuration at all.
        let home = TempHome::new("hook-noconfig");
        let output = pretooluse(Agent::ClaudeCode, &search).unwrap();
        assert!(output["hookSpecificOutput"]["permissionDecision"].is_null());
        assert!(
            note(&output).contains("not configured"),
            "{}",
            note(&output)
        );
        drop(home);

        // Configured, but the only provider has no key.
        let home = TempHome::new("hook-nokey");
        configure(&home, ONLY_EXA, &[]);
        let output = pretooluse(Agent::ClaudeCode, &search).unwrap();
        assert!(note(&output).contains("no search provider"));
        // ...yet fetch needs no provider and is still taken over.
        let fetch = pretooluse(
            Agent::ClaudeCode,
            &cc("WebFetch", json!({"url": "https://e.com/"})),
        )
        .unwrap();
        assert_eq!(fetch["hookSpecificOutput"]["permissionDecision"], "deny");
        drop(home);

        // Switched off.
        let home = TempHome::new("hook-off");
        configure(&home, r#"{"web": {"interceptBuiltin": false}}"#, &["exa"]);
        assert_eq!(pretooluse(Agent::ClaudeCode, &search), None);
        assert_eq!(
            pretooluse(Agent::Antigravity, &ag("search_web", json!({"query": "q"}))),
            Some(json!({"decision": "allow"}))
        );
        drop(home);
    }

    #[test]
    fn a_spent_budget_or_shared_cooldown_lets_search_through() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let home = TempHome::new("hook-spent");
        configure(&home, ONLY_EXA, &["exa"]);
        let id = crate::state::SessionId::resolve(
            Some("sess-1"),
            std::path::Path::new("/"),
            std::time::SystemTime::now(),
        );
        let mut session_2 = cc("WebSearch", json!({"query": "q"}));
        session_2["session_id"] = json!("sess-2");

        // exa's 30 calls spent in sess-1 only.
        let mut state = crate::state::SessionState::default();
        state.budget.provider_calls.insert("exa".into(), 30);
        crate::state::write_session_for_tests(&id, &state);
        let output =
            pretooluse(Agent::ClaudeCode, &cc("WebSearch", json!({"query": "q"}))).unwrap();
        assert!(note(&output).contains("out of budget"), "{}", note(&output));
        assert_eq!(
            pretooluse(Agent::ClaudeCode, &session_2).unwrap()["hookSpecificOutput"]["permissionDecision"],
            "deny"
        );

        // A shared cooldown lets every session through.
        crate::state::write_health_for_tests(&crate::state::HealthState {
            providers: vec![crate::web::provider_health::PersistedEntry {
                provider: "exa".into(),
                capability: "search".into(),
                soft_streak: 0,
                downs: 1,
                down_until: Some(crate::state::unix_now() + 600),
                fingerprint: None,
                last_reason: Some("quota_exhausted".into()),
                last_hard: Some(true),
                updated_at: 1,
            }],
            services: Vec::new(),
        });
        let output = pretooluse(Agent::ClaudeCode, &session_2).unwrap();
        assert!(note(&output).contains("cooling down"), "{}", note(&output));
    }
}
