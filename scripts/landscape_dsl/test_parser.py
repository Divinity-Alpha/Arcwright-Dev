"""Test for landscape_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from landscape_dsl.lexer import tokenize
from landscape_dsl.parser import parse
from landscape_dsl.validator import validate
from landscape_dsl.command_generator import generate
DSL = """LANDSCAPE: LS_Terrain
@size=4033
@scale=100,100,200
LAYER: Grass
  @material=M_Grass
  @weight=1.0
LAYER: Rock
  @material=M_Rock
  @slope_min=30
  @slope_max=90
PAINT_RULE: SlopeBlend
  @source=Grass
  @target=Rock
  @slope_threshold=35
  @blend_width=10
WATER_BODY: River
  @type=River
  @width=500
  @depth=200"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("layers", []))
print(f"landscape_dsl: {tree['name']}, {n} layers, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
