"""Test for sound_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sound_dsl.lexer import tokenize
from sound_dsl.parser import parse
from sound_dsl.validator import validate
from sound_dsl.command_generator import generate
DSL = """SOUND_DESIGN: SD_Dungeon
SOUND_CLASS: SFX_Ambient
  @volume=0.7
ATTENUATION: Att_Room
  @inner_radius=200
  @falloff_distance=1500
REVERB_ZONE: Hall
  @location=0,0,0
  @reverb_effect=LargeHall
AMBIENT: Wind
  @sound=S_Wind
  @class=SFX_Ambient"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("elements", []))
print(f"sound_dsl: {tree['name']}, {n} elements, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
