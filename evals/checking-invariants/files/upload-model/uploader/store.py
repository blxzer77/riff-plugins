class MemoryStore:
    """Stand-in for the object store: temp objects and published objects."""

    def __init__(self):
        self.temp = {}
        self.published = {}
        self._next = 0

    def create_temp(self, name: str) -> str:
        self._next += 1
        key = f"tmp/{name}.{self._next}"
        self.temp[key] = b""
        return key

    def append(self, key: str, chunk: bytes) -> None:
        self.temp[key] += chunk

    def publish(self, key: str, name: str) -> None:
        self.published[name] = self.temp[key]

    def unpublish(self, name: str) -> None:
        self.published.pop(name, None)

    def delete_temp(self, key: str) -> None:
        self.temp.pop(key, None)
