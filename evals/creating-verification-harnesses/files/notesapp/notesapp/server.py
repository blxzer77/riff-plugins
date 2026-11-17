import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import VERSION
from .store import Store


def make_handler(store: Store, data_dir: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/health":
                return self._send(200, {"ok": True, "version": VERSION, "data": data_dir})
            if url.path == "/notes":
                q = parse_qs(url.query).get("q", [""])[0]
                return self._send(200, store.search(q) if q else store.all())
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if urlparse(self.path).path != "/notes":
                return self._send(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                note = store.add(data.get("title", ""), data.get("body", ""))
            except (ValueError, json.JSONDecodeError) as e:
                return self._send(400, {"error": str(e)})
            self._send(201, note)

    return Handler


def serve(port: int, data_dir: str):
    store = Store(data_dir)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(store, data_dir))
    print(f"notesapp {VERSION} listening on http://127.0.0.1:{port} (data: {data_dir})", flush=True)
    server.serve_forever()
