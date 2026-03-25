# Arcwright DSL — Best Practices for Blueprint Generation

> **Version:** 2.0
> **Last Updated:** 2026-03-05
> **Compatibility:** Arcwright DSL v1, UE 5.7 Plugin, MCP Server v1
> **Audience:** AI systems (Claude, GPT, etc.), third-party tool developers, Claude Desktop users, compliance checker targets

This document defines how to generate valid, importable Blueprint DSL that works with the Arcwright pipeline. Follow these rules and your output will parse cleanly, map to real UE5 nodes, and produce working Blueprints.

---

## 1. DSL Structure

Every Blueprint follows this exact structure, in this order:

```
BLUEPRINT: <name>
PARENT: <parent_class>
CATEGORY: <optional_category>

VAR <name>: <type> = <default_value>
VAR <name>: <type> = <default_value>

GRAPH: EventGraph

NODE n1: <NodeType> [Param=Value]
NODE n2: <NodeType> [Param=Value, Param2=Value2]

EXEC n1.PinOut -> n2.PinIn
DATA n1.PinOut -> n2.PinIn [DataType]
```

**Rules:**
- `BLUEPRINT:` and `PARENT:` are required. `CATEGORY:` is optional.
- `GRAPH: EventGraph` is required before any nodes or connections.
- Variables (`VAR`) come before the GRAPH section.
- Nodes come before connections.
- Every line is one statement. No multi-line nodes or connections.
- No blank lines are required between sections, but they are allowed.
- Do not include any preamble, explanation, markdown formatting, or code fences. Output only the DSL.

---

## 2. Naming Conventions

### Blueprint Names
- Always prefix with `BP_`: `BP_HealthPickup`, `BP_DoorInteract`, `BP_EnemyTurret`
- PascalCase, no spaces, no special characters

### Parent Classes
- Use short class names: `Actor`, `Character`, `Pawn`, `PlayerController`
- Do not use full paths like `/Script/Engine.Actor`

### Variable Names
- PascalCase: `Health`, `MaxSpeed`, `IsActive`, `DamageAmount`
- No spaces, no special characters
- Be descriptive: `PlayerHealth` not `H`, `SpawnLocation` not `Loc`

### Node IDs
- Sequential: `n1`, `n2`, `n3`... Always start at `n1`.
- Never skip numbers. Never reuse an ID.

---

## 3. Variable Declarations

```
VAR Health: float = 100.0
VAR IsActive: bool = true
VAR PlayerName: string = "Hero"
VAR Counter: int = 0
VAR SpawnPoint: vector = (0,0,0)
VAR Targets: Actor[] = ()
```

**Supported types:** `float`, `int`, `bool`, `string`, `vector`, `rotator`, `Actor`, `Actor[]` (arrays)

**Rules:**
- Every variable used in GetVar/SetVar must be declared in the VAR section.
- Default values are required.
- Booleans: `true` or `false` (lowercase).
- Floats: always include decimal (`100.0` not `100`).
- Strings: quote with double quotes.
- Vectors: `(X,Y,Z)` format.
- Arrays: `()` for empty.

---

## 4. Node Types — Complete Reference

### Events (always the starting point of execution)

| DSL Name | Description | Exec Out | Data Out |
|---|---|---|---|
| `Event_BeginPlay` | Fires when actor spawns | `Then` | — |
| `Event_Tick` | Fires every frame | `Then` | `DeltaSeconds` (float) |
| `Event_EndPlay` | Fires when actor is destroyed | `Then` | — |
| `Event_ActorBeginOverlap` | Fires on overlap start | `Then` | `OtherActor` (object) |
| `Event_ActorEndOverlap` | Fires on overlap end | `Then` | `OtherActor` (object) |
| `Event_AnyDamage` | Fires when actor takes damage | `Then` | `Damage` (float) |
| `Event_Hit` | Fires on physics collision | `Then` | — |
| `Event_InputAction` | Fires on input | `Pressed`, `Released` | — |
| `Event_CustomEvent` | User-defined event | `Then` | — |

**Input Action usage:** `NODE n1: Event_InputAction [ActionName=Jump]`
**Custom Event usage:** `NODE n1: Event_CustomEvent [EventName=OnReset]`

**Rules:**
- Every Blueprint must have at least one Event node.
- Events are always the root of an execution chain.
- Event data outputs (like `DeltaSeconds`, `OtherActor`, `Damage`) are DATA connections, not parameters.

### Flow Control

| DSL Name | Exec In | Exec Out | Data In | Data Out |
|---|---|---|---|---|
| `Branch` | `Execute` | `True`, `False` | `Condition` (bool) | — |
| `Sequence` | `Execute` | `A`, `B`, `C`, `D`, `E`, `F` | — | — |
| `FlipFlop` | `Execute` | `A`, `B` | — | `IsA` (bool) |
| `DoOnce` | `Execute`, `Reset` | `Completed` | — | — |
| `Gate` | `Enter`, `Open`, `Close`, `Toggle` | `Exit` | — | — |
| `MultiGate` | `Execute` | `Out_0`, `Out_1`, `Out_2`... | — | — |

#### ⚠️ Sequence Node — Use Fan-Out, Not Linear Chaining

**CORRECT — Fan-out pattern:**
```
NODE n1: Event_BeginPlay
NODE n2: Sequence
NODE n3: PrintString [InString="First"]
NODE n4: PrintString [InString="Second"]
NODE n5: PrintString [InString="Third"]

EXEC n1.Then -> n2.Execute
EXEC n2.A -> n3.Execute
EXEC n2.B -> n4.Execute
EXEC n2.C -> n5.Execute
```

**WRONG — Linear chaining:**
```
EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
EXEC n3.Then -> n4.Execute
```

Sequence nodes fan out to parallel execution paths using pins `A`, `B`, `C`, `D`, `E`, `F`. They do NOT chain linearly with `Then` pins. This is the most common mistake.

### Loops

| DSL Name | Exec In | Exec Out | Data In | Data Out |
|---|---|---|---|---|
| `ForLoop` | `Execute` | `LoopBody`, `Completed` | `FirstIndex` (int), `LastIndex` (int) | `Index` (int) |
| `ForEachLoop` | `Execute` | `LoopBody`, `Completed` | `Array` (array) | `Element` (object), `Index` (int) |
| `WhileLoop` | `Execute` | `LoopBody`, `Completed` | `Condition` (bool) | — |

**ForLoop usage:**
```
NODE n3: ForLoop
DATA 0 -> n3.FirstIndex [int]
DATA 9 -> n3.LastIndex [int]
EXEC n3.LoopBody -> n4.Execute
EXEC n3.Completed -> n5.Execute
DATA n3.Index -> n4.InString [int]
```

### Casts

```
NODE n3: CastToCharacter
EXEC n2.Then -> n3.Execute
DATA n2.OtherActor -> n3.Object [object]
EXEC n3.CastSucceeded -> n4.Execute
EXEC n3.CastFailed -> n5.Execute
DATA n3.AsCharacter -> n6.Target [object]
```

**Rules:**
- Always wire BOTH `CastSucceeded` and `CastFailed` exec outputs.
- Always wire the `Object` data input.
- Always wire the `As<ClassName>` data output to downstream nodes.
- Available casts: `CastToCharacter`, `CastToPawn`, `CastToPlayerController`, or `CastTo<AnyClass>`

### Variables

| DSL Name | Usage | Exec | Data |
|---|---|---|---|
| `GetVar` | Read a variable | — (pure node) | `Value` out |
| `SetVar` | Write a variable | `Execute` → `Then` | `Value` in |

**Usage:**
```
NODE n3: GetVar [Variable=Health]
NODE n4: SetVar [Variable=Health]
```

**Rules:**
- The `Variable` parameter must match a name declared in the `VAR` section.
- GetVar is a pure node (no exec pins). SetVar has exec pins.
- When setting a boolean: `NODE n5: SetVar [Variable=IsActive, Value=true]`

### Switch

| DSL Name | Data In | Exec Out |
|---|---|---|
| `SwitchOnInt` | `Selection` (int) | `Default`, `0`, `1`, `2`... |
| `SwitchOnString` | `Selection` (string) | `Default`, named cases |

**Usage:**
```
NODE n2: SwitchOnInt
DATA n1.Value -> n2.Selection [int]
EXEC n2.0 -> n3.Execute
EXEC n2.1 -> n4.Execute
EXEC n2.Default -> n5.Execute
```

### Common Functions

| DSL Name | Exec | Key Inputs | Key Outputs |
|---|---|---|---|
| `PrintString` | Yes | `InString` (string) | — |
| `Delay` | Yes | `Duration` (float) | `Completed` (exec) |
| `DestroyActor` | Yes | — | — |
| `IsValid` | No (pure) | `Input` (object) | `ReturnValue` (bool) |
| `SetTimerByFunctionName` | Yes | `FunctionName` (string), `Time` (float), `Looping` (bool) | — |
| `ClearTimerByFunctionName` | Yes | `FunctionName` (string) | — |
| `GetPlayerPawn` | No (pure) | — | `ReturnValue` (object) |
| `SpawnActorFromClass` | Yes | `ActorClass` (class), `SpawnTransform` (transform) | `ReturnValue` (object) |
| `PlaySoundAtLocation` | Yes | `Sound` (object), `Location` (vector) | — |

### Actor Functions

| DSL Name | Exec | Key Inputs | Key Outputs |
|---|---|---|---|
| `GetActorLocation` | No | — | `ReturnValue` (vector) |
| `SetActorLocation` | Yes | `NewLocation` (vector) | — |
| `GetActorForwardVector` | No | — | `ReturnValue` (vector) |
| `GetDistanceTo` | No | `OtherActor` (object) | `ReturnValue` (float) |
| `SetActorHiddenInGame` | Yes | `bNewHidden` (bool) | — |
| `TeleportTo` | Yes | `DestLocation` (vector) | — |
| `SetVisibility` | Yes | `bNewVisibility` (bool) | — |
| `AddActorLocalRotation` | Yes | `DeltaRotation` (rotator) | — |
| `AddActorLocalOffset` | Yes | `DeltaLocation` (vector) | — |

### Math (Float)

| DSL Name | Inputs | Output |
|---|---|---|
| `AddFloat` | `A`, `B` | `ReturnValue` |
| `SubtractFloat` | `A`, `B` | `ReturnValue` |
| `MultiplyFloat` | `A`, `B` | `ReturnValue` |
| `DivideFloat` | `A`, `B` | `ReturnValue` |
| `ClampFloat` | `Value`, `Min`, `Max` | `ReturnValue` |
| `RandomFloatInRange` | `Min`, `Max` | `ReturnValue` |

### Math (Comparison)

| DSL Name | Inputs | Output |
|---|---|---|
| `LessThan` | `A`, `B` | `ReturnValue` (bool) |
| `GreaterThan` | `A`, `B` | `ReturnValue` (bool) |
| `LessEqual` | `A`, `B` | `ReturnValue` (bool) |
| `EqualEqual` | `A`, `B` | `ReturnValue` (bool) |

### Math (Vector / Rotator)

| DSL Name | Inputs | Output |
|---|---|---|
| `MakeVector` | `X`, `Y`, `Z` | `ReturnValue` (vector) |
| `MakeRotator` | `Roll`, `Pitch`, `Yaw` | `ReturnValue` (rotator) |
| `VectorLerp` | `A`, `B`, `Alpha` | `ReturnValue` (vector) |
| `VectorDistance` | `A`, `B` | `ReturnValue` (float) |

### UI / Widget

| DSL Name | Exec | Key Inputs | Key Outputs |
|---|---|---|---|
| `CreateWidget` | Yes | `WidgetClass` (class) | `ReturnValue` (object) |
| `AddToViewport` | Yes | `Target` (object) | — |
| `RemoveFromParent` | Yes | — | — |

### Array Operations

| DSL Name | Exec | Key Inputs | Key Outputs |
|---|---|---|---|
| `ArrayLength` | No | `Target` (array) | `ReturnValue` (int) |
| `Contains` | No | `Target` (array), `Item` | `ReturnValue` (bool) |
| `Get` | No | `Target` (array), `Index` (int) | `ReturnValue` |
| `AddUnique` | Yes | `Target` (array), `Item` | — |
| `RemoveAt` | Yes | `Target` (array), `Index` (int) | — |
| `ClearArray` | Yes | `Target` (array) | — |

### Physics

| DSL Name | Exec | Key Inputs |
|---|---|---|
| `SetSimulatePhysics` | Yes | `bSimulate` (bool) |
| `AddImpulse` | Yes | `Impulse` (vector) |

### String

| DSL Name | Inputs | Output |
|---|---|---|
| `Concatenate` | `A`, `B` | `ReturnValue` (string) |
| `GetDisplayName` | `Object` | `ReturnValue` (string) |

---

## 5. Connection Rules

### EXEC Connections (Execution Flow)

```
EXEC n1.Then -> n2.Execute
```

- EXEC connections define the order of execution.
- Source pin is an exec OUTPUT (e.g., `Then`, `True`, `False`, `Completed`, `A`, `B`).
- Target pin is an exec INPUT (e.g., `Execute`).
- Every node with exec pins must be connected to at least one exec chain. No orphaned nodes.
- A single exec output can only connect to one exec input (no fan-out from a single pin — use Sequence for that).

### DATA Connections (Data Flow)

```
DATA n1.ReturnValue -> n2.A [float]
DATA n3.OtherActor -> n4.Object [object]
```

- DATA connections pass values between nodes.
- Source pin is a data OUTPUT. Target pin is a data INPUT.
- The `[type]` suffix is required.
- Pure nodes (GetVar, math, comparison, IsValid) have no exec pins — they are pulled by the nodes that need their output.

### Literal Values

```
DATA 100.0 -> n2.Duration [float]
DATA "Hello" -> n3.InString [string]
DATA true -> n4.bNewHidden [bool]
DATA 0 -> n5.FirstIndex [int]
```

Literal values can be wired directly to data inputs without a source node. Alternatively, use node parameters:

```
NODE n2: Delay [Duration=2.0]
NODE n3: PrintString [InString="Hello World"]
```

Both are valid. Parameters are preferred for simple values. DATA connections are preferred when the value comes from another node's output.

---

## 6. Common Patterns

### Health System (Math → Compare → Branch)

```
BLUEPRINT: BP_HealthSystem
PARENT: Actor

VAR Health: float = 100.0

GRAPH: EventGraph

NODE n1: Event_AnyDamage
NODE n2: GetVar [Variable=Health]
NODE n3: SubtractFloat
NODE n4: SetVar [Variable=Health]
NODE n5: LessThan
NODE n6: Branch
NODE n7: DestroyActor
NODE n8: PrintString [InString="Still alive"]

EXEC n1.Then -> n4.Execute
DATA n2.Value -> n3.A [float]
DATA n1.Damage -> n3.B [float]
DATA n3.ReturnValue -> n4.Value [float]
EXEC n4.Then -> n6.Execute
DATA n3.ReturnValue -> n5.A [float]
DATA 0.0 -> n5.B [float]
DATA n5.ReturnValue -> n6.Condition [bool]
EXEC n6.True -> n7.Execute
EXEC n6.False -> n8.Execute
```

**Key pattern:** GetVar → Math → SetVar → Compare → Branch → Actions. The compare node feeds its boolean result into the Branch's Condition pin.

### Cast with Both Paths

```
NODE n1: Event_ActorBeginOverlap
NODE n2: CastToCharacter
NODE n3: PrintString [InString="Player entered"]
NODE n4: PrintString [InString="Not a player"]

EXEC n1.Then -> n2.Execute
DATA n1.OtherActor -> n2.Object [object]
EXEC n2.CastSucceeded -> n3.Execute
EXEC n2.CastFailed -> n4.Execute
```

**Key pattern:** Always wire both CastSucceeded and CastFailed. Always wire the Object input from the event's OtherActor output.

### Overlap → Destroy with Timer

```
NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="Picked up!"]
NODE n3: Delay [Duration=0.5]
NODE n4: DestroyActor

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
EXEC n3.Completed -> n4.Execute
```

**Key pattern:** Delay uses `Completed` as its exec output, not `Then`.

### Sequence Fan-Out

```
NODE n1: Event_BeginPlay
NODE n2: Sequence
NODE n3: PrintString [InString="Step 1"]
NODE n4: SetVar [Variable=IsActive, Value=true]
NODE n5: PrintString [InString="Step 3"]

EXEC n1.Then -> n2.Execute
EXEC n2.A -> n3.Execute
EXEC n2.B -> n4.Execute
EXEC n2.C -> n5.Execute
```

### Event Data Pin Wiring

```
NODE n1: Event_AnyDamage
NODE n2: SubtractFloat

DATA n1.Damage -> n2.B [float]
```

**Key pattern:** Event output pins (Damage, OtherActor, DeltaSeconds) are DATA connections. Do NOT use them as string literals or parameters.

---

## 7. Common Mistakes to Avoid

### ❌ Sequence chained linearly
```
EXEC n2.Then -> n3.Execute
EXEC n3.Then -> n4.Execute
```
**✅ Use fan-out:** `EXEC n2.A -> n3.Execute` / `EXEC n2.B -> n4.Execute`

### ❌ Cast with only one path
```
EXEC n2.CastSucceeded -> n3.Execute
```
**✅ Wire both:** Add `EXEC n2.CastFailed -> n4.Execute`

### ❌ Event data used as literal
```
NODE n2: PrintString [InString=Damage]
```
**✅ Wire as data connection:**
```
DATA n1.Damage -> n2.InString [float]
```

### ❌ Orphaned nodes (no exec connection)
```
NODE n5: PrintString [InString="Unreachable"]
```
**✅ Every node with exec pins must be in an exec chain.**

### ❌ Missing variable declaration
```
NODE n3: GetVar [Variable=Health]
```
Without `VAR Health: float = 100.0` at the top, this will fail validation.

### ❌ Node IDs skipped or reused
```
NODE n1: Event_BeginPlay
NODE n3: PrintString     <-- skipped n2
NODE n3: Delay           <-- reused n3
```
**✅ Always sequential: n1, n2, n3, n4...**

### ❌ Preamble or explanation text
```
Here's a Blueprint that prints Hello World:
BLUEPRINT: BP_Hello
```
**✅ Start directly with `BLUEPRINT:`**

### ❌ Markdown code fences
````
```
BLUEPRINT: BP_Hello
```
````
**✅ Raw DSL text only, no formatting.**

---

## 8. Validation Checklist

Before submitting DSL output, verify:

- [ ] Starts with `BLUEPRINT:` (no preamble)
- [ ] Has `PARENT:` line
- [ ] Has `GRAPH: EventGraph` before nodes
- [ ] All variables used in GetVar/SetVar are declared in VAR section
- [ ] At least one Event node exists
- [ ] Node IDs are sequential (n1, n2, n3...) with no gaps or duplicates
- [ ] Every node with exec pins is connected to an exec chain
- [ ] All EXEC connections use valid pin names for the node type
- [ ] All DATA connections include a `[type]` suffix
- [ ] Sequence nodes use fan-out (A, B, C) not linear (Then)
- [ ] Cast nodes have both CastSucceeded and CastFailed wired
- [ ] Event data outputs are wired as DATA connections, not used as literals
- [ ] No markdown formatting, code fences, or explanation text
- [ ] No trailing garbage, closing braces, or model artifacts

---

## 9. Compliance Tiers

Tools and models are evaluated against this spec at three tiers:

| Tier | Requirement | What It Means |
|---|---|---|
| **Basic** | Lessons 01-06 node types | Events, flow control, variables, basic functions, loops |
| **Advanced** | Full node set (179+ types) | All math, arrays, physics, UI, strings, all patterns |
| **Certified** | All eval tests at 90%+ | Edge cases, complex systems, ambiguous prompts handled |

---

## 10. Full Pipeline Workflow

The complete pipeline from natural language to playable game content:

```
Natural Language Description
    → DSL Text (generated by fine-tuned LLM or hand-written)
    → Python Parser (validates syntax, maps nodes, produces IR)
    → JSON IR (intermediate representation)
    → TCP Command Server (create_blueprint_from_dsl)
    → C++ Plugin (creates UBlueprint asset in UE Editor)
    → Component commands (add collision, meshes, lights)
    → Material commands (create instances, apply colors)
    → Level population (spawn actors at positions)
    → Save (persist to disk)
    → Play In Editor (automated gameplay testing)
```

Each step can be triggered individually via TCP commands or through the MCP server from Claude Desktop.

### Single-Command Blueprint Creation

The simplest path from DSL to compiled Blueprint:

```python
from scripts.mcp_client.blueprint_client import ArcwrightClient

dsl = """
BLUEPRINT: BP_MyActor
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Hello World"]

EXEC n1.Then -> n2.Execute
"""

with ArcwrightClient() as client:
    result = client.create_blueprint_from_dsl(dsl)
    # Blueprint is now compiled and ready in UE Editor
```

### Making Blueprints Playable

DSL creates Blueprint logic (event graphs) but not visual/physical components. After creating a Blueprint, add components to make it functional in-game:

```python
with ArcwrightClient() as client:
    # Create the Blueprint
    client.create_blueprint_from_dsl(pickup_dsl)
    
    # Add collision so overlaps work
    client.add_component("BP_Pickup", "BoxCollision", "PickupCollision",
                         properties={"extent": {"x": 50, "y": 50, "z": 50},
                                     "generate_overlap_events": True})
    
    # Add visible mesh
    client.add_component("BP_Pickup", "StaticMesh", "PickupMesh",
                         properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                                     "scale": {"x": 0.5, "y": 0.5, "z": 0.5}})
    
    # Create and apply colored material
    client.create_material_instance("MI_Gold", 
                                    "/Engine/BasicShapes/BasicShapeMaterial",
                                    vector_params={"BaseColor": {"r": 1.0, "g": 0.8, "b": 0.0, "a": 1.0}})
    client.apply_material("BP_Pickup", "PickupMesh", "/Game/MI_Gold")
    
    # Place in the level
    client.spawn_actor_at("BP_Pickup", label="Pickup_1",
                          location={"x": 0, "y": 500, "z": 100})
    
    # Save everything
    client.save_all()
```

---

## 11. Component Management

Blueprints need components to be visible and interactive. The plugin supports adding components to a Blueprint's Simple Construction Script (SCS).

### Supported Component Types

| Friendly Name | UE Class | Key Properties |
|---|---|---|
| `BoxCollision` | UBoxComponent | extent (x,y,z), generate_overlap_events, collision_profile |
| `SphereCollision` | USphereComponent | radius, generate_overlap_events |
| `CapsuleCollision` | UCapsuleComponent | radius, half_height |
| `StaticMesh` | UStaticMeshComponent | mesh (asset path), material |
| `PointLight` | UPointLightComponent | intensity, light_color (r,g,b), attenuation_radius |
| `SpotLight` | USpotLightComponent | intensity, light_color, attenuation_radius |
| `Audio` | UAudioComponent | — |
| `Arrow` | UArrowComponent | — |
| `Scene` | USceneComponent | — (generic parent for hierarchy) |

All components support: location, rotation, scale (relative transform), visibility.

### Common Mesh Asset Paths

| Shape | Path |
|---|---|
| Cube | `/Engine/BasicShapes/Cube.Cube` |
| Sphere | `/Engine/BasicShapes/Sphere.Sphere` |
| Cylinder | `/Engine/BasicShapes/Cylinder.Cylinder` |
| Cone | `/Engine/BasicShapes/Cone.Cone` |
| Plane | `/Engine/BasicShapes/Plane.Plane` |

### Critical: Overlap Events Require Collision Components

A Blueprint with `Event_ActorBeginOverlap` or `Event_ActorEndOverlap` will never fire those events unless the Blueprint has a collision component with `generate_overlap_events` set to true. Always add collision when using overlap events.

### Critical: Cast To Character Requires a Character Pawn

`CastToCharacter` fails silently if the player is using `DefaultPawn` (the default spectator camera). The cast returns false and the success exec path never fires. Either use a proper Character-based pawn or wire overlap events directly without casting.

---

## 12. Materials

Materials control the visual appearance of mesh components. The pipeline supports creating Material Instances and applying them to components.

### Creating Material Instances

```python
client.create_material_instance(
    name="MI_RedHazard",
    parent="/Engine/BasicShapes/BasicShapeMaterial",
    vector_params={"BaseColor": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}},
    scalar_params={"Metallic": 0.0, "Roughness": 0.8}
)
```

### Applying Materials

```python
client.apply_material("BP_HazardZone", "HazardMesh", "/Game/MI_RedHazard")
```

### Useful Color Presets

| Color | BaseColor Values |
|---|---|
| Red | r=1.0, g=0.0, b=0.0 |
| Green | r=0.0, g=1.0, b=0.0 |
| Blue | r=0.0, g=0.0, b=1.0 |
| Gold | r=1.0, g=0.8, b=0.0 |
| White | r=1.0, g=1.0, b=1.0 |
| Dark | r=0.1, g=0.1, b=0.1 |

---

## 13. Level Population

Actors are placed in the level using spawn commands. Transforms include location, rotation, and scale.

### Spawning Actors

```python
# Spawn by Blueprint name
client.spawn_actor_at("BP_Pickup", label="Pickup_1",
                      location={"x": 0, "y": 500, "z": 100})

# Spawn by native class
client.spawn_actor_at("PointLight", label="Light_1",
                      location={"x": 0, "y": 0, "z": 300})

# With rotation and scale
client.spawn_actor_at("BP_HazardZone", label="Hazard_1",
                      location={"x": 0, "y": 1000, "z": 0},
                      rotation={"pitch": 0, "yaw": 45, "roll": 0},
                      scale={"x": 2, "y": 2, "z": 1})
```

### Critical: Re-spawn After Component Changes

Adding components to a Blueprint updates the asset, but already-placed actors in the level don't pick up changes. You must delete and re-spawn actors after modifying their Blueprint's components.

```python
client.delete_actor("Pickup_1")
client.spawn_actor_at("BP_Pickup", label="Pickup_1",
                      location={"x": 0, "y": 500, "z": 100})
```

---

## 14. MCP Integration (Claude Desktop)

The pipeline can be controlled from Claude Desktop via MCP (Model Context Protocol). This enables conversational game development: describe what you want, and Claude creates it in Unreal Engine.

### Setup

Add to `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "blueprint-llm": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

Requires UE Editor running with the Arcwright plugin loaded (TCP server on port 13377).

### Available MCP Tools

Blueprint creation, component management, material creation, level population, actor management, Blueprint inspection — all accessible through natural conversation with Claude Desktop.

### Example Conversation

> **User:** "Create a health pickup that heals the player for 25 when they walk over it, make it a green sphere, and place 3 of them in a line."
>
> **Claude Desktop:** Creates BP_HealthPickup via DSL, adds collision + sphere mesh + green material, spawns 3 instances at spaced positions.

---

## 15. Lessons Learned from Real Game Development

These were discovered while building a working pickup collector game entirely through the automated pipeline:

1. **DSL creates logic, not structure.** You need separate component commands for collision, meshes, and materials. Plan for both when designing a Blueprint.

2. **Overlap events need collision.** The most common "my Blueprint doesn't work" issue. Always add a collision component with generate_overlap_events=true.

3. **DefaultPawn breaks Cast To Character.** Use direct overlap handling or set up a proper Character class in your project.

4. **Save frequently.** Changes only exist in memory until save_all is called. A UE crash loses everything.

5. **Re-spawn after component changes.** Already-placed actors don't update when their Blueprint's SCS changes. Delete and re-spawn.

6. **The plugin handles type conversion automatically.** Float→String, Int→Float, etc. are inserted by TryCreateConnection. Don't add conversion nodes in your DSL — let the plugin handle it.

7. **Float is Double in UE 5.7.** The plugin auto-remaps Add_FloatFloat → Add_DoubleDouble etc. Write your DSL using Float names — the plugin translates.

8. **Use GetVar/SetVar explicitly.** The model generates better results when variables are accessed through explicit GetVar and SetVar nodes rather than shorthand direct references.

---

## 16. Compliance Tiers (Updated)

| Tier | Requirement | Description |
|---|---|---|
| **Basic** | Pass L01-L06 node types | Core events, flow control, variables, loops |
| **Advanced** | Pass full node set (179+ types) | All math, arrays, physics, UI, strings, all patterns |
| **Certified** | All eval tests at 90%+ similarity | Edge cases, complex systems, ambiguous prompts handled |
| **Production** | 98%+ syntax across 300+ prompts | Real-world reliability for automated pipelines |

---

## 17. Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-03-02 | Initial release covering v6 DSL spec, node types, connection patterns, common mistakes |
| 2.0 | 2026-03-05 | Added pipeline workflow, component management, materials, level population, MCP integration, lessons learned from real game development. Updated compliance tiers. Reflects v10 model (99.4% syntax) and full plugin capability (20 MCP tools). |

---

*This is a living document. As the model and plugin capabilities expand, new node types, patterns, and rules will be added. Check the version number to ensure you are referencing the latest spec.*
