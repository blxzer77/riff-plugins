"""Read the CRM contact export (CSV with a header row: name,email,company)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Contact:
    name: str
    email: str
    company: str


def parse_line(line: str) -> Contact:
    name, email, company = line.rstrip("\r\n").split(",")
    if "@" not in email:
        raise ValueError(f"bad email for {name!r}: {email!r}")
    return Contact(name.strip(), email.strip().lower(), company.strip())


def load(path: str) -> list[Contact]:
    with open(path, encoding="utf-8", newline="") as f:
        f.readline()  # header
        return [parse_line(line) for line in f if line.strip()]
