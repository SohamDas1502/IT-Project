from __future__ import annotations

from datetime import datetime
from pathlib import Path


def save_script_text(script: str, output_folder: Path, *, prefix: str = "meditation_script") -> Path:
    output_folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.txt"
    file_path = output_folder / filename
    file_path.write_text(script, encoding="utf-8")
    return file_path