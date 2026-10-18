#!/usr/bin/env python3
"""PreToolUse hook: keep inbox/ read-only.

Rules:
  - Write / Edit with a path that resolves inside inbox/ -> block.
  - Bash command text that does NOT mention 'inbox' -> allow (not our business).
  - Bash command text that DOES mention 'inbox' -> only allow if it matches the
    tiny allowlist of expected safe operations. Everything else -> block.

Note: command-text inspection is not bulletproof (compound commands with
&& or ; could sneak things past). True protection would be OS-level
read-only permissions. This hook is defense in depth, not the last line.

Fails open: if the hook itself crashes, exit 0 so a bug here can't block work.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


# Allowlisted Bash command patterns that may touch inbox/.
# Keep this list as small as possible — if it grows past 2–3 entries,
# something is probably wrong with the architecture.
ALLOWED_BASH_PATTERNS = [
    r"\brun_pipeline\.py\b",  # end-to-end pipeline (reads PDFs from inbox)
    r"\bextract\.py\b",       # the extraction script
    r"\bgenerate\.py\b",      # generic generation script (reads PDFs from inbox)
    r"^\s*ls\b",               # listing (debug / exploration)
    r"^\s*find\s+inbox\b",     # read-only find
]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # malformed input — not our place to block

    tool = event.get("tool_name", "")
    inp = event.get("tool_input", {}) or {}
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    inbox = project_dir / "inbox"

    if tool in ("Write", "Edit"):
        file_path = inp.get("file_path", "")
        if file_path and is_under(Path(file_path), inbox):
            print(
                "inbox/ is read-only. PDFs should be read via "
                ".claude/skills/make-flashcards/scripts/extract.py, "
                "which writes to extracted/.",
                file=sys.stderr,
            )
            return 2
        return 0

    if tool == "Bash":
        cmd = inp.get("command", "") or ""
        if "inbox" not in cmd:
            return 0
        if any(re.search(pat, cmd) for pat in ALLOWED_BASH_PATTERNS):
            return 0
        print(
            "Bash commands that touch inbox/ are restricted. "
            "Allowed: extract.py, `ls`, `find inbox`. "
            "To read a PDF, run extract.py.\n"
            f"Blocked command: {cmd}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:  # noqa: BLE001
        print(f"protect_pdf hook crashed: {e}", file=sys.stderr)
        raise SystemExit(0)
