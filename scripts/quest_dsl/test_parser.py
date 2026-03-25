"""Quest DSL Parser Test."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from quest_dsl.lexer import tokenize
from quest_dsl.parser import parse
from quest_dsl.validator import validate
from quest_dsl.command_generator import generate

DSL = """
QUEST: Q_RepairSword
@title="The Broken Blade"
@description="The blacksmith can repair your ancestral sword, but needs materials."
@giver=NPC_Blacksmith
@level_requirement=5
@category=Side
@reward_xp=200
@reward_gold=0
@reward_items=BrokenSword_Repaired

STAGE: GatherIngots
  @description="Collect iron ingots for the blacksmith"
  @type=Collect
  OBJECTIVE: CollectIron
    @text="Collect Iron Ingots"
    @target=Item_IronIngot
    @count=3
    @current=0
  OBJECTIVE: OptionalCoal
    @text="Bring coal for faster repair"
    @target=Item_Coal
    @count=5
    @optional=true

STAGE: ReturnToBlacksmith
  @description="Bring the ingots to the blacksmith"
  @type=TalkTo
  OBJECTIVE: TalkBlacksmith
    @text="Return to the Blacksmith"
    @target=NPC_Blacksmith
    @count=1

STAGE: WaitForRepair
  @description="Wait for the sword to be repaired"
  @type=Wait
  OBJECTIVE: WaitTimer
    @text="Wait for the repair"
    @type=Timer
    @seconds=120

STAGE: CollectSword
  @description="Pick up your repaired sword"
  @type=TalkTo
  OBJECTIVE: GetSword
    @text="Collect the repaired sword from the Blacksmith"
    @target=NPC_Blacksmith
    @action=GiveItem:BrokenSword_Repaired

ON_COMPLETE:
  @set_flag=SwordRepaired
  @unlock_quest=Q_DragonSlayer

ON_ABANDON:
  @set_flag=AbandonedRepair
  @return_items=true
"""

print("=== Quest DSL Parser Test ===\\n")
tokens = tokenize(DSL)
print(f"[Lexer] {len(tokens)} tokens")

tree = parse(tokens)
props = tree.get("properties", {})
print(f"[Parser] ID={tree['id']}, Title={props.get('title','')}")
print(f"  Stages: {len(tree['stages'])}")
for s in tree['stages']:
    objs = len(s.get('objectives', []))
    print(f"    {s['id']:25s} type={s['properties'].get('type','?'):10s} objectives={objs}")
print(f"  On Complete: {len(tree['on_complete'])} actions")
print(f"  On Abandon: {len(tree['on_abandon'])} actions")

result = validate(tree)
print(f"[Validator] {len(result['errors'])} errors, {len(result['warnings'])} warnings")
for e in result['errors']: print(f"  ERROR: {e}")
for w in result['warnings']: print(f"  WARN: {w}")

commands = generate(tree)
print(f"\\n[Commands] {len(commands)} total:")
for cmd in commands[:6]:
    brief = ", ".join(f"{k}={str(v)[:20]}" for k, v in list(cmd["params"].items())[:3])
    print(f"  {cmd['command']:25s} {brief}")
if len(commands) > 6: print(f"  ... and {len(commands)-6} more")

ok = len(result['errors']) == 0
print(f"\\n{'PASS' if ok else 'FAIL'} — {len(tree['stages'])} stages, {len(commands)} commands")
sys.exit(0 if ok else 1)
