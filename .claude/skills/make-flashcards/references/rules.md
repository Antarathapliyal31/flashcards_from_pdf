# Flashcard Generation Rules

## Format
Return a JSON array of flashcard objects. Each object has three fields:
- `question` (string): A clear question that prompts recall of one fact
- `answer` (string): A concise answer, max 240 characters
- `page` (integer): The page number where this fact appears in the source

## Content Rules
- **One fact per card.** Each card teaches or tests a single concept, definition, formula, or relationship.
- **Prefer concrete, testable claims** over vague paraphrases. A card should ask for a specific fact or explain a specific mechanism, not summarize a paragraph.
- **Skip non-card-worthy pages:** title pages, tables of contents, pure figures with no text, blank pages.
- **Page numbers must match** those in the extracted text. Do not invent pages.

## Answer Length
- Maximum 240 characters per answer.
- Keep answers short and direct. If an answer runs long, split it into multiple cards.

## Card Count
- Generate **as many cards as needed** to capture the important concepts and pointers from the source.
- **Hard maximum: 50 cards** per PDF. If the source has more learnable facts, select the most important ones.
- **Quality over quantity:** prefer fewer, well-written cards to many weak ones.
- Skip redundant facts. If two pages teach the same concept, include the fact once (on either page).

## Output Structure
```json
[
  {"question": "What is X?", "answer": "X is Y.", "page": 5},
  {"question": "How does Z work?", "answer": "Z works by...", "page": 7}
]
```

Return **only** valid JSON. No prose, no markdown code fences, no explanations.
