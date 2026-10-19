#!/usr/bin/env python3
"""Print a markdown summary of the newest golden_dataset/results/*.json.

Used by the GitHub Actions workflow to populate the run's step summary.
Writes to stdout; the workflow redirects it to $GITHUB_STEP_SUMMARY.

Exits 0 even if no results file is found (prints a note instead), so the
'always()' step in the workflow doesn't swallow the real check-step error.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def main() -> int:
    if not RESULTS.exists():
        print("_No golden_dataset/results/ directory; the --check step likely never ran._")
        return 0
    files = sorted(RESULTS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("_No results JSON found._")
        return 0

    latest = files[0]
    data = json.loads(latest.read_text(encoding="utf-8"))
    t = data.get("totals", {})
    cases = data.get("cases", {})
    errors = {n: c.get("error") for n, c in cases.items() if "error" in c}

    print(f"## Golden run `{data.get('run_id', '?')}`")
    print()
    print(f"- **gen model:** `{data.get('gen_model', '?')}`")
    print(f"- **eval/judge model:** `{data.get('eval_model', '?')}`")
    print(f"- **cases:** {', '.join(sorted(cases.keys())) or '(none)'}")
    print(f"- **result file:** `{latest.relative_to(RESULTS.parent.parent)}`")
    print()

    if errors:
        print("### Errors")
        for name, err in errors.items():
            print(f"- **{name}:** `{err}`")
        print()

    print("### Evaluator (planted test)")
    print("| metric | value |")
    print("|---|---|")
    print(f"| caught | {t.get('planted_caught', 0)} / {t.get('planted_should_flag', 0)} |")
    print(f"| caught for right reason | {t.get('planted_right_reason', 0)} / {t.get('planted_should_flag', 0)} |")
    print(f"| false alarms | {t.get('planted_false_alarms', 0)} / {t.get('planted_should_pass', 0)} |")
    print()
    print("### Generator (answer-key test)")
    print("| metric | value |")
    print("|---|---|")
    print(f"| cards generated | {t.get('cards', 0)} |")
    print(f"| facts covered | {t.get('facts_covered', 0)} / {t.get('facts_total', 0)} |")
    print(f"| traps correct | {t.get('traps_correct', 0)} |")
    print(f"| traps wrong | {t.get('traps_wrong', 0)} |")
    print(f"| traps not covered | {t.get('traps_not_covered', 0)} |")
    print(f"| evaluator-flagged | {t.get('evaluator_flagged', 0)} |")
    print(f"| avg generate time (s) | {t.get('gen_sec_avg', 0)} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
