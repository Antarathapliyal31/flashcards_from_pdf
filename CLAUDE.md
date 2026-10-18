# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

A learning project exercising CLAUDE.md, Skills, Hooks, and external evaluation agents via three content-generation pipelines (flashcards, summaries, key points). End-to-end scaffold is in place; before first use, create the Python env and set the API key (see "Python environment" below).

## Folder layout

- `inbox/` — source PDFs. **Read-only to Claude.** Never Edit/Write/mv/rm/cp anything here. Only `generate.py` and `extract.py` read from `inbox/`.
- `extracted/` — one JSON per PDF, text grouped by page number. Produced by `extract.py` (called by `generate.py`). Single source of truth.
- `flashcards/` — generated flashcards, named `<pdf_stem>_<YYYYMMDD_HHMMSS>.json`. One fact per card: question, answer, source page.
- `summaries/` — generated summaries, named `<pdf_stem>_<YYYYMMDD_HHMMSS>.md`. Markdown format.
- `key-points/` — extracted key points, named `<pdf_stem>_<YYYYMMDD_HHMMSS>.md`. Hierarchical markdown format.
- `evals/` — flashcard evaluation reports named `<flashcards_stem>.report.md`. A sibling `<stem>.failed` marker means the evaluator gave up; delete to retry. `evals/errors.log` holds crash details. `evals/metrics.jsonl` logs `extract`, `generate`, `evaluate`, and `turn` events.
- `generate.py` — generic generation script. Single Claude API call per skill. Usage: `python3 generate.py --skill <skill> inbox/<file>.pdf`.
- `evaluator/evaluator.py` — standalone evaluation agent for flashcards only. Takes flashcard file paths on argv.
- `.claude/skills/*/` — skill definitions. Each has `SKILL.md` and `references/rules.md` (generation rules).
- `.claude/skills/*/scripts/` — `extract.py` (PDF → JSON) and `stamp.py` (timestamp helper).
- `.claude/hooks/` — Python hook scripts referenced from `.claude/settings.json`.
- `config.py` — shared constants (notably the flashcards ↔ report pairing rule).

## Hard rules

- **Never call generate.py directly from Claude Code.** Skills are the entry point; skills call `generate.py` via Bash (allowed by settings.json). Do NOT read or write output files yourself.
- **`inbox/` is read-only.** `protect_pdf.py` (PreToolUse hook) enforces this via an allowlist on Bash commands that reference `inbox/`. The allowlist includes `generate.py` and `extract.py`.
- **Pairing rule** (flashcards only): `flashcards/<stem>.json` ↔ `evals/<stem>.report.md`. Defined once in `config.py` and imported by both `evaluator.py` and `stop_guard.py` — don't duplicate the rule anywhere else.
- **`generate.py` owns timestamps and file writing.** It calls `stamp.py` internally and uses the Write API (simulated via direct file I/O in Python). Never generate timestamps in Claude Code.

## Pipeline

Three skills available:

1. **make-flashcards**: `python3 generate.py --skill make-flashcards inbox/<file>.pdf`, then evaluate with the evaluator.
2. **make-summary**: `python3 generate.py --skill make-summary inbox/<file>.pdf`.
3. **key-points**: `python3 generate.py --skill key-points inbox/<file>.pdf`.

Skills are thin wrappers around `generate.py`. In-session, ask "make flashcards from inbox/X.pdf" (etc.); the skill runs `generate.py` and reports results.

For debugging: run `generate.py` directly or call `evaluator/evaluator.py flashcards/<file>.json` to re-evaluate flashcards.

No build or lint step.

## Setup (one-time)

1. Create a virtualenv and install dependencies (Python 3.11+ recommended):
   ```
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
2. Copy the env template and add your Anthropic API key:
   ```
   cp .env.example .env
   # then edit .env to set ANTHROPIC_API_KEY and optionally GEN_MODEL
   ```
3. Launch Claude Code **from the project root** (hooks resolve `$CLAUDE_PROJECT_DIR` relative to launch). Restart the Claude Code session if `settings.json` or any hook was changed.

## Python environment

Python 3.11+. Hook and generation scripts are invoked via `python3` (resolved by your shell's PATH). If you create a `.venv/` but Claude Code picks up a different `python3`, the SDK and `pypdf` imports will fail. Easiest fix: launch Claude Code from a terminal where `.venv/bin/activate` has been run.
