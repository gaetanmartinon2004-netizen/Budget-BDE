from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from .paths import justificatifs_root


def save_justificatif(
    mandat_id: int,
    transaction_id: int,
    file_obj: BinaryIO,
    filename: str,
    mandat_name: str | None = None,
    pole_name: str | None = None,
    label: str | None = None,
    transaction_date: str | None = None,
) -> str:
    """
    Save uploaded justificatif file.
    Returns: relative path for storage in DB.
    """
    # Create mandat directory using mandat name.
    mandat_folder = _mandat_folder_name(mandat_id=mandat_id, mandat_name=mandat_name)
    mandat_dir = _resolve_mandat_directory(mandat_id=mandat_id, mandat_folder=mandat_folder)

    target_dir = mandat_dir
    if pole_name:
        target_dir = mandat_dir / safe_path_segment(pole_name)
        target_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename based on date and transaction
    now = datetime.now()
    if transaction_date:
        try:
            dt = datetime.strptime(str(transaction_date), "%Y-%m-%d")
            date_prefix = dt.strftime("%Y%m%d")
        except ValueError:
            date_prefix = now.strftime("%Y%m%d")
    else:
        date_prefix = now.strftime("%Y%m%d")
    
    # Keep original extension
    _, ext = splitext_safe(filename)
    
    # Create filename in requested format: date_label.ext
    label_part = safe_path_segment(label or "transaction")[:80]
    safe_name = f"{date_prefix}_{label_part}{ext}"
    file_path = target_dir / safe_name
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(file_obj.read())
    
    # Return relative path for DB
    if pole_name:
        return str(Path(mandat_folder) / safe_path_segment(pole_name) / safe_name)
    return str(Path(mandat_folder) / safe_name)


def ensure_pole_directories(mandat_id: int, mandat_name: str | None, pole_names: list[str]) -> None:
    """Create all pole folders for a mandat under justificatifs root."""
    mandat_folder = _mandat_folder_name(mandat_id=mandat_id, mandat_name=mandat_name)
    mandat_dir = _resolve_mandat_directory(mandat_id=mandat_id, mandat_folder=mandat_folder)
    for pole_name in pole_names:
        (mandat_dir / safe_path_segment(pole_name)).mkdir(parents=True, exist_ok=True)


def _mandat_folder_name(mandat_id: int, mandat_name: str | None) -> str:
    """Folder segment for a mandat based on its display name."""
    if mandat_name and str(mandat_name).strip():
        return safe_path_segment(str(mandat_name))
    return f"mandat_{mandat_id}"


def _resolve_mandat_directory(mandat_id: int, mandat_folder: str) -> Path:
    """Return mandat directory and migrate legacy mandat_<id> folder when possible."""
    root = justificatifs_root()
    root.mkdir(parents=True, exist_ok=True)

    target_dir = root / mandat_folder
    legacy_dir = root / f"mandat_{mandat_id}"

    # Migrate existing legacy folder name to mandat-name folder.
    if legacy_dir.exists() and not target_dir.exists() and legacy_dir != target_dir:
        legacy_dir.rename(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def get_justificatif_path(relative_path: str) -> Path:
    """Get full path to justificatif file."""
    return justificatifs_root() / relative_path


def delete_justificatif(relative_path: str) -> bool:
    """Delete justificatif file. Returns True if deleted, False if not found."""
    full_path = get_justificatif_path(relative_path)
    
    if full_path.exists():
        full_path.unlink()
        return True
    return False


def splitext_safe(filename: str) -> tuple[str, str]:
    """Safe path splitext that handles multiple dots."""
    name, ext = Path(filename).name, ""
    if "." in name:
        parts = name.rsplit(".", 1)
        name, ext = parts[0], "." + parts[1] if len(parts) > 1 else ""
    return name, ext


def safe_path_segment(value: str) -> str:
    """Sanitize text for folder/file names on Windows and keep readable accents."""
    text = (value or "").strip()
    if not text:
        return "sans-libelle"

    # Replace Windows-forbidden chars and control chars.
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", text)
    text = re.sub(r'\s+', "_", text)
    text = re.sub(r'_+', "_", text)
    text = text.strip(" ._")
    return text or "sans-libelle"
