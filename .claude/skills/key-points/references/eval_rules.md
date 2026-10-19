You are evaluating a bulleted key-points document against the source text it was made from. The document is organized into `##` headings; under each heading is a flat list of sub-bullets, and each sub-bullet ends with a page citation like `(p. 5)` or `(pp. 3–4)`.

For each sub-bullet, judge faithfulness: is the bullet's claim supported by its cited page(s) in the source text? A bullet is "flag" if it states something the cited pages do not support, or contradicts the source. It is "ok" otherwise.

Also produce two overall notes:
- coverage_note: is important content from the source missing from the key points? (one sentence; empty string if nothing missing)
- conciseness_note: is there padding, repetition, or filler that could be cut? (one sentence; empty string if clean)

Return STRICT JSON of exact shape:
{"bullets": [{"heading": "<the parent ## heading text verbatim>", "sub_index": int, "faithful": "ok"|"flag", "note": "<=1 sentence"}, ...], "coverage_note": "<=1 sentence", "conciseness_note": "<=1 sentence"}

sub_index is the 0-based position of the bullet within its parent heading. Output ONLY the JSON object. No prose, no code fences.
