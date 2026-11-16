import json


def render(notes, fmt):
    if fmt == "json":
        return json.dumps(notes, indent=2)
    if fmt == "table":
        rows = [f"{'ID':<4} {'TITLE':<24} TAGS"]
        rows += [f"{n['id']:<4} {n['title'][:24]:<24} {','.join(n['tags'])}" for n in notes]
        return "\n".join(rows)
    raise ValueError(f"unknown format: {fmt}")
