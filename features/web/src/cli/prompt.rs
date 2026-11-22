//! `riff prompt`: one global instructions file for every agent.
//!
//! `install` writes `$RIFF_HOME/global-prompt.md` from the bundled template
//! (never over an existing file) and makes each agent's user-level
//! instructions file a symbolic link to it, so one edit reaches every agent.
//! Nothing that exists is overwritten or moved: a file the user wrote is kept,
//! and a file that would hide the link from its agent, or be hidden by it,
//! blocks that agent until the user merges it into the source.
//!
//! Where each agent reads its user-level instructions (verified 2026-11-22):
//! - Claude Code: `$CLAUDE_CONFIG_DIR/CLAUDE.md`, default `~/.claude`
//!   (code.claude.com/docs/en/memory, /claude-directory).
//! - Codex: `$CODEX_HOME/AGENTS.md`, default `~/.codex`; a non-empty
//!   `AGENTS.override.md` there is read instead
//!   (learn.chatgpt.com/docs/agent-configuration/agents-md).
//! - Antigravity: `~/.gemini/AGENTS.md`; `GEMINI.md` and `config/` files there
//!   are loaded as well, rules add up (antigravity.google/docs/rules).
//! - pi: `$PI_CODING_AGENT_DIR/AGENTS.md`, default `~/.pi/agent`; pi reads only
//!   the first of `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`,
//!   `CLAUDE.MD` (pi 1.4.0, `loadContextFileFromDir`).

use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use super::web::exit;

/// The bundled template; release archives ship only the binary.
pub const TEMPLATE: &str = include_str!("../../../../template/global-prompt.md");
/// Every placeholder in the template starts with this.
const PLACEHOLDER: &str = "[fill in";
const SOURCE_NAME: &str = "global-prompt.md";

pub const HELP: &str = "\
Usage: riff prompt install [--agent <name>] [--dry-run]
       riff prompt path

One global instructions file for every agent. `install` writes
$RIFF_HOME/global-prompt.md (default ~/.riff) from the bundled template, never
over an existing file, and links each agent's user-level instructions file to it:

  claude-code   $CLAUDE_CONFIG_DIR/CLAUDE.md     (default ~/.claude)
  codex         $CODEX_HOME/AGENTS.md            (default ~/.codex)
  antigravity   ~/.gemini/AGENTS.md
  pi            $PI_CODING_AGENT_DIR/AGENTS.md   (default ~/.pi/agent)

Without --agent, every agent whose directory exists is linked. Existing files
are never overwritten or moved: merge one into the source, remove it, and run
`install` again. `path` prints the source file's path.

Options:
      --agent <name>   claude-code, codex, antigravity, pi or all (default all)
      --dry-run        Report what install would do; change nothing
  -h, --help           Show this help

Exit codes:
  0 every selected agent reads the source   1 an agent needs attention
  2 usage error
";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Agent {
    ClaudeCode,
    Codex,
    Antigravity,
    Pi,
}

const AGENTS: [Agent; 4] = [
    Agent::ClaudeCode,
    Agent::Codex,
    Agent::Antigravity,
    Agent::Pi,
];

impl Agent {
    fn parse(name: &str) -> Option<Self> {
        AGENTS.into_iter().find(|agent| agent.name() == name)
    }

    fn name(self) -> &'static str {
        match self {
            Self::ClaudeCode => "claude-code",
            Self::Codex => "codex",
            Self::Antigravity => "antigravity",
            Self::Pi => "pi",
        }
    }

    fn file_name(self) -> &'static str {
        match self {
            Self::ClaudeCode => "CLAUDE.md",
            Self::Codex | Self::Antigravity | Self::Pi => "AGENTS.md",
        }
    }
}

/// Where riff and the agents keep their files. Read from the process
/// environment once, so tests pass their own instead of mutating it.
#[derive(Clone, Debug)]
struct Env {
    riff_home: PathBuf,
    home: Option<PathBuf>,
    claude_config_dir: Option<PathBuf>,
    codex_home: Option<PathBuf>,
    pi_agent_dir: Option<PathBuf>,
}

impl Env {
    fn from_process() -> Self {
        let var = |name: &str| {
            std::env::var_os(name)
                .filter(|value| !value.is_empty())
                .map(|value| expand_tilde(PathBuf::from(value)))
        };
        Self {
            riff_home: crate::home::riff_home(),
            home: crate::home::home_dir(),
            claude_config_dir: var("CLAUDE_CONFIG_DIR"),
            codex_home: var("CODEX_HOME"),
            pi_agent_dir: var("PI_CODING_AGENT_DIR"),
        }
    }

    /// Absolute, because every link points at it from another directory.
    fn source(&self) -> PathBuf {
        let path = self.riff_home.join(SOURCE_NAME);
        std::path::absolute(&path).unwrap_or(path)
    }

    /// The directory an agent reads its user-level instructions from.
    fn agent_dir(&self, agent: Agent) -> Option<PathBuf> {
        let home = self.home.as_deref();
        match agent {
            Agent::ClaudeCode => self
                .claude_config_dir
                .clone()
                .or_else(|| home.map(|home| home.join(".claude"))),
            Agent::Codex => self
                .codex_home
                .clone()
                .or_else(|| home.map(|home| home.join(".codex"))),
            Agent::Antigravity => home.map(|home| home.join(".gemini")),
            Agent::Pi => self
                .pi_agent_dir
                .clone()
                .or_else(|| home.map(|home| home.join(".pi").join("agent"))),
        }
    }
}

fn expand_tilde(path: PathBuf) -> PathBuf {
    match path.to_str() {
        Some(text) if text == "~" || text.starts_with("~/") => crate::home::expand_path(text),
        _ => path,
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Selection {
    All,
    One(Agent),
}

#[derive(Debug, PartialEq, Eq)]
enum Parsed {
    Help,
    Path,
    Install { selection: Selection, dry_run: bool },
}

/// `args` are the words after `prompt`.
fn parse(args: &[String]) -> Result<Parsed, String> {
    let Some((command, rest)) = args.split_first() else {
        return Err("missing command: expected `install` or `path`".to_string());
    };
    let command = command.as_str();
    if matches!(command, "-h" | "--help" | "help")
        || rest.iter().any(|arg| arg == "-h" || arg == "--help")
    {
        return Ok(Parsed::Help);
    }
    match command {
        "path" => match rest.first() {
            Some(extra) => Err(format!("unexpected argument `{extra}`")),
            None => Ok(Parsed::Path),
        },
        "install" => {
            let mut selection = Selection::All;
            let mut dry_run = false;
            let mut index = 0;
            while index < rest.len() {
                let arg = rest[index].as_str();
                index += 1;
                let (flag, inline) = match arg.split_once('=') {
                    Some((flag, value)) if flag.starts_with("--") => (flag, Some(value)),
                    _ => (arg, None),
                };
                match flag {
                    "--dry-run" if inline.is_none() => dry_run = true,
                    "--agent" => {
                        let value = match inline {
                            Some(value) => value,
                            None => {
                                let value = rest
                                    .get(index)
                                    .ok_or_else(|| "--agent requires a value".to_string())?;
                                index += 1;
                                value.as_str()
                            }
                        };
                        selection = match value {
                            "all" => Selection::All,
                            name => Selection::One(Agent::parse(name).ok_or_else(|| {
                                format!(
                                    "unknown agent `{name}`: expected claude-code, codex, \
                                     antigravity, pi or all"
                                )
                            })?),
                        };
                    }
                    _ => return Err(format!("unknown option `{arg}`")),
                }
            }
            Ok(Parsed::Install { selection, dry_run })
        }
        other => Err(format!(
            "unknown command `{other}`: expected `install` or `path`"
        )),
    }
}

/// What happened to the source file.
#[derive(Clone, Debug, PartialEq, Eq)]
enum SourceState {
    /// Written from the template (in a dry run: would be).
    Written,
    Kept,
    Failed(String),
}

/// What happened to one agent's instructions file.
#[derive(Clone, Debug, PartialEq, Eq)]
enum Outcome {
    /// The link was created (in a dry run: would be).
    Linked,
    AlreadyLinked,
    /// All agents were selected and this one's directory does not exist.
    NotInstalled,
    /// A file that is not a link to the source is already there; it stays.
    Kept,
    /// Another file would hide the link from the agent, or be hidden by it.
    Blocked(String),
    Failed(String),
}

impl Outcome {
    fn is_ok(&self) -> bool {
        matches!(
            self,
            Self::Linked | Self::AlreadyLinked | Self::NotInstalled
        )
    }
}

#[derive(Debug)]
struct AgentReport {
    agent: Agent,
    /// The instructions file, or the missing directory for `NotInstalled`.
    path: Option<PathBuf>,
    outcome: Outcome,
    notes: Vec<String>,
}

#[derive(Debug)]
struct Report {
    dry_run: bool,
    source: PathBuf,
    source_state: SourceState,
    placeholders: usize,
    agents: Vec<AgentReport>,
}

fn install(env: &Env, selection: Selection, dry_run: bool) -> Report {
    let source = env.source();
    let source_state = ensure_source(&source, dry_run);
    let text = std::fs::read_to_string(&source).unwrap_or_else(|_| TEMPLATE.to_string());
    let placeholders = text.matches(PLACEHOLDER).count();
    let (selected, explicit) = match selection {
        Selection::All => (AGENTS.to_vec(), false),
        Selection::One(agent) => (vec![agent], true),
    };
    // A link to a source that could not be written would dangle.
    let agents = if matches!(source_state, SourceState::Failed(_)) {
        Vec::new()
    } else {
        selected
            .into_iter()
            .map(|agent| link_agent(env, agent, &source, explicit, dry_run))
            .collect()
    };
    Report {
        dry_run,
        source,
        source_state,
        placeholders,
        agents,
    }
}

fn ensure_source(source: &Path, dry_run: bool) -> SourceState {
    if std::fs::symlink_metadata(source).is_ok() {
        // Every link points here, so it must be a file an agent can read
        // (a link the user made to their own file counts).
        return if std::fs::metadata(source).is_ok_and(|meta| meta.is_file()) {
            SourceState::Kept
        } else {
            SourceState::Failed(format!(
                "{} exists but is not a readable file",
                source.display()
            ))
        };
    }
    if dry_run {
        return SourceState::Written;
    }
    if let Some(dir) = source.parent()
        && let Err(error) = crate::home::ensure_private_dir(dir)
    {
        return SourceState::Failed(format!("cannot create {}: {error}", dir.display()));
    }
    match super::setup::write_private(source, TEMPLATE) {
        Ok(()) => SourceState::Written,
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => SourceState::Kept,
        Err(error) => SourceState::Failed(format!("cannot write {}: {error}", source.display())),
    }
}

fn link_agent(
    env: &Env,
    agent: Agent,
    source: &Path,
    explicit: bool,
    dry_run: bool,
) -> AgentReport {
    let Some(dir) = env.agent_dir(agent) else {
        return AgentReport {
            agent,
            path: None,
            outcome: Outcome::Failed("no home directory (HOME is not set)".to_string()),
            notes: Vec::new(),
        };
    };
    if !explicit && !dir.is_dir() {
        return AgentReport {
            agent,
            path: Some(dir),
            outcome: Outcome::NotInstalled,
            notes: Vec::new(),
        };
    }
    let target = dir.join(agent.file_name());
    let outcome = decide(agent, &dir, &target, source, dry_run);
    let notes = if matches!(outcome, Outcome::Linked | Outcome::AlreadyLinked) {
        also_loaded(agent, &dir)
    } else {
        Vec::new()
    };
    AgentReport {
        agent,
        path: Some(target),
        outcome,
        notes,
    }
}

fn decide(agent: Agent, dir: &Path, target: &Path, source: &Path, dry_run: bool) -> Outcome {
    let linked = match std::fs::symlink_metadata(target) {
        Ok(meta) if meta.file_type().is_symlink() && points_to(target, source) => true,
        Ok(_) => return Outcome::Kept,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => false,
        Err(error) => return Outcome::Failed(error.to_string()),
    };
    if let Some(reason) = conflict(agent, dir, linked) {
        return Outcome::Blocked(reason);
    }
    if linked {
        return Outcome::AlreadyLinked;
    }
    if dry_run {
        return Outcome::Linked;
    }
    match create_link(dir, source, target) {
        Ok(()) => Outcome::Linked,
        // Created by someone else since the check: theirs stays.
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => Outcome::Kept,
        Err(error) => Outcome::Failed(format!("cannot create the link: {error}")),
    }
}

/// A file in the agent's directory that would hide the link from the agent,
/// or that the new link would silently replace.
fn conflict(agent: Agent, dir: &Path, linked: bool) -> Option<String> {
    match agent {
        // Codex skips empty files, so only a non-empty override wins.
        Agent::Codex => std::fs::metadata(dir.join("AGENTS.override.md"))
            .is_ok_and(|meta| meta.len() > 0)
            .then(|| "AGENTS.override.md is not empty, and Codex reads it instead".to_string()),
        Agent::Pi => {
            if present(&dir.join("AGENTS.override.md")) {
                return Some("AGENTS.override.md exists, and pi reads it instead".to_string());
            }
            if linked {
                return None;
            }
            ["AGENTS.MD", "CLAUDE.md", "CLAUDE.MD"]
                .into_iter()
                .find(|name| present(&dir.join(name)))
                .map(|name| {
                    format!("{name} exists, and pi reads only one global file: the link would replace it")
                })
        }
        Agent::ClaudeCode | Agent::Antigravity => None,
    }
}

/// Global rules files the agent loads next to the link, so their content
/// would appear twice once it is merged into the source.
fn also_loaded(agent: Agent, dir: &Path) -> Vec<String> {
    if agent != Agent::Antigravity {
        return Vec::new();
    }
    [
        dir.join("GEMINI.md"),
        dir.join("config").join("AGENTS.md"),
        dir.join("config").join("GEMINI.md"),
    ]
    .into_iter()
    .filter(|path| present(path))
    .map(|path| {
        format!(
            "{} is loaded as well (Antigravity adds up global rules); merge it into the source and remove it",
            path.display()
        )
    })
    .collect()
}

fn present(path: &Path) -> bool {
    std::fs::symlink_metadata(path).is_ok()
}

fn points_to(link: &Path, source: &Path) -> bool {
    match (std::fs::canonicalize(link), std::fs::canonicalize(source)) {
        (Ok(resolved), Ok(source)) => resolved == source,
        _ => std::fs::read_link(link).is_ok_and(|target| target == source),
    }
}

fn create_link(dir: &Path, source: &Path, target: &Path) -> std::io::Result<()> {
    if !dir.is_dir() {
        crate::home::ensure_private_dir(dir)?;
    }
    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(source, target)
    }
    #[cfg(windows)]
    {
        std::os::windows::fs::symlink_file(source, target)
    }
    #[cfg(not(any(unix, windows)))]
    {
        let _ = (source, target);
        Err(std::io::Error::from(std::io::ErrorKind::Unsupported))
    }
}

impl Report {
    fn exit_code(&self) -> i32 {
        let failed = matches!(self.source_state, SourceState::Failed(_))
            || self.agents.iter().any(|agent| !agent.outcome.is_ok())
            || self
                .agents
                .iter()
                .all(|agent| agent.outcome == Outcome::NotInstalled);
        if failed { exit::OTHER } else { 0 }
    }

    fn render(&self) -> String {
        let mut out = String::new();
        let source_detail = match &self.source_state {
            SourceState::Written if self.dry_run => {
                "would be written from the template".to_string()
            }
            SourceState::Written => "written from the template".to_string(),
            SourceState::Kept => "exists; kept".to_string(),
            SourceState::Failed(error) => error.clone(),
        };
        let _ = writeln!(
            out,
            "source          {} ({source_detail})",
            self.source.display()
        );
        for report in &self.agents {
            let path = report
                .path
                .as_ref()
                .map(|path| path.display().to_string())
                .unwrap_or_default();
            let (label, detail) = match &report.outcome {
                Outcome::Linked if self.dry_run => ("would link", String::new()),
                Outcome::Linked => ("linked", String::new()),
                Outcome::AlreadyLinked => ("already linked", String::new()),
                Outcome::NotInstalled => (
                    "not installed",
                    format!(
                        ": directory missing (--agent {} creates it)",
                        report.agent.name()
                    ),
                ),
                Outcome::Kept => (
                    "kept",
                    ": exists and is not a link to the source; not overwritten".to_string(),
                ),
                Outcome::Blocked(reason) => ("blocked", format!(": {reason}")),
                Outcome::Failed(error) => ("failed", format!(": {error}")),
            };
            let _ = writeln!(
                out,
                "{label:<15} {:<12} {path}{detail}",
                report.agent.name()
            );
            for note in &report.notes {
                let _ = writeln!(out, "  note: {note}");
            }
        }
        if !self.agents.is_empty()
            && self
                .agents
                .iter()
                .all(|agent| agent.outcome == Outcome::NotInstalled)
        {
            let _ = writeln!(out, "No agent directory found; name an agent with --agent.");
        }
        if self
            .agents
            .iter()
            .any(|agent| matches!(agent.outcome, Outcome::Kept | Outcome::Blocked(_)))
        {
            let _ = writeln!(
                out,
                "To finish: merge each kept or blocking file into the source, remove it, and run `riff prompt install` again."
            );
        }
        if self.placeholders > 0 {
            let _ = writeln!(
                out,
                "Fill in the {} `[fill in]` placeholder(s) in {}; agents read it from their next session.",
                self.placeholders,
                self.source.display()
            );
        } else if !matches!(self.source_state, SourceState::Failed(_)) {
            let _ = writeln!(out, "Agents read the source from their next session.");
        }
        out
    }
}

pub fn run(args: &[String]) -> i32 {
    match parse(args) {
        Ok(Parsed::Help) => {
            print!("{HELP}");
            0
        }
        Ok(Parsed::Path) => {
            println!("{}", Env::from_process().source().display());
            0
        }
        Ok(Parsed::Install { selection, dry_run }) => {
            let report = install(&Env::from_process(), selection, dry_run);
            print!("{}", report.render());
            report.exit_code()
        }
        Err(message) => {
            eprintln!("riff prompt: {message}\nRun `riff prompt --help` for usage.");
            exit::USAGE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(words: &[&str]) -> Vec<String> {
        words.iter().map(|word| (*word).to_string()).collect()
    }

    /// A fake home under `target/test-tmp`; no test touches the process
    /// environment or the real home.
    fn env_at(root: &Path) -> Env {
        Env {
            riff_home: root.join(".riff"),
            home: Some(root.to_path_buf()),
            claude_config_dir: None,
            codex_home: None,
            pi_agent_dir: None,
        }
    }

    fn fake_home(name: &str, agent_dirs: &[&str]) -> PathBuf {
        let root = crate::test_env::scratch_dir(&format!("prompt-{name}"));
        for dir in agent_dirs {
            std::fs::create_dir_all(root.join(dir)).unwrap();
        }
        root
    }

    const ALL_DIRS: [&str; 4] = [".claude", ".codex", ".gemini", ".pi/agent"];

    fn outcome(report: &Report, agent: Agent) -> &Outcome {
        &report
            .agents
            .iter()
            .find(|entry| entry.agent == agent)
            .unwrap()
            .outcome
    }

    #[test]
    fn the_template_is_marked_and_has_placeholders() {
        assert!(TEMPLATE.starts_with("<!-- riff-global-prompt:v1 -->\n"));
        assert!(TEMPLATE.contains("[fill in]"));
        assert!(
            !TEMPLATE.starts_with("---"),
            "no frontmatter: Antigravity reads it as rules text"
        );
    }

    #[test]
    fn install_is_the_default_command_shape_and_usage_errors_are_reported() {
        assert_eq!(
            parse(&args(&["install"])),
            Ok(Parsed::Install {
                selection: Selection::All,
                dry_run: false
            })
        );
        assert_eq!(
            parse(&args(&["install", "--agent=pi", "--dry-run"])),
            Ok(Parsed::Install {
                selection: Selection::One(Agent::Pi),
                dry_run: true
            })
        );
        assert_eq!(
            parse(&args(&["install", "--agent", "codex"])),
            Ok(Parsed::Install {
                selection: Selection::One(Agent::Codex),
                dry_run: false
            })
        );
        assert_eq!(parse(&args(&["path"])), Ok(Parsed::Path));
        assert_eq!(parse(&args(&["install", "--help"])), Ok(Parsed::Help));
        assert!(parse(&args(&[])).is_err());
        assert!(parse(&args(&["install", "--agent", "cursor"])).is_err());
        assert!(parse(&args(&["install", "--agent"])).is_err());
        assert!(parse(&args(&["install", "--force"])).is_err());
        assert!(parse(&args(&["path", "extra"])).is_err());
        assert!(parse(&args(&["uninstall"])).is_err());
    }

    #[test]
    fn agent_directories_follow_their_environment_variables() {
        let root = PathBuf::from("/home/u");
        let mut env = env_at(&root);
        assert_eq!(env.agent_dir(Agent::ClaudeCode), Some(root.join(".claude")));
        assert_eq!(env.agent_dir(Agent::Codex), Some(root.join(".codex")));
        assert_eq!(
            env.agent_dir(Agent::Antigravity),
            Some(root.join(".gemini"))
        );
        assert_eq!(
            env.agent_dir(Agent::Pi),
            Some(root.join(".pi").join("agent"))
        );
        env.claude_config_dir = Some(PathBuf::from("/c"));
        env.codex_home = Some(PathBuf::from("/x"));
        env.pi_agent_dir = Some(PathBuf::from("/p"));
        assert_eq!(env.agent_dir(Agent::ClaudeCode), Some(PathBuf::from("/c")));
        assert_eq!(env.agent_dir(Agent::Codex), Some(PathBuf::from("/x")));
        assert_eq!(env.agent_dir(Agent::Pi), Some(PathBuf::from("/p")));
    }

    #[cfg(unix)]
    #[test]
    fn every_installed_agent_reads_the_one_source() {
        let root = fake_home("all", &ALL_DIRS);
        let env = env_at(&root);
        let report = install(&env, Selection::All, false);
        assert_eq!(report.exit_code(), 0, "{}", report.render());
        assert_eq!(report.source_state, SourceState::Written);
        let source = root.join(".riff/global-prompt.md");
        assert_eq!(std::fs::read_to_string(&source).unwrap(), TEMPLATE);
        std::fs::write(&source, "edited once\n").unwrap();
        for target in [
            ".claude/CLAUDE.md",
            ".codex/AGENTS.md",
            ".gemini/AGENTS.md",
            ".pi/agent/AGENTS.md",
        ] {
            let path = root.join(target);
            assert!(
                std::fs::symlink_metadata(&path)
                    .unwrap()
                    .file_type()
                    .is_symlink(),
                "{target}"
            );
            assert_eq!(
                std::fs::read_to_string(&path).unwrap(),
                "edited once\n",
                "{target}"
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn a_second_install_keeps_the_edited_source_and_reports_already_linked() {
        let root = fake_home("again", &[".claude"]);
        let env = env_at(&root);
        install(&env, Selection::All, false);
        let source = root.join(".riff/global-prompt.md");
        std::fs::write(&source, "my rules\n").unwrap();
        let second = install(&env, Selection::All, false);
        assert_eq!(second.source_state, SourceState::Kept);
        assert_eq!(std::fs::read_to_string(&source).unwrap(), "my rules\n");
        assert_eq!(outcome(&second, Agent::ClaudeCode), &Outcome::AlreadyLinked);
        assert_eq!(second.placeholders, 0);
        assert_eq!(second.exit_code(), 0);
    }

    #[cfg(unix)]
    #[test]
    fn an_existing_instructions_file_is_never_overwritten() {
        let root = fake_home("kept", &[".claude", ".codex"]);
        std::fs::write(root.join(".claude/CLAUDE.md"), "the user's own\n").unwrap();
        let report = install(&env_at(&root), Selection::All, false);
        assert_eq!(outcome(&report, Agent::ClaudeCode), &Outcome::Kept);
        assert_eq!(
            std::fs::read_to_string(root.join(".claude/CLAUDE.md")).unwrap(),
            "the user's own\n"
        );
        // The other agent is still linked; the run as a whole needs attention.
        assert_eq!(outcome(&report, Agent::Codex), &Outcome::Linked);
        assert_eq!(report.exit_code(), exit::OTHER);
        assert!(
            report.render().contains("To finish: merge"),
            "{}",
            report.render()
        );
    }

    #[cfg(unix)]
    #[test]
    fn a_link_to_another_file_is_kept() {
        let root = fake_home("other-link", &[".claude"]);
        std::fs::write(root.join("elsewhere.md"), "elsewhere\n").unwrap();
        std::os::unix::fs::symlink(root.join("elsewhere.md"), root.join(".claude/CLAUDE.md"))
            .unwrap();
        let report = install(&env_at(&root), Selection::All, false);
        assert_eq!(outcome(&report, Agent::ClaudeCode), &Outcome::Kept);
        assert_eq!(
            std::fs::read_to_string(root.join(".claude/CLAUDE.md")).unwrap(),
            "elsewhere\n"
        );
    }

    #[cfg(unix)]
    #[test]
    fn pi_is_blocked_when_the_link_would_replace_its_claude_md() {
        let root = fake_home("pi-claude", &[".pi/agent"]);
        std::fs::write(root.join(".pi/agent/CLAUDE.md"), "pi rules\n").unwrap();
        let report = install(&env_at(&root), Selection::All, false);
        assert!(
            matches!(outcome(&report, Agent::Pi), Outcome::Blocked(reason) if reason.contains("CLAUDE.md")),
            "{}",
            report.render()
        );
        assert!(!present(&root.join(".pi/agent/AGENTS.md")));
        assert_eq!(report.exit_code(), exit::OTHER);
    }

    #[cfg(unix)]
    #[test]
    fn pi_is_blocked_by_an_override_even_when_already_linked() {
        let root = fake_home("pi-override", &[".pi/agent"]);
        let env = env_at(&root);
        assert_eq!(
            outcome(&install(&env, Selection::All, false), Agent::Pi),
            &Outcome::Linked
        );
        std::fs::write(root.join(".pi/agent/AGENTS.override.md"), "").unwrap();
        assert!(matches!(
            outcome(&install(&env, Selection::All, false), Agent::Pi),
            Outcome::Blocked(_)
        ));
    }

    #[cfg(unix)]
    #[test]
    fn codex_is_blocked_only_by_a_non_empty_override() {
        let root = fake_home("codex-override", &[".codex"]);
        let env = env_at(&root);
        std::fs::write(root.join(".codex/AGENTS.override.md"), "").unwrap();
        assert_eq!(
            outcome(&install(&env, Selection::All, false), Agent::Codex),
            &Outcome::Linked
        );
        std::fs::write(root.join(".codex/AGENTS.override.md"), "temporary\n").unwrap();
        assert!(matches!(
            outcome(&install(&env, Selection::All, false), Agent::Codex),
            Outcome::Blocked(_)
        ));
    }

    #[cfg(unix)]
    #[test]
    fn antigravity_names_the_other_global_rules_files_it_also_loads() {
        let root = fake_home("antigravity", &[".gemini/config"]);
        std::fs::write(root.join(".gemini/GEMINI.md"), "old rules\n").unwrap();
        let report = install(&env_at(&root), Selection::All, false);
        let entry = report
            .agents
            .iter()
            .find(|entry| entry.agent == Agent::Antigravity)
            .unwrap();
        assert_eq!(entry.outcome, Outcome::Linked);
        assert_eq!(entry.notes.len(), 1, "{:?}", entry.notes);
        assert!(entry.notes[0].contains("GEMINI.md"));
    }

    #[cfg(unix)]
    #[test]
    fn missing_agent_directories_are_skipped_unless_the_agent_is_named() {
        let root = fake_home("missing", &[".claude"]);
        let env = env_at(&root);
        let all = install(&env, Selection::All, false);
        assert_eq!(outcome(&all, Agent::Codex), &Outcome::NotInstalled);
        assert!(!root.join(".codex").exists());
        assert_eq!(all.exit_code(), 0, "{}", all.render());

        let named = install(&env, Selection::One(Agent::Codex), false);
        assert_eq!(outcome(&named, Agent::Codex), &Outcome::Linked);
        assert!(
            std::fs::symlink_metadata(root.join(".codex/AGENTS.md"))
                .unwrap()
                .file_type()
                .is_symlink()
        );
    }

    #[test]
    fn no_agent_directory_at_all_needs_attention() {
        let root = fake_home("none", &[]);
        let report = install(&env_at(&root), Selection::All, true);
        assert!(
            report
                .agents
                .iter()
                .all(|entry| entry.outcome == Outcome::NotInstalled)
        );
        assert_eq!(report.exit_code(), exit::OTHER);
        assert!(report.render().contains("No agent directory found"));
    }

    #[test]
    fn a_dry_run_changes_nothing() {
        let root = fake_home("dry", &ALL_DIRS);
        let report = install(&env_at(&root), Selection::All, true);
        assert_eq!(report.exit_code(), 0, "{}", report.render());
        assert_eq!(report.source_state, SourceState::Written);
        assert!(
            report
                .agents
                .iter()
                .all(|entry| entry.outcome == Outcome::Linked)
        );
        assert!(!root.join(".riff").exists());
        for target in [
            ".claude/CLAUDE.md",
            ".codex/AGENTS.md",
            ".gemini/AGENTS.md",
            ".pi/agent/AGENTS.md",
        ] {
            assert!(!present(&root.join(target)), "{target}");
        }
        assert!(report.render().contains("would link"));
        assert!(report.placeholders > 0);
    }

    #[test]
    fn a_source_path_that_is_not_a_file_fails_and_links_nothing() {
        let root = fake_home("source-dir", &[".codex"]);
        std::fs::create_dir_all(root.join(".riff/global-prompt.md")).unwrap();
        let report = install(&env_at(&root), Selection::All, false);
        assert!(
            matches!(&report.source_state, SourceState::Failed(reason) if reason.contains("not a readable file")),
            "{:?}",
            report.source_state
        );
        assert!(!present(&root.join(".codex/AGENTS.md")));
        assert_eq!(report.exit_code(), exit::OTHER);
    }

    #[test]
    fn a_dry_run_reports_an_existing_file_as_kept_not_linked() {
        let root = fake_home("dry-kept", &[".codex"]);
        std::fs::write(root.join(".codex/AGENTS.md"), "the user's own\n").unwrap();
        let report = install(&env_at(&root), Selection::All, true);
        assert_eq!(outcome(&report, Agent::Codex), &Outcome::Kept);
        assert_eq!(report.exit_code(), exit::OTHER);
    }

    #[cfg(unix)]
    #[test]
    fn the_source_file_is_private() {
        use std::os::unix::fs::PermissionsExt;
        let root = fake_home("private", &[".claude"]);
        install(&env_at(&root), Selection::All, false);
        let mode = std::fs::metadata(root.join(".riff/global-prompt.md"))
            .unwrap()
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(mode, 0o600);
    }
}
