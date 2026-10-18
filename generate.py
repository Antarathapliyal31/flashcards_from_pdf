#!/usr/bin/env python3
"""
Generic generation script for all three skills: make-flashcards, make-summary, key-points.

Single API call per skill eliminates round-trip overhead. Reuses extraction caching.

Usage:
    python3 generate.py --skill make-flashcards inbox/lecture5.pdf
    python3 generate.py --skill make-summary inbox/chapter3.pdf
    python3 generate.py --skill key-points inbox/paper.pdf
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from config import EVALS, INBOX  # noqa: E402
from metrics import log_event  # noqa: E402

# Import extract function to reuse extraction caching
import sys
sys.path.insert(0, str(HERE / ".claude" / "skills" / "make-flashcards" / "scripts"))
from extract import extract  # noqa: E402, F401

try:
    from anthropic import Anthropic
except ImportError:
    print("generate.py: anthropic SDK not installed (pip install -r requirements.txt)", file=sys.stderr)
    sys.exit(1)


SKILL_FOLDERS = {
    "make-flashcards": HERE / ".claude" / "skills" / "make-flashcards",
    "make-summary": HERE / ".claude" / "skills" / "make-summary",
    "key-points": HERE / ".claude" / "skills" / "key-points",
}

OUTPUT_FOLDERS = {
    "make-flashcards": HERE / "flashcards",
    "make-summary": HERE / "summaries",
    "key-points": HERE / "key-points",
}

MAX_CARDS = 50


def log_error(msg: str) -> None:
    """Append error to evals/errors.log."""
    EVALS.mkdir(parents=True, exist_ok=True)
    with (EVALS / "errors.log").open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def get_timestamp() -> str:
    """Get timestamp from stamp.py (same as other scripts)."""
    import time
    return time.strftime("%Y%m%d_%H%M%S")


def validate_skill(skill: str) -> Path:
    """Validate that skill folder and rules.md exist."""
    if skill not in SKILL_FOLDERS:
        raise ValueError(f"Unknown skill: {skill}. Must be one of: {', '.join(SKILL_FOLDERS.keys())}")
    skill_dir = SKILL_FOLDERS[skill]
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill folder not found: {skill_dir}")
    rules_file = skill_dir / "references" / "rules.md"
    if not rules_file.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_file}")
    return rules_file


def validate_pdf(pdf_path: Path) -> None:
    """Validate that PDF is in inbox/ and exists."""
    pdf_path = pdf_path.resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    try:
        pdf_path.relative_to(INBOX.resolve())
    except ValueError:
        raise RuntimeError(f"PDF must be in {INBOX}; got {pdf_path}")


def generate_flashcards(client: Anthropic, model: str, extracted: dict, rules: str) -> list[dict]:
    """Generate flashcards using Claude API. Returns list of dicts."""
    text_by_page = "\n".join(
        f"--- Page {p['page']} ---\n{p['text']}"
        for p in extracted["pages"]
    )

    user_prompt = f"""Extract important flashcards from this source material:

{text_by_page}"""

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": rules,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = response.content[0].text.strip()

    # Parse JSON
    try:
        cards = json.loads(response_text)
    except json.JSONDecodeError:
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
            cards = json.loads(json_str)
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
            cards = json.loads(json_str)
        else:
            raise ValueError("Failed to parse Claude's response as JSON")

    if not isinstance(cards, list):
        raise ValueError("Expected JSON array of cards")

    # Validate and enforce max count
    if len(cards) > MAX_CARDS:
        cards = cards[:MAX_CARDS]

    return cards


def generate_summary(client: Anthropic, model: str, extracted: dict, rules: str) -> str:
    """Generate summary using Claude API. Returns markdown string."""
    text_by_page = "\n".join(
        f"--- Page {p['page']} ---\n{p['text']}"
        for p in extracted["pages"]
    )

    user_prompt = f"""Generate a comprehensive summary of this source material:

{text_by_page}"""

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": rules,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text.strip()


def generate_key_points(client: Anthropic, model: str, extracted: dict, rules: str) -> str:
    """Generate key points using Claude API. Returns markdown string."""
    text_by_page = "\n".join(
        f"--- Page {p['page']} ---\n{p['text']}"
        for p in extracted["pages"]
    )

    user_prompt = f"""Extract the key points from this source material:

{text_by_page}"""

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": rules,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate flashcards, summaries, or key points from a PDF.")
    parser.add_argument("--skill", required=True, choices=list(SKILL_FOLDERS.keys()),
                        help="Skill to run: make-flashcards, make-summary, or key-points")
    parser.add_argument("pdf", help="Path to PDF in inbox/ (e.g., inbox/lecture5.pdf)")
    args = parser.parse_args()

    try:
        # Validate inputs
        rules_file = validate_skill(args.skill)
        pdf_path = Path(args.pdf)
        validate_pdf(pdf_path)

        # Load rules
        rules = rules_file.read_text(encoding="utf-8")

        # Extract PDF (reuses cache)
        extracted = extract(pdf_path)
        extracted_data = json.loads(extracted.read_text(encoding="utf-8"))

        # Set up API client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        client = Anthropic(api_key=api_key)

        # Get model from .env
        model = os.environ.get("GEN_MODEL", "claude-haiku-4-5-20251001")

        # Generate
        gen_start = time.time()
        if args.skill == "make-flashcards":
            content = generate_flashcards(client, model, extracted_data, rules)
            item_count = len(content) if isinstance(content, list) else 0
        elif args.skill == "make-summary":
            content = generate_summary(client, model, extracted_data, rules)
            item_count = 1  # one summary per PDF
        else:  # key-points
            content = generate_key_points(client, model, extracted_data, rules)
            item_count = 1  # one set of key points per PDF

        gen_sec = round(time.time() - gen_start, 3)

        # Write output
        output_folder = OUTPUT_FOLDERS[args.skill]
        output_folder.mkdir(parents=True, exist_ok=True)

        timestamp = get_timestamp()
        pdf_stem = pdf_path.stem

        if args.skill == "make-flashcards":
            output_path = output_folder / f"{pdf_stem}_{timestamp}.json"
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
        else:
            output_path = output_folder / f"{pdf_stem}_{timestamp}.md"
            output_path.write_text(content, encoding="utf-8")

        # Log metrics event
        log_event(
            "generate",
            skill=args.skill,
            pdf=pdf_path.name,
            output_file=str(output_path),
            generation_sec=gen_sec,
            model=model,
            item_count=item_count,
        )

        # Output success with timing
        print(output_path)
        print(f"[Timing] Actual execution: {gen_sec:.2f}s generation", file=sys.stderr)
        return 0

    except Exception as e:
        error_msg = f"generate.py --skill {args.skill} {args.pdf}: {e}\n{traceback.format_exc()}"
        log_error(error_msg)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
