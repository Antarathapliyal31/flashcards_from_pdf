---
name: make-summary
description: Generate a comprehensive summary of a PDF document in the inbox/ folder. Use when the user asks to summarize, condense, or extract key takeaways from a lecture, paper, chapter, or article. Produces a markdown document that captures the main ideas and structure.
---

# make-summary

Pipeline: generate summary from a PDF (single API call).

## Procedure

1. **Generate summary.** Run:
   ```
   python3 generate.py --skill make-summary inbox/<file>.pdf
   ```
   On success, prints the path to `summaries/<pdf_stem>_<timestamp>.md`. On failure, prints an error and points to `evals/errors.log`. Do NOT read or write the output file yourself.

2. **Reply to the user** with one line:
   ```
   Wrote <path>.
   ```
   If the command fails, say so and point to `evals/errors.log`.

## Direct invocation (debugging)

- Just generate: `python3 generate.py --skill make-summary inbox/<file>.pdf`
- Trigger the skill explicitly: `/make-summary`
