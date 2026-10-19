"""Shared project constants. Imported by evaluator.py and stop_guard.py so the
output <-> report pairing rule lives in exactly one place.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

INBOX = PROJECT_ROOT / "inbox"
GOLDEN_PDFS = PROJECT_ROOT / "golden_dataset" / "pdfs"
EXTRACTED = PROJECT_ROOT / "extracted"
FLASHCARDS = PROJECT_ROOT / "flashcards"
SUMMARIES = PROJECT_ROOT / "summaries"
KEY_POINTS = PROJECT_ROOT / "key-points"
EVALS = PROJECT_ROOT / "evals"
SESSIONS = PROJECT_ROOT / ".claude" / "sessions"

GEN_MODEL = "claude-sonnet-4-6"
EVALUATOR_MODEL = "claude-haiku-4-5-20251001"

MAX_ANSWER_CHARS = 240
MAX_SUMMARY_SECTIONS = 7
MAX_KEYPOINTS_HEADINGS = 7
MAX_KEYPOINTS_SUBBULLETS = 4

VALID_SKILLS = ("make-flashcards", "make-summary", "key-points")

OUTPUT_FOLDERS = {
    "make-flashcards": FLASHCARDS,
    "make-summary": SUMMARIES,
    "key-points": KEY_POINTS,
}


def infer_skill(output_path) -> str:
    """Infer the skill name from an output file's parent directory."""
    parent = Path(output_path).resolve().parent.name
    for skill, folder in OUTPUT_FOLDERS.items():
        if parent == folder.name:
            return skill
    raise ValueError(
        f"cannot infer skill from path {output_path}: parent dir '{parent}' "
        f"is not one of {[f.name for f in OUTPUT_FOLDERS.values()]}"
    )


def report_path(output_path, skill: str) -> Path:
    """<output>/<stem>.<ext>  ->  evals/<stem>.<skill>.report.md"""
    stem = Path(output_path).stem
    return EVALS / f"{stem}.{skill}.report.md"


def failed_marker(output_path, skill: str) -> Path:
    """Marker written by stop_guard.py when the evaluator keeps failing.
    Delete the file to retry on the next evaluator run."""
    stem = Path(output_path).stem
    return EVALS / f"{stem}.{skill}.failed"
