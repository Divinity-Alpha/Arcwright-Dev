"""Test for statetree_dsl."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from statetree_dsl.lexer import tokenize
from statetree_dsl.parser import parse
from statetree_dsl.validator import validate
from statetree_dsl.command_generator import generate
DSL = """STATE_TREE: ST_EnemyAI
STATE: Combat
  @priority=High
  CONDITION: CanSeeEnemy
    @type=Perception
    @sense=Sight
  TASK: AttackTarget
    @ability=GA_MeleeAttack
STATE: Patrol
  @priority=Normal
  TASK: MoveTo
    @target=PatrolPoint
  TASK: Wait
    @duration=3.0"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
n = len(tree.get("states", []))
print(f"statetree_dsl: {tree['name']}, {n} states, {len(cmds)} commands, {len(r['errors'])} errors")
print("PASS" if not r["errors"] else "FAIL")
