class UploadError(Exception):
    pass


class Session:
    """idle -> uploading -> publishing -> committed, or cancelled from the UI."""

    def __init__(self, store, name: str):
        self.store = store
        self.name = name
        self.state = "idle"
        self.temp = None

    def start(self) -> None:
        if self.state != "idle":
            raise UploadError(f"cannot start from {self.state}")
        self.temp = self.store.create_temp(self.name)
        self.state = "uploading"

    def write(self, chunk: bytes) -> None:
        if self.state != "uploading":
            raise UploadError(f"cannot write while {self.state}")
        self.store.append(self.temp, chunk)

    def publish(self) -> None:
        if self.state != "uploading":
            raise UploadError(f"cannot publish while {self.state}")
        self.state = "publishing"
        self.store.publish(self.temp, self.name)

    def mark_committed(self) -> None:
        if self.state != "publishing":
            raise UploadError(f"cannot commit while {self.state}")
        self.store.delete_temp(self.temp)
        self.state = "committed"

    def cancel(self) -> None:
        """Called from the UI's cancel button."""
        if self.state not in ("uploading", "publishing"):
            raise UploadError(f"cannot cancel while {self.state}")
        self.store.delete_temp(self.temp)
        self.state = "cancelled"
