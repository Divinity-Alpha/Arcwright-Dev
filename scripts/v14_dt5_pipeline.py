"""
Post-training pipeline: v14 exam → backup → DT v5 training → DT v5 exam → backup.
Waits for v14 training completion, then runs everything sequentially.
"""
import os, sys, json, time, subprocess, shutil, glob, re
from pathlib import Path
from datetime import datetime

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}")
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii', errors='replace').decode()}")
    sys.stdout.flush()

def wait_for_v14():
    """Wait for v14 adapter to appear (training completion)."""
    adapter_path = "models/blueprint-lora-v14/final/adapter_model.safetensors"
    log("Waiting for v14 training to complete...")
    while not os.path.exists(adapter_path):
        time.sleep(30)
        # Check heartbeat
        try:
            hb_age = time.time() - os.path.getmtime("logs/pipeline_heartbeat")
            if hb_age > 1800:
                log(f"WARNING: Heartbeat stale ({hb_age:.0f}s) — training may have crashed")
                return False
        except:
            pass
    size = os.path.getsize(adapter_path)
    log(f"V14 adapter saved: {size:,} bytes")
    # Wait a bit for training process to fully exit
    time.sleep(30)
    return True

def run_v14_exam():
    """Run full v14 exam suite across all 23 lessons."""
    log("=" * 60)
    log("STARTING V14 EXAM SUITE (23 lessons)")
    log("=" * 60)

    cmd = [
        sys.executable, "scripts/run_full_exam_suite.py",
        "--model", "models/blueprint-lora-v14/final",
        "--version", "v14",
    ]
    proc = subprocess.run(cmd, capture_output=False, timeout=14400)  # 4h max

    # Find and report combined summary
    summaries = sorted(glob.glob("results/exams/exam_all_summaries_v14_*.json"))
    if summaries:
        with open(summaries[-1], encoding="utf-8") as f:
            data = json.load(f)
        log(f"V14 RESULTS: {data['overall_syntax_pct']}% syntax / {data['overall_similarity']}% similarity")
        log(f"  {data['total_lessons']} lessons, {data['total_prompts']} prompts, {data['total_valid']} valid")
        for lesson in data.get("per_lesson", []):
            log(f"  {lesson['lesson_id']:>12}: syntax={lesson['syntax_pct']:5.1f}% sim={lesson['similarity']:5.1f}%")
        return True
    else:
        log("ERROR: No combined summary found")
        return False

def backup_v14():
    """Backup v14 adapter to D:."""
    log("Backing up v14 to D:\\BlueprintLLMBackup\\models\\...")
    src = "C:\\BlueprintLLM\\models\\blueprint-lora-v14"
    dst = "D:\\BlueprintLLMBackup\\models\\blueprint-lora-v14"
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        # Verify
        src_size = os.path.getsize(os.path.join(src, "final", "adapter_model.safetensors"))
        dst_size = os.path.getsize(os.path.join(dst, "final", "adapter_model.safetensors"))
        if src_size == dst_size:
            log(f"V14 backup verified: {src_size:,} bytes match")
        else:
            log(f"WARNING: Size mismatch! C:{src_size} vs D:{dst_size}")
    except Exception as e:
        log(f"Backup error: {e}")

    # Also backup datasets and lessons
    try:
        shutil.copytree("C:\\BlueprintLLM\\datasets", "D:\\BlueprintLLMBackup\\datasets", dirs_exist_ok=True)
        shutil.copytree("C:\\BlueprintLLM\\lessons", "D:\\BlueprintLLMBackup\\lessons", dirs_exist_ok=True)
        shutil.copytree("C:\\BlueprintLLM\\results\\exams", "D:\\BlueprintLLMBackup\\results\\exams", dirs_exist_ok=True)
        log("Datasets, lessons, and exam results backed up to D:")
    except Exception as e:
        log(f"Secondary backup error: {e}")

def train_dt_v5():
    """Train DT v5 continuation from v4."""
    log("=" * 60)
    log("STARTING DT v5 TRAINING (continuation from v4)")
    log("=" * 60)

    cmd = [
        sys.executable, "scripts/04_train_blueprint_lora.py",
        "--dataset", "datasets/dt_train.jsonl",
        "--output", "models/dt-lora-v5",
        "--resume_from", "models/dt-lora-v4/final",
        "--continuation_lr", "5e-5",
        "--epochs", "2",
        "--system_prompt", "scripts/dt_system_prompt.txt",
    ]

    log(f"Command: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Monitor via heartbeat
    last_report = time.time()
    while proc.poll() is None:
        time.sleep(30)
        now = time.time()
        if now - last_report > 300:  # Report every 5 min
            try:
                hb_age = now - os.path.getmtime("logs/pipeline_heartbeat")
                log(f"  DT v5 training running (heartbeat {hb_age:.0f}s ago)")
            except:
                pass
            last_report = now

    rc = proc.returncode
    if rc == 0:
        adapter = "models/dt-lora-v5/final/adapter_model.safetensors"
        if os.path.exists(adapter):
            log(f"DT v5 training complete: {os.path.getsize(adapter):,} bytes")
            return True
        else:
            log("WARNING: Training exited OK but no adapter found")
            return False
    else:
        log(f"DT v5 training failed with exit code {rc}")
        return False

def run_dt_v5_exam():
    """Run DT v5 exam across all DT lessons."""
    log("=" * 60)
    log("STARTING DT v5 EXAM SUITE")
    log("=" * 60)

    dt_lessons = sorted(glob.glob("lessons/dt_lesson_*.json"))
    log(f"Found {len(dt_lessons)} DT lessons")

    output_dir = "results/dt_exams"
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        sys.executable, "scripts/dt_run_exam.py",
        "--model", "models/dt-lora-v5/final",
        "--output", output_dir,
    ]

    all_summaries = []
    for lesson_path in dt_lessons:
        lesson_name = Path(lesson_path).stem
        log(f"  Examining {lesson_name}...")
        exam_cmd = cmd + ["--lesson", lesson_path]
        proc = subprocess.run(exam_cmd, capture_output=True, text=True, timeout=3600)

        # Find the summary file
        summaries = sorted(glob.glob(f"{output_dir}/*{lesson_name}*summary*.json"))
        if summaries:
            with open(summaries[-1], encoding="utf-8") as f:
                summary = json.load(f)
            log(f"    {lesson_name}: syntax={summary.get('valid_syntax_pct',0)}% sim={summary.get('avg_similarity_score',0)}%")
            all_summaries.append(summary)

    # Save combined DT summary
    if all_summaries:
        total_prompts = sum(s.get("total_prompts", 0) for s in all_summaries)
        total_valid = sum(s.get("valid_syntax", 0) for s in all_summaries)
        total_sim = sum(s.get("avg_similarity_score", 0) * s.get("total_prompts", 0) for s in all_summaries)
        combined = {
            "suite": "dt_v5_exam",
            "model": "models/dt-lora-v5/final",
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "total_lessons": len(all_summaries),
            "total_prompts": total_prompts,
            "total_valid": total_valid,
            "overall_syntax_pct": round(total_valid / max(total_prompts, 1) * 100, 1),
            "overall_similarity": round(total_sim / max(total_prompts, 1), 1),
            "per_lesson": [{
                "lesson_id": s.get("lesson_id", "?"),
                "syntax_pct": s.get("valid_syntax_pct", 0),
                "similarity": s.get("avg_similarity_score", 0),
                "valid": s.get("valid_syntax", 0),
                "total": s.get("total_prompts", 0),
            } for s in all_summaries],
        }
        combined_file = f"{output_dir}/exam_all_dt_summaries_v5_{combined['timestamp']}.json"
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
        log(f"DT v5 RESULTS: {combined['overall_syntax_pct']}% syntax / {combined['overall_similarity']}% similarity")
        return True
    return False

def backup_dt_v5():
    """Backup DT v5 adapter to D:."""
    log("Backing up DT v5 to D:\\BlueprintLLMBackup\\models\\...")
    src = "C:\\BlueprintLLM\\models\\dt-lora-v5"
    dst = "D:\\BlueprintLLMBackup\\models\\dt-lora-v5"
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        src_size = os.path.getsize(os.path.join(src, "final", "adapter_model.safetensors"))
        dst_size = os.path.getsize(os.path.join(dst, "final", "adapter_model.safetensors"))
        if src_size == dst_size:
            log(f"DT v5 backup verified: {src_size:,} bytes match")
        else:
            log(f"WARNING: Size mismatch! C:{src_size} vs D:{dst_size}")
    except Exception as e:
        log(f"DT v5 backup error: {e}")

    # Backup DT exam results
    try:
        shutil.copytree("C:\\BlueprintLLM\\results\\dt_exams", "D:\\BlueprintLLMBackup\\results\\dt_exams", dirs_exist_ok=True)
        log("DT exam results backed up to D:")
    except Exception as e:
        log(f"DT exam backup error: {e}")

def main():
    os.chdir("C:\\BlueprintLLM")
    start = time.time()

    log("=" * 60)
    log("POST-TRAINING PIPELINE: v14 exam → backup → DT v5 → exam → backup")
    log("=" * 60)

    # Step 1: Wait for v14 training
    if not wait_for_v14():
        log("ABORT: v14 training appears to have failed")
        return

    # Step 2: Run v14 exam
    run_v14_exam()

    # Step 3: Backup v14
    backup_v14()

    # Step 4: Train DT v5
    if not train_dt_v5():
        log("WARNING: DT v5 training failed — skipping exam")
    else:
        # Step 5: Run DT v5 exam
        run_dt_v5_exam()

        # Step 6: Backup DT v5
        backup_dt_v5()

    elapsed = time.time() - start
    log(f"\n{'='*60}")
    log(f"PIPELINE COMPLETE in {elapsed/3600:.1f} hours")
    log(f"{'='*60}")

if __name__ == "__main__":
    main()
