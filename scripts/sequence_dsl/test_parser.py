"""Sequence DSL Parser Test."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sequence_dsl.lexer import tokenize
from sequence_dsl.parser import parse
from sequence_dsl.validator import validate
from sequence_dsl.command_generator import generate

DSL = """
SEQUENCE: LS_IntroCutscene
@duration=15.0
@framerate=30

CAMERA: MainCamera
  @fov=70
  KEYFRAME: 0.0
    @location=500,0,200
    @rotation=0,-15,180
    @fov=70
  KEYFRAME: 3.0
    @location=200,0,150
    @rotation=0,-10,170
    @fov=60
  KEYFRAME: 6.0
    @location=50,30,120
    @rotation=0,-5,160
    @fov=55

ACTOR: BP_King
  @binding=KingActor
  TRACK: Transform
    KEYFRAME: 0.0
      @location=0,0,0
      @rotation=0,0,0
    KEYFRAME: 4.0
      @location=0,0,0
      @rotation=0,0,30

ACTOR: BP_Door
  @binding=ThroneRoomDoor
  TRACK: Transform
    KEYFRAME: 2.0
      @rotation=0,0,0
    KEYFRAME: 4.0
      @rotation=0,90,0

AUDIO: MusicTrack
  @sound=S_Epic_Intro
  @start_time=0.0
  @volume=0.8
  @fade_in=2.0

FADE:
  KEYFRAME: 0.0
    @opacity=1.0
  KEYFRAME: 1.0
    @opacity=0.0
  KEYFRAME: 14.0
    @opacity=0.0
  KEYFRAME: 15.0
    @opacity=1.0

EVENT: 5.0
  @action=PlaySound:SFX_DoorCreak

EVENT: 6.0
  @action=SpawnActor:BP_DramaticLighting
"""

print("=== Sequence DSL Parser Test ===\\n")
tokens = tokenize(DSL)
print(f"[Lexer] {len(tokens)} tokens")

tree = parse(tokens)
props = tree.get("properties", {})
print(f"[Parser] Name={tree['name']}, Duration={props.get('duration','')}s")
print(f"  Cameras: {len(tree['cameras'])}")
for c in tree['cameras']: print(f"    {c['name']} — {len(c['keyframes'])} keyframes")
print(f"  Actors: {len(tree['actors'])}")
for a in tree['actors']:
    tracks = len(a.get('tracks', []))
    kfs = sum(len(t['keyframes']) for t in a.get('tracks', []))
    print(f"    {a['name']} — {tracks} tracks, {kfs} keyframes")
print(f"  Audio: {len(tree['audio'])}")
print(f"  Fades: {len(tree['fades'])} ({sum(len(f['keyframes']) for f in tree['fades'])} keyframes)")
print(f"  Events: {len(tree['events'])}")

result = validate(tree)
print(f"[Validator] {len(result['errors'])} errors, {len(result['warnings'])} warnings")
for e in result['errors']: print(f"  ERROR: {e}")

commands = generate(tree)
print(f"\\n[Commands] {len(commands)} total:")
for cmd in commands[:8]:
    brief = ", ".join(f"{k}={str(v)[:20]}" for k, v in list(cmd["params"].items())[:3])
    print(f"  {cmd['command']:30s} {brief}")
if len(commands) > 8: print(f"  ... and {len(commands)-8} more")

ok = len(result['errors']) == 0
print(f"\\n{'PASS' if ok else 'FAIL'} — {len(commands)} commands")
sys.exit(0 if ok else 1)
