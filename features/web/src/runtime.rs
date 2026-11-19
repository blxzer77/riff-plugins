//! Process-level plumbing the imported code expects from its host: the active
//! configuration, cancellation, and debug logging.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, OnceLock, RwLock};

use crate::settings::{Config, DecisionSettings, WebSettings};

fn config_cell() -> &'static RwLock<Option<Arc<Config>>> {
    static CELL: OnceLock<RwLock<Option<Arc<Config>>>> = OnceLock::new();
    CELL.get_or_init(|| RwLock::new(None))
}

/// Installs the configuration for this process. The CLI calls it once after
/// loading `config.json`; tests call it per case under the test lock.
pub fn set_config(config: Option<Config>) {
    *config_cell().write().unwrap_or_else(|e| e.into_inner()) = config.map(Arc::new);
}

pub fn config() -> Option<Arc<Config>> {
    config_cell()
        .read()
        .unwrap_or_else(|e| e.into_inner())
        .clone()
}

pub fn web_settings() -> Option<WebSettings> {
    config().and_then(|config| config.web.clone())
}

pub fn decision_settings() -> Option<DecisionSettings> {
    config().and_then(|config| config.decision.clone())
}

/// Cooperative cancellation shared by one invocation (nyan's
/// `AbortController`, reduced to what the web code uses).
#[derive(Clone, Debug, Default)]
pub struct AbortController {
    aborted: Arc<AtomicBool>,
    notify: Arc<tokio::sync::Notify>,
}

impl AbortController {
    pub fn abort(&self) {
        self.aborted.store(true, Ordering::SeqCst);
        self.notify.notify_waiters();
    }

    pub fn is_aborted(&self) -> bool {
        self.aborted.load(Ordering::SeqCst)
    }

    pub fn signal(&self) -> AbortSignal {
        AbortSignal {
            controller: self.clone(),
        }
    }
}

pub struct AbortSignal {
    controller: AbortController,
}

impl AbortSignal {
    /// Resolves once the controller is aborted.
    pub async fn aborted(&mut self) {
        loop {
            let notified = self.controller.notify.notified();
            if self.controller.is_aborted() {
                return;
            }
            notified.await;
        }
    }
}

/// Debug log line on stderr when `RIFF_LOG` is set. Never carries keys:
/// callers redact before logging (external-search 3.6).
pub fn log_for_debugging(message: &str) {
    static ENABLED: OnceLock<bool> = OnceLock::new();
    if *ENABLED.get_or_init(|| std::env::var_os("RIFF_LOG").is_some_and(|v| !v.is_empty())) {
        eprintln!("riff[debug] {message}");
    }
}

/// POSIX single-quote shell quoting for the continuation command.
pub fn shell_quote(word: &str) -> String {
    if !word.is_empty()
        && word
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_./:=@+,".contains(&b))
    {
        return word.to_string();
    }
    format!("'{}'", word.replace('\'', r"'\''"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn abort_wakes_the_signal() {
        let controller = AbortController::default();
        let mut signal = controller.signal();
        let waiter = tokio::spawn(async move { signal.aborted().await });
        tokio::task::yield_now().await;
        controller.abort();
        tokio::time::timeout(std::time::Duration::from_secs(1), waiter)
            .await
            .unwrap()
            .unwrap();
        assert!(controller.is_aborted());
    }

    #[tokio::test]
    async fn signal_of_an_aborted_controller_resolves_at_once() {
        let controller = AbortController::default();
        controller.abort();
        let mut signal = controller.signal();
        tokio::time::timeout(std::time::Duration::from_millis(100), signal.aborted())
            .await
            .unwrap();
    }

    #[test]
    fn shell_quote_leaves_plain_words_and_quotes_the_rest() {
        assert_eq!(shell_quote("https://e.com/a"), "https://e.com/a");
        assert_eq!(
            shell_quote("https://e.com/a?b=1&c='x'"),
            "'https://e.com/a?b=1&c='\\''x'\\'''"
        );
        assert_eq!(shell_quote(""), "''");
    }
}
