import csv
import sys
from itertools import groupby

from .summary import summarize


def read(path):
    with open(path, newline="") as f:
        return [{"month": r["month"], "region": r["region"], "amount": int(r["amount"])}
                for r in csv.DictReader(f)]


rows = sorted(read(sys.argv[1]), key=lambda r: r["month"])
for month, group in groupby(rows, key=lambda r: r["month"]):
    print(month)
    for region, amount in sorted(summarize(list(group)).items()):
        print(f"  {region:<4} {amount:>8}")
