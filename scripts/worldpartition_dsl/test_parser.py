"""Test for worldpartition_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worldpartition_dsl.lexer import tokenize
from worldpartition_dsl.parser import parse
from worldpartition_dsl.validator import validate
from worldpartition_dsl.command_generator import generate
DSL = """WORLD_PARTITION: WP_MainWorld
@cell_size=12800
@loading_range=25600
REGION: TownCenter
  @bounds=-5000,-5000,5000,5000
  @priority=High
  @always_loaded=true
DATA_LAYER: Interiors
  @type=Runtime
  @default_visible=false
HLOD: LowDetail
  @min_distance=50000
  @simplification=0.3"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("regions", []))
print(f"worldpartition_dsl: {tree['name']}, {n} regions, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
