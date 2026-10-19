You are grading a set of study flashcards against a hand-written answer key.

You receive:
- FLASHCARDS: a JSON list of cards, each with "index", "question", "answer", "page".
- ANSWER KEY:
  - "must_know": facts a good card set should cover, each with "id", "page", "fact".
  - "traps": tricky points, each with "id", "page", "topic", "correct", and an optional "common_mistake".

For each must_know fact, decide whether any card teaches that fact. Wording can differ; the meaning must match.
- covered: true if at least one card teaches the fact, false otherwise.
- cards: the indexes of the cards that cover it (empty list if none).
- page_correct: true if a covering card cites the fact's page; false if covering cards cite only other pages; null if not covered.

For each trap, decide:
- "correct": a card covers this topic and states it in agreement with "correct".
- "wrong": a card covers this topic but states it incorrectly (for example, the common_mistake).
- "not_covered": no card addresses this topic.
If several cards cover a trap and any of them is wrong, the verdict is "wrong".

Return STRICT JSON of exactly this shape:
{"facts": [{"id": str, "covered": bool, "cards": [int], "page_correct": bool|null}],
 "traps": [{"id": str, "verdict": "correct"|"wrong"|"not_covered", "cards": [int], "note": "<=1 sentence"}]}

Include every fact id and every trap id exactly once. Output ONLY the JSON object. No prose, no code fences.
