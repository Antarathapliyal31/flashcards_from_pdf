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

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
sys.path.insert(0, str(HERE))

from config import EVALS, INBOX  # noqa: E402
from metrics import log_event  # noqa: E402

# Import extract function to reuse extraction caching
sys.path.insert(0, str(HERE / ".claude" / "skills" / "make-flashcards" / "scripts"))
from extract import extract  # noqa: E402

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
    """Get YYYYMMDD_HHMMSS timestamp."""
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


def generate_content(client: Anthropic, model: str, extracted: dict, rules: str, skill: str) -> tuple[str | list, dict]:
    """Generic content generation. Returns (content, usage_info)."""
    text_by_page = "\n".join(
        f"--- Page {p['page']} ---\n{p['text']}"
        for p in extracted["pages"]
    )

    skill_instructions = {
        "make-flashcards": "Extract important flashcards from this source material.",
        "make-summary": "Generate a comprehensive summary of this source material.",
        "key-points": "Extract the key points from this source material.",
    }

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": rules,
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"Source material:\n\n{text_by_page}",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": skill_instructions[skill]}],
    )

    # Check for truncation
    if response.stop_reason == "max_tokens":
        raise ValueError("Output was cut off (max_tokens reached)")
    elif response.stop_reason != "end_turn":
        raise ValueError(f"Response ended unexpectedly (stop_reason: {response.stop_reason})")

    response_text = response.content[0].text.strip()

    # Parse based on skill
    if skill == "make-flashcards":
        try:
            content = json.loads(response_text)
        except json.JSONDecodeError:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
                content = json.loads(json_str)
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
                content = json.loads(json_str)
            else:
                raise ValueError("Failed to parse JSON response")

        if not isinstance(content, list):
            raise ValueError("Expected JSON array of flashcards")

        if len(content) == 0:
            raise ValueError("No flashcards generated (empty array)")

        # Validate cards and page ranges
        valid_pages = {p["page"] for p in extracted["pages"]}
        for i, card in enumerate(content):
            if not isinstance(card, dict):
                raise ValueError(f"Card {i}: not a JSON object")
            for field in ("question", "answer", "page"):
                if field not in card:
                    raise ValueError(f"Card {i}: missing field '{field}'")
            if not isinstance(card["page"], int) or card["page"] not in valid_pages:
                raise ValueError(f"Card {i}: page {card.get('page')} not in range {sorted(valid_pages)}")

        # Truncate if needed
        if len(content) > MAX_CARDS:
            content = content[:MAX_CARDS]
    else:
        content = response_text

    # Collect usage info
    usage_info = {
        "input_tokens": getattr(response.usage, "input_tokens", None),
        "output_tokens": getattr(response.usage, "output_tokens", None),
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", None),
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", None),
    }

    return content, usage_info


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
        content, usage_info = generate_content(client, model, extracted_data, rules, args.skill)
        gen_sec = round(time.time() - gen_start, 3)

        # Count items
        if args.skill == "make-flashcards":
            item_count = len(content) if isinstance(content, list) else 0
        elif args.skill == "make-summary":
            # Count section headings (lines starting with "##")
            item_count = sum(1 for line in content.split("\n") if line.startswith("## ")) if isinstance(content, str) else 1
        else:  # key-points
            # Count main bullet points (lines starting with "## ")
            item_count = sum(1 for line in content.split("\n") if line.startswith("## ")) if isinstance(content, str) else 1

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

        # Log metrics event with token info
        event_data = {
            "skill": args.skill,
            "pdf": pdf_path.name,
            "output_file": str(output_path),
            "generation_sec": gen_sec,
            "model": model,
            "item_count": item_count,
        }
        if usage_info["input_tokens"] is not None:
            event_data["input_tokens"] = usage_info["input_tokens"]
        if usage_info["output_tokens"] is not None:
            event_data["output_tokens"] = usage_info["output_tokens"]
        if usage_info["cache_creation_input_tokens"] is not None:
            event_data["cache_creation_input_tokens"] = usage_info["cache_creation_input_tokens"]
        if usage_info["cache_read_input_tokens"] is not None:
            event_data["cache_read_input_tokens"] = usage_info["cache_read_input_tokens"]

        log_event("generate", **event_data)

        # Print output path for all skills
        print(output_path)
        return 0

    except Exception as e:
        error_msg = f"generate.py --skill {args.skill} {args.pdf}: {e}\n{traceback.format_exc()}"
        log_error(error_msg)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
