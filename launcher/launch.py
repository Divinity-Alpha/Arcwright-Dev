#!/usr/bin/env python3
# Arcwright Launcher
# C:\Arcwright\launcher\launch.py
#
# Usage:
#   python launch.py neonbreach
#   python launch.py fp_starter
#   python launch.py test_lighting
#   python launch.py list
#
# Writes a CLAUDE_NEXT.md file that Claude Code
# picks up automatically via file watch.
# No copy-paste required.

import os
import sys
import time
import datetime
import subprocess

COMMANDS_DIR  = r"C:\Arcwright\knowledge\commands"
LAUNCHER_DIR  = r"C:\Arcwright\launcher"
WATCH_FILE    = r"C:\Arcwright\launcher\CLAUDE_NEXT.md"
LOG_FILE      = r"C:\Arcwright\launcher\launch_log.txt"

# ─────────────────────────────────────────────
# COMMAND REGISTRY
# Add new command files here as they are created
# ─────────────────────────────────────────────

COMMANDS = {
    "neonbreach":       "neonbreach_build.md",
    "fp_starter":       "fp_starter_build.md",
    "test_lighting":    "test_lighting_suite.md",
    "test_mesh":        "test_mesh_suite.md",
    "test_fp":          "test_fp_suite.md",
    "test_all":         "arcwright_test_suite.py",
    "fix_loop_104":     "v104_overnight.md",
    "fix_loop_105":     "v105_fix_loop.md",
    "clean_project":    "create_clean_test_project.md",
    "nuclear_clean":    "nuclear_clean.md",
    "package":          "package_release.md",
}

# ─────────────────────────────────────────────

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def list_commands():
    print("\nAvailable commands:")
    print(f"  {'Name':<20} {'File'}")
    print(f"  {'────':<20} {'────'}")
    for name, file in sorted(COMMANDS.items()):
        path = os.path.join(COMMANDS_DIR, file)
        exists = "[OK]" if os.path.exists(path) else "[X] MISSING"
        print(f"  {name:<20} {file}  {exists}")
    print()

def launch(name):
    if name not in COMMANDS:
        print(f"Unknown command: {name}")
        print("Run: python launch.py list")
        sys.exit(1)

    filename = COMMANDS[name]
    filepath = os.path.join(COMMANDS_DIR, filename)

    if not os.path.exists(filepath):
        print(f"Command file not found: {filepath}")
        sys.exit(1)

    os.makedirs(LAUNCHER_DIR, exist_ok=True)

    # Write the instruction file Claude Code watches
    content = f"""# Arcwright Auto-Launch
## Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
## Command: {name}

Execute the following command file immediately.
Do not wait for further input.

{filepath}

Reference CLAUDE.md before starting.
GPU: CUDA_VISIBLE_DEVICES=0 (RTX 5070 Ti only)
"""
    with open(WATCH_FILE, "w") as f:
        f.write(content)

    log(f"Launched: {name} -> {filename}")
    print(f"\n  [OK] Launched: {name}")
    print(f"  File: {filepath}")
    print(f"  Watch: {WATCH_FILE}")
    print(f"\n  Claude Code will pick this up automatically.")
    print(f"  Check the Claude Code terminal for progress.\n")

def main():
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        list_commands()
        return

    cmd = sys.argv[1].lower()
    launch(cmd)

if __name__ == "__main__":
    main()
