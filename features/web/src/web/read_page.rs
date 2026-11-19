async fn run_nyan_web_fetch(
    args: &serde_json::Value,
    context: &crate::tool::ToolUseContext,
) -> Result<Output, String> {
    run_nyan_web_fetch_with(args, context, None).await
}

/// One direct-fetch + provider-fallback chain, with the mock seam when a test
/// supplies its own fetcher configuration.
async fn fetch_once(
    url: &str,
    abort_controller: &crate::tool::AbortController,
    web: &crate::utils::settings::nyan::WebSettings,
    config: Option<&crate::services::web::fetcher::FetchConfig>,
) -> Result<
    crate::services::web::fallback::FetchChainResult,
    crate::services::web::fallback::FetchChainFailure,
> {
    let config = match config {
        Some(config) => config.clone(),
        None => crate::services::web::fetcher::FetchConfig::from_settings(web),
    };
    // @nyan: `web.fetch_fallback` runs on the same decision seam as the tool's
    // page check, so a scripted provider in tests reaches both.
    let provider = crate::services::web::decision::provider();
    let decisions = provider.as_ref().map(|provider| {
        crate::services::web::decision::WebDecisions::new(provider, abort_controller)
    });
    crate::services::web::fallback::fetch_chain(
        url,
        abort_controller,
        web,
        &config,
        decisions.as_ref(),
    )
    .await
}

/// How [`read_page`] obtained its snapshot.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Origin {
    Cached,
    Continuation,
    Fresh,
}

/// The verbatim page read shared by the WebFetch tool and `nyan web fetch`:
/// the snapshot, the selected range (capped at `maxReturnChars`), and how the
/// snapshot was obtained.
#[derive(Debug)]
pub(crate) struct PageRead {
    pub snapshot: crate::services::web::snapshot::Snapshot,
    pub selected: crate::services::web::snapshot::SelectedRange,
    pub origin: Origin,
    pub direct_reason: Option<String>,
    pub challenge_fallback_failed: bool,
}

#[derive(Debug)]
pub(crate) enum ReadError {
    Target(crate::services::web::FetchError),
    Budget(crate::services::web::budget::BudgetError),
    Fetch(crate::services::web::fallback::FetchChainFailure),
    Range(crate::services::web::snapshot::RangeError),
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
    range: Option<&crate::services::web::snapshot::RangeSpec>,
    web: &crate::utils::settings::nyan::WebSettings,
    abort_controller: &crate::tool::AbortController,
    test_config: Option<crate::services::web::fetcher::FetchConfig>,
) -> Result<PageRead, ReadError> {
    let _ = crate::services::web::snapshot::cleanup_retention(web.snapshot_retention_days());
    let fetch_config = match &test_config {
        Some(config) => config.clone(),
        None => crate::services::web::fetcher::FetchConfig::from_settings(web),
    };
    let normalized_url = crate::services::web::fetcher::validate_target(url, &fetch_config)
        .map_err(ReadError::Target)?
        .url
        .to_string();

    // @nyan: a `range` continuation reads an existing snapshot for as long as
    // the file exists and counts against neither the call nor the byte budget
    // (external-search 3.5 / 4.3). Only a fresh fetch is budgeted.
    let cached = if range.is_some() {
        crate::services::web::snapshot::lookup_any(&normalized_url)
            .map(|snapshot| (snapshot, Origin::Continuation))
    } else {
        crate::services::web::snapshot::lookup_latest(&normalized_url)
            .map(|snapshot| (snapshot, Origin::Cached))
    };
    let (snapshot, direct_reason, origin, challenge_fallback_failed) = match cached {
        Some((snapshot, origin)) => (snapshot, None, origin, false),
        None => {
            crate::services::web::budget::begin_fetch(&web.fetch()).map_err(ReadError::Budget)?;
            let fetched = fetch_once(url, abort_controller, web, test_config.as_ref())
                .await
                .map_err(ReadError::Fetch)?;
            crate::services::web::budget::add_fetch_bytes(
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

    let selected = crate::services::web::snapshot::select_range(
        &snapshot.text,
        range,
        web.max_return_chars() as usize,
    )
    .map_err(ReadError::Range)?;
    Ok(PageRead {
        snapshot,
        selected,
        origin,
        direct_reason,
        challenge_fallback_failed,
    })
}

/// `test_config` is the loopback-mock seam: only `#[cfg(test)]` callers pass it,
/// so a production build cannot loosen the host guard.
async fn run_nyan_web_fetch_with(
    args: &serde_json::Value,
    context: &crate::tool::ToolUseContext,
    test_config: Option<crate::services::web::fetcher::FetchConfig>,
) -> Result<Output, String> {
    let started = std::time::Instant::now();
    let url = args
        .get("url")
        .and_then(|value| value.as_str())
        .ok_or_else(|| "Error: Missing URL".to_string())?;
    let prompt = args
        .get("prompt")
        .and_then(|value| value.as_str())
        .unwrap_or_default();
    let range = crate::services::web::snapshot::parse_range(
        args.get("range").and_then(|value| value.as_str()),
    )
    .map_err(|error| error.to_string())?;
    let web = crate::services::web::settings()
        .ok_or_else(|| "Error: nyan.web is not configured".to_string())?;
    let PageRead {
        snapshot,
        selected,
        origin,
        direct_reason,
        challenge_fallback_failed,
    } = read_page(
        url,
        range.as_ref(),
        &web,
        &context.abort_controller,
        test_config,
    )
    .await
    .map_err(|error| error.to_string())?;
    let body = if prompt.trim().is_empty() {
        selected.text.clone()
    } else {
        crate::services::web::extract::extract_prompt(
            prompt,
            &selected.text,
            web.extract_model.as_deref(),
            context.is_non_interactive_session,
            &context.abort_controller,
        )
        .await
        .map_err(|error| error.to_string())?
        .render()
    };
    let body = body
        .chars()
        .take(web.max_return_chars() as usize)
        .collect::<String>();
    // §7 post-hoc probe: a successful fetch is the usage evidence for any
    // retained `web.answers` / `web.page_answers` candidate. Match both the
    // requested URL and the post-redirect final URL.
    crate::services::decision::probe::observe_url(url);
    crate::services::decision::probe::observe_url(&snapshot.metadata.final_url);
    let fetched_at = snapshot.metadata.fetched_at.to_rfc3339();
    let source = &snapshot.metadata.final_url;
    let total = snapshot.text.chars().count();
    let origin_note = match (&direct_reason, origin) {
        (Some(reason), _) => format!(
            "(fetched via {}, {fetched_at}, {total} chars; direct fetch failed: {reason})",
            snapshot.metadata.fetched_by
        ),
        (None, Origin::Fresh) => format!(
            "(fetched {fetched_at}, {total} chars; source: {})",
            snapshot.metadata.fetched_by
        ),
        (None, Origin::Cached | Origin::Continuation) => format!(
            "(snapshot fetched {fetched_at}, {total} chars; source: {}; not refetched)",
            snapshot.metadata.fetched_by
        ),
    };
    // @nyan: web.fetch_fallback asked for a provider, every provider failed, and
    // the direct page was already accepted by the rules — say so, do not hide it.
    let origin_note = if challenge_fallback_failed {
        format!("{origin_note} [provider fallback failed; serving the direct fetch]")
    } else {
        origin_note
    };
    let continuation = if selected.end < selected.total {
        format!(". Continue with range=chars:{}-", selected.end)
    } else {
        String::new()
    };

    // @nyan: web.page_answers only appends a hint; the body is never rewritten.
    // The tool input's prompt is the only query this tool has (decision-provider 4.2).
    let mut hint = String::new();
    if !prompt.trim().is_empty()
        && let Some(provider) = crate::services::web::decision::provider()
    {
        let decisions =
            crate::services::web::decision::WebDecisions::new(&provider, &context.abort_controller);
        if decisions.page_lacks_answer(prompt, &selected.text).await {
            let next = crate::services::web::search::next_candidate(source);
            if let Some(next) = next.as_deref() {
                // §7: the hint names one candidate; probe whether it is used.
                crate::services::web::decision::register_next_candidate_probe(next);
            }
            hint.push_str(&format!(
                "\n[page may not answer the query — consider fetching: {}]",
                next.unwrap_or_else(|| "another search result".to_string())
            ));
        }
    }

    let result = format!(
        "{source}  {origin_note}\n\n<web_content source=\"{source}\">\n{body}\n</web_content>\n\n[Showing chars {}–{} of {}{}]{hint}",
        selected.start, selected.end, selected.total, continuation,
    );
    let code_text = reqwest::StatusCode::from_u16(snapshot.metadata.status)
        .ok()
        .and_then(|status| status.canonical_reason())
        .unwrap_or("Unknown")
        .to_string();
    Ok(Output {
        bytes: snapshot.metadata.bytes,
        code: i64::from(snapshot.metadata.status),
        code_text,
        result,
        duration_ms: started.elapsed().as_millis() as u64,
        url: url.to_string(),
    })
}

