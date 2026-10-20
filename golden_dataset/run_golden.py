#!/usr/bin/env python3
"""Golden dataset runner for the make-flashcards pipeline.

Runs two tests for every case in golden/cases/<name>/:

  1. Evaluator test (planted/): feeds the hand-made planted cards to the
     evaluator and checks it flags exactly the cards listed in expected.json,
     ideally with the expected flag (hallucination / citation / relevance).

  2. Generator test (answer_key.json): generates fresh cards from the golden
     PDF, then a judge call checks which must-know facts are covered and
     whether each trap is stated correctly. The real evaluator also grades
     the generated cards, so you get its pass rate too.

It imports functions from generate.py and evaluator/evaluator.py instead of
running them as commands, so golden runs never write to flashcards/ or evals/,
never log to metrics.jsonl, and never trip stop_guard.py.

Usage (from the project root):
    python3 golden/run_golden.py                  # both tests, all cases
    python3 golden/run_golden.py --only planted   # evaluator test only (cheaper)
    python3 golden/run_golden.py --only generator
    python3 golden/run_golden.py --case CS110-6
    python3 golden/run_golden.py --baseline       # replace the baseline with this run

Results go to golden/results/<timestamp>.json. The first full, error-free run
is saved automatically as golden/baseline/baseline.json; later runs are
compared against it. Use --baseline to replace it after an accepted change.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

GOLDEN = Path(__file__).resolve().parent
PROJECT_ROOT = GOLDEN.parent
CASES = GOLDEN / "cases"
PDFS = GOLDEN / "pdfs"
RESULTS = GOLDEN / "results"
BASELINE = GOLDEN / "baseline" / "baseline.json"
JUDGE_RULES = GOLDEN / "judge_rules.md"
SKILL = "make-flashcards"

# --check thresholds (how much a CI run may regress against the committed baseline).
CHECK_FALSE_ALARM_SLACK = 1        # +1 planted false alarms allowed
CHECK_FACTS_SLACK = 2              # -2 facts covered allowed
CHECK_TRAPS_NOT_COVERED_SLACK = 1  # +1 trap topics never addressed allowed


def load_module(name: str, path: Path):
    """Import a project script by path (generate.py, evaluator.py)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_json(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


# ------------------------- Shared setup -------------------------

def load_pages(extract_fn, pdf_path: Path) -> list[dict]:
    """Same extraction the real pipeline uses (single source of truth)."""
    extracted_file = extract_fn(pdf_path)
    data = json.loads(Path(extracted_file).read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    if not pages:
        raise ValueError(f"no pages extracted from {pdf_path}")
    return pages


def card_flags(ev, py: dict, llm: dict, n_cards: int) -> dict[int, dict]:
    """Per-card result in the evaluator's own terms: python issues + LLM flags."""
    llm_by_index = {e.get("index"): e for e in llm.get("per_card", [])}
    out = {}
    for i in range(n_cards):
        entry = llm_by_index.get(i, {})
        flags = [k for k in ("hallucination", "citation", "relevance") if entry.get(k) == "flag"]
        issues = py["per_item"][i]["issues"]
        out[i] = {
            "flagged": bool(flags) or bool(issues),
            "llm_flags": flags,
            "python_issues": issues,
            "note": entry.get("note", ""),
        }
    return out


# ------------------------- Test 1: evaluator (planted) -------------------------

def run_planted(case_dir: Path, pages, ev, client, eval_model, eval_rules) -> dict:
    cards = json.loads((case_dir / "planted" / "cards.json").read_text(encoding="utf-8"))
    expected = json.loads((case_dir / "planted" / "expected.json").read_text(encoding="utf-8"))

    start = time.time()
    py = ev.python_checks_flashcards(cards, pages)
    llm, usage = ev.llm_check_flashcards(client, eval_model, eval_rules, pages, cards)
    eval_sec = round(time.time() - start, 3)
    flags = card_flags(ev, py, llm, len(cards))

    misses, right_reason = [], 0
    for item in expected["should_flag"]:
        i = item["card"]
        got = flags[i]
        if not got["flagged"]:
            misses.append({"card": i, "type": item["type"], "why": item["why"]})
            continue
        if set(got["llm_flags"]) & set(item["expected_llm_flags"]):
            right_reason += 1

    false_alarms = [
        {"card": i, "llm_flags": flags[i]["llm_flags"],
         "python_issues": flags[i]["python_issues"], "note": flags[i]["note"]}
        for i in expected["should_pass"] if flags[i]["flagged"]
    ]

    n_bad = len(expected["should_flag"])
    return {
        "caught": n_bad - len(misses),
        "should_flag": n_bad,
        "caught_right_reason": right_reason,
        "false_alarms": len(false_alarms),
        "should_pass": len(expected["should_pass"]),
        "misses": misses,
        "false_alarm_details": false_alarms,
        "eval_sec": eval_sec,
        "usage": usage,
        "per_card": {str(k): v for k, v in flags.items()},
    }


# ------------------------- Test 2: generator (answer key) -------------------------

def judge(client, model: str, cards: list, key: dict) -> tuple[dict, dict]:
    cards_annotated = [{"index": i, **c} for i, c in enumerate(cards)]
    key_for_judge = {"must_know": key["must_know"], "traps": key["traps"]}
    user = (f"FLASHCARDS:\n{json.dumps(cards_annotated, indent=2)}\n\n"
            f"ANSWER KEY:\n{json.dumps(key_for_judge, indent=2)}")
    resp = client.messages.create(
        model=model, max_tokens=8000,
        system=JUDGE_RULES.read_text(encoding="utf-8"),
        messages=[{"role": "user", "content": user}],
    )
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
    return parse_json(resp.content[0].text), usage


def run_generator(case_dir: Path, pages, gen, ev, client, gen_model, eval_model,
                  gen_rules, eval_rules) -> dict:
    key = json.loads((case_dir / "answer_key.json").read_text(encoding="utf-8"))

    start = time.time()
    cards, gen_usage = gen.generate_content(client, gen_model, {"pages": pages}, gen_rules, SKILL)
    gen_sec = round(time.time() - start, 3)

    # Real evaluator on the generated cards
    start = time.time()
    py = ev.python_checks_flashcards(cards, pages)
    llm, eval_usage = ev.llm_check_flashcards(client, eval_model, eval_rules, pages, cards)
    eval_sec = round(time.time() - start, 3)
    flags = card_flags(ev, py, llm, len(cards))
    flagged = sum(1 for f in flags.values() if f["flagged"])

    # Judge against the answer key
    start = time.time()
    verdict, judge_usage = judge(client, eval_model, cards, key)
    judge_sec = round(time.time() - start, 3)

    facts = {f["id"]: f for f in verdict.get("facts", [])}
    traps = {t["id"]: t for t in verdict.get("traps", [])}
    missing_ids = [f["id"] for f in key["must_know"] if f["id"] not in facts] + \
                  [t["id"] for t in key["traps"] if t["id"] not in traps]

    covered = [fid for fid, f in facts.items() if f.get("covered")]
    page_ok = [fid for fid, f in facts.items() if f.get("covered") and f.get("page_correct")]
    trap_counts = {"correct": 0, "wrong": 0, "not_covered": 0}
    for t in traps.values():
        trap_counts[t.get("verdict", "not_covered")] = trap_counts.get(t.get("verdict", "not_covered"), 0) + 1

    return {
        "cards": len(cards),
        "facts_covered": len(covered),
        "facts_total": len(key["must_know"]),
        "facts_page_correct": len(page_ok),
        "facts_missed": [f["id"] for f in key["must_know"] if f["id"] not in covered],
        "traps": trap_counts,
        "traps_wrong": [{"id": t["id"], "note": t.get("note", "")}
                        for t in traps.values() if t.get("verdict") == "wrong"],
        "evaluator_flagged": flagged,
        "uncovered_pages": py["uncovered_pages"],
        "judge_missing_ids": missing_ids,
        "gen_sec": gen_sec,
        "eval_sec": eval_sec,
        "judge_sec": judge_sec,
        "usage": {"generate": gen_usage, "evaluate": eval_usage, "judge": judge_usage},
        "generated_cards": cards,
        "judge_verdict": verdict,
    }


# ------------------------- Reporting -------------------------

def totals(results: dict) -> dict:
    t = {}
    planted = [c["planted"] for c in results["cases"].values() if "planted" in c]
    if planted:
        t["planted_caught"] = sum(p["caught"] for p in planted)
        t["planted_should_flag"] = sum(p["should_flag"] for p in planted)
        t["planted_right_reason"] = sum(p["caught_right_reason"] for p in planted)
        t["planted_false_alarms"] = sum(p["false_alarms"] for p in planted)
        t["planted_should_pass"] = sum(p["should_pass"] for p in planted)
    gens = [c["generator"] for c in results["cases"].values() if "generator" in c]
    if gens:
        t["facts_covered"] = sum(g["facts_covered"] for g in gens)
        t["facts_total"] = sum(g["facts_total"] for g in gens)
        t["traps_correct"] = sum(g["traps"]["correct"] for g in gens)
        t["traps_wrong"] = sum(g["traps"]["wrong"] for g in gens)
        t["traps_not_covered"] = sum(g["traps"]["not_covered"] for g in gens)
        t["cards"] = sum(g["cards"] for g in gens)
        t["evaluator_flagged"] = sum(g["evaluator_flagged"] for g in gens)
        t["gen_sec_avg"] = round(sum(g["gen_sec"] for g in gens) / len(gens), 2)
    return t


def print_summary(results: dict) -> None:
    print(f"\nGolden run {results['run_id']}  (gen: {results['gen_model']}, eval/judge: {results['eval_model']})")
    for name, c in results["cases"].items():
        print(f"\n[{name}]")
        if "error" in c:
            print(f"  ERROR: {c['error']}")
        if "planted" in c:
            p = c["planted"]
            print(f"  Evaluator: caught {p['caught']}/{p['should_flag']} planted mistakes "
                  f"({p['caught_right_reason']} for the right reason), "
                  f"{p['false_alarms']}/{p['should_pass']} false alarms")
            for m in p["misses"]:
                print(f"    MISSED card {m['card']} ({m['type']}): {m['why']}")
            for f in p["false_alarm_details"]:
                print(f"    FALSE ALARM card {f['card']}: {f['llm_flags'] or f['python_issues']} {f['note']}")
        if "generator" in c:
            g = c["generator"]
            tr = g["traps"]
            print(f"  Generator: {g['cards']} cards, facts {g['facts_covered']}/{g['facts_total']} "
                  f"(page right on {g['facts_page_correct']}), traps {tr['correct']} correct / "
                  f"{tr['wrong']} wrong / {tr['not_covered']} not covered, "
                  f"evaluator flagged {g['evaluator_flagged']}")
            if g["facts_missed"]:
                print(f"    missed facts: {', '.join(g['facts_missed'])}")
            for t in g["traps_wrong"]:
                print(f"    WRONG trap {t['id']}: {t['note']}")
            if g["judge_missing_ids"]:
                print(f"    judge skipped ids: {g['judge_missing_ids']}")
            print(f"    time: generate {g['gen_sec']}s, evaluate {g['eval_sec']}s, judge {g['judge_sec']}s")
    print("\nTOTALS:", json.dumps(results["totals"]))


# ------------------------- --check mode -------------------------

def collect_misses(current: dict) -> list[dict]:
    """Return every planted mistake the evaluator failed to flag, flattened
    across cases. Shape: [{"case", "card", "type", "why"}, ...]."""
    out: list[dict] = []
    for name, case in current.get("cases", {}).items():
        planted = case.get("planted") or {}
        for m in planted.get("misses", []):
            out.append({
                "case": name,
                "card": m.get("card"),
                "type": m.get("type", ""),
                "why": m.get("why", ""),
            })
    return out


def _case_signature(case: dict) -> dict:
    """Shape of a case that must match baseline, independent of pass/fail numbers.
    This is what defines whether the planted set / answer key changed."""
    sig: dict = {}
    if "planted" in case:
        p = case["planted"]
        sig["planted"] = {"should_flag": p["should_flag"], "should_pass": p["should_pass"]}
    if "generator" in case:
        g = case["generator"]
        sig["generator"] = {"facts_total": g["facts_total"]}
    return sig


def staleness_reasons(current: dict, base: dict, gen_model: str, eval_model: str) -> list[str]:
    """Return empty list if baseline matches current config and case shape.
    Otherwise return one-line reasons the baseline is out of date."""
    reasons: list[str] = []
    if base.get("gen_model") != gen_model:
        reasons.append(f"gen_model: baseline={base.get('gen_model')!r} current={gen_model!r}")
    if base.get("eval_model") != eval_model:
        reasons.append(f"eval_model: baseline={base.get('eval_model')!r} current={eval_model!r}")
    if base.get("only") is not None:
        reasons.append(f"baseline was partial (only={base.get('only')!r}); re-baseline with a full run")

    base_cases = set(base.get("cases", {}).keys())
    cur_cases = set(current["cases"].keys())
    added = sorted(cur_cases - base_cases)
    removed = sorted(base_cases - cur_cases)
    if added:
        reasons.append(f"new cases not in baseline: {added}")
    if removed:
        reasons.append(f"baseline has cases that no longer exist: {removed}")

    for name in sorted(cur_cases & base_cases):
        cur_sig = _case_signature(current["cases"][name])
        base_sig = _case_signature(base["cases"][name])
        if cur_sig != base_sig:
            reasons.append(f"{name} shape changed: baseline={base_sig} current={cur_sig}")
    return reasons


def check_thresholds(current: dict, base: dict) -> list[str]:
    """Return list of threshold-violation strings. Empty list = pass."""
    violations: list[str] = []

    bad_cases = [n for n, c in current["cases"].items() if "error" in c]
    if bad_cases:
        for name in bad_cases:
            violations.append(f"case error: {name}: {current['cases'][name].get('error', '')}")

    ct = current.get("totals", {})
    bt = base.get("totals", {})

    if ct.get("planted_caught") != ct.get("planted_should_flag"):
        violations.append(
            f"planted misses: caught={ct.get('planted_caught')} "
            f"required={ct.get('planted_should_flag')}"
        )

    if ct.get("traps_wrong", 0) != 0:
        violations.append(f"traps stated wrong: actual={ct.get('traps_wrong')} allowed=0")

    cur_fa = ct.get("planted_false_alarms", 0)
    allowed_fa = bt.get("planted_false_alarms", 0) + CHECK_FALSE_ALARM_SLACK
    if cur_fa > allowed_fa:
        violations.append(
            f"planted false alarms: actual={cur_fa} allowed<={allowed_fa} "
            f"(baseline={bt.get('planted_false_alarms', 0)} + {CHECK_FALSE_ALARM_SLACK})"
        )

    cur_fc = ct.get("facts_covered", 0)
    allowed_fc = bt.get("facts_covered", 0) - CHECK_FACTS_SLACK
    if cur_fc < allowed_fc:
        violations.append(
            f"facts covered: actual={cur_fc} allowed>={allowed_fc} "
            f"(baseline={bt.get('facts_covered', 0)} - {CHECK_FACTS_SLACK})"
        )

    cur_tn = ct.get("traps_not_covered", 0)
    allowed_tn = bt.get("traps_not_covered", 0) + CHECK_TRAPS_NOT_COVERED_SLACK
    if cur_tn > allowed_tn:
        violations.append(
            f"traps not covered: actual={cur_tn} allowed<={allowed_tn} "
            f"(baseline={bt.get('traps_not_covered', 0)} + {CHECK_TRAPS_NOT_COVERED_SLACK})"
        )

    return violations


def compare(current: dict, base: dict) -> None:
    same_scope = (current.get("only") == base.get("only")
                  and sorted(current["cases"]) == sorted(base.get("cases", {})))
    if not same_scope:
        print(f"\nNot compared with baseline {base['run_id']}: it covers different cases or tests "
              f"(baseline: {sorted(base.get('cases', {}))}, only={base.get('only')}). "
              "Run the same scope to compare.")
        return
    print(f"\nCompared with baseline {base['run_id']}  (gen: {base.get('gen_model')}, eval: {base.get('eval_model')}):")
    for k, v in current["totals"].items():
        b = base.get("totals", {}).get(k)
        if b is None:
            continue
        delta = round(v - b, 2) if isinstance(v, (int, float)) else None
        mark = "" if not delta else f"  ({'+' if delta > 0 else ''}{delta})"
        print(f"  {k}: {b} -> {v}{mark}")


# ------------------------- Main -------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Run the golden dataset for make-flashcards.")
    parser.add_argument("--only", choices=["planted", "generator"], default=None)
    parser.add_argument("--case", default=None, help="Run a single case, e.g. CS110-6")
    parser.add_argument("--baseline", action="store_true", help="Replace the baseline with this run (full, error-free runs only)")
    parser.add_argument("--check", action="store_true",
                        help="CI pass/fail gate: run full set, compare to committed baseline, "
                             "exit 1 on regression. Never writes the baseline.")
    args = parser.parse_args()

    if args.check and (args.only or args.case or args.baseline):
        print("run_golden: --check is a full-run gate; cannot combine with --only/--case/--baseline",
              file=sys.stderr)
        return 2

    sys.path.insert(0, str(PROJECT_ROOT))
    gen = load_module("generate", PROJECT_ROOT / "generate.py")
    ev = load_module("evaluator", PROJECT_ROOT / "evaluator" / "evaluator.py")
    from config import EVALUATOR_MODEL, GEN_MODEL  # noqa: E402

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("run_golden: ANTHROPIC_API_KEY not set (check .env)", file=sys.stderr)
        return 1
    client = gen.Anthropic(api_key=api_key)
    gen_model = GEN_MODEL
    eval_model = EVALUATOR_MODEL
    gen_rules = (gen.SKILL_FOLDERS[SKILL] / "references" / "rules.md").read_text(encoding="utf-8")
    eval_rules = ev.load_eval_rules(SKILL)

    case_dirs = sorted(d for d in CASES.iterdir() if d.is_dir())
    if args.case:
        case_dirs = [d for d in case_dirs if d.name == args.case]
        if not case_dirs:
            print(f"run_golden: no case named {args.case}", file=sys.stderr)
            return 1

    run_id = time.strftime("%Y%m%d_%H%M%S")
    results = {"run_id": run_id, "gen_model": gen_model, "eval_model": eval_model,
               "only": args.only, "cases": {}}

    for case_dir in case_dirs:
        name = case_dir.name
        print(f"Running {name} ...", flush=True)
        case_result: dict = {}
        try:
            pages = load_pages(gen.extract, PDFS / f"{name}.pdf")
            if args.only in (None, "planted"):
                case_result["planted"] = run_planted(case_dir, pages, ev, client, eval_model, eval_rules)
            if args.only in (None, "generator"):
                case_result["generator"] = run_generator(case_dir, pages, gen, ev, client,
                                                         gen_model, eval_model, gen_rules, eval_rules)
        except Exception as e:  # noqa: BLE001
            case_result["error"] = f"{type(e).__name__}: {e}"
        results["cases"][name] = case_result

    results["totals"] = totals(results)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{run_id}.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print_summary(results)
    print(f"\nSaved: {out}")

    had_error = any("error" in c for c in results["cases"].values())
    full_run = args.only is None and args.case is None

    if args.check:
        # Gate mode: never write the baseline; exit 1 on regression or staleness.
        if not BASELINE.is_file():
            print("\nFAIL: No baseline committed; run locally and commit "
                  "golden_dataset/baseline/baseline.json "
                  "(python3 golden_dataset/run_golden.py --baseline).",
                  file=sys.stderr)
            return 1
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        stale = staleness_reasons(results, base, gen_model, eval_model)
        if stale:
            print("\nFAIL: baseline out of date; re-baseline locally with "
                  "`python3 golden_dataset/run_golden.py --baseline` and commit it.",
                  file=sys.stderr)
            for r in stale:
                print(f"  - {r}", file=sys.stderr)
            return 1
        compare(results, base)
        violations = check_thresholds(results, base)
        if violations:
            print(f"\nFAIL: {len(violations)} rule(s) violated vs baseline {base['run_id']}:",
                  file=sys.stderr)
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            misses = collect_misses(results)
            if misses:
                print("\nMissed planted cards:", file=sys.stderr)
                for m in misses:
                    why = f": {m['why']}" if m['why'] else ""
                    print(f"  - {m['case']} card {m['card']} ({m['type']}){why}",
                          file=sys.stderr)
            return 1
        print("\nPASS: thresholds met vs baseline "
              f"{base['run_id']} (gen: {base.get('gen_model')}, "
              f"eval: {base.get('eval_model')}).")
        return 0

    if args.baseline or not BASELINE.is_file():
        reason = "--baseline given" if args.baseline else "no baseline yet"
        if had_error:
            print(f"\nNot saved as baseline ({reason}): some cases failed. Fix them and run again.")
        elif not full_run:
            print(f"\nNot saved as baseline ({reason}): this was a partial run "
                  "(--only or --case). Run all cases and both tests to set the baseline.")
        else:
            BASELINE.parent.mkdir(parents=True, exist_ok=True)
            BASELINE.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"\nSaved as baseline ({reason}): {BASELINE}")
    else:
        compare(results, json.loads(BASELINE.read_text(encoding="utf-8")))

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
