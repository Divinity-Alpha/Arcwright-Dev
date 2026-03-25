# Temple Escape — Game Design Document

> **Purpose:** Visually polished demo game for Arcwright promotion
> **Genre:** Puzzle / Exploration
> **Engine:** Unreal Engine 5.7
> **Build Method:** 100% automated through Arcwright pipeline
> **Estimated Build Time:** 15-20 minutes via script

---

## 1. Concept

The player wakes up in an ancient temple. To escape, they must collect 3 golden keys scattered through the rooms, avoid patrol enemies and hazard zones, solve pressure plate puzzles to open doors, and reach the exit portal. A HUD tracks keys collected, health, and shows messages.

**Why this game:**
- Uses every tool we've built (Blueprints, BT, components, materials, widgets, Blender, post-process, splines, sequencer)
- Visually impressive with atmospheric lighting and color-coded interactions
- Different genre from Arena Collector — proves versatility
- Clear goal structure (collect 3 keys → exit) makes a compelling demo video

---

## 2. Visual Style Guide

### Color Language (players learn what colors mean)
| Color | Meaning | Material | Example |
|---|---|---|---|
| **Gold/Yellow** | Collectible / Interactive | Emissive glow, metallic | Keys, coins |
| **Blue/Cyan** | Puzzle element / Safe | Soft glow, low roughness | Pressure plates, levers, doors |
| **Red/Orange** | Danger / Enemy | Pulsing emissive, rough | Hazard zones, enemies |
| **Green** | Health / Positive | Bright emissive | Health pickups, exit portal |
| **Grey/Stone** | Environment / Neutral | High roughness, no emissive | Walls, floors, pillars |
| **Purple** | Magical / Special | Emissive, low roughness | Teleporters, buffs |

### Lighting
- **Ambient:** Very low — temple should feel dark and atmospheric
- **Point lights:** Warm orange (torches) at regular intervals along walls
- **Key lights:** Gold point lights near each key — draws the eye
- **Hazard lights:** Red point lights in danger areas
- **Exit light:** Bright green glow at the exit portal
- **Post-process:** High vignette (0.5), slight bloom (1.5), desaturated colors (saturation 0.85), slight blue tint in shadows

### Scale
- Player height: ~180 units (default pawn)
- Room size: 1000x1000 units (comfortable for movement)
- Corridor width: 400 units
- Wall height: 500 units
- Door opening: 300 wide x 400 tall

---

## 3. Level Layout

Top-down view (Y is forward, X is right):

```
                    [EXIT ROOM]
                   (0, 4000, 0)
                        |
                   [CORRIDOR 3]
                        |
              [KEY 3 ROOM] --- [HAZARD CORRIDOR]
             (-1000, 3000)      (1000, 3000)
                        |
                   [MAIN HALL]
                   (0, 2000, 0)
                  /             \
         [KEY 1 ROOM]     [KEY 2 ROOM]
        (-1500, 1000)    (1500, 1000)
                  \             /
                   [CORRIDOR 1]
                        |
                  [STARTING ROOM]
                   (0, 0, 0)
```

### Room Definitions

#### Starting Room (0, 0, 0)
- Size: 1200 x 1200 x 500
- Contents: PlayerStart, 2 torches, intro message trigger
- Feel: Safe, warm lighting, establishes the visual style
- Floor: Stone grey
- Walls: Darker stone

#### Corridor 1 (0, 500, 0)
- Size: 400 x 1000 x 500
- Contents: 4 torches (2 per side), 1 health pickup
- First enemy patrol route (between y=600 and y=1400)

#### Key 1 Room — West Wing (-1500, 1000, 0)
- Size: 1000 x 1000 x 500
- Contents: Key 1 (gold, glowing), pressure plate puzzle
- Puzzle: Step on plate → door opens for 5 seconds → grab key
- 2 torches, 1 enemy patrolling
- Hazard zone blocking direct path to key

#### Key 2 Room — East Wing (1500, 1000, 0)
- Size: 1000 x 1000 x 500
- Contents: Key 2 (gold, glowing), lever puzzle
- Puzzle: Pull lever → toggles bridge/platform → reach key
- 3 torches, no enemies (puzzle-focused room)

#### Main Hall (0, 2000, 0)
- Size: 2000 x 1000 x 600 (tall ceiling)
- Contents: Central pillar, 6 torches, 2 health pickups
- 2 enemies patrolling in figure-8 pattern
- Impressive visual — largest room, most lights

#### Key 3 Room (-1000, 3000, 0)
- Size: 800 x 800 x 500
- Contents: Key 3 (gold, glowing), timed pressure plate sequence
- Puzzle: Step on plates in order (A, B, C) within 5 seconds → key accessible
- 2 torches, 1 enemy

#### Hazard Corridor (1000, 3000, 0)
- Size: 400 x 800 x 500
- Contents: 3 damage zones with gaps between them
- "Run the gauntlet" — timing challenge
- Red lighting throughout

#### Corridor 3 (0, 3500, 0)
- Size: 400 x 500 x 500
- Contents: 2 torches, locked door (requires 3 keys)
- Door checks key count on overlap — if 3, opens and prints "The exit opens!"

#### Exit Room (0, 4000, 0)
- Size: 800 x 800 x 600
- Contents: Exit portal (green glowing platform), victory trigger
- Dramatic green lighting, swirling particle effect if possible
- On overlap: "TEMPLE ESCAPED! You Win!" + large HUD message

---

## 4. Blueprint Specifications

### BP_TempleKey
**Pattern:** collectible_basic (template)
**DSL:**
```
BLUEPRINT: BP_TempleKey
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="Key Collected!"]
NODE n3: DestroyActor

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
```
**Components:**
- BoxCollision: extent (40, 40, 40), generate_overlap_events=true
- StaticMesh: Blender-created key model OR /Engine/BasicShapes/Cube.Cube scaled (0.3, 0.15, 0.5) as placeholder
- PointLight: intensity=5000, color=(255, 200, 0), attenuation=400

**Material:** MI_GoldKey — emissive gold, metallic=0.9, roughness=0.1, emissive boost

### BP_TempleDoor
**Pattern:** new
**DSL:**
```
BLUEPRINT: BP_TempleDoor
PARENT: Actor

VAR IsOpen: Bool = false
VAR RequiredKeys: Int = 0

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="Door requires keys..."]

EXEC n1.Then -> n2.Execute
```
**Components:**
- BoxCollision: extent (150, 20, 200), generate_overlap_events=true
- StaticMesh: /Engine/BasicShapes/Cube.Cube scaled (3, 0.4, 4) — solid door slab

**Material:** MI_StoneDoor — dark grey, roughness=0.9

### BP_PressurePlate
**Pattern:** trigger_pressure_plate (template)
**DSL:**
```
BLUEPRINT: BP_PressurePlate
PARENT: Actor

VAR IsPressed: Bool = false

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: SetVar [Variable=IsPressed, Value=true]
NODE n3: PrintString [InString="Plate activated!"]
NODE n4: Event_ActorEndOverlap
NODE n5: SetVar [Variable=IsPressed, Value=false]
NODE n6: PrintString [InString="Plate deactivated"]

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
EXEC n4.Then -> n5.Execute
EXEC n5.Then -> n6.Execute
```
**Components:**
- BoxCollision: extent (100, 100, 10), generate_overlap_events=true
- StaticMesh: /Engine/BasicShapes/Cube.Cube scaled (2, 2, 0.2) — flat plate

**Material:** MI_PlateCyan — cyan/blue glow, emissive

### BP_TempleLever
**Pattern:** trigger_lever (template)
**DSL:**
```
BLUEPRINT: BP_TempleLever
PARENT: Actor

VAR IsActive: Bool = false

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: FlipFlop
NODE n3: SetVar [Variable=IsActive, Value=true]
NODE n4: PrintString [InString="Lever ON"]
NODE n5: SetVar [Variable=IsActive, Value=false]
NODE n6: PrintString [InString="Lever OFF"]

EXEC n1.Then -> n2.Execute
EXEC n2.A -> n3.Execute
EXEC n3.Then -> n4.Execute
EXEC n2.B -> n5.Execute
EXEC n5.Then -> n6.Execute
```
**Components:**
- BoxCollision: extent (50, 50, 80), generate_overlap_events=true
- StaticMesh: /Engine/BasicShapes/Cylinder.Cylinder scaled (0.3, 0.3, 1.5)

**Material:** MI_LeverBlue — blue, metallic

### BP_HazardZone
**Pattern:** hazard_zone (template)
*Same as Arena Collector but with temple theming*

**Material:** MI_HazardRed — deep red, emissive pulsing effect

### BP_HealthPickup
**Pattern:** collectible_health (template)
*Same as Arena Collector*

**Material:** MI_HealthGreen — green glow

### BP_TempleEnemy
**Pattern:** enemy_patrol_chase (template)
*Pawn + FloatingPawnMovement + AIController with patrol+chase*

**Components:**
- StaticMesh: /Engine/BasicShapes/Cylinder.Cylinder scaled (0.8, 0.8, 2)
- PointLight: intensity=2000, color=(255, 50, 0), attenuation=300

**Material:** MI_EnemyRed — dark red, slight emissive

### BP_ExitPortal
**Pattern:** trigger_victory (template)

**Components:**
- BoxCollision: extent (150, 150, 200), generate_overlap_events=true
- StaticMesh: /Engine/BasicShapes/Cylinder.Cylinder scaled (3, 3, 0.3) — flat platform
- PointLight: intensity=8000, color=(0, 255, 100), attenuation=600

**Material:** MI_PortalGreen — bright green, highly emissive

### BP_Torch
**Pattern:** new (decorative, no logic)
**DSL:**
```
BLUEPRINT: BP_Torch
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: PrintString [InString=""]

EXEC n1.Then -> n2.Execute
```
**Components:**
- StaticMesh: /Engine/BasicShapes/Cylinder.Cylinder scaled (0.15, 0.15, 0.8)
- PointLight: intensity=3000, color=(255, 150, 50), attenuation=500

**Material:** MI_TorchDark — dark brown/black

### BP_Wall
**Pattern:** new (environment building block)
**No Blueprint needed** — spawn static mesh actors directly with materials

### BP_TempleGameManager
**Pattern:** manager + HUD
**DSL:**
```
BLUEPRINT: BP_TempleGameManager
PARENT: Actor

VAR KeysCollected: Int = 0
VAR Health: Float = 100.0
VAR GameWon: Bool = false

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: CreateWidget [WidgetClass=WBP_TempleHUD]
NODE n3: AddToViewport
NODE n4: PrintString [InString="Find 3 keys to escape the temple..."]

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
EXEC n3.Then -> n4.Execute

DATA n2.ReturnValue -> n3.Target [Widget]
```

---

## 5. HUD Design — WBP_TempleHUD

```
┌──────────────────────────────────────────────────────┐
│ 🔑 Keys: 0/3          ██████████ Health: 100         │
│                                                      │
│                                                      │
│                                                      │
│                                                      │
│                                                      │
│                                                      │
│                                                      │
│              [Message text area]                      │
│                                                      │
│                    TEMPLE ESCAPE                      │
└──────────────────────────────────────────────────────┘
```

**Widgets:**
- CanvasPanel: RootPanel
- TextBlock: KeysLabel — "Keys: 0/3", gold, size 24, top-left (40, 30)
- ProgressBar: HealthBar — green fill, top-center (500, 25), size (300, 25)
- TextBlock: HealthText — "Health: 100", white, size 16, (580, 5)
- TextBlock: MessageText — "", yellow, size 28, bottom-center (400, 620)
- TextBlock: TitleText — "TEMPLE ESCAPE", white 50% opacity, size 14, bottom-right (1050, 690)

---

## 6. Materials List

| Material | Color RGB | Metallic | Roughness | Emissive | Used On |
|---|---|---|---|---|---|
| MI_StoneFloor | (0.25, 0.22, 0.2) | 0.0 | 0.9 | No | Floors |
| MI_StoneWall | (0.18, 0.16, 0.15) | 0.0 | 0.85 | No | Walls |
| MI_StoneDoor | (0.15, 0.13, 0.12) | 0.0 | 0.9 | No | Doors |
| MI_GoldKey | (1.0, 0.8, 0.0) | 0.9 | 0.1 | Yes | Keys |
| MI_PlateCyan | (0.0, 0.8, 1.0) | 0.3 | 0.3 | Yes | Pressure plates |
| MI_LeverBlue | (0.1, 0.3, 1.0) | 0.6 | 0.3 | Yes | Levers |
| MI_HazardRed | (1.0, 0.05, 0.0) | 0.0 | 0.5 | Yes | Hazard zones |
| MI_EnemyRed | (0.8, 0.1, 0.05) | 0.0 | 0.6 | Slight | Enemies |
| MI_HealthGreen | (0.1, 1.0, 0.2) | 0.0 | 0.3 | Yes | Health pickups |
| MI_PortalGreen | (0.0, 1.0, 0.4) | 0.3 | 0.1 | Strong | Exit portal |
| MI_TorchDark | (0.1, 0.06, 0.03) | 0.0 | 0.8 | No | Torch bases |
| MI_Pillar | (0.3, 0.28, 0.25) | 0.0 | 0.7 | No | Decorative pillars |

---

## 7. Actor Placement (exact positions)

### Starting Room
| Actor | Class | Position | Notes |
|---|---|---|---|
| PlayerStart | PlayerStart | (0, 0, 50) | Player spawn |
| Torch_S1 | BP_Torch | (-500, -400, 200) | Left wall |
| Torch_S2 | BP_Torch | (500, -400, 200) | Right wall |
| GameManager | BP_TempleGameManager | (0, 0, 300) | Hidden, manages HUD |

### Corridor 1
| Actor | Class | Position | Notes |
|---|---|---|---|
| Torch_C1a | BP_Torch | (-180, 600, 200) | Left wall |
| Torch_C1b | BP_Torch | (180, 600, 200) | Right wall |
| Torch_C1c | BP_Torch | (-180, 1000, 200) | Left wall |
| Torch_C1d | BP_Torch | (180, 1000, 200) | Right wall |
| Health_C1 | BP_HealthPickup | (0, 800, 50) | Center corridor |
| Enemy_C1 | BP_TempleEnemy | (0, 700, 50) | Patrols y=600→1400 |

### Key 1 Room (West)
| Actor | Class | Position | Notes |
|---|---|---|---|
| Key1 | BP_TempleKey | (-1500, 1200, 50) | Behind hazard |
| Plate_K1 | BP_PressurePlate | (-1200, 800, 0) | Opens path to key |
| Hazard_K1 | BP_HazardZone | (-1400, 1000, 50) | Blocks direct path |
| Torch_K1a | BP_Torch | (-1800, 800, 200) | |
| Torch_K1b | BP_Torch | (-1200, 1200, 200) | |
| Enemy_K1 | BP_TempleEnemy | (-1500, 900, 50) | Patrols room |

### Key 2 Room (East)
| Actor | Class | Position | Notes |
|---|---|---|---|
| Key2 | BP_TempleKey | (1500, 1200, 50) | On raised platform |
| Lever_K2 | BP_TempleLever | (1200, 800, 50) | Toggles platform |
| Torch_K2a | BP_Torch | (1200, 800, 200) | |
| Torch_K2b | BP_Torch | (1800, 1200, 200) | |
| Torch_K2c | BP_Torch | (1500, 1400, 200) | |

### Main Hall
| Actor | Class | Position | Notes |
|---|---|---|---|
| Pillar_1 | StaticMesh | (-400, 2000, 0) | Decorative, scale (1,1,5) |
| Pillar_2 | StaticMesh | (400, 2000, 0) | Decorative, scale (1,1,5) |
| Torch_MH1 | BP_Torch | (-800, 1600, 200) | |
| Torch_MH2 | BP_Torch | (800, 1600, 200) | |
| Torch_MH3 | BP_Torch | (-800, 2400, 200) | |
| Torch_MH4 | BP_Torch | (800, 2400, 200) | |
| Torch_MH5 | BP_Torch | (-400, 2000, 300) | Pillar-mounted |
| Torch_MH6 | BP_Torch | (400, 2000, 300) | Pillar-mounted |
| Health_MH1 | BP_HealthPickup | (-600, 2200, 50) | |
| Health_MH2 | BP_HealthPickup | (600, 1800, 50) | |
| Enemy_MH1 | BP_TempleEnemy | (-300, 1800, 50) | Patrol pattern 1 |
| Enemy_MH2 | BP_TempleEnemy | (300, 2200, 50) | Patrol pattern 2 |

### Key 3 Room
| Actor | Class | Position | Notes |
|---|---|---|---|
| Key3 | BP_TempleKey | (-1000, 3200, 50) | Locked behind plate sequence |
| Plate_K3a | BP_PressurePlate | (-1200, 2800, 0) | Sequence plate A |
| Plate_K3b | BP_PressurePlate | (-800, 2900, 0) | Sequence plate B |
| Plate_K3c | BP_PressurePlate | (-1000, 3000, 0) | Sequence plate C |
| Torch_K3a | BP_Torch | (-1200, 3200, 200) | |
| Torch_K3b | BP_Torch | (-800, 3200, 200) | |
| Enemy_K3 | BP_TempleEnemy | (-1000, 2900, 50) | Guards the key |

### Hazard Corridor
| Actor | Class | Position | Notes |
|---|---|---|---|
| Hazard_HC1 | BP_HazardZone | (1000, 2800, 50) | Gap, gap, hazard |
| Hazard_HC2 | BP_HazardZone | (1000, 3100, 50) | |
| Hazard_HC3 | BP_HazardZone | (1000, 3400, 50) | |
| Light_HC1 | PointLight | (1000, 2800, 200) | Red, intensity 2000 |
| Light_HC2 | PointLight | (1000, 3100, 200) | Red |
| Light_HC3 | PointLight | (1000, 3400, 200) | Red |

### Exit Corridor + Room
| Actor | Class | Position | Notes |
|---|---|---|---|
| Door_Exit | BP_TempleDoor | (0, 3500, 0) | Requires 3 keys |
| Torch_EC1 | BP_Torch | (-180, 3600, 200) | |
| Torch_EC2 | BP_Torch | (180, 3600, 200) | |
| Portal | BP_ExitPortal | (0, 4000, 0) | Victory trigger |
| Light_Portal | PointLight | (0, 4000, 300) | Green, intensity 8000 |

---

## 8. Post-Process Settings

Applied via infinite-extent PostProcessVolume:

```json
{
    "bloom_intensity": 1.5,
    "bloom_threshold": 0.8,
    "vignette_intensity": 0.5,
    "auto_exposure_min": 0.5,
    "auto_exposure_max": 2.0,
    "ambient_occlusion_intensity": 0.8,
    "color_saturation": [0.85, 0.85, 0.9, 1.0],
    "color_contrast": [1.1, 1.1, 1.15, 1.0]
}
```

---

## 9. Sequencer — Intro Camera

A 5-second intro sequence that sweeps across the temple:

| Time | Camera Position | Camera Rotation | What's Visible |
|---|---|---|---|
| 0.0s | (0, -500, 400) | (-20, 0, 0) | Looking into starting room |
| 1.5s | (0, 1000, 500) | (-25, 0, 0) | Corridor, first enemy visible |
| 3.0s | (0, 2000, 600) | (-30, 0, 0) | Main hall overview |
| 4.5s | (0, 4000, 400) | (-15, 180, 0) | Exit portal glowing in distance |
| 5.0s | (0, 0, 180) | (0, 0, 0) | Back to player start |

---

## 10. Build Checklist

This becomes the demo_temple_escape.py script:

```
[ ] 1. Clean scene
[ ] 2. Create WBP_TempleHUD widget tree
[ ] 3. Create all 10 Blueprints from DSL
[ ] 4. Add components to all Blueprints
[ ] 5. Create all 12 materials
[ ] 6. Apply materials to meshes
[ ] 7. Spawn all ~60 actors in correct positions
[ ] 8. Set AI class defaults for enemies
[ ] 9. Add NavMeshBoundsVolume
[ ] 10. Add PostProcessVolume with settings
[ ] 11. Create intro sequence with keyframes
[ ] 12. Save level + save all
[ ] 13. Take screenshots from 4 camera angles
[ ] 14. Verify all Blueprints compile
[ ] 15. Verify actor count matches expected
```

---

## 11. Video Shot List

| Shot | Duration | What's Shown | Audio |
|---|---|---|---|
| 1. Text card | 3s | "What if you could describe a game..." | Quiet ambient |
| 2. Conversation | 8s | Claude Desktop chat: user typing the game description | Typing sounds |
| 3. Fast-forward build | 15s | UE editor, Blueprints appearing, actors spawning, materials applied | Upbeat music |
| 4. Slow reveal | 5s | Camera sweep through finished temple (the sequencer intro) | Dramatic music |
| 5. Gameplay | 15s | Player running through, collecting keys, avoiding enemies | Game sounds |
| 6. Key moment | 5s | Collecting final key, door opens, "The exit opens!" | Crescendo |
| 7. Victory | 3s | Stepping on portal, "TEMPLE ESCAPED!" on screen | Triumph |
| 8. Stats card | 5s | "10 Blueprints. 60 actors. 12 materials. Built in 3 minutes." | Quiet |
| 9. Logo | 3s | "Arcwright — Describe. Build. Play." | Fade |

Total: ~62 seconds

---

*This document is the complete specification. The demo_temple_escape.py script will implement every detail listed here.*
