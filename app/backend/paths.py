"""Paths and configuration."""

from pathlib import Path

def get_app_root() -> Path:
    """Get the application root directory."""
    return Path(__file__).parent.parent.parent
