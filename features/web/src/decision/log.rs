//! The one decision-provider JSONL log (decision-provider §7).
//!
//! Every point appends one JSON object per decision to
//! `$RIFF_HOME/decision/decisions.jsonl`. Records are self-describing:
//! each carries `point`, `outcome` and, where applicable, `mode` and latency,
//! plus the calling `agent` and `session` (design 5), so the log can be
//! aggregated without knowing point-specific payloads.

use std::path::PathBuf;
use std::sync::{OnceLock, RwLock};

use serde::Serialize;
use serde_json::{Value, json};

use crate::decision::{DecisionOutcome, DecisionPoint, FallbackReason};

/// `$RIFF_HOME/decision`.
pub fn log_dir() -> PathBuf {
    crate::home::riff_home().join("decision")
}

/// `$RIFF_HOME/decision/decisions.jsonl`.
pub fn log_path() -> PathBuf {
    log_dir().join("decisions.jsonl")
}

/// Append one record as a single JSON line.
pub fn append<T: Serialize>(record: &T) -> std::io::Result<()> {
    let path = log_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)?;
    let line = serde_json::to_string(record)
        .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?;
    use std::io::Write;
    writeln!(file, "{line}")
}

#[derive(Clone, Debug, Default)]
struct Context {
    agent: Option<String>,
    session: Option<String>,
}

fn context() -> &'static RwLock<Context> {
    static CELL: OnceLock<RwLock<Context>> = OnceLock::new();
    CELL.get_or_init(|| RwLock::new(Context::default()))
}

/// Who is deciding: the `--agent` name and the session id, stamped on every
/// record this process writes. Unset fields are written as `unknown` / absent.
pub fn set_context(agent: Option<&str>, session: Option<&str>) {
    *context().write().unwrap_or_else(|e| e.into_inner()) = Context {
        agent: agent.map(str::to_string),
        session: session.map(str::to_string),
    };
}

/// The record written by every web seam.
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct OutcomeRecord<'a> {
    timestamp: String,
    agent: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    session: Option<String>,
    point: &'a str,
    model: &'a str,
    latency_ms: u64,
    /// `answered`, `shadow`, or `fallback`.
    outcome: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    fallback_reason: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    request_id: Option<&'a str>,
    state_sha256: &'a str,
    state_bytes: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    agreed_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    differed_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    detail: Option<Value>,
}

/// Append one decision made by a retrieval or web seam.
///
/// `off` and globally-disabled points never reach a backend, so they are not
/// decisions and are not logged. A shadow answer (`reason == Shadow`) is
/// recorded as `outcome: "shadow"`: the request happened, the behaviour did
/// not change.
pub fn log_outcome(point: DecisionPoint, outcome: &DecisionOutcome) {
    let receipt = outcome.receipt();
    let (result, fallback_reason) = match outcome {
        DecisionOutcome::Answered { .. } => ("answered", None),
        DecisionOutcome::Fallback {
            reason: FallbackReason::Shadow,
            ..
        } => ("shadow", None),
        DecisionOutcome::Fallback {
            reason: FallbackReason::Disabled,
            ..
        } => return,
        DecisionOutcome::Fallback { reason, .. } => ("fallback", Some(reason.as_str())),
    };
    let total = receipt.agreement.len();
    let agreed = receipt.agreement.values().filter(|agrees| **agrees).count();
    // `/decision` reads `detail.agrees` and `agreedCount`/`differedCount`
    // independently and adds both. Emit exactly one shape: the detail for a
    // single question, the counts for several. Emitting both made every
    // single-question point count the same agreement twice.
    let detail = match total {
        0 => None,
        1 => receipt
            .agreement
            .values()
            .next()
            .map(|agrees| json!({"agrees": agrees})),
        _ => None,
    };
    let context = context().read().unwrap_or_else(|e| e.into_inner()).clone();
    let record = OutcomeRecord {
        timestamp: chrono::Utc::now().to_rfc3339(),
        agent: context.agent.unwrap_or_else(|| "unknown".to_string()),
        session: context.session,
        point: point.as_str(),
        model: &receipt.model,
        latency_ms: receipt.latency.as_millis().min(u128::from(u64::MAX)) as u64,
        outcome: result,
        fallback_reason,
        request_id: receipt.request_id.as_deref(),
        state_sha256: &receipt.state.sha256,
        state_bytes: receipt.state.bytes,
        agreed_count: (total > 1).then_some(agreed),
        differed_count: (total > 1).then_some(total - agreed),
        detail,
    };
    if let Err(error) = append(&record) {
        crate::runtime::log_for_debugging(&format!(
            "DecisionProvider: cannot append {}: {error}",
            point.as_str()
        ));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::decision::{Answer, Receipt};
    use crate::test_env::TEST_ENV_LOCK;

    fn outcome(answer: Option<Answer>, agreement: bool) -> DecisionOutcome {
        let mut receipt = Receipt {
            point: "web.answers".into(),
            backend: "mock".into(),
            model: "mock-model".into(),
            latency: std::time::Duration::from_millis(42),
            request_id: Some("req_1".into()),
            state: crate::decision::StateDigest {
                sha256: "abc".into(),
                bytes: 12,
            },
            ..Default::default()
        };
        receipt.agreement.insert("q".into(), agreement);
        match answer {
            Some(answer) => {
                let mut answers = std::collections::BTreeMap::new();
                answers.insert("q".into(), answer);
                receipt.answers = answers.clone();
                DecisionOutcome::Answered { answers, receipt }
            }
            None => DecisionOutcome::Fallback {
                reason: FallbackReason::Timeout,
                receipt,
            },
        }
    }

    #[test]
    fn logs_answers_fallbacks_and_shadow_outcomes_with_agreement() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let dir = crate::test_env::scratch_root().join(format!(
            "riff-decision-log-{}",
            uuid::Uuid::new_v4().simple()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let _env = crate::test_env::HomeGuard::set(&dir);

        log_outcome(
            DecisionPoint::WebAnswers,
            &outcome(Some(Answer::Noul { probability: 0.9 }), true),
        );
        log_outcome(DecisionPoint::WebQueryKind, &outcome(None, false));
        let mut shadow = outcome(Some(Answer::Noul { probability: 0.9 }), false);
        if let DecisionOutcome::Answered { receipt, .. } = shadow {
            shadow = DecisionOutcome::Fallback {
                reason: FallbackReason::Shadow,
                receipt,
            };
        }
        log_outcome(DecisionPoint::WebPrune, &shadow);
        let mut multi = outcome(Some(Answer::Noul { probability: 0.9 }), true);
        if let DecisionOutcome::Answered { receipt, .. } = &mut multi {
            receipt.agreement.insert("q2".into(), false);
        }
        log_outcome(DecisionPoint::WebPageAnswers, &multi);

        let text = std::fs::read_to_string(log_path()).unwrap();
        let records = text
            .lines()
            .map(|line| serde_json::from_str::<Value>(line).unwrap())
            .collect::<Vec<_>>();
        assert_eq!(records.len(), 4);
        assert_eq!(records[0]["outcome"], "answered");
        // One question is described by `detail` alone; also emitting counts
        // would make `/decision` add the same agreement twice.
        assert_eq!(records[0]["detail"]["agrees"], true);
        assert!(records[0].get("agreedCount").is_none());
        assert!(records[0].get("differedCount").is_none());
        assert_eq!(records[1]["outcome"], "fallback");
        assert_eq!(records[1]["fallbackReason"], "timeout");
        assert_eq!(records[2]["outcome"], "shadow");
        assert!(records[2].get("fallbackReason").is_none());
        // Several questions are described by the counts, with no detail.
        assert_eq!(records[3]["agreedCount"], 1);
        assert_eq!(records[3]["differedCount"], 1);
        assert!(records[3].get("detail").is_none());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn disabled_decisions_are_not_logged() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let dir = crate::test_env::scratch_root().join(format!(
            "riff-decision-log-off-{}",
            uuid::Uuid::new_v4().simple()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let _env = crate::test_env::HomeGuard::set(&dir);
        log_outcome(
            DecisionPoint::WebAnswers,
            &DecisionOutcome::Fallback {
                reason: FallbackReason::Disabled,
                receipt: Receipt::default(),
            },
        );
        assert!(!log_path().exists());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
