"""Shared project constants. Imported by evaluator.py and stop_guard.py so the
flashcards <-> report pairing rule lives in exactly one place.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

INBOX = PROJECT_ROOT / "inbox"
EXTRACTED = PROJECT_ROOT / "extracted"
FLASHCARDS = PROJECT_ROOT / "flashcards"
EVALS = PROJECT_ROOT / "evals"
SESSIONS = PROJECT_ROOT / ".claude" / "sessions"

MAX_ANSWER_CHARS = 240


def report_path(cards_path) -> Path:
    """flashcards/<stem>.json  ->  evals/<stem>.report.md"""
    stem = Path(cards_path).stem
    return EVALS / f"{stem}.report.md"


def failed_marker(cards_path) -> Path:
    """Marker written by stop_guard.py when the evaluator keeps failing.
    Delete the file to retry on the next evaluator run."""
    stem = Path(cards_path).stem
    return EVALS / f"{stem}.failed"
