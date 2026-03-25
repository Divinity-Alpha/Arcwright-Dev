# Arcwright

### The AI Game Creation Platform

---

## Describe your game. Watch it build itself.

Arcwright is the first platform that turns natural language descriptions into playable Unreal Engine 5 game prototypes. Tell it what you want — enemies that patrol and chase, collectible items with glowing effects, a health bar HUD, weapon stats tables — and it builds everything automatically in UE5.

No manual Blueprint editing. No manual 3D modeling. No manual data entry.

---

## What It Does

**You say:** "Create a fantasy arena with gold collectibles, red danger zones, patrol enemies that chase the player, and a HUD showing score and health."

**It builds:**
- Blueprint logic for pickups, hazards, and enemies
- AI behavior trees for patrol and chase
- Widget HUD with score display and health bar
- 3D meshes and colored materials
- Actors placed in the level
- Data tables for game configuration
- Everything saved and ready to play

**Time:** Minutes, not weeks.

---

## Three AI Models, One Platform

| Model | What It Generates | Accuracy |
|---|---|---|
| **Blueprint DSL** | Game logic, events, variables, physics | 97.2% syntax |
| **Behavior Tree DSL** | AI patrol, chase, attack, flee behaviors | 95.0% syntax |
| **Data Table DSL** | Weapons, items, enemies, abilities, waves | Training now |

Each model was trained using a proprietary **teaching loop** — an iterative cycle of train → examine → grade → correct that targets specific weaknesses each round. The methodology is language-agnostic and applies to any structured format.

---

## 90 Tools Across Two Engines

| Engine | Tools | Capabilities |
|---|---|---|
| **Unreal Engine 5** | 62 commands | Blueprints, AI, UI widgets, components, materials, splines, post-processing, sequencer, foliage, physics, audio, input, level management |
| **Blender** | 22 commands | Mesh creation, modifiers, materials, UV, edit mode, export (FBX/OBJ/glTF) |
| **Cross-tool** | 6 commands | Import meshes/textures/sounds from Blender into UE |

Claude Desktop connects to both engines simultaneously via MCP. One conversation builds 3D models in Blender, imports them into Unreal, creates game logic, and places everything in the level.

---

## Proven Results

**Games built entirely through the pipeline:**
- **Pickup Collector** — Collectibles, hazard zones, victory condition, score tracking
- **Arena Collector** — Enemies with AI patrol+chase, HUD, damage zones, health pickups, post-processing

**Every game element automated:**
- Blueprint creation from natural language
- Collision, mesh, light components
- Colored materials (gold pickups, red hazards, green health)
- AI enemies with behavior trees
- Widget HUD with score and health display
- Level population with actors at specified positions
- Project save to disk

---

## Template Library

16 reusable game patterns, each proven and tested:

- **Collectibles** — Basic pickup, score pickup, health pickup, timed powerup
- **Hazards** — Damage zone with timer-based ticks
- **Triggers** — Victory zone, pressure plate, teleporter, lever/switch
- **Enemies** — Patrol+chase AI, stationary turret
- **Managers** — Score tracker, wave spawner
- **UI** — Full game HUD with score, health bar, wave counter
- **Movement** — Rotating obstacle, moving platform

Templates are customizable — change the mesh, color, damage values, patrol points — and instantiable with one command.

---

## Who It's For

**Solo indie developers** — Your AI technical co-founder. Go from game design document to playable prototype in an afternoon instead of months.

**Game design students** — Learn UE5 by building, not by watching tutorials. See how Blueprints, AI, and UI work by having them generated and explained.

**Studios (prototyping)** — A designer roughs out a level in hours. Hand it to engineers for polish. Cut prototype cycles from weeks to days.

**Non-technical creators** — Writers, artists, and designers with game ideas but no coding ability. This is the first tool that lets you build what you imagine.

---

## Technology

- **Base Model:** LLaMA 3.1 70B with domain-specific LoRA adapters
- **Training Hardware:** NVIDIA RTX PRO 6000 (96GB VRAM)
- **UE Plugin:** C++ TCP command server embedded in the editor
- **Blender Addon:** Python TCP server using bpy API
- **Integration:** MCP (Model Context Protocol) for Claude Desktop
- **DSL Parsers:** Python parsers with validation, compliance checking, and IR generation
- **Teaching Loop:** Automated train → examine → grade → correct cycle

---

## Roadmap

| Phase | Status | What |
|---|---|---|
| Blueprint Mastery | ✅ Complete | 97.2% accuracy, 179 node types |
| UE5 Plugin | ✅ Complete | 62 commands, full game creation |
| Behavior Trees | ✅ 80% | AI patrol, chase, attack patterns |
| Data Tables | 🔄 In Progress | Weapons, items, enemies, abilities |
| Blender Integration | ✅ Complete | 22 commands, cross-tool pipeline |
| Animation Blueprints | 📋 Spec Ready | State machines, locomotion, combat |
| Material Graphs | 📋 Planned | PBR materials, shader effects |
| Open Standard | 📋 Planned | Compliance checker, certification tiers |

---

## Contact

**Divinity Alpha**
GitHub: github.com/Divinity-Alpha/Arcwright

---

*Arcwright — Describe. Build. Play.*
