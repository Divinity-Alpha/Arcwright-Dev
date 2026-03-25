# CLAUDE.md v8.1 Update Patch

> **Instructions:** Apply these changes to the existing CLAUDE.md v8.0.
> Each section below shows what to REPLACE and what to REPLACE IT WITH.

---

## CHANGE 1: Update version header

REPLACE line 3-4:
```
> **Doc Version:** 8.0
> **Last Updated:** 2026-03-13
```

WITH:
```
> **Doc Version:** 8.1
> **Last Updated:** 2026-03-14
```

---

## CHANGE 2: Add changelog entry at the top of the changelog table

ADD after the last changelog entry (8.0):
```
| 8.1 | 2026-03-14 | **Product repositioning: Arcwright is "The Bridge Between AI and Unreal Engine."** Removed human-facing Generator Panel / intent server from deployment scope. Product is now AI-first: any AI assistant (Claude, GPT, Cursor, Windsurf, custom agents) connects via MCP/TCP and drives UE5 directly. One plugin, tier-gated features: Connect (free, no account, all 81 TCP + 90 MCP) → Community ($0 account, 5 gen/day) → Pro ($29/mo, 1000/mo) → Studio ($99/mo). Updated roadmap to remove human interface milestones. Added: Pre-Launch Priority Stack (7 items), Next TCP Commands (10 planned), MCP Tool Description Quality initiative, AI Workflow Test Suite, Telemetry system design, Capability Matrix (transparent tier system). Blueprint complexity training: L19-L21 added (connection patterns, compositional mid-tier, complex systems). Node count guidance removed ("15-20 nodes" ceiling eliminated). v13 training launched with 21 lessons, 389 prompts. |
```

---

## CHANGE 3: Replace "What This Project Is" section

REPLACE:
```
## What This Project Is

**Arcwright** (formerly Arcwright) is a self-improving AI system that trains LLMs to generate **validated, structurally correct** Unreal Engine 5 Blueprint DSL from natural language descriptions. The core innovation is the **teaching loop** — a closed-loop cycle of train → examine → grade → create lesson → retrain that targets specific weaknesses each iteration.

The long-term vision is a platform that trains validated AI models for ANY structured language (not just Blueprints). Blueprints are the proof-of-concept. The teaching loop infrastructure is language-agnostic.

> **Tagline:** *Architect Your Game from Language.*
```

WITH:
```
## What This Project Is

**Arcwright** is the bridge between AI assistants and Unreal Engine 5. It's a UE5 plugin that gives any AI — Claude, GPT, Cursor, Windsurf, or custom agents — the power to create Blueprints, build levels, and modify assets inside the running editor through 81 TCP commands and 90 MCP tools.

The product is **AI-first**: there is no human-facing natural language interface in the deployed product. Users connect their own AI assistant to Arcwright via MCP or TCP protocol. The AI handles intent classification, planning, retries, and orchestration. Arcwright handles execution — reliably translating each command into real UE5 editor actions.

The core innovation is the **teaching loop** — a closed-loop cycle of train → examine → grade → create lesson → retrain that produces specialized LoRA adapters for Blueprint, Behavior Tree, and Data Table DSL generation. These adapters power the `generate_dsl` command that AI assistants call through Arcwright.

> **Tagline:** *The Bridge Between AI and Unreal Engine.*

### Product Architecture

```
User describes game → Their AI assistant plans the build
    → AI calls Arcwright MCP tools (90 tools) or TCP commands (81 commands)
    → Arcwright executes inside UE5 Editor
    → Blueprints created, actors spawned, materials applied, levels built
    → AI queries results via find_actors/find_blueprints/get_level_info
    → AI iterates based on results
```

### What Arcwright Is NOT
- NOT a standalone AI — it requires an external AI assistant to drive it
- NOT a human-facing chat interface — the Generator Panel is a development/testing tool only
- NOT locked to one AI provider — any MCP-compatible or TCP-capable client works
- NOT a replacement for UE knowledge — the AI assistant needs to understand game development concepts

### Product Tiers (One Plugin, Tier-Gated Features)

| Tier | Price | Account | What's Included |
|---|---|---|---|
| **Connect** | Free forever | None needed | All 81 TCP commands, all 90 MCP tools, Blender addon, 16 templates, 4 game bases, full docs |
| **Community** | $0/mo | Free account | Everything in Connect + Generator Panel + 5 AI generations/day (Blueprint only) |
| **Pro** | $29/mo | Paid | Everything + 1,000 generations/month, all 3 domains (BP+BT+DT), 12 languages, API access |
| **Studio** | $99/mo | Paid | Everything + 5,000 gen/month, custom templates, 5 team seats, priority queue, telemetry |

Connect is the viral growth engine — free, no account, no limits on commands. Paid tiers unlock hosted AI generation via the `generate_dsl` endpoint on RunPod.

### Compatible AI Assistants (Tested or Expected)

| AI Assistant | Connection Method | Status |
|---|---|---|
| Claude Desktop | MCP (native) | ✅ Proven — primary development workflow |
| Claude Code | TCP (direct) | ✅ Proven — built Temple Escape demo |
| Cursor | MCP | Expected to work |
| Windsurf | MCP | Expected to work |
| ChatGPT (Custom GPT) | TCP via Python client | Expected to work |
| Cline | MCP | Expected to work |
| Custom agents | TCP or MCP | Any language, any framework |
```

---

## CHANGE 4: Replace Product Roadmap section

REPLACE the entire "Product Roadmap (Summary)" section AND "Grand Vision" section (from "## Product Roadmap" through the end of "Phase 5: Community Ecosystem" compliance checker architecture) WITH:

```
## Product Roadmap

### Pre-Launch Priority Stack (in order)

| # | Priority | Description | Status |
|---|---|---|---|
| 1 | **Blueprint complexity training** | V13 with L19-L21 (connection patterns, compositional mid-tier, complex systems 25-50 nodes). Then L22 (error correction), L23 (40-60 node tier). Tier-based exam scoring. | V13 training in progress |
| 2 | **Expand TCP/MCP commands to ~100** | 10 new commands: set_collision_preset, get_blueprint_details, set_camera_properties, create_input_action, bind_input_to_blueprint, set_collision_shape, create_nav_mesh_bounds, set_audio_properties, set_actor_tags, get_actor_properties | Planned |
| 3 | **MCP tool description quality** | Enrich all 90 tool descriptions with parameter explanations, valid values, examples, usage notes, return value docs. Free accuracy improvement — AI reads these at connection time. | Planned |
| 4 | **Error messages + discovery commands** | Better error messages ("Material not found. Available: [list]"). New commands: list_available_materials, list_available_blueprints, get_last_error, validate_before_execute. | Planned |
| 5 | **AI workflow test suite** | Tests that mimic how Claude Desktop actually uses tools: query → plan → execute → verify → iterate. Not human-prompt tests. | Planned |
| 6 | **Documentation site** | arcwright.app/docs — command reference, cookbooks, MCP setup guides for each AI client, troubleshooting. The AI reads this. | Planned |
| 7 | **Telemetry pipeline** | Opt-in usage capture: what commands AIs call, what fails, what patterns emerge. Feeds the training flywheel. | Post-launch |

### Post-Launch Roadmap

| Phase | Timeline | Goal |
|---|---|---|
| **Launch** | Now | Ship Connect (free) on FAB. MCP + TCP + 81 commands + 90 tools. |
| **Expand Commands** | Month 1-2 | Reach ~100 TCP commands, ~110 MCP tools. Close the top capability gaps. |
| **Blueprint Scaling** | Months 1-3 | V14-V16 training targeting 40-60 node Blueprints at 90%+ accuracy. |
| **API Launch** | Month 2-3 | RunPod + Zuplo. Paid tiers go live. generate_dsl available via API. |
| **Telemetry Flywheel** | Month 3+ | Real user data → training improvements → better models → more users. |
| **DSL Open Standard** | Months 4-8 | Publish DSL spec, compliance checker API, enable community tools. |
| **Animation Blueprint DSL** | Months 6-12 | Fourth domain: Animation Blueprints from natural language. |
| **Platform** | Months 12-20 | Teaching loop as a service for other structured languages. |

### Removed from Scope

The following were previously planned but are removed from the deployment scope:

- **Generator Panel as primary user interface** — The panel remains as a development/testing tool but is not the marketed product experience. The primary workflow is AI assistant → MCP/TCP → Arcwright.
- **Intent classification system (intent_server.py) as user-facing feature** — The multi-stage LLM intent classification was designed for human natural language input. Since the product is AI-first, the external AI handles intent and sends specific commands. The intent server may still be useful internally for the Generator Panel in Community/Pro tiers.
- **Human-facing "describe your game" workflow** — The tagline "Describe your game. Watch it build itself" is replaced with "The Bridge Between AI and Unreal Engine." Arcwright is infrastructure, not a standalone AI.
- **Hard override system for human input patterns** — The regex-based hard overrides in intent_server.py for catching "make enemies faster" etc. are less relevant when the AI sends explicit commands like batch_set_variable.

### What This Simplifies

Removing the human interface as the primary product path eliminates:
- Dependency on the 70B intent classification model for user-facing reliability
- The accuracy gap between "what users say" and "what the system understands"
- The MODIFY/MULTI classification problem (87.8% → needs 95%+ for production)
- Hard override maintenance for every new phrasing pattern
- The need for a hosted LLM for every free-tier user interaction

The AI assistant handles all natural language understanding. Arcwright just needs to execute commands reliably — which it already does at near 100%.

## Next TCP Commands (Planned)

These 10 commands close the biggest gaps an AI assistant would encounter:

| Command | Purpose | Parameters | Priority |
|---|---|---|---|
| `set_collision_preset` | Set collision channel/response on actor or component | actor/component, preset_name or custom channels | High |
| `get_blueprint_details` | Inspect a Blueprint's variables, nodes, events, components | blueprint_name → JSON with full structure | High |
| `set_camera_properties` | Configure spring arm length, FOV, rotation constraints | actor, fov, arm_length, pitch_min, pitch_max | High |
| `create_input_action` | Create Enhanced Input Action asset | action_name, value_type (bool/axis1d/axis2d/axis3d) | High |
| `bind_input_to_blueprint` | Wire an input action to a Blueprint event | blueprint, action, event_name | High |
| `set_collision_shape` | Resize collision box/sphere/capsule on placed actors | actor, shape_type, extents/radius/half_height | Medium |
| `create_nav_mesh_bounds` | Create NavMeshBoundsVolume for AI pathfinding | location, extents | Medium |
| `set_audio_properties` | Configure attenuation, spatialization, volume | actor/component, attenuation_radius, inner_radius | Medium |
| `set_actor_tags` | Set tags on actors (used for batch filtering) | actor_label, tags[] | Medium |
| `get_actor_properties` | Read current property values from a placed actor | actor_label → JSON with transform, variables, components | Medium |

## MCP Tool Description Quality Initiative

Current MCP tool descriptions are functional but minimal. AI assistants read these descriptions to decide which tool to use and what parameters to pass. Better descriptions = better AI decisions = better user experience.

**Standard for each tool description:**
```python
@tool("create_blueprint")
async def create_blueprint(name: str, parent_class: str = "Actor", variables: list = None):
    """Create a new Blueprint asset in the UE5 Content Browser.

    Creates a compiled Blueprint class that can be spawned into levels.

    Parameters:
        name: Blueprint name (e.g. "BP_HealthPickup"). Will be created at /Game/Arcwright/Generated/{name}
        parent_class: UE parent class. Common values: "Actor" (default), "Character", "Pawn",
                      "PlayerController", "GameModeBase", "AIController"
        variables: Optional list of variables to add. Each: {"name": "Health", "type": "Float", "default": "100.0"}
                   Supported types: Bool, Int, Float, String, Vector, Rotator, Name

    Returns:
        {"status": "ok", "blueprint_path": "/Game/Arcwright/Generated/BP_HealthPickup", "compiled": true}

    Example usage:
        create_blueprint("BP_Enemy", "Character", [{"name": "Health", "type": "Float", "default": "100"}])

    Notes:
        - Blueprint is auto-compiled after creation
        - If a Blueprint with the same name exists, it will be deleted and recreated
        - Use import_from_ir for complex Blueprints with node graphs and connections
        - Use spawn_actor_at to place instances in the level after creation
    """
```

**Apply to all 90 tools. Priority: most-used tools first (create_blueprint, spawn_actor_at, find_actors, apply_material, batch_set_variable).**

## Telemetry System Design

Opt-in telemetry to learn from real AI usage patterns. See `/mnt/user-data/outputs/Arcwright_Telemetry_System.md` for full design.

**Per request captured:** command name, parameters, success/failure, error message, execution time, AI client identifier.
**Weekly report:** top 20 command patterns, top 10 failures, new patterns discovered.
**Training flywheel:** most-requested patterns that fail → create targeted training lessons → retrain → improved accuracy.

## Capability Matrix

Transparent capability tiers communicated to users. See `/mnt/user-data/outputs/Arcwright_Capability_Matrix.md` for full matrix.

**Two tiers for AI-driven workflow:**
- **Single Command (green):** Every individual TCP command is deterministic and reliable. create_blueprint, spawn_actor_at, batch_apply_material — all near 100%.
- **AI Orchestrated (purple):** Complex systems require the AI to chain multiple reliable commands. The intelligence is in the AI's sequencing, not Arcwright's execution.

There is no "unreliable" tier because every command works. Complexity comes from the AI's planning, which improves as AI assistants improve.

## Accuracy Test Suites

### 120-Command Suite (accuracy/test_runner.py)
Full end-to-end test: 120 commands across 6 phases (Foundation, Create, Modify, Query, Multi, Edge/Vague).
5-dimensional scoring: Intent, Plan, Execute, Verify, Quality.
Current best: Run #006 = 421/600 (70.2%).
**Note:** This suite tests the intent_server.py human-facing pipeline, which is no longer the primary product path. Retained for regression testing the Generator Panel.

### AI Workflow Test Suite (planned)
Tests that mimic how an AI assistant actually uses Arcwright:
- AI calls get_level_info → receives JSON → decides what to create
- AI calls create_blueprint with DSL → receives success/error → handles error if needed
- AI calls spawn_actor_at → receives actor label → uses it in next call
- AI calls find_actors → receives list → calls batch_set_variable on results
- Full session: 50+ chained calls building a complete level

This is the test suite that matters for the shipped product.
```

---

## CHANGE 5: Update the Arcwright Generator Panel section header

The Generator Panel section should note it is now a development/testing tool:

ADD at the top of the "### Arcwright Generator Panel" section (around line 1068):
```
> **Note (v8.1):** The Generator Panel is retained as a development and testing tool, and is available to Community/Pro/Studio tier users. However, it is NOT the primary marketed product experience. The primary workflow is: user's AI assistant → MCP/TCP → Arcwright commands → UE5. The intent_server.py and multi-stage classification system support the Generator Panel but are not part of the Connect (free) tier.
```

---

## CHANGE 6: Update the tagline in the hero-logo SVG reference

Anywhere the old tagline "ARCHITECT YOUR GAME FROM LANGUAGE" appears in documentation, update to:
```
THE BRIDGE BETWEEN AI AND UNREAL ENGINE
```

---

END OF PATCH
