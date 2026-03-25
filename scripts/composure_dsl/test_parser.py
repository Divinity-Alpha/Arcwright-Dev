import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from composure_dsl.lexer import tokenize
from composure_dsl.parser import parse
from composure_dsl.validator import validate
from composure_dsl.command_generator import generate
DSL = """
COMPOSURE: COMP_GreenScreen
ELEMENT: CameraPlate
  @type=MediaPlate
ELEMENT: CGBackground
  @type=CapturePass
PASS: ChromaKey
  @type=ChromaKeyer
  @key_color=0,1,0
COMPOSITE: FinalOutput
  @layers=CGBackground,CameraPlate
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
ek = 'elements'
n = len(tree.get(ek, []))
print(f'composure_dsl: {tree["name"]}, {n} elements, {len(cmds)} commands, {len(r["errors"])} errors')
print('PASS' if not r['errors'] else 'FAIL')
