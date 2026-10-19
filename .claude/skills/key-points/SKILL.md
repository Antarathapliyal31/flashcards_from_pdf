---
name: key-points
description: List the most important takeaways from a PDF in inbox/ as a short bullet list. Use when the user asks for key points, key takeaways, main points, highlights, or a quick bulleted recap. Not for a prose summary or overview; use make-summary for that.
---

# key-points

Pipeline: generate key points from a PDF (single API call) → evaluate the resulting file (standalone Python agent).

## Procedure

1. **Run the pipeline from the project root.** Run:
   ```
   python3 run_pipeline.py --skill key-points inbox/<file>.pdf
   ```
   (Make sure you're in the project root directory: `/Users/antarathapliyal/flashcards-from-pdf/`)

   This chains extraction → generation → evaluation in one command. On success, prints the evaluation summary. On failure, prints an error and points to `evals/errors.log`. Do NOT read or write the output file yourself.

2. **Reply to the user** with one line:
   ```
   Wrote <path> (<count> bullets). Evaluation: <passed> passed, <flagged> flagged. Report: <report_path>.
   ```
   If the pipeline fails, say so and point to `evals/errors.log`.

## Direct invocation (debugging)

- Just generate: `python3 generate.py --skill key-points inbox/<file>.pdf`
- Just evaluate: `python evaluator/evaluator.py --skill key-points key-points/<file>.md`
- Trigger the skill explicitly: `/key-points`
