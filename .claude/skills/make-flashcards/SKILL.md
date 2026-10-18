---
name: make-flashcards
description: Create study flashcards (also called revision cards, learning cards, or study cards) from a PDF in the inbox/ folder. Use when the user asks to turn a PDF, lecture, slide deck, chapter, or paper into flashcards for studying, revision, or spaced repetition. Each card has a question, an answer, and a cited source page. Do NOT use for summarizing a PDF, extracting a table of contents, or quizzing on existing cards.
---

# make-flashcards

Pipeline: generate cards from a PDF (single API call) → evaluate the resulting file (standalone Python agent).

## Procedure

1. **Generate flashcards.** Run:
   ```
   python3 generate.py --skill make-flashcards inbox/<file>.pdf
   ```
   On success, prints the path to `flashcards/<pdf_stem>_<timestamp>.json`. On failure, prints an error and points to `evals/errors.log`. Do NOT read or write the output file yourself.

2. **Evaluate.** Run:
   ```
   python evaluator/evaluator.py <path-from-above>
   ```
   On success, writes a report to `evals/<pdf_stem>_<timestamp>.report.md` and prints a summary. On failure, points to `evals/errors.log`.

3. **Reply to the user** with one line:
   ```
   Wrote <path> (<count> cards). Evaluation: <passed> passed, <flagged> flagged. Report: <report_path>.
   ```
   If either command fails, say so and point to `evals/errors.log`. Never claim cards were checked if evaluation failed.

## Direct invocation (debugging)

- Just generate: `python3 generate.py --skill make-flashcards inbox/<file>.pdf`
- Just evaluate: `python evaluator/evaluator.py flashcards/<file>.json`
- Trigger the skill explicitly: `/make-flashcards`
