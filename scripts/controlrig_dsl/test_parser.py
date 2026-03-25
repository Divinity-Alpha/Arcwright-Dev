"""Test for controlrig_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from controlrig_dsl.lexer import tokenize
from controlrig_dsl.parser import parse
from controlrig_dsl.validator import validate
from controlrig_dsl.command_generator import generate
DSL = """CONTROL_RIG: CR_Character
@skeleton=SK_Mannequin
IK_CHAIN: LeftArm
  @root=upperarm_l
  @tip=hand_l
  @pole_target=0,100,0
FK_CONTROL: Spine
  @bone=spine_01
  @limit_rotation=true
CONSTRAINT: LookAt
  @bone=head
  @target=LookTarget
  @axis=X"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("elements", []))
print(f"controlrig_dsl: {tree['name']}, {n} elements, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
