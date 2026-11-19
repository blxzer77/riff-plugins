//! Post-hoc usage probes (decision-provider §7).
//!
//! A decision can only record what it answered. Whether the retained result
//! was actually used afterwards is observable from a later event: the model
//! fetches a URL candidate with `riff web fetch`. This module
//! keeps the recent probes in memory and appends two extra record shapes to
//! the same `decision/decisions.jsonl`:
//!
//! - `{"event":"probe", "probeId", "point", "kind", "candidateCount"}` when a
//!   decision retains candidates (immediately after the decision record);
//! - `{"event":"posthoc", "probeId", "point", "kind", "identity"}` the first
//!   time each retained candidate is observed.
//!
//! `riff web decisions` reads `probes` and `used` from these rows, so the denominator
//! is explicit and decision samples are never double-counted. Probes expire
//! after [`PROBE_TTL`]; an expired probe simply stops matching, keeping memory
//! bounded across a long session. `riff web reset` forgets them (`clear`).
//!
//! Scope: riff only has URL candidates (`web.answers`, `web.page_answers`).

use std::collections::HashSet;
use std::sync::{Mutex, MutexGuard, OnceLock};
use std::time::{Duration, Instant};

use serde::Serialize;

use super::DecisionPoint;

/// How long a retained candidate can still be attributed to its decision.
const PROBE_TTL: Duration = Duration::from_secs(30 * 60);
/// Upper bound on pending probes; the oldest is dropped first.
const MAX_PROBES: usize = 256;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Kind {
    Url,
}

impl Kind {
    fn as_str(self) -> &'static str {
        match self {
            Kind::Url => "url",
        }
    }
}

struct Candidate {
    key: String,
    label: String,
    used: bool,
}

struct Probe {
    id: String,
    point: DecisionPoint,
    kind: Kind,
    created: Instant,
    candidates: Vec<Candidate>,
}

fn probes() -> &'static Mutex<Vec<Probe>> {
    static PROBES: OnceLock<Mutex<Vec<Probe>>> = OnceLock::new();
    PROBES.get_or_init(|| Mutex::new(Vec::new()))
}

fn lock() -> MutexGuard<'static, Vec<Probe>> {
    probes()
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ProbeRecord<'a> {
    timestamp: String,
    event: &'static str,
    probe_id: &'a str,
    point: &'a str,
    kind: &'a str,
    candidate_count: usize,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct PosthocRecord {
    timestamp: String,
    event: &'static str,
    probe_id: String,
    point: &'static str,
    kind: &'static str,
    identity: String,
}

/// Register the URL candidates a decision retained. URLs are matched later
/// against `WebFetch` calls after scheme/host and fragment normalization.
pub fn register_urls<I>(point: DecisionPoint, urls: I) -> Option<String>
where
    I: IntoIterator<Item = String>,
{
    register(
        point,
        Kind::Url,
        urls.into_iter().map(|url| {
            let key = normalize_url(&url);
            (key, url)
        }),
    )
}

fn register<I>(point: DecisionPoint, kind: Kind, candidates: I) -> Option<String>
where
    I: IntoIterator<Item = (String, String)>,
{
    let mut seen = HashSet::new();
    let candidates = candidates
        .into_iter()
        .filter(|(key, _)| !key.is_empty() && seen.insert(key.clone()))
        .map(|(key, label)| Candidate {
            key,
            label,
            used: false,
        })
        .collect::<Vec<_>>();
    if candidates.is_empty() {
        return None;
    }

    let candidate_count = candidates.len();
    let id = uuid::Uuid::new_v4().simple().to_string();
    let now = Instant::now();
    {
        let mut pending = lock();
        pending.retain(|probe| now.duration_since(probe.created) < PROBE_TTL);
        while pending.len() >= MAX_PROBES {
            pending.remove(0);
        }
        pending.push(Probe {
            id: id.clone(),
            point,
            kind,
            created: now,
            candidates,
        });
    }
    append(&ProbeRecord {
        timestamp: chrono::Utc::now().to_rfc3339(),
        event: "probe",
        probe_id: &id,
        point: point.as_str(),
        kind: kind.as_str(),
        candidate_count,
    });
    Some(id)
}

/// Report a `WebFetch` of `url`. Every live URL probe that retained the
/// candidate is marked used.
pub fn observe_url(url: &str) {
    observe(Kind::Url, normalize_url(url));
}

fn observe(kind: Kind, key: String) {
    if key.is_empty() {
        return;
    }
    let now = Instant::now();
    let mut records = Vec::new();
    {
        let mut pending = lock();
        pending.retain(|probe| now.duration_since(probe.created) < PROBE_TTL);
        for probe in pending.iter_mut() {
            if probe.kind != kind {
                continue;
            }
            for candidate in &mut probe.candidates {
                if candidate.used || candidate.key != key {
                    continue;
                }
                candidate.used = true;
                records.push(PosthocRecord {
                    timestamp: chrono::Utc::now().to_rfc3339(),
                    event: "posthoc",
                    probe_id: probe.id.clone(),
                    point: probe.point.as_str(),
                    kind: kind.as_str(),
                    identity: candidate.label.clone(),
                });
            }
        }
    }
    for record in records {
        append(&record);
    }
}

fn append<T: Serialize>(record: &T) {
    if let Err(error) = crate::decision::log::append(record) {
        crate::runtime::log_for_debugging(&format!(
            "DecisionProvider: cannot append post-hoc probe: {error}"
        ));
    }
}

/// `riff web reset`: a new conversation must not attribute old fetches to old decisions.
pub fn clear() {
    lock().clear();
}

fn normalize_url(raw: &str) -> String {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return String::new();
    }
    match url::Url::parse(trimmed) {
        Ok(mut parsed) => {
            // Fragments never reach the server and search providers disagree
            // on trailing slashes; both must not split one candidate in two.
            parsed.set_fragment(None);
            let path = parsed.path().to_string();
            if path != "/" && path.ends_with('/') {
                parsed.set_path(path.trim_end_matches('/'));
            }
            parsed.to_string()
        }
        Err(_) => trimmed.trim_end_matches('/').to_string(),
    }
}

#[cfg(test)]
pub fn pending_count() -> usize {
    lock().len()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_env::{TEST_ENV_LOCK, TempHome};
    use serde_json::Value;

    fn isolated_config(name: &str) -> (std::path::PathBuf, TempHome) {
        let home = TempHome::new(&format!("decision-probe-{name}"));
        clear();
        (home.path.clone(), home)
    }

    fn records() -> Vec<Value> {
        let text = std::fs::read_to_string(crate::decision::log::log_path()).unwrap_or_default();
        text.lines()
            .filter_map(|line| serde_json::from_str::<Value>(line).ok())
            .collect()
    }

    fn events(event: &str) -> Vec<Value> {
        records()
            .into_iter()
            .filter(|record| record["event"] == event)
            .collect()
    }

    #[test]
    fn url_matching_ignores_fragments_case_and_a_trailing_slash() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let (config, _env) = isolated_config("url");
        let id = register_urls(
            DecisionPoint::WebAnswers,
            ["https://Example.com/docs/page/?q=1#section".to_string()],
        )
        .expect("probe");
        observe_url("https://example.com/docs/page?q=1");

        let posthoc = events("posthoc");
        assert_eq!(posthoc.len(), 1);
        assert_eq!(posthoc[0]["probeId"], id);
        assert_eq!(posthoc[0]["kind"], "url");
        assert_eq!(
            posthoc[0]["identity"],
            "https://Example.com/docs/page/?q=1#section"
        );
        clear();
        let _ = std::fs::remove_dir_all(&config);
    }

    #[test]
    fn duplicate_candidates_are_kept_once_and_empty_registrations_log_nothing() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let (config, _env) = isolated_config("dedupe");
        let url = "https://example.com/a".to_string();
        assert!(register_urls(DecisionPoint::WebAnswers, []).is_none());
        assert!(
            register_urls(
                DecisionPoint::WebAnswers,
                [url.clone(), format!("{url}/#x")]
            )
            .is_some()
        );
        let probes = events("probe");
        assert_eq!(probes.len(), 1);
        assert_eq!(probes[0]["candidateCount"], 1);
        clear();
        let _ = std::fs::remove_dir_all(&config);
    }

    #[test]
    fn expired_probes_stop_matching_and_are_evicted() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let (config, _env) = isolated_config("ttl");
        let url = "https://example.com/ttl";
        {
            let mut pending = lock();
            pending.push(Probe {
                id: "expired".to_string(),
                point: DecisionPoint::WebAnswers,
                kind: Kind::Url,
                created: Instant::now()
                    .checked_sub(PROBE_TTL)
                    .expect("instant supports subtracting the TTL"),
                candidates: vec![Candidate {
                    key: normalize_url(url),
                    label: url.to_string(),
                    used: false,
                }],
            });
        }
        observe_url(url);
        assert!(
            events("posthoc").is_empty(),
            "an expired probe cannot match"
        );
        assert_eq!(pending_count(), 0, "observation evicts expired probes");
        clear();
        let _ = std::fs::remove_dir_all(&config);
    }

    #[test]
    fn the_oldest_probe_is_dropped_at_the_cap() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let (config, _env) = isolated_config("cap");
        let url = |index: usize| format!("https://example.com/cap/{index}");
        for index in 0..=MAX_PROBES {
            register_urls(DecisionPoint::WebAnswers, [url(index)]).expect("probe");
        }
        assert_eq!(pending_count(), MAX_PROBES);
        // The first registration was evicted, the newest one is still live.
        observe_url(&url(0));
        assert!(events("posthoc").is_empty());
        observe_url(&url(MAX_PROBES));
        let posthoc = events("posthoc");
        assert_eq!(posthoc.len(), 1);
        assert_eq!(posthoc[0]["identity"], url(MAX_PROBES));
        clear();
        let _ = std::fs::remove_dir_all(&config);
    }

    #[test]
    fn clear_forgets_pending_probes() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let (config, _env) = isolated_config("clear");
        register_urls(
            DecisionPoint::WebAnswers,
            ["https://example.com/a".to_string()],
        )
        .expect("probe");
        assert_eq!(pending_count(), 1);
        clear();
        assert_eq!(pending_count(), 0);
        observe_url("https://example.com/a");
        assert!(events("posthoc").is_empty());
        let _ = std::fs::remove_dir_all(&config);
    }
}
