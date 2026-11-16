def summarize(rows, totals={}):
    """Total amount per region for the given rows."""
    for row in rows:
        totals[row["region"]] = totals.get(row["region"], 0) + row["amount"]
    return totals
