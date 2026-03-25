# Arcwright DSL — Best Practices for Blueprint Generation

> **Version:** 1.0
> **Last Updated:** 2026-03-02
> **Compatibility:** Arcwright DSL v1, UE 5.7 Plugin
> **Audience:** AI systems (Claude, GPT, etc.), third-party tool developers, compliance checker targets

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

## 10. Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-03-02 | Initial release covering v6 DSL spec, all proven node types, connection patterns, common mistakes |

---

*This is a living document. As the model and plugin capabilities expand, new node types, patterns, and rules will be added. Check the version number to ensure you are referencing the latest spec.*
