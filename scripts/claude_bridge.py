#!/usr/bin/env python3
"""
Claude Bridge -- File-based message queue between Claude.ai and Claude Code.

Uses the centralized bridge repo at C:\\Projects\\claude-bridge\\.
Supports multiple projects via --project flag.

Usage:
    python scripts/claude_bridge.py --check                          # Check default project
    python scripts/claude_bridge.py --check --project bore-and-stroke
    python scripts/claude_bridge.py --watch --project arcwright
    python scripts/claude_bridge.py --status
    python scripts/claude_bridge.py --complete 002 --summary "Done"
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BRIDGE_ROOT = Path(r"C:\Projects\claude-bridge")
DEFAULT_PROJECT = "bore-and-stroke"


def get_dirs(project: str):
    return (
        BRIDGE_ROOT / "instructions" / project,
        BRIDGE_ROOT / "results" / project,
        BRIDGE_ROOT / "status" / f"{project}.json",
        BRIDGE_ROOT / "conversation.log",
    )


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_msg(log_file: Path, msg: str):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {msg}\n")


def update_status(status_file: Path, state: str, message: str, project: str, last_id: str = None):
    pending = get_pending(status_file.parent.parent / "instructions" / project)
    data = {
        "project": project,
        "state": state,
        "message": message,
        "timestamp": now_iso(),
        "last_instruction": last_id,
        "pending_count": len(pending),
        "pending_ids": [d.get("id", "?") for _, d in pending],
    }
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_pending(inst_dir: Path):
    pending = []
    if not inst_dir.exists():
        return pending
    for f in sorted(inst_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status", "pending") == "pending":
                pending.append((f, data))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Warning: {f.name}: {e}", file=sys.stderr)
    return pending


def get_all(inst_dir: Path):
    items = []
    if not inst_dir.exists():
        return items
    for f in sorted(inst_dir.glob("*.json")):
        try:
            items.append((f, json.loads(f.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, OSError):
            pass
    return items


def git_push_results(project: str):
    """Commit and push results in the bridge repo."""
    os.chdir(BRIDGE_ROOT)
    try:
        subprocess.run(["git", "add", f"results/{project}/", f"status/{project}.json",
                        "instructions/", "conversation.log"],
                       capture_output=True, timeout=10)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        if not result.stdout.strip():
            return
        subprocess.run(
            ["git", "commit", "-m", f"Bridge: {project} result update"],
            capture_output=True, timeout=10
        )
        push = subprocess.run(["git", "push"], capture_output=True, text=True, timeout=30)
        if push.returncode == 0:
            print(f"  Pushed results to claude-bridge repo")
        else:
            print(f"  Push failed: {push.stderr[:150]}")
    except Exception as e:
        print(f"  Git error: {e}")


def cmd_check(project: str):
    inst_dir, res_dir, status_file, log_file = get_dirs(project)
    inst_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    pending = get_pending(inst_dir)
    if not pending:
        print(f"Claude Bridge [{project}]: No pending instructions.")
        update_status(status_file, "idle", "No pending instructions", project)
        return

    print(f"Claude Bridge [{project}]: {len(pending)} pending instruction(s)!")
    print()
    for f, data in pending:
        inst_id = data.get("id", "?")
        title = data.get("title", "Untitled")
        priority = data.get("priority", "normal")
        print(f"  [{priority.upper()}] {inst_id}: {title}")
        instructions = data.get("instructions", "")
        if instructions:
            print(f"    {instructions[:200]}{'...' if len(instructions) > 200 else ''}")
        print()

    update_status(status_file, "has_pending", f"{len(pending)} instruction(s) waiting",
                  project, pending[0][1].get("id"))
    log_msg(log_file, f"CHECK [{project}]: {len(pending)} pending")


def cmd_status(project: str):
    inst_dir, res_dir, status_file, _ = get_dirs(project)

    if status_file.exists():
        s = json.loads(status_file.read_text(encoding="utf-8"))
        print(f"Project: {s.get('project', project)}")
        print(f"State:   {s.get('state', '?')}")
        print(f"Message: {s.get('message', '?')}")
        print(f"Pending: {s.get('pending_count', 0)}")
        print(f"Updated: {s.get('timestamp', '?')}")
    else:
        print(f"No status for {project}. Run --check first.")

    all_inst = get_all(inst_dir)
    if all_inst:
        print(f"\nInstructions ({len(all_inst)}):")
        for _, data in all_inst:
            st = data.get("status", "pending")
            icon = {"pending": "[ ]", "completed": "[x]", "error": "[!]"}.get(st, "[?]")
            print(f"  {icon} {data.get('id', '?')}: {data.get('title', 'Untitled')} ({st})")


def cmd_complete(project: str, instruction_id: str, summary: str):
    inst_dir, res_dir, status_file, log_file = get_dirs(project)
    res_dir.mkdir(parents=True, exist_ok=True)

    for f in inst_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("id") == instruction_id:
                data["status"] = "completed"
                data["completed_at"] = now_iso()
                f.write_text(json.dumps(data, indent=2), encoding="utf-8")

                result = {
                    "id": instruction_id,
                    "instruction_id": instruction_id,
                    "status": "completed",
                    "summary": summary,
                    "timestamp": now_iso(),
                    "from": "claude_code",
                    "project": project,
                }
                result_file = res_dir / f"{instruction_id}_result.json"
                result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

                log_msg(log_file, f"COMPLETED [{project}]: {instruction_id} -- {summary}")
                print(f"Marked {instruction_id} as completed.")

                update_status(status_file, "idle", f"Completed {instruction_id}", project)
                git_push_results(project)
                return
        except (json.JSONDecodeError, OSError):
            pass

    print(f"Instruction {instruction_id} not found in {project}.", file=sys.stderr)
    sys.exit(1)


def cmd_watch(project: str):
    inst_dir, _, status_file, log_file = get_dirs(project)
    inst_dir.mkdir(parents=True, exist_ok=True)
    update_status(status_file, "watching", "Watcher active", project)
    log_msg(log_file, f"WATCHER [{project}]: Started")
    print(f"Claude Bridge [{project}]: Watching... (Ctrl+C to stop)")
    print(f"  Dir: {inst_dir}")

    seen = set()
    try:
        while True:
            for f, data in get_pending(inst_dir):
                inst_id = data.get("id", "?")
                if inst_id not in seen:
                    seen.add(inst_id)
                    print(f"\n{'='*60}")
                    print(f"NEW [{data.get('priority','normal').upper()}] {inst_id}: {data.get('title','')}")
                    print(f"{'='*60}")
                    print(data.get("instructions", "")[:500])
                    print(f"\n>> Run: python scripts/claude_bridge.py --complete {inst_id} --project {project}")
                    update_status(status_file, "new_instruction", data.get("title", ""), project, inst_id)
                    log_msg(log_file, f"NEW [{project}]: {inst_id} -- {data.get('title','')}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopped.")
        update_status(status_file, "stopped", "Watcher stopped", project)


def main():
    p = argparse.ArgumentParser(description="Claude Bridge -- multi-project message queue")
    p.add_argument("--project", default=DEFAULT_PROJECT, help=f"Project name (default: {DEFAULT_PROJECT})")
    p.add_argument("--check", action="store_true", help="Check for pending instructions")
    p.add_argument("--watch", action="store_true", help="Watch continuously")
    p.add_argument("--status", action="store_true", help="Show bridge status")
    p.add_argument("--complete", metavar="ID", help="Mark instruction as completed")
    p.add_argument("--summary", default="Completed", help="Summary for --complete")

    args = p.parse_args()

    if args.complete:
        cmd_complete(args.project, args.complete, args.summary)
    elif args.check:
        cmd_check(args.project)
    elif args.watch:
        cmd_watch(args.project)
    elif args.status:
        cmd_status(args.project)
    else:
        cmd_check(args.project)


if __name__ == "__main__":
    main()
