# Claude-to-Claude MCP Bridge
# Enables direct communication between Claude.ai and Claude Code
# 
# STATUS: Design Document — give this to Claude Code to implement

---

## The Problem

Currently:
```
Claude.ai (architect) → Scott (copy/paste) → Claude Code (executor)
Claude Code (results) → Scott (copy/paste) → Claude.ai (review)
```

Scott is the bottleneck. Every instruction and every result passes through manual copy-paste.
Instructions get truncated, context gets lost, and Scott spends hours as a middleman.

## The Solution

An MCP server that both Claude.ai and Claude Code can communicate through:

```
Claude.ai → writes to shared message queue → Claude Code reads and executes
Claude Code → writes results to queue → Claude.ai reads and reviews
```

## Architecture

### Option A: File-Based Message Queue (Simplest)

A shared directory on the local machine acts as the message queue.
Claude.ai can't write files directly, but Scott can paste a single 
JSON blob that creates the instruction file. Claude Code watches the 
directory and auto-executes.

```
C:\Projects\BoreAndStroke_Original\.claude-bridge\
├── instructions/
│   ├── 001_build_station_actions.json    (Claude.ai's instructions)
│   ├── 002_fix_hud_layout.json
│   └── 003_run_qa_test.json
├── results/
│   ├── 001_result.json                    (Claude Code's results)
│   ├── 002_result.json
│   └── 003_result.json
├── status.json                            (Current state)
└── conversation.log                       (Full history)
```

**Instruction format:**
```json
{
  "id": "001",
  "timestamp": "2026-03-22T15:00:00Z",
  "from": "claude.ai",
  "priority": "high",
  "type": "build",
  "title": "Make station actions functional",
  "instructions": "Check BSStationWidget for action list population...",
  "verification": {
    "type": "play_test",
    "steps": ["walk to station", "press E", "verify actions listed"],
    "success_criteria": "Station UI shows available actions from CSV"
  },
  "constraints": [
    "Do NOT modify any widget not in the Arcwright manifest",
    "Git commit after verified working"
  ]
}
```

**Result format:**
```json
{
  "id": "001",
  "instruction_id": "001",
  "timestamp": "2026-03-22T15:15:00Z",
  "from": "claude_code",
  "status": "completed",
  "summary": "Station actions now load from CSV. 5 actions per station.",
  "changes": [
    {"file": "BSStationWidget.cpp", "action": "modified", "lines_changed": 45},
    {"file": "WBP_Station_Degriming.uasset", "action": "created"}
  ],
  "verification_result": {
    "play_test": "PASS",
    "screenshots": ["station_actions_01.png", "station_actions_02.png"],
    "log_output": ["5 actions loaded for Degriming station"]
  },
  "issues": [],
  "lessons_learned": [],
  "git_commit": "abc123"
}
```

### Option B: TCP Socket Bridge (More Automated)

An MCP server that runs on the local machine. Claude Code connects 
to it as an MCP client. The server also exposes a simple HTTP API 
that could be called from a browser (where Claude.ai conversation runs).

```
Claude.ai conversation
  → Scott clicks "Send to Claude Code" button (in an artifact)
  → HTTP POST to localhost:13380/instruction
  → MCP Bridge server receives it
  → Claude Code polls for new instructions
  → Executes and posts results
  → Claude.ai artifact polls for results
  → Displays in conversation
```

This is more complex but could be almost fully automated.

### Option C: CLAUDE.md Instruction Queue (Simplest for Claude Code)

Use CLAUDE.md itself as the communication channel. Claude.ai writes 
instructions to a specific section. Claude Code reads CLAUDE.md on 
every session start and executes pending instructions.

```markdown
## Pending Instructions (from Claude.ai)

### INSTRUCTION 001 — Build Station Actions
Priority: HIGH
Status: PENDING

Instructions:
[detailed instructions here]

Verification:
[verification steps here]

---

### INSTRUCTION 002 — Fix HUD Layout  
Priority: MEDIUM
Status: PENDING
```

Claude Code reads these, executes them, and changes status to COMPLETED 
with results.

## Recommended: Option A + Watcher Script

**Why:** File-based is the most reliable. No extra servers to run.
Claude Code can watch the directory with a simple Python script.

### Implementation

**1. Bridge Watcher (Python — runs alongside Claude Code)**

```python
# scripts/claude_bridge.py
"""
Watches for instruction files from Claude.ai.
Claude Code runs this in the background.
"""
import json, os, time, glob
from pathlib import Path

BRIDGE_DIR = Path(".claude-bridge")
INSTRUCTIONS_DIR = BRIDGE_DIR / "instructions"
RESULTS_DIR = BRIDGE_DIR / "results"
STATUS_FILE = BRIDGE_DIR / "status.json"

def init():
    """Create bridge directories."""
    INSTRUCTIONS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    update_status("idle", "Waiting for instructions")

def update_status(state, message):
    """Update the shared status file."""
    status = {
        "state": state,  # idle, executing, waiting_for_verification
        "message": message,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_instruction": None,
        "pending_count": len(get_pending_instructions())
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))

def get_pending_instructions():
    """Find all unprocessed instruction files."""
    pending = []
    for f in sorted(INSTRUCTIONS_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        if data.get("status", "pending") == "pending":
            pending.append((f, data))
    return pending

def mark_completed(instruction_file, result):
    """Mark an instruction as completed and save result."""
    # Update instruction status
    data = json.loads(instruction_file.read_text())
    data["status"] = "completed"
    instruction_file.write_text(json.dumps(data, indent=2))
    
    # Save result
    result_file = RESULTS_DIR / f"{data['id']}_result.json"
    result_file.write_text(json.dumps(result, indent=2))

def watch(callback):
    """Watch for new instructions and call callback for each."""
    init()
    print("Claude Bridge: Watching for instructions...")
    
    while True:
        pending = get_pending_instructions()
        if pending:
            for f, instruction in pending:
                print(f"  Executing: {instruction.get('title', instruction['id'])}")
                update_status("executing", instruction.get("title", ""))
                
                try:
                    result = callback(instruction)
                    mark_completed(f, result)
                    print(f"  Completed: {instruction['id']}")
                except Exception as e:
                    mark_completed(f, {
                        "id": instruction["id"],
                        "status": "error",
                        "error": str(e)
                    })
                    print(f"  Error: {e}")
                
                update_status("idle", "Waiting for instructions")
        
        time.sleep(2)  # Poll every 2 seconds
```

**2. How Scott Uses It**

Instead of copying my full instructions to Claude Code, Scott does:

1. I (Claude.ai) generate a JSON instruction file
2. Scott saves it to `.claude-bridge/instructions/001_task.json`
3. Claude Code's watcher picks it up automatically
4. Claude Code executes and saves the result
5. Scott (or I via the conversation) reads the result file

**3. How Claude Code Uses It**

At the start of every session:
```bash
# In CLAUDE.md or session start:
# Check for pending bridge instructions
python scripts/claude_bridge.py --check
```

Or run the watcher in background:
```bash
python scripts/claude_bridge.py --watch &
```

**4. Integration with Artifacts**

In Claude.ai, I can create a React artifact that:
- Shows a text input for instructions
- Has a "Send to Claude Code" button
- Writes the instruction JSON to the clipboard
- Scott pastes it into a terminal command:
  `echo '{"id":"001",...}' > .claude-bridge/instructions/001.json`

Or even better — I generate a PowerShell one-liner that creates the file:
```powershell
Set-Content -Path ".claude-bridge\instructions\001_task.json" -Value '{"id":"001","instructions":"..."}'
```
Scott runs that ONE command and the instruction is delivered.

## Future: Full Automation via MCP

When Claude.ai supports calling MCP servers directly (not just 
Claude Code), the bridge becomes fully automated:

```
Claude.ai → MCP call → Bridge Server → Claude Code
Claude Code → MCP result → Bridge Server → Claude.ai
```

No Scott in the loop at all for routine instructions.

## Priority for Implementation

1. Create the bridge directory structure
2. Create claude_bridge.py with watch functionality
3. Add bridge checking to CLAUDE.md session start
4. I (Claude.ai) start generating instruction JSONs instead of prose
5. Scott runs one PowerShell command per instruction instead of copy-pasting paragraphs

This reduces Scott's role from "translate and copy paragraphs of instructions"
to "run a single command per task."
