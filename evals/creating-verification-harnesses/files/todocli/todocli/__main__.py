import argparse
import sys

from . import core

p = argparse.ArgumentParser(prog="todocli")
sub = p.add_subparsers(dest="cmd", required=True)
sub.add_parser("add").add_argument("text")
sub.add_parser("list")
sub.add_parser("done").add_argument("id", type=int)
args = p.parse_args()
if args.cmd == "add":
    print(f"added {core.add(args.text)['id']}")
elif args.cmd == "list":
    for i in core.load():
        print(f"[{'x' if i['done'] else ' '}] {i['id']} {i['text']}")
else:
    try:
        core.done(args.id)
        print(f"done {args.id}")
    except KeyError:
        sys.exit(f"error: no item {args.id}")
