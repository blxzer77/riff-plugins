def dedupe(items):
    """Drop repeated items, keeping the first occurrence."""
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def dedupe_fast(items):
    """Faster dedupe (added by Sam)."""
    return list(set(items))
