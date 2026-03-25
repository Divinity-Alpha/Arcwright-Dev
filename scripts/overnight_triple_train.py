"""
overnight_triple_train.py
=========================
Master orchestrator for sequential training jobs:
  JOB 1: BT v3 (full consolidation retrain)
  JOB 2: Blueprint v12 (full consolidation retrain)

Each job: preflight → dataset prep → train → exam all lessons → backup to D: → summary
If any job FAILS, stops immediately and reports.

Stall detection: Uses HEARTBEAT FILE as the SOLE liveness signal.
  - Training writes heartbeat every step (~4-5 min for 70B).
  - If heartbeat age > 1800s (30 min), training is stalled → kill.
  - NEVER kill based on lack of stdout output (Lesson #46).
  - 70B full retrain takes 7-10 hours; empty model dir mid-run is NORMAL (Lesson #47).

Usage:
    python scripts/overnight_triple_train.py
    python scripts/overnight_triple_train.py --start-from "Blueprint v12"
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
# CONFIG
# ============================================================

GOLDEN_CONFIG = {
    "epochs": 3,
    "learning_rate": 0.0002,
    "batch_size": 1,
    "gradient_accumulation_steps": 4,
    "lora_r": 32,
    "lora_alpha": 64,
    "max_seq_length": 1024,
    "quantization": "8bit",
}

HEARTBEAT_FILE = ROOT / "logs" / "pipeline_heartbeat"
HEARTBEAT_STALL_THRESHOLD = 1800  # 30 minutes — ONLY stall signal (Lesson #46)
HEARTBEAT_LOG_INTERVAL = 300      # Log heartbeat age every 5 minutes

JOBS = [
    {
        "name": "BT v3",
        "domain": "bt",
        "adapter_name": "bt-lora-v3",
        "prev_adapter": "bt-lora-v2",
        "dataset": "datasets/bt_train.jsonl",
        "lesson_glob": "bt_lesson_*.json",
        "lesson_converter": "scripts/bt_lesson_to_training.py",
        "exam_runner": "scripts/bt_run_exam.py",
        "lessons": ["lessons/bt_lesson_01.json", "lessons/bt_lesson_02.json", "lessons/bt_lesson_03.json"],
    },
    {
        "name": "Blueprint v12",
        "domain": "blueprint",
        "adapter_name": "blueprint-lora-v12",
        "prev_adapter": "blueprint-lora-v11",
        "dataset": "datasets/train.jsonl",
        "lesson_glob": "lesson_*.json",
        "lesson_converter": "scripts/13_lesson_to_training.py",
        "exam_runner": "scripts/12_run_exam.py",
        "lessons": [f"lessons/lesson_{i:02d}.json" for i in range(1, 18)],
    },
]

LOG_FILE = ROOT / "logs" / f"overnight_triple_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


# ============================================================
# HELPERS
# ============================================================

def log(msg, also_print=True):
    """Log to file and optionally print."""
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
    """Run a command and return (returncode, stdout, stderr)."""
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
    """Run a Python script in the venv."""
    python = str(ROOT / "venv" / "Scripts" / "python.exe")
    cmd = f'"{python}" {script_args}'
    return run_cmd(cmd, timeout=timeout, label=label)


def kill_zombie_gpu_processes():
    """Kill zombie Python processes on GPU 1 (nvidia-smi index for PRO 6000)."""
    log("  Killing zombie GPU processes...")
    # nvidia-smi GPU 1 = PRO 6000 (PyTorch cuda:0)
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
    """Check that VRAM is mostly free on PRO 6000."""
    rc, out, err = run_cmd(
        'nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1',
        timeout=15, label="VRAM check"
    )
    if rc != 0:
        log(f"  WARNING: VRAM check failed: {err.strip()}")
        return True  # Proceed anyway

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
    """Backup a model adapter to D: drive."""
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

        # Verify adapter file size match
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
            log(f"  WARNING: adapter_model.safetensors not found, checking dir...")
            # Might be OK if training hasn't finished yet
            return True
    except Exception as e:
        log(f"  ERROR backing up: {e}")
        return False


def backup_results_to_d():
    """Backup exam results to D:."""
    for subdir in ["results", "datasets", "lessons"]:
        src = ROOT / subdir
        dst = Path(f"D:/BlueprintLLMBackup/{subdir}")
        if src.exists():
            try:
                shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            except Exception as e:
                log(f"  WARNING: Failed to backup {subdir}: {e}")


def verify_golden_config():
    """Verify pipeline_config.json matches golden config."""
    cfg_path = ROOT / "pipeline_config.json"
    with open(cfg_path, encoding="utf-8") as f:
        pcfg = json.load(f)

    checks = {
        "epochs": pcfg.get("training", {}).get("epochs"),
        "learning_rate": pcfg.get("training", {}).get("learning_rate"),
        "batch_size": pcfg.get("training", {}).get("batch_size"),
        "gradient_accumulation_steps": pcfg.get("training", {}).get("gradient_accumulation_steps"),
        "lora_r": pcfg.get("lora", {}).get("lora_r"),
        "lora_alpha": pcfg.get("lora", {}).get("lora_alpha"),
        "max_seq_length": pcfg.get("model", {}).get("max_seq_length"),
        "use_8bit": pcfg.get("quantization", {}).get("use_8bit"),
        "base_model": pcfg.get("model", {}).get("base_model"),
    }

    log("  Golden Config Verification:")
    all_ok = True
    for key, actual in checks.items():
        if key in GOLDEN_CONFIG:
            expected = GOLDEN_CONFIG[key]
            match = "OK" if actual == expected else f"MISMATCH (expected {expected})"
            if actual != expected:
                all_ok = False
            log(f"    {key}: {actual} — {match}")
        else:
            log(f"    {key}: {actual}")

    if not all_ok:
        log("  ERROR: Golden config mismatch! Aborting.")
    return all_ok


def count_lines(filepath):
    """Count lines in a file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except:
        return 0


# ============================================================
# JOB EXECUTION
# ============================================================

def run_preflight(job):
    """Pre-flight checks for a training job."""
    log(f"\n{'='*60}")
    log(f"PRE-FLIGHT: {job['name']}")
    log(f"{'='*60}")

    # 1. Kill zombies
    kill_zombie_gpu_processes()

    # 2. Check VRAM
    if not check_vram_free():
        # Try killing again
        kill_zombie_gpu_processes()
        time.sleep(5)
        if not check_vram_free():
            return False

    # 3. Verify golden config
    if not verify_golden_config():
        return False

    # 4. Backup previous adapter
    if job["prev_adapter"]:
        prev_path = ROOT / "models" / job["prev_adapter"]
        if prev_path.exists():
            backup_adapter_to_d(job["prev_adapter"])
        else:
            log(f"  Previous adapter {job['prev_adapter']} not found, skipping backup")

    return True


def prepare_dataset(job):
    """Regenerate training dataset from ALL lessons."""
    log(f"\nDATASET PREP: {job['name']}")

    if job["domain"] in ("dt", "bt"):
        # DT/BT: regenerate from all lesson files using domain converter
        converter = job["lesson_converter"]
        dataset = job["dataset"]

        # First pass: overwrite (--no-append)
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
        # Blueprint: full dataset rebuild
        # 1. Extract base data (non-lesson entries) from current dataset
        # 2. Regenerate all lesson entries from L01-L17
        # 3. Combine: base + lessons + synthetic + auto_translated
        converter = job["lesson_converter"]
        dataset = job["dataset"]
        dataset_path = ROOT / dataset

        # Backup current dataset
        backup_path = str(dataset) + ".bak"
        if dataset_path.exists():
            shutil.copy2(str(dataset_path), backup_path)
            log(f"  Backed up current dataset to {backup_path}")

        # Extract non-lesson "base" entries (original curated data)
        base_entries = []
        if Path(backup_path).exists():
            with open(backup_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        src = entry.get("source", "")
                        # Keep entries that are NOT from lessons or corrections
                        if not src.startswith("lesson:") and not src.startswith("correction"):
                            base_entries.append(line)
                    except json.JSONDecodeError:
                        continue
            log(f"  Extracted {len(base_entries)} base (non-lesson) entries")

        # Regenerate all lesson entries from L01-L17 (fresh)
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

        # Append synthetic + auto-translated data
        for extra in ["datasets/synthetic_train.jsonl", "datasets/auto_translated.jsonl"]:
            extra_path = ROOT / extra
            if extra_path.exists():
                extra_lines = count_lines(str(extra_path))
                if extra_lines > 0:
                    with open(dataset_path, "a", encoding="utf-8") as dst:
                        with open(extra_path, encoding="utf-8") as src:
                            dst.write(src.read())
                    log(f"  Appended {extra_lines} lines from {extra}")

    # Verify dataset
    lines = count_lines(str(ROOT / job["dataset"]))
    log(f"  Final dataset: {job['dataset']} = {lines} training examples")

    if lines == 0:
        log(f"  ERROR: Dataset is empty!")
        return False

    return True


def get_heartbeat_age():
    """Read the heartbeat file and return age in seconds. Returns None if unreadable."""
    try:
        with open(HEARTBEAT_FILE, "r") as f:
            hb_ts = float(f.read().strip())
        return time.time() - hb_ts
    except (FileNotFoundError, ValueError, OSError):
        return None


def run_training(job):
    """Run the actual training.

    Stall detection: HEARTBEAT-ONLY (Lesson #46).
      - The training script writes a heartbeat file every step_begin/step_end.
      - Each 70B gradient step takes ~4.5 min, so heartbeat updates every ~4.5 min.
      - If heartbeat age > 1800s (30 min), training is stalled → kill.
      - NEVER kill based on lack of stdout — readline() blocks on \\r progress bars.
      - 70B full retrain takes 7-10 hours; empty model dir mid-run is normal (Lesson #47).
    """
    log(f"\nTRAINING: {job['name']}")
    log(f"  Domain: {job['domain']}")
    log(f"  Dataset: {job['dataset']}")
    log(f"  Output: models/{job['adapter_name']}")
    log(f"  Mode: FULL (golden config, 3 epochs)")

    # Build command
    cmd = (
        f'scripts/04_train_blueprint_lora.py '
        f'--domain {job["domain"]} '
        f'--dataset {job["dataset"]} '
        f'--output models/{job["adapter_name"]} '
        f'--epochs 3 '
        f'--lr 0.0002 '
        f'--lora_r 32 '
        f'--max_seq_length 1024 '
        f'--batch_size 1'
    )

    log(f"  Training command: python {cmd}")
    log(f"  Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Stall detection: HEARTBEAT-ONLY (threshold={HEARTBEAT_STALL_THRESHOLD}s)")
    log(f"  NOTE: 70B full retrain takes 7-10h. No stdout for hours is NORMAL.")

    start_time = time.time()

    # Run training with PYTHONUNBUFFERED=1 (Fix 2: forces immediate stdout flush)
    python = str(ROOT / "venv" / "Scripts" / "python.exe")
    full_cmd = f'"{python}" {cmd}'

    train_env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",  # Fix 2: flush stdout/stderr immediately
    }

    proc = subprocess.Popen(
        full_cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=train_env,
        bufsize=0,  # Unbuffered at OS level too
    )

    # --- Heartbeat monitor thread (Fix 1) ---
    # Runs alongside stdout reading. Checks heartbeat age periodically.
    # If heartbeat exceeds threshold, kills the process.
    stall_detected = threading.Event()
    monitor_stop = threading.Event()

    def heartbeat_monitor():
        """Monitor heartbeat file in a background thread.
        ONLY signal that determines if training is alive.
        Never kill based on stdout silence.

        CRITICAL: Ignore heartbeats written BEFORE this training started.
        The heartbeat file may be stale from a previous (killed) run.
        Only start stall-checking once a heartbeat has been written AFTER start_time.
        """
        last_log_time = time.time()
        seen_fresh_heartbeat = False  # True once a post-start_time heartbeat appears

        while not monitor_stop.is_set():
            monitor_stop.wait(30)  # Check every 30 seconds
            if monitor_stop.is_set():
                break

            hb_age = get_heartbeat_age()
            elapsed = time.time() - start_time
            elapsed_str = f"{elapsed/3600:.1f}h"

            # Check if this heartbeat was written AFTER training started
            if hb_age is not None:
                # Heartbeat timestamp = now - hb_age
                hb_timestamp = time.time() - hb_age
                if hb_timestamp > start_time:
                    seen_fresh_heartbeat = True

            # Log heartbeat status every HEARTBEAT_LOG_INTERVAL seconds
            if time.time() - last_log_time >= HEARTBEAT_LOG_INTERVAL:
                if not seen_fresh_heartbeat:
                    log(f"  HEARTBEAT: waiting for first fresh heartbeat (elapsed: {elapsed_str}, model loading...)")
                elif hb_age is not None:
                    log(f"  HEARTBEAT: age={hb_age:.0f}s — training alive (elapsed: {elapsed_str})")
                else:
                    log(f"  HEARTBEAT: file not found (elapsed: {elapsed_str})")
                last_log_time = time.time()

            # Stall detection: ONLY check if we've seen at least one fresh heartbeat
            # This prevents killing training during model loading (before first heartbeat)
            if seen_fresh_heartbeat and hb_age is not None and hb_age > HEARTBEAT_STALL_THRESHOLD:
                log(f"  STALL DETECTED: Heartbeat age={hb_age:.0f}s > threshold={HEARTBEAT_STALL_THRESHOLD}s")
                log(f"  Killing training process (elapsed: {elapsed_str})")
                stall_detected.set()
                proc.kill()
                break

    monitor_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
    monitor_thread.start()

    # --- Stream stdout (non-blocking with heartbeat monitor running) ---
    for raw_line in iter(proc.stdout.readline, b""):
        try:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
        except Exception:
            line = raw_line.decode("latin-1", errors="replace").rstrip()
        if line:
            # Log important lines, skip noisy progress bar fragments
            if any(kw in line for kw in [
                "STEP", "loss", "COMPLETE", "ERROR", "PROGRESS",
                "epoch", "Epoch", "Training", "VRAM", "GPU",
                "adapter", "checkpoint", "eval", "Saving",
                "WARNING", "token_accuracy", "train_runtime",
                "Loading checkpoint", "100%",
            ]):
                log(f"  TRAIN: {line}")
            elif "[STEP" in line:
                log(f"  TRAIN: {line}")

    # --- Cleanup ---
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
            timeout=3600,  # 1 hour max per lesson exam
            label=f"exam {lesson_name}"
        )

        if rc != 0:
            log(f"  WARNING: Exam failed for {lesson_name}: {err[:300]}")
            results.append({"lesson": lesson_name, "status": "FAILED", "error": err[:300]})
            continue

        # Parse results from output
        syntax_pct = None
        sim_pct = None
        for line in out.split("\n"):
            if "syntax" in line.lower() and "%" in line:
                try:
                    # Look for patterns like "95.0%" or "100.0%"
                    import re
                    matches = re.findall(r'(\d+\.?\d*)%', line)
                    if matches and syntax_pct is None:
                        syntax_pct = float(matches[0])
                except:
                    pass
            if "similarity" in line.lower() and "%" in line:
                try:
                    import re
                    matches = re.findall(r'(\d+\.?\d*)%', line)
                    if matches:
                        sim_pct = float(matches[-1])
                except:
                    pass

        # Also try to read the summary JSON
        # Find the most recent summary file for this lesson
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
            # Just log the raw output
            log(f"  {lesson_name} output:\n{out[-500:]}")

        results.append({
            "lesson": lesson_name,
            "status": "OK",
            "syntax_pct": syntax_pct,
            "similarity_pct": sim_pct,
        })

    return results


def print_job_summary(job, exam_results, elapsed_total):
    """Print a formatted summary for a completed job."""
    log(f"\n{'='*60}")
    log(f"SUMMARY: {job['name']}")
    log(f"{'='*60}")
    log(f"  Adapter: models/{job['adapter_name']}/final")
    log(f"  Total elapsed: {elapsed_total/60:.0f} minutes ({elapsed_total/3600:.1f} hours)")

    if not exam_results:
        log("  No exam results.")
        return

    # Per-lesson breakdown
    log(f"\n  {'Lesson':<25} {'Syntax':>8} {'Similarity':>12} {'Status':>8}")
    log(f"  {'-'*25} {'-'*8} {'-'*12} {'-'*8}")

    total_syntax = 0
    total_sim = 0
    count = 0
    below_60 = []

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
            if r['similarity_pct'] < 60:
                below_60.append(r['lesson'])

    if count > 0:
        avg_syn = total_syntax / count
        avg_sim = total_sim / count
        log(f"\n  Average: syntax={avg_syn:.1f}% similarity={avg_sim:.1f}% ({count} lessons)")

    if below_60:
        log(f"\n  BELOW 60% SIMILARITY: {', '.join(below_60)}")
        log(f"  → Continuation training recommended for these categories")
    else:
        log(f"\n  All lessons above 60% similarity threshold.")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Overnight sequential training")
    parser.add_argument("--start-from", type=str, default=None,
                        help="Skip jobs before this name (e.g. 'BT v3')")
    args = parser.parse_args()

    # Filter jobs if --start-from specified
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

    job_names = " -> ".join(j["name"] for j in active_jobs)
    log("=" * 70)
    log("OVERNIGHT TRAINING RUN")
    log(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Jobs: {job_names}")
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

        # Exams
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

        # Kill GPU processes and verify VRAM before next job
        if job_num < total_jobs:
            log(f"\nCLEANUP between jobs...")
            # Force garbage collection and CUDA cleanup
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

    # Overall summary
    below_60_all = []
    for job_name, data in all_results.items():
        log(f"\n{job_name}:")
        for r in data.get("exam_results", []):
            sim = r.get("similarity_pct")
            if sim is not None and sim < 60:
                below_60_all.append(f"{job_name}/{r['lesson']}")
            syn = f"{r.get('syntax_pct', '?')}%"
            sim_str = f"{sim}%" if sim is not None else "?"
            log(f"  {r['lesson']}: syntax={syn} sim={sim_str}")

    if below_60_all:
        log(f"\nCATEGORIES BELOW 60% (need continuation training):")
        for cat in below_60_all:
            log(f"  - {cat}")
    else:
        log(f"\nAll categories above 60%. No immediate continuation needed.")

    # Save summary JSON
    summary_path = ROOT / "results" / f"overnight_triple_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "started": start_all,
            "total_elapsed_seconds": total_elapsed,
            "jobs": all_results,
            "below_60_pct": below_60_all,
        }, f, indent=2)
    log(f"\nResults saved to: {summary_path}")
    log(f"Full log: {LOG_FILE}")


if __name__ == "__main__":
    main()
