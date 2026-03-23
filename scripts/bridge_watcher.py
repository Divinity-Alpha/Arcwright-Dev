#!/usr/bin/env python3
"""
Bridge Watcher — monitors Downloads folder for instruction files from Claude.ai.

Flow:
1. Claude.ai creates a JSON file artifact → Scott downloads it (or it auto-downloads)
2. This script detects the file in Downloads → copies to .claude-bridge/instructions/
3. claude_bridge.py --check picks it up → Claude Code executes
4. Result saved to .claude-bridge/results/ → git pushed automatically

Usage:
    python scripts/bridge_watcher.py                  # Watch ~/Downloads (default)
    python scripts/bridge_watcher.py --dir C:\custom  # Watch custom folder
    python scripts/bridge_watcher.py --once            # Single check, no loop
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_DIR = PROJECT_ROOT / ".claude-bridge"
INSTRUCTIONS_DIR = BRIDGE_DIR / "instructions"
RESULTS_DIR = BRIDGE_DIR / "results"

# Track processed files to avoid re-copying
PROCESSED_FILE = BRIDGE_DIR / ".processed_downloads"


def load_processed():
    if PROCESSED_FILE.exists():
        return set(PROCESSED_FILE.read_text(encoding="utf-8").strip().splitlines())
    return set()


def save_processed(processed: set):
    PROCESSED_FILE.write_text("\n".join(sorted(processed)), encoding="utf-8")


def is_bridge_instruction(filepath: str) -> dict | None:
    """Check if a file is a valid bridge instruction JSON."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Must have id and instructions fields
        if isinstance(data, dict) and "id" in data and "instructions" in data:
            return data
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass
    return None


def find_instruction_files(watch_dir: str) -> list[tuple[str, dict]]:
    """Find bridge instruction files in the watch directory."""
    found = []
    patterns = [
        os.path.join(watch_dir, "*bridge*.json"),
        os.path.join(watch_dir, "*instruction*.json"),
        os.path.join(watch_dir, "0*.json"),  # 001_task.json, 002_fix.json, etc.
    ]
    seen_paths = set()
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            if filepath in seen_paths:
                continue
            seen_paths.add(filepath)
            data = is_bridge_instruction(filepath)
            if data:
                found.append((filepath, data))
    return found


def copy_to_bridge(filepath: str, data: dict) -> str | None:
    """Copy an instruction file to the bridge instructions directory."""
    INSTRUCTIONS_DIR.mkdir(parents=True, exist_ok=True)
    dest_name = os.path.basename(filepath)
    # Ensure filename starts with the instruction ID
    inst_id = data.get("id", "unknown")
    if not dest_name.startswith(inst_id):
        dest_name = f"{inst_id}_{dest_name}"
    dest = INSTRUCTIONS_DIR / dest_name

    # Don't overwrite existing instructions
    if dest.exists():
        existing = json.loads(dest.read_text(encoding="utf-8"))
        if existing.get("status") == "completed":
            return None  # Already processed
        if existing.get("id") == data.get("id"):
            return None  # Same instruction

    shutil.copy2(filepath, dest)
    return str(dest)


def git_push_results():
    """Commit and push results to GitHub."""
    os.chdir(PROJECT_ROOT)
    try:
        # Check if there are results to push
        result = subprocess.run(
            ["git", "status", "--porcelain", ".claude-bridge/results/"],
            capture_output=True, text=True, timeout=10
        )
        if not result.stdout.strip():
            return False  # Nothing to push

        # Stage results
        subprocess.run(
            ["git", "add", ".claude-bridge/results/"],
            capture_output=True, timeout=10
        )

        # Find which instruction IDs have new results
        result_files = list(RESULTS_DIR.glob("*_result.json"))
        ids = [f.stem.replace("_result", "") for f in result_files]
        ids_str = ", ".join(ids[-3:])  # Last 3

        subprocess.run(
            ["git", "commit", "-m", f"Bridge results: {ids_str}"],
            capture_output=True, timeout=10
        )

        push_result = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, timeout=30
        )
        if push_result.returncode == 0:
            print(f"  Git pushed results for: {ids_str}")
            return True
        else:
            print(f"  Git push failed: {push_result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print("  Git operation timed out")
        return False
    except Exception as e:
        print(f"  Git error: {e}")
        return False


def check_for_new_results():
    """Check if there are completed results to push."""
    if not RESULTS_DIR.exists():
        return
    result_files = list(RESULTS_DIR.glob("*_result.json"))
    if result_files:
        git_push_results()


def watch_loop(watch_dir: str, interval: float = 5.0):
    """Main watch loop."""
    INSTRUCTIONS_DIR.mkdir(parents=True, exist_ok=True)
    processed = load_processed()

    print(f"Bridge Watcher: Monitoring {watch_dir}")
    print(f"  Instructions → {INSTRUCTIONS_DIR}")
    print(f"  Results → {RESULTS_DIR}")
    print(f"  Already processed: {len(processed)} file(s)")
    print(f"  Polling every {interval}s (Ctrl+C to stop)")
    print()

    try:
        while True:
            # Check Downloads for new instruction files
            found = find_instruction_files(watch_dir)
            for filepath, data in found:
                if filepath in processed:
                    continue

                inst_id = data.get("id", "?")
                title = data.get("title", "Untitled")
                print(f"  Found: [{inst_id}] {title}")

                dest = copy_to_bridge(filepath, data)
                if dest:
                    print(f"  Copied to bridge: {dest}")
                    processed.add(filepath)
                    save_processed(processed)
                else:
                    print(f"  Skipped (already in bridge)")
                    processed.add(filepath)
                    save_processed(processed)

            # Check for completed results to push
            check_for_new_results()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nWatcher stopped.")


def single_check(watch_dir: str):
    """Single check — no loop."""
    processed = load_processed()
    found = find_instruction_files(watch_dir)
    new_count = 0
    for filepath, data in found:
        if filepath in processed:
            continue
        inst_id = data.get("id", "?")
        title = data.get("title", "Untitled")
        dest = copy_to_bridge(filepath, data)
        if dest:
            print(f"  Copied: [{inst_id}] {title} -> {dest}")
            processed.add(filepath)
            new_count += 1
        else:
            processed.add(filepath)

    save_processed(processed)

    if new_count == 0:
        print("No new instruction files found.")
    else:
        print(f"{new_count} new instruction(s) copied to bridge.")

    check_for_new_results()


def main():
    default_downloads = str(Path.home() / "Downloads")

    parser = argparse.ArgumentParser(description="Bridge Watcher — monitors Downloads for instruction files")
    parser.add_argument("--dir", default=default_downloads, help=f"Directory to watch (default: {default_downloads})")
    parser.add_argument("--once", action="store_true", help="Single check, no loop")
    parser.add_argument("--interval", type=float, default=5.0, help="Poll interval in seconds (default: 5)")

    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Watch directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)

    if args.once:
        single_check(args.dir)
    else:
        watch_loop(args.dir, args.interval)


if __name__ == "__main__":
    main()
