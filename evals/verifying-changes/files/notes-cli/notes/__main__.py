import argparse
import json
from pathlib import Path

from . import config
from .render import render


def main(argv=None):
    cfg = config.load()
    parser = argparse.ArgumentParser(prog="notes")
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--format", choices=["table", "json"], default=cfg["format"])
    args = parser.parse_args(argv)
    notes = json.loads(Path(cfg["store"]).read_text(encoding="utf-8"))[: cfg["page_size"]]
    print(render(notes, args.format))


main()
