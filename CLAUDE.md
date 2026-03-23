# Arcwright — Claude Code Project Context

> *The Bridge Between AI and Unreal Engine.*

> **Doc Version:** 13.0
> **Last Updated:** 2026-03-22
> **Owner:** Divinity Alpha
> **Repo:** github.com/Divinity-Alpha/BlueprintLLM
> **Product Name:** Arcwright

---

## What This Is

**Arcwright** is a UE5 plugin that gives any AI assistant (Claude, GPT, Cursor, Windsurf) the power to create Blueprints, build levels, and modify assets inside the running editor through **280 TCP commands** and **288 MCP tools**.

**Pricing:** $49.99 one-time purchase via FAB Marketplace. No subscription, no API keys, no remote validation. All commands available to all purchasers.

**Architecture:**
```
AI assistant plans the build → calls Arcwright MCP/TCP commands → Arcwright executes inside UE5 Editor
```

The core innovation is the **teaching loop** — train → examine → grade → create lesson → retrain — producing specialized LoRA adapters for Blueprint, Behavior Tree, DataTable, and Widget DSL generation.

---

## Hardware

| Component | Details |
|---|---|
| **GPU 0 (cuda:0)** | NVIDIA RTX PRO 6000 Blackwell, 96GB VRAM — ML training & inference |
| **GPU 1 (cuda:1)** | NVIDIA GeForce RTX 5070 Ti, 16GB VRAM — Display + UE Editor |
| **RAM** | 64GB DDR5 |
| **CUDA** | 13.1 |

**Critical:** PyTorch cuda:0 = PRO 6000. nvidia-smi GPU 0 = 5070 Ti (reversed). Always use 8-bit quantization (4-bit broken on Blackwell sm_120). UE Editor forced to 5070 Ti via `-graphicsadapter=0`.

---

## Session Startup Protocol

1. Print: `[SESSION START] CLAUDE.md v{version} loaded. Autonomous mode active.`
2. Check `logs/pipeline_heartbeat` age for any active training
3. **Check Claude Bridge for pending instructions:** `python scripts/claude_bridge.py --check --project bore-and-stroke`
   - Bridge repo: `C:\Projects\claude-bridge\` (multi-project: bore-and-stroke, arcwright)
   - If pending instructions exist, execute them in priority order before other work
4. Resume the most logical next step **without asking permission**
5. UE launch: `scripts/launch_ue.bat` (forces 5070 Ti). Start crash reporter killer loop after launch.
6. Before training: `python scripts/pre_training_check.py` to clear GPU

**Autonomous operations — act immediately, no permission needed:**
Launch/close/restart UE, kill processes, run training/exams/backups/tests.

**Stop and notify only for:** Unrecoverable data deletion, Golden Config deviation, 3x failure, genuine irreversible fork.

---

## Project Structure

```
C:\BlueprintLLM\
├── scripts/                    # Pipeline scripts (01-20+), DSL parsers, MCP/TCP
│   ├── 04_train_blueprint_lora.py      # Training script
│   ├── 07_inference.py                 # Interactive inference
│   ├── 09_evaluate_model.py            # Evaluation
│   ├── 11_pipeline_orchestrator.py     # Autonomous pipeline
│   ├── 12_run_exam.py                  # Exam runner
│   ├── 13_lesson_to_training.py        # Lesson integration
│   ├── mcp_client/                     # TCP client library + tests
│   ├── mcp_server/                     # MCP server (289 tools)
│   ├── dsl_parser/                     # Blueprint DSL parser
│   ├── bt_parser/                      # Behavior Tree DSL parser
│   ├── dt_parser/                      # DataTable DSL parser
│   ├── auto_diagnose.py                # Auto-scan + fix UE issues
│   ├── check_and_confirm.py            # Verification protocol
│   ├── ARCWRIGHT_AI_GUIDE.md           # AI best practices (200+ UFunction paths)
│   └── CHECK_AND_CONFIRM.md            # Check & Confirm SOP
├── ue_plugin/BlueprintLLM/             # UE5 C++ plugin source
│   ├── Source/BlueprintLLM/
│   │   ├── Private/CommandServer.cpp   # 277 TCP commands (~16K lines)
│   │   ├── Private/BlueprintBuilder.cpp
│   │   ├── Private/BehaviorTreeBuilder.cpp
│   │   ├── Private/DataTableBuilder.cpp
│   │   └── Private/ArcwrightDashboardPanel.cpp
│   └── Public/                         # Headers
├── datasets/                           # Training JSONL files
├── lessons/                            # Teaching loop lessons (23 BP, 4 BT, 5 DT)
├── models/                             # Trained LoRA adapters
├── templates/                          # 16 game pattern templates
├── tests/                              # Test scripts
└── dashboard/                          # HTML dashboards
```

---

## TCP Command Server (port 13377)

Newline-delimited JSON protocol. Background thread I/O, game thread dispatch via AsyncTask.

```json
{"command": "health_check", "params": {}}
→ {"status": "ok", "data": {"server": "Arcwright", "version": "1.0"}}
```

**277 TCP commands** across categories:
- **Blueprint CRUD:** create_blueprint, add_nodes_batch, add_connections_batch, compile_blueprint, validate_blueprint, delete_blueprint, get_blueprint_details, import_from_ir
- **Actor/Level:** spawn_actor_at, find_actors, delete_actor, set_actor_transform, get_level_info, save_all, save_level
- **Components:** add_component (11 types), get_components, remove_component, set_component_property
- **Materials:** create_simple_material, apply_material, set_actor_material, batch_apply_material
- **Widgets:** create_widget_blueprint, add_widget_child, set_widget_property, get_widget_tree
- **BehaviorTree:** create_behavior_tree, get_behavior_tree_info, setup_ai_for_pawn
- **DataTable:** create_data_table, add_data_table_row, get_data_table_rows
- **Batch ops:** batch_set_variable, batch_add_component, batch_delete_actors, batch_move_actors
- **Spawn patterns:** spawn_actor_grid, spawn_actor_circle, spawn_actor_line
- **Query:** find_blueprints, find_assets, list_project_assets, get_capabilities
- **Inspection:** get_blueprint_details, get_actor_properties, verify_all_blueprints
- **Diagnostics:** run_map_check, get_message_log, get_output_log, get_stats
- **PIE control:** play_in_editor, stop_play, is_playing, teleport_player, get_player_location, teleport_to_actor, get_player_view
- **29 DSL parsers:** Blueprint, BT, DT, Widget, AnimBP, Material, Dialogue, Quest, Sequence, GAS, Perception, Physics, Tags, Enhanced Input, Smart Objects, Sound, Replication, Control Rig, State Trees, Vehicles, World Partition, Landscape, Foliage, Mass Entity, Shader, ProcMesh, Paper2D, Composure, DMX

### Default Event Nodes — Critical Rule

`create_blueprint` auto-creates: `node_0` (BeginPlay), `node_1` (ActorBeginOverlap), `node_2` (Tick). **Never recreate these in add_nodes_batch** — duplicates become "Event None" and never fire. Wire directly to `node_0`/`node_1`/`node_2`.

### Blueprint Actor Spawning — Critical Rule

If a Blueprint has logic (overlap events, variables, custom events), spawn as Blueprint instance:
```json
{"command": "spawn_actor_at", "params": {"class": "/Game/BlueprintLLM/Generated/BP_Name.BP_Name_C", "label": "MyActor", "x": 0, "y": 0, "z": 50}}
```
NOT as a plain mesh (which runs no Blueprint logic).

---

## MCP Server (289 tools)

Stdio JSON-RPC server at `scripts/mcp_server/server.py`. Wraps TCP commands + adds compound workflows.

**Claude Desktop config** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{"mcpServers": {"arcwright": {"command": "python", "args": ["scripts/mcp_server/server.py"]}}}
```

---

## Check & Confirm Protocol

Every build action follows: **Action → Verify → Confirm**

```python
from scripts.check_and_confirm import CheckAndConfirm
cc = CheckAndConfirm()
cc.create_and_verify_blueprint("BP_MyActor", nodes, connections)
cc.verify_all_blueprints()
cc.verify_level()
cc.play_test()  # PIE + screenshot + log check
cc.report()
```

## Auto-Diagnose

```python
python scripts/auto_diagnose.py
```
Scans: `run_map_check`, `verify_all_blueprints`, `get_message_log`. Auto-fixes: duplicate SkyLights/DirectionalLights, missing PlayerStart.

---

## Training Configuration (Golden Config)

```
base_model: meta-llama/Meta-Llama-3.1-70B
epochs: 3                    # NEVER 2 (causes regression)
learning_rate: 0.0002
batch_size: 1
gradient_accumulation_steps: 4  # NEVER 8 (caused v7 regression)
lora_rank: 32
lora_alpha: 64
max_seq_length: 1024
quantization: 8bit (load_in_8bit=True)
stall_detection: heartbeat (1800s threshold, no fixed timeout)
```

**Continuation mode:** `--resume_from <prev_adapter>`, lr=5e-5, 2 epochs.

### Current Production Adapters

| Adapter | Domain | Syntax | Similarity | Date |
|---|---|---|---|---|
| blueprint-lora-v14 | Blueprint | 97.8% | 96.0% | 2026-03-16 |
| bt-lora-v3 | BehaviorTree | 98.3% | 92.0% | 2026-03-09 |
| dt-lora-v5 | DataTable | 100% | 87.2% | 2026-03-16 |
| widget-lora-v4 | Widget | 100% | — | 2026-03-19 |

All adapters backed up to `D:\BlueprintLLMBackup\models\`.

---

## Strategic Rules

1. **3 epochs always.** 2 causes regressions (proven v5→v6).
2. **Include replay buffer** when adding lessons — prevents catastrophic forgetting.
3. **Full exam suite after every training** — regressions hide in untested lessons.
4. **8-bit quantization only** on Blackwell hardware.
5. **gradient_accumulation_steps=4** — v7 regressed at 8.
6. **Pin mismatches go in the plugin, not the model.**
7. **Delete before re-import** — overwriting crashes.
8. **CLAUDE.md is source of truth** — pipeline_config.json must match.
9. **Heartbeat-based stall detection** — NEVER kill based on stdout (readline blocks on \r).
10. **UE on 5070 Ti** via `-graphicsadapter=0`. PRO 6000 reserved for training.
11. **Back up models to D: immediately** after every training/exam run.
12. **Never recreate player controls with Blueprint nodes** — use `setup_game_base.py`.
13. **Claude Code operates autonomously** — no permission needed for routine ops.
14. **Don't duplicate default event nodes** — wire to node_0/node_1/node_2 instead.
15. **Spawn Blueprint actors with class path** — plain mesh actors have no Blueprint logic.

---

## Build & Launch Procedure

```bash
# Copy plugin
cp -r /c/BlueprintLLM/ue_plugin/BlueprintLLM/* /c/Junk/BlueprintLLMTest/Plugins/BlueprintLLM/

# Build
"/c/Program Files/Epic Games/UE_5.7/Engine/Build/BatchFiles/Build.bat" \
  BlueprintLLMTestEditor Win64 Development "C:\Junk\BlueprintLLMTest\BlueprintLLMTest.uproject"

# Launch (MUST use -skipcompile and -graphicsadapter=0)
"/c/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor.exe" \
  "C:\Junk\BlueprintLLMTest\BlueprintLLMTest.uproject" \
  -skipcompile -graphicsadapter=0 -nosplash -unattended -nopause &

# Kill crash reporter popups
powershell -Command "while (\$true) { Get-Process -Name 'CrashReportClient*' -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 10 }" &

# Verify
python scripts/mcp_client/verify.py
```

**Graceful shutdown:** `quit_editor` TCP command (saves first). Fallback: `taskkill //F //IM "UnrealEditor.exe"`.

---

## Backup System

| Tier | Location | What |
|---|---|---|
| **Primary** | `C:\BlueprintLLM\backups\` | Milestone backups |
| **Secondary** | `D:\BlueprintLLMBackup\` | Mirror of all models, datasets, lessons, results |
| **Git** | github.com/Divinity-Alpha/BlueprintLLM | Scripts, docs (not models/datasets) |

**After every training:** `cp -r models/<new> /d/BlueprintLLMBackup/models/` and verify file sizes match.

---

## Key Lessons Learned

1. **Default events are auto-created** — creating duplicates via add_nodes_batch produces "Event None" that never fires
2. **Blueprint actors vs plain meshes** — spawn with `class` param for Blueprint logic to run
3. **SCS OverrideMaterials don't persist** — use `set_actor_material` on placed actors
4. **FScreenshotRequest doesn't capture UMG widgets** — only captures 3D viewport
5. **Widget API param names:** `widget_blueprint`, `widget_type`, `widget_name` (child name), `parent_name`
6. **set_node_param uses `pin_name`/`value`** — not `param_name`/`param_value`
7. **SavePackage crashes on partial-loaded packages** — use SafeSavePackage.h (FullyLoad first)
8. **World Partition stores actors externally** — save_all explicitly saves `__ExternalActors__` packages
9. **TCP partial writes** on Windows — SendResponse loops until all bytes sent, 256KB buffers
10. **70B first training step takes ~96 min** — CUDA JIT + cuBLAS autotuning, normal
11. **UE Editor on wrong GPU = 245x training slowdown** — always use `-graphicsadapter=0`
12. **create_simple_material works with Substrate** — create_material_instance does NOT

---

## CLAUDE.md Update Policy

**Update immediately when:** config changes, something breaks, new strategic rule, new capability.
**Update after training cycle:** version history, accuracy numbers.
**Don't update for:** brainstorming, debugging details already in grading reports.

**When updating, increment version number and add changelog entry.**

### Changelog (Recent)
| Version | Date | Changes |
|---|---|---|
| 12.0 | 2026-03-21 | Product pivot: pure bridge plugin. Removed RunPod/Zuplo/tiers. $49.99 one-time. |
| 13.0 | 2026-03-22 | Condensed CLAUDE.md (2302→490 lines). Added Check & Confirm, auto-diagnose, default event rules, Blueprint actor spawning rules. |
