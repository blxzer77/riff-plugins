import json
from pathlib import Path

from . import defaults


def load() -> dict:
    """Settings shipped with the package, falling back to the built-in defaults."""
    path = Path(__file__).with_name("default_config.json")
    cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {
        "format": cfg.get("format", defaults.DEFAULT_FORMAT),
        "page_size": cfg.get("page_size", defaults.PAGE_SIZE),
        "store": cfg.get("store", "data/notes.json"),
    }
