"""
Widget DSL v2 Parser Test — end-to-end pipeline test (no UE needed).

Tests: lexer -> parser -> theme_resolver -> binding_extractor ->
       animation_compiler -> validator -> command_generator
"""

import sys
import os
import json

# Ensure imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from widget_dsl.lexer import tokenize
from widget_dsl.parser import parse
from widget_dsl.theme_resolver import resolve
from widget_dsl.binding_extractor import extract
from widget_dsl.animation_compiler import compile_animations
from widget_dsl.validator import validate
from widget_dsl.command_generator import generate


# ─── Test 1: Simple Health Bar ──────────────────────────────────

SIMPLE_DSL = """
WIDGET: WBP_HealthBar
THEME: Normal

CANVAS Root
  HBOX HealthContainer
    @anchor: BottomLeft
    @offset_x: 40
    @offset_y: -60
    TEXT HealthLabel
      @text: HP
      @font_size: 18
      @color: $text_secondary
      @bold: true
    PROGRESS_BAR HealthBar
      @percent: BIND:Health/MaxHealth
      @fill_color: $health
      @size_x: 300
      @size_y: 24
      @anim:OnDamage = Shake|intensity=8|duration=0.3
    TEXT HealthText
      @text: BIND:"{CurrentHP}/{MaxHP}"
      @font_size: 16
      @color: $text
"""


# ─── Test 2: Full HUD with COMPONENTS ──────────────────────────

FULL_HUD_DSL = """
WIDGET: WBP_GameHUD
THEME: Normal

PALETTE:
  $health = #00FF88
  $mana = #4488FF
  $xp_bar = #AA66FF

CANVAS Root

  -- Top-left: Health + Mana
  VBOX StatusBars
    @anchor: TopLeft
    @offset_x: 30
    @offset_y: 30
    HBOX HealthRow
      @spacing: 8
      TEXT HealthIcon
        @text: +
        @font_size: 20
        @color: $health
        @bold: true
      PROGRESS_BAR HealthBar
        @percent: BIND:Health
        @fill_color: $health
        @size_x: 250
        @size_y: 20
        @anim:OnDamage = Flash|color=#FF0000|duration=0.15
    HBOX ManaRow
      @spacing: 8
      TEXT ManaIcon
        @text: *
        @font_size: 20
        @color: $mana
        @bold: true
      PROGRESS_BAR ManaBar
        @percent: BIND:Mana
        @fill_color: $mana
        @size_x: 200
        @size_y: 16

  -- Top-right: Score
  TEXT ScoreText
    @anchor: TopRight
    @offset_x: -30
    @offset_y: 30
    @text: BIND:"{Score}"
    @font_size: 32
    @color: $warning
    @bold: true

  -- Bottom-center: XP Bar
  VBOX XPContainer
    @anchor: BottomCenter
    @offset_y: -40
    PROGRESS_BAR XPBar
      @percent: BIND:XP
      @fill_color: $xp_bar
      @size_x: 600
      @size_y: 10
    TEXT XPLabel
      @text: BIND:"Level {Level} - {XPCurrent}/{XPMax} XP"
      @font_size: 12
      @color: $text_muted
      @justification: Center

  -- Center: Crosshair
  TEXT Crosshair
    @anchor: Center
    @text: +
    @font_size: 24
    @color: $text
    @opacity: 0.6
"""


def run_pipeline(name: str, dsl: str):
    """Run the full pipeline on a DSL string and print results."""
    print(f"\n{'='*60}")
    print(f"  TEST: {name}")
    print(f"{'='*60}")

    # Step 1: Lexer
    tokens = tokenize(dsl)
    widget_tokens = [t for t in tokens if t.type not in ("BLANK", "COMMENT")]
    print(f"\n[Lexer] {len(tokens)} tokens ({len(widget_tokens)} non-blank)")
    for t in widget_tokens[:8]:
        print(f"  {t.type:20s} indent={t.indent} name={t.name or t.key:20s} "
              f"type={t.widget_type or ''}")
    if len(widget_tokens) > 8:
        print(f"  ... and {len(widget_tokens)-8} more")

    # Step 2: Parser
    tree = parse(tokens)
    print(f"\n[Parser] widget_name={tree['widget_name']}, theme={tree['theme']}, "
          f"palette={len(tree['palette'])} entries")
    root = tree["root"]
    child_count = _count_nodes(root) - 1
    print(f"  Root: {root['type']} '{root['name']}' with {child_count} descendant(s)")

    # Step 3: Theme resolver
    tree = resolve(tree)
    lookup_count = len(tree.get("_lookup", {}))
    print(f"\n[Theme Resolver] {lookup_count} lookup entries loaded")
    # Show a few resolved values
    _show_resolved(root, depth=0, max_show=3)

    # Step 4: Binding extractor
    variables = extract(tree)
    print(f"\n[Binding Extractor] {len(variables)} variable(s) found")
    for v in variables:
        uses = len(v["used_by"])
        print(f"  {v['name']:20s} type={v['type']:8s} used_by={uses} widget(s)")

    # Step 5: Animation compiler
    animations = compile_animations(tree)
    print(f"\n[Animation Compiler] {len(animations)} animation(s)")
    for a in animations:
        errs = a.get("errors", [])
        err_str = f" ERRORS: {errs}" if errs else ""
        print(f"  {a['widget']:20s} @{a['trigger']:15s} -> {a['type']}{err_str}")

    # Step 6: Validator
    result = validate(tree)
    errors = result["errors"]
    warnings = result["warnings"]
    print(f"\n[Validator] {len(errors)} error(s), {len(warnings)} warning(s)")
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings:
        print(f"  WARN:  {w}")

    # Step 7: Command generator
    commands = generate(tree, variables)
    print(f"\n[Command Generator] {len(commands)} command(s)")
    for cmd in commands[:10]:
        p = cmd["params"]
        brief = ", ".join(f"{k}={v}" for k, v in list(p.items())[:3])
        print(f"  {cmd['command']:30s} {brief}")
    if len(commands) > 10:
        print(f"  ... and {len(commands)-10} more")

    # Summary
    ok = len(errors) == 0
    status = "PASS" if ok else "FAIL"
    print(f"\n[Result] {status} — {len(commands)} commands, "
          f"{len(variables)} bindings, {len(animations)} animations, "
          f"{len(errors)} errors, {len(warnings)} warnings")
    return ok


def _count_nodes(node: dict) -> int:
    count = 1
    for c in node.get("children", []):
        count += _count_nodes(c)
    return count


def _show_resolved(node: dict, depth: int, max_show: int, shown: list = None):
    if shown is None:
        shown = [0]
    if shown[0] >= max_show:
        return
    for k, v in node.get("properties", {}).items():
        if shown[0] >= max_show:
            return
        if isinstance(v, str) and (v.startswith("#") or v.startswith("rgba")):
            print(f"  {'  '*depth}{node['name']}.{k} = {v}")
            shown[0] += 1
    for c in node.get("children", []):
        _show_resolved(c, depth+1, max_show, shown)


def test_component_expansion():
    """Test expanding 5 components via component_expander."""
    from widget_dsl.component_expander import expand_component, list_components, get_component_variables

    print(f"\n{'='*60}")
    print(f"  TEST: Component Expansion (5 components)")
    print(f"{'='*60}")

    components = ["health_bar", "ammo_counter", "score_panel", "crosshair", "boss_health_bar"]
    all_nodes = 0
    all_vars = 0
    all_anims = 0

    root = {"type": "CANVAS", "name": "Root", "properties": {}, "children": [], "animations": [], "bindings": []}

    for comp_id in components:
        node = expand_component(comp_id)
        if node is None:
            print(f"  FAIL: Component '{comp_id}' not found")
            return False

        nodes = _count_nodes(node)
        vars_list = get_component_variables(comp_id)
        anims = sum(1 for _ in _walk_anims(node))
        all_nodes += nodes
        all_vars += len(vars_list)
        all_anims += anims
        root["children"].append(node)
        print(f"  {comp_id:25s} {nodes:2d} nodes, {len(vars_list):2d} vars, {anims} anims")

    # Build a tree and generate commands
    tree = {"widget_name": "WBP_ComponentTest", "theme": "Normal", "palette": {}, "root": root}
    tree = resolve(tree)
    commands = generate(tree)

    print(f"\n  Total: {all_nodes} nodes, {all_vars} vars, {all_anims} anims")
    print(f"  Commands generated: {len(commands)}")

    # Also check component listing
    index = list_components()
    hud_count = len(index.get("hud_components", []))
    menu_count = len(index.get("menu_components", []))
    print(f"  Component index: {hud_count} HUD + {menu_count} menu = {hud_count+menu_count} total")

    ok = len(commands) > 0 and all_nodes > 5
    print(f"\n[Result] {'PASS' if ok else 'FAIL'} — {len(commands)} commands from 5 components")
    return ok


def _walk_anims(node):
    """Yield all animations in a tree."""
    for a in node.get("animations", []):
        yield a
    for c in node.get("children", []):
        yield from _walk_anims(c)


def test_anchor_properties():
    """Test that anchor-related DSL properties map to correct Slot.Anchors.* commands."""
    print(f"\n{'='*60}")
    print(f"  TEST: Anchor Property Mapping")
    print(f"{'='*60}")

    # Build a tree manually with anchor properties
    root = {
        "type": "CANVAS", "name": "Root", "properties": {},
        "children": [
            {
                "type": "BORDER", "name": "Border_Panel",
                "properties": {
                    "anchor_min_x": "0.65",
                    "anchor_min_y": "0.0",
                    "anchor_max_x": "1.0",
                    "anchor_max_y": "1.0",
                    "offset_left": "0",
                    "offset_top": "0",
                    "offset_right": "0",
                    "offset_bottom": "0",
                    "background": "#112233",
                },
                "children": [],
                "animations": [],
                "bindings": [],
            },
            {
                "type": "BORDER", "name": "Border_Overlay",
                "properties": {
                    "anchor_min_x": "0.0",
                    "anchor_min_y": "0.0",
                    "anchor_max_x": "1.0",
                    "anchor_max_y": "1.0",
                    "background": "#000000",
                },
                "children": [],
                "animations": [],
                "bindings": [],
            },
        ],
        "animations": [],
        "bindings": [],
    }
    tree = {"widget_name": "WBP_AnchorTest", "theme": "Normal", "palette": {}, "root": root}
    tree = resolve(tree)
    commands = generate(tree)

    # Check anchor commands were generated with correct property names
    anchor_cmds = [c for c in commands
                   if c["command"] == "set_widget_property"
                   and "Anchors" in c["params"].get("property", "")]
    offset_cmds = [c for c in commands
                   if c["command"] == "set_widget_property"
                   and "Offsets" in c["params"].get("property", "")]
    brush_cmds = [c for c in commands
                  if c["command"] == "set_widget_property"
                  and c["params"].get("property") == "BrushColor"]

    print(f"\n  Anchor commands: {len(anchor_cmds)}")
    for cmd in anchor_cmds:
        p = cmd["params"]
        print(f"    {p['widget_name']}.{p['property']} = {p['value']}")

    print(f"  Offset commands: {len(offset_cmds)}")
    for cmd in offset_cmds:
        p = cmd["params"]
        print(f"    {p['widget_name']}.{p['property']} = {p['value']}")

    print(f"  BrushColor commands: {len(brush_cmds)}")

    # Verify: 2 widgets × 4 anchor props = 8 anchor commands
    ok = len(anchor_cmds) == 8 and len(offset_cmds) == 4 and len(brush_cmds) == 2
    print(f"\n[Result] {'PASS' if ok else 'FAIL'} — "
          f"{len(anchor_cmds)} anchor + {len(offset_cmds)} offset + {len(brush_cmds)} brush commands")
    return ok


if __name__ == "__main__":
    pass1 = run_pipeline("Simple Health Bar", SIMPLE_DSL)
    pass2 = run_pipeline("Full Game HUD", FULL_HUD_DSL)
    pass3 = test_component_expansion()
    pass4 = test_anchor_properties()

    total = sum([pass1, pass2, pass3, pass4])
    print(f"\n{'='*60}")
    all_pass = total == 4
    print(f"  ALL TESTS: {'PASS' if all_pass else 'FAIL'} ({total}/4)")
    print(f"{'='*60}")
    sys.exit(0 if all_pass else 1)
