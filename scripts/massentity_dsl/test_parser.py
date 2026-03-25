"""Test for massentity_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from massentity_dsl.lexer import tokenize
from massentity_dsl.parser import parse
from massentity_dsl.validator import validate
from massentity_dsl.command_generator import generate
DSL = """MASS_CONFIG: ME_CrowdSim
ARCHETYPE: Civilian
  TRAIT: Transform
  TRAIT: Movement
    @speed=300
  TRAIT: Avoidance
    @radius=50
  TRAIT: SmartObject
    @search_radius=1000
PROCESSOR: MoveToTarget
  @requires=Transform,Movement
  @frequency=EveryFrame
SPAWNER: CrowdSpawner
  @archetype=Civilian
  @count=100
  @area=2000,2000
  @spawn_rate=10"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("archetypes", []))
print(f"massentity_dsl: {tree['name']}, {n} archetypes, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
