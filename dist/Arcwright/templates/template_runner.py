#!/usr/bin/env python3
"""
Arcwright Template Runner
Instantiates game templates through the automated pipeline.

Usage:
    python template_runner.py collectibles/collectible_basic
    python template_runner.py collectibles/collectible_basic --set blueprint_name=BP_Coin --set message="Got a coin!" --set color='{"r":0,"g":0.5,"b":1,"a":1}'
    python template_runner.py enemies/enemy_patrol_chase --spawn 0,500,92
    python template_runner.py --list
    python template_runner.py --list collectibles

Requires: UE Editor running with the Arcwright plugin (TCP port 13377)
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_project_root, "scripts"))
sys.path.insert(0, _project_root)

try:
    from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError
except ImportError:
    try:
        from scripts.mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError
    except ImportError:
        print("Error: Cannot import Arcwright client. Run from C:\\BlueprintLLM\\")
        sys.exit(1)


TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_template(template_path: str) -> dict:
    """Load a template JSON file."""
    full_path = os.path.join(TEMPLATE_DIR, template_path)
    if not full_path.endswith(".json"):
        full_path += ".json"
    
    if not os.path.exists(full_path):
        print(f"Template not found: {full_path}")
        sys.exit(1)
    
    with open(full_path) as f:
        return json.load(f)


def apply_customizations(text: str, customs: dict) -> str:
    """Replace {{key|default}} placeholders with custom values or defaults."""
    def replacer(match):
        key = match.group(1)
        default = match.group(2)
        value = customs.get(key, default)
        return str(value)
    
    return re.sub(r'\{\{(\w+)\|([^}]*)\}\}', replacer, text)


def instantiate_template(template: dict, customs: dict, client, spawn_loc=None):
    """Create all assets defined in a template."""
    tid = template["template_id"]
    print(f"\n{'='*50}")
    print(f"  Instantiating: {template['name']}")
    print(f"  Template: {tid}")
    print(f"{'='*50}")
    
    # Handle single-asset templates (collectibles, hazards, triggers)
    if "blueprint_dsl" in template:
        _create_single_asset(template, customs, client, spawn_loc)
    
    # Handle multi-asset templates (enemies)
    elif "assets" in template:
        _create_multi_asset(template, customs, client, spawn_loc)
    
    # Handle widget templates
    elif "widget_tree" in template:
        _create_widget(template, customs, client)
    
    print(f"\n  ✅ Template '{template['name']}' instantiated")


def _create_single_asset(template: dict, customs: dict, client, spawn_loc):
    """Create a single Blueprint with components and material."""
    
    # Create Blueprint from DSL
    dsl = apply_customizations(template["blueprint_dsl"], customs)
    bp_name = re.search(r'BLUEPRINT:\s*(\S+)', dsl).group(1)
    
    print(f"\n  Creating {bp_name}...")
    try:
        client.delete_blueprint(bp_name)
    except BlueprintLLMError:
        pass
    
    result = client.create_blueprint_from_dsl(dsl)
    print(f"    ✅ Blueprint created")
    
    # Add components
    for comp in template.get("components", []):
        props = comp.get("properties", {})
        # Resolve any string properties that should be dicts
        for k, v in props.items():
            if isinstance(v, str) and v.startswith("{"):
                try:
                    props[k] = json.loads(apply_customizations(v, customs))
                except json.JSONDecodeError:
                    pass
        
        try:
            client.add_component(bp_name, comp["type"], comp["name"], properties=props)
            print(f"    ✅ Component: {comp['name']} ({comp['type']})")
        except Exception as e:
            print(f"    ⚠️ Component {comp['name']}: {e}")
    
    # Create and apply material (uses create_simple_material for Substrate compat)
    mat = template.get("material")
    if mat:
        mat_name = apply_customizations(mat.get("name", f"MI_{bp_name}"), customs)
        # Extract color from vector_params BaseColor
        vp = mat.get("vector_params", {})
        base_color = vp.get("BaseColor", {"r": 0.5, "g": 0.5, "b": 0.5})
        if isinstance(base_color, str):
            try:
                base_color = json.loads(apply_customizations(base_color, customs))
            except json.JSONDecodeError:
                base_color = {"r": 0.5, "g": 0.5, "b": 0.5}
        color = {"r": base_color.get("r", 0.5), "g": base_color.get("g", 0.5), "b": base_color.get("b", 0.5)}
        emissive = mat.get("scalar_params", {}).get("Emissive", 0.0)
        try:
            client.create_simple_material(mat_name, color, emissive_strength=emissive)
            print(f"    ✅ Material: {mat_name}")
        except Exception as e:
            print(f"    ⚠️ Material: {e}")

        # Apply to first mesh component
        mesh_comps = [c for c in template.get("components", []) if c["type"] == "StaticMesh"]
        if mesh_comps:
            try:
                client.apply_material(bp_name, mesh_comps[0]["name"], f"/Game/Arcwright/Materials/{mat_name}")
                print(f"    ✅ Material applied to {mesh_comps[0]['name']}")
            except Exception as e:
                print(f"    ⚠️ Apply material: {e}")
    
    # Spawn if requested
    if spawn_loc:
        label = customs.get("label", f"{bp_name}_1")
        try:
            client.delete_actor(label)
        except BlueprintLLMError:
            pass
        
        try:
            client.spawn_actor_at(bp_name, label=label, location=spawn_loc)
            print(f"    ✅ Spawned at ({spawn_loc['x']}, {spawn_loc['y']}, {spawn_loc['z']})")
        except Exception as e:
            print(f"    ⚠️ Spawn: {e}")


def _create_multi_asset(template: dict, customs: dict, client, spawn_loc):
    """Create multi-asset templates (like enemies with pawn + controller + BT)."""
    assets = template["assets"]
    
    for asset_key, asset_def in assets.items():
        if "blueprint_dsl" in asset_def:
            dsl = apply_customizations(asset_def["blueprint_dsl"], customs)
            bp_name = re.search(r'BLUEPRINT:\s*(\S+)', dsl).group(1)
            
            print(f"\n  Creating {bp_name} ({asset_key})...")
            try:
                client.delete_blueprint(bp_name)
            except BlueprintLLMError:
                pass
            
            try:
                client.create_blueprint_from_dsl(dsl)
                print(f"    ✅ Blueprint created")
            except Exception as e:
                print(f"    ❌ Blueprint: {e}")
                continue
            
            # Components
            for comp in asset_def.get("components", []):
                try:
                    client.add_component(bp_name, comp["type"], comp["name"],
                                         properties=comp.get("properties", {}))
                    print(f"    ✅ Component: {comp['name']}")
                except Exception as e:
                    print(f"    ⚠️ Component: {e}")
            
            # Material (uses create_simple_material for Substrate compat)
            mat = asset_def.get("material")
            if mat:
                try:
                    vp = mat.get("vector_params", {})
                    base_color = vp.get("BaseColor", {"r": 0.5, "g": 0.5, "b": 0.5})
                    color = {"r": base_color.get("r", 0.5), "g": base_color.get("g", 0.5), "b": base_color.get("b", 0.5)}
                    client.create_simple_material(mat["name"], color)
                    mesh_comps = [c for c in asset_def.get("components", []) if c["type"] == "StaticMesh"]
                    if mesh_comps:
                        client.apply_material(bp_name, mesh_comps[0]["name"], f"/Game/Arcwright/Materials/{mat['name']}")
                    print(f"    ✅ Material: {mat['name']}")
                except Exception as e:
                    print(f"    ⚠️ Material: {e}")
        
        elif "bt_dsl" in asset_def:
            dsl = apply_customizations(asset_def["bt_dsl"], customs)
            bt_name = re.search(r'BEHAVIORTREE:\s*(\S+)', dsl).group(1)
            
            print(f"\n  Creating {bt_name} ({asset_key})...")
            try:
                client.create_behavior_tree_from_dsl(dsl)
                print(f"    ✅ Behavior Tree created")
            except Exception as e:
                print(f"    ⚠️ BT: {e}")
    
    if spawn_loc:
        # Find the pawn asset to spawn
        pawn_key = next((k for k in assets if "pawn" in k.lower()), None)
        if pawn_key and "blueprint_dsl" in assets[pawn_key]:
            dsl = apply_customizations(assets[pawn_key]["blueprint_dsl"], customs)
            bp_name = re.search(r'BLUEPRINT:\s*(\S+)', dsl).group(1)
            label = customs.get("label", f"{bp_name}_1")
            try:
                client.spawn_actor_at(f"/Game/Arcwright/Generated/{bp_name}",
                                      label=label, location=spawn_loc)
                print(f"    ✅ Spawned {bp_name} at ({spawn_loc['x']}, {spawn_loc['y']}, {spawn_loc['z']})")
            except Exception as e:
                print(f"    ⚠️ Spawn: {e}")


def _create_widget(template: dict, customs: dict, client):
    """Create a widget Blueprint from template."""
    wt = template["widget_tree"]
    widget_name = apply_customizations(wt.get("create", "WBP_Template"), customs)
    
    print(f"\n  Creating widget {widget_name}...")
    try:
        client.create_widget_blueprint(widget_name)
        print(f"    ✅ Widget Blueprint created")
    except Exception as e:
        print(f"    ⚠️ Widget create: {e}")
    
    for widget in wt.get("widgets", []):
        try:
            client.add_widget_child(widget_name, widget["type"], widget["name"],
                                    parent=widget.get("parent"))
            print(f"    ✅ Widget: {widget['name']} ({widget['type']})")
            
            for prop, val in widget.get("properties", {}).items():
                client.set_widget_property(widget_name, widget["name"], prop, val)
        except Exception as e:
            print(f"    ⚠️ Widget {widget['name']}: {e}")
    
    # Create HUD manager if defined
    if "hud_manager_dsl" in template:
        dsl = apply_customizations(template["hud_manager_dsl"], customs)
        bp_name = re.search(r'BLUEPRINT:\s*(\S+)', dsl).group(1)
        print(f"\n  Creating HUD manager {bp_name}...")
        try:
            client.delete_blueprint(bp_name)
        except BlueprintLLMError:
            pass
        try:
            client.create_blueprint_from_dsl(dsl)
            print(f"    ✅ HUD manager created")
        except Exception as e:
            print(f"    ⚠️ HUD manager: {e}")


def list_templates(category=None):
    """List available templates."""
    index_path = os.path.join(TEMPLATE_DIR, "template_index.json")
    if not os.path.exists(index_path):
        print("No template index found")
        return
    
    with open(index_path) as f:
        index = json.load(f)
    
    print(f"\nArcwright Template Library v{index['version']}")
    print(f"{'='*60}")
    
    for cat_name, cat_info in index["categories"].items():
        if category and cat_name != category:
            continue
        
        print(f"\n  {cat_name}: {cat_info['description']}")
        for tid in cat_info["templates"]:
            # Check both subdirectory and flat paths
            tpath = os.path.join(TEMPLATE_DIR, cat_name, f"{tid}.json")
            tpath_flat = os.path.join(TEMPLATE_DIR, f"{tid}.json")
            found = tpath if os.path.exists(tpath) else (tpath_flat if os.path.exists(tpath_flat) else None)
            if found:
                with open(found) as f:
                    t = json.load(f)
                print(f"    ✅ {tid}: {t['name']}")
            else:
                print(f"    ⬜ {tid}: (not yet created)")


def main():
    ap = argparse.ArgumentParser(description="Arcwright Template Runner")
    ap.add_argument("template", nargs="?", help="Template path (e.g. collectibles/collectible_basic)")
    ap.add_argument("--list", nargs="?", const="all", help="List templates (optionally filter by category)")
    ap.add_argument("--set", action="append", help="Set customization: --set key=value")
    ap.add_argument("--spawn", help="Spawn location: x,y,z")
    ap.add_argument("--setup-lighting", default=None, metavar="PRESET",
                    help="Setup scene lighting first (indoor_dark/indoor_bright/outdoor_day/outdoor_night)")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=13377)
    args = ap.parse_args()
    
    if args.list:
        list_templates(None if args.list == "all" else args.list)
        return
    
    if not args.template:
        ap.print_help()
        return
    
    # Parse customizations
    customs = {}
    for s in (args.set or []):
        key, _, val = s.partition("=")
        customs[key] = val
    
    # Parse spawn location
    spawn_loc = None
    if args.spawn:
        parts = args.spawn.split(",")
        if len(parts) == 3:
            spawn_loc = {"x": float(parts[0]), "y": float(parts[1]), "z": float(parts[2])}
    
    template = load_template(args.template)
    
    with ArcwrightClient(host=args.host, port=args.port) as client:
        client.health_check()

        # Lesson #42: Setup scene lighting before spawning anything
        if args.setup_lighting:
            try:
                r = client.setup_scene_lighting(args.setup_lighting)
                count = r.get('data', {}).get('actors_created', 0)
                print(f"  Scene lighting: {count} actors ({args.setup_lighting} preset)")
            except Exception as e:
                print(f"  WARN: setup_scene_lighting failed: {e}")

        instantiate_template(template, customs, client, spawn_loc)
        
        try:
            client.save_all()
            print(f"\n  💾 Project saved")
        except Exception as e:
            print(f"\n  ⚠️ Save: {e}")


if __name__ == "__main__":
    main()
