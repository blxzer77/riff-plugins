import json
import os
from pathlib import Path


def path() -> Path:
    return Path(os.environ.get("TODO_FILE", "todo.json"))


def load():
    p = path()
    return json.loads(p.read_text()) if p.exists() else []


def save(items):
    path().write_text(json.dumps(items, indent=2))


def add(text):
    items = load()
    item = {"id": max((i["id"] for i in items), default=0) + 1, "text": text, "done": False}
    items.append(item)
    save(items)
    return item


def done(item_id):
    items = load()
    for i in items:
        if i["id"] == item_id:
            i["done"] = True
            save(items)
            return i
    raise KeyError(item_id)
