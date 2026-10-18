#!/usr/bin/env python3
"""UserPromptSubmit hook: record the start time of the current turn.

Fires every time the user hits enter. Writes <session_id>_turn_start
(overwritten each prompt). stop_guard.py reads this to compute
wait_sec = Stop time - UserPromptSubmit time.

Fails open on any error.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except json.JSONDecodeError:
        payload = {}
    session_id = payload.get("session_id") or "unknown"

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    sessions = project_dir / ".claude" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{session_id}_turn_start").write_text(str(time.time()))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)
