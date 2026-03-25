"""Test for foliage_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from foliage_dsl.lexer import tokenize
from foliage_dsl.parser import parse
from foliage_dsl.validator import validate
from foliage_dsl.command_generator import generate
DSL = """FOLIAGE_CONFIG: FC_Forest
FOLIAGE_TYPE: Trees
  @mesh=SM_Oak_Tree
  @density=0.01
  @min_scale=0.8
  @max_scale=1.3
  @align_to_surface=true
FOLIAGE_TYPE: Bushes
  @mesh=SM_Bush
  @density=0.05
  @cluster_radius=200
PLACEMENT_RULE: NearWater
  @type=Trees
  @boost_near=WaterBody
  @boost_radius=500
  @boost_factor=2.0
EXCLUSION_ZONE: Roads
  @shape=Spline
  @radius=300"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("types", []))
print(f"foliage_dsl: {tree['name']}, {n} types, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
