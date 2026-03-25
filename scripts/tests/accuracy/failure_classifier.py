#!/usr/bin/env python3
"""
Arcwright Failure Classifier

Auto-classifies test failures by 17 root cause codes.
Compares to previous runs to find new failures, fixes, and persistent issues.
Updates known_failures.json.

Usage:
    python scripts/tests/accuracy/failure_classifier.py --run latest
    python scripts/tests/accuracy/failure_classifier.py --run 3
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ACCURACY_DIR = PROJECT_ROOT / "scripts" / "tests" / "accuracy"
RESULTS_DIR = ACCURACY_DIR / "results"

# Root cause code descriptions
ROOT_CAUSE_CODES = {
    "I1": "Intent misclassified (wrong mode)",
    "I2": "Intent timeout / empty response",
    "I3": "Intent returned wrong command",
    "P1": "Plan has empty operations",
    "P2": "Plan has wrong parameters",
    "P3": "Plan uses non-existent command",
    "P4": "Plan missing step dependency",
    "E1": "TCP command returned error",
    "E2": "Material not found / not resolved",
    "E3": "Actor not found",
    "E4": "Blueprint not found",
    "E5": "Parameter format mismatch",
    "V1": "Asset created but wrong structure",
    "V2": "Variable exists but wrong value",
    "V3": "Correct command but wrong targets changed",
    "V4": "Partial success (some actors failed)",
    "Q1": "Quality: variable names nonsensical",
    "Q2": "Quality: missing expected functionality",
    "Q3": "Quality: extra unwanted nodes/logic",
}

# Where to fix each root cause
FIX_LOCATIONS = {
    "I1": "intent_server.py CLASSIFY_PROMPT or hard override",
    "I2": "Inference timeout / model issue",
    "I3": "intent_server.py CLASSIFY_PROMPT or hard override",
    "P1": "intent_server.py REFINE_PROMPT examples",
    "P2": "intent_server.py REFINE_PROMPT or post-processor",
    "P3": "intent_server.py COMMAND_WHITELIST / alias map",
    "P4": "ArcwrightGeneratorPanel.cpp post-processor",
    "E1": "CommandServer.cpp handler bug",
    "E2": "CommandServer.cpp ResolveMaterialByName",
    "E3": "intent_server.py discovery stage filters",
    "E4": "intent_server.py search path issue",
    "E5": "intent_server.py _postprocess_plan normalization",
    "V1": "Training lessons (DSL model quality)",
    "V2": "Training lessons (DSL model quality)",
    "V3": "intent_server.py discovery stage filter issue",
    "V4": "Actors missing components / partial batch",
    "Q1": "Training lessons (variable naming)",
    "Q2": "Training lessons (missing functionality)",
    "Q3": "Training lessons (excess logic)",
}


def classify_failures(run_data):
    """Classify all failures in a run by root cause code."""
    results = run_data.get("results", {})
    failures = []

    for test_id, result in results.items():
        total = result.get("total", 0)
        if total == 5:
            continue  # Perfect score, skip

        codes = result.get("failure_codes", [])
        if not codes:
            # Infer codes from scores
            if not result.get("intent_score"):
                codes.append("I1")
            if not result.get("plan_score"):
                codes.append("P2")
            if not result.get("exec_score"):
                codes.append("E1")
            if not result.get("verify_score"):
                codes.append("V1")
            if not result.get("quality_score"):
                codes.append("Q2")

        # Deduplicate
        codes = list(dict.fromkeys(codes))

        failure = {
            "test_id": test_id,
            "total": total,
            "intent": result.get("intent_score", 0),
            "plan": result.get("plan_score", 0),
            "exec": result.get("exec_score", 0),
            "verify": result.get("verify_score", 0),
            "quality": result.get("quality_score", 0),
            "actual_mode": result.get("actual_mode", ""),
            "actual_commands": result.get("actual_commands", []),
            "root_causes": codes,
            "error": result.get("error", ""),
        }
        failures.append(failure)

    return failures


def compare_to_previous(current_run, failures):
    """Compare current failures to previous run. Find new, fixed, and persistent."""
    history_path = ACCURACY_DIR / "accuracy_history.json"
    if not history_path.exists():
        return [], [], failures

    with open(history_path) as f:
        history = json.load(f)

    runs = history.get("runs", [])
    current_num = current_run.get("run", 0)

    # Find previous run
    prev_runs = [r for r in runs if r.get("run", 0) < current_num]
    if not prev_runs:
        return [], [], failures

    prev = max(prev_runs, key=lambda r: r.get("run", 0))
    prev_file = RESULTS_DIR / prev["file"]
    if not prev_file.exists():
        return [], [], failures

    with open(prev_file) as f:
        prev_data = json.load(f)

    prev_results = prev_data.get("results", {})
    prev_failed_ids = {tid for tid, r in prev_results.items() if r.get("total", 0) < 5}
    curr_failed_ids = {f["test_id"] for f in failures}

    new_failures = [f for f in failures if f["test_id"] not in prev_failed_ids]
    fixed = [tid for tid in prev_failed_ids if tid not in curr_failed_ids]
    persistent = [f for f in failures if f["test_id"] in prev_failed_ids]

    return new_failures, fixed, persistent


def update_known_failures(run_data, failures):
    """Update known_failures.json with current run data."""
    kf_path = ACCURACY_DIR / "known_failures.json"
    if kf_path.exists():
        with open(kf_path) as f:
            known = json.load(f)
    else:
        known = {"failures": []}

    run_num = run_data.get("run", 0)
    current_failed_ids = {f["test_id"] for f in failures}

    # Load test commands for prompt text
    tests_path = ACCURACY_DIR / "test_commands.json"
    test_prompts = {}
    if tests_path.exists():
        with open(tests_path) as f:
            for cmd in json.load(f).get("commands", []):
                test_prompts[cmd["id"]] = cmd["prompt"]

    # Update existing entries
    for entry in known["failures"]:
        tid = entry["test_id"]
        if tid in current_failed_ids:
            entry["last_seen_run"] = run_num
            entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
            if entry["consecutive_failures"] >= 3:
                entry["priority"] = "HIGH"
            elif entry["consecutive_failures"] >= 2:
                entry["priority"] = "MEDIUM"
            # Update root causes
            matching = [f for f in failures if f["test_id"] == tid]
            if matching:
                entry["root_causes"] = matching[0]["root_causes"]
        else:
            # Fixed!
            entry["status"] = "FIXED"
            entry["fixed_in_run"] = run_num
            entry["consecutive_failures"] = 0

    # Add new failures
    known_ids = {e["test_id"] for e in known["failures"]}
    for f in failures:
        if f["test_id"] not in known_ids:
            known["failures"].append({
                "test_id": f["test_id"],
                "prompt": test_prompts.get(f["test_id"], ""),
                "root_causes": f["root_causes"],
                "description": f.get("error", "") or ", ".join(f["root_causes"]),
                "first_seen_run": run_num,
                "last_seen_run": run_num,
                "consecutive_failures": 1,
                "priority": "LOW",
                "fix_attempted": "",
                "status": "OPEN",
            })

    with open(kf_path, "w") as f:
        json.dump(known, f, indent=2)

    return known


def classify_run(run_data):
    """Full classification pipeline for a run."""
    run_num = run_data.get("run", 0)
    failures = classify_failures(run_data)
    new_failures, fixed, persistent = compare_to_previous(run_data, failures)
    known = update_known_failures(run_data, failures)

    # Print classification report
    print(f"\n{'='*65}")
    print(f" FAILURE CLASSIFICATION — Run #{run_num:03d}")
    print(f"{'='*65}")

    total_tests = run_data.get("test_count", 0)
    passed = total_tests - len(failures)
    print(f"\n  {passed}/{total_tests} passed, {len(failures)} failures\n")

    if failures:
        # Count by root cause
        cause_counts = {}
        for f in failures:
            for code in f["root_causes"]:
                cause_counts[code] = cause_counts.get(code, 0) + 1

        print("  Failures by Root Cause:")
        for code, count in sorted(cause_counts.items(), key=lambda x: -x[1]):
            desc = ROOT_CAUSE_CODES.get(code, "Unknown")
            fix = FIX_LOCATIONS.get(code, "Unknown")
            print(f"    {code} ({desc}): {count}")

        if new_failures:
            print(f"\n  NEW failures (not in previous run): {len(new_failures)}")
            for f in new_failures[:5]:
                print(f"    {f['test_id']}: {', '.join(f['root_causes'])}")

        if fixed:
            print(f"\n  FIXED (failed before, pass now): {len(fixed)}")
            for tid in fixed[:5]:
                print(f"    {tid}")

        high_priority = [f for f in failures
                         if any(e.get("test_id") == f["test_id"] and
                                e.get("consecutive_failures", 0) >= 3
                                for e in known.get("failures", []))]
        if high_priority:
            print(f"\n  HIGH PRIORITY (failed 3+ runs): {len(high_priority)}")
            for f in high_priority:
                print(f"    {f['test_id']}: {', '.join(f['root_causes'])} — "
                      f"actual_mode={f['actual_mode']}")

    print()
    return failures


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Arcwright Failure Classifier")
    parser.add_argument("--run", default="latest", help="Run to classify ('latest' or number)")
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

    classify_run(run_data)


if __name__ == "__main__":
    main()
