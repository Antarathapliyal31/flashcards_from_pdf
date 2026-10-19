You are evaluating a prose summary against the source text it was made from. The summary is organized into `##` sections; each section's opening paragraph ends with a page citation like `(p. 5)` or `(pp. 3–4)`.

For each section, judge faithfulness: is the opening paragraph's claim supported by the cited page(s) in the source text? A section is "flag" if the paragraph states something the cited pages do not support, or contradicts the source. It is "ok" otherwise.

Also produce two overall notes:
- coverage_note: is important content from the source missing from the summary? (one sentence; empty string if nothing missing)
- conciseness_note: is there padding, repetition, or filler that could be cut? (one sentence; empty string if clean)

Return STRICT JSON of exact shape:
{"sections": [{"heading": "<the ## heading text verbatim>", "faithful": "ok"|"flag", "note": "<=1 sentence"}, ...], "coverage_note": "<=1 sentence", "conciseness_note": "<=1 sentence"}

Output ONLY the JSON object. No prose, no code fences.
