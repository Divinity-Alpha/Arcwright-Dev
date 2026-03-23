#!/usr/bin/env python3
"""
Claude Bridge — File-based message queue between Claude.ai and Claude Code.

Claude.ai (architect) generates JSON instruction files.
Scott saves them to .claude-bridge/instructions/.
This script watches for new instructions and reports them to Claude Code.

Usage:
    python scripts/claude_bridge.py --check      # Check for pending instructions (non-blocking)
    python scripts/claude_bridge.py --watch       # Watch continuously (blocking)
    python scripts/claude_bridge.py --status      # Show current bridge status
    python scripts/claude_bridge.py --complete ID # Mark instruction as completed with result

The bridge directory is at .claude-bridge/ relative to the project root.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Bridge lives at project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_DIR = PROJECT_ROOT / ".claude-bridge"
INSTRUCTIONS_DIR = BRIDGE_DIR / "instructions"
RESULTS_DIR = BRIDGE_DIR / "results"
STATUS_FILE = BRIDGE_DIR / "status.json"
LOG_FILE = BRIDGE_DIR / "conversation.log"


def init():
    """Create bridge directories if they don't exist."""
    INSTRUCTIONS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_message(message: str):
    """Append a timestamped message to the conversation log."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {message}\n")


def update_status(state: str, message: str, last_instruction: str = None):
    """Update the shared status file."""
    pending = get_pending_instructions()
    status = {
        "state": state,
        "message": message,
        "timestamp": now_iso(),
        "last_instruction": last_instruction,
        "pending_count": len(pending),
        "pending_ids": [d.get("id", "?") for _, d in pending],
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")


def get_pending_instructions():
    """Find all unprocessed instruction files, sorted by filename."""
    pending = []
    if not INSTRUCTIONS_DIR.exists():
        return pending
    for f in sorted(INSTRUCTIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status", "pending") == "pending":
                pending.append((f, data))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Warning: Could not read {f.name}: {e}", file=sys.stderr)
    return pending


def get_all_instructions():
    """Get all instruction files with their status."""
    instructions = []
    if not INSTRUCTIONS_DIR.exists():
        return instructions
    for f in sorted(INSTRUCTIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            instructions.append((f, data))
        except (json.JSONDecodeError, OSError):
            pass
    return instructions


def mark_completed(instruction_id: str, result: dict):
    """Mark an instruction as completed and save the result."""
    # Find the instruction file
    for f in INSTRUCTIONS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("id") == instruction_id:
                data["status"] = "completed"
                data["completed_at"] = now_iso()
                f.write_text(json.dumps(data, indent=2), encoding="utf-8")

                # Save result
                result["instruction_id"] = instruction_id
                result["timestamp"] = now_iso()
                result["from"] = "claude_code"
                result_file = RESULTS_DIR / f"{instruction_id}_result.json"
                result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

                log_message(f"COMPLETED: {instruction_id} — {result.get('summary', 'done')}")
                return True
        except (json.JSONDecodeError, OSError):
            pass
    print(f"Instruction {instruction_id} not found.", file=sys.stderr)
    return False


def cmd_check():
    """Check for pending instructions — non-blocking, for session start."""
    init()
    pending = get_pending_instructions()

    if not pending:
        print("Claude Bridge: No pending instructions.")
        update_status("idle", "No pending instructions")
        return

    print(f"Claude Bridge: {len(pending)} pending instruction(s)!")
    print()
    for f, data in pending:
        inst_id = data.get("id", "?")
        title = data.get("title", "Untitled")
        priority = data.get("priority", "normal")
        inst_type = data.get("type", "task")
        print(f"  [{priority.upper()}] {inst_id}: {title} ({inst_type})")

        # Show brief instructions
        instructions = data.get("instructions", "")
        if instructions:
            preview = instructions[:200]
            if len(instructions) > 200:
                preview += "..."
            print(f"    {preview}")
        print()

    update_status("has_pending", f"{len(pending)} instruction(s) waiting", pending[0][1].get("id"))
    log_message(f"CHECK: Found {len(pending)} pending instruction(s)")


def cmd_status():
    """Show current bridge status."""
    if STATUS_FILE.exists():
        status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        print(f"Bridge State: {status.get('state', '?')}")
        print(f"Message: {status.get('message', '?')}")
        print(f"Pending: {status.get('pending_count', 0)}")
        print(f"Last Update: {status.get('timestamp', '?')}")
    else:
        print("Bridge not initialized. Run: python scripts/claude_bridge.py --check")

    # Show all instructions
    all_inst = get_all_instructions()
    if all_inst:
        print(f"\nAll Instructions ({len(all_inst)}):")
        for f, data in all_inst:
            status_str = data.get("status", "pending")
            icon = {"pending": "[ ]", "completed": "[x]", "error": "[!]"}.get(status_str, "[?]")
            print(f"  {icon} {data.get('id', '?')}: {data.get('title', 'Untitled')} ({status_str})")


def cmd_watch():
    """Watch for new instructions continuously."""
    init()
    update_status("watching", "Watcher active — waiting for instructions")
    log_message("WATCHER: Started")
    print("Claude Bridge: Watching for instructions... (Ctrl+C to stop)")
    print(f"  Instructions dir: {INSTRUCTIONS_DIR}")
    print(f"  Results dir: {RESULTS_DIR}")
    print()

    seen = set()
    try:
        while True:
            pending = get_pending_instructions()
            for f, data in pending:
                inst_id = data.get("id", "?")
                if inst_id not in seen:
                    seen.add(inst_id)
                    title = data.get("title", "Untitled")
                    priority = data.get("priority", "normal")
                    print(f"\n{'='*60}")
                    print(f"NEW INSTRUCTION: [{priority.upper()}] {inst_id}")
                    print(f"Title: {title}")
                    print(f"{'='*60}")
                    instructions = data.get("instructions", "")
                    if instructions:
                        print(instructions[:500])
                    print()
                    print(">> Claude Code should execute this instruction now.")
                    print(f">> When done: python scripts/claude_bridge.py --complete {inst_id}")
                    print()

                    update_status("new_instruction", f"New: {title}", inst_id)
                    log_message(f"NEW: {inst_id} — {title}")

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")
        update_status("stopped", "Watcher stopped")
        log_message("WATCHER: Stopped")


def cmd_complete(instruction_id: str, summary: str = "Completed"):
    """Mark an instruction as completed."""
    result = {
        "id": instruction_id,
        "status": "completed",
        "summary": summary,
    }
    if mark_completed(instruction_id, result):
        print(f"Marked {instruction_id} as completed.")
        update_status("idle", f"Completed {instruction_id}")
    else:
        print(f"Failed to mark {instruction_id}.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Claude Bridge — message queue between Claude.ai and Claude Code")
    parser.add_argument("--check", action="store_true", help="Check for pending instructions")
    parser.add_argument("--watch", action="store_true", help="Watch for instructions continuously")
    parser.add_argument("--status", action="store_true", help="Show bridge status")
    parser.add_argument("--complete", metavar="ID", help="Mark instruction ID as completed")
    parser.add_argument("--summary", default="Completed", help="Summary for --complete")

    args = parser.parse_args()

    if args.check:
        cmd_check()
    elif args.watch:
        cmd_watch()
    elif args.status:
        cmd_status()
    elif args.complete:
        cmd_complete(args.complete, args.summary)
    else:
        # Default: check
        cmd_check()


if __name__ == "__main__":
    main()
