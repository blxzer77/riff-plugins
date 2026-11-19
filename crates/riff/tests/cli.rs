//! The `riff` binary across separate processes (design 11: 1–4). Each test
//! gets its own `$RIFF_HOME` under `target/test-tmp` and a loopback mock search
//! provider; nothing touches the network or the real home.

use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

struct Mock {
    origin: String,
    hits: Arc<AtomicUsize>,
    reply: Arc<Mutex<(u16, &'static str)>>,
    delay: Arc<Mutex<Duration>>,
}

impl Mock {
    fn reply(&self, status: u16, body: &'static str) {
        *self.reply.lock().unwrap() = (status, body);
    }

    /// Holds every later answer back, so a caller stays inside its command.
    fn delay(&self, delay: Duration) {
        *self.delay.lock().unwrap() = delay;
    }
}

/// A tiny HTTP/1.1 server answering every request with the current reply.
fn mock(body: &'static str) -> Mock {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let origin = format!("http://{}", listener.local_addr().unwrap());
    let hits = Arc::new(AtomicUsize::new(0));
    let reply = Arc::new(Mutex::new((200u16, body)));
    let delay = Arc::new(Mutex::new(Duration::ZERO));
    let (counter, current, pause) = (Arc::clone(&hits), Arc::clone(&reply), Arc::clone(&delay));
    std::thread::spawn(move || {
        for stream in listener.incoming() {
            let Ok(mut stream) = stream else { continue };
            let mut reader = BufReader::new(stream.try_clone().unwrap());
            let mut length = 0usize;
            loop {
                let mut line = String::new();
                if reader.read_line(&mut line).unwrap_or(0) == 0 || line == "\r\n" {
                    break;
                }
                if let Some(value) = line.to_ascii_lowercase().strip_prefix("content-length:") {
                    length = value.trim().parse().unwrap_or(0);
                }
            }
            let mut request_body = vec![0; length];
            let _ = reader.read_exact(&mut request_body);
            counter.fetch_add(1, Ordering::SeqCst);
            let wait = *pause.lock().unwrap();
            std::thread::sleep(wait);
            let (status, body) = *current.lock().unwrap();
            let response = format!(
                "HTTP/1.1 {status} X\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{body}",
                body.len()
            );
            let _ = stream.write_all(response.as_bytes());
        }
    });
    Mock {
        origin,
        hits,
        reply,
        delay,
    }
}

const RESULTS: &str = r#"{"results":[
 {"title":"B result","url":"https://b.example/doc","highlights":["second"]},
 {"title":"A result","url":"https://a.example/doc","highlights":["first"]}]}"#;

fn home(name: &str) -> PathBuf {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../target/test-tmp")
        .join(format!("cli-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(dir.join("keys")).unwrap();
    std::fs::write(dir.join("keys/exa"), "test-key\n").unwrap();
    dir
}

/// Only exa is enabled, pointed at the mock; decisions are off so no test
/// can reach EMRank.
fn configure(home: &Path, mock: &Mock, extra: &str) {
    let mut providers = String::new();
    for name in [
        "anysearch",
        "brave",
        "deepseek",
        "firecrawl",
        "tavily",
        "searxng",
    ] {
        providers.push_str(&format!(r#""{name}": {{"enabled": false}},"#));
    }
    let config = format!(
        r#"{{"web": {{"providers": {{ {providers}
              "exa": {{"baseUrl": "{}", "maxCallsPerSession": 2}} }}{extra} }},
            "decision": {{"enabled": false}} }}"#,
        mock.origin
    );
    std::fs::write(home.join("config.json"), config).unwrap();
}

fn riff(home: &Path, cwd: &Path, args: &[&str]) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_riff"));
    command
        .args(args)
        .current_dir(cwd)
        .env("RIFF_HOME", home)
        .env_remove("RIFF_SESSION")
        .env_remove("CODEX_SESSION_ID");
    for name in [
        "https_proxy",
        "HTTPS_PROXY",
        "http_proxy",
        "HTTP_PROXY",
        "NO_PROXY",
        "no_proxy",
    ] {
        command.env_remove(name);
    }
    command.output().unwrap()
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn search_output_is_byte_stable_across_processes() {
    let mock = mock(RESULTS);
    let home = home("stable");
    configure(&home, &mock, "");
    let first = riff(&home, &home, &["web", "search", "q", "--session", "s1"]);
    let second = riff(&home, &home, &["web", "search", "q", "--session", "s2"]);
    assert!(first.status.success(), "{}", stderr(&first));
    assert_eq!(first.stdout, second.stdout);
    let text = stdout(&first);
    assert!(text.contains("**B result**"), "{text}");
    let json1 = riff(
        &home,
        &home,
        &["web", "search", "q", "--json", "--session", "s3"],
    );
    let json2 = riff(
        &home,
        &home,
        &["web", "search", "q", "--json", "--session", "s4"],
    );
    assert_eq!(json1.stdout, json2.stdout);
}

#[test]
fn the_provider_budget_carries_across_processes_and_reset_clears_it() {
    let mock = mock(RESULTS);
    let home = home("budget");
    configure(&home, &mock, "");
    for _ in 0..2 {
        assert!(
            riff(&home, &home, &["web", "search", "q", "--session", "a"])
                .status
                .success()
        );
    }
    assert_eq!(mock.hits.load(Ordering::SeqCst), 2);
    // maxCallsPerSession = 2: the third process must not reach the provider.
    let third = riff(&home, &home, &["web", "search", "q", "--session", "a"]);
    assert_eq!(mock.hits.load(Ordering::SeqCst), 2, "{}", stderr(&third));
    assert_eq!(third.status.code(), Some(5), "{}", stderr(&third));
    assert!(
        stderr(&third).contains("exa budget_exhausted"),
        "{}",
        stderr(&third)
    );

    // Another session has its own budget.
    assert!(
        riff(&home, &home, &["web", "search", "q", "--session", "b"])
            .status
            .success()
    );
    assert_eq!(mock.hits.load(Ordering::SeqCst), 3);

    assert!(
        riff(&home, &home, &["web", "reset", "--session", "a"])
            .status
            .success()
    );
    assert!(
        riff(&home, &home, &["web", "search", "q", "--session", "a"])
            .status
            .success()
    );
    assert_eq!(mock.hits.load(Ordering::SeqCst), 4);
}

#[test]
fn without_a_session_id_the_working_directory_is_the_session() {
    let mock = mock(RESULTS);
    let home = home("cwd");
    configure(&home, &mock, "");
    let one = home.join("one");
    let two = home.join("two");
    std::fs::create_dir_all(&one).unwrap();
    std::fs::create_dir_all(&two).unwrap();
    for _ in 0..2 {
        assert!(riff(&home, &one, &["web", "search", "q"]).status.success());
    }
    assert_eq!(
        riff(&home, &one, &["web", "search", "q"]).status.code(),
        Some(5)
    );
    assert!(riff(&home, &two, &["web", "search", "q"]).status.success());
    assert_eq!(mock.hits.load(Ordering::SeqCst), 3);
}

#[test]
fn a_quota_cooldown_is_shared_by_every_session() {
    let mock = mock(RESULTS);
    mock.reply(
        402,
        r#"{"error":"out of credits","code":"NO_MORE_CREDITS"}"#,
    );
    let home = home("cooldown");
    configure(&home, &mock, "");
    let first = riff(&home, &home, &["web", "search", "q", "--session", "x"]);
    assert_eq!(first.status.code(), Some(5), "{}", stderr(&first));
    assert_eq!(mock.hits.load(Ordering::SeqCst), 1);
    // A different session, a new process: still cooling down, no request.
    let second = riff(&home, &home, &["web", "search", "q", "--session", "y"]);
    assert_eq!(mock.hits.load(Ordering::SeqCst), 1, "{}", stderr(&second));
    assert!(
        stderr(&second).contains("(cooling down)"),
        "{}",
        stderr(&second)
    );
    // `reset` clears cooldowns for everyone.
    mock.reply(200, RESULTS);
    assert!(
        riff(&home, &home, &["web", "reset", "--session", "x"])
            .status
            .success()
    );
    assert!(
        riff(&home, &home, &["web", "search", "q", "--session", "y"])
            .status
            .success()
    );
    assert_eq!(mock.hits.load(Ordering::SeqCst), 2);
}

#[test]
fn concurrent_processes_in_one_session_never_overspend() {
    let mock = mock(RESULTS);
    let home = home("concurrent");
    configure(&home, &mock, "");
    let children = (0..8)
        .map(|_| {
            let mut command = Command::new(env!("CARGO_BIN_EXE_riff"));
            command
                .args(["web", "search", "q", "--session", "c"])
                .current_dir(&home)
                .env("RIFF_HOME", &home)
                .env_remove("RIFF_SESSION")
                .env_remove("CODEX_SESSION_ID")
                .env_remove("https_proxy")
                .env_remove("HTTPS_PROXY")
                .env_remove("http_proxy")
                .env_remove("HTTP_PROXY");
            command
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .spawn()
                .unwrap()
        })
        .collect::<Vec<_>>();
    let ok = children
        .into_iter()
        .map(|mut child| child.wait().unwrap().success())
        .filter(|ok| *ok)
        .count();
    assert_eq!(
        mock.hits.load(Ordering::SeqCst),
        2,
        "the per-session cap is exact"
    );
    assert_eq!(ok, 2);
}

/// Calls that overlap without starting together: the second starts while the
/// first runs, the third after the first has written its state back but while
/// the second still runs. Each must see the counts of the ones before it.
#[test]
fn staggered_processes_in_one_session_never_overspend() {
    let mock = mock(RESULTS);
    mock.delay(Duration::from_millis(300));
    let home = home("staggered");
    configure(&home, &mock, "");
    let spawn = || {
        let mut command = Command::new(env!("CARGO_BIN_EXE_riff"));
        command
            .args(["web", "search", "q", "--session", "c"])
            .current_dir(&home)
            .env("RIFF_HOME", &home)
            .env_remove("RIFF_SESSION")
            .env_remove("CODEX_SESSION_ID")
            .env_remove("https_proxy")
            .env_remove("HTTPS_PROXY")
            .env_remove("http_proxy")
            .env_remove("HTTP_PROXY");
        command
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .unwrap()
    };
    let first = spawn();
    std::thread::sleep(Duration::from_millis(80));
    let second = spawn();
    std::thread::sleep(Duration::from_millis(370));
    let third = spawn();
    let ok = [first, second, third]
        .into_iter()
        .map(|mut child| child.wait().unwrap().success())
        .filter(|ok| *ok)
        .count();
    assert_eq!(
        mock.hits.load(Ordering::SeqCst),
        2,
        "the per-session cap is exact"
    );
    assert_eq!(ok, 2);
}

#[test]
fn configuration_in_the_working_directory_is_ignored() {
    let mock = mock(RESULTS);
    let home = home("isolation");
    configure(&home, &mock, "");
    let project = home.join("project");
    std::fs::create_dir_all(project.join(".riff")).unwrap();
    // A repository trying to loosen policy or redirect providers.
    let hostile = r#"{"web": {"fetchVia": "direct", "providers": {"exa": {"baseUrl": "http://127.0.0.1:1"}}}}"#;
    std::fs::write(project.join(".riff/config.json"), hostile).unwrap();
    std::fs::write(project.join("config.json"), hostile).unwrap();
    let output = riff(&home, &project, &["web", "search", "q"]);
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(mock.hits.load(Ordering::SeqCst), 1);
}

#[test]
fn a_missing_configuration_is_exit_three_and_says_where() {
    let home = home("missing");
    let output = riff(&home, &home, &["web", "search", "q"]);
    assert_eq!(output.status.code(), Some(3));
    assert!(
        stderr(&output).contains("config.json"),
        "{}",
        stderr(&output)
    );
    assert!(
        !home.join("state").exists(),
        "no state before a valid config"
    );
}

#[test]
fn state_files_are_private() {
    let mock = mock(RESULTS);
    let home = home("private");
    configure(&home, &mock, "");
    assert!(
        riff(&home, &home, &["web", "search", "q", "--session", "p"])
            .status
            .success()
    );
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        for path in [home.join("state"), home.join("state/health.json")] {
            let mode = std::fs::metadata(&path).unwrap().permissions().mode() & 0o777;
            assert_eq!(mode & 0o077, 0, "{} is {mode:o}", path.display());
        }
        let sessions = std::fs::read_dir(home.join("state/sessions")).unwrap();
        for entry in sessions {
            let mode = entry.unwrap().metadata().unwrap().permissions().mode() & 0o777;
            assert_eq!(mode & 0o077, 0);
        }
    }
}
