//! `riff web decisions`: what the Decision Provider did, per point (design 5).
//!
//! From nyan's `/decision` (`src/commands/decision.rs`, nyan 3227f768e): reads
//! `$RIFF_HOME/decision/decisions.jsonl` and prints one row per point with its
//! sample count, outcomes, agreement counts and latency. It never calls the
//! backend and needs no configuration.
//!
//! Different from nyan: shadow answers have their own column instead of
//! counting as answered; the latency percentiles leave out rows that sent no
//! request (`latencyMs` 0, as for `backend_down`), which would otherwise drag
//! them toward zero; and fallbacks are broken down by reason, because a
//! fallback is often the model's answer rather than a failure
//! (`out_of_safe_set`, `low_confidence`).

use std::collections::{BTreeMap, BTreeSet};

use serde_json::Value;

use super::web::exit;
use crate::decision::DecisionPoint;

pub const HELP: &str = "\
Usage: riff web decisions [--point <name>]

Summarizes $RIFF_HOME/decision/decisions.jsonl, one row per decision point:
  n          decisions made (requests answered, shadowed or fallen back)
  answered   the answer was used
  shadow     the answer was recorded only; behaviour was the rule's
  fallback   the rule decided; see \"Fallbacks by reason\"
  agree / disagree   answers that matched / contradicted the rule
  p50 / p95  latency in ms of the decisions that sent a request
  probes     decisions that kept candidates for a later fetch
  used       probes whose candidate was fetched afterwards

Options:
      --point <name>   Only this point (web.answers, web.page_answers,
                       web.fetch_fallback, web.query_kind, web.prune)
  -h, --help           Show this help
";

/// `args` are the words after `decisions`.
pub fn run(args: &[String]) -> i32 {
    let filter = match parse(args) {
        Ok(Some(filter)) => filter,
        Ok(None) => {
            print!("{HELP}");
            return 0;
        }
        Err(message) => {
            eprintln!("riff web decisions: {message}\nRun `riff web decisions --help` for usage.");
            return exit::USAGE;
        }
    };
    match summarize(filter) {
        Ok(output) => {
            print!("{output}");
            0
        }
        Err(message) => {
            eprintln!("riff web decisions: {message}");
            exit::OTHER
        }
    }
}

/// `Ok(None)` is `--help`; `Ok(Some(None))` is every point.
fn parse(args: &[String]) -> Result<Option<Option<DecisionPoint>>, String> {
    let mut filter = None;
    let mut index = 0;
    while index < args.len() {
        let arg = args[index].as_str();
        index += 1;
        let name = match arg.split_once('=') {
            Some(("--point", value)) => value.to_string(),
            _ => match arg {
                "-h" | "--help" => return Ok(None),
                "--point" => {
                    let value = args.get(index).ok_or("--point requires a value")?;
                    index += 1;
                    value.clone()
                }
                _ if arg.starts_with('-') => return Err(format!("unknown option `{arg}`")),
                _ => return Err(format!("unexpected argument `{arg}`")),
            },
        };
        let point = DecisionPoint::from_str(name.trim()).ok_or_else(|| {
            let known = DecisionPoint::ALL
                .iter()
                .map(|point| point.as_str())
                .collect::<Vec<_>>()
                .join(", ");
            format!("unknown point `{name}`: expected one of {known}")
        })?;
        filter = Some(point);
    }
    Ok(Some(filter))
}

#[derive(Default)]
struct PointStats {
    samples: usize,
    answered: usize,
    shadow: usize,
    fallback: usize,
    fallback_reasons: BTreeMap<String, usize>,
    agree: usize,
    disagree: usize,
    /// `event: "probe"` rows: decisions that retained candidates.
    probes: usize,
    /// Probe ids that a later fetch matched (`event: "posthoc"`).
    used_probes: BTreeSet<String>,
    /// Of the decisions that sent a request.
    latencies: Vec<u64>,
}

impl PointStats {
    fn percentile(&mut self, percentile: f64) -> u64 {
        if self.latencies.is_empty() {
            return 0;
        }
        self.latencies.sort_unstable();
        let index = ((self.latencies.len() as f64 - 1.0) * percentile).round() as usize;
        self.latencies[index]
    }
}

fn summarize(filter: Option<DecisionPoint>) -> Result<String, String> {
    let path = crate::decision::log::log_path();
    let content = match std::fs::read_to_string(&path) {
        Ok(content) => content,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(format!(
                "No decision records yet (log: {}).\n",
                path.display()
            ));
        }
        Err(error) => return Err(format!("cannot read {}: {error}", path.display())),
    };

    let mut by_point = BTreeMap::<String, PointStats>::new();
    for line in content.lines() {
        let Ok(record) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        let Some(point) = record.get("point").and_then(Value::as_str) else {
            continue;
        };
        if filter.is_some_and(|filter| filter.as_str() != point) {
            continue;
        }
        let stats = by_point.entry(point.to_string()).or_default();
        // Post-hoc rows share the file but are not decisions: counting them as
        // samples would double-count and lower every latency percentile.
        match record.get("event").and_then(Value::as_str) {
            Some("probe") => {
                stats.probes += 1;
                continue;
            }
            Some("posthoc") => {
                if let Some(id) = record.get("probeId").and_then(Value::as_str) {
                    stats.used_probes.insert(id.to_string());
                }
                continue;
            }
            Some(_) => continue,
            None => {}
        }
        stats.samples += 1;
        match record.get("outcome").and_then(Value::as_str) {
            Some("fallback") => {
                stats.fallback += 1;
                let reason = record
                    .get("fallbackReason")
                    .and_then(Value::as_str)
                    .unwrap_or("unknown");
                *stats
                    .fallback_reasons
                    .entry(reason.to_string())
                    .or_default() += 1;
            }
            Some("shadow") => stats.shadow += 1,
            _ => stats.answered += 1,
        }
        if let Some(latency) = record.get("latencyMs").and_then(Value::as_u64)
            && latency > 0
        {
            stats.latencies.push(latency);
        }
        if let Some(agree) = record
            .get("detail")
            .and_then(|detail| detail.get("agrees"))
            .and_then(Value::as_bool)
        {
            if agree {
                stats.agree += 1;
            } else {
                stats.disagree += 1;
            }
        }
        let agreed = record.get("agreedCount").and_then(Value::as_u64);
        let differed = record.get("differedCount").and_then(Value::as_u64);
        if agreed.is_some() || differed.is_some() {
            stats.agree += agreed.unwrap_or(0) as usize;
            stats.disagree += differed.unwrap_or(0) as usize;
        }
    }

    if by_point.is_empty() {
        return Ok(format!(
            "No decision records for {} (log: {}).\n",
            filter.map_or("any point", DecisionPoint::as_str),
            path.display()
        ));
    }

    let mut output = format!("Decision log: {}\n\n", path.display());
    output.push_str(
        "point                  n answered shadow fallback agree disagree   p50   p95 probes  used\n",
    );
    let mut reasons = String::new();
    for (point, mut stats) in by_point {
        let p50 = stats.percentile(0.50);
        let p95 = stats.percentile(0.95);
        output.push_str(&format!(
            "{point:<20} {:>3} {:>8} {:>6} {:>8} {:>5} {:>8} {:>5} {:>5} {:>6} {:>5}\n",
            stats.samples,
            stats.answered,
            stats.shadow,
            stats.fallback,
            stats.agree,
            stats.disagree,
            p50,
            p95,
            stats.probes,
            stats.used_probes.len(),
        ));
        if !stats.fallback_reasons.is_empty() {
            let list = stats
                .fallback_reasons
                .iter()
                .map(|(reason, count)| format!("{reason} {count}"))
                .collect::<Vec<_>>()
                .join(", ");
            reasons.push_str(&format!("{point:<20} {list}\n"));
        }
    }
    if !reasons.is_empty() {
        output.push_str("\nFallbacks by reason:\n");
        output.push_str(&reasons);
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_env::{HomeGuard, TEST_ENV_LOCK};

    fn args(words: &[&str]) -> Vec<String> {
        words.iter().map(|word| (*word).to_string()).collect()
    }

    /// A `$RIFF_HOME` holding this log; keep the guard alive while reading.
    fn home_with_log(name: &str, lines: &[&str]) -> HomeGuard {
        let root = crate::test_env::scratch_dir(name);
        std::fs::create_dir_all(root.join("decision")).unwrap();
        let mut log = lines.join("\n");
        log.push('\n');
        std::fs::write(root.join("decision/decisions.jsonl"), log).unwrap();
        HomeGuard::set(&root)
    }

    fn row<'a>(text: &'a str, point: &str) -> Vec<&'a str> {
        text.lines()
            .find(|line| line.starts_with(point))
            .unwrap_or_else(|| panic!("no row for {point} in:\n{text}"))
            .split_whitespace()
            .collect()
    }

    #[test]
    fn groups_points_counts_agreement_and_filters_by_point() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let _home = home_with_log(
            "decisions-groups",
            &[
                r#"{"point":"web.query_kind","outcome":"answered","latencyMs":10,"detail":{"agrees":true}}"#,
                r#"{"point":"web.query_kind","outcome":"fallback","fallbackReason":"timeout","latencyMs":30,"detail":{"agrees":false}}"#,
                r#"{"point":"web.answers","outcome":"answered","latencyMs":20,"agreedCount":2,"differedCount":1}"#,
                "not json",
            ],
        );

        let text = summarize(None).unwrap();
        // point n answered shadow fallback agree disagree p50 p95 probes used
        assert_eq!(
            row(&text, "web.query_kind"),
            [
                "web.query_kind",
                "2",
                "1",
                "0",
                "1",
                "1",
                "1",
                "30",
                "30",
                "0",
                "0"
            ]
        );
        assert_eq!(
            row(&text, "web.answers"),
            [
                "web.answers",
                "1",
                "1",
                "0",
                "0",
                "2",
                "1",
                "20",
                "20",
                "0",
                "0"
            ]
        );

        let only = summarize(Some(DecisionPoint::WebQueryKind)).unwrap();
        assert!(only.contains("web.query_kind"));
        assert!(!only.contains("web.answers"));
        let none = summarize(Some(DecisionPoint::WebPrune)).unwrap();
        assert!(
            none.starts_with("No decision records for web.prune"),
            "{none}"
        );
    }

    #[test]
    fn probe_rows_are_not_samples_and_used_counts_distinct_probes() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let _home = home_with_log(
            "decisions-probes",
            &[
                r#"{"point":"web.answers","outcome":"answered","latencyMs":40,"detail":{"agrees":true}}"#,
                r#"{"point":"web.answers","event":"probe","probeId":"p1","kind":"url","candidateCount":2}"#,
                r#"{"point":"web.answers","event":"probe","probeId":"p2","kind":"url","candidateCount":1}"#,
                r#"{"point":"web.answers","event":"posthoc","probeId":"p1","kind":"url","identity":"https://a.example/"}"#,
                r#"{"point":"web.answers","event":"posthoc","probeId":"p1","kind":"url","identity":"https://b.example/"}"#,
            ],
        );

        let text = summarize(Some(DecisionPoint::WebAnswers)).unwrap();
        let columns = row(&text, "web.answers");
        assert_eq!(columns[1], "1", "probe/posthoc rows are not samples");
        assert_eq!(columns[9], "2", "two retained decisions");
        assert_eq!(columns[10], "1", "one probe matched a later use");
    }

    #[test]
    fn shadow_is_its_own_column_and_fallbacks_are_listed_by_reason() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let _home = home_with_log(
            "decisions-reasons",
            &[
                r#"{"point":"web.prune","outcome":"shadow","latencyMs":900}"#,
                r#"{"point":"web.prune","outcome":"fallback","fallbackReason":"backend_down","latencyMs":0}"#,
                r#"{"point":"web.prune","outcome":"fallback","fallbackReason":"backend_down","latencyMs":0}"#,
                r#"{"point":"web.prune","outcome":"fallback","fallbackReason":"timeout","latencyMs":3001}"#,
                r#"{"point":"web.fetch_fallback","outcome":"fallback","fallbackReason":"out_of_safe_set","latencyMs":700}"#,
            ],
        );

        let text = summarize(None).unwrap();
        // The two rows that sent no request (0 ms) are not in the percentiles.
        assert_eq!(
            row(&text, "web.prune"),
            [
                "web.prune",
                "4",
                "0",
                "1",
                "3",
                "0",
                "0",
                "3001",
                "3001",
                "0",
                "0"
            ]
        );
        let reasons = text.split("Fallbacks by reason:\n").nth(1).unwrap();
        assert_eq!(
            reasons,
            "web.fetch_fallback   out_of_safe_set 1\nweb.prune            backend_down 2, timeout 1\n"
        );
    }

    #[test]
    fn a_log_without_fallbacks_has_no_reason_section_and_no_log_says_so() {
        let _lock = TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        {
            let _home = home_with_log(
                "decisions-clean",
                &[r#"{"point":"web.query_kind","outcome":"answered","latencyMs":10}"#],
            );
            assert!(!summarize(None).unwrap().contains("Fallbacks by reason"));
        }
        let empty = crate::test_env::scratch_dir("decisions-none");
        let _home = HomeGuard::set(&empty);
        let text = summarize(None).unwrap();
        assert!(text.starts_with("No decision records yet (log: "), "{text}");
    }

    #[test]
    fn the_point_filter_takes_only_known_points() {
        assert_eq!(parse(&args(&[])), Ok(Some(None)));
        assert_eq!(
            parse(&args(&["--point", "web.prune"])),
            Ok(Some(Some(DecisionPoint::WebPrune)))
        );
        assert_eq!(
            parse(&args(&["--point=web.answers"])),
            Ok(Some(Some(DecisionPoint::WebAnswers)))
        );
        assert_eq!(parse(&args(&["--help"])), Ok(None));
        let unknown = parse(&args(&["--point", "memory.type"])).unwrap_err();
        assert!(
            unknown.contains("unknown point `memory.type`") && unknown.contains("web.query_kind"),
            "{unknown}"
        );
        assert!(parse(&args(&["--point"])).is_err());
        assert!(parse(&args(&["--json"])).is_err());
        assert!(parse(&args(&["web.prune"])).is_err());
    }
}
