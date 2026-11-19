//! `riff` command-line entry point.

pub mod decisions;
pub mod hook;
pub mod setup;
pub mod web;

pub const HELP: &str = "\
Usage: riff <command> [args...]

Commands:
  web       Web search and verbatim page fetch (riff web --help)
  init      Write a starting configuration (never overwrites)
  hook      Host-agent hook adapter (riff hook --help)
  --version Print the version

Configuration: $RIFF_HOME/config.json (default ~/.riff/config.json).
";

/// `args` are the words after the program name. Returns the exit code.
pub fn main(args: Vec<String>) -> i32 {
    match args.first().map(String::as_str) {
        Some("web") => web::run(&args[1..]),
        Some("init") => setup::init(&args[1..]),
        Some("hook") => hook::run(&args[1..]),
        Some("--version" | "-V") => {
            println!("riff {}", env!("CARGO_PKG_VERSION"));
            0
        }
        Some("--help" | "-h" | "help") => {
            print!("{HELP}");
            0
        }
        Some(other) => {
            eprintln!("riff: unknown command `{other}`\n\n{HELP}");
            web::exit::USAGE
        }
        None => {
            eprint!("{HELP}");
            web::exit::USAGE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(words: &[&str]) -> Vec<String> {
        words.iter().map(|word| (*word).to_string()).collect()
    }

    #[test]
    fn dispatches_web_help_version_and_rejects_the_rest() {
        assert_eq!(main(args(&["web", "--help"])), 0);
        assert_eq!(main(args(&["web", "fetch"])), web::exit::USAGE);
        assert_eq!(main(args(&["--version"])), 0);
        assert_eq!(main(args(&["--help"])), 0);
        assert_eq!(main(args(&["nope"])), web::exit::USAGE);
        assert_eq!(main(Vec::new()), web::exit::USAGE);
    }
}
