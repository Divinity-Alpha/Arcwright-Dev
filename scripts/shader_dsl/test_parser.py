import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shader_dsl.lexer import tokenize
from shader_dsl.parser import parse
from shader_dsl.validator import validate
from shader_dsl.command_generator import generate
DSL = """
SHADER: SF_HoloDissolve
@type=MaterialFunction
INPUT: DissolveAmount
  @type=Float
  @default=0.5
INPUT: EdgeColor
  @type=Color
HLSL: DissolveLogic
  @code=step_noise
OUTPUT: Color
  @source=DissolveLogic.rgb
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
ek = 'elements'
n = len(tree.get(ek, []))
print(f'shader_dsl: {tree["name"]}, {n} elements, {len(cmds)} commands, {len(r["errors"])} errors')
print('PASS' if not r['errors'] else 'FAIL')
