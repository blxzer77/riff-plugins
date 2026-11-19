//! Test-only process guards: one lock for every test that touches
//! process-wide state (environment, configuration, `$RIFF_HOME`, the
//! in-memory registries), and an environment variable guard.

use std::ffi::OsString;
use std::sync::{Mutex, MutexGuard};

pub static TEST_ENV_LOCK: Mutex<()> = Mutex::new(());

/// Root for every test's scratch files: `<workspace>/target/test-tmp`, not
/// the system temp dir (tmpfs on some machines, and shared with other users).
pub fn scratch_root() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../target/test-tmp")
}

/// A new, unique directory under [`scratch_root`].
pub fn scratch_dir(name: &str) -> std::path::PathBuf {
    let dir = scratch_root().join(format!("{name}-{}", uuid::Uuid::new_v4().simple()));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

pub type TestEnvGuard<'a> = MutexGuard<'a, ()>;

/// Sets or unsets one variable and restores it on drop. Hold
/// [`TEST_ENV_LOCK`] while it is alive.
pub struct EnvVarGuard {
    name: &'static str,
    previous: Option<OsString>,
}

impl EnvVarGuard {
    pub fn set(name: &'static str, value: impl AsRef<std::ffi::OsStr>) -> Self {
        let previous = std::env::var_os(name);
        // SAFETY: tests hold TEST_ENV_LOCK, so no other test thread reads or
        // writes the environment concurrently.
        unsafe { std::env::set_var(name, value) };
        Self { name, previous }
    }

    pub fn unset(name: &'static str) -> Self {
        let previous = std::env::var_os(name);
        // SAFETY: as in `set`.
        unsafe { std::env::remove_var(name) };
        Self { name, previous }
    }
}

impl Drop for EnvVarGuard {
    fn drop(&mut self) {
        // SAFETY: as in `set`.
        unsafe {
            match &self.previous {
                Some(value) => std::env::set_var(self.name, value),
                None => std::env::remove_var(self.name),
            }
        }
    }
}

/// Points `$RIFF_HOME` at `dir` until dropped; the caller owns the directory.
/// Replaces nyan's `EnvVarGuard::set("NYAN_CONFIG_DIR", dir)`.
pub struct HomeGuard;

impl HomeGuard {
    pub fn set(dir: &std::path::Path) -> Self {
        crate::home::set_home_override(Some(dir.to_path_buf()));
        Self
    }
}

impl Drop for HomeGuard {
    fn drop(&mut self) {
        crate::home::set_home_override(None);
    }
}

/// A fresh `$RIFF_HOME` for one test, removed on drop.
pub struct TempHome {
    pub path: std::path::PathBuf,
}

impl TempHome {
    pub fn new(name: &str) -> Self {
        let path = crate::test_env::scratch_root().join(format!(
            "riff-test-{name}-{}",
            uuid::Uuid::new_v4().simple()
        ));
        std::fs::create_dir_all(&path).unwrap();
        crate::home::set_home_override(Some(path.clone()));
        Self { path }
    }
}

impl Drop for TempHome {
    fn drop(&mut self) {
        crate::home::set_home_override(None);
        let _ = std::fs::remove_dir_all(&self.path);
    }
}
