"""DONUZ website + API service; shares PostgreSQL with bot.py."""
import logging, mimetypes, os
from pathlib import Path
from http.server import HTTPServer
from urllib.parse import urlparse
import bot as core

ROOT = Path(__file__).resolve().parent / "static"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class DONUZHandler(core.WebAPIHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        files = {"/": "index.html", "/index.html": "index.html", "/style.css": "style.css", "/script.js": "script.js"}
        if path in files:
            file_path = ROOT / files[path]
            try:
                data = file_path.read_bytes()
            except OSError:
                return self._reply({"ok": False, "error": "Sayt fayli topilmadi: " + files[path]}, 404)
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

def main():
    if not core.DATABASE_URL:
        raise SystemExit("DATABASE_URL yo'q. Render Environment Variables sozlang.")
    core.CURRENT_DB.set(core.MAIN_DB)
    core.init_db()
    core.ensure_external_schema()
    core.ensure_pubg()
    core.ensure_mobile_legends()
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), DONUZHandler)
    core.log.info("DONUZ Web/API ishga tushdi: 0.0.0.0:%s", port)
    server.serve_forever()

if __name__ == "__main__":
    main()
