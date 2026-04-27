from __future__ import annotations

import sys
from pathlib import Path


def _base_path() -> Path:
    """Return application writable base path for source and frozen modes."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def database_file() -> Path:
    """Legacy monolithic DB path used for migration/backward compatibility."""
    base_path = _base_path()

    if getattr(sys, "frozen", False):
        return base_path / "budget.db"

    return base_path / "data" / "budget.db"


def mandats_database_file() -> Path:
    """Main metadata DB path (mandats list + active mandat)."""
    base_path = _base_path()
    if getattr(sys, "frozen", False):
        return base_path / "mandats.db"
    return base_path / "data" / "mandats.db"


def mandat_database_file(mandat_id: int) -> Path:
    """Return dedicated DB file path for one mandat."""
    base_path = _base_path()
    if getattr(sys, "frozen", False):
        return base_path / "mandats" / f"mandat_{int(mandat_id)}.db"
    return base_path / "data" / "mandats" / f"mandat_{int(mandat_id)}.db"


def justificatifs_root() -> Path:
    """Returns path to root directory for attachments storage."""
    base_path = _base_path()

    return base_path / "justificatifs"
