"""Physics test."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from physics_dsl.lexer import tokenize
from physics_dsl.parser import parse
from physics_dsl.validator import validate
from physics_dsl.command_generator import generate
DSL = """
PHYSICS: PHY_WoodenDoor
@actor=BP_Door
CONSTRAINT: DoorHinge
  @type=Hinge
  @component1=DoorFrame
  @component2=DoorPanel
  @angle_min=-120
  @angle_max=0
  @breakable=true
  @break_threshold=5000
CONSTRAINT: RopeAnchor
  @type=Ball
  @component1=Ceiling
  @component2=Chandelier
  @swing_limit=45
DESTRUCTIBLE: DoorPanel
  @health=100
  @on_break=SpawnFragments:3
  @on_break=PlaySound:SFX_WoodBreak
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
print(f"Physics: {tree['name']}, {len(tree['constraints'])} constraints, {len(tree['destructibles'])} destructibles, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r['errors'] else "FAIL")
