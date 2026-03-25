"""
overnight_launch_triple.py
==========================
Pre-launch showcase training: three sequential CONTINUATION jobs.

  JOB 1: DT v4 — continuation from dt-lora-v3, + dt_lesson_04 showcase prompts
  JOB 2: BT v4 — continuation from bt-lora-v3, + bt_lesson_04 showcase prompts
  JOB 3: Blueprint v13 — continuation from blueprint-lora-v12, + lesson_18 showcase prompts

Mode: Continuation (lr=5e-5, 2 epochs, resume from previous adapter)
After each: full exam on ALL lessons in that domain, backup to D:

Stall detection: HEARTBEAT-ONLY (threshold=1800s). See Lessons #52-53.

Usage:
    python scripts/overnight_launch_triple.py
    python scripts/overnight_launch_triple.py --start-from "BT v4"
"""

import os
import sys
import time
import json
import shutil
import subprocess
import datetime
import argparse
import threading
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# Ensure we use the PRO 6000
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# ============================================================
# CONFIG — CONTINUATION MODE
# ============================================================

CONTINUATION_CONFIG = {
    "epochs": 2,
    "learning_rate": 5e-5,
    "batch_size": 1,
    "gradient_accumulation_steps": 4,
    "lora_r": 32,
    "lora_alpha": 64,
    "max_seq_length": 1024,
    "quantization": "8bit",
}

HEARTBEAT_FILE = ROOT / "logs" / "pipeline_heartbeat"
HEARTBEAT_STALL_THRESHOLD = 1800  # 30 minutes
HEARTBEAT_LOG_INTERVAL = 300      # Log every 5 minutes

JOBS = [
    {
        "name": "DT v4",
        "domain": "dt",
        "adapter_name": "dt-lora-v4",
        "resume_from": "models/dt-lora-v3/final",
        "prev_adapter": "dt-lora-v3",
        "dataset": "datasets/dt_train.jsonl",
        "lesson_converter": "scripts/dt_lesson_to_training.py",
        "exam_runner": "scripts/dt_run_exam.py",
        "lessons": [
            "lessons/dt_lesson_01.json",
            "lessons/dt_lesson_02.json",
            "lessons/dt_lesson_03.json",
            "lessons/dt_lesson_04.json",
        ],
    },
    {
        "name": "BT v4",
        "domain": "bt",
        "adapter_name": "bt-lora-v4",
        "resume_from": "models/bt-lora-v3/final",
        "prev_adapter": "bt-lora-v3",
        "dataset": "datasets/bt_train.jsonl",
        "lesson_converter": "scripts/bt_lesson_to_training.py",
        "exam_runner": "scripts/bt_run_exam.py",
        "lessons": [
            "lessons/bt_lesson_01.json",
            "lessons/bt_lesson_02.json",
            "lessons/bt_lesson_03.json",
            "lessons/bt_lesson_04.json",
        ],
    },
    {
        "name": "Blueprint v13",
        "domain": "blueprint",
        "adapter_name": "blueprint-lora-v13",
        "resume_from": "models/blueprint-lora-v12/final",
        "prev_adapter": "blueprint-lora-v12",
        "dataset": "datasets/train.jsonl",
        "lesson_converter": "scripts/13_lesson_to_training.py",
        "exam_runner": "scripts/12_run_exam.py",
        "lessons": [f"lessons/lesson_{i:02d}.json" for i in range(1, 19)],  # L01-L18
    },
]

LOG_FILE = ROOT / "logs" / f"overnight_launch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


# ============================================================
# HELPERS (same as overnight_triple_train.py)
# ============================================================

def log(msg, also_print=True):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    if also_print:
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode("ascii", errors="replace").decode("ascii"), flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_cmd(cmd, timeout=None, label=""):
    log(f"  CMD: {cmd[:200]}{'...' if len(cmd) > 200 else ''}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=str(ROOT),
            env={**os.environ, "CUDA_VISIBLE_DEVICES": "0", "PYTHONIOENCODING": "utf-8"}
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT after {timeout}s: {label}")
        return -1, "", f"Timeout after {timeout}s"
    except Exception as e:
        log(f"  ERROR: {e}")
        return -1, "", str(e)


def run_python(script_args, timeout=None, label=""):
    python = str(ROOT / "venv" / "Scripts" / "python.exe")
    cmd = f'"{python}" {script_args}'
    return run_cmd(cmd, timeout=timeout, label=label)


def kill_zombie_gpu_processes():
    log("  Killing zombie GPU processes...")
    rc, out, err = run_cmd(
        'nvidia-smi --query-compute-apps=pid,name --format=csv,noheader -i 1',
        timeout=30, label="nvidia-smi query"
    )
    if rc != 0:
        log(f"  WARNING: nvidia-smi query failed (rc={rc}): {err.strip()}")
        return False

    my_pid = os.getpid()
    killed = 0
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) >= 2:
            try:
                pid = int(parts[0].strip())
                name = parts[1].strip()
                if pid != my_pid and "python" in name.lower():
                    log(f"  Killing zombie PID {pid} ({name})")
                    os.system(f'taskkill /F /PID {pid} 2>NUL')
                    killed += 1
            except ValueError:
                continue

    if killed > 0:
        log(f"  Killed {killed} zombie process(es). Waiting 5s...")
        time.sleep(5)
    else:
        log("  No zombie processes found.")
    return True


def check_vram_free():
    rc, out, err = run_cmd(
        'nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1',
        timeout=15, label="VRAM check"
    )
    if rc != 0:
        log(f"  WARNING: VRAM check failed: {err.strip()}")
        return True

    try:
        used_mb = int(out.strip())
        used_gb = used_mb / 1024
        log(f"  VRAM used on PRO 6000: {used_gb:.1f} GB")
        if used_gb > 5.0:
            log(f"  ERROR: VRAM > 5GB used! Something is still running.")
            return False
        return True
    except ValueError:
        log(f"  WARNING: Could not parse VRAM: {out.strip()}")
        return True


def backup_adapter_to_d(adapter_name):
    src = ROOT / "models" / adapter_name
    dst = Path(f"D:/BlueprintLLMBackup/models/{adapter_name}")

    if not src.exists():
        log(f"  WARNING: Source {src} does not exist, skipping backup")
        return False

    log(f"  Backing up {adapter_name} to D:...")
    try:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(str(src), str(dst))

        src_adapter = src / "final" / "adapter_model.safetensors"
        dst_adapter = dst / "final" / "adapter_model.safetensors"
        if src_adapter.exists() and dst_adapter.exists():
            src_size = src_adapter.stat().st_size
            dst_size = dst_adapter.stat().st_size
            if src_size == dst_size:
                log(f"  Backup verified: {adapter_name} ({src_size / 1024 / 1024:.0f} MB)")
                return True
            else:
                log(f"  ERROR: Size mismatch! src={src_size} dst={dst_size}")
                return False
        else:
            log(f"  WARNING: adapter_model.safetensors not found in backup")
            return True
    except Exception as e:
        log(f"  ERROR backing up: {e}")
        return False


def backup_results_to_d():
    for subdir in ["results", "datasets", "lessons"]:
        src = ROOT / subdir
        dst = Path(f"D:/BlueprintLLMBackup/{subdir}")
        if src.exists():
            try:
                shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            except Exception as e:
                log(f"  WARNING: Failed to backup {subdir}: {e}")


def count_lines(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except:
        return 0


def get_heartbeat_age():
    try:
        with open(HEARTBEAT_FILE, "r") as f:
            hb_ts = float(f.read().strip())
        return time.time() - hb_ts
    except (FileNotFoundError, ValueError, OSError):
        return None


# ============================================================
# JOB EXECUTION
# ============================================================

def run_preflight(job):
    log(f"\n{'='*60}")
    log(f"PRE-FLIGHT: {job['name']}")
    log(f"{'='*60}")

    # 1. Kill zombies
    kill_zombie_gpu_processes()

    # 2. Check VRAM
    if not check_vram_free():
        kill_zombie_gpu_processes()
        time.sleep(5)
        if not check_vram_free():
            return False

    # 3. Verify previous adapter exists
    resume_path = ROOT / job["resume_from"]
    if not (resume_path / "adapter_model.safetensors").exists():
        log(f"  ERROR: Resume adapter not found at {resume_path}")
        return False
    log(f"  Resume adapter verified: {job['resume_from']}")

    # 4. Backup previous adapter to D:
    backup_adapter_to_d(job["prev_adapter"])

    # 5. Print continuation config
    log(f"\n  CONTINUATION CONFIG:")
    log(f"    resume_from: {job['resume_from']}")
    log(f"    lr: {CONTINUATION_CONFIG['learning_rate']}")
    log(f"    epochs: {CONTINUATION_CONFIG['epochs']}")
    log(f"    batch_size: {CONTINUATION_CONFIG['batch_size']}")
    log(f"    GA: {CONTINUATION_CONFIG['gradient_accumulation_steps']}")
    log(f"    lora_r: {CONTINUATION_CONFIG['lora_r']}")
    log(f"    max_seq_length: {CONTINUATION_CONFIG['max_seq_length']}")

    return True


def prepare_dataset(job):
    log(f"\nDATASET PREP: {job['name']}")

    if job["domain"] in ("dt", "bt"):
        # DT/BT: regenerate from ALL lesson files (new + replay buffer)
        converter = job["lesson_converter"]
        dataset = job["dataset"]

        first = True
        for lesson_path in job["lessons"]:
            if not Path(lesson_path).exists():
                log(f"  WARNING: {lesson_path} does not exist, skipping")
                continue

            flag = "--no-append" if first else ""
            rc, out, err = run_python(
                f'{converter} --lesson {lesson_path} --output {dataset} {flag}',
                timeout=60, label=f"convert {lesson_path}"
            )
            if rc != 0:
                log(f"  ERROR converting {lesson_path}: {err[:500]}")
                return False
            log(f"  {out.strip()}")
            first = False

    else:
        # Blueprint: rebuild with ALL lessons (L01-L18) + base data + synthetic
        converter = job["lesson_converter"]
        dataset = job["dataset"]
        dataset_path = ROOT / dataset

        # Backup current dataset
        backup_path = str(dataset) + ".bak"
        if dataset_path.exists():
            shutil.copy2(str(dataset_path), backup_path)
            log(f"  Backed up current dataset to {backup_path}")

        # Extract non-lesson base entries
        base_entries = []
        if Path(backup_path).exists():
            with open(backup_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        src = entry.get("source", "")
                        if not src.startswith("lesson:") and not src.startswith("correction"):
                            base_entries.append(line)
                    except json.JSONDecodeError:
                        continue
            log(f"  Extracted {len(base_entries)} base (non-lesson) entries")

        # Regenerate ALL lesson entries (L01-L18) fresh
        rc, out, err = run_python(
            f'{converter} --lesson-dir lessons/ --output {dataset} --no-append',
            timeout=120, label="convert all Blueprint lessons"
        )
        if rc != 0:
            log(f"  ERROR converting lessons: {err[:500]}")
            if Path(backup_path).exists():
                shutil.copy2(backup_path, str(dataset_path))
            return False
        log(f"  {out.strip()}")

        # Append base entries
        if base_entries:
            with open(dataset_path, "a", encoding="utf-8") as f:
                f.writelines(base_entries)
            log(f"  Appended {len(base_entries)} base data entries")

        # Append synthetic + auto-translated
        for extra in ["datasets/synthetic_train.jsonl", "datasets/auto_translated.jsonl"]:
            extra_path = ROOT / extra
            if extra_path.exists():
                extra_lines = count_lines(str(extra_path))
                if extra_lines > 0:
                    with open(dataset_path, "a", encoding="utf-8") as dst_f:
                        with open(extra_path, encoding="utf-8") as src_f:
                            dst_f.write(src_f.read())
                    log(f"  Appended {extra_lines} lines from {extra}")

    # Verify
    lines = count_lines(str(ROOT / job["dataset"]))
    log(f"  Final dataset: {job['dataset']} = {lines} training examples")

    if lines == 0:
        log(f"  ERROR: Dataset is empty!")
        return False

    return True


def run_training(job):
    """Run CONTINUATION training with heartbeat-only stall detection."""
    log(f"\nTRAINING: {job['name']}")
    log(f"  Domain: {job['domain']}")
    log(f"  Dataset: {job['dataset']}")
    log(f"  Output: models/{job['adapter_name']}")
    log(f"  Mode: CONTINUATION (lr={CONTINUATION_CONFIG['learning_rate']}, {CONTINUATION_CONFIG['epochs']} epochs)")
    log(f"  Resume from: {job['resume_from']}")

    # Build continuation command
    cmd = (
        f'scripts/04_train_blueprint_lora.py '
        f'--domain {job["domain"]} '
        f'--dataset {job["dataset"]} '
        f'--output models/{job["adapter_name"]} '
        f'--resume_from {job["resume_from"]} '
        f'--continuation_lr {CONTINUATION_CONFIG["learning_rate"]} '
        f'--epochs {CONTINUATION_CONFIG["epochs"]} '
        f'--lora_r {CONTINUATION_CONFIG["lora_r"]} '
        f'--max_seq_length {CONTINUATION_CONFIG["max_seq_length"]} '
        f'--batch_size {CONTINUATION_CONFIG["batch_size"]}'
    )

    log(f"  Training command: python {cmd}")
    log(f"  Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Stall detection: HEARTBEAT-ONLY (threshold={HEARTBEAT_STALL_THRESHOLD}s)")

    start_time = time.time()

    python = str(ROOT / "venv" / "Scripts" / "python.exe")
    full_cmd = f'"{python}" {cmd}'

    train_env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }

    proc = subprocess.Popen(
        full_cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=train_env,
        bufsize=0,
    )

    # Heartbeat monitor thread
    stall_detected = threading.Event()
    monitor_stop = threading.Event()

    def heartbeat_monitor():
        last_log_time = time.time()
        seen_fresh_heartbeat = False

        while not monitor_stop.is_set():
            monitor_stop.wait(30)
            if monitor_stop.is_set():
                break

            hb_age = get_heartbeat_age()
            elapsed = time.time() - start_time
            elapsed_str = f"{elapsed/3600:.1f}h"

            if hb_age is not None:
                hb_timestamp = time.time() - hb_age
                if hb_timestamp > start_time:
                    seen_fresh_heartbeat = True

            if time.time() - last_log_time >= HEARTBEAT_LOG_INTERVAL:
                if not seen_fresh_heartbeat:
                    log(f"  HEARTBEAT: waiting for first fresh heartbeat (elapsed: {elapsed_str}, model loading...)")
                elif hb_age is not None:
                    log(f"  HEARTBEAT: age={hb_age:.0f}s — training alive (elapsed: {elapsed_str})")
                else:
                    log(f"  HEARTBEAT: file not found (elapsed: {elapsed_str})")
                last_log_time = time.time()

            if seen_fresh_heartbeat and hb_age is not None and hb_age > HEARTBEAT_STALL_THRESHOLD:
                log(f"  STALL DETECTED: Heartbeat age={hb_age:.0f}s > threshold={HEARTBEAT_STALL_THRESHOLD}s")
                log(f"  Killing training process (elapsed: {elapsed_str})")
                stall_detected.set()
                proc.kill()
                break

    monitor_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
    monitor_thread.start()

    # Stream stdout
    for raw_line in iter(proc.stdout.readline, b""):
        try:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
        except Exception:
            line = raw_line.decode("latin-1", errors="replace").rstrip()
        if line:
            if any(kw in line for kw in [
                "STEP", "loss", "COMPLETE", "ERROR", "PROGRESS",
                "epoch", "Epoch", "Training", "VRAM", "GPU",
                "adapter", "checkpoint", "eval", "Saving",
                "WARNING", "token_accuracy", "train_runtime",
                "Loading checkpoint", "100%", "Resume",
            ]):
                log(f"  TRAIN: {line}")
            elif "[STEP" in line:
                log(f"  TRAIN: {line}")

    # Cleanup
    monitor_stop.set()
    proc.wait()
    monitor_thread.join(timeout=5)

    elapsed = time.time() - start_time
    elapsed_str = f"{elapsed/3600:.1f}h" if elapsed > 3600 else f"{elapsed/60:.0f}m"

    if stall_detected.is_set():
        log(f"  Training KILLED due to heartbeat stall after {elapsed_str}")
        return False

    log(f"  Training finished. RC={proc.returncode}, Elapsed: {elapsed_str}")

    if proc.returncode != 0:
        log(f"  ERROR: Training failed with return code {proc.returncode}")
        return False

    # Verify adapter was created
    adapter_path = ROOT / "models" / job["adapter_name"] / "final" / "adapter_model.safetensors"
    if not adapter_path.exists():
        log(f"  ERROR: Adapter not found at {adapter_path}")
        return False

    adapter_size = adapter_path.stat().st_size / 1024 / 1024
    log(f"  Adapter created: {adapter_size:.0f} MB")

    return True


def run_exams(job):
    """Run exams on ALL lessons for this domain."""
    log(f"\nEXAMS: {job['name']}")

    adapter_path = f"models/{job['adapter_name']}/final"
    exam_runner = job["exam_runner"]
    results = []

    for lesson_path in job["lessons"]:
        if not Path(lesson_path).exists():
            log(f"  WARNING: {lesson_path} not found, skipping exam")
            continue

        lesson_name = Path(lesson_path).stem
        log(f"  Examining {lesson_name}...")

        rc, out, err = run_python(
            f'{exam_runner} --lesson {lesson_path} --model {adapter_path}',
            timeout=3600,
            label=f"exam {lesson_name}"
        )

        if rc != 0:
            log(f"  WARNING: Exam failed for {lesson_name}: {err[:300]}")
            results.append({"lesson": lesson_name, "status": "FAILED", "error": err[:300]})
            continue

        # Parse results
        import re
        syntax_pct = None
        sim_pct = None
        for line in out.split("\n"):
            if "syntax" in line.lower() and "%" in line:
                try:
                    matches = re.findall(r'(\d+\.?\d*)%', line)
                    if matches and syntax_pct is None:
                        syntax_pct = float(matches[0])
                except:
                    pass
            if "similarity" in line.lower() and "%" in line:
                try:
                    matches = re.findall(r'(\d+\.?\d*)%', line)
                    if matches:
                        sim_pct = float(matches[-1])
                except:
                    pass

        # Try to read summary JSON
        if job["domain"] == "dt":
            results_dir = ROOT / "results" / "dt_exams"
        elif job["domain"] == "bt":
            results_dir = ROOT / "results" / "bt_exams"
        else:
            results_dir = ROOT / "results" / "exams"

        summary_files = sorted(results_dir.glob(f"*{lesson_name}*summary*.json"),
                               key=lambda p: p.stat().st_mtime, reverse=True) if results_dir.exists() else []

        if summary_files:
            try:
                with open(summary_files[0], encoding="utf-8") as f:
                    summary = json.load(f)
                syntax_pct = summary.get("syntax_valid_pct", syntax_pct)
                sim_pct = summary.get("avg_similarity", summary.get("avg_similarity_pct", sim_pct))
                log(f"  {lesson_name}: syntax={syntax_pct}% sim={sim_pct}%")
            except:
                pass

        if syntax_pct is None and sim_pct is None:
            log(f"  {lesson_name} output:\n{out[-500:]}")

        results.append({
            "lesson": lesson_name,
            "status": "OK",
            "syntax_pct": syntax_pct,
            "similarity_pct": sim_pct,
        })

    return results


def print_job_summary(job, exam_results, elapsed_total):
    log(f"\n{'='*60}")
    log(f"SUMMARY: {job['name']}")
    log(f"{'='*60}")
    log(f"  Adapter: models/{job['adapter_name']}/final")
    log(f"  Mode: CONTINUATION from {job['resume_from']}")
    log(f"  Total elapsed: {elapsed_total/60:.0f} minutes ({elapsed_total/3600:.1f} hours)")

    if not exam_results:
        log("  No exam results.")
        return

    log(f"\n  {'Lesson':<25} {'Syntax':>8} {'Similarity':>12} {'Status':>8}")
    log(f"  {'-'*25} {'-'*8} {'-'*12} {'-'*8}")

    total_syntax = 0
    total_sim = 0
    count = 0

    for r in exam_results:
        syn = f"{r.get('syntax_pct', '?')}%" if r.get('syntax_pct') is not None else "?"
        sim = f"{r.get('similarity_pct', '?')}%" if r.get('similarity_pct') is not None else "?"
        status = r.get('status', '?')
        log(f"  {r['lesson']:<25} {syn:>8} {sim:>12} {status:>8}")

        if r.get('syntax_pct') is not None:
            total_syntax += r['syntax_pct']
            count += 1
        if r.get('similarity_pct') is not None:
            total_sim += r['similarity_pct']

    if count > 0:
        avg_syn = total_syntax / count
        avg_sim = total_sim / count
        log(f"\n  Average: syntax={avg_syn:.1f}% similarity={avg_sim:.1f}% ({count} lessons)")

    # Flag showcase lesson results specifically
    showcase_lessons = {
        "DT v4": "dt_lesson_04",
        "BT v4": "bt_lesson_04",
        "Blueprint v13": "lesson_18",
    }
    showcase = showcase_lessons.get(job["name"])
    if showcase:
        for r in exam_results:
            if showcase in r["lesson"]:
                syn = r.get("syntax_pct", "?")
                sim = r.get("similarity_pct", "?")
                log(f"\n  *** SHOWCASE ({showcase}): syntax={syn}% similarity={sim}% ***")
                if isinstance(sim, (int, float)) and sim < 80:
                    log(f"  *** WARNING: Showcase similarity below 80% — may need attention ***")
                break


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Pre-launch showcase continuation training")
    parser.add_argument("--start-from", type=str, default=None,
                        help="Skip jobs before this name (e.g. 'BT v4')")
    args = parser.parse_args()

    active_jobs = JOBS
    if args.start_from:
        found = False
        for i, job in enumerate(JOBS):
            if args.start_from.lower() in job["name"].lower():
                active_jobs = JOBS[i:]
                found = True
                break
        if not found:
            print(f"ERROR: No job matching '{args.start_from}'. Available: {[j['name'] for j in JOBS]}")
            sys.exit(1)

    start_all = time.time()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    job_names = " → ".join(j["name"] for j in active_jobs)
    log("=" * 70)
    log("PRE-LAUNCH SHOWCASE TRAINING")
    log(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Jobs: {job_names}")
    log(f"Mode: CONTINUATION (lr={CONTINUATION_CONFIG['learning_rate']}, {CONTINUATION_CONFIG['epochs']} epochs)")
    log(f"Stall detection: HEARTBEAT-ONLY (threshold={HEARTBEAT_STALL_THRESHOLD}s)")
    log(f"Log: {LOG_FILE}")
    log("=" * 70)

    all_results = {}
    total_jobs = len(active_jobs)

    for job_num, job in enumerate(active_jobs, 1):
        job_start = time.time()

        log(f"\n\n{'#'*70}")
        log(f"JOB {job_num}/{total_jobs}: {job['name']}")
        log(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"{'#'*70}")

        # Pre-flight
        if not run_preflight(job):
            log(f"\nFATAL: Pre-flight failed for {job['name']}. STOPPING ALL JOBS.")
            break

        # Dataset prep
        if not prepare_dataset(job):
            log(f"\nFATAL: Dataset preparation failed for {job['name']}. STOPPING ALL JOBS.")
            break

        # Training
        if not run_training(job):
            log(f"\nFATAL: Training failed for {job['name']}. STOPPING ALL JOBS.")
            break

        # Immediate backup (Rule 22)
        log(f"\nBACKUP: {job['adapter_name']} to D:")
        backup_adapter_to_d(job["adapter_name"])

        # Exams on ALL lessons
        exam_results = run_exams(job)

        # Backup results
        backup_results_to_d()

        # Summary
        job_elapsed = time.time() - job_start
        print_job_summary(job, exam_results, job_elapsed)
        all_results[job["name"]] = {
            "exam_results": exam_results,
            "elapsed_seconds": job_elapsed,
            "adapter": f"models/{job['adapter_name']}/final",
        }

        # Cleanup between jobs
        if job_num < total_jobs:
            log(f"\nCLEANUP between jobs...")
            run_python('-c "import torch; torch.cuda.empty_cache(); print(\'CUDA cache cleared\')"',
                      timeout=30, label="CUDA cleanup")
            time.sleep(5)
            kill_zombie_gpu_processes()
            time.sleep(5)
            if not check_vram_free():
                log("  WARNING: VRAM not fully free. Waiting 30s...")
                time.sleep(30)
                kill_zombie_gpu_processes()
                if not check_vram_free():
                    log("  ERROR: VRAM still not free. Attempting to continue anyway...")

        log(f"\nJOB {job_num}/{total_jobs} COMPLETE: {job['name']} in {job_elapsed/60:.0f} minutes")

    # Final summary
    total_elapsed = time.time() - start_all
    log(f"\n\n{'='*70}")
    log(f"ALL JOBS COMPLETE")
    log(f"Total elapsed: {total_elapsed/3600:.1f} hours ({total_elapsed/60:.0f} minutes)")
    log(f"Finished: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*70}")

    log(f"\nSHOWCASE RESULTS:")
    for job_name, data in all_results.items():
        log(f"\n  {job_name} (adapter: {data['adapter']})")
        log(f"  Elapsed: {data['elapsed_seconds']/60:.0f}m")
        for r in data.get("exam_results", []):
            syn = f"{r.get('syntax_pct', '?')}%"
            sim = f"{r.get('similarity_pct', '?')}%" if r.get('similarity_pct') is not None else "?"
            log(f"    {r['lesson']:<25} syntax={syn:>7} sim={sim:>7} {r['status']}")

    # Save combined results JSON
    results_path = ROOT / "results" / f"overnight_launch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    log(f"\nResults saved to: {results_path}")

    log(f"\n{'='*70}")
    log(f"OVERNIGHT RUN FINISHED")
    log(f"{'='*70}")


if __name__ == "__main__":
    main()
