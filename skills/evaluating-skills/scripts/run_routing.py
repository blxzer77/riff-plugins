#!/usr/bin/env python3
"""Measure routing across a suite: install every skill at once and record which
skills the agent loads for each skill's trigger queries.

run_triggers.py installs one skill, so it shows whether a description is found but
not whether a neighboring skill takes the query instead. This script installs every
skill under --suite together, runs each skill's trigger queries (with their
fixtures), and reports per query which skills were loaded, plus a matrix of the
query's owner against the skills loaded.

Example:
    run_routing.py --suite skills --agent claude-code --set validation --runs 1
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from agents import add_agent_args, adapter_from_args, execute
from common import HarnessError, die, evals_dir, read_frontmatter, read_json, write_json
from sandbox import DEFAULT_ROOT, sandbox

NONE = "(none)"


def route_once(query, skills, adapter, model, timeout, root, fixture):
    """One run with every skill installed: (skills loaded, failed, process, agent error)."""
    with sandbox(root, fixture) as workdir:
        extra = adapter.install_suite(skills, workdir)
        argv, stdin_text = adapter.command(query, workdir, model, extra)
        proc = execute(argv, stdin_text, workdir, timeout, adapter.env())
        result = adapter.parse(proc.stdout, workdir)
        adapter.uninstall(workdir)
    loaded = set(result.invoked_skill if adapter.native_invocation else result.read_skill)
    failed = not loaded and not proc.stopped_early and not result.asked_user and (
        proc.timed_out or proc.exit_code != 0 or result.error is not None)
    return loaded, failed, proc, result.error


def route(query, skills, adapter, model, timeout, root, fixture, retries, backoff):
    for attempt in range(max(0, retries) + 1):
        if attempt:
            time.sleep(backoff * attempt)
        loaded, failed, proc, error = route_once(query, skills, adapter, model, timeout,
                                                 root, fixture)
        if not failed or proc.timed_out:
            break
    return loaded, failed, proc, error, attempt


def load_queries(skill_dirs: list[Path], names: dict[Path, str], wanted_set: str) -> list[dict]:
    queries = []
    for skill_dir in skill_dirs:
        eval_root = evals_dir(skill_dir)
        path = eval_root / "trigger-queries.json"
        if not path.is_file():
            print(f"warning: {names[skill_dir]} has no {path}; its queries are skipped",
                  file=sys.stderr)
            continue
        for q in read_json(path):
            if wanted_set != "all" and q.get("set") != wanted_set:
                continue
            fixture = None
            if q.get("fixture") is not None:
                fixture = (eval_root / q["fixture"]).resolve()
                if eval_root.resolve() not in fixture.parents or not fixture.is_dir():
                    die(f"{names[skill_dir]}: query fixture must be a directory inside "
                        f"the eval directory: {q['fixture']!r}")
            queries.append({"owner": names[skill_dir], "query": q["query"],
                            "should_trigger": bool(q["should_trigger"]), "set": q.get("set"),
                            "fixture": fixture})
    return queries


def matrix_text(rows: list[str], columns: list[str], cells: dict) -> str:
    width = max(len(r) for r in rows) + 2
    head = "owner \\ loaded".ljust(width) + " ".join(c[:10].rjust(10) for c in columns)
    lines = [head]
    for row in rows:
        lines.append(row.ljust(width) + " ".join(str(cells.get((row, c), 0)).rjust(10)
                                                 for c in columns))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", required=True, type=Path,
                        help="directory whose subdirectories are the skills to install together")
    parser.add_argument("--set", choices=["train", "validation", "all"], default="validation")
    parser.add_argument("--runs", type=int, default=1, help="runs per query")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=300, help="seconds per run")
    parser.add_argument("--retries", type=int, default=2,
                        help="re-run a run that ended in an agent error (rate limit, API failure)")
    parser.add_argument("--retry-backoff", type=float, default=30,
                        help="seconds to wait before a retry, multiplied by the attempt number")
    parser.add_argument("--workspace", type=Path, help="default: .workspace/_suite")
    parser.add_argument("--sandbox-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    add_agent_args(parser)
    args = parser.parse_args()

    skill_dirs = sorted(p.resolve() for p in args.suite.iterdir() if (p / "SKILL.md").is_file())
    if len(skill_dirs) < 2:
        die(f"need at least two skills under {args.suite}")
    try:
        names = {d: read_frontmatter(d).get("name") or d.name for d in skill_dirs}
        adapter = adapter_from_args(args)
    except HarnessError as exc:
        die(str(exc))
    duplicates = sorted(n for n, k in Counter(names.values()).items() if k > 1)
    if duplicates:
        die(f"several skills share the name {', '.join(duplicates)}; names must be unique")
    queries = load_queries(skill_dirs, names, args.set)
    if not queries:
        die(f"no trigger queries in set '{args.set}'")
    if args.dry_run:
        print(f"{len(skill_dirs)} skills installed together: {', '.join(names.values())}")
        print(f"{len(queries)} queries x {args.runs} runs = {len(queries) * args.runs} agent runs, "
              f"set={args.set}, agent={adapter.name}")
        return 0

    per_query = [{"loaded": Counter(), "runs": 0, "errors": 0} for _ in queries]
    infra_errors = retried_runs = 0
    with tempfile.TemporaryDirectory(prefix="riff-routing-skills-") as tmp:
        installed = []
        for skill_dir in skill_dirs:
            copy = Path(tmp) / skill_dir.name
            shutil.copytree(skill_dir, copy, ignore=shutil.ignore_patterns("evals", "__pycache__"))
            installed.append(copy)
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            futures = {pool.submit(route, q["query"], installed, adapter, args.model, args.timeout,
                                   args.sandbox_root, q["fixture"], args.retries,
                                   args.retry_backoff): i
                       for i, q in enumerate(queries) for _ in range(args.runs)}
            for done, future in enumerate(as_completed(futures), 1):
                i = futures[future]
                try:
                    loaded, failed, proc, agent_error, retries = future.result()
                except HarnessError as exc:
                    infra_errors += 1
                    print(f"error: {exc}", file=sys.stderr)
                    continue
                retried_runs += int(retries > 0)
                if failed:
                    infra_errors += 1
                    per_query[i]["errors"] += 1
                    detail = agent_error or proc.stderr.strip()[-200:]
                    print(f"error: {queries[i]['owner']} query: exit={proc.exit_code} "
                          f"timed_out={proc.timed_out}: {detail[:200]}", file=sys.stderr)
                    continue
                per_query[i]["runs"] += 1
                per_query[i]["loaded"].update(loaded or {NONE})
                if done % 10 == 0:
                    print(f"{done}/{len(futures)} runs done", file=sys.stderr)

    results, cells = [], Counter()
    for q, counts in zip(queries, per_query):
        loaded = dict(sorted(counts["loaded"].items()))
        results.append({"owner": q["owner"], "query": q["query"],
                        "should_trigger": q["should_trigger"], "set": q["set"],
                        "runs": counts["runs"], "errors": counts["errors"], "loaded": loaded})
        if q["should_trigger"]:
            for skill, n in loaded.items():
                cells[(q["owner"], skill)] += n

    owners = sorted(set(names.values()))
    summary = {"queries": len(results), "infra_errors": infra_errors, "retried_runs": retried_runs}
    positives = [r for r in results if r["should_trigger"] and r["runs"]]
    negatives = [r for r in results if not r["should_trigger"] and r["runs"]]
    summary["owner_loaded_runs"] = sum(r["loaded"].get(r["owner"], 0) for r in positives)
    summary["positive_runs"] = sum(r["runs"] for r in positives)
    summary["taken_by_another_runs"] = sum(
        sum(n for s, n in r["loaded"].items() if s not in (r["owner"], NONE)) for r in positives)
    summary["negative_owner_loaded_runs"] = sum(r["loaded"].get(r["owner"], 0) for r in negatives)
    summary["negative_runs"] = sum(r["runs"] for r in negatives)

    report = {"skills": owners, "agent": adapter.name, "model": args.model, "set": args.set,
              "runs_per_query": args.runs, "results": results,
              "matrix": {f"{o} -> {s}": n for (o, s), n in sorted(cells.items())},
              "summary": summary}
    workspace = (args.workspace or Path(".workspace") / "_suite").resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = workspace / "routing" / f"{stamp}-{args.set}.json"
    write_json(out, report)

    print("Positive queries: runs in which each skill was loaded")
    print(matrix_text(owners, owners + [NONE], cells))
    print(f"\nowner loaded in {summary['owner_loaded_runs']}/{summary['positive_runs']} positive runs; "
          f"another skill loaded {summary['taken_by_another_runs']} times; "
          f"owner loaded in {summary['negative_owner_loaded_runs']}/{summary['negative_runs']} "
          f"negative runs")
    for r in results:
        others = {s: n for s, n in r["loaded"].items() if s not in (r["owner"], NONE)}
        if r["should_trigger"] and others or not r["should_trigger"] and r["loaded"].get(r["owner"]):
            print(f"  {r['owner']:24} {'+' if r['should_trigger'] else '-'} {r['loaded']}  "
                  f"{r['query'][:70]}")
    print(f"results: {out}")
    return 2 if infra_errors else 0


if __name__ == "__main__":
    sys.exit(main())
