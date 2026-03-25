"""
Overnight Blueprint v12 Training + Exam Cycle
==============================================
Continuation training from v11 + lesson_17 corrections.

Targets 18 weak categories from v11 (<50% similarity):
  full_game_loop, math_heavy, spawn_pattern, moving_platform,
  hud_health, physics_force, movement_clamp, branch, foreach,
  timer_clear, ui_complete_flow, ui_input_close, ui_gate_controlled...

Runs:
  1. Train v12 (continuation from v11, lr=5e-5, 2 epochs)
  2. Exam v12 against ALL 17 lessons
  3. Backup to D:
  4. Print comparison matrix v11 vs v12
"""
import os
import sys
import io
import json
import time
import glob
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Force UTF-8 on Windows (Lesson #54)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# ── Config ──────────────────────────────────────────────────────
MODEL_V11 = "models/blueprint-lora-v11/final"
MODEL_V12_OUTPUT = "models/blueprint-lora-v12"
DATASET = "datasets/train.jsonl"
LESSONS_DIR = "lessons"
EXAM_OUTPUT_DIR = "results/exams"
BACKUP_D = Path("D:/BlueprintLLMBackup")

CONTINUATION_LR = 5e-5
CONTINUATION_EPOCHS = 2
VERSION = "v12"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii', errors='replace').decode()}", flush=True)


def phase_1_train():
    """Train v12 as continuation from v11."""
    log("=" * 60)
    log("  PHASE 1: Train Blueprint v12 (continuation from v11)")
    log(f"  Dataset: {DATASET} | LR: {CONTINUATION_LR} | Epochs: {CONTINUATION_EPOCHS}")
    log("=" * 60)

    cmd = [
        sys.executable, "scripts/04_train_blueprint_lora.py",
        "--dataset", DATASET,
        "--output", MODEL_V12_OUTPUT,
        "--resume_from", MODEL_V11,
        "--continuation_lr", str(CONTINUATION_LR),
        "--epochs", str(CONTINUATION_EPOCHS),
    ]

    log(f"CMD: {' '.join(cmd)}")
    start = time.time()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # Reset heartbeat before launch (prevents stale file from previous run triggering kill)
    heartbeat_path = PROJECT_ROOT / "logs" / "pipeline_heartbeat"
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text(f"v12 training started {datetime.now().isoformat()}")
    log(f"  Heartbeat reset: {heartbeat_path}")

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env, cwd=str(PROJECT_ROOT)
    )

    # Monitor via heartbeat (Rule 18)
    # Don't check heartbeat until model has had time to load (~3 min)
    WARMUP_SECONDS = 300  # 5 min warmup before stall detection activates
    STALL_THRESHOLD = 1800  # 30 min

    for line in iter(proc.stdout.readline, b""):
        try:
            text = line.decode("utf-8", errors="replace").rstrip()
        except Exception:
            text = str(line)
        if text:
            log(f"  [TRAIN] {text}")

        # Only check heartbeat after warmup period
        elapsed = time.time() - start
        if elapsed > WARMUP_SECONDS and heartbeat_path.exists():
            hb_age = time.time() - heartbeat_path.stat().st_mtime
            if hb_age > STALL_THRESHOLD:
                log(f"  [STALL] Heartbeat age {hb_age:.0f}s > {STALL_THRESHOLD}s — killing")
                proc.kill()
                return False

    proc.wait()
    elapsed = time.time() - start
    log(f"  Training completed in {elapsed/60:.1f} minutes (exit code: {proc.returncode})")

    # Verify adapter was saved
    adapter_path = Path(MODEL_V12_OUTPUT) / "final" / "adapter_model.safetensors"
    if not adapter_path.exists():
        log(f"  [ERROR] Adapter not found at {adapter_path}")
        return False

    size_mb = adapter_path.stat().st_size / (1024 * 1024)
    log(f"  Adapter saved: {adapter_path} ({size_mb:.1f} MB)")
    return True


def phase_2_exam():
    """Run exam against all 17 lessons using v12 model."""
    log("")
    log("=" * 60)
    log("  PHASE 2: Full Exam Suite — v12 vs L01-L17")
    log("=" * 60)

    model_path = f"{MODEL_V12_OUTPUT}/final"

    # Find all lesson files L01-L17
    lesson_files = sorted(glob.glob(f"{LESSONS_DIR}/lesson_*.json"))
    lesson_files = [f for f in lesson_files if any(f"lesson_{i:02d}.json" in f for i in range(1, 18))]

    log(f"  {len(lesson_files)} lessons, model: {model_path}")

    # Import exam module
    import importlib
    exam_mod = importlib.import_module('12_run_exam')

    # Load model once
    log("  Loading model...")
    start_load = time.time()
    model, tokenizer, base_model = exam_mod.load_model(model_path)
    log(f"  Model loaded in {time.time()-start_load:.0f}s")

    all_summaries = []
    total_valid = 0
    total_prompts = 0
    total_sim_weighted = 0
    suite_start = time.time()

    Path(EXAM_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    for i, lesson_path in enumerate(lesson_files):
        lesson = json.load(open(lesson_path, encoding="utf-8"))
        lesson_id = lesson["lesson_id"]
        lesson_name = lesson["lesson_name"]
        n_prompts = len(lesson["prompts"])

        log(f"\n  [{i+1}/{len(lesson_files)}] {lesson_id}: {lesson_name} ({n_prompts} prompts)")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path(EXAM_OUTPUT_DIR) / f"exam_{lesson_id}_v12_{ts}.jsonl"
        summary_file = Path(EXAM_OUTPUT_DIR) / f"exam_{lesson_id}_v12_{ts}_summary.json"

        results = []
        valid_count = 0
        total_score = 0

        for j, prompt in enumerate(lesson["prompts"]):
            log(f"    [{j+1}/{n_prompts}] {prompt['id']}: {prompt['instruction'][:55]}...")

            start = time.time()
            try:
                cleaned_dsl, raw_output = exam_mod.generate(model, tokenizer, prompt["instruction"])
            except Exception as e:
                log(f"    [ERROR] {e}")
                cleaned_dsl = ""
                raw_output = str(e)
            elapsed = time.time() - start

            validation = exam_mod.validate_dsl(cleaned_dsl)
            comparison = exam_mod.compare_outputs(prompt["expected_dsl"], cleaned_dsl)

            status = "[OK]" if validation["valid"] else "[X]"
            log(f"    {status} Score: {comparison['score']:.0%} | Nodes: {validation['nodes']} | {elapsed:.1f}s")

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

        log(f"  => syntax={summary['valid_syntax_pct']}% sim={summary['avg_similarity_score']}%")

    # Combined summary
    suite_elapsed = time.time() - suite_start
    combined = {
        "version": VERSION,
        "model": model_path,
        "base_model": base_model,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "total_lessons": len(all_summaries),
        "total_prompts": total_prompts,
        "total_valid_syntax": total_valid,
        "valid_syntax_pct": round(total_valid / max(total_prompts, 1) * 100, 1),
        "avg_score": round(total_sim_weighted / max(total_prompts, 1) * 100, 1),
        "passed": len(all_summaries),
        "failed": 0,
        "suite_time_seconds": round(suite_elapsed, 1),
        "lessons": all_summaries,
    }

    combined_file = Path(EXAM_OUTPUT_DIR) / f"exam_all_summaries_{VERSION}_{combined['timestamp']}.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    log(f"\n{'='*60}")
    log(f"  FULL SUITE RESULTS — {VERSION}")
    log(f"{'='*60}")
    for s in all_summaries:
        log(f"  {s['lesson_id']:>12}: syntax={s['valid_syntax_pct']:5.1f}% ({s['valid_syntax']:2}/{s['total_prompts']:2})  sim={s['avg_similarity_score']:5.1f}%")
    log(f"  {'':>12}  {'─'*40}")
    log(f"  {'OVERALL':>12}: syntax={combined['valid_syntax_pct']:5.1f}% ({total_valid}/{total_prompts})  sim={combined['avg_score']:5.1f}%")
    log(f"  Time: {suite_elapsed/60:.1f} minutes")
    log(f"  Saved: {combined_file}")

    return combined


def phase_3_backup():
    """Backup v12 adapter + exam results to D:"""
    log("")
    log("=" * 60)
    log("  PHASE 3: Backup to D:")
    log("=" * 60)

    if not BACKUP_D.exists():
        log("  [WARN] D: drive not available — skipping backup")
        return

    # Copy model
    src_model = Path(MODEL_V12_OUTPUT)
    dst_model = BACKUP_D / MODEL_V12_OUTPUT
    if src_model.exists():
        log(f"  Copying {src_model} -> {dst_model}")
        shutil.copytree(str(src_model), str(dst_model), dirs_exist_ok=True)

        # Verify adapter size
        src_adapter = src_model / "final" / "adapter_model.safetensors"
        dst_adapter = dst_model / "final" / "adapter_model.safetensors"
        if src_adapter.exists() and dst_adapter.exists():
            src_size = src_adapter.stat().st_size
            dst_size = dst_adapter.stat().st_size
            match = "YES" if src_size == dst_size else "NO !!!"
            log(f"  Adapter: C={src_size} D={dst_size} Match={match}")
        else:
            log(f"  [WARN] Adapter file missing on one drive")

    # Copy exam results
    src_exams = Path(EXAM_OUTPUT_DIR)
    dst_exams = BACKUP_D / EXAM_OUTPUT_DIR
    if src_exams.exists():
        log(f"  Copying exam results -> {dst_exams}")
        shutil.copytree(str(src_exams), str(dst_exams), dirs_exist_ok=True)

    # Copy datasets and lessons
    for subdir in ["datasets", "lessons"]:
        src = Path(subdir)
        dst = BACKUP_D / subdir
        if src.exists():
            log(f"  Copying {subdir} -> {dst}")
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)

    log("  Backup complete.")


def phase_4_compare():
    """Print v11 vs v12 comparison."""
    log("")
    log("=" * 60)
    log("  PHASE 4: v11 vs v12 Comparison")
    log("=" * 60)

    # Load v11 results
    v11_file = Path("results/exams/exam_all_summaries_v11_20260306_141228.json")
    if v11_file.exists():
        v11 = json.load(open(v11_file, encoding="utf-8"))
        v11_lessons = {s["lesson_id"]: s for s in v11["lessons"]}
    else:
        log("  [WARN] v11 results not found — skipping comparison")
        return

    # Load v12 results (most recent)
    v12_files = sorted(glob.glob(f"{EXAM_OUTPUT_DIR}/exam_all_summaries_v12_*.json"))
    if not v12_files:
        log("  [WARN] v12 results not found — skipping comparison")
        return

    v12 = json.load(open(v12_files[-1], encoding="utf-8"))
    v12_lessons = {s["lesson_id"]: s for s in v12["lessons"]}

    log(f"\n  {'Lesson':>12}  {'v11 Syn':>8}  {'v12 Syn':>8}  {'v11 Sim':>8}  {'v12 Sim':>8}  {'Delta':>7}")
    log(f"  {'':>12}  {'─'*50}")

    all_lessons = sorted(set(list(v11_lessons.keys()) + list(v12_lessons.keys())))
    for lid in all_lessons:
        v11_syn = v11_lessons.get(lid, {}).get("valid_syntax_pct", "—")
        v12_syn = v12_lessons.get(lid, {}).get("valid_syntax_pct", "—")
        v11_sim = v11_lessons.get(lid, {}).get("avg_similarity_score", "—")
        v12_sim = v12_lessons.get(lid, {}).get("avg_similarity_score", "—")

        if isinstance(v11_sim, (int, float)) and isinstance(v12_sim, (int, float)):
            delta = v12_sim - v11_sim
            delta_str = f"{delta:+.1f}%"
        else:
            delta_str = "NEW"

        v11_syn_s = f"{v11_syn}%" if isinstance(v11_syn, (int, float)) else v11_syn
        v12_syn_s = f"{v12_syn}%" if isinstance(v12_syn, (int, float)) else v12_syn
        v11_sim_s = f"{v11_sim}%" if isinstance(v11_sim, (int, float)) else v11_sim
        v12_sim_s = f"{v12_sim}%" if isinstance(v12_sim, (int, float)) else v12_sim

        log(f"  {lid:>12}  {v11_syn_s:>8}  {v12_syn_s:>8}  {v11_sim_s:>8}  {v12_sim_s:>8}  {delta_str:>7}")

    log(f"  {'':>12}  {'─'*50}")
    log(f"  {'OVERALL':>12}  {v11.get('valid_syntax_pct','—')}%     {v12.get('valid_syntax_pct','—')}%     {v11.get('avg_score','—')}%     {v12.get('avg_score','—')}%")


def main():
    log("=" * 60)
    log("  OVERNIGHT BLUEPRINT v12 TRAINING + EXAM CYCLE")
    log(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # Phase 1: Train
    success = phase_1_train()
    if not success:
        log("[ABORT] Training failed — stopping cycle")
        return

    # Phase 2: Exam
    results = phase_2_exam()

    # Phase 3: Backup
    phase_3_backup()

    # Phase 4: Compare
    phase_4_compare()

    log(f"\n  Cycle complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
