# flashcards-from-pdf

Turn a PDF (lecture, chapter, paper, slide deck) into **flashcards**, a **prose summary**, or **key-point bullets** — each with page-level citations and an evaluator pass that flags unsupported claims.

A learning project built on Claude Code's Skills, Hooks, and standalone Python agents. The main loop never reads or writes outputs itself; it dispatches to Python via skills, and a Stop hook enforces that every generated file gets an evaluation report before Claude finishes.

## What it does

Three pipelines, same shape — `extract` → `generate` → `evaluate`:

| Skill | Output | Report |
|-------|--------|--------|
| `make-flashcards` | `flashcards/<pdf>_<ts>.json` — one fact per card with cited page | `evals/<stem>.make-flashcards.report.md` |
| `make-summary` | `summaries/<pdf>_<ts>.md` — up to 7 sections, each ending with `(p. N)` | `evals/<stem>.make-summary.report.md` |
| `key-points` | `key-points/<pdf>_<ts>.md` — up to 7 headings × 4 sub-bullets, each cited | `evals/<stem>.key-points.report.md` |

Every output is checked by:
- **Python checks** — format conformance, citation presence, cited-page validity, length caps, page coverage.
- **One LLM call** — faithfulness per card/section/bullet, plus overall coverage and conciseness notes.

## Quick start

```bash
# 1. Set up the Python env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Set your API key
cp .env.example .env
# edit .env to set ANTHROPIC_API_KEY

# 3. Launch Claude Code from the project root
#    (so hooks resolve $CLAUDE_PROJECT_DIR correctly)

# 4. Drop a PDF into inbox/, then ask Claude:
#    "make flashcards from inbox/<file>.pdf"
#    "summarize inbox/<file>.pdf"
#    "key points from inbox/<file>.pdf"
```

Each skill is a thin wrapper that calls `run_pipeline.py --skill <skill> inbox/<file>.pdf`. The pipeline runs generation, then evaluation, and prints one line with the output path, pass/flag counts, and the report path.

## Running the pipeline directly

```bash
# End-to-end: generate + evaluate
python3 run_pipeline.py --skill make-flashcards inbox/CS110.pdf
python3 run_pipeline.py --skill make-summary    inbox/CS110.pdf
python3 run_pipeline.py --skill key-points      inbox/CS110.pdf

# Just generate
python3 generate.py --skill make-summary inbox/CS110.pdf

# Just evaluate an existing output
python3 evaluator/evaluator.py --skill make-summary summaries/CS110_20261019_000000.md
```

The evaluator infers the skill from the output file's parent directory if `--skill` is omitted.

## How the pieces fit

```
inbox/*.pdf  ──►  extract.py  ──►  extracted/*.json
                                        │
                                        ▼
          generate.py  ──►  flashcards/ | summaries/ | key-points/
                                        │
                                        ▼
                               evaluator/evaluator.py
                                        │
                                        ▼
                              evals/<stem>.<skill>.report.md
```

- **`inbox/` is read-only** — enforced by the `protect_pdf.py` PreToolUse hook, which only lets `generate.py` and `extract.py` touch files in there.
- **Timestamps and file writes live in `generate.py`** — Claude Code never writes outputs directly.
- **Pairing rule** (output ↔ report) is defined once in `config.py` and reused by `evaluator.py` and `stop_guard.py`.
- **Stop hook** scans all three output folders at the end of a turn. If any file is missing its report, it blocks the stop and tells Claude to run the evaluator. After one retry it writes a `.failed` marker and gives up.

## Repository layout

```
inbox/              # Source PDFs (read-only)
extracted/          # Cached PDF text, grouped by page
flashcards/         # Flashcard JSON outputs
summaries/          # Markdown summary outputs
key-points/         # Markdown key-points outputs
evals/              # Evaluation reports + errors.log + metrics.jsonl
evaluator/          # Standalone evaluation agent
.claude/
  skills/<skill>/
    SKILL.md               # Thin wrapper, invoked by Claude Code
    references/
      rules.md             # Generation rules (what the model writes)
      eval_rules.md        # Evaluator LLM-judge system prompt
    scripts/               # extract.py, stamp.py (make-flashcards only)
  hooks/                   # protect_pdf, session_start, stop_guard, …
  settings.json            # Hook wiring + permission allowlist
generate.py         # Generic generator for all three skills
run_pipeline.py     # Chains generate + evaluator per skill
config.py           # Shared constants + pairing rule
metrics.py          # Append-only JSONL metrics logger
```

## Configuration

- `GEN_MODEL` — model used by `generate.py` (default: `claude-haiku-4-5-20251001`).
- `EVALUATOR_MODEL` — model used by the evaluator (default: same Haiku; using a different model from `GEN_MODEL` reduces same-model bias).

Both live in `.env`. See `.env.example` for the template.

## Metrics

Every run appends a JSON line to `evals/metrics.jsonl`:
- `extract` — PDF → JSON extraction (with cache hit/miss)
- `generate` — generation time, model, item count, token usage
- `evaluate` — skill, eval time, passed/flagged/total, token usage
- `turn` — total wait time from `UserPromptSubmit` to `Stop` exit 0

Errors land in `evals/errors.log`.

## Design decisions

- **Three skills, hardcoded routing.** Claude Code picks the skill from the user's request; each `SKILL.md` runs one command with `--skill <name>` baked in. `generate.py` never parses prompts, so there's no duplicate routing in Python.
- **Evaluator is a separate process.** It runs as the skill's last step, with a Stop hook as the guard that it actually ran.
- **Shared pairing rule.** The output ↔ report mapping lives in exactly one place (`config.py`) and is imported by both the evaluator and the Stop hook.

## Latency: how end-to-end wait came down

A single flashcards request on `CS110.pdf`, measured end-to-end (user prompt → Stop exit 0):

| Stage | Wait | What changed |
|---|---|---|
| First version | 73.4s | Claude composed cards in its main loop (read, compose, write round trips, with hooks on each) |
| Fresh context + Haiku | 41.9s | `/clear` removed accumulated context; the Haiku switch itself gave no clear gain |
| `generate.py` | 30.0s | One API call instead of tool round trips; generation down to ~12s |
| Chained scripts | 29.1s | `run_pipeline.py` cut the gap between generate and evaluate from ~2.9s to ~0.6s |
| Exact filename | ~26–28s | `CS110.pdf` instead of `CS110` removed a folder search, saving ~8s on cold requests |

Overall: **~73s → ~26–28s** (≈60% less waiting). The bottleneck was round trips and context, not the model.

### Other findings
- **Bigger model, slower, same quality.** Sonnet 4.6 took 27.3s to generate vs. ~12s for Haiku 4.5, both passing all cards. Haiku is the better fit here.
- **Prompt caching in the scripts did nothing.** The prompts are below Haiku 4.5's 4,096-token minimum cache threshold.
- **Skill description overlap matters, but wasn't the slow part.** "Key takeaways" appeared in both `make-summary` and `key-points` descriptions; the ambiguous *filename* (not the ambiguous skill picker) was what slowed summaries down.
