# Arcwright — Claude Code Project Context

> *The Bridge Between AI and Unreal Engine.*

> **Doc Version:** 22.0
> **Last Updated:** 2026-03-28
> **Owner:** Divinity Alpha
> **Repo:** github.com/Divinity-Alpha/Arcwright
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
C:\Arcwright\
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
├── ue_plugin/Arcwright/             # UE5 C++ plugin source
│   ├── Source/Arcwright/
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
- **Widgets:** create_widget_blueprint, add_widget_child, set_widget_property, get_widget_tree, set_widget_design_size
- **BehaviorTree:** create_behavior_tree, get_behavior_tree_info, setup_ai_for_pawn
- **DataTable:** create_data_table, add_data_table_row, get_data_table_rows
- **Batch ops:** batch_set_variable, batch_add_component, batch_delete_actors, batch_move_actors
- **Spawn patterns:** spawn_actor_grid, spawn_actor_circle, spawn_actor_line
- **Query:** find_blueprints, find_assets, list_project_assets, get_capabilities
- **Inspection:** get_blueprint_details, get_actor_properties, verify_all_blueprints
- **Diagnostics:** run_map_check, get_message_log, get_output_log, get_stats
- **PIE control:** play_in_editor, stop_play, is_playing, teleport_player, get_player_location, teleport_to_actor, get_player_view
- **29 DSL parsers:** Blueprint, BT, DT, Widget, AnimBP, Material, Dialogue, Quest, Sequence, GAS, Perception, Physics, Tags, Enhanced Input, Smart Objects, Sound, Replication, Control Rig, State Trees, Vehicles, World Partition, Landscape, Foliage, Mass Entity, Shader, ProcMesh, Paper2D, Composure, DMX

### BoreAndStroke UI Linear Color Palette

All station widget colors use sRGB→Linear conversion. Use these constants for all B&S UI work:

| Name | Linear RGBA | Hex |
|---|---|---|
| BG_DEEP | (R=0.0030,G=0.0037,B=0.0048,A=1.0) | #0A0C0F |
| BG_PANEL | (R=0.0060,G=0.0080,B=0.0116,A=1.0) | #12161C |
| BG_CARD | (R=0.0091,G=0.0123,B=0.0194,A=1.0) | #181D26 |
| BORDER | (R=0.0232,G=0.0296,B=0.0513,A=1.0) | #2A3040 |
| BORDER_ACT | (R=0.0423,G=0.0595,B=0.1170,A=1.0) | #3A4560 |
| ACCENT | (R=0.8070,G=0.3813,B=0.0176,A=1.0) | #E8A624 |
| GREEN | (R=0.0467,G=0.7157,B=0.2307,A=1.0) | #3DDC84 |
| YELLOW | (R=0.8714,G=0.5271,B=0.0513,A=1.0) | #F0C040 |
| RED | (R=0.7454,G=0.0513,B=0.0802,A=1.0) | #E04050 |
| TEXT | (R=0.6308,G=0.6584,B=0.7157,A=1.0) | #D0D4DC |
| DIM | (R=0.1620,G=0.1878,B=0.2462,A=1.0) | #707888 |
| BRIGHT | (R=0.8550,G=0.8714,B=0.9047,A=1.0) | #EEF0F4 |
| APPROVE_BG | (R=0.008,G=0.052,B=0.022,A=0.9) | — |
| CANCEL_BG | (R=0.073,G=0.006,B=0.009,A=0.8) | — |

### Default Event Nodes — Critical Rule

`create_blueprint` auto-creates: `node_0` (BeginPlay), `node_1` (ActorBeginOverlap), `node_2` (Tick). **Never recreate these in add_nodes_batch** — duplicates become "Event None" and never fire. Wire directly to `node_0`/`node_1`/`node_2`.

### Blueprint Actor Spawning — Critical Rule

If a Blueprint has logic (overlap events, variables, custom events), spawn as Blueprint instance:
```json
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Name.BP_Name_C", "label": "MyActor", "x": 0, "y": 0, "z": 50}}
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

All adapters backed up to `D:\ArcwrightBackup\models\`.

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
16. **All widget blueprints at 1920x1080 design size.** Use `set_widget_design_size` after `create_widget_blueprint` if `design_width`/`design_height` not passed to create.
17. **Always use `hex:` prefix for colors** in set_widget_property calls. Example: `hex:#E8A624`. Never pass raw sRGB floats as linear values — the plugin auto-converts `hex:` and `srgb:` to linear correctly.
18. **All widget visual layers protected via `protect_widget_layout`** after building. C++ can only access `txt_*` and `Btn_*` named widgets. Visual layer widgets are not variables and not hit-testable.

---

## Build & Launch Procedure

```bash
# Copy plugin
cp -r /c/Arcwright/ue_plugin/Arcwright/* /c/Junk/ArcwrightTestBed/Plugins/Arcwright/

# Build
"/c/Program Files/Epic Games/UE_5.7/Engine/Build/BatchFiles/Build.bat" \
  ArcwrightTestBedEditor Win64 Development "C:\Junk\ArcwrightTestBed\ArcwrightTestBed.uproject"

# Launch (MUST use -skipcompile and -graphicsadapter=0)
"/c/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor.exe" \
  "C:\Junk\ArcwrightTestBed\ArcwrightTestBed.uproject" \
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
| **Primary** | `C:\Arcwright\backups\` | Milestone backups |
| **Secondary** | `D:\ArcwrightBackup\` | Mirror of all models, datasets, lessons, results |
| **Git** | github.com/Divinity-Alpha/Arcwright | Scripts, docs (not models/datasets) |

**After every training:** `cp -r models/<new> /d/ArcwrightBackup/models/` and verify file sizes match.

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
13. **FAB requires PlatformAllowList in every .uplugin module**, copyright headers on all source files, no Binaries/Intermediate/Saved in submission, MarketplaceURL in .uplugin
14. **FAB Python folder structure** — `Content/Python/Lib/site-packages/` must exist even if no third-party packages are bundled. RunUAT leaves `Intermediate/` in packaged output — always remove it before zipping.
15. **FAB copyright headers required on ALL source files** including `.cs` (Build.cs) — not just `.cpp` and `.h`. Check every file type in `Source/`.
16. **FAB ships source-only** — no pre-compiled Binaries folder. Customers compile on first load in UE5. Exclude Binaries/, Intermediate/, Saved/, Build/ from submission zip.
17. **Website sidebar layout rules** — Sidebars on help.html and docs.html must follow these exact CSS rules or links collapse into a horizontal mess instead of a vertical list:
    - Layout container: `display:grid` (NOT `display:flex`), NO `align-items:start` on the container — use `align-self:start` on each child instead
    - Sidebar div: `align-self:start` + `position:sticky` + `display:flex` + `flex-direction:column` (ALL FOUR required)
    - Sidebar section: `display:flex` + `flex-direction:column` (explicit vertical)
    - Sidebar link: `display:block` + `width:100%` (explicit block, not inline)
    - Sidebar title: `display:block` (explicit)
    - Use `<div class="help-sidebar">` NOT `<nav class="help-sidebar">` — browsers apply default flex/inline styling to nav elements that breaks the vertical layout
    - Every sidebar-section must be a properly closed `<div>` — orphaned links outside their section div break the layout
    - **Common mistakes causing horizontal packing:** `align-items:start` on grid parent instead of `align-self:start` on children, using `<nav>` tag, missing `flex-direction:column` on sidebar or sidebar-section, unclosed sidebar-section divs
18. **Strict includes required for FAB submission** — FAB's build server compiles with `-StrictIncludes` and without unity builds. Local builds hide missing includes through unity build merging. Before any FAB submission always run: (1) Add `bUseUnity = false` to Build.cs temporarily, (2) clean intermediates, (3) `Build.bat` with `-DisableUnity -NoHotReload`, (4) `RunUAT BuildPlugin` with `-StrictIncludes`, (5) must show zero errors, (6) remove `bUseUnity = false` before final package. Files commonly affected: any `.h` or `.cpp` that uses `FJsonObject`, `FJsonValue`, `FAssetData`, `UEdGraphPin`, `EMaterialDomain` values, `ENGINE_MAJOR_VERSION`, or any UE type without explicitly including its header. These all get pulled in transitively by unity builds but fail under strict compilation.
19. **setup_default_lighting missing from v1.0.2** — every new level session needs lighting. Workaround: create BP_Lighting with SkyLight + DirectionalLight components. Fix: v1.0.3 command.
20. **take_screenshot captures editor viewport not PIE** — always wait 5 seconds after `play_in_editor` before any screenshot. Fix: v1.0.3 PIE viewport detection.
21. **Fresh install test required before every FAB release** — test on blank project with zero prior setup. Lighting and PIE screenshots must both pass. No exceptions.
22. **Workarounds are always future commands** — every time a workaround is used, log it as a future Arcwright command requirement in `knowledge/skills/`.
23. **The knowledge system IS the product roadmap** — command failures and workarounds directly become the v1.0.3, v1.0.4 feature lists.
24. **Null check every asset load (F008)** — every `LoadObject` call must check for null and return a graceful error response. Never let a missing asset reach a dereference. Pattern: `UObject* Asset = LoadObject<...>(nullptr, *Path); if (!Asset) return FCommandResult::Error("Asset not found: " + Path);`
25. **Test suite before every FAB submission** — run `python arcwright_test_suite.py --mode all`. Regression must be 36/36. Stress must be 0 crashes, 0 timeouts. Discovery warnings acceptable, failures are not. Gate: 95%+ pass rate before packaging.
26. **Accept multiple param names for actor references** — commands that accept actor references must accept: `actor_name`, `label`, `name`, `actor_label`. Never reject a valid actor reference due to param name mismatch.
27. **Test project pollution** — keep test project (ArcwrightTestBed) clean. Never use it for development or demos. Maintain separate ArcwrightDemo project for game builds and recordings. Content pollution causes false discovery failures that look like command bugs but are environment issues.

---

## Knowledge Capture Protocol

Every Claude Code session must log to `C:\Arcwright\knowledge\`:

**START:** `python C:\Arcwright\knowledge\capture_session.py [session_name]`

**DURING — log every:**
- Command failure (command, params, exact error)
- Workaround used (intended, actual, why)
- Problem encountered (description, UE error)
- Problem resolved (root cause, resolution, lesson)

**END:**
- Save session log
- Run `extract_lessons.py`
- Create `SKILL_XXX.md` for any new lessons
- Update CLAUDE.md if new strategic rules discovered

**WEEKLY:**
- Run `generate_report.py`
- Review output for CLAUDE.md updates

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
| 13.1 | 2026-03-24 | Added set_widget_design_size command, rule 16 (1920x1080 default), create_widget_blueprint now defaults to 1920x1080. |
| 13.2 | 2026-03-24 | Added BoreAndStroke linear color constants (sRGB->Linear). Permanent UI color palette for all station widgets. |
| 13.3 | 2026-03-24 | ParseLinearColor now supports `hex:#RRGGBB` and `srgb:(R=,G=,B=,A=)` prefixes with auto sRGB→linear conversion. Rule 17. |
| 13.4 | 2026-03-24 | Root CanvasPanel auto-clips. protect_widget_layout command. Rule 18. |
| 13.5 | 2026-03-24 | Content paths /Game/Arcwright/ → /Game/Arcwright/. HTML→Arcwright translator. Display string rename (202 replacements across 8 files). |
| 13.6 | 2026-03-24 | Plugin v1.0.1 release. hex:/srgb: colors, set_widget_design_size, protect_widget_layout, auto-clip root canvas, content path rename. |
| 14.0 | 2026-03-25 | FAB resubmission: PlatformAllowList, MarketplaceURL, copyright headers, clean package (Arcwright_1.0.2_r2.zip). |
| 15.0 | 2026-03-26 | FAB r3: Python folder at Content/Python/Lib/site-packages/, confirmed Niagara+EnhancedInput deps required, Intermediate cleanup, package Arcwright_1.0.2_r3.zip. |
| 16.0 | 2026-03-26 | FAB r4: Build.cs copyright header fix. All source file types (.cpp, .h, .cs) now have headers. Package Arcwright_1.0.2_r4.zip. |
| 17.0 | 2026-03-27 | FAB r5: Source-only submission — Binaries excluded. Customers compile from source. Package Arcwright_1.0.2_r5.zip (223 KB). |
| 18.0 | 2026-03-27 | Added website sidebar layout rules to Key Lessons (lesson 17). |
| 19.0 | 2026-03-27 | FAB r6: strict include fixes across 9 source files. Added lesson 18 (strict includes verification protocol). |
| 20.0 | 2026-03-28 | Knowledge capture system deployed. 5 skill files, session logger, lesson extractor, weekly report generator. Lessons 19-23 added. Knowledge capture protocol section. |
| 21.0 | 2026-03-28 | v1.0.3 release. F008/F007/F009 fixed. Regression 36/36. Stress 26/26 (0 crashes). Test suite mandatory before every release. Lessons 24-26 added. |
| 22.0 | 2026-03-28 | v1.0.3 final. All F001-F008 FIXED. M001/M002/M004/M005 ADDED. Lesson 27 (test pollution). SKILL_006 added. Run 4 results. Docs updated for shipped fixes. |
