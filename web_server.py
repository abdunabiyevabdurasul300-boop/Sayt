"""DONUZ Web App + API entry point for a separate Render Web Service."""
import logging
import mimetypes
import os
from pathlib import Path
from http.server import HTTPServer
from urllib.parse import urlparse
import bot as core

ROOT = Path(__file__).resolve().parent / "static"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class DONUZHandler(core.WebAPIHandler):
    def do_HEAD(self):
        # Render health checks may use HEAD; return the same status/headers as GET.
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/style.css", "/script.js"):
            name = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
            file_path = ROOT / name
            try:
                data = file_path.read_bytes()
            except OSError:
                self.send_error(404, "Static file not found")
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return
        # API HEAD requests are treated as health-style GETs without a response body.
        self.send_response(200 if path == "/health" else 404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            return self._static("index.html")
        if path in ("/style.css", "/script.js"):
            return self._static(path.lstrip("/"))
        return super().do_GET()

    def _static(self, name):
        file_path = ROOT / name
        try:
            data = file_path.read_bytes()
        except OSError:
            return self._reply({"ok": False, "error": "Sayt fayli topilmadi: " + name}, 404)
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

def main():
    if not core.DATABASE_URL:
        raise SystemExit("DATABASE_URL kiritilmagan: web va bot servisida bir xil PostgreSQL URL bo‘lishi kerak.")
    core.CURRENT_DB.set(core.MAIN_DB)
    core.init_db()
    core.ensure_external_schema()
    core.ensure_pubg()
    core.ensure_mobile_legends()
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), DONUZHandler)
    core.log.info("DONUZ Web App + API ishga tushdi: 0.0.0.0:%s", port)
    server.serve_forever()

if __name__ == "__main__":
    main()
