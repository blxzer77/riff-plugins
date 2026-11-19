//! External web search/fetch services.
//!
//! Search and fetch share this module so SSRF policy, snapshots, provider
//! errors, session budgets, and deterministic result rendering cannot drift
//! between the two commands.

pub mod budget;
pub mod decision;
pub mod fallback;
pub mod fetcher;
pub mod host_guard;
pub mod provider_health;
pub mod providers;
pub mod read_page;
pub mod redact;
pub mod search;
pub mod snapshot;
#[cfg(test)]
pub(crate) mod test_support;

pub use fetcher::{FetchConfig, FetchError, FetchedPage, RedirectHop, fetch_url};

pub fn settings() -> Option<crate::settings::WebSettings> {
    crate::runtime::web_settings()
}

pub fn is_configured() -> bool {
    settings().is_some()
}

/// Providers that can actually be asked: enabled (a builtin the user did not
/// mention is enabled, external-search 5) and either holding a key or not
/// needing one (SearXNG). The hook uses this to decide whether intercepting
/// the host's built-in search would leave the agent without search (design 7.1).
pub fn usable_search_providers(web: &crate::settings::WebSettings) -> Vec<&'static str> {
    crate::settings::provider_names()
        .into_iter()
        .filter(|name| {
            let resolved = web.provider(name);
            resolved.enabled
                && (resolved.api_key_file.is_none() || providers::has_key(name, &resolved))
        })
        .collect()
}

/// The rerank client, or `None` when the service is not configured
/// (`web.search.rerank.service`) or web rerank is switched off.
pub fn rerank_client(web: &crate::settings::WebSettings) -> Option<crate::rerank::RerankClient> {
    let rerank = web.search().rerank();
    if !rerank.enabled() {
        return None;
    }
    let service = rerank.service.as_ref()?;
    service.url.as_ref()?;
    crate::rerank::RerankClient::from_settings(service, rerank.timeout_ms()).ok()
}

/// `riff web reset`: what nyan's `/clear` reset for web (design 2.4) — the
/// session budgets, provider cooldowns, the URL index, the last search's
/// candidates, and the Decision Provider's session budget and probes.
pub fn reset_session() {
    budget::reset();
    provider_health::reset();
    snapshot::clear_index();
    search::clear_candidates();
    crate::decision::reset_session_budget();
    crate::decision::probe::clear();
}
