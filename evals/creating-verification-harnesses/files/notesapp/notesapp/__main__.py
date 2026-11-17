import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from .server import serve


def call(method, path, payload=None):
    base = os.environ.get("NOTES_URL", "http://127.0.0.1:8765").rstrip("/")
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"error: {json.loads(e.read()).get('error')}")
    except urllib.error.URLError as e:
        sys.exit(f"error: cannot reach {base}: {e.reason}")


def main():
    p = argparse.ArgumentParser(prog="notesapp")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--data", default="./data")
    a = sub.add_parser("add")
    a.add_argument("title")
    a.add_argument("--body", default="")
    q = sub.add_parser("search")
    q.add_argument("query")
    args = p.parse_args()
    if args.cmd == "serve":
        serve(args.port, args.data)
    elif args.cmd == "add":
        note = call("POST", "/notes", {"title": args.title, "body": args.body})
        print(f"added #{note['id']}: {note['title']}")
    else:
        from urllib.parse import quote
        for n in call("GET", f"/notes?q={quote(args.query)}"):
            print(f"#{n['id']}\t{n['title']}")


main()
