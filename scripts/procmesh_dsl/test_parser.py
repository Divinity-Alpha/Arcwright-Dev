import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from procmesh_dsl.lexer import tokenize
from procmesh_dsl.parser import parse
from procmesh_dsl.validator import validate
from procmesh_dsl.command_generator import generate
DSL = """
PROC_MESH: PM_Crystal
@collision=true
SHAPE: BaseCrystal
  @type=Cylinder
  @radius=20
SHAPE: SideRock
  @type=Sphere
  @radius=40
DEFORM: Noise
  @target=BaseCrystal
  @amplitude=3.0
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
ek = 'elements'
n = len(tree.get(ek, []))
print(f'procmesh_dsl: {tree["name"]}, {n} elements, {len(cmds)} commands, {len(r["errors"])} errors')
print('PASS' if not r['errors'] else 'FAIL')
