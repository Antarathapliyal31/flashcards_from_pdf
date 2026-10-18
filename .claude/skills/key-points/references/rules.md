# Key Points Extraction Rules

## Format
Return a markdown document with a hierarchical bullet-point list.

## Content Rules
- **Focus on what to remember and do.** Identify the most essential takeaways: facts, skills, definitions, and actions a reader should know.
- **Top-level points:** 3–7 main ideas that anchor the source.
- **Sub-points:** 2–4 details or examples under each main idea.
- **Concrete facts:** Include definitions, formulas, numbers, and concrete relationships.
- **Skip elaboration:** Omit anecdotes, lengthy explanations, and context that can be inferred.

## Structure
```markdown
# Key Points: [Source Title or Topic]

## 1. Main Point A
- Sub-point A1 (fact or skill)
- Sub-point A2 (related concept or example)
- Sub-point A3 (practical application, if relevant)

## 2. Main Point B
[Similar structure]

...
```

## Output Style
- Concise bullet-point language (not full sentences unless needed for clarity).
- Use secondary headings (##) to organize main points.
- Use nested bullets for sub-points.
- Optimized for scanning and quick recall.

Return **only** markdown. No preamble, no meta-commentary.
