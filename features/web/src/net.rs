//! HTTP client construction for riff.
//!
//! Written for riff, not copied: it implements the transport rules the web
//! design states (external-search 4.2 rule 1, 4.6 "provider HTTP client",
//! decision-provider 5.2) on top of reqwest.
//!
//! Three kinds of client exist and none of them may be built any other way:
//!
//! - [`fetch_client_builder`]: fetching a URL the model chose. Always through
//!   the explicit proxy, never reading `NO_PROXY` (or with no proxy at all in
//!   direct mode, where the caller pins resolved addresses).
//! - [`api_client_builder`]: calling a fixed provider API host from config.
//!   Uses the proxy variables and honours `NO_PROXY`.
//! - [`direct_client_builder`]: private-network services (SearXNG, rerank).
//!   Never uses a proxy.
//!
//! Extra CA certificates come from `RIFF_CA_CERTS` (a PEM bundle path) and a
//! client certificate from `RIFF_CLIENT_CERT` + `RIFF_CLIENT_KEY` (PEM paths).

use std::sync::OnceLock;

/// The process environment, read once per call site so tests can substitute it.
pub trait Env {
    fn var(&self, name: &str) -> Option<String>;
}

/// The real process environment. Empty values count as unset.
pub struct ProcessEnv;

impl Env for ProcessEnv {
    fn var(&self, name: &str) -> Option<String> {
        std::env::var(name)
            .ok()
            .filter(|value| !value.trim().is_empty())
    }
}

/// `riff/<version>`. EMRank rejects reqwest's default agent behind Cloudflare
/// (decision-provider 1.4), and pages see the same agent.
pub fn user_agent() -> String {
    format!("riff/{}", env!("CARGO_PKG_VERSION"))
}

/// Installs the ring crypto provider for rustls once per process.
pub fn install_crypto_provider() {
    static ONCE: OnceLock<()> = OnceLock::new();
    ONCE.get_or_init(|| {
        // A second install (another library got there first) is harmless.
        let _ = rustls::crypto::ring::default_provider().install_default();
    });
}

/// The proxy URL from `https_proxy`, `HTTPS_PROXY`, `http_proxy`,
/// `HTTP_PROXY`, first set wins. `ALL_PROXY` is not read. SOCKS URLs are
/// rewritten to `socks5h://` so names resolve at the proxy (external-search
/// 4.2: local DNS is not trusted).
pub fn proxy_url(env: &dyn Env) -> Option<String> {
    ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"]
        .into_iter()
        .find_map(|name| env.var(name))
        .map(|url| remote_dns(url.trim()))
}

fn remote_dns(url: &str) -> String {
    for scheme in ["socks5://", "socks://"] {
        if let Some(rest) = url.strip_prefix(scheme) {
            return format!("socks5h://{rest}");
        }
    }
    url.to_string()
}

/// `NO_PROXY` / `no_proxy`, used only by [`api_client_builder`].
fn no_proxy(env: &dyn Env) -> Option<reqwest::NoProxy> {
    env.var("NO_PROXY")
        .or_else(|| env.var("no_proxy"))
        .and_then(|value| reqwest::NoProxy::from_string(&value))
}

#[derive(Debug, thiserror::Error)]
pub enum NetError {
    #[error("invalid proxy URL")]
    InvalidProxy,
    #[error("cannot read {0}")]
    Unreadable(&'static str),
    #[error("invalid certificate in {0}")]
    InvalidCertificate(&'static str),
}

/// A builder with nothing but the shared TLS setup: rustls with webpki roots
/// plus `RIFF_CA_CERTS`, and the optional client identity.
fn base_builder(env: &dyn Env) -> Result<reqwest::ClientBuilder, NetError> {
    install_crypto_provider();
    let mut builder = reqwest::Client::builder()
        .use_rustls_tls()
        .user_agent(user_agent());
    if let Some(path) = env.var("RIFF_CA_CERTS") {
        let pem = std::fs::read(path).map_err(|_| NetError::Unreadable("RIFF_CA_CERTS"))?;
        let certs = reqwest::Certificate::from_pem_bundle(&pem)
            .map_err(|_| NetError::InvalidCertificate("RIFF_CA_CERTS"))?;
        for cert in certs {
            builder = builder.add_root_certificate(cert);
        }
    }
    match (env.var("RIFF_CLIENT_CERT"), env.var("RIFF_CLIENT_KEY")) {
        (Some(cert), Some(key)) => {
            let mut pem =
                std::fs::read(cert).map_err(|_| NetError::Unreadable("RIFF_CLIENT_CERT"))?;
            pem.push(b'\n');
            pem.extend(std::fs::read(key).map_err(|_| NetError::Unreadable("RIFF_CLIENT_KEY"))?);
            let identity = reqwest::Identity::from_pem(&pem)
                .map_err(|_| NetError::InvalidCertificate("RIFF_CLIENT_CERT"))?;
            builder = builder.identity(identity);
        }
        (None, None) => {}
        _ => return Err(NetError::Unreadable("RIFF_CLIENT_CERT and RIFF_CLIENT_KEY")),
    }
    Ok(builder)
}

/// For fetching model-chosen URLs. `proxy = Some(url)` routes every request
/// through it regardless of `NO_PROXY`; `None` disables proxies entirely.
pub fn fetch_client_builder(
    env: &dyn Env,
    proxy: Option<&str>,
) -> Result<reqwest::ClientBuilder, NetError> {
    let builder = base_builder(env)?.no_proxy();
    match proxy {
        Some(url) => {
            let proxy = reqwest::Proxy::all(url).map_err(|_| NetError::InvalidProxy)?;
            Ok(builder.proxy(proxy))
        }
        None => Ok(builder),
    }
}

/// For fixed API hosts from config (search providers, EMRank): the proxy
/// variables apply, and `NO_PROXY` exempts hosts from them.
pub fn api_client_builder(env: &dyn Env) -> Result<reqwest::ClientBuilder, NetError> {
    let builder = base_builder(env)?.no_proxy();
    let Some(url) = proxy_url(env) else {
        return Ok(builder);
    };
    let proxy = reqwest::Proxy::all(url)
        .map_err(|_| NetError::InvalidProxy)?
        .no_proxy(no_proxy(env));
    Ok(builder.proxy(proxy))
}

/// For private-network services: never proxied.
pub fn direct_client_builder(env: &dyn Env) -> Result<reqwest::ClientBuilder, NetError> {
    Ok(base_builder(env)?.no_proxy())
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use std::collections::HashMap;

    #[derive(Default)]
    pub(crate) struct MapEnv(pub HashMap<&'static str, String>);

    impl Env for MapEnv {
        fn var(&self, name: &str) -> Option<String> {
            self.0
                .get(name)
                .cloned()
                .filter(|value| !value.trim().is_empty())
        }
    }

    fn env(pairs: &[(&'static str, &str)]) -> MapEnv {
        MapEnv(pairs.iter().map(|(k, v)| (*k, v.to_string())).collect())
    }

    #[test]
    fn proxy_variables_are_read_in_order() {
        assert_eq!(proxy_url(&env(&[])), None);
        assert_eq!(
            proxy_url(&env(&[
                ("HTTP_PROXY", "http://c:3"),
                ("http_proxy", "http://b:2")
            ])),
            Some("http://b:2".into())
        );
        assert_eq!(
            proxy_url(&env(&[
                ("HTTPS_PROXY", "http://a:1"),
                ("http_proxy", "http://b:2")
            ])),
            Some("http://a:1".into())
        );
        assert_eq!(
            proxy_url(&env(&[
                ("https_proxy", "http://x:9"),
                ("HTTPS_PROXY", "http://a:1")
            ])),
            Some("http://x:9".into())
        );
    }

    #[test]
    fn all_proxy_and_empty_values_are_ignored() {
        assert_eq!(proxy_url(&env(&[("ALL_PROXY", "http://a:1")])), None);
        assert_eq!(
            proxy_url(&env(&[("https_proxy", " "), ("http_proxy", "http://b:2")])),
            Some("http://b:2".into())
        );
    }

    #[test]
    fn socks_proxies_resolve_names_remotely() {
        assert_eq!(
            proxy_url(&env(&[("https_proxy", "socks5://127.0.0.1:7897")])),
            Some("socks5h://127.0.0.1:7897".into())
        );
        assert_eq!(
            proxy_url(&env(&[("https_proxy", "socks://127.0.0.1:7897")])),
            Some("socks5h://127.0.0.1:7897".into())
        );
        assert_eq!(
            proxy_url(&env(&[("https_proxy", "socks5h://p:1")])),
            Some("socks5h://p:1".into())
        );
    }

    #[test]
    fn clients_build_with_and_without_a_proxy() {
        let e = env(&[
            ("https_proxy", "http://127.0.0.1:1"),
            ("NO_PROXY", "example.com"),
        ]);
        assert!(
            fetch_client_builder(&e, Some("http://127.0.0.1:1"))
                .unwrap()
                .build()
                .is_ok()
        );
        assert!(fetch_client_builder(&e, None).unwrap().build().is_ok());
        assert!(api_client_builder(&e).unwrap().build().is_ok());
        assert!(direct_client_builder(&e).unwrap().build().is_ok());
    }

    #[test]
    fn half_a_client_identity_is_an_error() {
        let e = env(&[("RIFF_CLIENT_CERT", "/nonexistent.pem")]);
        assert!(api_client_builder(&e).is_err());
    }

    #[test]
    fn unreadable_ca_bundle_is_an_error_not_ignored() {
        let e = env(&[("RIFF_CA_CERTS", "/nonexistent/ca.pem")]);
        assert!(matches!(
            api_client_builder(&e),
            Err(NetError::Unreadable(_))
        ));
    }

    #[test]
    fn user_agent_names_riff() {
        assert!(user_agent().starts_with("riff/"));
    }
}
