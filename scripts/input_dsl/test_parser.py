"""Test for input_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from input_dsl.lexer import tokenize
from input_dsl.parser import parse
from input_dsl.validator import validate
from input_dsl.command_generator import generate
DSL = """INPUT: InputConfig_FPS
ACTION: IA_Move
  @type=Axis2D
ACTION: IA_Jump
  @type=Bool
ACTION: IA_Fire
  @type=Bool
MAPPING: IMC_Default
  MAP: IA_Move
    @key=W
    @modifiers=SwizzleYXZ
  MAP: IA_Jump
    @key=SpaceBar
  MAP: IA_Fire
    @key=LeftMouseButton"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("actions", []))
print(f"input_dsl: {tree['name']}, {n} actions, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
