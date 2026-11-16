#!/usr/bin/env python3
"""contacts eval: quoted fields parse exactly, nothing is silently dropped (hidden oracle)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import os, sys, tempfile, unittest
from contacts.importer import load

def write(text):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path

got = [(c.name, c.email, c.company) for c in load("data/export.csv")]
assert len(got) == 6, got
assert ("Zoë Martin, PhD", "zoe@example.fr", "Laboratoire Lumière") in got, got
assert ("Sørensen, Mette", "mette@example.dk", "Nordlys") in got, got
assert ("Jürgen Weiß", "juergen@example.de", "Müller & Söhne GmbH") in got, got

hidden = write('name,email,company\r\n'
               '"Dana ""DJ"" Okafor",Dana@Example.com,"Smith, Jones & Co"\r\n'
               '\r\n'
               'Łucja Nowak,lucja@example.pl,Żabka\r\n')
got = [(c.name, c.email, c.company) for c in load(hidden)]
assert got == [('Dana "DJ" Okafor', "dana@example.com", "Smith, Jones & Co"),
               ("Łucja Nowak", "lucja@example.pl", "Żabka")], got

for bad in ('name,email,company\nAnn Lee,ann@example.com\n',
            'name,email,company\nAnn Lee,not-an-email,Initech\n'):
    path = write(bad)
    try:
        rows = load(path)
    except Exception:
        continue
    raise AssertionError(f"malformed row accepted silently: {bad!r} -> {rows!r}")

suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
assert r.wasSuccessful() and r.testsRun >= 3, (r.failures, r.errors)
'''
finish(run_probe(probe), "quoted and unicode rows import exactly; malformed rows still fail",
       "import is still wrong, lossy, or silently drops bad rows")
