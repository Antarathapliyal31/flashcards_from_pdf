#!/usr/bin/env python3
"""Extract page-numbered text from a PDF into extracted/<stem>.json.

Deterministic (no LLM). Idempotent: skips re-extraction if the extracted file
is newer than the PDF. Only reads from inbox/ or golden_dataset/pdfs/
(defense-in-depth check in addition to the protect_pdf.py hook).

Usage:
    python extract.py inbox/<file>.pdf
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from config import EXTRACTED, GOLDEN_PDFS, INBOX  # noqa: E402
from metrics import log_event  # noqa: E402

try:
    from pypdf import PdfReader
except ImportError:
    print("extract.py: pypdf not installed (pip install -r requirements.txt)", file=sys.stderr)
    sys.exit(1)


ALLOWED_ROOTS = (INBOX, GOLDEN_PDFS)


def extract(pdf_path: Path) -> Path:
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    for root in ALLOWED_ROOTS:
        try:
            pdf_path.relative_to(root.resolve())
            break
        except ValueError:
            continue
    else:
        allowed = " or ".join(str(r) for r in ALLOWED_ROOTS)
        raise RuntimeError(f"extract.py only reads from {allowed}; got {pdf_path}")

    EXTRACTED.mkdir(parents=True, exist_ok=True)
    out_path = EXTRACTED / f"{pdf_path.stem}.json"

    start = time.time()
    skipped = out_path.exists() and out_path.stat().st_mtime >= pdf_path.stat().st_mtime
    if not skipped:
        reader = PdfReader(str(pdf_path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": i, "text": text.strip()})
        out_path.write_text(
            json.dumps({"source": pdf_path.name, "pages": pages}, indent=2),
            encoding="utf-8",
        )
    elapsed = round(time.time() - start, 3)
    log_event("extract", pdf=pdf_path.name, elapsed_sec=elapsed, skipped=skipped)
    return out_path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: extract.py <path/to/file.pdf>", file=sys.stderr)
        return 2
    out = extract(Path(sys.argv[1]))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
