# Arcwright AI Best Practices Guide
# This file teaches AI assistants (Claude, GPT, Cursor, etc.) how to use Arcwright correctly.
# Include this in your AI's context when working with Arcwright, or reference it via the
# get_arcwright_quickstart MCP teaching tool.
#
# Last updated: 2026-03-22
# Version: 2.0

---

## Rule Zero: Check Before Create

**NEVER create an asset without checking if it exists.**
**NEVER delete an actor you didn't create.**
**NEVER overwrite human changes.**

Use `StateManager` for all creation:
```python
from scripts.state_manager import StateManager

sm = StateManager()
sm.safe_create_blueprint("BP_Economy", "Actor")     # Creates only if needed
sm.safe_spawn_actor("Light_Main", x=0, y=0, z=290)  # Skips if exists
sm.safe_setup_lighting("outdoor_day")                # Skips if any DirectionalLight exists
sm.safe_create_material("MAT_Gold", {"r": 1, "g": 0.84, "b": 0})  # Skips if exists
sm.clean_duplicate_lights()                          # Removes extras, keeps one of each
sm.report()                                          # Shows project state + Arcwright manifest
```

After every build, `save_manifest()` records what Arcwright owns.
On subsequent runs, only missing or empty assets are created.
`clean_arcwright_assets()` deletes ONLY what Arcwright created — never human assets.

### First Build vs Iteration
- **First build:** StateManager creates everything (nothing exists yet)
- **Iteration:** StateManager skips existing BPs with >3 nodes, skips existing actors
- **Cleanup:** `clean_duplicate_lights()` fixes accumulated duplicates from prior builds

### Post-Phase Check (MANDATORY)

After EVERY build phase, run `post_phase_check()`. This catches duplicates, map errors,
and compile failures IMMEDIATELY instead of discovering them at the end.

```python
from scripts.check_and_confirm import CheckAndConfirm

cc = CheckAndConfirm()

# Phase 1: Data Tables
build_data_tables()
cc.post_phase_check("Data Tables")

# Phase 5: Blueprints
build_blueprints()
cc.post_phase_check("Blueprints")

# Phase 7: Level Setup
build_level()
cc.post_phase_check("Level Setup")  # Catches duplicate lights immediately
```

`post_phase_check` automatically:
- Removes duplicate DirectionalLights and SkyLights (keeps 1 of each)
- Removes duplicate manager actors (HUDManager, TimeManager, etc.)
- Runs `run_map_check` and reports errors
- Runs `verify_all_blueprints` and reports compile failures
- Saves after any fixes

---

## 1. Connection & Communication

### TCP Protocol
- Arcwright runs a TCP server on `localhost:13377`
- Send JSON commands terminated with `\n`
- Format: `{"command": "command_name", "params": {key: value}}\n`
- Response is JSON terminated with `\n`
- Always check `response.status` — "ok" means success, "error" means failure

### Connection Stability
- Reconnect every 30-40 commands as a safety measure
- If a command times out, reconnect and retry once before reporting failure
- The server sets TCP_NODELAY and 256KB buffers — large responses are fine

### DO NOT assume "ok" means the asset is complete
- `create_blueprint` returning "ok" means the asset FILE was created
- It does NOT mean nodes, variables, or connections were added
- Always verify critical assets by opening them or querying their contents

---

## 2. Blueprint Creation — CRITICAL

### The correct workflow for creating Blueprints with logic:

**Step 1: Create the Blueprint asset**
```json
{"command": "create_blueprint", "params": {"name": "BP_MyActor", "parent_class": "Actor"}}
```

**Step 2: Add variables (if needed)**
```json
{"command": "add_blueprint_variable", "params": {"blueprint": "BP_MyActor", "name": "Health", "type": "Float", "default": "100.0"}}
```

**Step 3: Add nodes in batch**
```json
{"command": "add_nodes_batch", "params": {"blueprint": "BP_MyActor", "nodes": [
  {"id": "1", "type": "K2Node_Event", "event": "ReceiveBeginPlay", "position": [0, 0]},
  {"id": "2", "type": "K2Node_CallFunction", "function": "/Script/Engine.KismetSystemLibrary.PrintString", "position": [300, 0], "params": {"InString": "Hello!"}}
]}}
```

**Step 4: Wire connections in batch**
```json
{"command": "add_connections_batch", "params": {"blueprint": "BP_MyActor", "connections": [
  {"from_node": "1", "from_pin": "then", "to_node": "2", "to_pin": "execute"}
]}}
```

**Step 5: Compile**
```json
{"command": "compile_blueprint", "params": {"blueprint": "BP_MyActor"}}
```

### OR use the single-command IR JSON approach:
```json
{"command": "import_from_ir", "params": {"ir": "{\"metadata\":{\"name\":\"BP_MyActor\",\"parent_class\":\"Actor\"},\"variables\":[],\"nodes\":[...],\"connections\":[...]}"}}
```

### CRITICAL: IR JSON format
The IR JSON MUST use the metadata wrapper:
```json
{
  "metadata": {"name": "BP_Name", "parent_class": "Actor"},
  "variables": [...],
  "nodes": [...],
  "connections": [...]
}
```

**WRONG** (will crash or create empty Blueprint):
```json
{"blueprint_name": "BP_Name", "parent_class": "Actor", "nodes": [...]}
```

### Known pin naming quirks:
- **Sequence node**: Output pins are named `then 0`, `then 1`, `then 2` (with a space, not underscore). If connections fail, try both `"then 0"` and `"then_0"`.
- **FlipFlop**: Outputs are `A` and `B`, not `True`/`False`
- **ForLoop**: Outputs are `LoopBody` and `Completed`, index is `Index`
- **Branch**: Outputs are `True` and `False` (capital T and F)

### Supported node types:
| Node Type | K2Node Class | Use For |
|---|---|---|
| Event | K2Node_Event | BeginPlay, Tick, ActorBeginOverlap, AnyDamage |
| CustomEvent | K2Node_CustomEvent | User-defined events (two-pass: definition then call) |
| CallFunction | K2Node_CallFunction | Any UFunction — PrintString, math, gameplay statics |
| Branch | K2Node_IfThenElse | If/then/else flow control |
| Sequence | K2Node_ExecutionSequence | Execute multiple outputs in order |
| ForLoop | K2Node_ForLoop | For loop (macro) |
| ForEachLoop | K2Node_ForEachLoop | Iterate arrays |
| WhileLoop | K2Node_WhileLoop | While loop |
| VariableGet | K2Node_VariableGet | Read a variable |
| VariableSet | K2Node_VariableSet | Write a variable |
| SpawnActor | K2Node_SpawnActorFromClass | Spawn actor at runtime |
| Cast | K2Node_DynamicCast | Cast to a specific class |
| SwitchInt | K2Node_SwitchInteger | Switch on integer |
| SwitchString | K2Node_SwitchString | Switch on string |
| BreakStruct | K2Node_BreakStruct | Break a struct into pins |
| InputAction | K2Node_InputAction | Respond to input action |
| FlipFlop | FlipFlop macro | Alternates between two outputs |
| DoOnce | DoOnce macro | Execute only once |
| Gate | Gate macro | Controllable gate |
| MultiGate | MultiGate macro | Route to multiple outputs |

### Blueprint Build Sequence (CRITICAL)

```
create_blueprint (with variables)
    → compile_blueprint (skeleton — resolves variable references)
    → add_nodes_batch
    → add_connections_batch
    → compile_blueprint (final)
```

The **skeleton compile** between variable creation and node addition is **REQUIRED**.
Without it, `GetVar`/`SetVar` nodes cannot resolve variable references and will error
with "Could not find a function named VariableGet".

### Node IDs in add_nodes_batch:
- You can use ANY custom string as node IDs: "evt", "branch", "myNode", etc.
- These IDs are stored internally and used by add_connections_batch to wire nodes
- The handler accepts both `{"id": "evt", "type": "K2Node_Event"}` and `{"node_id": "evt", "node_type": "K2Node_Event"}`

### Connection field names in add_connections_batch:
All three formats work:
```json
{"from_node": "evt", "from_pin": "then", "to_node": "branch", "to_pin": "execute"}
{"source_node": "evt", "source_pin": "then", "target_node": "branch", "target_pin": "execute"}
{"src_node": "evt", "src_pin": "then", "dst_node": "branch", "dst_pin": "execute"}
```
**Recommended: use `from_node` / `to_node` format — it's the most readable.**

### Node type shorthand:
You can use full K2Node class names or shortcuts:
- `"K2Node_Event"` or `"Event"` or `"Event_ReceiveBeginPlay"`
- `"K2Node_IfThenElse"` or `"Branch"`
- `"K2Node_CallFunction"` or `"CallFunction"` or `"PrintString"` (function name as shorthand)
- `"K2Node_VariableGet"` or `"VariableGet"` or `"GetVar"`
- `"K2Node_VariableSet"` or `"VariableSet"` or `"SetVar"`

**Variable node shorthand:** Use the `variable` key for cleaner syntax:
```json
{"id": "get_hp", "type": "GetVar", "variable": "Health"}
{"id": "set_hp", "type": "SetVar", "variable": "Health"}
```

### Custom Event Parameters

Custom events can have typed output pins. Use array format for `params`:
```json
{"id": "add_cash", "type": "CustomEvent", "event": "AddCash",
 "params": [{"name": "Amount", "type": "Float"}]}
```

Supported parameter types: `Float`, `Int`, `Bool`, `String`, `Name`, `Vector`, `Rotator`, `Text`

The parameter appears as an output pin on the event node. Wire it like any data pin:
```json
{"from_node": "add_cash", "from_pin": "Amount", "to_node": "add_math", "to_pin": "B"}
```

**Important:** When reading a variable AFTER setting it (for display), use a **separate GetVar node**
instead of reading from the SetVar output pin. SetVar's variable pin name is ambiguous (input vs output).

### Pin naming conventions:
- Execution pins: "execute" (input), "then" (output)
- Branch: "Condition" (input bool), "True" (output), "False" (output)
- ForLoop: "FirstIndex", "LastIndex", "LoopBody", "Index", "Completed"
- Function params: match the UFunction parameter names exactly
- Return value: "ReturnValue"

### CallFunction supports ANY UFunction path
Format: `/Script/<Module>.<Class>:<FunctionName>`

The C++ handler calls `SetFromFunction()` which auto-creates ALL pins. You don't need to define pins manually — just provide the correct path and wire to the auto-generated pin names.

### Complete UFunction Path Reference

**System / Utility:**
```
/Script/Engine.KismetSystemLibrary:PrintString
/Script/Engine.KismetSystemLibrary:Delay
/Script/Engine.KismetSystemLibrary:SetTimerByFunctionName
/Script/Engine.KismetSystemLibrary:ClearTimerByFunctionName
/Script/Engine.KismetSystemLibrary:IsValid
/Script/Engine.KismetSystemLibrary:IsValidClass
/Script/Engine.KismetSystemLibrary:GetDisplayName
/Script/Engine.KismetSystemLibrary:GetObjectName
/Script/Engine.KismetSystemLibrary:LineTraceSingle
/Script/Engine.KismetSystemLibrary:SphereTraceSingle
/Script/Engine.KismetSystemLibrary:BoxTraceSingle
```

**Math (NOTE: UE5 uses Double not Float):**
```
/Script/Engine.KismetMathLibrary:Add_DoubleDouble
/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble
/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble
/Script/Engine.KismetMathLibrary:Divide_DoubleDouble
/Script/Engine.KismetMathLibrary:Clamp
/Script/Engine.KismetMathLibrary:FClamp
/Script/Engine.KismetMathLibrary:Min
/Script/Engine.KismetMathLibrary:Max
/Script/Engine.KismetMathLibrary:Abs
/Script/Engine.KismetMathLibrary:RandomIntegerInRange
/Script/Engine.KismetMathLibrary:RandomFloatInRange
/Script/Engine.KismetMathLibrary:Lerp
/Script/Engine.KismetMathLibrary:FInterpTo
/Script/Engine.KismetMathLibrary:MapRangeUnclamped
/Script/Engine.KismetMathLibrary:MapRangeClamped
/Script/Engine.KismetMathLibrary:Percent_DoubleDouble
/Script/Engine.KismetMathLibrary:Sqrt
/Script/Engine.KismetMathLibrary:Power
/Script/Engine.KismetMathLibrary:Sin
/Script/Engine.KismetMathLibrary:Cos
```

**Comparison / Logic:**
```
/Script/Engine.KismetMathLibrary:EqualEqual_DoubleDouble
/Script/Engine.KismetMathLibrary:NotEqual_DoubleDouble
/Script/Engine.KismetMathLibrary:Greater_DoubleDouble
/Script/Engine.KismetMathLibrary:Less_DoubleDouble
/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble
/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble
/Script/Engine.KismetMathLibrary:BooleanAND
/Script/Engine.KismetMathLibrary:BooleanOR
/Script/Engine.KismetMathLibrary:Not_PreBool
/Script/Engine.KismetMathLibrary:EqualEqual_IntInt
/Script/Engine.KismetMathLibrary:EqualEqual_StrStr
```

**String Operations:**
```
/Script/Engine.KismetStringLibrary:Concat_StrStr
/Script/Engine.KismetStringLibrary:Contains
/Script/Engine.KismetStringLibrary:Len
/Script/Engine.KismetStringLibrary:Left
/Script/Engine.KismetStringLibrary:Right
/Script/Engine.KismetStringLibrary:Mid
/Script/Engine.KismetStringLibrary:Replace
/Script/Engine.KismetStringLibrary:ToUpper
/Script/Engine.KismetStringLibrary:ToLower
/Script/Engine.KismetStringLibrary:Conv_IntToString
/Script/Engine.KismetStringLibrary:Conv_DoubleToString
/Script/Engine.KismetStringLibrary:Conv_BoolToString
/Script/Engine.KismetTextLibrary:Conv_StringToText
```

**Array Operations:**
```
/Script/Engine.KismetArrayLibrary:Array_Add
/Script/Engine.KismetArrayLibrary:Array_Remove
/Script/Engine.KismetArrayLibrary:Array_RemoveItem
/Script/Engine.KismetArrayLibrary:Array_Contains
/Script/Engine.KismetArrayLibrary:Array_Find
/Script/Engine.KismetArrayLibrary:Array_Length
/Script/Engine.KismetArrayLibrary:Array_Clear
/Script/Engine.KismetArrayLibrary:Array_Get
/Script/Engine.KismetArrayLibrary:Array_Set
/Script/Engine.KismetArrayLibrary:Array_IsValidIndex
/Script/Engine.KismetArrayLibrary:Array_Shuffle
/Script/Engine.KismetArrayLibrary:Array_Random
```

**Actor / Component:**
```
/Script/Engine.Actor:GetActorLocation
/Script/Engine.Actor:SetActorLocation
/Script/Engine.Actor:GetActorRotation
/Script/Engine.Actor:SetActorRotation
/Script/Engine.Actor:SetActorTransform
/Script/Engine.Actor:GetActorForwardVector
/Script/Engine.Actor:GetActorScale3D
/Script/Engine.Actor:SetActorScale3D
/Script/Engine.Actor:SetActorHiddenInGame
/Script/Engine.Actor:SetActorEnableCollision
/Script/Engine.Actor:K2_DestroyActor
/Script/Engine.Actor:GetDistanceTo
/Script/Engine.Actor:IsOverlappingActor
/Script/Engine.Actor:GetComponentByClass
/Script/Engine.Actor:GetComponentsByClass
/Script/Engine.Actor:AddActorLocalOffset
/Script/Engine.Actor:AddActorLocalRotation
/Script/Engine.Actor:SetLifeSpan
/Script/Engine.Actor:GetInstigator
/Script/Engine.Actor:SetOwner
```

**Gameplay Statics (World Functions):**
```
/Script/Engine.GameplayStatics:GetPlayerCharacter
/Script/Engine.GameplayStatics:GetPlayerController
/Script/Engine.GameplayStatics:GetPlayerPawn
/Script/Engine.GameplayStatics:GetPlayerCameraManager
/Script/Engine.GameplayStatics:GetGameMode
/Script/Engine.GameplayStatics:GetGameInstance
/Script/Engine.GameplayStatics:GetGameState
/Script/Engine.GameplayStatics:ApplyDamage
/Script/Engine.GameplayStatics:ApplyRadialDamage
/Script/Engine.GameplayStatics:PlaySoundAtLocation
/Script/Engine.GameplayStatics:PlaySound2D
/Script/Engine.GameplayStatics:SpawnSoundAtLocation
/Script/Engine.GameplayStatics:SpawnEmitterAtLocation
/Script/Engine.GameplayStatics:GetWorldDeltaSeconds
/Script/Engine.GameplayStatics:GetTimeSeconds
/Script/Engine.GameplayStatics:GetRealTimeSeconds
/Script/Engine.GameplayStatics:SetGamePaused
/Script/Engine.GameplayStatics:IsGamePaused
/Script/Engine.GameplayStatics:GetAllActorsOfClass
/Script/Engine.GameplayStatics:GetAllActorsWithTag
/Script/Engine.GameplayStatics:FinishSpawningActor
/Script/Engine.GameplayStatics:OpenLevel
/Script/Engine.GameplayStatics:GetCurrentLevelName
/Script/Engine.GameplayStatics:SaveGameToSlot
/Script/Engine.GameplayStatics:LoadGameFromSlot
/Script/Engine.GameplayStatics:DoesSaveGameExist
/Script/Engine.GameplayStatics:CreateSaveGameObject
/Script/Engine.GameplayStatics:ProjectWorldLocationToScreen
```

**Widget / UI (Runtime):**
```
/Script/UMG.WidgetBlueprintLibrary:Create
/Script/UMG.UserWidget:AddToViewport
/Script/UMG.UserWidget:RemoveFromParent
/Script/UMG.UserWidget:SetVisibility
/Script/UMG.UserWidget:IsInViewport
/Script/UMG.WidgetBlueprintLibrary:GetAllWidgetsOfClass
/Script/UMG.TextBlock:SetText
/Script/UMG.ProgressBar:SetPercent
/Script/UMG.Image:SetColorAndOpacity
/Script/UMG.Image:SetBrushFromTexture
```

**Physics:**
```
/Script/Engine.PrimitiveComponent:AddForce
/Script/Engine.PrimitiveComponent:AddImpulse
/Script/Engine.PrimitiveComponent:AddTorque
/Script/Engine.PrimitiveComponent:SetSimulatePhysics
/Script/Engine.PrimitiveComponent:SetCollisionEnabled
/Script/Engine.PrimitiveComponent:SetCollisionResponseToChannel
/Script/Engine.PrimitiveComponent:GetPhysicsLinearVelocity
/Script/Engine.PrimitiveComponent:SetPhysicsLinearVelocity
```

**Character / Movement:**
```
/Script/Engine.Character:Jump
/Script/Engine.Character:StopJumping
/Script/Engine.Character:LaunchCharacter
/Script/Engine.CharacterMovementComponent:SetMovementMode
/Script/Engine.CharacterMovementComponent:GetMaxSpeed
/Script/Engine.CharacterMovementComponent:SetMaxWalkSpeed
/Script/Engine.PawnMovementComponent:GetInputVector
```

**AI:**
```
/Script/AIModule.AIController:MoveToLocation
/Script/AIModule.AIController:MoveToActor
/Script/AIModule.AIController:StopMovement
/Script/AIModule.AIController:RunBehaviorTree
/Script/AIModule.AIController:UseBlackboardData
/Script/AIModule.BlackboardComponent:SetValueAsFloat
/Script/AIModule.BlackboardComponent:SetValueAsBool
/Script/AIModule.BlackboardComponent:SetValueAsString
/Script/AIModule.BlackboardComponent:SetValueAsVector
/Script/AIModule.BlackboardComponent:SetValueAsObject
/Script/AIModule.BlackboardComponent:GetValueAsFloat
/Script/AIModule.BlackboardComponent:GetValueAsBool
```

**Data Table Access:**
```
/Script/Engine.DataTableFunctionLibrary:GetDataTableRowFromName
/Script/Engine.DataTableFunctionLibrary:GetDataTableRowNames
/Script/Engine.DataTableFunctionLibrary:DoesDataTableRowExist
```

**Vector / Transform Math:**
```
/Script/Engine.KismetMathLibrary:MakeVector
/Script/Engine.KismetMathLibrary:BreakVector
/Script/Engine.KismetMathLibrary:MakeRotator
/Script/Engine.KismetMathLibrary:BreakRotator
/Script/Engine.KismetMathLibrary:MakeTransform
/Script/Engine.KismetMathLibrary:BreakTransform
/Script/Engine.KismetMathLibrary:Add_VectorVector
/Script/Engine.KismetMathLibrary:Subtract_VectorVector
/Script/Engine.KismetMathLibrary:Multiply_VectorFloat
/Script/Engine.KismetMathLibrary:VSize
/Script/Engine.KismetMathLibrary:Normal
/Script/Engine.KismetMathLibrary:Dot_VectorVector
/Script/Engine.KismetMathLibrary:Cross_VectorVector
/Script/Engine.KismetMathLibrary:FindLookAtRotation
/Script/Engine.KismetMathLibrary:GetForwardVector
/Script/Engine.KismetMathLibrary:GetRightVector
/Script/Engine.KismetMathLibrary:GetUpVector
```

**Rendering / Camera:**
```
/Script/Engine.GameplayStatics:GetPlayerCameraManager
/Script/Engine.PlayerCameraManager:GetCameraLocation
/Script/Engine.PlayerCameraManager:GetCameraRotation
/Script/Engine.SceneComponent:SetWorldLocation
/Script/Engine.SceneComponent:SetWorldRotation
/Script/Engine.SceneComponent:SetRelativeLocation
/Script/Engine.SceneComponent:SetRelativeRotation
/Script/Engine.SceneComponent:GetWorldLocation
/Script/Engine.SceneComponent:GetWorldRotation
/Script/Engine.SceneComponent:SetVisibility
```

**Material (Runtime):**
```
/Script/Engine.PrimitiveComponent:SetMaterial
/Script/Engine.PrimitiveComponent:GetMaterial
/Script/Engine.PrimitiveComponent:CreateDynamicMaterialInstance
/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue
/Script/Engine.MaterialInstanceDynamic:SetVectorParameterValue
/Script/Engine.MaterialInstanceDynamic:SetTextureParameterValue
```

### How to find ANY UFunction path:
1. Open UE5, open a Blueprint, right-click in the graph
2. Search for the node you want (e.g., "Set Timer")
3. Place it, then hover over it — the tooltip shows the function path
4. Or use: `Get All Functions Of Class` in the reflection system
5. The format is always: `/Script/<Module>.<ClassName>:<FunctionName>`

---

## 3. Widget UI Creation

### The correct workflow:

**Step 1: Create the Widget Blueprint**
```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_MyHUD"}}
```

**Step 2: Add a root Canvas Panel**
```json
{"command": "add_widget_child", "params": {"widget_name": "WBP_MyHUD", "type": "CanvasPanel", "name": "Root"}}
```

**Step 3: Add child widgets**
```json
{"command": "add_widget_child", "params": {"widget_name": "WBP_MyHUD", "type": "TextBlock", "name": "TitleText", "parent": "Root"}}
```

**Step 4: Set properties**
```json
{"command": "set_widget_property", "params": {"widget_name": "WBP_MyHUD", "target": "TitleText", "property": "Text", "value": "My Game"}}
```

### Widget types supported:
TextBlock, ProgressBar, Image, Button, VerticalBox, HorizontalBox, CanvasPanel, Overlay, SizeBox, Border, Spacer, ScrollBox, CheckBox, EditableTextBox

### Anchoring:
Use `set_widget_anchor` with presets: TopLeft, TopCenter, TopRight, CenterLeft, Center, CenterRight, BottomLeft, BottomCenter, BottomRight, TopFill, BottomFill, LeftFill, RightFill, Fill

### Styling tips for game UIs:
- Use the Widget DSL theme system — 8 built-in themes (SciFi, Medieval, Racing, Fighting, Simulation, Normal, Horror, Cartoon)
- Color values are hex strings: "#FF3A5C"
- Font sizes are integers
- Always set anchor and offset for Canvas Panel children

---

## 4. Data Table Creation

### The correct workflow:

**Step 1: Create the table with column schema**
```json
{"command": "create_data_table", "params": {
  "name": "DT_Weapons",
  "columns": {"WeaponID": "Name", "Damage": "Float", "FireRate": "Float", "AmmoCapacity": "Integer", "WeaponName": "String"}
}}
```

**Step 2: Add rows**
```json
{"command": "add_data_table_row", "params": {
  "table_name": "DT_Weapons",
  "row_name": "Pistol",
  "values": {"WeaponID": "Pistol", "Damage": 25.0, "FireRate": 0.3, "AmmoCapacity": 12, "WeaponName": "M1911"}
}}
```

### Important: 
- `row_name` is the row identifier — must be unique per table
- `values` is a dict, NOT a JSON string
- Column types: Name, String, Float, Integer, Bool
- The first column is typically the row key

---

## 5. Spawning & Level Building

### Spawn an actor from a Blueprint:
```json
{"command": "spawn_actor_at", "params": {"blueprint": "BP_MyActor", "label": "MyActor_01", "x": 100, "y": 200, "z": 0}}
```

### Spawn a basic mesh:
```json
{"command": "spawn_actor_at", "params": {"label": "Floor", "x": 0, "y": 0, "z": 0, "mesh": "/Engine/BasicShapes/Cube", "scale_x": 10, "scale_y": 10, "scale_z": 0.1}}
```

### Apply materials:
```json
{"command": "apply_material", "params": {"actor": "Floor", "material": "M_MyMaterial"}}
```

### Set properties:
```json
{"command": "set_actor_property", "params": {"actor": "MyActor_01", "property": "Mobility", "value": "Movable"}}
```

### Player Start:
- Find existing: `find_actors` with class_name "PlayerStart"
- Move it: `set_actor_transform` with x, y, z, yaw
- The player spawns here on Play

### Game Mode:
- Set via: `set_game_mode` with game_mode parameter
- The GameMode Blueprint controls what player controller and HUD are used

---

## 6. Common Mistakes to Avoid

### Blueprint creation:
- ❌ Sending `{"blueprint_name": "BP_Test"}` — WRONG field name, will crash
- ✅ Sending `{"metadata": {"name": "BP_Test", "parent_class": "Actor"}}` — correct IR format
- ❌ Creating a Blueprint and assuming it has nodes — it starts EMPTY
- ✅ Always add nodes and connections after creation
- ❌ Using `create_blueprint("Make a health system")` as natural language — the command takes structured params, not descriptions
- ✅ Design the Blueprint logic yourself, then express it as nodes and connections

### Default Event Nodes — DO NOT CREATE DUPLICATES

`create_blueprint` automatically creates these default event nodes:
- `node_0`: Event ReceiveBeginPlay
- `node_1`: Event ActorBeginOverlap (if parent has collision)
- `node_2`: Event ReceiveTick

**DO NOT** create these again in `add_nodes_batch`. If you do, UE creates
a duplicate "Event None" that never fires. Instead, wire directly
to `node_0`, `node_1`, `node_2`.

**WRONG** (creates broken duplicate):
```json
{"command": "add_nodes_batch", "params": {"blueprint": "BP_MyActor", "nodes": [
  {"id": "overlap", "type": "Event_ActorBeginOverlap"}
]}}
{"command": "add_connections_batch", "params": {"blueprint": "BP_MyActor", "connections": [
  {"from_node": "overlap", "from_pin": "then", "to_node": "print1", "to_pin": "execute"}
]}}
```

**RIGHT** (wires the real auto-created event):
```json
{"command": "add_nodes_batch", "params": {"blueprint": "BP_MyActor", "nodes": [
  {"id": "print1", "type": "PrintString", "params": {"InString": "Overlap!"}}
]}}
{"command": "add_connections_batch", "params": {"blueprint": "BP_MyActor", "connections": [
  {"from_node": "node_1", "from_pin": "then", "to_node": "print1", "to_pin": "execute"}
]}}

### Widget creation:
- ❌ Adding children without a root CanvasPanel — widgets need a layout parent
- ✅ Always create CanvasPanel "Root" first, then add children to it
- ❌ Setting position directly — use anchors and offsets instead
- ✅ Use `set_widget_anchor` with named presets

### Data Tables:
- ❌ Passing `values` as a JSON string: `"values": "{\"key\": \"val\"}"`
- ✅ Passing `values` as a dict: `"values": {"key": "val"}`

### Spawning Blueprint Actors vs Plain Meshes

If a Blueprint has logic (overlap events, variables, custom events),
you MUST spawn it as a Blueprint instance, not a plain mesh:

**WRONG** (no Blueprint logic runs — it's just a static cube):
```json
{"command": "spawn_actor_at", "params": {"label": "Station_X", "mesh": "/Engine/BasicShapes/Cube"}}
```

**RIGHT** (Blueprint logic is active — overlap events, variables, BeginPlay all fire):
```json
{"command": "spawn_actor_at", "params": {
  "class": "/Game/Arcwright/Generated/BP_StationBase.BP_StationBase_C",
  "label": "Station_X", "x": 0, "y": 0, "z": 50
}}
```

After spawning, set Blueprint variables on the placed actor:
```json
{"command": "set_variable_default", "params": {"blueprint": "BP_StationBase", "variable": "StationName", "value": "Degriming"}}
```

### Actor spawning:
- ❌ Spawning actors at z=0 when the floor is at z=0 — actors clip into floor
- ✅ Spawn actors slightly above the floor (z=50 or higher)
- ❌ Forgetting to save: changes are in-memory until `save_all` is called
- ✅ Call `save_all` after building a batch of assets

### Materials:
- ❌ Applying a material that doesn't exist yet
- ✅ Create the material first with `create_material_graph`, then apply it

### Widget Blueprint Reparenting — Conflicting Functions

When reparenting a Widget Blueprint to a C++ parent class, any Blueprint
function that has the same name as a C++ function in the parent will cause
a compile error.

**SYMPTOMS:**
- "The function name in node X is already used"
- "Overridden function is not compatible with parent function"

**CAUSE:**
The Blueprint has a function (e.g., `SetInteractionPrompt`) and the C++
parent class also has a function with the same name.

**FIX — use `reparent_widget_blueprint`:**
```json
{"command": "reparent_widget_blueprint", "params": {
  "name": "WBP_MainHUD", "new_parent": "BSMainHUDWidget"
}}
```
This command automatically:
1. Scans for functions that conflict with the new parent
2. Removes Blueprint functions that clash with non-overridable C++ functions
3. Keeps Blueprint functions that override `BlueprintImplementableEvent` (safe)
4. Reparents, compiles, and saves

Returns `conflicts_resolved` array showing what was fixed.

**PREVENTION for C++ parent classes:**
- Use `BlueprintImplementableEvent` for functions Blueprint should own
- Use `BlueprintNativeEvent` if C++ needs a default (Blueprint overrides via `_Implementation`)
- Never use plain `BlueprintCallable` for functions Blueprint might also define

### General:
- ❌ Putting function path in params.FunctionReference — the handler ignores it
- ✅ Put the function path AS the node type: `{"type": "/Script/Engine.KismetSystemLibrary:PrintString"}`
- ❌ Sending 200+ commands without reconnecting — connection may drop
- ✅ Reconnect every 30-40 commands
- ❌ Assuming the level has content — a new project has an empty default level
- ✅ Build the environment (floor, walls, lights) before placing gameplay objects
- ❌ Pressing Play expecting to see results without setting GameMode and placing actors
- ✅ Set GameMode, place PlayerStart, spawn actors, add HUD manager, then Play

---

## 7. Recommended Build Order for a New Game

1. **Data Tables** first — define your game data (weapons, enemies, items, stats)
2. **Input System** — set up controls
3. **Gameplay Tags** — tag hierarchy for your systems
4. **Materials** — create visual materials
5. **Level Environment** — floor, walls, lights, player start
6. **Blueprints** — game logic (managers, controllers, gameplay)
7. **Widget UIs** — HUD, menus, panels
8. **Dialogue & Quests** — narrative content
9. **Sound Design** — audio environment
10. **Animation** — character animation (if applicable)
11. **Level Sequences** — cinematics
12. **Wire everything** — set GameMode, spawn managers, add HUD
13. **Save and test** — `save_all`, then Play in Editor

### Screenshot Limitation

`take_viewport_screenshot` and `get_player_view` capture the 3D scene only.
They do **NOT** capture the UMG widget overlay (HUD elements, menus, text).

To verify HUDs programmatically:
1. **`get_widget_tree`** — check the design-time widget hierarchy exists
2. **`get_output_log`** during PIE — confirm "HUD Active" or CreateWidget log messages
3. **`get_viewport_widgets`** during PIE — check runtime widget instances in viewport (class, visibility, children with text/percent values)
4. **Manual verification** — human confirms HUD visible in game window

```json
// Design-time: verify widget structure
{"command": "get_widget_tree", "params": {"widget_blueprint": "WBP_GameHUD"}}

// Runtime (during PIE): verify widget is live in viewport
{"command": "get_viewport_widgets", "params": {}}
// Returns: {"widgets": [{"class": "WBP_GameHUD_C", "in_viewport": true, "visible": true, "children": [...]}]}
```

---

## 8. Debugging

### Check what exists:
```json
{"command": "find_blueprints"}
{"command": "find_actors"}
{"command": "find_assets", "params": {"class_name": "DataTable"}}
{"command": "get_level_info"}
{"command": "get_widget_tree", "params": {"widget_name": "WBP_MyHUD"}}
```

### If a Blueprint is empty:
- It was created but nodes weren't added
- Use `add_nodes_batch` and `add_connections_batch` to populate it
- Then `compile_blueprint` to compile

### If nothing shows on Play:
- Check GameMode is set: `get_game_mode`
- Check PlayerStart exists and is positioned correctly
- Check actors are actually in the level: `find_actors`
- Check the HUD is being created on BeginPlay
- Check lighting exists — no lights = black screen

### If commands return "error":
- Read the error message — it usually tells you exactly what's wrong
- Common: asset not found (wrong name), invalid parameter type, missing required param

---

## 9. Teaching Tools

Call these MCP tools to learn DSL formats on demand:
- `get_arcwright_quickstart` — overview of all capabilities
- `get_blueprint_dsl_guide` — Blueprint IR JSON format with examples
- `get_animation_dsl_guide` — Animation Blueprint DSL format
- `get_material_dsl_guide` — Material Graph DSL format
- `get_widget_dsl_guide` — Widget UI DSL format (if available)
- `get_dialogue_dsl_guide` — Dialogue Tree format
- `get_quest_dsl_guide` — Quest System format
- `get_sequence_dsl_guide` — Level Sequence format
- `get_gas_dsl_guide` — Gameplay Ability System format
- `get_tags_dsl_guide` — Gameplay Tags format
- `get_input_dsl_guide` — Enhanced Input format
- `get_perception_dsl_guide` — AI Perception format
- `get_physics_dsl_guide` — Physics Constraints format
- `get_sound_dsl_guide` — Sound Design format
- `get_replication_dsl_guide` — Multiplayer Replication format
- And more — one guide per DSL system

Each guide returns the format spec, valid types, and working examples.

---

## 10. Performance Tips

- Batch operations are faster than individual commands (use add_nodes_batch, not individual add_node calls)
- Create all Data Tables before Blueprints (Blueprints may reference table data)
- Create materials before applying them to actors
- Save periodically with save_all — don't wait until the end
- Use find_actors to verify placement before moving on to the next system
