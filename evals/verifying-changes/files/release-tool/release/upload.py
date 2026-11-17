import os
import urllib.request
from pathlib import Path


def upload(dist: Path, version: str) -> None:
    """PUT every file in dist/ to the release store."""
    base = os.environ["RELEASE_URL"].rstrip("/")
    for f in sorted(dist.iterdir()):
        req = urllib.request.Request(f"{base}/{version}/{f.name}", data=f.read_bytes(), method="PUT")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"upload of {f.name} failed: {resp.status}")
