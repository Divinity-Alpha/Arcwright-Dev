"""
pre_training_check.py
---------------------
Runs BEFORE every training job to ensure the PRO 6000 (training GPU) is clear.

1. Checks if UE Editor is on the PRO 6000 (warns if so — should be on 5070 Ti)
2. Kills zombie Python processes on the training GPU
3. Checks VRAM on the training GPU (nvidia-smi GPU 1 = PRO 6000)
4. Reports free VRAM and warns if <95% available
5. Returns exit code 1 if VRAM isn't clear enough

Note: UE Editor should run on the 5070 Ti (D3D12 adapter 0) via
r.GraphicsAdapter=0 in DefaultEngine.ini. It no longer needs to be closed
for training. This script only verifies the PRO 6000 is clear.

Usage:
    python scripts/pre_training_check.py
    # Returns 0 if GPU is clear, 1 if not
"""

import json
import os
import socket
import subprocess
import sys
import time


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [PRE-TRAIN] {msg}")


def kill_process(name: str):
    """Kill a process by image name. Returns True if killed."""
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", name],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def check_process_running(name: str) -> bool:
    """Check if a process is running by name."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}"],
            capture_output=True, text=True, timeout=10
        )
        return name.lower() in result.stdout.lower()
    except Exception:
        return False


def get_gpu_vram(gpu_index: int = 1):
    """Get VRAM usage for a GPU (nvidia-smi index). Returns (used_mb, total_mb) or None."""
    try:
        result = subprocess.run(
            ["nvidia-smi", f"--query-gpu=memory.used,memory.total",
             "--format=csv,noheader,nounits", f"-i", str(gpu_index)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            return int(parts[0].strip()), int(parts[1].strip())
    except Exception:
        pass
    return None


def get_gpu_processes(gpu_index: int = 1):
    """Get list of processes using a GPU."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader", f"-i", str(gpu_index)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            processes = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    processes.append({"pid": parts[0], "name": parts[1],
                                      "memory": parts[2] if len(parts) > 2 else "N/A"})
            return processes
    except Exception:
        pass
    return []


def main():
    log("Starting pre-training GPU check (PRO 6000 = nvidia-smi GPU 1)")

    # --- Step 1: Check if UE is on the wrong GPU ---
    # nvidia-smi GPU 1 = PRO 6000. UE should be on GPU 0 (5070 Ti).
    pro6000_procs = get_gpu_processes(gpu_index=1)
    ue_on_training_gpu = any("unreal" in p["name"].lower() for p in pro6000_procs)
    if ue_on_training_gpu:
        log("WARNING: UnrealEditor.exe is using the PRO 6000 (training GPU)!")
        log("UE should run on the 5070 Ti. Add -graphicsadapter=0 to launch args")
        log("and r.GraphicsAdapter=0 to DefaultEngine.ini.")
        log("Training with UE on the same GPU causes 245x slowdown.")

    # --- Step 2: Kill Epic helper processes on training GPU ---
    epic_processes = [
        "EpicWebHelper.exe",
        "CrashReportClient.exe",
    ]
    for proc in epic_processes:
        # Only kill if they're actually using the training GPU
        for gp in pro6000_procs:
            if proc.lower() in gp["name"].lower():
                log(f"Killing {proc} (on training GPU)")
                kill_process(proc)

    # --- Step 3: Kill zombie Python processes on training GPU ---
    gpu_procs = get_gpu_processes(gpu_index=1)
    current_pid = str(os.getpid())
    killed_any = False
    for proc in gpu_procs:
        if "python" in proc["name"].lower() and proc["pid"] != current_pid:
            log(f"Killing zombie GPU process: PID {proc['pid']} ({proc['name']}, {proc['memory']})")
            try:
                subprocess.run(["taskkill", "/F", "/PID", proc["pid"]],
                               capture_output=True, timeout=10)
                killed_any = True
            except Exception:
                pass
    if killed_any:
        time.sleep(5)

    # --- Step 4: Check VRAM ---
    vram = get_gpu_vram(gpu_index=1)
    if vram is None:
        log("ERROR: Could not query GPU VRAM via nvidia-smi")
        return 1

    used_mb, total_mb = vram
    free_mb = total_mb - used_mb
    free_gb = free_mb / 1024
    total_gb = total_mb / 1024
    free_pct = (free_mb / total_mb) * 100

    log(f"PRO 6000 VRAM: {used_mb} MiB used / {total_mb} MiB total")
    log(f"GPU clear: {free_gb:.1f} GB free out of {total_gb:.1f} GB total")

    # Warn if less than 95% is available
    if free_pct < 95:
        remaining_procs = get_gpu_processes(gpu_index=1)
        if remaining_procs:
            log(f"WARNING: PRO 6000 still has {len(remaining_procs)} process(es):")
            for p in remaining_procs:
                log(f"  PID {p['pid']}: {p['name']} ({p['memory']})")
        log(f"WARNING: Only {free_pct:.1f}% VRAM free ({free_gb:.1f} GB)")
        log(f"Training requires >95% free VRAM to avoid thrashing.")
        log(f"VRAM thrashing slows training from 18s/step to 4000+s/step (245x slower)")
        log("FAIL: GPU not clear enough for training")
        return 1

    log(f"PASS: {free_pct:.1f}% VRAM free — safe to train")
    return 0


if __name__ == "__main__":
    sys.exit(main())
