#!/usr/bin/env python3
"""Standalone evaluation agent for flashcards.

Usage:
    python evaluator.py <flashcards/X.json> [<flashcards/Y.json> ...]

For each file:
  - Python checks (no LLM): JSON validity, required fields, page in range,
    answer length, uncovered pages (which pages have zero cards).
  - LLM call (one): hallucination, citation support, question/answer relevance.
  - Writes evals/<stem>.report.md on success (exit 0 even when some cards are
    flagged — "flagged" is a successful evaluation with bad news).
  - Logs an 'evaluate' metrics event with eval_sec, generation_sec (when
    reachable), tokens, passed/flagged/total.
  - On crash: appends to evals/errors.log and exits 1. No report is written.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

from config import EVALS, EXTRACTED, MAX_ANSWER_CHARS, SESSIONS, report_path  # noqa: E402
from metrics import log_event, resolve_session_id  # noqa: E402

try:
    from anthropic import Anthropic
except ImportError:
    print("evaluator: anthropic SDK not installed (pip install -r requirements.txt)", file=sys.stderr)
    sys.exit(1)


ERRORS_LOG = EVALS / "errors.log"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_RETRIES = 2
RETRY_BACKOFF_SEC = 2


def log_error(msg: str) -> None:
    EVALS.mkdir(parents=True, exist_ok=True)
    with ERRORS_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def python_checks(cards: list, pages: list[dict]) -> dict:
    """Deterministic per-card checks + page coverage. No LLM."""
    valid_pages = {p["page"] for p in pages}
    page_range = (min(valid_pages), max(valid_pages)) if valid_pages else (0, 0)

    per_card = []
    for i, card in enumerate(cards):
        issues: list[str] = []
        if not isinstance(card, dict):
            issues.append("not a JSON object")
            per_card.append({"index": i, "issues": issues})
            continue
        for field in ("question", "answer", "page"):
            if field not in card:
                issues.append(f"missing field: {field}")
        if "answer" in card and isinstance(card["answer"], str) and len(card["answer"]) > MAX_ANSWER_CHARS:
            issues.append(f"answer too long ({len(card['answer'])} > {MAX_ANSWER_CHARS})")
        if "page" in card:
            p = card["page"]
            if not isinstance(p, int):
                issues.append(f"page is not int: {p!r}")
            elif p not in valid_pages:
                issues.append(f"page {p} not in extracted pages (range {page_range[0]}-{page_range[1]})")
        per_card.append({"index": i, "issues": issues})

    cited = {c["page"] for c in cards if isinstance(c, dict) and isinstance(c.get("page"), int)}
    uncovered = sorted(valid_pages - cited)
    return {"per_card": per_card, "uncovered_pages": uncovered, "page_range": page_range}


def llm_check(client: Anthropic, model: str, pages: list[dict], cards: list) -> tuple[dict, dict]:
    """One LLM call. Returns (parsed_json, usage).
       usage = {"input_tokens": int|None, "output_tokens": int|None}
    """
    system = (
        "You are evaluating study flashcards against the source text they were made from. "
        "For each card, judge three things:\n"
        "  (a) hallucination: is the answer supported by the source text at all?\n"
        "  (b) citation: does the specific cited page support this card?\n"
        "  (c) relevance: does the question actually elicit the given answer?\n"
        "Return STRICT JSON of exact shape:\n"
        '{"per_card": [{"index": int, "hallucination": "ok"|"flag", '
        '"citation": "ok"|"flag", "relevance": "ok"|"flag", "note": "<=1 sentence"}, ...]}\n'
        "Output ONLY the JSON object. No prose, no code fences."
    )

    source_text = "\n\n".join(f"[page {p['page']}]\n{p['text']}" for p in pages)
    cards_annotated = [{"index": i, **c} for i, c in enumerate(cards) if isinstance(c, dict)]
    user = f"SOURCE TEXT:\n{source_text}\n\nCARDS:\n{json.dumps(cards_annotated, indent=2)}"

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=8000,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = resp.content[0].text.strip() if resp.content else ""
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(raw)
            usage = {
                "input_tokens": getattr(resp.usage, "input_tokens", None),
                "output_tokens": getattr(resp.usage, "output_tokens", None),
            }
            return parsed, usage
        except (json.JSONDecodeError, Exception) as e:  # noqa: BLE001
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
    raise RuntimeError(f"LLM check failed after {MAX_RETRIES} attempts: {last_err}")


def _llm_entry(llm: dict, index: int) -> dict:
    for entry in llm.get("per_card", []):
        if entry.get("index") == index:
            return entry
    return {}


def _is_flagged(py_issues: list, llm_entry: dict) -> bool:
    if py_issues:
        return True
    for k in ("hallucination", "citation", "relevance"):
        if llm_entry.get(k) == "flag":
            return True
    return False


def render_report(cards_path: Path, cards: list, py: dict, llm: dict) -> tuple[str, int, int]:
    lines: list[str] = [f"# Evaluation: {cards_path.name}", ""]
    passed = 0
    flagged = 0
    card_blocks: list[str] = []

    for i, card in enumerate(cards):
        py_issues = py["per_card"][i]["issues"]
        llm_entry = _llm_entry(llm, i)
        is_flagged = _is_flagged(py_issues, llm_entry)
        if is_flagged:
            flagged += 1
        else:
            passed += 1

        block = [f"## Card {i} — {'FLAGGED' if is_flagged else 'ok'}"]
        if isinstance(card, dict):
            block.append(f"- Q: {card.get('question', '<missing>')}")
            block.append(f"- A: {card.get('answer', '<missing>')}")
            block.append(f"- Page: {card.get('page', '<missing>')}")
        if py_issues:
            block.append("- Python issues: " + "; ".join(py_issues))
        llm_flags = [k for k in ("hallucination", "citation", "relevance") if llm_entry.get(k) == "flag"]
        if llm_flags:
            note = llm_entry.get("note", "")
            tail = f" — {note}" if note else ""
            block.append(f"- LLM flags: {', '.join(llm_flags)}{tail}")
        card_blocks.append("\n".join(block))

    header = [
        f"**Summary:** {passed} passed, {flagged} flagged out of {len(cards)}",
        f"**Uncovered pages** (pages with no cards): "
        + (", ".join(str(p) for p in py["uncovered_pages"]) if py["uncovered_pages"] else "none"),
        "",
    ]
    return "\n".join(lines + header + card_blocks) + "\n", passed, flagged


def _find_extracted(cards_path: Path) -> Path:
    """Card filename is <pdf_stem>_<YYYYMMDD>_<HHMMSS>.json; strip the last two
    underscore-fields to recover the PDF stem."""
    parts = cards_path.stem.rsplit("_", 2)
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        raise ValueError(
            f"card filename does not match <pdf_stem>_<YYYYMMDD>_<HHMMSS>.json: {cards_path.name}"
        )
    pdf_stem = parts[0]
    extracted_file = EXTRACTED / f"{pdf_stem}.json"
    if not extracted_file.is_file():
        raise FileNotFoundError(f"extracted file missing for {cards_path.name}: {extracted_file}")
    return extracted_file


def _generation_sec(cards_path: Path) -> float | None:
    """[DEPRECATED] generation_sec is now logged by generate.py at source.

    This function is kept for backwards compatibility but always returns None.
    The generate.py script logs the real generation time when creating cards.
    """
    return None


def process_one(cards_path: Path, client: Anthropic, model: str) -> dict:
    if not cards_path.is_file():
        raise FileNotFoundError(cards_path)
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    if not isinstance(cards, list):
        raise ValueError(f"expected a JSON array in {cards_path}")

    extracted_file = _find_extracted(cards_path)
    extracted = json.loads(extracted_file.read_text(encoding="utf-8"))
    pages = extracted.get("pages", [])
    if not pages:
        raise ValueError(f"no pages in {extracted_file}")

    eval_start = time.time()
    py = python_checks(cards, pages)
    llm, usage = llm_check(client, model, pages, cards)
    report, passed, flagged = render_report(cards_path, cards, py, llm)

    out = report_path(cards_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")

    eval_sec = round(time.time() - eval_start, 3)
    generation_sec = _generation_sec(cards_path)

    event: dict = {
        "cards": str(cards_path),
        "report": str(out),
        "eval_sec": eval_sec,
        "passed": passed,
        "flagged": flagged,
        "total": len(cards),
    }
    if generation_sec is not None:
        event["generation_sec"] = generation_sec
    if usage.get("input_tokens") is not None:
        event["input_tokens"] = usage["input_tokens"]
    if usage.get("output_tokens") is not None:
        event["output_tokens"] = usage["output_tokens"]
    log_event("evaluate", **event)
    return event


def _fmt_summary(s: dict) -> str:
    lines = [f"{s['cards']}: {s['passed']}/{s['total']} passed, {s['flagged']} flagged"]
    stages = []
    if s.get("generation_sec") is not None:
        stages.append(f"generation: {s['generation_sec']}s")
    stages.append(f"evaluation: {s['eval_sec']}s")
    if s.get("input_tokens") is not None:
        stages.append(f"tokens: {s['input_tokens']} in / {s['output_tokens']} out")
    lines.append("  " + "  |  ".join(stages))
    lines.append(f"  report: {s['report']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: evaluator.py <flashcards.json> [<flashcards.json> ...]", file=sys.stderr)
        return 2

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log_error("missing ANTHROPIC_API_KEY (check .env)")
        print("evaluator: ANTHROPIC_API_KEY not set (see evals/errors.log)", file=sys.stderr)
        return 1

    model = os.environ.get("EVALUATOR_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)

    had_failure = False
    for path_str in argv[1:]:
        cards_path = Path(path_str).resolve()
        try:
            summary = process_one(cards_path, client, model)
            print(_fmt_summary(summary))
        except Exception as e:  # noqa: BLE001
            had_failure = True
            tb = traceback.format_exc()
            log_error(f"{cards_path}: {e}\n{tb}")
            print(f"evaluator failed on {cards_path}: {e} (see evals/errors.log)", file=sys.stderr)

    return 1 if had_failure else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
