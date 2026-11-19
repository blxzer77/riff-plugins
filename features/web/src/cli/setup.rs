//! `riff init` and `riff web doctor` (design 4.1, 8).

use std::path::Path;
use std::time::Duration;

/// The template `riff init` writes. Every builtin provider is enabled by
/// default and reads `$RIFF_HOME/keys/<name>`; only what has no default is
/// spelled out.
pub const TEMPLATE: &str = r#"{
  "web": {
    "providers": {
      "searxng": { "enabled": false, "url": "http://127.0.0.1:8092" }
    },
    "fetchVia": "proxy"
  },
  "decision": {
    "enabled": true
  }
}
"#;

/// Keys riff can use, as files under `$RIFF_HOME/keys/`.
const KEY_NAMES: [&str; 7] = [
    "anysearch",
    "brave",
    "deepseek",
    "exa",
    "firecrawl",
    "tavily",
    "emrank",
];

/// `riff init`: writes the template unless a configuration exists, creates
/// `keys/`, and names the keys a previous nyan install could supply.
pub fn init(args: &[String]) -> i32 {
    if let Some(extra) = args.first() {
        if extra == "-h" || extra == "--help" {
            println!(
                "Usage: riff init\n\nWrites a starting $RIFF_HOME/config.json (never overwrites)."
            );
            return 0;
        }
        eprintln!("riff init: unexpected argument `{extra}`");
        return super::web::exit::USAGE;
    }
    let home = crate::home::riff_home();
    let config = crate::home::config_path();
    if let Err(error) = crate::home::ensure_private_dir(&home.join("keys")) {
        eprintln!(
            "riff init: cannot create {}: {error}",
            home.join("keys").display()
        );
        return super::web::exit::OTHER;
    }
    if config.exists() {
        println!("{} already exists; not overwritten.", config.display());
    } else {
        if let Err(error) = write_private(&config, TEMPLATE) {
            eprintln!("riff init: cannot write {}: {error}", config.display());
            return super::web::exit::OTHER;
        }
        println!("Wrote {}.", config.display());
    }
    let missing = KEY_NAMES
        .iter()
        .filter(|name| !home.join("keys").join(name).exists())
        .collect::<Vec<_>>();
    if missing.is_empty() {
        return 0;
    }
    println!(
        "Put each provider's key in {}/<name> (mode 0600). Missing: {}.",
        home.join("keys").display(),
        missing
            .iter()
            .map(|name| name.to_string())
            .collect::<Vec<_>>()
            .join(", ")
    );
    if let Some(nyan) = crate::home::home_dir().map(|dir| dir.join(".nyan/keys")) {
        let found = missing
            .iter()
            .filter(|name| nyan.join(name).is_file())
            .collect::<Vec<_>>();
        if !found.is_empty() {
            let names = found
                .iter()
                .map(|name| name.to_string())
                .collect::<Vec<_>>()
                .join(",");
            println!(
                "nyan has some of them; copy (not move) with:\n  for k in {{{names}}}; do install -m 600 {}/$k {}/$k; done",
                nyan.display(),
                home.join("keys").display()
            );
        }
    }
    0
}

fn write_private(path: &Path, content: &str) -> std::io::Result<()> {
    #[cfg(unix)]
    {
        use std::io::Write;
        use std::os::unix::fs::OpenOptionsExt;
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(path)?;
        file.write_all(content.as_bytes())
    }
    #[cfg(not(unix))]
    {
        std::fs::write(path, content)
    }
}

/// One line of `riff web doctor`.
struct Check {
    ok: bool,
    label: String,
    detail: String,
}

impl Check {
    fn new(ok: bool, label: impl Into<String>, detail: impl Into<String>) -> Self {
        Self {
            ok,
            label: label.into(),
            detail: detail.into(),
        }
    }
}

/// `riff web doctor`: what riff would use, and what is missing. Exit 0 when
/// riff can search and fetch, 3 when it cannot. Reachability is a TCP connect
/// only (no API request, no quota spent); the hosts behind a proxy are not
/// probed, the proxy is.
pub fn doctor() -> i32 {
    let mut checks = Vec::new();
    let path = crate::home::config_path();
    let config = match crate::home::load_config(None) {
        Ok(config) => {
            checks.push(Check::new(true, "config", path.display().to_string()));
            config
        }
        Err(error) => {
            checks.push(Check::new(false, "config", error.to_string()));
            print(&checks);
            return super::web::exit::CONFIG;
        }
    };
    let web = config.web.clone().unwrap_or_default();

    let usable = crate::web::usable_search_providers(&web);
    for name in crate::settings::provider_names() {
        let resolved = web.provider(name);
        let detail = if !resolved.enabled {
            "disabled".to_string()
        } else if name == "searxng" {
            match &resolved.url {
                Some(url) => format!("{url} ({})", reachable(url)),
                None => "no url".to_string(),
            }
        } else if usable.contains(&name) {
            "key found".to_string()
        } else {
            format!(
                "no key: put it in {} or set {}",
                resolved
                    .api_key_file
                    .as_deref()
                    .map(|path| crate::home::expand_path(path).display().to_string())
                    .unwrap_or_default(),
                crate::web::providers::key_env_var(name)
            )
        };
        let ok = !resolved.enabled || usable.contains(&name);
        checks.push(Check::new(ok, format!("provider {name}"), detail));
    }
    checks.push(Check::new(
        !usable.is_empty(),
        "search",
        if usable.is_empty() {
            "no provider can be asked".to_string()
        } else {
            format!("{} provider(s): {}", usable.len(), usable.join(", "))
        },
    ));

    let proxy = crate::net::proxy_url(&crate::net::ProcessEnv);
    match web.fetch_via() {
        crate::settings::FetchVia::Proxy => checks.push(Check::new(
            proxy.is_some(),
            "fetch",
            match &proxy {
                Some(url) => format!("via proxy {} ({})", redact_userinfo(url), reachable(url)),
                None => {
                    "fetchVia is proxy but no https_proxy/HTTPS_PROXY/http_proxy/HTTP_PROXY is set"
                        .to_string()
                }
            },
        )),
        crate::settings::FetchVia::Direct => {
            checks.push(Check::new(true, "fetch", "direct (DNS-pinned)"));
        }
    }
    let pdftotext = which("pdftotext");
    checks.push(Check::new(
        true,
        "pdf",
        match pdftotext {
            Some(path) => format!("pdftotext at {}", path.display()),
            None => "pdftotext not found: PDF pages will be refused".to_string(),
        },
    ));

    let rerank = web.search().rerank();
    checks.push(Check::new(
        true,
        "rerank",
        match (&rerank.service, rerank.enabled()) {
            (_, false) => "disabled".to_string(),
            (Some(service), true) if service.url.is_some() => {
                format!("{} ({})", service.url(), reachable(service.url()))
            }
            _ => "not configured (results keep the fused order)".to_string(),
        },
    ));
    let decision = config.decision.clone().unwrap_or_default();
    let emrank = decision.emrank();
    let key = crate::home::expand_path(emrank.api_key_file());
    checks.push(Check::new(
        true,
        "decision",
        if !decision.enabled() {
            "disabled".to_string()
        } else if !key.is_file() {
            format!(
                "no EMRank key at {} (every point uses its rule)",
                key.display()
            )
        } else {
            format!(
                "EMRank {}, fast={}, accurate={}, critical deadline {} ms",
                emrank.url(),
                emrank.model_id(crate::settings::DecisionModel::Fast),
                emrank.model_id(crate::settings::DecisionModel::Accurate),
                decision.deadline(true).as_millis()
            )
        },
    ));

    let health = crate::state::peek(&crate::state::SessionId::cwd_window(
        Path::new("/"),
        std::time::SystemTime::now(),
    ))
    .health;
    let now = crate::state::unix_now();
    let cooling = health
        .providers
        .iter()
        .filter_map(|entry| {
            let until = entry.down_until.filter(|until| *until > now)?;
            Some(format!(
                "{} {} {} ({}s left)",
                entry.provider,
                entry.capability,
                entry.last_reason.as_deref().unwrap_or("down"),
                until - now
            ))
        })
        .chain(health.services.iter().filter_map(|entry| {
            let until = entry.down_until.filter(|until| *until > now)?;
            Some(format!(
                "{} {} ({}s left)",
                entry.kind,
                entry.last_failure.as_deref().unwrap_or("down"),
                until - now
            ))
        }))
        .collect::<Vec<_>>();
    checks.push(Check::new(
        true,
        "cooldowns",
        if cooling.is_empty() {
            "none".to_string()
        } else {
            format!("{} (clear with `riff web reset`)", cooling.join("; "))
        },
    ));
    checks.push(Check::new(
        true,
        "intercept",
        if web.intercept_builtin() {
            "built-in web tools are redirected to riff"
        } else {
            "off (web.interceptBuiltin = false)"
        },
    ));

    print(&checks);
    if usable.is_empty() || (web.fetch_via() == crate::settings::FetchVia::Proxy && proxy.is_none())
    {
        super::web::exit::CONFIG
    } else {
        0
    }
}

fn print(checks: &[Check]) {
    let width = checks
        .iter()
        .map(|check| check.label.len())
        .max()
        .unwrap_or(0);
    for check in checks {
        println!(
            "{} {:width$}  {}",
            if check.ok { "ok  " } else { "FAIL" },
            check.label,
            check.detail
        );
    }
}

/// `http://user:pass@host:port` → `http://host:port` for display.
fn redact_userinfo(url: &str) -> String {
    match url::Url::parse(url) {
        Ok(mut parsed) if !parsed.username().is_empty() || parsed.password().is_some() => {
            let _ = parsed.set_username("");
            let _ = parsed.set_password(None);
            parsed.to_string()
        }
        _ => url.to_string(),
    }
}

/// A 2-second TCP connect to the URL's host and port.
fn reachable(url: &str) -> &'static str {
    let Ok(parsed) = url::Url::parse(url) else {
        return "invalid url";
    };
    let Some(host) = parsed.host_str() else {
        return "invalid url";
    };
    let Some(port) = parsed.port_or_known_default().or(match parsed.scheme() {
        "socks5" | "socks5h" => Some(1080),
        _ => None,
    }) else {
        return "no port";
    };
    use std::net::ToSocketAddrs;
    let Ok(addresses) = (host, port).to_socket_addrs() else {
        return "unresolvable";
    };
    for address in addresses {
        if std::net::TcpStream::connect_timeout(&address, Duration::from_secs(2)).is_ok() {
            return "reachable";
        }
    }
    "unreachable"
}

fn which(program: &str) -> Option<std::path::PathBuf> {
    std::env::var_os("PATH")?
        .to_str()?
        .split(if cfg!(windows) { ';' } else { ':' })
        .map(|dir| Path::new(dir).join(program))
        .find(|candidate| candidate.is_file())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_env::{TEST_ENV_LOCK, TempHome};

    #[test]
    fn the_template_is_a_valid_configuration() {
        crate::home::parse_config(TEMPLATE).unwrap();
    }

    #[test]
    fn init_writes_once_and_never_overwrites() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let home = TempHome::new("init");
        assert_eq!(init(&[]), 0);
        let config = home.path.join("config.json");
        assert_eq!(std::fs::read_to_string(&config).unwrap(), TEMPLATE);
        std::fs::write(&config, "{}").unwrap();
        assert_eq!(init(&[]), 0);
        assert_eq!(std::fs::read_to_string(&config).unwrap(), "{}");
        assert!(home.path.join("keys").is_dir());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::remove_file(&config).unwrap();
            init(&[]);
            let mode = std::fs::metadata(&config).unwrap().permissions().mode() & 0o777;
            assert_eq!(mode, 0o600);
        }
    }

    #[test]
    fn userinfo_is_never_shown() {
        assert_eq!(
            redact_userinfo("http://alice:s3cret@proxy:8080"),
            "http://proxy:8080/"
        );
        assert_eq!(redact_userinfo("http://proxy:8080"), "http://proxy:8080");
    }
}
