"""Top-level WSGI entrypoint compatibility for the app package."""

from app.backend.api import create_app

# Allows Gunicorn to load this package with: gunicorn app:app
app = create_app()

__all__ = ["app", "create_app"]
