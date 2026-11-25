"""Response helpers for the JSON API."""


def ok(data, status: int = 200) -> tuple[int, dict]:
    return status, {"data": data}


def error(status: int, message: str) -> tuple[int, dict]:
    return status, {"error": message}
