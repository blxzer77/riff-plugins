import re
import unicodedata


def slugify(title: str) -> str:
    out = ""
    for ch in title:
        base = unicodedata.normalize("NFKD", ch)
        base = "".join(c for c in base if not unicodedata.combining(c))
        out += base.encode("ascii", "ignore").decode("ascii").lower()
    out = re.sub(r"[^a-z0-9]+", "-", out)
    return re.sub(r"^-+|-+$", "", out)
