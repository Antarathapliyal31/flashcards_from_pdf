# Key Points Extraction Rules

## Format
Return a markdown document with a hierarchical bullet-point list.

## Content Rules
- **Focus on what to remember and do.** Identify the most essential takeaways: facts, skills, definitions, and actions a reader should know.
- **Top-level points:** 3–7 main ideas that anchor the source.
- **Sub-points:** 2–4 details or examples under each main idea.
- **Concrete facts:** Include definitions, formulas, numbers, and concrete relationships.
- **Skip elaboration:** Omit anecdotes, lengthy explanations, and context that can be inferred.

## Citations
- Every sub-bullet must end with a page citation: `(p. N)` for a single page or `(pp. N–M)` for a range.
- Use an en-dash `–` (not a hyphen) inside page ranges.
- For non-contiguous pages, list them separated by commas: `(pp. 3, 7–8)`.
- Cited pages must exist in the source material. Do not invent page numbers.
- Top-level `## Main Point` headings themselves do NOT need citations — only the sub-bullets under them.

## Length
- **Hard maximum: 7 `##` headings**, each with at most **4 sub-bullets**.
- Prefer fewer, denser bullets over many shallow ones.

## Structure
```markdown
# Key Points: [Source Title or Topic]

## 1. Main Point A
- Sub-point A1 (fact or skill) (p. 3)
- Sub-point A2 (related concept or example) (pp. 4–5)
- Sub-point A3 (practical application, if relevant) (p. 6)

## 2. Main Point B
- Sub-point B1 (p. 7)
- Sub-point B2 (pp. 8, 10)

...
```

## Output Style
- Concise bullet-point language (not full sentences unless needed for clarity).
- Use secondary headings (##) to organize main points.
- Each sub-bullet is a single line, starting with `- ` and ending with its citation.
- Do not use nested bullets (indented sub-sub-points) — one level only.
- Optimized for scanning and quick recall.

Return **only** markdown. No preamble, no meta-commentary.
