import argparse
import sys

from ledger.importer import import_statement


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ledger")
    commands = parser.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import", help="import a bank statement CSV")
    imp.add_argument("path")
    args = parser.parse_args(argv)
    result = import_statement(args.path)
    total = sum((t["amount"] for t in result.transactions), start=0)
    print(f"Imported {len(result.transactions)} transactions ({result.skipped} skipped), "
          f"total {total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
