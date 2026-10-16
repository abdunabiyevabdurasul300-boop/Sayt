"""DONUZ Web API entry point for a separate Render Web Service.

Set the same DATABASE_URL and required API environment variables as the bot
service. This process does not start Telegram polling.
"""
import logging
import os
from http.server import HTTPServer

import bot as core

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main():
    # The web and bot services must point to the SAME PostgreSQL database.
    if not core.DATABASE_URL:
        raise SystemExit("DATABASE_URL kiritilmagan: bot va web servisda bir xil PostgreSQL URL bo'lishi kerak.")

    core.CURRENT_DB.set(core.MAIN_DB)
    core.init_db()
    core.ensure_external_schema()
    core.ensure_pubg()
    core.ensure_mobile_legends()

    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), core.WebAPIHandler)
    core.log.info("DONUZ Web API alohida servisda ishga tushdi: 0.0.0.0:%s", port)
    server.serve_forever()


if __name__ == "__main__":
    main()
