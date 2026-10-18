---
name: key-points
description: Extract the key points from a PDF document in the inbox/ folder as a concise bullet-point list. Use when the user asks for key takeaways, main points, or highlights from a lecture, paper, or article. Produces a structured list focused on the most important ideas.
---

# key-points

Pipeline: extract text from the PDF (deterministic Python) → identify key points (Claude API single call) → save with the Write tool.

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

4. **Extract key points.** Call Claude with the extracted text and ask for a concise, hierarchical list of:
   - Top-level concepts (2-5 main ideas)
   - Supporting points under each concept (3-4 per concept)
   - Concrete facts, definitions, or formulas where applicable
   - Focus on what the reader needs to remember and be able to do

5. **Save with the Write tool** to:
   ```
   key-points/<pdf_stem>_<timestamp>.md
   ```
   where `<pdf_stem>` is the PDF filename without `.pdf`, and `<timestamp>` is the stamp.py output. Example: `key-points/lecture5_20261016_143022.md`.

6. **Reply to the user** with: path to the key points file and a count of main concepts extracted.

## Direct invocation (debugging)

- Just extract: `python .claude/skills/make-flashcards/scripts/extract.py inbox/<file>.pdf`
- Trigger the skill explicitly: `/key-points`
