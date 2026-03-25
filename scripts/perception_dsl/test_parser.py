"""AI Perception test."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from perception_dsl.lexer import tokenize
from perception_dsl.parser import parse
from perception_dsl.validator import validate
from perception_dsl.command_generator import generate
DSL = """
PERCEPTION: APC_EnemySenses
@owner=BP_PatrolEnemy
SENSE: Sight
  @range=1500
  @fov=90
  @max_age=5.0
  @detect_enemies=true
SENSE: Hearing
  @range=3000
  @max_age=3.0
SENSE: Damage
  @max_age=10.0
TEAM:
  @team_id=1
  @attitude_to_0=Hostile
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
print(f"Perception: {tree['name']}, {len(tree['senses'])} senses, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r['errors'] else "FAIL")
