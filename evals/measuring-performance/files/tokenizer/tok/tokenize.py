import re
import unicodedata

_WORD = re.compile(r"\w+(?:['’]\w+)*", re.UNICODE)


def tokenize(text):
    """Lowercased word tokens, NFKC-normalized, apostrophes kept inside words."""
    normalized_text = unicodedata.normalize("NFKC", text)
    return [m.group(0).lower() for m in _WORD.finditer(normalized_text)]
