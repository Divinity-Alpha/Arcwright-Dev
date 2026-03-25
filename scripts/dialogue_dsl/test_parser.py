"""Dialogue DSL Parser Test."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dialogue_dsl.lexer import tokenize
from dialogue_dsl.parser import parse
from dialogue_dsl.validator import validate
from dialogue_dsl.command_generator import generate

DSL = """
DIALOGUE: DLG_Blacksmith
@speaker_default=NPC_Blacksmith
@portrait=T_Portrait_Blacksmith

NODE: Greeting
  @speaker=NPC_Blacksmith
  @text="Welcome, traveler. Looking to buy some gear?"
  @condition=NOT HasMetBlacksmith
  @set_flag=HasMetBlacksmith
  CHOICE: "Show me what you have."
    @next=ShowInventory
  CHOICE: "I need a sword repaired."
    @next=RepairQuest
    @condition=HasBrokenSword
  CHOICE: "Just passing through."
    @next=Farewell

NODE: ReturnGreeting
  @speaker=NPC_Blacksmith
  @text="Back again? What can I do for you?"
  @condition=HasMetBlacksmith
  CHOICE: "Show me what you have."
    @next=ShowInventory
  CHOICE: "About that sword..."
    @next=RepairProgress
  CHOICE: "Nothing, thanks."
    @next=Farewell

NODE: ShowInventory
  @speaker=NPC_Blacksmith
  @text="Take a look. Best steel in the kingdom."
  @action=OpenShopUI
  @next=END

NODE: RepairQuest
  @speaker=NPC_Blacksmith
  @text="That's a fine blade, but badly damaged. Bring me 3 iron ingots and I'll fix it up."
  @action=StartQuest:RepairSword
  @set_flag=RepairQuestActive
  CHOICE: "I'll find the ingots."
    @next=Farewell
  CHOICE: "How much will it cost?"
    @next=RepairCost

NODE: RepairCost
  @speaker=NPC_Blacksmith
  @text="50 gold, plus the ingots. Fair price for this quality of work."
  CHOICE: "Deal."
    @next=Farewell
  CHOICE: "That's too expensive."
    @next=Haggle

NODE: Haggle
  @speaker=NPC_Blacksmith
  @text="Tell you what - bring me 5 ingots instead of 3, and I'll waive the gold."
  CHOICE: "Fine, 5 ingots it is."
    @next=Farewell
  CHOICE: "Never mind."
    @next=Farewell

NODE: RepairProgress
  @speaker=NPC_Blacksmith
  @text="Still working on that sword. Come back later."
  @next=Farewell

NODE: Farewell
  @speaker=NPC_Blacksmith
  @text="Safe travels."
  @next=END
"""

print("=== Dialogue DSL Parser Test ===\\n")
tokens = tokenize(DSL)
print(f"[Lexer] {len(tokens)} tokens")
tree = parse(tokens)
print(f"[Parser] Name={tree['name']}, {len(tree['nodes'])} nodes")
for n in tree['nodes']:
    choices = len(n.get('choices', []))
    print(f"  {n['id']:20s} choices={choices} next={n.get('next','')[:15]:15s} speaker={n.get('speaker','')}")

result = validate(tree)
print(f"[Validator] {len(result['errors'])} errors, {len(result['warnings'])} warnings")
for e in result['errors']: print(f"  ERROR: {e}")
for w in result['warnings']: print(f"  WARN: {w}")

commands = generate(tree)
print(f"\\n[Commands] {len(commands)} total:")
for cmd in commands[:5]:
    brief = ", ".join(f"{k}={str(v)[:25]}" for k, v in list(cmd["params"].items())[:3])
    print(f"  {cmd['command']:30s} {brief}")
if len(commands) > 5: print(f"  ... and {len(commands)-5} more")

ok = len(result['errors']) == 0
print(f"\\n{'PASS' if ok else 'FAIL'} - {len(tree['nodes'])} nodes, {len(commands)} commands, {len(result['errors'])} errors")
sys.exit(0 if ok else 1)
