---
name: make-summary
description: Write a prose summary of a PDF in inbox/, organized in short sections that follow the document's structure, with a reference table mapping each section to its source pages. Use when the user asks to summarize, condense, give an overview, or explain what a lecture, paper, chapter, or article is about. Not for bullet lists of takeaways; use key-points for that.
---

# make-summary

Pipeline: generate summary from a PDF (single API call) → evaluate the resulting file (standalone Python agent).

## Procedure

1. **Run the pipeline from the project root.** Run:
   ```
   python3 run_pipeline.py --skill make-summary inbox/<file>.pdf
   ```
   (Make sure you're in the project root directory: `/Users/antarathapliyal/flashcards-from-pdf/`)

   This chains extraction → generation → evaluation in one command. On success, prints the evaluation summary. On failure, prints an error and points to `evals/errors.log`. Do NOT read or write the output file yourself.

2. **Reply to the user** with one line:
   ```
   Wrote <path> (<count> sections). Evaluation: <passed> passed, <flagged> flagged. Report: <report_path>.
   ```
   If the pipeline fails, say so and point to `evals/errors.log`.

## Direct invocation (debugging)

- Just generate: `python3 generate.py --skill make-summary inbox/<file>.pdf`
- Just evaluate: `python evaluator/evaluator.py --skill make-summary summaries/<file>.md`
- Trigger the skill explicitly: `/make-summary`
