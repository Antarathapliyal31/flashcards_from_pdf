---
name: key-points
description: Extract the key points from a PDF document in the inbox/ folder as a concise bullet-point list. Use when the user asks for key takeaways, main points, or highlights from a lecture, paper, or article. Produces a structured list focused on the most important ideas.
---

# key-points

Pipeline: generate key points from a PDF (single API call).

## Procedure

1. **Generate key points.** Run:
   ```
   python3 generate.py --skill key-points inbox/<file>.pdf
   ```
   On success, prints the path to `key-points/<pdf_stem>_<timestamp>.md`. On failure, prints an error and points to `evals/errors.log`. Do NOT read or write the output file yourself.

2. **Reply to the user** with one line:
   ```
   Wrote <path>.
   ```
   If the command fails, say so and point to `evals/errors.log`.

## Direct invocation (debugging)

- Just generate: `python3 generate.py --skill key-points inbox/<file>.pdf`
- Trigger the skill explicitly: `/key-points`
