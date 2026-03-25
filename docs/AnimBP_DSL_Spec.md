# Arcwright — Animation Blueprint DSL Specification

> **Version:** 0.1 (Draft)
> **Last Updated:** 2026-03-07
> **Status:** Design phase — not yet implemented
> **Depends on:** AnimBP parser, AnimBP plugin builder, training data

## 1. Why Animation Blueprints

Every game with characters needs animation state machines. UE5's Animation Blueprints control which animation plays based on movement speed, jumping, attacking, dying. Without AnimBP support, characters are static T-poses.

AnimBPs are structured as state machines with transitions — similar to Behavior Trees but with a different topology: states have animations, transitions have conditions, and blend spaces interpolate between animations.

## 2. UE5 Animation Blueprint Architecture

**UAnimInstance** — The animation Blueprint class. Contains the AnimGraph and EventGraph.

**FAnimNode_StateMachine** — A state machine node in the AnimGraph. Contains states and transitions.

**FAnimStateNode** — A single state. References an animation asset or blend space.

**FAnimTransitionNode** — A transition between states. Has a condition (typically based on variables).

**FBlendSpace** — Blends between multiple animations based on 1D or 2D parameters (e.g. speed, direction).

**Skeleton** — The bone hierarchy that animations target. All animations in an AnimBP must share the same skeleton.

## 3. AnimBP DSL Structure

```
ANIMBLUEPRINT: <name>
SKELETON: <skeleton_asset_path>

VAR <name>: <type> = <default>

STATEMACHINE: <name>

STATE: <name> [Animation=<asset_path>]
STATE: <name> [BlendSpace=<asset_path>, Axis=<var_name>]
STATE: <name> [Animation=<asset_path>, Loop=true]

TRANSITION: <source_state> -> <target_state> [Condition=<expression>]
TRANSITION: <source_state> -> <target_state> [Condition=<expression>, Duration=<blend_time>]

DEFAULT: <state_name>
```

### Rules:
- `ANIMBLUEPRINT:` and `SKELETON:` are required at the top
- `VAR` declarations define variables that drive transitions (Speed, IsJumping, IsFalling, etc.)
- `STATEMACHINE:` starts a state machine definition (can have multiple)
- `STATE:` defines a state with an animation or blend space
- `TRANSITION:` defines a condition for moving between states
- `DEFAULT:` sets the initial state
- Conditions use simple expressions: `Speed > 0`, `IsJumping == true`, `Speed < 10 AND IsGrounded == true`

## 4. Variable Types

```
VAR Speed: Float = 0.0
VAR Direction: Float = 0.0
VAR IsJumping: Bool = false
VAR IsFalling: Bool = false
VAR IsGrounded: Bool = true
VAR IsSprinting: Bool = false
VAR IsAttacking: Bool = false
VAR IsDead: Bool = false
VAR Health: Float = 100.0
VAR AttackType: Int = 0
```

Variables are updated from the owning character's Blueprint via `GetAnimInstance()` → `SetFloatValue()` / `SetBoolValue()`.

## 5. Common Patterns

### Basic Locomotion (Walk/Run)

```
ANIMBLUEPRINT: ABP_Character
SKELETON: /Game/Characters/Mannequin/Skeleton

VAR Speed: Float = 0.0
VAR IsJumping: Bool = false
VAR IsFalling: Bool = false

STATEMACHINE: Locomotion

STATE: Idle [Animation=/Game/Animations/Idle_Anim, Loop=true]
STATE: Walk [Animation=/Game/Animations/Walk_Anim, Loop=true]
STATE: Run [Animation=/Game/Animations/Run_Anim, Loop=true]
STATE: Jump [Animation=/Game/Animations/Jump_Start]
STATE: Fall [Animation=/Game/Animations/Fall_Loop, Loop=true]
STATE: Land [Animation=/Game/Animations/Jump_Land]

TRANSITION: Idle -> Walk [Condition=Speed > 0, Duration=0.2]
TRANSITION: Walk -> Idle [Condition=Speed == 0, Duration=0.2]
TRANSITION: Walk -> Run [Condition=Speed > 300, Duration=0.2]
TRANSITION: Run -> Walk [Condition=Speed <= 300, Duration=0.2]
TRANSITION: Idle -> Jump [Condition=IsJumping == true, Duration=0.1]
TRANSITION: Walk -> Jump [Condition=IsJumping == true, Duration=0.1]
TRANSITION: Run -> Jump [Condition=IsJumping == true, Duration=0.1]
TRANSITION: Jump -> Fall [Condition=IsFalling == true, Duration=0.1]
TRANSITION: Fall -> Land [Condition=IsFalling == false, Duration=0.1]
TRANSITION: Land -> Idle [Condition=Speed == 0, Duration=0.2]
TRANSITION: Land -> Walk [Condition=Speed > 0, Duration=0.2]

DEFAULT: Idle
```

### Combat States

```
ANIMBLUEPRINT: ABP_Fighter
SKELETON: /Game/Characters/Fighter/Skeleton

VAR Speed: Float = 0.0
VAR IsAttacking: Bool = false
VAR IsDead: Bool = false
VAR AttackType: Int = 0

STATEMACHINE: Combat

STATE: Idle [Animation=/Game/Animations/Combat_Idle, Loop=true]
STATE: Move [Animation=/Game/Animations/Combat_Walk, Loop=true]
STATE: LightAttack [Animation=/Game/Animations/Attack_Light]
STATE: HeavyAttack [Animation=/Game/Animations/Attack_Heavy]
STATE: Death [Animation=/Game/Animations/Death]

TRANSITION: Idle -> Move [Condition=Speed > 0, Duration=0.15]
TRANSITION: Move -> Idle [Condition=Speed == 0, Duration=0.15]
TRANSITION: Idle -> LightAttack [Condition=IsAttacking == true AND AttackType == 1, Duration=0.1]
TRANSITION: Idle -> HeavyAttack [Condition=IsAttacking == true AND AttackType == 2, Duration=0.1]
TRANSITION: LightAttack -> Idle [Condition=IsAttacking == false, Duration=0.2]
TRANSITION: HeavyAttack -> Idle [Condition=IsAttacking == false, Duration=0.3]
TRANSITION: Idle -> Death [Condition=IsDead == true, Duration=0.1]
TRANSITION: Move -> Death [Condition=IsDead == true, Duration=0.1]

DEFAULT: Idle
```

### Blend Space Locomotion

```
ANIMBLUEPRINT: ABP_BlendLocomotion
SKELETON: /Game/Characters/Mannequin/Skeleton

VAR Speed: Float = 0.0
VAR Direction: Float = 0.0

STATEMACHINE: Movement

STATE: Idle [Animation=/Game/Animations/Idle, Loop=true]
STATE: Locomotion [BlendSpace=/Game/Animations/BS_Locomotion, AxisX=Direction, AxisY=Speed]
STATE: Jump [Animation=/Game/Animations/Jump]

TRANSITION: Idle -> Locomotion [Condition=Speed > 10, Duration=0.2]
TRANSITION: Locomotion -> Idle [Condition=Speed <= 10, Duration=0.2]

DEFAULT: Idle
```

## 6. Condition Expression Syntax

Conditions support simple boolean expressions:

```
Speed > 0
Speed == 0
IsJumping == true
Speed > 300 AND IsGrounded == true
IsFalling == false OR IsJumping == true
Health <= 0
AttackType == 1
```

Operators: `==`, `!=`, `>`, `<`, `>=`, `<=`
Combinators: `AND`, `OR`
No parentheses (kept simple for LLM generation)

## 7. Validation Checklist

- [ ] Starts with `ANIMBLUEPRINT:` 
- [ ] Has `SKELETON:` declaration with asset path
- [ ] Has at least one `STATEMACHINE:`
- [ ] Each state machine has at least 2 states
- [ ] Each state has an Animation or BlendSpace
- [ ] All transitions reference existing states
- [ ] All conditions reference declared variables
- [ ] Has a `DEFAULT:` state that exists
- [ ] No orphaned states (states with no transitions in or out, except DEFAULT)
- [ ] Transition conditions use valid syntax
- [ ] BlendSpace axes reference declared Float variables

## 8. Implementation Plan

### Phase 1: Parser
- `animbp_parser.py` — parse DSL to IR JSON
- Validate state machine structure, transition references, conditions
- Output IR: `{"name": ..., "skeleton": ..., "variables": [...], "state_machines": [...]}`

### Phase 2: Plugin Builder
- Create UAnimBlueprint asset referencing skeleton
- Create state machine nodes with states and transitions
- Set animation references on states
- Set transition rules from condition expressions
- TCP command: `create_anim_blueprint_from_dsl`

### Phase 3: Training
- AnimBP Lesson 01: locomotion, combat, blend spaces
- Expected: high accuracy since state machines are regular structures

### Phase 4: Integration
- Character Blueprint references AnimBP via SkeletalMeshComponent
- AnimBP variables updated from character EventGraph
- Template: "character with full locomotion AnimBP"

## 9. Version History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-03-07 | Initial draft — state machine structure, patterns, conditions |

---

*Draft specification. Requires animation assets in the project to be functional.*
