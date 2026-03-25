"""
Regenerate all IR test files from v9 FIXED exam JSONL outputs.
The fixed stopping criteria (2026-03-04) produces complete DATA lines.

Reads ir_test_selections.json for test_id → instruction mappings,
finds matching prompts in the fixed exam JSONL files,
extracts actual_dsl, parses through DSL parser, saves IR JSON.
"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "dsl_parser"))
from parser import parse, save_ir

ROOT = Path(__file__).parent.parent
SELECTIONS_FILE = ROOT / "ir_test_selections.json"
IR_DIR = ROOT / "test_ir"

# Fixed exam JSONL files (20260304_18xxxx through 20260304_21xxxx)
FIXED_JSONL_MAP = {
    1: ROOT / "results/exams/exam_lesson_01_20260304_181243.jsonl",
    2: ROOT / "results/exams/exam_lesson_02_20260304_182252.jsonl",
    3: ROOT / "results/exams/exam_lesson_03_20260304_183509.jsonl",
    4: ROOT / "results/exams/exam_lesson_04_20260304_185041.jsonl",
    5: ROOT / "results/exams/exam_lesson_05_20260304_190435.jsonl",
    6: ROOT / "results/exams/exam_lesson_06_20260304_192125.jsonl",
    7: ROOT / "results/exams/exam_lesson_07_20260304_193811.jsonl",
    8: ROOT / "results/exams/exam_lesson_08_20260304_195127.jsonl",
    9: ROOT / "results/exams/exam_lesson_09_20260304_200852.jsonl",
    10: ROOT / "results/exams/exam_lesson_10_20260304_203042.jsonl",
    11: ROOT / "results/exams/exam_lesson_11_20260304_205703.jsonl",
    12: ROOT / "results/exams/exam_lesson_12_20260304_211845.jsonl",
    13: ROOT / "results/exams/exam_lesson_13_20260304_213422.jsonl",
    14: ROOT / "results/exams/exam_lesson_14_20260304_215522.jsonl",
}


def load_exam_entries(jsonl_path):
    """Load all entries from a JSONL exam file."""
    entries = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def main():
    selections = json.load(open(SELECTIONS_FILE, encoding="utf-8"))
    tests = selections["selections"]

    print(f"{'='*60}")
    print(f"  REGENERATE IR FROM FIXED v9 EXAM OUTPUTS")
    print(f"  {len(tests)} test files to generate")
    print(f"{'='*60}\n")

    # Pre-load all needed JSONL files
    exam_cache = {}
    needed_lessons = set(t["lesson"] for t in tests)
    for lesson_num in sorted(needed_lessons):
        jsonl_path = FIXED_JSONL_MAP[lesson_num]
        if not jsonl_path.exists():
            print(f"  ERROR: Missing JSONL for lesson {lesson_num}: {jsonl_path}")
            continue
        exam_cache[lesson_num] = load_exam_entries(jsonl_path)
        print(f"  Loaded L{lesson_num:02d}: {len(exam_cache[lesson_num])} entries")

    print()
    IR_DIR.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    results = []

    for i, test in enumerate(tests):
        test_id = test["test_id"]
        lesson_num = test["lesson"]
        instruction = test["instruction"]

        # Find matching entry by instruction text
        entries = exam_cache.get(lesson_num, [])
        match = None
        for entry in entries:
            if entry["instruction"].strip() == instruction.strip():
                match = entry
                break

        if not match:
            # Try fuzzy match (first 60 chars)
            for entry in entries:
                if entry["instruction"][:60] == instruction[:60]:
                    match = entry
                    break

        if not match:
            print(f"  [{i+1:2d}/25] {test_id}: MISS — no matching instruction in L{lesson_num:02d}")
            failed += 1
            results.append({"test_id": test_id, "status": "miss", "reason": "no matching instruction"})
            continue

        actual_dsl = match.get("actual_dsl", "")
        if not actual_dsl:
            print(f"  [{i+1:2d}/25] {test_id}: EMPTY — actual_dsl is empty")
            failed += 1
            results.append({"test_id": test_id, "status": "empty", "prompt_id": match.get("prompt_id")})
            continue

        # Parse DSL to IR
        ir_result = parse(actual_dsl)
        ir_path = IR_DIR / f"{test_id}.blueprint.json"
        save_ir(ir_result, str(ir_path))

        nodes = ir_result["stats"]["nodes"]
        conns = ir_result["stats"]["connections"]
        mapped = ir_result["stats"]["mapped"]
        unmapped = ir_result["stats"]["unmapped"]
        errors = ir_result["errors"]

        status_str = "OK" if not errors else f"WARN({len(errors)} errors)"
        print(f"  [{i+1:2d}/25] {test_id}: {status_str} | {nodes}n {conns}c | mapped={mapped} unmapped={unmapped} | {match['prompt_id']}")

        if errors:
            for e in errors[:3]:
                print(f"         ERROR: {e}")

        success += 1
        results.append({
            "test_id": test_id,
            "status": "ok",
            "prompt_id": match.get("prompt_id"),
            "nodes": nodes,
            "connections": conns,
            "mapped": mapped,
            "unmapped": unmapped,
            "errors": errors,
        })

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {success}/{len(tests)} IR files generated, {failed} failed")
    print(f"{'='*60}")

    # Save generation report
    report = {
        "source": "v9_fixed_stopping_criteria",
        "exam_timestamps": "20260304_18xxxx-21xxxx",
        "total_tests": len(tests),
        "generated": success,
        "failed": failed,
        "results": results,
    }
    report_path = ROOT / "results" / "ir_regeneration_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
