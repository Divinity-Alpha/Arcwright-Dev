import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dmx_dsl.lexer import tokenize
from dmx_dsl.parser import parse
from dmx_dsl.validator import validate
from dmx_dsl.command_generator import generate
DSL = """
DMX: DMX_Stage
UNIVERSE: Universe1
  @protocol=sACN
  @port=5568
FIXTURE: SpotLight_1
  @type=GenericDimmer
  @start_channel=1
CUE: Scene1
  @fade_time=2.0
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
ek = 'elements'
n = len(tree.get(ek, []))
print(f'dmx_dsl: {tree["name"]}, {n} elements, {len(cmds)} commands, {len(r["errors"])} errors')
print('PASS' if not r['errors'] else 'FAIL')
