You are evaluating study flashcards against the source text they were made from. For each card, judge three things:
  (a) hallucination: is the answer supported by the source text at all?
  (b) citation: does the specific cited page support this card?
  (c) relevance: does the question actually elicit the given answer?

Return STRICT JSON of exact shape:
{"per_card": [{"index": int, "hallucination": "ok"|"flag", "citation": "ok"|"flag", "relevance": "ok"|"flag", "note": "<=1 sentence"}, ...]}

Output ONLY the JSON object. No prose, no code fences.
