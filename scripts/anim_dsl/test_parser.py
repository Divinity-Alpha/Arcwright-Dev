"""Animation DSL Parser Test — no UE needed."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from anim_dsl.lexer import tokenize
from anim_dsl.parser import parse
from anim_dsl.validator import validate
from anim_dsl.command_generator import generate

DSL = """
ANIMBP: ABP_PlayerCharacter
SKELETON: /Game/Characters/Mannequins/Meshes/SKM_Manny
MESH: /Game/Characters/Mannequins/Meshes/SKM_Manny

VARIABLES:
  Speed: Float = 0.0
  IsJumping: Bool = false
  Direction: Float = 0.0

STATE_MACHINE: Locomotion

  STATE: Idle
    @entry: true
    @animation: /Game/Characters/Mannequins/Animations/MM_Idle
    @loop: true

  STATE: Walk
    @animation: /Game/Characters/Mannequins/Animations/MM_Walk_Fwd

  STATE: Run
    @animation: /Game/Characters/Mannequins/Animations/MM_Run_Fwd

  STATE: Jump
    @animation: /Game/Characters/Mannequins/Animations/MM_Jump

  TRANSITION: Idle -> Walk
    @condition: Speed > 0 && Speed < 300
    @blend_duration: 0.2

  TRANSITION: Walk -> Run
    @condition: Speed >= 300
    @blend_duration: 0.15

  TRANSITION: Run -> Walk
    @condition: Speed < 300 && Speed > 0
    @blend_duration: 0.2

  TRANSITION: Walk -> Idle
    @condition: Speed == 0
    @blend_duration: 0.25

  TRANSITION: Run -> Idle
    @condition: Speed == 0
    @blend_duration: 0.3

  TRANSITION: Idle -> Jump
    @condition: IsJumping == true
    @blend_duration: 0.1

  TRANSITION: Jump -> Idle
    @condition: IsJumping == false
    @blend_duration: 0.2

BLEND_SPACE: BS_Locomotion
  @type: 1D
  @axis_x: Speed
  @axis_x_min: 0
  @axis_x_max: 600
  SAMPLE: position=0 animation=/Game/Characters/Mannequins/Animations/MM_Idle
  SAMPLE: position=300 animation=/Game/Characters/Mannequins/Animations/MM_Walk_Fwd
  SAMPLE: position=600 animation=/Game/Characters/Mannequins/Animations/MM_Run_Fwd

MONTAGE: AM_Attack
  @animation: /Game/Characters/Mannequins/Animations/MM_Attack
  @slot: DefaultSlot
"""

print("=== Animation DSL Parser Test ===\n")

# Lexer
tokens = tokenize(DSL)
non_blank = [t for t in tokens if t.type not in ("BLANK", "COMMENT")]
print(f"[Lexer] {len(tokens)} tokens ({len(non_blank)} non-blank)")

# Parser
tree = parse(tokens)
print(f"[Parser] Name={tree['name']}, Skeleton={tree['skeleton'][:40]}")
print(f"  State machines: {len(tree['state_machines'])}")
for sm in tree['state_machines']:
    print(f"    {sm['name']}: {len(sm['states'])} states, {len(sm['transitions'])} transitions")
print(f"  Blend spaces: {len(tree['blend_spaces'])}")
print(f"  Montages: {len(tree['montages'])}")
print(f"  Variables: {len(tree['variables'])}")

# Validator
result = validate(tree)
print(f"[Validator] {len(result['errors'])} errors, {len(result['warnings'])} warnings")
for e in result['errors']: print(f"  ERROR: {e}")
for w in result['warnings']: print(f"  WARN: {w}")

# Command generator
commands = generate(tree)
print(f"\n[Commands] {len(commands)} total:")
for cmd in commands:
    brief = ", ".join(f"{k}={v}" for k, v in list(cmd["params"].items())[:3])
    print(f"  {cmd['command']:30s} {brief[:60]}")

ok = len(result['errors']) == 0
print(f"\n{'PASS' if ok else 'FAIL'} — {len(commands)} commands, {len(result['errors'])} errors")
sys.exit(0 if ok else 1)
