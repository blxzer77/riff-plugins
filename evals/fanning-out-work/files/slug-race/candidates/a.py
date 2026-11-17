import re

_NON = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    return _NON.sub("-", title.lower()).strip("-")
