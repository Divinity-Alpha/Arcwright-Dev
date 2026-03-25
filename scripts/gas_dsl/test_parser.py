"""GAS DSL Parser Test."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gas_dsl.lexer import tokenize
from gas_dsl.parser import parse
from gas_dsl.validator import validate
from gas_dsl.command_generator import generate

DSL = """
ABILITY_SYSTEM: GAS_PlayerCombat
@owner=BP_PlayerCharacter

ATTRIBUTE_SET: AS_PlayerStats
  ATTRIBUTE: Health
    @base=100
    @min=0
    @max=100
  ATTRIBUTE: MaxHealth
    @base=100
  ATTRIBUTE: Mana
    @base=50
    @min=0
    @max=50
  ATTRIBUTE: MaxMana
    @base=50
  ATTRIBUTE: AttackPower
    @base=15
  ATTRIBUTE: Defense
    @base=5
  ATTRIBUTE: MoveSpeed
    @base=600

ABILITY: GA_Fireball
  @display_name="Fireball"
  @description="Launches a fireball that deals fire damage"
  @cooldown=2.0
  @cost_attribute=Mana
  @cost_amount=15
  @tags=Ability.Active.Fire,Ability.Ranged
  EFFECT: FireballDamage
    @type=Instant
    @target=Enemy
    @modifier=Damage
      @attribute=Health
      @operation=Add
      @magnitude=-50
      @scale_attribute=AttackPower
      @scale_factor=1.5
  EFFECT: BurnDoT
    @type=Duration
    @duration=5.0
    @period=1.0
    @target=Enemy
    @tags_granted=Status.Burning
    @modifier=Damage
      @attribute=Health
      @operation=Add
      @magnitude=-10

ABILITY: GA_HealingSurge
  @display_name="Healing Surge"
  @cooldown=8.0
  @cost_attribute=Mana
  @cost_amount=25
  @tags=Ability.Active.Heal
  EFFECT: HealOverTime
    @type=Duration
    @duration=4.0
    @period=0.5
    @target=Self
    @tags_granted=Status.Regenerating
    @modifier=Heal
      @attribute=Health
      @operation=Add
      @magnitude=8

ABILITY: GA_DodgeRoll
  @display_name="Dodge Roll"
  @cooldown=1.5
  @tags=Ability.Active.Movement
  EFFECT: DodgeInvincibility
    @type=Duration
    @duration=0.4
    @target=Self
    @tags_granted=Status.Invincible
  EFFECT: DodgeSpeedBoost
    @type=Duration
    @duration=0.4
    @target=Self
    @modifier=SpeedBuff
      @attribute=MoveSpeed
      @operation=Multiply
      @magnitude=2.0
"""

print("=== GAS DSL Parser Test ===\\n")
tokens = tokenize(DSL)
print(f"[Lexer] {len(tokens)} tokens")

tree = parse(tokens)
print(f"[Parser] System={tree['name']}")
for aset in tree['attribute_sets']:
    print(f"  Attribute Set: {aset['name']} ({len(aset['attributes'])} attributes)")
    for attr in aset['attributes']:
        base = attr['properties'].get('base', '?')
        print(f"    {attr['name']:15s} base={base}")
print(f"  Abilities: {len(tree['abilities'])}")
for ab in tree['abilities']:
    effects = len(ab.get('effects', []))
    cd = ab['properties'].get('cooldown', '0')
    cost = ab['properties'].get('cost_amount', '0')
    print(f"    {ab['name']:20s} cd={cd}s cost={cost} effects={effects}")

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
print(f"\\n{'PASS' if ok else 'FAIL'} — {len(tree['abilities'])} abilities, {len(commands)} commands")
sys.exit(0 if ok else 1)
