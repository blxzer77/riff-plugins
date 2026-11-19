//! riff web: external search and verbatim page fetch for coding agents.
//!
//! The search, fetch, snapshot and decision code comes from nyan (3227f768e);
//! see `docs/design.md` for what changed and why.

pub mod cli;
pub mod decision;
pub mod home;
pub mod net;
pub mod rerank;
pub mod runtime;
pub mod service_health;
pub mod settings;
pub mod web;

#[cfg(test)]
pub(crate) mod test_env;
