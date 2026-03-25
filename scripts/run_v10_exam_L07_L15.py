"""
Run v10 exam L07-L15, saving results incrementally.
Runs as standalone — no dependency on external task management.
"""
import os, sys, json, time, glob, traceback
from pathlib import Path
from datetime import datetime

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
sys.path.insert(0, str(Path(__file__).parent))

LOG_FILE = Path("logs/v10_exam_L07_L15.log")

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    output_dir = "results/exams"
    model_path = "models/blueprint-lora-v10/final"

    # Lessons to run: L07 through L15
    lesson_files = sorted(glob.glob("lessons/lesson_*.json"))
    lesson_files = [f for f in lesson_files if any(f"lesson_{i:02d}.json" in f for i in range(7, 16))]

    log(f"v10 Exam Suite L07-L15 — {len(lesson_files)} lessons")
    log(f"Model: {model_path}")

    exam_mod = __import__('12_run_exam')

    log("Loading model...")
    start_load = time.time()
    try:
        model, tokenizer, base_model = exam_mod.load_model(model_path)
    except Exception as e:
        log(f"FATAL: Model load failed: {e}")
        traceback.print_exc()
        return 1
    log(f"Model loaded in {time.time()-start_load:.0f}s")

    all_summaries = []
    total_valid = 0
    total_prompts = 0
    total_sim_weighted = 0

    for i, lesson_path in enumerate(lesson_files):
        lesson = json.load(open(lesson_path, encoding="utf-8"))
        lesson_id = lesson["lesson_id"]
        lesson_name = lesson["lesson_name"]
        n_prompts = len(lesson["prompts"])

        log(f"=== [{i+1}/{len(lesson_files)}] {lesson_id}: {lesson_name} ({n_prompts} prompts) ===")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path(output_dir) / f"exam_{lesson_id}_{ts}.jsonl"
        summary_file = Path(output_dir) / f"exam_{lesson_id}_{ts}_summary.json"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = []
        valid_count = 0
        total_score = 0

        for j, prompt in enumerate(lesson["prompts"]):
            log(f"  [{j+1}/{n_prompts}] {prompt['id']}")
            try:
                start = time.time()
                cleaned_dsl, raw_output = exam_mod.generate(model, tokenizer, prompt["instruction"])
                elapsed = time.time() - start

                validation = exam_mod.validate_dsl(cleaned_dsl)
                comparison = exam_mod.compare_outputs(prompt["expected_dsl"], cleaned_dsl)

                status_mark = "OK" if validation["valid"] else "X"
                log(f"    [{status_mark}] score={comparison['score']:.0%} nodes={validation['nodes']} {elapsed:.1f}s")

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

                with open(results_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")

            except Exception as e:
                log(f"    ERROR on {prompt['id']}: {e}")
                traceback.print_exc()
                # Write partial result
                result = {
                    "prompt_id": prompt["id"],
                    "category": prompt["category"],
                    "instruction": prompt["instruction"],
                    "status": "error",
                    "error": str(e),
                }
                results.append(result)
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
            cat = r.get("category", "unknown")
            if cat not in summary["per_category"]:
                summary["per_category"][cat] = {"count": 0, "valid": 0, "avg_score": 0}
            summary["per_category"][cat]["count"] += 1
            if r.get("validation", {}).get("valid", False):
                summary["per_category"][cat]["valid"] += 1
            summary["per_category"][cat]["avg_score"] += r.get("comparison", {}).get("score", 0)

        for cat in summary["per_category"]:
            s = summary["per_category"][cat]
            s["avg_score"] = round(s["avg_score"] / max(s["count"], 1) * 100, 1)

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        all_summaries.append(summary)
        total_valid += valid_count
        total_prompts += len(results)
        total_sim_weighted += avg_score * len(results)

        log(f"  => {lesson_id}: syntax={summary['valid_syntax_pct']}% sim={summary['avg_similarity_score']}%")

    # Combined summary
    if all_summaries:
        combined = {
            "suite": "v10_L07_L15",
            "model": model_path,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "total_lessons": len(all_summaries),
            "total_prompts": total_prompts,
            "total_valid": total_valid,
            "overall_syntax_pct": round(total_valid / max(total_prompts, 1) * 100, 1),
            "overall_similarity": round(total_sim_weighted / max(total_prompts, 1) * 100, 1),
            "per_lesson": [{
                "lesson_id": s["lesson_id"],
                "syntax_pct": s["valid_syntax_pct"],
                "similarity": s["avg_similarity_score"],
                "valid": s["valid_syntax"],
                "total": s["total_prompts"],
            } for s in all_summaries],
        }
        combined_file = Path(output_dir) / f"exam_all_summaries_v10_L07_L15_{combined['timestamp']}.json"
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
        log(f"Combined saved: {combined_file}")

    log("Suite complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
