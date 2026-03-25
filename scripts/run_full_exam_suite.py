"""
Run full exam suite sequentially, reusing model between lessons.
Saves individual lesson results + combined summary.

Usage:
    python scripts/run_full_exam_suite.py --model models/blueprint-lora-v14/final --version v14
    python scripts/run_full_exam_suite.py --model models/blueprint-lora-v14/final --version v14 --start-lesson 10
"""
import os, sys, json, time, glob
from pathlib import Path
from datetime import datetime

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
sys.path.insert(0, str(Path(__file__).parent))

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-lesson", type=int, default=1, help="Lesson number to start from (e.g. 6 to resume from L06)")
    parser.add_argument("--model", type=str, default="models/blueprint-lora-v10/final", help="Path to LoRA adapter")
    parser.add_argument("--version", type=str, default="v10", help="Version label for output files (e.g. v14)")
    parser.add_argument("--max-lesson", type=int, default=99, help="Max lesson number to include")
    args = parser.parse_args()

    model_path = args.model
    version = args.version
    output_dir = "results/exams"
    lessons_dir = "lessons"

    # Find all lesson files matching lesson_XX.json (not bt_lesson or dt_lesson)
    lesson_files = sorted(glob.glob(f"{lessons_dir}/lesson_*.json"))
    lesson_files = [f for f in lesson_files
                    if not any(prefix in f for prefix in ["bt_lesson", "dt_lesson"])]
    # Filter by lesson number range
    import re
    filtered = []
    for f in lesson_files:
        m = re.search(r'lesson_(\d+)\.json$', f)
        if m:
            num = int(m.group(1))
            if args.start_lesson <= num <= args.max_lesson:
                filtered.append(f)
    lesson_files = filtered

    print(f"{'='*60}")
    print(f"  FULL EXAM SUITE — {version}")
    print(f"  {len(lesson_files)} lessons, model: {model_path}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Import and run each lesson
    from importlib import import_module
    exam_mod = __import__('12_run_exam')

    # Load model once
    print("Loading model...")
    start_load = time.time()
    model, tokenizer, base_model = exam_mod.load_model(model_path)
    print(f"Model loaded in {time.time()-start_load:.0f}s\n")

    all_summaries = []
    total_valid = 0
    total_prompts = 0
    total_sim_weighted = 0
    suite_start = time.time()

    for i, lesson_path in enumerate(lesson_files):
        lesson = json.load(open(lesson_path, encoding="utf-8"))
        lesson_id = lesson["lesson_id"]
        lesson_name = lesson["lesson_name"]
        n_prompts = len(lesson["prompts"])

        print(f"\n{'='*60}")
        print(f"  [{i+1}/{len(lesson_files)}] {lesson_id}: {lesson_name} ({n_prompts} prompts)")
        print(f"{'='*60}")

        # Run all prompts
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path(output_dir) / f"exam_{lesson_id}_{version}_{ts}.jsonl"
        summary_file = Path(output_dir) / f"exam_{lesson_id}_{version}_{ts}_summary.json"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = []
        valid_count = 0
        total_score = 0

        for j, prompt in enumerate(lesson["prompts"]):
            print(f"  [{j+1}/{n_prompts}] {prompt['id']}: {prompt['instruction'][:55]}...")

            start = time.time()
            cleaned_dsl, raw_output = exam_mod.generate(model, tokenizer, prompt["instruction"])
            elapsed = time.time() - start

            validation = exam_mod.validate_dsl(cleaned_dsl)
            comparison = exam_mod.compare_outputs(prompt["expected_dsl"], cleaned_dsl)

            status = "[OK]" if validation["valid"] else "[X]"
            print(f"    {status} Score: {comparison['score']:.0%} | Nodes: {validation['nodes']} | {elapsed:.1f}s")

            result = {
                "prompt_id": prompt["id"],
                "category": prompt["category"],
                "instruction": prompt["instruction"],
                "expected_dsl": prompt["expected_dsl"],
                "actual_dsl": cleaned_dsl,
                "raw_output": raw_output,
                "validation": validation,
                "comparison": comparison,
                "time_seconds": round(elapsed, 1),
                "status": "completed",
            }
            results.append(result)

            if validation["valid"]:
                valid_count += 1
            total_score += comparison["score"]

            # Write incrementally
            with open(results_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

        # Save summary
        avg_score = total_score / max(len(results), 1)
        summary = {
            "lesson_id": lesson_id,
            "lesson_name": lesson_name,
            "model": model_path,
            "base_model": base_model,
            "timestamp": ts,
            "total_prompts": len(results),
            "valid_syntax": valid_count,
            "valid_syntax_pct": round(valid_count / max(len(results), 1) * 100, 1),
            "avg_similarity_score": round(avg_score * 100, 1),
            "per_category": {},
        }

        for r in results:
            cat = r["category"]
            if cat not in summary["per_category"]:
                summary["per_category"][cat] = {"count": 0, "valid": 0, "avg_score": 0}
            summary["per_category"][cat]["count"] += 1
            if r["validation"]["valid"]:
                summary["per_category"][cat]["valid"] += 1
            summary["per_category"][cat]["avg_score"] += r["comparison"]["score"]

        for cat in summary["per_category"]:
            s = summary["per_category"][cat]
            s["avg_score"] = round(s["avg_score"] / max(s["count"], 1) * 100, 1)

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        all_summaries.append(summary)
        total_valid += valid_count
        total_prompts += len(results)
        total_sim_weighted += avg_score * len(results)

        print(f"  => syntax={summary['valid_syntax_pct']}% sim={summary['avg_similarity_score']}%")

    # Combined summary
    suite_elapsed = time.time() - suite_start
    combined = {
        "suite": f"{version}_exam",
        "model": model_path,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "total_lessons": len(all_summaries),
        "total_prompts": total_prompts,
        "total_valid": total_valid,
        "overall_syntax_pct": round(total_valid / max(total_prompts, 1) * 100, 1),
        "overall_similarity": round(total_sim_weighted / max(total_prompts, 1) * 100, 1),
        "suite_time_seconds": round(suite_elapsed, 1),
        "per_lesson": [{
            "lesson_id": s["lesson_id"],
            "syntax_pct": s["valid_syntax_pct"],
            "similarity": s["avg_similarity_score"],
            "valid": s["valid_syntax"],
            "total": s["total_prompts"],
        } for s in all_summaries],
    }

    combined_file = Path(output_dir) / f"exam_all_summaries_{version}_{combined['timestamp']}.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"  FULL SUITE RESULTS — {version}")
    print(f"{'='*60}")
    for s in all_summaries:
        print(f"  {s['lesson_id']:>12}: syntax={s['valid_syntax_pct']:5.1f}% ({s['valid_syntax']:2}/{s['total_prompts']:2})  sim={s['avg_similarity_score']:5.1f}%")
    print(f"  {'':>12}  {'─'*40}")
    print(f"  {'OVERALL':>12}: syntax={combined['overall_syntax_pct']:5.1f}% ({total_valid}/{total_prompts})  sim={combined['overall_similarity']:5.1f}%")
    print(f"  Time: {suite_elapsed/60:.1f} minutes")
    print(f"  Saved: {combined_file}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
