"""Test for vehicle_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vehicle_dsl.lexer import tokenize
from vehicle_dsl.parser import parse
from vehicle_dsl.validator import validate
from vehicle_dsl.command_generator import generate
DSL = """VEHICLE: VH_SportsCar
@chassis_mass=1500
WHEEL: FrontLeft
  @position=-80,-130,0
  @radius=35
  @friction=3.0
  @steer_angle=40
WHEEL: FrontRight
  @position=80,-130,0
  @radius=35
  @friction=3.0
  @steer_angle=40
ENGINE: V8
  @max_torque=750
  @max_rpm=7000
TRANSMISSION: Auto5Speed
  @type=Automatic
  @gear_count=5"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("components", []))
print(f"vehicle_dsl: {tree['name']}, {n} components, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
