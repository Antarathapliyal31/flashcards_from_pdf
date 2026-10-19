# Summary Generation Rules

## Format
Return a markdown document structured with headings and bullet points.

## Content Rules
- **Main concepts first:** Identify and explain the 3–7 core ideas the source teaches.
- **Supporting details:** Under each concept, list 2–4 key supporting points or examples.
- **Definitions and formulas:** Include important terms, definitions, and mathematical/algorithmic formulas.
- **Context:** Explain why these concepts matter and how they fit together.
- **Examples:** Cite concrete examples from the source where they illustrate a concept.
- **Track page numbers:** As you write each section, record which pages in the source it draws from.

## Structure
```markdown
# Summary: [Source Title or Topic]

## Core Concept 1
Explanation of the concept and why it matters.

- Supporting point A
- Supporting point B (with example if available)

## Core Concept 2
[Similar structure]

...

## Key Takeaways
- One-sentence summary of each core concept.

## Source References
| Section | Pages |
|---------|-------|
| Core Concept 1 | 3–5 |
| Core Concept 2 | 6–8, 12 |
| ... | ... |
```

## Output Style
- Clear, readable markdown.
- Use headings (##) for main concepts.
- Use bullet points for supporting details.
- Keep language direct and accessible.
- Assume the reader is unfamiliar with the topic but has the intelligence to learn it.

Return **only** markdown. No preamble, no meta-commentary.
