//! riff configuration: `$RIFF_HOME/config.json`.
//!
//! The `web`, `decision` and rerank sections are nyan's `settings.nyan.web`,
//! `settings.nyan.decision` and `settings.nyan.retrieval.rerank` types (nyan
//! 3227f768e, `utils/settings/nyan.rs`). Every field is `Option` and the
//! design defaults live in accessors, as in nyan, so "unset" stays
//! distinguishable from "set to the default".

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════
// Rerank
// ════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct RerankSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_n: Option<u32>,
    /// Characters of each document sent to the reranker. The caller's snippet
    /// is not shortened. Default stays inside the service's 4096-token limit
    /// at one token per character, with room for the template and the query.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_document_chars: Option<u32>,
}

impl RerankSettings {
    pub fn url(&self) -> &str {
        self.url.as_deref().unwrap_or("http://10.144.0.11:8091")
    }
    pub fn model(&self) -> &str {
        self.model.as_deref().unwrap_or("qwen3-reranker-0.6b")
    }
    pub fn top_n(&self) -> u32 {
        // Eval 2026-11-01: top_n=10 beat 20 on Hit@5 and MRR at about 1/4 the latency.
        self.top_n.unwrap_or(10)
    }
    pub fn max_document_chars(&self) -> u32 {
        self.max_document_chars.unwrap_or(3_000)
    }
}

// ════════════════════════════════════════════════════════════
// Web (external search)
// ════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct WebSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub providers: Option<BTreeMap<String, ProviderConfig>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub search: Option<WebSearchSettings>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fetch: Option<WebFetchSettings>,
    /// Provider fallback order for WebFetch (external search 4.6).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fetch_fallback: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fetch_via: Option<FetchVia>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub allow_hosts: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deny_hosts: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub allow_ports: Option<Vec<u16>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_bytes: Option<u64>,
    /// Unicode scalars (external search 4.4); hard cap 40000.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_return_chars: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub snapshot_retention_days: Option<u32>,
    /// Intercept the host agent's built-in web tools (design 7.1).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub intercept_builtin: Option<bool>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct ProviderConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_key_file: Option<String>,
    /// Test/mocking seam; absent means the provider's official URL.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub base_url: Option<String>,
    /// SearXNG only: the deployed instance URL.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_calls_per_session: Option<u32>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct WebSearchSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recall_depth: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fusion_keep: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub domain_cap: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rrf_k: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub per_provider_deadline_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deadline_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_per_session: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_concurrent_searches: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rerank: Option<WebRerankSettings>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct WebRerankSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
    /// The rerank service (`/score`). nyan kept it under
    /// `nyan.retrieval.rerank`; riff has no retrieval (design 3.2). Absent
    /// means web rerank is unavailable and search keeps the RRF order.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub service: Option<RerankSettings>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timeout_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub snippet_chars: Option<u32>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct WebFetchSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timeout_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub connect_timeout_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_redirects: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_per_session: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_bytes_per_session: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fallback_deadline_ms: Option<u64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum FetchVia {
    Proxy,
    Direct,
}

/// Built-in provider defaults from external-search 2.2 / 5.
pub struct ProviderDefaults {
    pub name: &'static str,
    pub api_key_file: Option<&'static str>,
    pub max_calls_per_session: Option<u32>,
    pub url: Option<&'static str>,
}

pub const BUILTIN_PROVIDERS: &[ProviderDefaults] = &[
    ProviderDefaults {
        name: "anysearch",
        api_key_file: Some("$RIFF_HOME/keys/anysearch"),
        max_calls_per_session: Some(40),
        url: None,
    },
    ProviderDefaults {
        name: "brave",
        api_key_file: Some("$RIFF_HOME/keys/brave"),
        max_calls_per_session: Some(40),
        url: None,
    },
    ProviderDefaults {
        name: "deepseek",
        api_key_file: Some("$RIFF_HOME/keys/deepseek"),
        max_calls_per_session: Some(60),
        url: None,
    },
    ProviderDefaults {
        name: "exa",
        api_key_file: Some("$RIFF_HOME/keys/exa"),
        max_calls_per_session: Some(30),
        url: None,
    },
    ProviderDefaults {
        name: "firecrawl",
        api_key_file: Some("$RIFF_HOME/keys/firecrawl"),
        max_calls_per_session: Some(20),
        url: None,
    },
    ProviderDefaults {
        name: "tavily",
        api_key_file: Some("$RIFF_HOME/keys/tavily"),
        max_calls_per_session: Some(20),
        url: None,
    },
    ProviderDefaults {
        name: "searxng",
        api_key_file: None,
        max_calls_per_session: None,
        url: Some("http://10.144.0.3:8454"),
    },
];

pub fn provider_names() -> Vec<&'static str> {
    BUILTIN_PROVIDERS.iter().map(|p| p.name).collect()
}

#[derive(Debug, Clone, PartialEq)]
pub struct ResolvedProvider {
    pub enabled: bool,
    pub api_key_file: Option<String>,
    pub base_url: Option<String>,
    pub url: Option<String>,
    pub max_calls_per_session: Option<u32>,
}

impl WebSettings {
    pub fn provider(&self, name: &str) -> ResolvedProvider {
        let builtin = BUILTIN_PROVIDERS.iter().find(|p| p.name == name);
        let config = self
            .providers
            .as_ref()
            .and_then(|providers| providers.get(name));
        ResolvedProvider {
            enabled: config.and_then(|c| c.enabled).unwrap_or(true),
            api_key_file: config
                .and_then(|c| c.api_key_file.clone())
                .or_else(|| builtin.and_then(|b| b.api_key_file.map(str::to_owned))),
            base_url: config.and_then(|c| c.base_url.clone()),
            url: config
                .and_then(|c| c.url.clone())
                .or_else(|| builtin.and_then(|b| b.url.map(str::to_owned))),
            max_calls_per_session: config
                .and_then(|c| c.max_calls_per_session)
                .or_else(|| builtin.and_then(|b| b.max_calls_per_session)),
        }
    }

    pub fn search(&self) -> WebSearchSettings {
        self.search.clone().unwrap_or_default()
    }
    pub fn fetch(&self) -> WebFetchSettings {
        self.fetch.clone().unwrap_or_default()
    }
    pub fn fetch_via(&self) -> FetchVia {
        self.fetch_via.unwrap_or(FetchVia::Proxy)
    }
    pub fn fallback_order(&self) -> Vec<String> {
        self.fetch_fallback.clone().unwrap_or_else(|| {
            ["firecrawl", "anysearch", "exa", "deepseek", "tavily"]
                .into_iter()
                .map(str::to_owned)
                .collect()
        })
    }
    pub fn allow_hosts(&self) -> &[String] {
        self.allow_hosts.as_deref().unwrap_or(&[])
    }
    pub fn deny_hosts(&self) -> &[String] {
        self.deny_hosts.as_deref().unwrap_or(&[])
    }
    pub fn allow_ports(&self) -> &[u16] {
        self.allow_ports.as_deref().unwrap_or(&[])
    }
    pub fn max_bytes(&self) -> u64 {
        self.max_bytes.unwrap_or(5_242_880)
    }
    pub fn max_return_chars(&self) -> u32 {
        self.max_return_chars.unwrap_or(20_000).min(40_000)
    }
    pub fn snapshot_retention_days(&self) -> u32 {
        self.snapshot_retention_days.unwrap_or(30)
    }
    pub fn intercept_builtin(&self) -> bool {
        self.intercept_builtin.unwrap_or(true)
    }
}

impl WebSearchSettings {
    pub fn recall_depth(&self) -> u32 {
        self.recall_depth.unwrap_or(20)
    }
    pub fn fusion_keep(&self) -> u32 {
        self.fusion_keep.unwrap_or(30)
    }
    pub fn domain_cap(&self) -> u32 {
        self.domain_cap.unwrap_or(3)
    }
    pub fn rrf_k(&self) -> u32 {
        self.rrf_k.unwrap_or(60)
    }
    pub fn per_provider_deadline_ms(&self) -> u64 {
        self.per_provider_deadline_ms.unwrap_or(8_000)
    }
    pub fn deadline_ms(&self) -> u64 {
        self.deadline_ms.unwrap_or(10_000)
    }
    pub fn max_per_session(&self) -> u32 {
        self.max_per_session.unwrap_or(40)
    }
    pub fn max_concurrent_searches(&self) -> u32 {
        self.max_concurrent_searches.unwrap_or(2)
    }
    pub fn rerank(&self) -> WebRerankSettings {
        self.rerank.clone().unwrap_or_default()
    }
}

impl WebRerankSettings {
    pub fn enabled(&self) -> bool {
        self.enabled.unwrap_or(true)
    }
    pub fn timeout_ms(&self) -> u64 {
        self.timeout_ms.unwrap_or(2_000)
    }
    pub fn snippet_chars(&self) -> u32 {
        self.snippet_chars.unwrap_or(500)
    }
}

impl WebFetchSettings {
    pub fn timeout_ms(&self) -> u64 {
        self.timeout_ms.unwrap_or(10_000)
    }
    pub fn connect_timeout_ms(&self) -> u64 {
        self.connect_timeout_ms.unwrap_or(5_000)
    }
    pub fn max_redirects(&self) -> u32 {
        self.max_redirects.unwrap_or(5)
    }
    pub fn max_per_session(&self) -> u32 {
        self.max_per_session.unwrap_or(60)
    }
    pub fn max_bytes_per_session(&self) -> u64 {
        self.max_bytes_per_session.unwrap_or(104_857_600)
    }
    pub fn fallback_deadline_ms(&self) -> u64 {
        self.fallback_deadline_ms.unwrap_or(30_000)
    }
}

// ════════════════════════════════════════════════════════════
// Decision Provider
// ════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct DecisionSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub emrank: Option<EmrankSettings>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deadline_ms: Option<DecisionDeadlineSettings>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_batch: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_calls_per_session: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_input_tokens_per_session: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub points: Option<BTreeMap<String, DecisionPointConfig>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub log_retention_days: Option<u32>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct EmrankSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_key_file: Option<String>,
    /// `fast` / `accurate` → model ID.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub models: Option<BTreeMap<String, String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pool_idle_timeout_ms: Option<u64>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct DecisionDeadlineSettings {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub critical: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub background: Option<u64>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
pub struct DecisionPointConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mode: Option<DecisionMode>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<DecisionModel>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub min_confidence: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_prob: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub keep_at_least: Option<u32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DecisionMode {
    Off,
    Shadow,
    Active,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DecisionModel {
    Fast,
    Accurate,
}

/// Built-in mode/model/threshold per decision point (decision-provider 4 /
/// 8). The table is the source of truth for both the settings schema's key
/// set and the decision module's closed enum.
pub struct BuiltinDecisionPoint {
    pub name: &'static str,
    pub mode: DecisionMode,
    pub model: DecisionModel,
    pub min_confidence: f64,
    pub max_prob: Option<f64>,
    pub keep_at_least: Option<u32>,
}

pub const BUILTIN_DECISION_POINTS: &[BuiltinDecisionPoint] = &[
    BuiltinDecisionPoint {
        name: "web.answers",
        mode: DecisionMode::Active,
        model: DecisionModel::Fast,
        min_confidence: 0.6,
        max_prob: None,
        keep_at_least: None,
    },
    BuiltinDecisionPoint {
        name: "web.page_answers",
        mode: DecisionMode::Active,
        model: DecisionModel::Fast,
        min_confidence: 0.7,
        max_prob: None,
        keep_at_least: None,
    },
    BuiltinDecisionPoint {
        name: "web.fetch_fallback",
        mode: DecisionMode::Active,
        model: DecisionModel::Accurate,
        min_confidence: 0.8,
        max_prob: None,
        keep_at_least: None,
    },
    BuiltinDecisionPoint {
        name: "web.query_kind",
        mode: DecisionMode::Active,
        model: DecisionModel::Fast,
        min_confidence: 0.7,
        max_prob: None,
        keep_at_least: None,
    },
    BuiltinDecisionPoint {
        name: "web.prune",
        mode: DecisionMode::Shadow,
        model: DecisionModel::Fast,
        min_confidence: 0.7,
        max_prob: Some(0.05),
        keep_at_least: Some(5),
    },
];

pub fn decision_point_names() -> Vec<&'static str> {
    BUILTIN_DECISION_POINTS.iter().map(|p| p.name).collect()
}

#[derive(Debug, Clone, PartialEq)]
pub struct ResolvedDecisionPoint {
    pub name: String,
    pub mode: DecisionMode,
    pub model: DecisionModel,
    pub min_confidence: f64,
    pub max_prob: Option<f64>,
    pub keep_at_least: Option<u32>,
}

impl DecisionSettings {
    pub fn enabled(&self) -> bool {
        self.enabled.unwrap_or(true)
    }
    pub fn emrank(&self) -> EmrankSettings {
        self.emrank.clone().unwrap_or_default()
    }
    pub fn max_batch(&self) -> u32 {
        self.max_batch.unwrap_or(30)
    }
    pub fn max_calls_per_session(&self) -> u32 {
        self.max_calls_per_session.unwrap_or(600)
    }
    pub fn max_input_tokens_per_session(&self) -> u64 {
        self.max_input_tokens_per_session.unwrap_or(3_000_000)
    }
    pub fn log_retention_days(&self) -> u32 {
        self.log_retention_days.unwrap_or(30)
    }
    pub fn deadline(&self, critical: bool) -> std::time::Duration {
        let deadlines = self.deadline_ms.clone().unwrap_or_default();
        let millis = if critical {
            deadlines.critical.unwrap_or(800)
        } else {
            deadlines.background.unwrap_or(2_000)
        };
        std::time::Duration::from_millis(millis)
    }
    /// Built-in defaults overlaid with the user's per-point config.
    pub fn resolved_point(&self, name: &str) -> Option<ResolvedDecisionPoint> {
        let builtin = BUILTIN_DECISION_POINTS.iter().find(|p| p.name == name)?;
        let config = self.points.as_ref().and_then(|points| points.get(name));
        Some(ResolvedDecisionPoint {
            name: name.to_string(),
            mode: config.and_then(|c| c.mode).unwrap_or(builtin.mode),
            model: config.and_then(|c| c.model).unwrap_or(builtin.model),
            min_confidence: config
                .and_then(|c| c.min_confidence)
                .unwrap_or(builtin.min_confidence),
            max_prob: config.and_then(|c| c.max_prob).or(builtin.max_prob),
            keep_at_least: config
                .and_then(|c| c.keep_at_least)
                .or(builtin.keep_at_least),
        })
    }
    /// Every web point sits on the critical path (decision-provider 5.2).
    pub fn is_critical_point(name: &str) -> bool {
        name.starts_with("web.")
    }
}

impl EmrankSettings {
    pub fn url(&self) -> &str {
        self.url
            .as_deref()
            .unwrap_or("https://emrank.tech/v1/decisions")
    }
    pub fn api_key_file(&self) -> &str {
        self.api_key_file
            .as_deref()
            .unwrap_or("$RIFF_HOME/keys/emrank")
    }
    pub fn model_id(&self, alias: DecisionModel) -> String {
        let fallback = match alias {
            // `typesafe/jev-1.14.0` (decision-provider 5.1) is no longer
            // listed by EMRank; clef is the one decision model that answered
            // both point shapes correctly (design 5, 2026-11-19).
            DecisionModel::Fast => "cloudflare/clef",
            DecisionModel::Accurate => "cloudflare/clef",
        };
        let key = match alias {
            DecisionModel::Fast => "fast",
            DecisionModel::Accurate => "accurate",
        };
        self.models
            .as_ref()
            .and_then(|models| models.get(key))
            .cloned()
            .unwrap_or_else(|| fallback.to_string())
    }
    pub fn pool_idle_timeout_ms(&self) -> u64 {
        self.pool_idle_timeout_ms.unwrap_or(90_000)
    }
}

// ════════════════════════════════════════════════════════════
// Config file
// ════════════════════════════════════════════════════════════

/// `$RIFF_HOME/config.json`. Unknown keys are rejected so a typo does not
/// silently fall back to a default (nyan's settings schema was strict too).
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Config {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub web: Option<WebSettings>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub decision: Option<DecisionSettings>,
}
