//! The verbatim page read behind `riff web fetch`: snapshot lookup, budgeted
//! fresh fetch with provider fallback, and range selection.
//!
//! From nyan's WebFetch tool (`tools/web_fetch_tool/mod.rs` 125-266, the part
//! shared with `nyan web fetch`); the tool wrapper and `prompt` extraction are
//! not carried over (design 4.4).

/// One direct-fetch + provider-fallback chain, with the mock seam when a test
/// supplies its own fetcher configuration.
async fn fetch_once(
    url: &str,
    abort_controller: &crate::runtime::AbortController,
    web: &crate::settings::WebSettings,
    config: Option<&crate::web::fetcher::FetchConfig>,
) -> Result<crate::web::fallback::FetchChainResult, crate::web::fallback::FetchChainFailure> {
    let config = match config {
        Some(config) => config.clone(),
        None => crate::web::fetcher::FetchConfig::from_settings(web),
    };
    // `web.fetch_fallback` runs on the same decision seam as the page check,
    // so a scripted provider in tests reaches both.
    let provider = crate::web::decision::provider();
    let decisions = provider
        .as_ref()
        .map(|provider| crate::web::decision::WebDecisions::new(provider, abort_controller));
    crate::web::fallback::fetch_chain(url, abort_controller, web, &config, decisions.as_ref()).await
}

/// How [`read_page`] obtained its snapshot.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Origin {
    Cached,
    Continuation,
    Fresh,
}

/// The verbatim page read behind `riff web fetch`:
/// the snapshot, the selected range (capped at `maxReturnChars`), and how the
/// snapshot was obtained.
#[derive(Debug)]
pub(crate) struct PageRead {
    pub snapshot: crate::web::snapshot::Snapshot,
    pub selected: crate::web::snapshot::SelectedRange,
    pub origin: Origin,
    pub direct_reason: Option<String>,
    pub challenge_fallback_failed: bool,
    /// Set by `--query` when `web.page_answers` judged the page unhelpful:
    /// the URL to suggest instead.
    pub next_hint: Option<String>,
}

#[derive(Debug)]
pub(crate) enum ReadError {
    Target(crate::web::FetchError),
    Budget(crate::web::budget::BudgetError),
    Fetch(crate::web::fallback::FetchChainFailure),
    Range(crate::web::snapshot::RangeError),
}

impl std::fmt::Display for ReadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Target(error) => error.fmt(f),
            Self::Budget(error) => error.fmt(f),
            Self::Fetch(error) => error.fmt(f),
            Self::Range(error) => error.fmt(f),
        }
    }
}

/// `test_config` is the loopback-mock seam: only `#[cfg(test)]` callers pass it,
/// so a production build cannot loosen the host guard.
pub(crate) async fn read_page(
    url: &str,
    range: Option<&crate::web::snapshot::RangeSpec>,
    web: &crate::settings::WebSettings,
    abort_controller: &crate::runtime::AbortController,
    test_config: Option<crate::web::fetcher::FetchConfig>,
) -> Result<PageRead, ReadError> {
    let _ = crate::web::snapshot::cleanup_retention(web.snapshot_retention_days());
    let fetch_config = match &test_config {
        Some(config) => config.clone(),
        None => crate::web::fetcher::FetchConfig::from_settings(web),
    };
    let normalized_url = crate::web::fetcher::validate_target(url, &fetch_config)
        .map_err(ReadError::Target)?
        .url
        .to_string();

    // A `range` continuation reads an existing snapshot for as long as
    // the file exists and counts against neither the call nor the byte budget
    // (external-search 3.5 / 4.3). Only a fresh fetch is budgeted.
    let cached = if range.is_some() {
        crate::web::snapshot::lookup_any(&normalized_url)
            .map(|snapshot| (snapshot, Origin::Continuation))
    } else {
        crate::web::snapshot::lookup_latest(&normalized_url)
            .map(|snapshot| (snapshot, Origin::Cached))
    };
    let (snapshot, direct_reason, origin, challenge_fallback_failed) = match cached {
        Some((snapshot, origin)) => (snapshot, None, origin, false),
        None => {
            crate::web::budget::begin_fetch(&web.fetch()).map_err(ReadError::Budget)?;
            let fetched = fetch_once(url, abort_controller, web, test_config.as_ref())
                .await
                .map_err(ReadError::Fetch)?;
            crate::web::budget::add_fetch_bytes(
                &web.fetch(),
                fetched.snapshot.metadata.bytes as u64,
            )
            .map_err(ReadError::Budget)?;
            (
                fetched.snapshot,
                fetched.direct_reason,
                Origin::Fresh,
                fetched.challenge_fallback_failed,
            )
        }
    };

    let selected =
        crate::web::snapshot::select_range(&snapshot.text, range, web.max_return_chars() as usize)
            .map_err(ReadError::Range)?;
    Ok(PageRead {
        snapshot,
        selected,
        origin,
        direct_reason,
        challenge_fallback_failed,
        next_hint: None,
    })
}
