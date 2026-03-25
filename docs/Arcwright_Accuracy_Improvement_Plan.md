# Arcwright — Continuous Accuracy Improvement Plan

> **Goal:** Systematically test every command Arcwright should handle, score results, identify failures, fix them, retest, and track improvement over time.
> **Method:** Automated test cycles that mimic real users, with results feeding back into fixes and training.

---

## THE LOOP

```
    ┌─────────────────────────────┐
    │   1. RUN TEST SUITE         │
    │   (120 commands, scored)    │
    └────────────┬────────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │   2. GRADE RESULTS          │
    │   (per-command 4-point)     │
    └────────────┬────────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │   3. CLASSIFY FAILURES      │
    │   (intent? plan? exec?      │
    │    verify? which component?) │
    └────────────┬────────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │   4. FIX                    │
    │   - Hard override rule?     │
    │   - System prompt example?  │
    │   - Post-processor rule?    │
    │   - TCP command bug?        │
    │   - Training data needed?   │
    └────────────┬────────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │   5. RETEST FAILURES ONLY   │
    │   (confirm fix works)       │
    └────────────┬────────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │   6. FULL REGRESSION        │
    │   (make sure fixes didn't   │
    │    break other things)      │
    └────────────┬────────────────┘
                 │
                 └──────── back to 1
```

Every cycle produces a scored report. Over time we track the accuracy curve and identify patterns in what fails.

---

## TEST INFRASTRUCTURE

### Files

```
C:\BlueprintLLM\tests\
├── accuracy/
│   ├── test_commands.json          # The 120 commands with metadata
│   ├── test_runner.py              # Sends commands, scores results
│   ├── test_verifier.py            # Queries UE to verify outcomes
│   ├── report_generator.py         # Builds HTML/MD report from results
│   ├── failure_classifier.py       # Categorizes failures by root cause
│   └── results/
│       ├── run_001_20260312.json   # Each run saved with timestamp
│       ├── run_002_20260312.json
│       ├── ...
│       └── accuracy_history.json   # Score over time for trend tracking
├── manual_test_log.txt             # Human-readable replay log
└── known_failures.json             # Tracked failures with status
```

### Test Command Schema

Each command in `test_commands.json`:

```json
{
  "id": "C.01",
  "prompt": "Create a health pickup that restores 25 HP when the player touches it",
  "category": "create_blueprint",
  "subcategory": "pickup",
  "expected_mode": "CREATE",
  "expected_commands": ["create_blueprint"],
  "verify": [
    {
      "type": "blueprint_exists",
      "params": {"name_pattern": "*Health*Pickup*"}
    },
    {
      "type": "blueprint_has_variable",
      "params": {"name_pattern": "*Health*Pickup*", "variable": "Health", "or_variable": "HealAmount"}
    },
    {
      "type": "blueprint_has_node",
      "params": {"name_pattern": "*Health*Pickup*", "node_type": "Event_ActorBeginOverlap"}
    }
  ],
  "tags": ["simple", "overlap", "destroy", "variable"],
  "difficulty": 1,
  "added_in_run": 0,
  "last_passed_run": null,
  "consecutive_failures": 0
}
```

### Scoring (5 dimensions now, not 4)

| Dimension | Points | What It Measures |
|---|---|---|
| **Intent** | 1 | Did the LLM classify the mode correctly? |
| **Plan** | 1 | Did the plan contain the right commands? |
| **Execute** | 1 | Did all commands execute without errors? |
| **Verify** | 1 | Does the UE state match expectations? |
| **Quality** | 1 | Is the output GOOD? (right variable names, sensible node structure, proper connections) |

**Total: 5 points per command × 120 commands = 600 points maximum**

Quality scoring requires deeper inspection:
- For Blueprints: does it have sensible variable names? reasonable node count? proper exec chain?
- For BT: correct tree structure? right decorators and services?
- For DT: correct column types? reasonable default values?
- For MODIFY: did it change the RIGHT things? (not just "no errors")

---

## THE 120 COMMANDS — ORGANIZED BY PHASE

### Phase 1: Foundation (run first, creates level state)

Commands 1-10 build the base level that all other tests operate on:

```
F.01  "Set up FPS controls for the game"
F.02  "Add dark indoor lighting to the level"
F.03  "Create a ground floor with stone texture"
F.04  "Create an enemy with 100 health, 15 damage, and 300 speed"
F.05  "Create a gold coin pickup worth 10 points"
F.06  "Create a torch with a point light"
F.07  "Create a health pickup that heals 25 HP"
F.08  "Spawn 5 enemies around the level"
F.09  "Spawn 8 coins around the level"
F.10  "Spawn 4 torches along the walls"
```

### Phase 2: Create Tests (25 commands)

Each creates a new asset and verifies it exists with correct properties:

```
C.01  "Create a health pickup that restores 25 HP when the player touches it"
C.02  "Make a coin that adds 10 points to the score and destroys itself"
C.03  "Build a door that opens when the player has a key"
C.04  "Create a pressure plate that activates when something stands on it"
C.05  "Make a timed bomb that explodes after 5 seconds"
C.06  "Build a checkpoint that saves the player's position"
C.07  "Create a turret that fires at the player every 2 seconds when in range"
C.08  "Make a moving platform that goes up 300 units and comes back down"
C.09  "Build a score manager that tracks points and high score"
C.10  "Create a wave spawner that sends enemies every 15 seconds"
C.11  "Make a day night cycle that toggles every 60 seconds"
C.12  "Build a respawn system that resets the player after 3 seconds"
C.13  "Create a treasure chest that gives random gold between 10 and 50"
C.14  "Make a lever that toggles between on and off"
C.15  "Build a damage zone that hurts 10 HP per second"
C.16  "Create a teleporter that moves the player to a target point"
C.17  "Make a blinking light that turns on and off every 3 seconds"
C.18  "Create a spinning actor that rotates on its Z axis"
C.19  "Build a spring pad that launches the player upward"
C.20  "Create a game manager that initializes score and health"
C.21  "Make a patrol AI that walks between two waypoints"
C.22  "Build a boss AI with three phases based on health"
C.23  "Create a weapons table with name, damage, fire rate, and ammo"
C.24  "Make an enemy stats table with name, health, damage, and XP reward"
C.25  "Build a difficulty settings table with multipliers for health and damage"
```

### Phase 3: Modify Tests (35 commands)

Each modifies existing assets from Phases 1-2 and verifies the change:

```
M.01  "Set health to 200 on all enemies"
M.02  "Make the enemies faster"
M.03  "Double the enemy damage"
M.04  "Gold coins should be worth 50 each"
M.05  "Reduce torch intensity to 2000"
M.06  "All enemies need 500 HP and 40 damage"
M.07  "Make the health pickups heal 50 instead of 25"
M.08  "Change the material on all the walls to brick"
M.09  "Replace the texture on every floor with marble"
M.10  "Make the torches look like gold"
M.11  "Swap the stone material to concrete on all walls"
M.12  "Replace stone with brick everywhere in the level"
M.13  "Apply the lava material to all hazard zones"
M.14  "Change the wall texture to M_Pack_Bonus_Stone_2"
M.15  "Scale all enemies up by 1.5"
M.16  "Make the coins smaller"
M.17  "Delete all the gold coins from the level"
M.18  "Remove every torch"
M.19  "Hide all the health pickups"
M.20  "Move all coins up by 50 units"
M.21  "Clear out all the damage zones"
M.22  "Add a point light to every torch"
M.23  "Give all enemies a sphere collision component"
M.24  "Rename BP_GoldCoin to BP_TreasureCoin"
M.25  "Change the enemy parent class to Character"
M.26  "The enemies are too weak, buff them"
M.27  "Everything looks too plain, change the walls"
M.28  "Make all coins worth double"
M.29  "The torches are too bright, dim them"
M.30  "Replace the material on all walls with M_Pack_Bonus_Stone_2"
M.31  "Swap the wall material to marble"
M.32  "Change the texture on all the walls to stone"
M.33  "Make the floor darker"
M.34  "Set the coin value to 100 on every pickup"
M.35  "Increase enemy detection range to 1200"
```

### Phase 4: Query Tests (15 commands)

Each queries the level and verifies the response contains correct information:

```
Q.01  "How many enemies are in the level?"
Q.02  "Show me all the blueprints in the project"
Q.03  "What's in the level right now?"
Q.04  "Which blueprints have a Health variable?"
Q.05  "How many coins did I place?"
Q.06  "List all the materials in the project"
Q.07  "What components does the enemy blueprint have?"
Q.08  "How many actors total are in the level?"
Q.09  "Show me all the data tables I've created"
Q.10  "What variables does BP_Enemy have?"
Q.11  "Are there any torches in the level?"
Q.12  "How many health pickups are placed?"
Q.13  "What's the current lighting setup?"
Q.14  "List all behavior trees in the project"
Q.15  "Show me everything matching 'wall'"
```

### Phase 5: Multi-Step Tests (15 commands)

Each requires multiple operations and verifies all of them:

```
X.01  "Create a health potion and spawn 3 of them"
X.02  "Set up FPS controls and add dark lighting"
X.03  "Delete all coins and replace them with gems worth 100"
X.04  "Make all enemies tougher and change lighting to outdoor"
X.05  "Build a boss room with one strong enemy and health pickups"
X.06  "Create a patrol enemy, set health to 200, spawn 5 of them"
X.07  "Add torches to the hallway and make them glow warm"
X.08  "Create an enemy and a behavior tree and wire them together"
X.09  "Replace all wall materials with brick and add bloom"
X.10  "Create weapons, enemy stats, and difficulty tables for my game"
X.11  "Delete all enemies, create a stronger version, spawn 3"
X.12  "Change walls to marble and make the room brighter"
X.13  "Create a key, a locked door, and place them in the level"
X.14  "Add 6 torches along the corridor and apply gold material"
X.15  "Set up the arena: floor, walls, lighting, enemies, and pickups"
```

### Phase 6: Edge Cases and Conversational (20 commands)

```
V.01  "The level feels empty"
V.02  "Make it better"
V.03  "The game is too easy"
V.04  "I'm stuck, help me"
V.05  "Can you suggest what to add next?"
V.06  "The boss room needs to feel more dramatic"
V.07  "Something doesn't look right about the lighting"
V.08  "I need more variety"
V.09  "The enemies are boring"
V.10  "Too many coins"
E.01  "Create a blueprint called BP_Test with no functionality"
E.02  "Delete everything in the level"
E.03  "Set health to -50 on all enemies"
E.04  "Apply a material that doesn't exist to the walls"
E.05  "Create 100 enemies"
E.06  "Change the material on actors that don't exist"
E.07  "Rename a blueprint that doesn't exist"
E.08  "Make the walls transparent"
E.09  "Create a weapon that does 999999 damage"
E.10  "Undo the last thing you did"
```

---

## FAILURE CLASSIFICATION

Every failure gets categorized by root cause:

| Code | Root Cause | Fix Location |
|---|---|---|
| **I1** | Intent misclassified (wrong mode) | System prompt examples |
| **I2** | Intent timeout / empty response | Inference timeout / model issue |
| **I3** | Intent returned wrong command | System prompt or hard override |
| **P1** | Plan has empty operations | System prompt examples |
| **P2** | Plan has wrong parameters | Post-processor rule or system prompt |
| **P3** | Plan uses non-existent command | Command whitelist / alias map |
| **P4** | Plan missing step dependency | Post-processor injection rule |
| **E1** | TCP command returned error | C++ command handler bug |
| **E2** | Material not found / not resolved | Material resolver or asset path |
| **E3** | Actor not found | Name filter too narrow / wrong |
| **E4** | Blueprint not found | Search path issue |
| **E5** | Parameter format mismatch | Post-processor normalization |
| **V1** | Asset created but wrong structure | DSL model quality (training) |
| **V2** | Variable exists but wrong value | DSL model quality (training) |
| **V3** | Correct command but wrong targets changed | Discovery stage filter issue |
| **V4** | Partial success (some actors failed) | Actors missing components |
| **Q1** | Quality: variable names nonsensical | DSL model quality (training) |
| **Q2** | Quality: missing expected functionality | DSL model quality (training) |
| **Q3** | Quality: extra unwanted nodes/logic | DSL model quality (training) |

---

## TRACKING AND REPORTING

### Per-Run Report (generated automatically)

```
═══════════════════════════════════════════════════════════
 ARCWRIGHT ACCURACY REPORT — Run #007 — 2026-03-12
═══════════════════════════════════════════════════════════

 Overall: 487/600 (81.2%)   Previous: 472/600 (78.7%)   Δ: +2.5%

 ┌──────────────────┬───────┬───────┬────────┬────────┬────────┬───────┐
 │ Category         │Intent │ Plan  │  Exec  │ Verify │Quality │ Total │
 ├──────────────────┼───────┼───────┼────────┼────────┼────────┼───────┤
 │ Foundation (10)  │ 10/10 │ 10/10 │  9/10  │  9/10  │  8/10  │ 46/50 │
 │ Create (25)      │ 24/25 │ 23/25 │ 22/25  │ 20/25  │ 18/25  │107/125│
 │ Modify (35)      │ 34/35 │ 33/35 │ 30/35  │ 28/35  │ 27/35  │152/175│
 │ Query (15)       │ 15/15 │ 14/15 │ 14/15  │ 14/15  │ 13/15  │ 70/75 │
 │ Multi (15)       │ 13/15 │ 12/15 │ 10/15  │  9/15  │  8/15  │ 52/75 │
 │ Edge/Conv (20)   │ 18/20 │ 16/20 │ 14/20  │ 14/20  │ 12/20  │ 60/100│
 └──────────────────┴───────┴───────┴────────┴────────┴────────┴───────┘

 Failures by Root Cause:
  I1 (intent misclass):    3  ← needs system prompt examples
  P2 (wrong params):       5  ← needs post-processor rules
  E2 (material not found): 4  ← needs resolver improvement
  V1 (wrong structure):    7  ← needs training data
  Q2 (missing function):   5  ← needs training data

 New Failures (not in previous run):  2
 Fixed (failed before, pass now):     7
 Persistent (failed 3+ runs):         4  ← priority fixes

 Accuracy Trend:
  Run 001: 56.2%
  Run 002: 72.0%
  Run 003: 78.7%
  Run 004: 81.2%  ← current
```

### Accuracy History (accuracy_history.json)

```json
{
  "runs": [
    {"run": 1, "date": "2026-03-11", "score": 337, "max": 600, "pct": 56.2},
    {"run": 2, "date": "2026-03-11", "score": 432, "max": 600, "pct": 72.0},
    {"run": 3, "date": "2026-03-12", "score": 472, "max": 600, "pct": 78.7},
    {"run": 4, "date": "2026-03-12", "score": 487, "max": 600, "pct": 81.2}
  ]
}
```

### Known Failures Tracker (known_failures.json)

```json
{
  "failures": [
    {
      "test_id": "M.06",
      "prompt": "All enemies need 500 HP and 40 damage",
      "root_cause": "P2",
      "description": "Plan puts both variables in one batch_set_variable call instead of two",
      "first_seen_run": 1,
      "last_seen_run": 4,
      "consecutive_failures": 4,
      "priority": "HIGH",
      "fix_attempted": "system prompt example added run 3",
      "status": "OPEN"
    }
  ]
}
```

---

## RUNNING THE CYCLE

### Step 1: Run full suite
```powershell
python scripts/tests/accuracy/test_runner.py --run-all --fresh-level
```
This:
- Creates a fresh UE project (or resets the test level)
- Runs Phase 1 (Foundation) to build the base state
- Runs Phases 2-6 in order
- Saves results to `results/run_NNN_YYYYMMDD.json`
- Generates the report

### Step 2: Review failures
```powershell
python scripts/tests/accuracy/failure_classifier.py --run latest
```
This:
- Reads the latest run results
- Auto-classifies failures by root cause code
- Compares to previous run to find new failures and fixes
- Updates `known_failures.json`
- Prints priority fixes (persistent failures first)

### Step 3: Fix and retest
```powershell
# Retest only the failures from the latest run
python scripts/tests/accuracy/test_runner.py --retest-failures --run latest
```

### Step 4: Full regression
```powershell
# Full suite again to confirm fixes didn't break anything
python scripts/tests/accuracy/test_runner.py --run-all --fresh-level
```

---

## FIX CATEGORIES AND WHERE TO APPLY THEM

| Root Cause | Where to Fix | How |
|---|---|---|
| I1, I3 (intent) | `intent_server.py` CLASSIFY_PROMPT | Add few-shot examples |
| I1, I3 (intent) | `intent_server.py` hard overrides | Add regex pattern |
| P1, P2 (plan) | `intent_server.py` REFINE_PROMPT | Add format examples |
| P3 (bad command) | `intent_server.py` COMMAND_WHITELIST | Add alias |
| P4 (no dependency) | `ArcwrightGeneratorPanel.cpp` post-processor | Add injection rule |
| E1 (TCP error) | `CommandServer.cpp` handler | Fix C++ command logic |
| E2 (material) | `CommandServer.cpp` ResolveMaterialByName | Expand search paths |
| E3, E4 (not found) | `intent_server.py` discovery stage | Broaden search filters |
| E5 (params) | `intent_server.py` _postprocess_plan | Add normalization |
| V1, V2, Q1-Q3 | Training lessons | Create targeted correction data |

**Key principle:** Infrastructure fixes (I, P, E codes) are immediate. Quality fixes (V, Q codes) require training data and model retraining — batch these and train after accumulating enough examples.

---

## MILESTONES

| Score | Grade | Meaning |
|---|---|---|
| < 60% | F | Fundamentally broken |
| 60-70% | D | Major gaps, not usable |
| 70-80% | C | Works sometimes, frustrating |
| 80-85% | B | Usable with workarounds |
| 85-90% | B+ | Good, occasional failures |
| 90-95% | A | Production ready |
| 95%+ | A+ | Excellent, ship it |

**Current: ~89.6% (B+) on the 48-test suite**
**Target for launch: 90%+ on the 120-test suite**
**Target for v2: 95%+**

---

*Every run makes Arcwright smarter. Every failure is a lesson. The accuracy only goes up.*
