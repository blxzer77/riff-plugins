import json
import os
import urllib.request


def upload_report(report: dict, url: str | None = None, opener=urllib.request.urlopen) -> int:
    """PUT the report as JSON to the report store. Returns the HTTP status."""
    url = url or os.environ["REPORT_STORE_URL"]
    body = json.dumps(report).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="PUT",
                                     headers={"Content-Type": "application/json"})
    with opener(request, timeout=10) as response:
        return response.status
