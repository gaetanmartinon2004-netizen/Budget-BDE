#!/usr/bin/env python3
"""WSGI entrypoint for local dev and deployment."""

from __future__ import annotations

import os

from app.backend.api import create_app
from app.backend.database import initialize_database


app = create_app()

# Initialize database at module load time
# This ensures it runs with Gunicorn (which never enters the if __name__ block)
print("[MAIN] Initializing database at module load time...")
initialize_database()
print("[MAIN] Database initialization complete")


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
