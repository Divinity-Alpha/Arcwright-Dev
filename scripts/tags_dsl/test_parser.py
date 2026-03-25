"""Tags test."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tags_dsl.lexer import tokenize
from tags_dsl.parser import parse
from tags_dsl.validator import validate
from tags_dsl.command_generator import generate
DSL = """
TAGS: GameplayTags
HIERARCHY: Ability
  Active
    Fire
    Ice
    Heal
    Movement
  Passive
    Buff
HIERARCHY: Status
  Positive
    Regenerating
    Invincible
  Negative
    Burning
    Stunned
    Poisoned
HIERARCHY: Damage
  Physical
    Blunt
    Slash
  Magical
    Fire
    Ice
"""
tree = parse(tokenize(DSL))
r = validate(tree)
cmds = generate(tree)
total_tags = sum(len(h["tags"]) for h in tree["hierarchies"])
print(f"Tags: {tree['name']}, {len(tree['hierarchies'])} hierarchies, {total_tags} tags, {len(cmds)} commands, {len(r['errors'])} errors")
# Show some tags
for h in tree["hierarchies"]:
    print(f"  {h['root']}: {', '.join(t.split('.')[-1] for t in h['tags'][:5])}{'...' if len(h['tags'])>5 else ''}")
print("PASS" if not r['errors'] else "FAIL")
