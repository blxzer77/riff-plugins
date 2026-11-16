import sys

from .importer import load

contacts = load(sys.argv[1])
for c in contacts:
    print(f"{c.email}\t{c.name}\t{c.company}")
print(f"imported {len(contacts)} contacts", file=sys.stderr)
