"""Test for smartobject_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from smartobject_dsl.lexer import tokenize
from smartobject_dsl.parser import parse
from smartobject_dsl.validator import validate
from smartobject_dsl.command_generator import generate
DSL = """SMART_OBJECT: SO_Chair
@actor=BP_Chair
SLOT: SitDown
  @type=Interaction
  @animation=AM_Sit_Loop
  @duration=30,60
  @tags_required=NPC.Civilian
SLOT: LeanOn
  @type=Interaction
  @duration=20,40"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("slots", []))
print(f"smartobject_dsl: {tree['name']}, {n} slots, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
