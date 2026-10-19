#!/usr/bin/env python3
"""End-to-end pipeline for all three skills: extract → generate → evaluate.

Chains generate.py and evaluator.py as separate processes.

Usage:
    python3 run_pipeline.py --skill make-flashcards inbox/<file>.pdf
    python3 run_pipeline.py --skill make-summary inbox/<file>.pdf
    python3 run_pipeline.py --skill key-points inbox/<file>.pdf
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from config import VALID_SKILLS  # noqa: E402


def log_error(msg: str) -> None:
    """Append error to evals/errors.log."""
    evals_dir = HERE / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    with (evals_dir / "errors.log").open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run generate -> evaluate pipeline for a skill.")
    parser.add_argument("--skill", required=True, choices=list(VALID_SKILLS),
                        help="Skill to run: make-flashcards, make-summary, or key-points")
    parser.add_argument("pdf", help="Path to PDF in inbox/ (e.g., inbox/lecture5.pdf)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found", file=sys.stderr)
        return 1

    try:
        gen_result = subprocess.run(
            [sys.executable, str(HERE / "generate.py"), "--skill", args.skill, str(pdf_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        output_path = gen_result.stdout.strip()
        if not output_path or not Path(output_path).exists():
            raise RuntimeError("Generation failed: no output file produced")

        eval_result = subprocess.run(
            [sys.executable, str(HERE / "evaluator" / "evaluator.py"),
             "--skill", args.skill, output_path],
            capture_output=True,
            text=True,
            check=True,
        )

        print(eval_result.stdout, end="")
        return 0

    except subprocess.CalledProcessError as e:
        step = "generation" if "generate.py" in str(e.cmd) else "evaluation"
        error_msg = f"run_pipeline.py --skill {args.skill} {pdf_path}: {step} failed\n{e.stderr}"
        log_error(error_msg)
        print(f"Error: {step} failed (see evals/errors.log)", file=sys.stderr)
        return 1

    except Exception as e:
        error_msg = f"run_pipeline.py --skill {args.skill} {pdf_path}: {e}\n{traceback.format_exc()}"
        log_error(error_msg)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
