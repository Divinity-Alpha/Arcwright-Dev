# Arcwright Check & Confirm Architecture
# The closed-loop verification system that makes AI-driven UE development reliable.
#
# PRINCIPLE: No command is complete until its effect is verified.
# Every action Claude takes in UE must be checked, confirmed, and logged.
# When verification fails, Claude works the problem until resolution.

---

## 1. The Problem

AI sends commands to UE blind. It has no way to know:
- Did the Blueprint actually get nodes? Or is it an empty shell?
- Did the widget render correctly? Or is it invisible?
- Did the actor spawn in the right place? Or is it underground?
- Does the game actually work when you press Play? Or is it the default template?
- Did the asset save to disk? Or will it vanish on restart?

Without verification, every "OK" response is a lie. The command succeeded at the TCP level
but may have failed at the UE level.

## 2. The Solution: Check & Confirm Protocol

Every verifiable action follows this pattern:

```
ACTION → CHECK → CONFIRM → LOG
   ↑                ↓
   └── RETRY ← DISCREPANCY
```

### ACTION
Claude sends the TCP command (create_blueprint, add_nodes_batch, etc.)

### CHECK
Claude immediately inspects the result using verification commands:
- get_blueprint_graph — verify nodes, connections, compile status
- get_level_snapshot — verify actors placed correctly
- get_widget_tree — verify widget hierarchy
- get_asset_list — verify asset exists on disk
- take_viewport_screenshot — visual verification of editor state
- play_and_capture — visual verification of runtime state

### CONFIRM
Claude compares the CHECK result against the EXPECTED result:
- Expected 20 nodes → got 20 nodes? CONFIRMED
- Expected actor at (100, 200, 0) → actor at (100, 200, 0)? CONFIRMED
- Expected compile success → compiled? CONFIRMED
- Expected visible shop interior → screenshot shows shop? CONFIRMED

### DISCREPANCY
If CHECK doesn't match EXPECTED:
- Log the discrepancy with full details
- Diagnose the root cause
- Fix and RETRY the action
- Re-CHECK after retry
- Maximum 3 retries before escalating to human

### LOG
Every action-check-confirm cycle is logged:
```json
{
  "action": "add_nodes_batch",
  "blueprint": "BP_TimeManager",
  "expected": {"nodes": 20, "connections": 18},
  "actual": {"nodes": 20, "connections": 18},
  "status": "CONFIRMED",
  "timestamp": "2026-03-21T20:15:00Z"
}
```

---

## 3. Verification Levels

Not every command needs the same level of verification.

### Level 0: Trust (no verification needed)
- Gameplay tag creation (always works)
- Sound class creation
- Simple property sets

### Level 1: Quick Check (verify status response)
- Data Table creation → check response has "ok" and row count
- Material creation → check response
- Input action creation → check response

### Level 2: Inspect (verify with inspection command)
- Blueprint creation → get_blueprint_graph to verify nodes + connections
- Widget creation → get_widget_tree to verify hierarchy
- Actor spawning → get_level_snapshot to verify position

### Level 3: Visual Verify (take screenshot)
- Level setup complete → take_viewport_screenshot, verify scene looks correct
- Widget UI complete → get_widget_preview, verify layout
- After all phases → play_and_capture, verify game runs

### Level 4: Persistence Verify (restart and re-check)
- After full build → save_all, close/reopen UE, re-verify assets exist
- Critical for: Blueprints (known persistence issue), Widgets, Level data

---

## 4. Check & Confirm for Each Asset Type

### Blueprints (Level 2 + compile check)
```
create_blueprint
  → CHECK: get_asset_list — does the .uasset exist?
  
add_nodes_batch
  → CHECK: get_blueprint_graph — node_count matches expected?
  
add_connections_batch
  → CHECK: get_blueprint_graph — connection_count matches expected?
  → DISCREPANCY: If connections < expected, log which failed, retry with corrected pin names
  
compile_blueprint
  → CHECK: get_compile_status — compiles=true? errors=[]?
  → DISCREPANCY: If compile fails, get error messages, diagnose, fix node/connection, retry
  → CONFIRM: "saved": true in response (persistence verified)

FULL VERIFICATION:
  → get_blueprint_graph returns: nodes >= target, connections >= target, compiles = true
  → Asset exists on disk (get_asset_list shows it)
```

### Widgets (Level 2)
```
create_widget_blueprint
  → CHECK: get_asset_list — .uasset exists?

add_widget_child (multiple)
  → CHECK after all children: get_widget_tree
  → CONFIRM: hierarchy matches expected structure
  → CONFIRM: property values are set correctly (text, color, font size)
  
FULL VERIFICATION:
  → get_widget_tree returns correct hierarchy
  → get_widget_preview shows rendered widget (if available)
```

### Level/Actors (Level 2-3)
```
spawn_actor_at
  → CHECK: get_level_snapshot — actor exists at expected position?
  → DISCREPANCY: If actor not found or wrong position, retry with corrected params

set_game_mode
  → CHECK: get_level_snapshot — game mode matches?

After all level setup:
  → take_viewport_screenshot — editor shows the scene correctly?
  → play_and_capture — PIE shows expected gameplay?
  → DISCREPANCY: If PIE shows default template, diagnose:
    - Is game mode set?
    - Is PlayerStart positioned inside the scene?
    - Are manager Blueprints spawned?
    - Do Blueprints have nodes (not empty shells)?
    - Were assets saved to disk?
```

### Data Tables (Level 1)
```
create_data_table
  → CHECK: response has row count matching expected
  → For critical tables: get_data_table_info — verify column schema and row count
```

---

## 5. The Play Test Cycle

The most important verification: does the game actually work?

```
1. save_all (ensure everything is on disk)
2. take_viewport_screenshot (verify editor state)
3. play_in_editor
4. wait 3 seconds (let game initialize)
5. take_pie_screenshot (capture what player sees)
6. get_log_output (capture any runtime errors or print statements)
7. stop_play

VERIFY:
- PIE screenshot shows game scene (NOT default template)
- Log output shows expected print statements from BeginPlay events
- No crash, no error messages
- If PrintStrings are in the Blueprints, they should appear in the log

DISCREPANCY HANDLING:
- If PIE shows default template:
  → Check: Is game mode set on this level?
  → Check: Does the game mode Blueprint compile?
  → Check: Is PlayerStart inside the scene geometry?
  → Check: Are the scene actors actually in this level (not a sublevel)?
  → Fix whichever is wrong, re-run Play Test Cycle

- If PIE shows black screen:
  → Check: Are there lights in the level?
  → Check: Is the player start below the floor?
  → Fix, re-run

- If PIE crashes:
  → get_log_output to find the crash reason
  → Fix the offending Blueprint or actor
  → Re-run
```

---

## 6. The Build Pipeline with Check & Confirm

Every phase of a game build uses Check & Confirm:

```
PHASE 1: Data Tables
  FOR each table:
    create_data_table → CHECK response → CONFIRM row count
  END PHASE CHECK: get_asset_list type=DataTable → CONFIRM count matches expected

PHASE 2: Input System
  FOR each action:
    create_input_action → CHECK response
  END PHASE CHECK: verify input config exists

PHASE 3: Gameplay Tags
  FOR each tag group:
    create_gameplay_tags → CHECK response
  END PHASE CHECK: verify tags registered

PHASE 4: Materials
  FOR each material:
    create_material → CHECK response → CONFIRM asset exists
  END PHASE CHECK: get_asset_list type=Material → CONFIRM count

PHASE 5: Blueprints [MOST CRITICAL]
  FOR each blueprint:
    create_blueprint → CHECK asset exists
    add_nodes_batch → CHECK get_blueprint_graph → CONFIRM node_count
    add_connections_batch → CHECK get_blueprint_graph → CONFIRM connection_count
    compile_blueprint → CHECK get_compile_status → CONFIRM compiles=true
    IF compile fails:
      get_compile_status for error messages
      diagnose and fix
      retry (max 3)
  END PHASE CHECK: 
    FOR each blueprint: get_blueprint_graph → CONFIRM all pass
    ALL must compile clean

PHASE 6: Widget UIs
  FOR each widget:
    create_widget_blueprint → CHECK asset exists
    add children → CHECK get_widget_tree → CONFIRM hierarchy
  END PHASE CHECK: get_asset_list type=WidgetBlueprint → CONFIRM count

PHASE 7: Level Setup
  Build geometry → CHECK get_level_snapshot → CONFIRM actor positions
  Set game mode → CHECK get_level_snapshot → CONFIRM game mode
  Place PlayerStart → CHECK position is inside scene
  END PHASE CHECK: take_viewport_screenshot → CONFIRM scene visible

FINAL VERIFICATION:
  save_all
  take_viewport_screenshot → CONFIRM editor scene
  play_in_editor → wait → take_pie_screenshot → CONFIRM gameplay works
  get_log_output → CONFIRM expected prints appear, no errors
  stop_play
  
  REPORT:
  - Total commands, successes, errors
  - Per-blueprint: nodes, connections, compile status
  - Asset counts by type
  - Viewport screenshot path
  - PIE screenshot path
  - Any unresolved discrepancies
```

---

## 7. Discrepancy Resolution Protocol

When CHECK doesn't match EXPECTED:

```
SEVERITY 1 — Auto-fix (retry with corrected params):
- Wrong parameter name (blueprint vs name)
- Wrong pin name (then vs Then)
- Wrong function path
→ Fix params, retry, re-check

SEVERITY 2 — Diagnose and fix:
- Blueprint doesn't compile (pin type mismatch, unconnected required pins)
- Widget child not appearing (wrong parent name)
- Actor at wrong position
→ Get detailed error info, adjust approach, retry

SEVERITY 3 — Redesign:
- Node type not supported
- Feature not available via TCP commands
- UE API limitation
→ Log the limitation, find alternative approach, document for future

SEVERITY 4 — Escalate to human:
- After 3 retries with no resolution
- Crash that can't be diagnosed from logs
- Visual issue that can't be verified without human eyes
→ Take screenshot, log full state, ask human for guidance
```

---

## 8. Logging Format

Every Check & Confirm cycle produces a log entry:

```json
{
  "phase": "Blueprints",
  "action": "add_nodes_batch",
  "target": "BP_TimeManager",
  "expected": {
    "node_count": 20,
    "connection_count": 18
  },
  "check_command": "get_blueprint_graph",
  "actual": {
    "node_count": 20,
    "connection_count": 16
  },
  "status": "DISCREPANCY",
  "discrepancy": "2 connections missing",
  "resolution": "Retried with corrected pin names 'then 0' → 'Then 0'",
  "retry_count": 1,
  "final_status": "CONFIRMED",
  "timestamp": "2026-03-21T20:15:00Z"
}
```

The full build log is a sequence of these entries, providing:
- Complete audit trail of what was built
- Every discrepancy and how it was resolved
- Performance data (which commands fail most often)
- Input for improving ARCWRIGHT_AI_GUIDE.md

---

## 9. Customer Value

For customers, Check & Confirm means:
- Their AI validates its own work automatically
- Fewer broken assets, fewer "why doesn't this work" moments
- The AI catches its own mistakes and fixes them
- Build logs show exactly what was created and verified
- Confidence that the game build is correct before human review

For us (Arcwright development):
- Automated regression testing
- Every bug found by Check & Confirm improves the AI guide
- Build reliability metrics per command
- Identifies which commands need better error handling

---

## 10. Implementation Priority

### Phase 1 (NOW): Core inspection commands
- [DONE] take_viewport_screenshot
- [DONE] get_blueprint_graph
- [DONE] get_compile_status
- [DONE] get_level_snapshot
- [DONE] get_asset_list
- [DONE] get_widget_tree
- [DONE] get_actor_details
- [DONE] get_log_output

### Phase 2 (NEXT): PIE verification
- play_and_capture (start PIE, wait, screenshot, stop)
- get_pie_screenshot (screenshot during active PIE)
- get_runtime_log (capture PrintString output during PIE)

### Phase 3: Enhanced verification
- get_widget_preview (render widget to image without PIE)
- get_blueprint_compile_errors (detailed error messages with line/node info)
- compare_blueprint_graph (expected vs actual diff)
- verify_all_blueprints (batch compile check)

### Phase 4: Self-healing
- auto_fix_compile_errors (common fixes applied automatically)
- auto_fix_connections (retry failed connections with pin name variations)
- auto_fix_persistence (force save if dirty packages detected)

---

## 11. The Arcwright AI Guide Integration

The AI Best Practices Guide must include:
1. The Check & Confirm protocol (this document, summarized)
2. Which verification level to use for each command
3. The exact check commands to call after each action
4. The discrepancy resolution protocol
5. Expected values for common scenarios
6. The Play Test Cycle steps

Every customer's AI reads this guide on first connection and follows Check & Confirm automatically.
