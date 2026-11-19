//! On-disk state for short-lived processes (design 2.3, 2.4).
//!
//! nyan kept budgets, provider health, the URL index, the last search's
//! candidates and decision probes in process memory; every `riff` call is a new
//! process, so they live under `$RIFF_HOME/state/` instead:
//!
//! - `sessions/<id>.json`: per-session counters (web budget, decision budget,
//!   last candidates, probes);
//! - `health.json`: provider and service health, shared by every session
//!   (a provider out of quota is out of quota for everyone).
//!
//! A command loads state at start ([`Session::load`]) and writes it back at
//! the end ([`Session::store`]); both happen under an exclusive file lock on
//! the session (and on `health.json`), held for the whole command so two
//! concurrent calls in one session cannot lose each other's counts. Different
//! sessions run in parallel; they only serialize on `health.json` for the
//! short load/store, not the command.

use std::fs::File;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize, de::DeserializeOwned};

/// The window that stands in for a session when the host gives no id
/// (design 2.4): calls from one working directory in the same 6-hour slot
/// share a budget.
pub const CWD_WINDOW: Duration = Duration::from_secs(6 * 60 * 60);

/// Session ids hosts export to every shell command they run. Codex sets
/// `CODEX_SESSION_ID` (codex-rs/core/src/exec_env.rs, rust-v0.170.0).
pub const HOST_SESSION_VARS: [&str; 1] = ["CODEX_SESSION_ID"];

/// Session files untouched for this long are deleted on the next store.
const SESSION_RETENTION: Duration = Duration::from_secs(7 * 24 * 60 * 60);

pub fn state_dir() -> PathBuf {
    crate::home::riff_home().join("state")
}

fn sessions_dir() -> PathBuf {
    state_dir().join("sessions")
}

/// Which session a command belongs to.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SessionId(String);

impl SessionId {
    /// `--session`, then `RIFF_SESSION`, then a session id the host puts in
    /// every shell command's environment ([`HOST_SESSION_VARS`]), then the
    /// cwd window. The same raw id reaches the same session whichever way it
    /// arrives (a hook-suggested `--session`, an exported variable).
    pub fn resolve(explicit: Option<&str>, cwd: &Path, now: SystemTime) -> Self {
        let from_env = |name: &str| {
            std::env::var(name)
                .ok()
                .map(|value| value.trim().to_string())
                .filter(|value| !value.is_empty())
        };
        let named = explicit
            .map(|value| value.trim().to_string())
            .filter(|value| !value.is_empty())
            .or_else(|| from_env("RIFF_SESSION"))
            .or_else(|| HOST_SESSION_VARS.iter().find_map(|name| from_env(name)));
        match named {
            Some(name) => Self(format!("s-{}", short_hash(name.as_bytes()))),
            None => Self::cwd_window(cwd, now),
        }
    }

    pub fn cwd_window(cwd: &Path, now: SystemTime) -> Self {
        let cwd = std::fs::canonicalize(cwd).unwrap_or_else(|_| cwd.to_path_buf());
        let slot =
            now.duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() / CWD_WINDOW.as_secs();
        Self(format!(
            "cwd-{}-{slot}",
            short_hash(cwd.to_string_lossy().as_bytes())
        ))
    }

    /// File-name-safe by construction: a fixed prefix plus hex.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Host session ids are opaque and may contain anything; only a digest is
/// used in paths, so no input can escape `sessions/`.
fn short_hash(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    Sha256::digest(bytes)[..12]
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

/// An exclusively locked JSON file. The lock is held until drop.
pub struct Locked<T> {
    file: File,
    path: PathBuf,
    pub value: T,
}

impl<T: Serialize + DeserializeOwned + Default> Locked<T> {
    /// Opens (creating if needed) and locks `path`. A missing, empty or
    /// unparsable file yields `T::default()`: state is a cache of counters,
    /// and a corrupt file must not wedge every later command.
    pub fn open(path: PathBuf) -> std::io::Result<Self> {
        if let Some(parent) = path.parent() {
            crate::home::ensure_private_dir(parent)?;
        }
        let file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(&path)?;
        set_private(&path);
        file.lock()?;
        let value = std::fs::read(&path)
            .ok()
            .and_then(|bytes| serde_json::from_slice(&bytes).ok())
            .unwrap_or_default();
        Ok(Self { file, path, value })
    }

    /// Writes the value back atomically (temp file + rename) while still
    /// holding the lock on the original path.
    pub fn store(&self) -> std::io::Result<()> {
        let bytes = serde_json::to_vec(&self.value).map_err(std::io::Error::other)?;
        let temp = self
            .path
            .with_extension(format!("tmp-{}", uuid::Uuid::new_v4().simple()));
        std::fs::write(&temp, bytes)?;
        set_private(&temp);
        std::fs::rename(&temp, &self.path)
    }
}

impl<T> Drop for Locked<T> {
    fn drop(&mut self) {
        let _ = self.file.unlock();
    }
}

fn set_private(path: &Path) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600));
    }
    #[cfg(not(unix))]
    let _ = path;
}

/// Seconds since the Unix epoch, for on-disk timestamps. `Instant` is not
/// meaningful across processes.
pub fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

/// Milliseconds since the Unix epoch: the `updatedAt` stamp that tells a
/// process's own change from the value it loaded (see `merge_health`).
pub fn unix_now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
        .min(u128::from(u64::MAX)) as u64
}

/// Per-session state. Each module owns its field and converts to/from its
/// in-memory form.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct SessionState {
    pub budget: crate::web::budget::Persisted,
    pub decision_budget: crate::decision::PersistedBudget,
    pub candidates: Vec<String>,
    pub probes: Vec<crate::decision::probe::PersistedProbe>,
}

/// Shared health state.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct HealthState {
    pub providers: Vec<crate::web::provider_health::PersistedEntry>,
    pub services: Vec<crate::service_health::PersistedService>,
}

/// The state of one command: the session's file and the shared health file,
/// both locked from [`Session::load`] until [`Session::store`] / drop.
pub struct Session {
    pub id: SessionId,
    session: Locked<SessionState>,
    /// Health as installed at load, for telling this process's changes apart.
    loaded_health: HealthState,
}

impl Session {
    /// Locks the session file and installs its counters and the shared health
    /// into the process registries.
    pub fn load(id: SessionId) -> std::io::Result<Self> {
        let session =
            Locked::<SessionState>::open(sessions_dir().join(format!("{}.json", id.as_str())))?;
        install_session(&session.value);
        let health = Locked::<HealthState>::open(state_dir().join("health.json"))?;
        install_health(&health.value);
        drop(health);
        let loaded_health = capture_health();
        Ok(Self {
            id,
            session,
            loaded_health,
        })
    }

    /// Writes the process registries back. Health is merged under its own
    /// lock: another session may have recorded outcomes meanwhile, so only
    /// the entries this process changed are written (`merge_health`).
    pub fn store(mut self) -> std::io::Result<()> {
        self.session.value = capture_session();
        self.session.store()?;
        let mut health = Locked::<HealthState>::open(state_dir().join("health.json"))?;
        health.value = merge_health(
            std::mem::take(&mut health.value),
            &self.loaded_health,
            capture_health(),
        );
        health.store()?;
        drop(health);
        prune_sessions(&sessions_dir(), self.id.as_str());
        Ok(())
    }

    /// `riff web reset`: a fresh session, and cooldowns cleared for everyone.
    pub fn reset(mut self) -> std::io::Result<()> {
        crate::web::reset_session();
        self.session.value = SessionState::default();
        self.session.store()?;
        let mut health = Locked::<HealthState>::open(state_dir().join("health.json"))?;
        health.value = HealthState::default();
        health.store()
    }
}

/// A read-only look at a session and the shared health, without the locks.
/// The hook uses it: it must answer in milliseconds and must not wait for a
/// search that holds the session lock. A file being replaced reads as the old
/// or the new content (writes are temp file + rename), never torn.
pub struct Peek {
    pub session: SessionState,
    pub health: HealthState,
}

pub fn peek(id: &SessionId) -> Peek {
    fn read<T: DeserializeOwned + Default>(path: PathBuf) -> T {
        std::fs::read(path)
            .ok()
            .and_then(|bytes| serde_json::from_slice(&bytes).ok())
            .unwrap_or_default()
    }
    Peek {
        session: read(sessions_dir().join(format!("{}.json", id.as_str()))),
        health: read(state_dir().join("health.json")),
    }
}

#[cfg(test)]
pub fn write_session_for_tests(id: &SessionId, state: &SessionState) {
    let mut locked =
        Locked::<SessionState>::open(sessions_dir().join(format!("{}.json", id.as_str()))).unwrap();
    locked.value = state.clone();
    locked.store().unwrap();
}

#[cfg(test)]
pub fn write_health_for_tests(state: &HealthState) {
    let mut locked = Locked::<HealthState>::open(state_dir().join("health.json")).unwrap();
    locked.value = state.clone();
    locked.store().unwrap();
}

fn install_session(state: &SessionState) {
    crate::web::budget::restore(&state.budget);
    crate::decision::restore_session_budget(&state.decision_budget);
    crate::web::search::remember_candidates(state.candidates.clone());
    crate::decision::probe::restore(&state.probes);
}

fn capture_session() -> SessionState {
    SessionState {
        budget: crate::web::budget::persist(),
        decision_budget: crate::decision::persist_session_budget(),
        candidates: crate::web::search::recent_candidate_list(),
        probes: crate::decision::probe::persist(),
    }
}

fn install_health(state: &HealthState) {
    crate::web::provider_health::restore(&state.providers);
    crate::service_health::restore(&state.services);
}

fn capture_health() -> HealthState {
    HealthState {
        providers: crate::web::provider_health::persist(),
        services: crate::service_health::persist(),
    }
}

/// Writes back only the entries this process recorded something for; every
/// other entry keeps the stored value, which another session may have updated
/// meanwhile. An entry's `updated_at` only moves when this process records an
/// outcome for it, so "changed" is "`updated_at` differs from what was
/// loaded" (`base`). Comparing whole entries would not work: `down_until`
/// round-trips through `Instant` and can drift by a second. Of two changes to
/// one entry, the later `updated_at` wins.
fn merge_health(stored: HealthState, base: &HealthState, ours: HealthState) -> HealthState {
    HealthState {
        providers: merge_by_key(
            stored.providers,
            &base.providers,
            ours.providers,
            |e| e.key(),
            |e| e.updated_at,
        ),
        services: merge_by_key(
            stored.services,
            &base.services,
            ours.services,
            |e| e.kind.clone(),
            |e| e.updated_at,
        ),
    }
}

fn merge_by_key<T, K: PartialEq>(
    stored: Vec<T>,
    base: &[T],
    ours: Vec<T>,
    key: impl Fn(&T) -> K,
    updated: impl Fn(&T) -> u64,
) -> Vec<T> {
    let mut merged = stored;
    for entry in ours {
        let untouched = base
            .iter()
            .any(|loaded| key(loaded) == key(&entry) && updated(loaded) == updated(&entry));
        if untouched {
            continue;
        }
        match merged
            .iter()
            .position(|existing| key(existing) == key(&entry))
        {
            Some(index) if updated(&entry) >= updated(&merged[index]) => merged[index] = entry,
            Some(_) => {}
            None => merged.push(entry),
        }
    }
    merged
}

/// Deletes session files older than [`SESSION_RETENTION`]. Best effort; never
/// touches the current session.
fn prune_sessions(dir: &Path, current: &str) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    let cutoff = SystemTime::now() - SESSION_RETENTION;
    for entry in entries.flatten() {
        let path = entry.path();
        if path.file_stem().and_then(|s| s.to_str()) == Some(current) {
            continue;
        }
        let old = entry
            .metadata()
            .and_then(|m| m.modified())
            .is_ok_and(|modified| modified < cutoff);
        if old {
            let _ = std::fs::remove_file(path);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn named_sessions_hash_and_unnamed_ones_fall_into_a_cwd_window() {
        let cwd = Path::new("/");
        let t0 = UNIX_EPOCH + Duration::from_secs(10 * CWD_WINDOW.as_secs() + 5);
        let a = SessionId::resolve(Some("../../etc/passwd"), cwd, t0);
        assert!(a.as_str().starts_with("s-"));
        assert!(a.as_str()[2..].bytes().all(|b| b.is_ascii_hexdigit()));
        assert_eq!(a, SessionId::resolve(Some(" ../../etc/passwd "), cwd, t0));
        assert_ne!(a, SessionId::resolve(Some("other"), cwd, t0));

        let w = SessionId::cwd_window(cwd, t0);
        assert_eq!(w, SessionId::cwd_window(cwd, t0 + Duration::from_secs(60)));
        assert_ne!(w, SessionId::cwd_window(cwd, t0 + CWD_WINDOW));
        assert_ne!(w, SessionId::cwd_window(Path::new("/tmp"), t0));
    }

    #[test]
    fn a_host_session_variable_names_the_same_session_as_the_flag() {
        use crate::test_env::{EnvVarGuard, TEST_ENV_LOCK};
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let cwd = Path::new("/");
        let now = SystemTime::now();
        let _riff = EnvVarGuard::unset("RIFF_SESSION");
        let _codex = EnvVarGuard::unset("CODEX_SESSION_ID");
        let window = SessionId::resolve(None, cwd, now);
        assert!(window.as_str().starts_with("cwd-"));
        {
            let _codex = EnvVarGuard::set("CODEX_SESSION_ID", "019a-thread");
            assert_eq!(
                SessionId::resolve(None, cwd, now),
                SessionId::resolve(Some("019a-thread"), cwd, now)
            );
            // RIFF_SESSION and the flag outrank the host's variable.
            let _riff = EnvVarGuard::set("RIFF_SESSION", "mine");
            assert_eq!(
                SessionId::resolve(None, cwd, now),
                SessionId::resolve(Some("mine"), cwd, now)
            );
            assert_eq!(
                SessionId::resolve(Some("flag"), cwd, now),
                SessionId::resolve(Some("flag"), Path::new("/tmp"), now)
            );
        }
        assert_eq!(SessionId::resolve(None, cwd, now), window);
    }

    #[test]
    fn a_corrupt_file_reads_as_default_and_is_replaced_on_store() {
        let dir = crate::test_env::scratch_dir("state-corrupt");
        let path = dir.join("x.json");
        std::fs::write(&path, b"{not json").unwrap();
        let mut locked = Locked::<SessionState>::open(path.clone()).unwrap();
        assert_eq!(locked.value, SessionState::default());
        locked.value.candidates = vec!["https://a.example/".into()];
        locked.store().unwrap();
        drop(locked);
        let reread = Locked::<SessionState>::open(path).unwrap();
        assert_eq!(reread.value.candidates, ["https://a.example/"]);
    }

    #[test]
    fn the_lock_is_exclusive_until_drop() {
        let dir = crate::test_env::scratch_dir("state-lock");
        let path = dir.join("x.json");
        let held = Locked::<SessionState>::open(path.clone()).unwrap();
        let other = File::open(&path).unwrap();
        assert!(other.try_lock().is_err());
        drop(held);
        assert!(other.try_lock().is_ok());
    }

    #[test]
    fn newer_health_entries_win_and_untouched_ones_survive() {
        let entry =
            |kind: &str, updated_at: u64, failures: u32| crate::service_health::PersistedService {
                kind: kind.to_string(),
                down_until: Some(updated_at + 30),
                consecutive_failures: failures,
                last_failure: None,
                updated_at,
            };
        let stored = HealthState {
            providers: Vec::new(),
            services: vec![entry("searxng", 100, 3), entry("rerank", 100, 1)],
        };
        let ours = HealthState {
            providers: Vec::new(),
            services: vec![entry("searxng", 90, 1), entry("emrank", 200, 2)],
        };
        // This process loaded searxng@90 and rerank@100 and changed nothing
        // but emrank; another session meanwhile moved searxng to @100.
        let base = HealthState {
            providers: Vec::new(),
            services: vec![entry("searxng", 90, 1), entry("rerank", 100, 1)],
        };
        let merged = merge_health(stored, &base, ours).services;
        let get = |kind: &str| {
            merged
                .iter()
                .find(|e| e.kind == kind)
                .unwrap()
                .consecutive_failures
        };
        assert_eq!(
            get("searxng"),
            3,
            "untouched here, so the other session's value stays"
        );
        assert_eq!(get("rerank"), 1, "untouched by this process");
        assert_eq!(get("emrank"), 2, "new from this process");
    }

    #[test]
    fn a_stale_untouched_entry_never_overwrites_a_concurrent_change() {
        let service = |updated_at: u64, failures: u32| crate::service_health::PersistedService {
            kind: "searxng".to_string(),
            down_until: None,
            consecutive_failures: failures,
            last_failure: None,
            updated_at,
        };
        // Loaded Ready@100; another session recorded Down@100 (same stamp
        // would be a coincidence, a later one the norm) — either way ours,
        // untouched, must not win.
        for other in [100, 150] {
            let stored = HealthState {
                providers: Vec::new(),
                services: vec![service(other, 4)],
            };
            let base = HealthState {
                providers: Vec::new(),
                services: vec![service(100, 0)],
            };
            let ours = base.clone();
            let merged = merge_health(stored, &base, ours).services;
            assert_eq!(merged[0].consecutive_failures, 4, "other={other}");
        }
        // Our own later change wins over an older concurrent one.
        let stored = HealthState {
            providers: Vec::new(),
            services: vec![service(150, 4)],
        };
        let base = HealthState {
            providers: Vec::new(),
            services: vec![service(100, 0)],
        };
        let ours = HealthState {
            providers: Vec::new(),
            services: vec![service(200, 1)],
        };
        assert_eq!(
            merge_health(stored, &base, ours).services[0].consecutive_failures,
            1
        );
    }
}
