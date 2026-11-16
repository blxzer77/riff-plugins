from .summary import summarize


def region_totals(rows):
    """Dashboard endpoint: totals per region, largest first."""
    totals = summarize(rows)
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
