# SKILL 001 — Level Lighting Setup
**Category:** Scene Setup
**Status:** FIXED in v1.0.4 — Movable mobility on all lights
**Reliability:** High
**Discovered:** NeonBreach session

## v1.0.4 Fix
```json
{"command": "setup_default_lighting", "params": {"scene_type": "outdoor"}}
```
Now sets Movable mobility automatically. Works on blank levels in PIE.
After lighting, also run:
```json
{"command": "run_console_command", "params": {"command": "r.SkyLight.RealTimeCapture 1"}}
{"command": "run_console_command", "params": {"command": "r.DynamicGlobalIlluminationMethod 0"}}
```

**Root cause of black PIE:** Static lights require a lighting build.
Blank levels have no lighting build. Movable lights work immediately.

## Problem
New blank levels have zero lighting. Screenshots and PIE
sessions are completely black. setup_scene_lighting
hardcodes intensity=2 and ignores all parameters.

## Root Cause
- setup_scene_lighting developed against existing project
  that already had lights — gap was never visible
- No fresh-install test run before v1.0.2 shipped
- Editor viewport captures wireframe not geometry
- PIE captures before scene fully loads

## Current Workaround
1. create_blueprint {name: "BP_Lighting", parent: "Actor"}
2. add_component SkyLight — set_component_property intensity=3.0
3. add_component DirectionalLight — set intensity=10.0, color=(1.0,0.95,0.85)
4. compile_blueprint
5. spawn_actor_at (0,0,500) label="LevelLighting"
6. run_console_command "r.SkyLight.RealTimeCapture 1"

## Correct Solution — v1.0.3
New command: setup_default_lighting
  Params: scene_type (outdoor/indoor/dark), intensity_multiplier
  Auto-spawns SkyLight + DirectionalLight + SkyAtmosphere
  Handles all three scene types correctly

## Rule
Run setup_default_lighting at the start of EVERY new level
session. It is now step 1.5 in the session startup protocol.

## Verification Checklist
- [ ] Workaround tested on blank level
- [ ] v1.0.3 command implemented
- [ ] v1.0.3 tested on blank level
- [ ] Added to fresh install test checklist
- [ ] Added to AI Guide startup protocol
