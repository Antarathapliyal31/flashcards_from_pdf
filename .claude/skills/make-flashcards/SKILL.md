---
name: make-flashcards
description: Create study flashcards (also called revision cards, learning cards, or study cards) from a PDF in the inbox/ folder. Use when the user asks to turn a PDF, lecture, slide deck, chapter, or paper into flashcards for studying, revision, or spaced repetition. Each card has a question, an answer, and a cited source page. Do NOT use for summarizing a PDF, extracting a table of contents, or quizzing on existing cards.
---

# make-flashcards

Pipeline: generate cards from a PDF (single API call) → evaluate the resulting file (standalone Python agent).

## Procedure

1. **Run the pipeline.** Run:
   ```
   python3 run_pipeline.py inbox/<file>.pdf
   ```
   This chains extraction → generation → evaluation in one command. On success, prints the evaluation summary. On failure, prints an error and points to `evals/errors.log`. Do NOT read or write the output file yourself.

2. **Reply to the user** with one line:
   ```
   Wrote <path> (<count> cards). Evaluation: <passed> passed, <flagged> flagged. Report: <report_path>.
   ```
   If the pipeline fails, say so and point to `evals/errors.log`.

## Direct invocation (debugging)

- Just generate: `python3 generate.py --skill make-flashcards inbox/<file>.pdf`
- Just evaluate: `python evaluator/evaluator.py flashcards/<file>.json`
- Trigger the skill explicitly: `/make-flashcards`
