import re
import unicodedata

_NON = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    ascii_only = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    return _NON.sub("-", ascii_only.lower()).strip("-")
