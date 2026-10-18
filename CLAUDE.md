# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Pre-code — a learning project exercising four Claude Code primitives (CLAUDE.md, Skills, Hooks, an external evaluation agent) via a PDF → flashcards pipeline. Design is agreed; scaffolding is in progress. If a directory below is missing, it hasn't been created yet.

## Folder layout

- `inbox/` — source PDFs. **Read-only to Claude.** Never Edit/Write/mv/rm/cp anything here. Only `scripts/extract.py` reads from `inbox/`; everything downstream reads the extracted JSON, not the PDF.
- `extracted/` — one JSON per PDF, text grouped by page number. Produced by `extract.py`. Single source of truth for the generator and evaluator.
- `flashcards/` — generated cards, named `<pdf_stem>_<YYYYMMDD_HHMMSS>.json`. One fact per card: question, answer, source page.
- `evals/` — evaluator reports named `<flashcards_stem>.report.md`. A sibling `<stem>.failed` marker means the evaluator gave up on that card file; delete the marker to retry. `evals/errors.log` holds evaluator crash details.
- `evaluator/evaluator.py` — standalone Python evaluation agent. Takes flashcard file paths on argv (e.g. `python evaluator/evaluator.py flashcards/X.json`).
- `.claude/skills/make-flashcards/` — the generation procedure. Read `SKILL.md` there, not this file, for the step-by-step.
- `.claude/hooks/` — Python hook scripts referenced from `.claude/settings.json`.
- `config.py` — shared constants (notably the flashcards ↔ report pairing rule).

## Hard rules

- **Save flashcards with the Write tool, never Bash.** Writing via `echo` or `cat >` bypasses expected tracking and makes files hard to attribute.
- **Never invent timestamps.** Get them from `scripts/stamp.py` or `date +%Y%m%d_%H%M%S`.
- **`inbox/` is read-only.** `protect_pdf.py` (PreToolUse hook) enforces this via an allowlist on Bash commands that reference `inbox/`, but follow the rule rather than relying on the hook.
- **Pairing rule**: `flashcards/<stem>.json` ↔ `evals/<stem>.report.md`. Defined once in `config.py` and imported by both `evaluator.py` and `stop_guard.py` — don't duplicate the rule anywhere else.

## Running things

The normal pipeline runs by asking Claude in-session (e.g. "make flashcards from inbox/lecture5.pdf"); the `make-flashcards` skill chains extract → generate → evaluate. Direct invocation for debugging: `python scripts/extract.py inbox/<file>.pdf` and `python evaluator/evaluator.py flashcards/<file>.json`.

No build or lint step yet.

## Python environment

TBD — pin a Python version and venv before implementation starts, and record both here. System default is pyenv 3.11.9. Hook scripts must call Python by absolute path (via `shebang` or in `settings.json`) so Claude's Bash tool resolves the intended interpreter.
