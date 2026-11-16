from .dedupe import dedupe


def unique_terms(query):
    """Distinct search terms of a query."""
    return dedupe(query.lower().split())
