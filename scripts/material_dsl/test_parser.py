"""Material DSL Parser Test."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from material_dsl.lexer import tokenize
from material_dsl.parser import parse
from material_dsl.validator import validate
from material_dsl.command_generator import generate

DSL = """
MATERIAL: M_RustyMetal
@domain=Surface
@blend_mode=Opaque
@shading_model=DefaultLit

CONSTANT3: RustColor
  @default=0.45,0.25,0.12

SCALAR_PARAM: RoughnessValue
  @default=0.7

SCALAR_PARAM: MetallicValue
  @default=0.9

MULTIPLY: TintedColor
  @A=RustColor
  @B=RustColor

OUTPUT:
  @BaseColor=TintedColor
  @Roughness=RoughnessValue
  @Metallic=MetallicValue
"""

print("=== Material DSL Parser Test ===\n")
tokens = tokenize(DSL)
print(f"[Lexer] {len(tokens)} tokens")
tree = parse(tokens)
print(f"[Parser] Name={tree['name']}, {len(tree['nodes'])} nodes, {len(tree['outputs'])} outputs")
for n in tree['nodes']: print(f"  {n['type']:20s} {n['name']}")
result = validate(tree)
print(f"[Validator] {len(result['errors'])} errors, {len(result['warnings'])} warnings")
for e in result['errors']: print(f"  ERROR: {e}")
commands = generate(tree)
print(f"\n[Commands] {len(commands)} total:")
for cmd in commands:
    brief = ", ".join(f"{k}={v}" for k,v in list(cmd["params"].items())[:3])
    print(f"  {cmd['command']:30s} {brief[:60]}")
ok = len(result['errors']) == 0
print(f"\n{'PASS' if ok else 'FAIL'} — {len(commands)} commands")
sys.exit(0 if ok else 1)
