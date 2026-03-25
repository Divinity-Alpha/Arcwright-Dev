#!/usr/bin/env python3
"""
Arcwright Accuracy Report Generator

Builds the formatted console report from run results.

Usage:
    python scripts/tests/accuracy/report_generator.py --run latest
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ACCURACY_DIR = PROJECT_ROOT / "scripts" / "tests" / "accuracy"
RESULTS_DIR = ACCURACY_DIR / "results"

# Category display names and order
CATEGORY_DISPLAY = {
    "foundation": "Foundation",
    "create":     "Create",
    "modify":     "Modify",
    "query":      "Query",
    "multi":      "Multi-Step",
    "vague":      "Vague/Conv",
    "edge":       "Edge Cases",
}

CATEGORY_ORDER = ["foundation", "create", "modify", "query", "multi", "vague", "edge"]

# Root cause descriptions
ROOT_CAUSE_LABELS = {
    "I1": "intent misclass",
    "I2": "intent timeout",
    "I3": "wrong command",
    "P1": "empty plan",
    "P2": "wrong params",
    "P3": "bad command name",
    "P4": "missing dependency",
    "E1": "TCP error",
    "E2": "material not found",
    "E3": "actor not found",
    "E4": "blueprint not found",
    "E5": "param format",
    "V1": "wrong structure",
    "V2": "wrong value",
    "V3": "wrong targets",
    "V4": "partial success",
    "Q1": "bad var names",
    "Q2": "missing function",
    "Q3": "extra logic",
}

# Grade thresholds
def get_grade(pct):
    if pct >= 95: return "A+"
    if pct >= 90: return "A"
    if pct >= 85: return "B+"
    if pct >= 80: return "B"
    if pct >= 70: return "C"
    if pct >= 60: return "D"
    return "F"


def generate_report(run_data, previous_run=None):
    """Generate and print the formatted accuracy report."""
    run_num = run_data.get("run", 0)
    date = run_data.get("date", "?")
    total_score = run_data.get("total_score", 0)
    max_score = run_data.get("max_score", 0)
    pct = run_data.get("pct", 0.0)
    test_count = run_data.get("test_count", 0)
    categories = run_data.get("categories", {})
    failure_counts = run_data.get("failure_counts", {})
    results = run_data.get("results", {})

    grade = get_grade(pct)

    # Load previous run for comparison
    prev_pct = None
    prev_score = None
    if previous_run is None:
        prev_data = _load_previous_run(run_num)
        if prev_data:
            prev_pct = prev_data.get("pct", 0)
            prev_score = prev_data.get("total_score", 0)
    elif previous_run:
        prev_pct = previous_run.get("pct", 0)
        prev_score = previous_run.get("total_score", 0)

    # Header
    w = 65
    print(f"\n{'='*w}")
    print(f" ARCWRIGHT ACCURACY REPORT — Run #{run_num:03d} — {date}")
    print(f"{'='*w}")

    # Overall score
    delta_str = ""
    if prev_pct is not None:
        delta = pct - prev_pct
        sign = "+" if delta >= 0 else ""
        delta_str = f"   Previous: {prev_score}/{max_score} ({prev_pct}%)   Delta: {sign}{delta:.1f}%"

    print(f"\n Overall: {total_score}/{max_score} ({pct}%)  Grade: {grade}{delta_str}")
    print()

    # Category breakdown table
    header = f" {'Category':<16s} {'Intent':>6s} {'Plan':>6s} {'Exec':>6s} {'Verify':>6s} {'Qualit':>6s} {'Total':>7s}"
    sep =    f" {'-'*16} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*7}"
    print(header)
    print(sep)

    for cat in CATEGORY_ORDER:
        if cat not in categories:
            continue
        c = categories[cat]
        n = c["count"]
        if n == 0:
            continue
        label = CATEGORY_DISPLAY.get(cat, cat)
        cat_total = c["intent"] + c["plan"] + c["exec"] + c["verify"] + c["quality"]
        cat_max = n * 5

        print(f" {label+f' ({n})':<16s} "
              f"{c['intent']:>2d}/{n:<2d}  "
              f"{c['plan']:>2d}/{n:<2d}  "
              f"{c['exec']:>2d}/{n:<2d}  "
              f"{c['verify']:>2d}/{n:<2d}  "
              f"{c['quality']:>2d}/{n:<2d}  "
              f"{cat_total:>3d}/{cat_max}")

    # Totals row
    t_intent = sum(c["intent"] for c in categories.values())
    t_plan = sum(c["plan"] for c in categories.values())
    t_exec = sum(c["exec"] for c in categories.values())
    t_verify = sum(c["verify"] for c in categories.values())
    t_quality = sum(c["quality"] for c in categories.values())
    n_total = sum(c["count"] for c in categories.values())

    print(sep)
    print(f" {'TOTAL':<16s} "
          f"{t_intent:>2d}/{n_total:<2d}  "
          f"{t_plan:>2d}/{n_total:<2d}  "
          f"{t_exec:>2d}/{n_total:<2d}  "
          f"{t_verify:>2d}/{n_total:<2d}  "
          f"{t_quality:>2d}/{n_total:<2d}  "
          f"{total_score:>3d}/{max_score}")
    print()

    # Failure breakdown
    if failure_counts:
        print(" Failures by Root Cause:")
        sorted_codes = sorted(failure_counts.items(), key=lambda x: -x[1])
        for code, count in sorted_codes:
            label = ROOT_CAUSE_LABELS.get(code, "unknown")
            print(f"   {code} ({label}): {count}")
        print()

    # Failed tests detail
    failed_tests = [(tid, r) for tid, r in results.items() if r.get("total", 0) < 5]
    if failed_tests:
        failed_tests.sort(key=lambda x: x[1].get("total", 0))
        print(f" Failed Tests ({len(failed_tests)}):")
        for tid, r in failed_tests[:20]:
            score_bar = ""
            score_bar += "I" if r.get("intent_score") else "."
            score_bar += "P" if r.get("plan_score") else "."
            score_bar += "E" if r.get("exec_score") else "."
            score_bar += "V" if r.get("verify_score") else "."
            score_bar += "Q" if r.get("quality_score") else "."
            codes = ", ".join(r.get("failure_codes", []))
            print(f"   {tid:5s} [{score_bar}] {r.get('total',0)}/5  {codes}")
        if len(failed_tests) > 20:
            print(f"   ... and {len(failed_tests) - 20} more")
        print()

    # Accuracy trend
    history = _load_history()
    if history and len(history) > 1:
        print(" Accuracy Trend:")
        for entry in history[-10:]:
            marker = " <-- current" if entry.get("run") == run_num else ""
            print(f"   Run {entry['run']:03d}: {entry['pct']}%{marker}")
        print()

    # Dimension analysis
    dims = {"Intent": t_intent, "Plan": t_plan, "Execute": t_exec,
            "Verify": t_verify, "Quality": t_quality}
    weakest = min(dims.items(), key=lambda x: x[1])
    strongest = max(dims.items(), key=lambda x: x[1])
    print(f" Strongest dimension: {strongest[0]} ({strongest[1]}/{n_total})")
    print(f" Weakest dimension:  {weakest[0]} ({weakest[1]}/{n_total})")
    print()

    print(f"{'='*w}\n")


def _load_previous_run(current_num):
    """Load the run immediately before current_num."""
    history_path = ACCURACY_DIR / "accuracy_history.json"
    if not history_path.exists():
        return None
    with open(history_path) as f:
        history = json.load(f)
    runs = history.get("runs", [])
    prev_runs = [r for r in runs if r.get("run", 0) < current_num]
    if not prev_runs:
        return None
    return max(prev_runs, key=lambda r: r.get("run", 0))


def _load_history():
    """Load accuracy_history.json runs list."""
    history_path = ACCURACY_DIR / "accuracy_history.json"
    if not history_path.exists():
        return []
    with open(history_path) as f:
        return json.load(f).get("runs", [])


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Arcwright Report Generator")
    parser.add_argument("--run", default="latest", help="Run to report ('latest' or number)")
    args = parser.parse_args()

    # Load run data
    run_data = None
    if args.run == "latest":
        history_path = ACCURACY_DIR / "accuracy_history.json"
        if history_path.exists():
            with open(history_path) as f:
                history = json.load(f)
            runs = history.get("runs", [])
            if runs:
                latest = max(runs, key=lambda r: r.get("run", 0))
                run_file = RESULTS_DIR / latest["file"]
                if run_file.exists():
                    with open(run_file) as f:
                        run_data = json.load(f)
    else:
        for p in RESULTS_DIR.glob(f"run_{int(args.run):03d}_*.json"):
            with open(p) as f:
                run_data = json.load(f)
            break

    if not run_data:
        print("No run data found.")
        return

    generate_report(run_data)


if __name__ == "__main__":
    main()
