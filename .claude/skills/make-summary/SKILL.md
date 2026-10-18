---
name: make-summary
description: Generate a comprehensive summary of a PDF document in the inbox/ folder. Use when the user asks to summarize, condense, or extract key takeaways from a lecture, paper, chapter, or article. Produces a markdown document that captures the main ideas and structure.
---

# make-summary

Pipeline: extract text from the PDF (deterministic Python) → generate summary (Claude API single call) → save with the Write tool.

## Procedure

1. **Extract text.** Run:
   ```
   python .claude/skills/make-flashcards/scripts/extract.py inbox/<file>.pdf
   ```
   It writes `extracted/<file>.json` and prints the path. Idempotent: a second run on the same PDF skips re-extraction. If the script exits non-zero, stop and tell the user.

2. **Read the extracted text.** Use the Read tool on `extracted/<file>.json`. Shape:
   ```json
   {"source": "<file>.pdf", "pages": [{"page": 1, "text": "..."}, ...]}
   ```

3. **Get a timestamp.** Run:
   ```
   python .claude/skills/make-flashcards/scripts/stamp.py
   ```
   Capture its stdout (format: `YYYYMMDD_HHMMSS`). Never invent a timestamp.

4. **Generate summary.** Call Claude with the extracted text and ask for a structured summary covering:
   - Main concepts and themes
   - Key arguments or findings
   - Important definitions or formulas
   - Examples provided
   - Recommended next steps or practice areas

5. **Save with the Write tool** to:
   ```
   summaries/<pdf_stem>_<timestamp>.md
   ```
   where `<pdf_stem>` is the PDF filename without `.pdf`, and `<timestamp>` is the stamp.py output. Example: `summaries/lecture5_20261016_143022.md`.

6. **Reply to the user** with: path to the summary file and a brief note on its contents.

## Direct invocation (debugging)

- Just extract: `python .claude/skills/make-flashcards/scripts/extract.py inbox/<file>.pdf`
- Trigger the skill explicitly: `/make-summary`
