"""Append-only JSON-lines metrics log.

Writers (extract.py, evaluator.py, stop_guard.py) call log_event(name, **data).
Each call writes one JSON object to evals/metrics.jsonl.

Append-only line writes on a local filesystem are safe for this use case
without locking: we never update existing lines, and each writer emits a
complete line per call.

session_id resolution: scripts invoked via Bash (extract.py, evaluator.py)
do not receive session_id directly. We look it up from a file that the
SessionStart hook writes. This assumes a single active Claude Code session
per project at a time.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

try:
    from config import EVALS, SESSIONS
except ImportError:
    PROJECT = Path(__file__).resolve().parent
    EVALS = PROJECT / "evals"
    SESSIONS = PROJECT / ".claude" / "sessions"

METRICS_FILE = EVALS / "metrics.jsonl"
_CURRENT_SESSION_ID_FILE = SESSIONS / "current_session_id"


def resolve_session_id() -> str | None:
    """Return the current session_id, or None if not resolvable.

    Precedence: CLAUDE_SESSION_ID env var (if Claude Code happens to set it)
    then .claude/sessions/current_session_id, which session_start.py writes.
    """
    sid = os.environ.get("CLAUDE_SESSION_ID")
    if sid:
        return sid
    try:
        content = _CURRENT_SESSION_ID_FILE.read_text().strip()
        return content or None
    except FileNotFoundError:
        return None


def log_event(event: str, **data) -> None:
    """Append one JSON event to evals/metrics.jsonl.

    Automatically stamps ts (epoch seconds) and session_id. Extra fields
    pass through as-is. If a caller passes session_id explicitly in data,
    it overrides the file-based lookup.
    """
    EVALS.mkdir(parents=True, exist_ok=True)
    payload: dict = {"ts": round(time.time(), 3), "event": event}
    sid = resolve_session_id()
    if sid:
        payload["session_id"] = sid
    payload.update(data)
    with METRICS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
