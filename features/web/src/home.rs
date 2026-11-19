//! `$RIFF_HOME` (default `~/.riff`) and the configuration file in it.
//!
//! Design §3: one data root shared by every agent and project. Only
//! `$RIFF_HOME/config.json` (or `--config`) is read; nothing in the working
//! directory can change riff's egress or SSRF policy.

use std::path::{Path, PathBuf};
use std::sync::{OnceLock, RwLock};

use crate::settings::Config;

fn override_cell() -> &'static RwLock<Option<PathBuf>> {
    static CELL: OnceLock<RwLock<Option<PathBuf>>> = OnceLock::new();
    CELL.get_or_init(|| RwLock::new(None))
}

/// Points `riff_home()` somewhere else for the rest of the process. Tests use
/// it instead of mutating `RIFF_HOME`, which would race other tests.
pub fn set_home_override(path: Option<PathBuf>) {
    *override_cell().write().unwrap_or_else(|e| e.into_inner()) = path;
}

pub fn home_dir() -> Option<PathBuf> {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

/// The data root: override, then `RIFF_HOME`, then `~/.riff`.
pub fn riff_home() -> PathBuf {
    if let Some(path) = override_cell()
        .read()
        .unwrap_or_else(|e| e.into_inner())
        .clone()
    {
        return path;
    }
    default_home()
}

#[cfg(not(test))]
fn default_home() -> PathBuf {
    if let Some(path) = std::env::var_os("RIFF_HOME").filter(|value| !value.is_empty()) {
        return PathBuf::from(path);
    }
    home_dir().unwrap_or_else(std::env::temp_dir).join(".riff")
}

/// Tests never see the real home: without an explicit `TempHome` /
/// `HomeGuard`, each test process gets one throwaway directory. (nyan relied
/// on the justfile setting `NYAN_CONFIG_DIR`; a bare `cargo test` wrote into
/// `~/.nyan`.)
#[cfg(test)]
fn default_home() -> PathBuf {
    static DIR: OnceLock<PathBuf> = OnceLock::new();
    DIR.get_or_init(|| crate::test_env::scratch_dir("default-home"))
        .clone()
}

pub fn config_path() -> PathBuf {
    riff_home().join("config.json")
}

/// Expands `$RIFF_HOME/…` and `~/…` in a configured path.
pub fn expand_path(path: &str) -> PathBuf {
    if let Some(rest) = path.strip_prefix("$RIFF_HOME/") {
        return riff_home().join(rest);
    }
    if path == "~" {
        return home_dir().unwrap_or_default();
    }
    if let Some(rest) = path.strip_prefix("~/") {
        return home_dir().unwrap_or_default().join(rest);
    }
    PathBuf::from(path)
}

/// Creates `dir` (and parents) with mode 0700 on Unix.
pub fn ensure_private_dir(dir: &Path) -> std::io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        std::fs::DirBuilder::new()
            .recursive(true)
            .mode(0o700)
            .create(dir)
    }
    #[cfg(not(unix))]
    {
        std::fs::create_dir_all(dir)
    }
}

#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("no configuration at {0} (run `riff init`)")]
    Missing(PathBuf),
    #[error("cannot read {path}: {source}")]
    Unreadable {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("invalid configuration in {path}: {message}")]
    Invalid { path: PathBuf, message: String },
}

/// Reads and validates the configuration. `path = None` means
/// `$RIFF_HOME/config.json`.
pub fn load_config(path: Option<&Path>) -> Result<Config, ConfigError> {
    let path = path.map(Path::to_path_buf).unwrap_or_else(config_path);
    let text = match std::fs::read_to_string(&path) {
        Ok(text) => text,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Err(ConfigError::Missing(path));
        }
        Err(source) => return Err(ConfigError::Unreadable { path, source }),
    };
    parse_config(&text).map_err(|message| ConfigError::Invalid { path, message })
}

pub fn parse_config(text: &str) -> Result<Config, String> {
    let config: Config = serde_json::from_str(text).map_err(|error| error.to_string())?;
    validate(&config)?;
    Ok(config)
}

/// The checks nyan's settings schema made beyond the types: names must be
/// known so a typo is reported instead of becoming a silently ignored entry.
fn validate(config: &Config) -> Result<(), String> {
    if let Some(web) = &config.web {
        let known = crate::settings::provider_names();
        for name in web.providers.iter().flat_map(|providers| providers.keys()) {
            if !known.contains(&name.as_str()) {
                return Err(format!("web.providers: unknown provider `{name}`"));
            }
        }
        for name in web.fetch_fallback.iter().flatten() {
            if !known.contains(&name.as_str()) {
                return Err(format!("web.fetchFallback: unknown provider `{name}`"));
            }
        }
    }
    if let Some(decision) = &config.decision {
        let known = crate::settings::decision_point_names();
        for name in decision.points.iter().flat_map(|points| points.keys()) {
            if !known.contains(&name.as_str()) {
                return Err(format!("decision.points: unknown decision point `{name}`"));
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_object_is_a_valid_config() {
        assert_eq!(parse_config("{}").unwrap(), Config::default());
    }

    #[test]
    fn unknown_keys_and_names_are_rejected() {
        assert!(parse_config(r#"{"wbe": {}}"#).is_err());
        assert!(parse_config(r#"{"web": {"providers": {"google": {}}}}"#).is_err());
        assert!(parse_config(r#"{"web": {"fetchFallback": ["brave2"]}}"#).is_err());
        assert!(parse_config(r#"{"decision": {"points": {"memory.type": {}}}}"#).is_err());
    }

    #[test]
    fn web_and_decision_sections_parse() {
        let config = parse_config(
            r#"{"web": {"providers": {"exa": {"enabled": false}}, "fetchVia": "direct",
                 "search": {"rerank": {"service": {"url": "http://h:1"}}}},
                "decision": {"points": {"web.prune": {"mode": "off"}}}}"#,
        )
        .unwrap();
        let web = config.web.unwrap();
        assert!(!web.provider("exa").enabled);
        assert_eq!(web.fetch_via(), crate::settings::FetchVia::Direct);
        assert_eq!(web.search().rerank().service.unwrap().url(), "http://h:1");
    }

    #[test]
    fn riff_home_paths_expand() {
        set_home_override(Some(PathBuf::from("/tmp/riff-home-test")));
        assert_eq!(
            expand_path("$RIFF_HOME/keys/exa"),
            PathBuf::from("/tmp/riff-home-test/keys/exa")
        );
        assert_eq!(expand_path("/abs/key"), PathBuf::from("/abs/key"));
        set_home_override(None);
    }
}
