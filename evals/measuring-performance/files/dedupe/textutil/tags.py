from .dedupe import dedupe


def normalize_tags(raw_tags):
    """Tags as the user typed them: trimmed, lowercased, duplicates removed, in order."""
    return dedupe(t.strip().lower() for t in raw_tags if t.strip())
