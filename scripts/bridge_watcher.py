#!/usr/bin/env python3
"""
Bridge Watcher -- monitors Downloads for instruction files, routes to project folders.

Uses the centralized bridge repo at C:\\Projects\\claude-bridge\\.
Routes files to the correct project based on filename or content.

Usage:
    python scripts/bridge_watcher.py                                # Watch ~/Downloads
    python scripts/bridge_watcher.py --project arcwright            # Force project
    python scripts/bridge_watcher.py --dir C:\\custom --once         # Single check
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

BRIDGE_ROOT = Path(r"C:\Projects\claude-bridge")
DEFAULT_PROJECT = "bore-and-stroke"

PROCESSED_FILE = BRIDGE_ROOT / ".processed_downloads"

# Filename patterns that map to projects
PROJECT_PATTERNS = {
    "bore": "bore-and-stroke",
    "stroke": "bore-and-stroke",
    "station": "bore-and-stroke",
    "hud": "bore-and-stroke",
    "engine": "bore-and-stroke",
    "arcwright": "arcwright",
    "blueprint": "arcwright",
    "plugin": "arcwright",
    "training": "arcwright",
    "lora": "arcwright",
}


def load_processed():
    if PROCESSED_FILE.exists():
        return set(PROCESSED_FILE.read_text(encoding="utf-8").strip().splitlines())
    return set()


def save_processed(processed: set):
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text("\n".join(sorted(processed)), encoding="utf-8")


def detect_project(filepath: str, data: dict, forced_project: str = None) -> str:
    """Determine which project an instruction belongs to."""
    if forced_project:
        return forced_project

    # Check explicit project field in JSON
    if data.get("project"):
        return data["project"]

    # Check filename for project hints
    basename = os.path.basename(filepath).lower()
    for keyword, project in PROJECT_PATTERNS.items():
        if keyword in basename:
            return project

    # Check instruction text for hints
    instructions = data.get("instructions", "").lower()
    title = data.get("title", "").lower()
    combined = f"{title} {instructions}"
    for keyword, project in PROJECT_PATTERNS.items():
        if keyword in combined:
            return project

    return DEFAULT_PROJECT


def is_bridge_instruction(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "id" in data and "instructions" in data:
            return data
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass
    return None


def find_instruction_files(watch_dir: str):
    found = []
    patterns = [
        os.path.join(watch_dir, "*bridge*.json"),
        os.path.join(watch_dir, "*instruction*.json"),
        os.path.join(watch_dir, "0*.json"),
    ]
    seen = set()
    for pattern in patterns:
        for fp in glob.glob(pattern):
            if fp not in seen:
                seen.add(fp)
                data = is_bridge_instruction(fp)
                if data:
                    found.append((fp, data))
    return found


def copy_to_bridge(filepath: str, data: dict, project: str) -> str | None:
    inst_dir = BRIDGE_ROOT / "instructions" / project
    inst_dir.mkdir(parents=True, exist_ok=True)

    dest_name = os.path.basename(filepath)
    inst_id = data.get("id", "unknown")
    if not dest_name.startswith(inst_id):
        dest_name = f"{inst_id}_{dest_name}"
    dest = inst_dir / dest_name

    if dest.exists():
        existing = json.loads(dest.read_text(encoding="utf-8"))
        if existing.get("status") == "completed" or existing.get("id") == data.get("id"):
            return None

    shutil.copy2(filepath, dest)
    return str(dest)


def git_push():
    os.chdir(BRIDGE_ROOT)
    try:
        subprocess.run(["git", "add", "-A"], capture_output=True, timeout=10)
        st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10)
        if not st.stdout.strip():
            return
        subprocess.run(["git", "commit", "-m", "Bridge: new instructions detected"],
                       capture_output=True, timeout=10)
        push = subprocess.run(["git", "push"], capture_output=True, text=True, timeout=30)
        if push.returncode == 0:
            print("  Pushed to claude-bridge repo")
        else:
            print(f"  Push failed: {push.stderr[:150]}")
    except Exception as e:
        print(f"  Git error: {e}")


def watch_loop(watch_dir: str, forced_project: str, interval: float):
    processed = load_processed()
    print(f"Bridge Watcher: monitoring {watch_dir}")
    print(f"  Bridge repo: {BRIDGE_ROOT}")
    print(f"  Default project: {forced_project or DEFAULT_PROJECT}")
    print(f"  Polling every {interval}s (Ctrl+C to stop)")
    print()

    try:
        while True:
            found = find_instruction_files(watch_dir)
            new_count = 0
            for fp, data in found:
                if fp in processed:
                    continue
                project = detect_project(fp, data, forced_project)
                inst_id = data.get("id", "?")
                title = data.get("title", "Untitled")

                dest = copy_to_bridge(fp, data, project)
                if dest:
                    print(f"  [{project}] {inst_id}: {title} -> {dest}")
                    new_count += 1
                processed.add(fp)
                save_processed(processed)

            if new_count > 0:
                git_push()

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def single_check(watch_dir: str, forced_project: str):
    processed = load_processed()
    found = find_instruction_files(watch_dir)
    new_count = 0
    for fp, data in found:
        if fp in processed:
            continue
        project = detect_project(fp, data, forced_project)
        inst_id = data.get("id", "?")
        title = data.get("title", "Untitled")

        dest = copy_to_bridge(fp, data, project)
        if dest:
            print(f"  [{project}] {inst_id}: {title} -> {dest}")
            new_count += 1
        processed.add(fp)

    save_processed(processed)
    if new_count == 0:
        print("No new instruction files found.")
    else:
        print(f"{new_count} new instruction(s) copied.")
        git_push()


def main():
    default_dl = str(Path.home() / "Downloads")
    p = argparse.ArgumentParser(description="Bridge Watcher -- monitors Downloads for instructions")
    p.add_argument("--dir", default=default_dl, help=f"Watch directory (default: {default_dl})")
    p.add_argument("--project", default=None, help="Force project (default: auto-detect)")
    p.add_argument("--once", action="store_true", help="Single check")
    p.add_argument("--interval", type=float, default=5.0, help="Poll interval (default: 5s)")

    args = p.parse_args()
    if not os.path.isdir(args.dir):
        print(f"Directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)

    if args.once:
        single_check(args.dir, args.project)
    else:
        watch_loop(args.dir, args.project, args.interval)


if __name__ == "__main__":
    main()
