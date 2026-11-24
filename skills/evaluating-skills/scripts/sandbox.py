"""Fresh per-run working directories, kept outside the repository under test."""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path

from common import HarnessError, git

# The agent sees this path and the initial commit below. Agents behave differently
# when they can tell they are being evaluated, so neither may name an eval, a
# fixture, a skill or the harness (tests/test_harness_blinding.py).
DEFAULT_ROOT = Path.home() / ".cache" / "riff" / "checkouts"
# Git directory, next to the working directory, recording the state the agent starts from.
START_GIT = "start.git"


def copy_fixture(skill_dir: Path, files: list[str], dest: Path) -> None:
    """Copy eval input files into `dest`: files by basename, directories by contents."""
    dest.mkdir(parents=True, exist_ok=True)
    root = Path(skill_dir).resolve()
    for rel in files or []:
        src = (root / rel).resolve()
        if root not in src.parents and src != root:
            raise HarnessError(f"eval file {rel!r} escapes the skill directory")
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        elif src.is_file():
            shutil.copy2(src, dest / src.name)
        else:
            raise HarnessError(f"eval file not found: {rel}")


SETUP_SCRIPT = "setup.sh"


@contextmanager
def sandbox(root: Path, fixture: Path | None = None):
    """Yield a git-initialized working directory with the fixture committed; delete it after.

    If the fixture contains `setup.sh`, it runs after the initial commit (with git
    identity configured) and is then removed, so a fixture can stage changes, create
    branches, or leave uncommitted edits without the agent seeing the script.

    The state the agent starts from (fixture plus setup) is then recorded in a git
    directory outside the working directory; see `diff_against_fixture`.
    """
    base = Path(root).expanduser() / uuid.uuid4().hex[:12]
    workdir = base / "work"
    workdir.mkdir(parents=True)
    try:
        if fixture is not None and fixture.is_dir():
            shutil.copytree(fixture, workdir, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(SETUP_SCRIPT))
        git(["init", "-q", "-b", "main"], workdir)
        git(["add", "-A"], workdir)
        git(["commit", "-q", "--no-gpg-sign", "--allow-empty", "-m", "Initial commit"], workdir)
        setup = fixture / SETUP_SCRIPT if fixture is not None else None
        if setup is not None and setup.is_file():
            env = dict(os.environ, GIT_AUTHOR_NAME="dev", GIT_AUTHOR_EMAIL="dev@localhost",
                       GIT_COMMITTER_NAME="dev", GIT_COMMITTER_EMAIL="dev@localhost",
                       GIT_CONFIG_GLOBAL="/dev/null")
            proc = subprocess.run(["bash", str(setup.resolve())], cwd=workdir, env=env,
                                  capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                raise HarnessError(f"fixture setup failed: {proc.stderr[-500:]}")
        shutil.copytree(workdir / ".git", base / START_GIT, symlinks=True)
        _start_git(workdir, ["add", "-A"])
        _start_git(workdir, ["commit", "-q", "--no-gpg-sign", "--allow-empty", "-m", "start"])
        yield workdir
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _start_git(workdir: Path, args: list[str]) -> str:
    """Run git against the harness's copy of the repository, never the agent's.

    After a run the agent's `.git` is untrusted: its config can name commands
    (`core.fsmonitor`, filter and diff drivers) that git would execute here.
    """
    return git([f"--git-dir={workdir.parent / START_GIT}", f"--work-tree={workdir}", *args],
               workdir)


def diff_against_fixture(workdir: Path) -> str:
    """The agent's changes: the work tree against the state it started from.

    Changes made by the fixture's `setup.sh` are part of that start state, so they
    are not attributed to the agent. A nested repository is an error: git would
    record it as a single gitlink and hide every change inside it.
    """
    for root, dirs, files in os.walk(workdir):
        here = Path(root)
        if here == workdir:
            dirs[:] = [d for d in dirs if d != ".git"]
            continue
        if ".git" in dirs or ".git" in files:
            nested = here.relative_to(workdir).as_posix()
            raise HarnessError(f"nested git repository at {nested}: changes.patch cannot "
                               "show the changes inside it")
    _start_git(workdir, ["add", "-A"])
    return _start_git(workdir, ["diff", "--cached", "--binary", "--no-ext-diff",
                                "--no-textconv", "HEAD"])
