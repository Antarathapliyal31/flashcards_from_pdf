#!/usr/bin/env python3
"""Stop hook: two jobs.

  (1) Safety net — if any current-session flashcards file has no evaluator
      report, block the stop so Claude runs the evaluator before finishing.
  (2) Latency — log wait_sec (UserPromptSubmit -> Stop exit 0) to metrics.

Logic:
  - Read session_id and stop_hook_active from stdin JSON.
  - Read session start (set earlier by session_start.py) and turn start
    (set by user_prompt_submit.py).
  - Scan flashcards/*.json. "Missing" = modified at/after session start,
    AND has no evals/<stem>.report.md, AND no evals/<stem>.failed marker.
  - No missing              -> log 'turn', delete turn_start, exit 0.
  - Missing + !stop_active  -> exit 2, DO NOT touch turn_start (Stop will
                               fire again this turn, and we want to measure
                               wait_sec from the original prompt).
  - Missing +  stop_active  -> give up: write .failed markers, log giveup,
                               log 'turn', delete turn_start, systemMessage,
                               exit 0.

The session_start marker is left in place across turns within the same session;
SessionStart overwrites it. Only the turn_start marker is cleaned here.

Fails open on any unexpected error.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", HERE.parents[1]))
sys.path.insert(0, str(PROJECT_ROOT))

from config import EVALS, FLASHCARDS, SESSIONS, failed_marker, report_path  # noqa: E402
from metrics import log_event  # noqa: E402


def read_float_marker(path: Path) -> float | None:
    try:
        return float(path.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def find_unreported(since: float | None) -> list[Path]:
    if not FLASHCARDS.exists():
        return []
    missing: list[Path] = []
    for cards in FLASHCARDS.glob("*.json"):
        if since is not None and cards.stat().st_mtime < since:
            continue
        if report_path(cards).exists():
            continue
        if failed_marker(cards).exists():
            continue
        missing.append(cards)
    return missing


def log_giveup(files: list[Path]) -> None:
    EVALS.mkdir(parents=True, exist_ok=True)
    with (EVALS / "errors.log").open("a", encoding="utf-8") as f:
        f.write(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] stop_guard gave up on "
            + ", ".join(str(p) for p in files)
            + "\n"
        )


def log_turn(session_id: str, turn_start: float | None) -> None:
    if turn_start is None:
        return
    wait_sec = round(time.time() - turn_start, 3)
    # wait_sec is total user-visible wait (UserPromptSubmit -> Stop exit 0).
    # It includes Claude's thinking, hook overhead, extract/generate/eval, and
    # the Stop hook's own time. It is NOT generation time — use generation_sec
    # from the 'evaluate' event for that.
    log_event("turn", session_id=session_id, wait_sec=wait_sec)


def cleanup_turn_marker(session_id: str) -> None:
    (SESSIONS / f"{session_id}_turn_start").unlink(missing_ok=True)


def main() -> int:
    try:
        event = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except json.JSONDecodeError:
        event = {}

    session_id = event.get("session_id") or "unknown"
    stop_active = bool(event.get("stop_hook_active", False))

    turn_start = read_float_marker(SESSIONS / f"{session_id}_turn_start")
    session_start_time = read_float_marker(SESSIONS / f"{session_id}_start")
    missing = find_unreported(session_start_time)

    if not missing:
        log_turn(session_id, turn_start)
        cleanup_turn_marker(session_id)
        return 0

    if stop_active:
        for p in missing:
            failed_marker(p).write_text("")
        log_giveup(missing)
        log_turn(session_id, turn_start)
        cleanup_turn_marker(session_id)
        print(
            json.dumps(
                {
                    "systemMessage": (
                        "Evaluator did not produce reports for: "
                        + ", ".join(p.name for p in missing)
                        + ". Marked as .failed; see evals/errors.log and delete the marker to retry."
                    )
                }
            )
        )
        return 0

    # Block + instruct Claude. Do NOT touch turn_start — Stop will fire again.
    cmd_args = " ".join(str(p.relative_to(PROJECT_ROOT)) for p in missing)
    file_list = "\n".join(f"  - {p.relative_to(PROJECT_ROOT)}" for p in missing)
    print(
        "These flashcard files have no evaluator report yet:\n"
        f"{file_list}\n"
        f"Run: python evaluator/evaluator.py {cmd_args}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:  # noqa: BLE001
        print(f"stop_guard hook crashed: {e}", file=sys.stderr)
        raise SystemExit(0)
