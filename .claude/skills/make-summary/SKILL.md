---
name: make-summary
description: Write a prose summary of a PDF in inbox/, organized in short sections that follow the document's structure, with a reference table mapping each section to its source pages. Use when the user asks to summarize, condense, give an overview, or explain what a lecture, paper, chapter, or article is about. Not for bullet lists of takeaways; use key-points for that.
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
