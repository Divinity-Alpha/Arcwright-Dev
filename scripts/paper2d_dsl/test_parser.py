import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from paper2d_dsl.lexer import tokenize
from paper2d_dsl.parser import parse
from paper2d_dsl.validator import validate
from paper2d_dsl.command_generator import generate
DSL = """
PAPER2D: P2D_Player
SPRITE: SPR_Idle
  @texture=T_Sheet
  @source_width=64
FLIPBOOK: FB_Run
  @fps=12
  @loop=true
TILEMAP: TM_Level1
  @tile_width=32
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
ek = 'elements'
n = len(tree.get(ek, []))
print(f'paper2d_dsl: {tree["name"]}, {n} elements, {len(cmds)} commands, {len(r["errors"])} errors')
print('PASS' if not r['errors'] else 'FAIL')
