import json
import threading
from pathlib import Path


class Store:
    """Notes kept in <data>/notes.json."""

    def __init__(self, data_dir: str):
        self.path = Path(data_dir) / "notes.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]")
        self._lock = threading.Lock()

    def all(self):
        return json.loads(self.path.read_text())

    def add(self, title: str, body: str = ""):
        title = title.strip()
        if not title:
            raise ValueError("title is required")
        with self._lock:
            notes = self.all()
            note = {"id": max((n["id"] for n in notes), default=0) + 1, "title": title, "body": body}
            notes.append(note)
            self.path.write_text(json.dumps(notes, indent=2))
        return note

    def search(self, query: str):
        q = query.lower()
        return [n for n in self.all() if q in n["title"].lower() or q in n["body"].lower()]
