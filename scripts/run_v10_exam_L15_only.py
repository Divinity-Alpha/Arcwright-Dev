"""Run v10 exam for L15 only."""
import os, sys, json, time, traceback
from pathlib import Path
from datetime import datetime

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
sys.path.insert(0, str(Path(__file__).parent))

LOG_FILE = Path("logs/v10_exam_L15.log")

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    output_dir = "results/exams"
    model_path = "models/blueprint-lora-v10/final"

    log("v10 Exam L15 Only")
    exam_mod = __import__('12_run_exam')

    log("Loading model...")
    start_load = time.time()
    model, tokenizer, base_model = exam_mod.load_model(model_path)
    log(f"Model loaded in {time.time()-start_load:.0f}s")

    lesson = json.load(open("lessons/lesson_15.json", encoding="utf-8"))
    lesson_id = lesson["lesson_id"]
    n_prompts = len(lesson["prompts"])
    log(f"L15: {lesson['lesson_name']} ({n_prompts} prompts)")

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
                "prompt_id": prompt["id"], "category": prompt["category"],
                "instruction": prompt["instruction"],
                "expected_dsl": prompt["expected_dsl"], "actual_dsl": cleaned_dsl,
                "raw_output": raw_output, "validation": validation,
                "comparison": comparison, "time_seconds": round(elapsed, 1),
                "status": "completed",
            }
            results.append(result)
            if validation["valid"]: valid_count += 1
            total_score += comparison["score"]
            with open(results_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        except Exception as e:
            log(f"    ERROR: {e}")
            traceback.print_exc()
            results.append({"prompt_id": prompt["id"], "category": prompt["category"],
                           "status": "error", "error": str(e)})

    avg_score = total_score / max(len(results), 1)
    summary = {
        "lesson_id": lesson_id, "lesson_name": lesson["lesson_name"],
        "model": model_path, "base_model": base_model, "timestamp": ts,
        "total_prompts": len(results), "valid_syntax": valid_count,
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

    log(f"L15 RESULT: syntax={summary['valid_syntax_pct']}% sim={summary['avg_similarity_score']}%")
    log("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
