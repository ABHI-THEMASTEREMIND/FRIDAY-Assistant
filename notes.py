"""Small local notes store for FRIDAY."""

from __future__ import annotations

import datetime as dt
from pathlib import Path


NOTES_FILE = Path(__file__).resolve().parent / "friday_notes.txt"


def save_note(note: str) -> None:
    timestamp = dt.datetime.now().strftime("%d %b %Y, %I:%M %p")
    with NOTES_FILE.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {note.strip()}\n")


def recent_notes(limit: int = 3) -> list[str]:
    if not NOTES_FILE.exists():
        return []
    lines = [line.strip() for line in NOTES_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[-limit:]
