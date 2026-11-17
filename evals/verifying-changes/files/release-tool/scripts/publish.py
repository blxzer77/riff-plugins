"""Publish a release: bump the version, update the changelog, tag, upload."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from release.upload import upload  # noqa: E402


def bump(version: str) -> str:
    major, minor, patch = (int(p) for p in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)

    meta_file = ROOT / "release.json"
    meta = json.loads(meta_file.read_text())
    new = bump(meta["version"])
    meta["version"] = new
    meta_file.write_text(json.dumps(meta, indent=2) + "\n")
    with open(ROOT / "CHANGELOG.md", "a") as f:
        f.write(f"\n## {new}\n{args.notes}\n")
    subprocess.run(["git", "tag", f"v{new}"], cwd=ROOT, check=True)
    upload(ROOT / "dist", new)
    print(f"published {meta['name']} {new}")


if __name__ == "__main__":
    main()
