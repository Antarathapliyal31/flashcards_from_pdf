#!/usr/bin/env python3
"""
End-to-end pipeline for make-flashcards: extract → generate → evaluate.

Single entry point that chains generate.py and evaluator as separate processes.
For other skills, use generate.py directly.

Usage:
    python3 run_pipeline.py inbox/<file>.pdf
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent


def log_error(msg: str) -> None:
    """Append error to evals/errors.log."""
    evals_dir = HERE / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    with (evals_dir / "errors.log").open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 run_pipeline.py inbox/<file>.pdf", file=sys.stderr)
        return 1

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found", file=sys.stderr)
        return 1

    try:
        # Step 1: Generate flashcards
        gen_result = subprocess.run(
            [sys.executable, str(HERE / "generate.py"), "--skill", "make-flashcards", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        cards_path = gen_result.stdout.strip()
        if not cards_path or not Path(cards_path).exists():
            raise RuntimeError(f"Generation failed: no output file produced")

        # Step 2: Evaluate flashcards
        eval_result = subprocess.run(
            [sys.executable, str(HERE / "evaluator" / "evaluator.py"), cards_path],
            capture_output=True,
            text=True,
            check=True,
        )

        # Output results (evaluator output includes counts and report path)
        print(eval_result.stdout, end="")
        return 0

    except subprocess.CalledProcessError as e:
        step = "generation" if "generate.py" in str(e.cmd) else "evaluation"
        error_msg = f"run_pipeline.py {pdf_path}: {step} failed\n{e.stderr}"
        log_error(error_msg)
        print(f"Error: {step} failed (see evals/errors.log)", file=sys.stderr)
        return 1

    except Exception as e:
        error_msg = f"run_pipeline.py {pdf_path}: {e}\n{traceback.format_exc()}"
        log_error(error_msg)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
