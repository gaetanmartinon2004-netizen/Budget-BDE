"""Justificatifs management."""

from pathlib import Path

def justificatifs_root() -> Path:
    """Get the root directory for justificatifs."""
    return Path("justificatifs")

def safe_path_segment(text: str) -> str:
    """Convert text to a safe path segment."""
    return text.replace("/", "_").replace("\\", "_")

def save_justificatif(mandat_id, transaction_id, file_obj, filename, mandat_name, pole_name, label, transaction_date):
    """Save a justificatif file."""
    return f"justificatifs/{mandat_id}/{transaction_id}/{filename}"
