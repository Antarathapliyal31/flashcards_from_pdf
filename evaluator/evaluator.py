#!/usr/bin/env python3
"""Standalone evaluation agent for all three skills.

Usage:
    python evaluator.py <output_path> [<output_path> ...]
    python evaluator.py --skill <skill> <output_path>

If --skill is not given, the skill is inferred from the output file's parent
directory (flashcards/ -> make-flashcards, summaries/ -> make-summary,
key-points/ -> key-points).

For each file:
  - Python checks (no LLM): format conformance, length limits, citation
    presence, cited page validity, page coverage.
  - LLM call (one): faithfulness per item + overall coverage/conciseness notes.
  - Writes evals/<stem>.<skill>.report.md on success (exit 0 even when some
    items are flagged).
  - Logs an 'evaluate' metrics event with skill, eval_sec, tokens, counts.
  - On crash: appends to evals/errors.log and exits 1. No report is written.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

from config import (  # noqa: E402
    EVALS,
    EXTRACTED,
    MAX_ANSWER_CHARS,
    MAX_KEYPOINTS_HEADINGS,
    MAX_KEYPOINTS_SUBBULLETS,
    MAX_SUMMARY_SECTIONS,
    VALID_SKILLS,
    infer_skill,
    report_path,
)
from metrics import log_event  # noqa: E402

try:
    from anthropic import Anthropic
except ImportError:
    print("evaluator: anthropic SDK not installed (pip install -r requirements.txt)", file=sys.stderr)
    sys.exit(1)


ERRORS_LOG = EVALS / "errors.log"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_RETRIES = 2
RETRY_BACKOFF_SEC = 2

SKILL_FOLDERS = {
    "make-flashcards": PROJECT_ROOT / ".claude" / "skills" / "make-flashcards",
    "make-summary": PROJECT_ROOT / ".claude" / "skills" / "make-summary",
    "key-points": PROJECT_ROOT / ".claude" / "skills" / "key-points",
}

# Match "(p. 5)" or "(pp. 3-4)" / "(pp. 3–4)" / "(pp. 3, 7-8)" at end of a line.
# En-dash preferred per rules, but accept hyphen too.
CITATION_RE = re.compile(r"\(p{1,2}\.\s*([0-9,\s\-–]+)\)\s*$")


def log_error(msg: str) -> None:
    EVALS.mkdir(parents=True, exist_ok=True)
    with ERRORS_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def load_eval_rules(skill: str) -> str:
    path = SKILL_FOLDERS[skill] / "references" / "eval_rules.md"
    if not path.is_file():
        raise FileNotFoundError(f"eval_rules.md not found for {skill}: {path}")
    return path.read_text(encoding="utf-8").strip()


def _parse_cited_pages(citation_body: str) -> list[int]:
    """Parse the body of a citation like "3", "3-5", "3–5", "3, 7-8"."""
    pages: list[int] = []
    for part in citation_body.split(","):
        part = part.strip()
        if not part:
            continue
        # Normalize both hyphen and en-dash
        rng = re.split(r"[\-–]", part)
        if len(rng) == 1:
            if rng[0].isdigit():
                pages.append(int(rng[0]))
        elif len(rng) == 2 and rng[0].strip().isdigit() and rng[1].strip().isdigit():
            start, end = int(rng[0].strip()), int(rng[1].strip())
            pages.extend(range(start, end + 1))
    return pages


# ------------------------- Flashcards -------------------------

def python_checks_flashcards(cards: list, pages: list[dict]) -> dict:
    valid_pages = {p["page"] for p in pages}
    page_range = (min(valid_pages), max(valid_pages)) if valid_pages else (0, 0)

    per_item = []
    for i, card in enumerate(cards):
        issues: list[str] = []
        if not isinstance(card, dict):
            issues.append("not a JSON object")
            per_item.append({"index": i, "issues": issues})
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
        per_item.append({"index": i, "issues": issues})

    cited = {c["page"] for c in cards if isinstance(c, dict) and isinstance(c.get("page"), int)}
    uncovered = sorted(valid_pages - cited)
    return {"per_item": per_item, "uncovered_pages": uncovered, "page_range": page_range}


def llm_check_flashcards(client: Anthropic, model: str, system: str, pages: list[dict], cards: list) -> tuple[dict, dict]:
    source_text = "\n\n".join(f"[page {p['page']}]\n{p['text']}" for p in pages)
    cards_annotated = [{"index": i, **c} for i, c in enumerate(cards) if isinstance(c, dict)]
    user = f"SOURCE TEXT:\n{source_text}\n\nCARDS:\n{json.dumps(cards_annotated, indent=2)}"
    return _call_llm(client, model, system, user)


def render_report_flashcards(output_path: Path, cards: list, py: dict, llm: dict) -> tuple[str, int, int]:
    lines: list[str] = [f"# Evaluation: {output_path.name}", ""]
    passed = 0
    flagged = 0
    card_blocks: list[str] = []

    llm_by_index = {e.get("index"): e for e in llm.get("per_card", [])}

    for i, card in enumerate(cards):
        py_issues = py["per_item"][i]["issues"]
        llm_entry = llm_by_index.get(i, {})
        llm_flags = [k for k in ("hallucination", "citation", "relevance") if llm_entry.get(k) == "flag"]
        is_flagged = bool(py_issues) or bool(llm_flags)
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


# ------------------------- Summary -------------------------

def parse_summary(text: str) -> dict:
    """Return {"sections": [{"heading", "intro_line", "cited_pages_raw", "cited_pages"}]}
    "sections" excludes "Key Takeaways" and "Source References".
    """
    lines = text.splitlines()
    sections: list[dict] = []
    i = 0
    excluded = {"key takeaways", "source references"}
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading.lower() in excluded:
                i += 1
                continue
            # First non-blank line after heading is the intro paragraph.
            # Rules say the opening paragraph's final line carries the citation.
            # We treat the paragraph as consecutive non-blank non-bullet lines
            # until a blank line, a bullet (-), or the next ## heading.
            j = i + 1
            paragraph: list[str] = []
            while j < len(lines):
                nxt = lines[j].rstrip()
                if not nxt:
                    if paragraph:
                        break
                    j += 1
                    continue
                if nxt.startswith("## ") or nxt.startswith("- ") or nxt.startswith("| "):
                    break
                paragraph.append(nxt)
                j += 1
            intro = " ".join(paragraph).strip()
            cited_raw = ""
            cited: list[int] = []
            if intro:
                m = CITATION_RE.search(intro)
                if m:
                    cited_raw = m.group(0)
                    cited = _parse_cited_pages(m.group(1))
            sections.append({
                "heading": heading,
                "intro": intro,
                "cited_pages_raw": cited_raw,
                "cited_pages": cited,
            })
            i = j
        else:
            i += 1
    return {"sections": sections}


def python_checks_summary(parsed: dict, pages: list[dict]) -> dict:
    valid_pages = {p["page"] for p in pages}
    page_range = (min(valid_pages), max(valid_pages)) if valid_pages else (0, 0)

    sections = parsed["sections"]
    per_item = []
    for i, sec in enumerate(sections):
        issues: list[str] = []
        if not sec["intro"]:
            issues.append("section has no intro paragraph")
        elif not sec["cited_pages_raw"]:
            issues.append("intro paragraph missing citation (expected '(p. N)' or '(pp. N–M)' at end)")
        else:
            bad = [p for p in sec["cited_pages"] if p not in valid_pages]
            if bad:
                issues.append(f"cited pages not in source: {bad} (valid range {page_range[0]}-{page_range[1]})")
        per_item.append({"index": i, "heading": sec["heading"], "issues": issues})

    overall: list[str] = []
    if len(sections) > MAX_SUMMARY_SECTIONS:
        overall.append(f"too many sections: {len(sections)} > {MAX_SUMMARY_SECTIONS}")
    elif len(sections) == 0:
        overall.append("no ## sections found")

    all_cited: set[int] = set()
    for sec in sections:
        all_cited.update(sec["cited_pages"])
    uncovered = sorted(valid_pages - all_cited)

    return {
        "per_item": per_item,
        "uncovered_pages": uncovered,
        "page_range": page_range,
        "overall_issues": overall,
    }


def llm_check_summary(client: Anthropic, model: str, system: str, pages: list[dict], parsed: dict) -> tuple[dict, dict]:
    source_text = "\n\n".join(f"[page {p['page']}]\n{p['text']}" for p in pages)
    sections_annotated = [
        {
            "index": i,
            "heading": s["heading"],
            "intro_paragraph": s["intro"],
            "cited_pages": s["cited_pages"],
        }
        for i, s in enumerate(parsed["sections"])
    ]
    user = f"SOURCE TEXT:\n{source_text}\n\nSUMMARY SECTIONS:\n{json.dumps(sections_annotated, indent=2)}"
    return _call_llm(client, model, system, user)


def render_report_summary(output_path: Path, parsed: dict, py: dict, llm: dict) -> tuple[str, int, int]:
    lines: list[str] = [f"# Evaluation: {output_path.name}", ""]
    sections = parsed["sections"]
    passed = 0
    flagged = 0
    blocks: list[str] = []

    llm_sections = llm.get("sections", [])
    llm_by_heading: dict[str, dict] = {}
    for e in llm_sections:
        h = e.get("heading", "")
        if h and h not in llm_by_heading:
            llm_by_heading[h] = e

    for i, sec in enumerate(sections):
        py_issues = py["per_item"][i]["issues"]
        llm_entry = llm_by_heading.get(sec["heading"], {})
        llm_flagged = llm_entry.get("faithful") == "flag"
        is_flagged = bool(py_issues) or llm_flagged
        if is_flagged:
            flagged += 1
        else:
            passed += 1

        block = [f"## Section {i} — {'FLAGGED' if is_flagged else 'ok'}"]
        block.append(f"- Heading: {sec['heading']}")
        block.append(f"- Citation: {sec['cited_pages_raw'] or '<missing>'}")
        if py_issues:
            block.append("- Python issues: " + "; ".join(py_issues))
        if llm_flagged:
            note = llm_entry.get("note", "")
            tail = f" — {note}" if note else ""
            block.append(f"- LLM flag: faithful{tail}")
        blocks.append("\n".join(block))

    header: list[str] = [
        f"**Summary:** {passed} passed, {flagged} flagged out of {len(sections)}",
        f"**Uncovered pages** (pages never cited): "
        + (", ".join(str(p) for p in py["uncovered_pages"]) if py["uncovered_pages"] else "none"),
    ]
    if py["overall_issues"]:
        header.append("**Overall issues:** " + "; ".join(py["overall_issues"]))
    coverage = llm.get("coverage_note", "")
    conciseness = llm.get("conciseness_note", "")
    if coverage:
        header.append(f"**Coverage note:** {coverage}")
    if conciseness:
        header.append(f"**Conciseness note:** {conciseness}")
    header.append("")

    return "\n".join(lines + header + blocks) + "\n", passed, flagged


# ------------------------- Key points -------------------------

def parse_keypoints(text: str) -> dict:
    """Return {"headings": [{"heading", "bullets": [{"text", "cited_pages_raw", "cited_pages"}]}]}"""
    lines = text.splitlines()
    headings: list[dict] = []
    current: dict | None = None
    for line in lines:
        stripped = line.rstrip()
        if stripped.startswith("## "):
            if current is not None:
                headings.append(current)
            current = {"heading": stripped[3:].strip(), "bullets": []}
        elif stripped.startswith("- ") and current is not None:
            body = stripped[2:].strip()
            m = CITATION_RE.search(body)
            cited_raw = m.group(0) if m else ""
            cited = _parse_cited_pages(m.group(1)) if m else []
            current["bullets"].append({
                "text": body,
                "cited_pages_raw": cited_raw,
                "cited_pages": cited,
            })
    if current is not None:
        headings.append(current)
    return {"headings": headings}


def python_checks_keypoints(parsed: dict, pages: list[dict]) -> dict:
    valid_pages = {p["page"] for p in pages}
    page_range = (min(valid_pages), max(valid_pages)) if valid_pages else (0, 0)

    headings = parsed["headings"]
    per_item = []
    for h_idx, h in enumerate(headings):
        for b_idx, b in enumerate(h["bullets"]):
            issues: list[str] = []
            if not b["cited_pages_raw"]:
                issues.append("missing citation (expected '(p. N)' or '(pp. N–M)' at end)")
            else:
                bad = [p for p in b["cited_pages"] if p not in valid_pages]
                if bad:
                    issues.append(f"cited pages not in source: {bad} (valid range {page_range[0]}-{page_range[1]})")
            per_item.append({
                "heading_index": h_idx,
                "sub_index": b_idx,
                "heading": h["heading"],
                "text": b["text"],
                "issues": issues,
            })

    overall: list[str] = []
    if len(headings) > MAX_KEYPOINTS_HEADINGS:
        overall.append(f"too many ## headings: {len(headings)} > {MAX_KEYPOINTS_HEADINGS}")
    elif len(headings) == 0:
        overall.append("no ## headings found")
    for h in headings:
        if len(h["bullets"]) > MAX_KEYPOINTS_SUBBULLETS:
            overall.append(f"heading '{h['heading']}' has {len(h['bullets'])} sub-bullets (max {MAX_KEYPOINTS_SUBBULLETS})")

    all_cited: set[int] = set()
    for h in headings:
        for b in h["bullets"]:
            all_cited.update(b["cited_pages"])
    uncovered = sorted(valid_pages - all_cited)

    total_bullets = sum(len(h["bullets"]) for h in headings)
    return {
        "per_item": per_item,
        "total_bullets": total_bullets,
        "uncovered_pages": uncovered,
        "page_range": page_range,
        "overall_issues": overall,
    }


def llm_check_keypoints(client: Anthropic, model: str, system: str, pages: list[dict], parsed: dict) -> tuple[dict, dict]:
    source_text = "\n\n".join(f"[page {p['page']}]\n{p['text']}" for p in pages)
    bullets_annotated = []
    for h in parsed["headings"]:
        for b_idx, b in enumerate(h["bullets"]):
            bullets_annotated.append({
                "heading": h["heading"],
                "sub_index": b_idx,
                "bullet": b["text"],
                "cited_pages": b["cited_pages"],
            })
    user = f"SOURCE TEXT:\n{source_text}\n\nKEY POINTS:\n{json.dumps(bullets_annotated, indent=2)}"
    return _call_llm(client, model, system, user)


def render_report_keypoints(output_path: Path, parsed: dict, py: dict, llm: dict) -> tuple[str, int, int]:
    lines: list[str] = [f"# Evaluation: {output_path.name}", ""]
    passed = 0
    flagged = 0
    blocks: list[str] = []

    llm_bullets = llm.get("bullets", [])
    llm_by_key: dict[tuple[str, int], dict] = {}
    for e in llm_bullets:
        key = (e.get("heading", ""), e.get("sub_index", -1))
        if key not in llm_by_key:
            llm_by_key[key] = e

    for item in py["per_item"]:
        py_issues = item["issues"]
        key = (item["heading"], item["sub_index"])
        llm_entry = llm_by_key.get(key, {})
        llm_flagged = llm_entry.get("faithful") == "flag"
        is_flagged = bool(py_issues) or llm_flagged
        if is_flagged:
            flagged += 1
        else:
            passed += 1

        block = [f"## {item['heading']} — bullet {item['sub_index']} — {'FLAGGED' if is_flagged else 'ok'}"]
        block.append(f"- Text: {item['text']}")
        if py_issues:
            block.append("- Python issues: " + "; ".join(py_issues))
        if llm_flagged:
            note = llm_entry.get("note", "")
            tail = f" — {note}" if note else ""
            block.append(f"- LLM flag: faithful{tail}")
        blocks.append("\n".join(block))

    header: list[str] = [
        f"**Summary:** {passed} passed, {flagged} flagged out of {py['total_bullets']}",
        f"**Uncovered pages** (pages never cited): "
        + (", ".join(str(p) for p in py["uncovered_pages"]) if py["uncovered_pages"] else "none"),
    ]
    if py["overall_issues"]:
        header.append("**Overall issues:** " + "; ".join(py["overall_issues"]))
    coverage = llm.get("coverage_note", "")
    conciseness = llm.get("conciseness_note", "")
    if coverage:
        header.append(f"**Coverage note:** {coverage}")
    if conciseness:
        header.append(f"**Conciseness note:** {conciseness}")
    header.append("")

    return "\n".join(lines + header + blocks) + "\n", passed, flagged


# ------------------------- Shared LLM call -------------------------

def _call_llm(client: Anthropic, model: str, system: str, user: str) -> tuple[dict, dict]:
    """One LLM call with retries. Returns (parsed_json, usage)."""
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


# ------------------------- Dispatch -------------------------

def _find_extracted(output_path: Path) -> Path:
    """Output filename is <pdf_stem>_<YYYYMMDD>_<HHMMSS>.<ext>; strip the last
    two underscore-fields to recover the PDF stem."""
    parts = output_path.stem.rsplit("_", 2)
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        raise ValueError(
            f"output filename does not match <pdf_stem>_<YYYYMMDD>_<HHMMSS>.<ext>: {output_path.name}"
        )
    pdf_stem = parts[0]
    extracted_file = EXTRACTED / f"{pdf_stem}.json"
    if not extracted_file.is_file():
        raise FileNotFoundError(f"extracted file missing for {output_path.name}: {extracted_file}")
    return extracted_file


def process_one(output_path: Path, client: Anthropic, model: str, skill: str) -> dict:
    if not output_path.is_file():
        raise FileNotFoundError(output_path)

    extracted_file = _find_extracted(output_path)
    extracted = json.loads(extracted_file.read_text(encoding="utf-8"))
    pages = extracted.get("pages", [])
    if not pages:
        raise ValueError(f"no pages in {extracted_file}")

    system = load_eval_rules(skill)
    eval_start = time.time()

    if skill == "make-flashcards":
        cards = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(cards, list):
            raise ValueError(f"expected a JSON array in {output_path}")
        py = python_checks_flashcards(cards, pages)
        llm, usage = llm_check_flashcards(client, model, system, pages, cards)
        report, passed, flagged = render_report_flashcards(output_path, cards, py, llm)
        total = len(cards)

    elif skill == "make-summary":
        text = output_path.read_text(encoding="utf-8")
        parsed = parse_summary(text)
        py = python_checks_summary(parsed, pages)
        llm, usage = llm_check_summary(client, model, system, pages, parsed)
        report, passed, flagged = render_report_summary(output_path, parsed, py, llm)
        total = len(parsed["sections"])

    elif skill == "key-points":
        text = output_path.read_text(encoding="utf-8")
        parsed = parse_keypoints(text)
        py = python_checks_keypoints(parsed, pages)
        llm, usage = llm_check_keypoints(client, model, system, pages, parsed)
        report, passed, flagged = render_report_keypoints(output_path, parsed, py, llm)
        total = py["total_bullets"]

    else:
        raise ValueError(f"unknown skill: {skill}")

    out = report_path(output_path, skill)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")

    eval_sec = round(time.time() - eval_start, 3)

    event: dict = {
        "skill": skill,
        "output": str(output_path),
        "report": str(out),
        "eval_sec": eval_sec,
        "passed": passed,
        "flagged": flagged,
        "total": total,
    }
    if usage.get("input_tokens") is not None:
        event["input_tokens"] = usage["input_tokens"]
    if usage.get("output_tokens") is not None:
        event["output_tokens"] = usage["output_tokens"]
    log_event("evaluate", **event)
    return event


def _fmt_summary(s: dict) -> str:
    lines = [f"{s['output']}: {s['passed']}/{s['total']} passed, {s['flagged']} flagged"]
    stages = [f"evaluation: {s['eval_sec']}s"]
    if s.get("input_tokens") is not None:
        stages.append(f"tokens: {s['input_tokens']} in / {s['output_tokens']} out")
    lines.append("  " + "  |  ".join(stages))
    lines.append(f"  report: {s['report']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Evaluate generated flashcards, summaries, or key points.")
    parser.add_argument("--skill", choices=list(VALID_SKILLS), default=None,
                        help="Skill to evaluate. If omitted, inferred from output file's parent directory.")
    parser.add_argument("paths", nargs="+", help="One or more output file paths to evaluate.")
    args = parser.parse_args(argv[1:])

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log_error("missing ANTHROPIC_API_KEY (check .env)")
        print("evaluator: ANTHROPIC_API_KEY not set (see evals/errors.log)", file=sys.stderr)
        return 1

    model = os.environ.get("EVALUATOR_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)

    had_failure = False
    for path_str in args.paths:
        output_path = Path(path_str).resolve()
        try:
            skill = args.skill or infer_skill(output_path)
            summary = process_one(output_path, client, model, skill)
            print(_fmt_summary(summary))
        except Exception as e:  # noqa: BLE001
            had_failure = True
            tb = traceback.format_exc()
            log_error(f"{output_path}: {e}\n{tb}")
            print(f"evaluator failed on {output_path}: {e} (see evals/errors.log)", file=sys.stderr)

    return 1 if had_failure else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
