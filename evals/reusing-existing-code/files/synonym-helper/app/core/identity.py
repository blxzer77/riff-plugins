import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def canonicalize_account_slug(raw: str, *, max_length: int = 40) -> str:
    """Normalize a team or account handle into lowercase ASCII kebab-case."""
    text = unicodedata.normalize("NFKC", raw).strip()
    ascii_text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = _NON_ALNUM.sub("-", ascii_text).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    if len(slug) < 3:
        raise ValueError(f"handle too short after normalization: {raw!r}")
    return slug
