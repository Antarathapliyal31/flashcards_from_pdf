#!/usr/bin/env python3
"""SessionStart hook.

Records two things:
  1. .claude/sessions/<session_id>_start   - epoch time (used by stop_guard.py
                                              to scope its "missing report"
                                              check to this session).
  2. .claude/sessions/current_session_id   - the session_id as plain text,
                                              so scripts invoked via Bash
                                              (which don't receive session_id
                                              on stdin) can look it up via
                                              metrics.resolve_session_id().

Limitation: current_session_id is a single file, overwritten each SessionStart.
If two Claude Code sessions are active in this project simultaneously, the
later one clobbers the earlier, and metric events from the earlier session
will be tagged with the wrong id. For a single-user learning project this is
acceptable.

Fails open: any error exits 0.
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
    (sessions / f"{session_id}_start").write_text(str(time.time()))
    (sessions / "current_session_id").write_text(session_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)
