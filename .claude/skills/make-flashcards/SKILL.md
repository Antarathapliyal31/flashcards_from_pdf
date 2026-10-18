---
name: make-flashcards
description: Create study flashcards (also called revision cards, learning cards, or study cards) from a PDF in the inbox/ folder. Use when the user asks to turn a PDF, lecture, slide deck, chapter, or paper into flashcards for studying, revision, or spaced repetition. Each card has a question, an answer, and a cited source page. Do NOT use for summarizing a PDF, extracting a table of contents, or quizzing on existing cards.
---

# make-flashcards

Pipeline: extract text from the PDF (deterministic Python) → generate cards from the extracted text (you, the model) → save with the Write tool → evaluate the resulting file (standalone Python agent).

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

4. **Compose cards** as a JSON array. Each card:
   ```json
   {"question": "<question>", "answer": "<answer>", "page": <int>}
   ```
   Rules:
   - One fact per card.
   - Answer under 240 characters.
   - `page` must be an integer that appears in the extracted JSON.
   - Prefer concrete, testable claims over paraphrased summaries.
   - Skip pages with no card-worthy content (title page, pure figure, TOC, blank).

5. **Save with the Write tool** (never Bash) to:
   ```
   flashcards/<pdf_stem>_<timestamp>.json
   ```
   where `<pdf_stem>` is the PDF filename without `.pdf`, and `<timestamp>` is the stamp.py output. Example: `flashcards/lecture5_20261016_143022.json`.

6. **Evaluate.** Run:
   ```
   python evaluator/evaluator.py flashcards/<pdf_stem>_<timestamp>.json
   ```
   On success the evaluator prints a one-line summary to stdout and writes a report to `evals/<pdf_stem>_<timestamp>.report.md`. If exit code is non-zero, no report was written — tell the user the evaluation crashed and point them to `evals/errors.log`. Do not claim cards were evaluated.

7. **Reply to the user** with: path to the cards file, the one-line evaluation summary (if the evaluator succeeded), and the report path. Example:
   > Wrote `flashcards/lecture5_20261016_143022.json` (18 cards). Evaluation: 16 passed, 2 flagged. Report: `evals/lecture5_20261016_143022.report.md`.

## Direct invocation (debugging)

- Just extract: `python .claude/skills/make-flashcards/scripts/extract.py inbox/<file>.pdf`
- Just evaluate: `python evaluator/evaluator.py flashcards/<file>.json`
- Trigger the skill explicitly: `/make-flashcards`
