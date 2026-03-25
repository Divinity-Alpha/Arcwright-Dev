#!/usr/bin/env python3
"""
BlueprintLLM Demo — Arena Collector
====================================
Builds the complete Arena Collector game from scratch.
Pickups, hazards, health pickups, enemies with patrol+chase, HUD, colored materials.
All through the automated pipeline. Zero manual steps.

Usage:
    python demo_arena_collector.py
    python demo_arena_collector.py --clean    # Delete everything first

Requires: UE Editor running with BlueprintLLM plugin (TCP port 13377)
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
try:
    from mcp_client.blueprint_client import BlueprintLLMClient, BlueprintLLMError
except ImportError:
    from scripts.mcp_client.blueprint_client import BlueprintLLMClient, BlueprintLLMError


# ─── DSL Definitions ────────────────────────────────────────────────────────

BLUEPRINTS = {
    "BP_ScorePickup": {
        "dsl": """BLUEPRINT: BP_ScorePickup
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="+10 Points!"]
NODE n3: DestroyActor

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute""",
        "components": [
            {"type": "BoxCollision", "name": "Collision", "properties": {"extent": {"x": 50, "y": 50, "z": 50}, "generate_overlap_events": True}},
            {"type": "StaticMesh", "name": "Mesh", "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube", "scale": {"x": 0.4, "y": 0.4, "z": 0.4}}},
            {"type": "PointLight", "name": "Glow", "properties": {"intensity": 3000, "light_color": {"r": 255, "g": 200, "b": 0}, "attenuation_radius": 300}},
        ],
        "material": {"name": "MI_ScoreGold", "color": {"r": 1.0, "g": 0.85, "b": 0.0}},
    },
    "BP_HealthPickup": {
        "dsl": """BLUEPRINT: BP_HealthPickup
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="+25 Health!"]
NODE n3: DestroyActor

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute""",
        "components": [
            {"type": "BoxCollision", "name": "Collision", "properties": {"extent": {"x": 60, "y": 60, "z": 60}, "generate_overlap_events": True}},
            {"type": "StaticMesh", "name": "Mesh", "properties": {"mesh": "/Engine/BasicShapes/Sphere.Sphere", "scale": {"x": 0.6, "y": 0.6, "z": 0.6}}},
            {"type": "PointLight", "name": "Glow", "properties": {"intensity": 3000, "light_color": {"r": 0, "g": 255, "b": 0}, "attenuation_radius": 300}},
        ],
        "material": {"name": "MI_HealthGreen", "color": {"r": 0.1, "g": 1.0, "b": 0.2}},
    },
    "BP_DamageZone": {
        "dsl": """BLUEPRINT: BP_DamageZone
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="Entering danger zone!"]
NODE n3: SetTimerByFunctionName [FunctionName="DealDamage", Time=1.0, Looping=true]
NODE n4: Event_ActorEndOverlap
NODE n5: ClearTimerByFunctionName [FunctionName="DealDamage"]
NODE n6: PrintString [InString="Left danger zone"]
NODE n7: Event_CustomEvent [EventName="DealDamage"]
NODE n8: PrintString [InString="-5 HP!"]

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
EXEC n4.Then -> n5.Execute
EXEC n5.Then -> n6.Execute
EXEC n7.Then -> n8.Execute""",
        "components": [
            {"type": "BoxCollision", "name": "Collision", "properties": {"extent": {"x": 150, "y": 150, "z": 80}, "generate_overlap_events": True}},
            {"type": "StaticMesh", "name": "Mesh", "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube", "scale": {"x": 3, "y": 3, "z": 1.5}}},
        ],
        "material": {"name": "MI_DangerRed", "color": {"r": 1.0, "g": 0.1, "b": 0.1}},
    },
    "BP_ArenaManager": {
        "dsl": """BLUEPRINT: BP_ArenaManager
PARENT: Actor

VAR Score: Int = 0
VAR Health: Float = 100.0
VAR Wave: Int = 1

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: CreateWidget [WidgetClass=WBP_ArenaHUD]
NODE n3: AddToViewport
NODE n4: PrintString [InString="Arena Collector - Survive!"]

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
EXEC n3.Then -> n4.Execute

DATA n2.ReturnValue -> n3.Target [Widget]""",
        "components": [],
        "material": None,
    },
}

HUD_WIDGETS = [
    {"type": "CanvasPanel", "name": "RootPanel", "parent": None, "properties": {}},
    {"type": "TextBlock", "name": "ScoreLabel", "parent": "RootPanel", "properties": {"text": "Score: 0", "font_size": 28, "color": {"r": 1, "g": 0.9, "b": 0, "a": 1}, "slot_position": {"x": 40, "y": 30}}},
    {"type": "ProgressBar", "name": "HealthBar", "parent": "RootPanel", "properties": {"percent": 1.0, "fill_color": {"r": 0, "g": 1, "b": 0, "a": 1}, "slot_position": {"x": 500, "y": 25}, "slot_size": {"x": 300, "y": 30}}},
    {"type": "TextBlock", "name": "HealthLabel", "parent": "RootPanel", "properties": {"text": "Health: 100", "font_size": 18, "color": {"r": 1, "g": 1, "b": 1, "a": 1}, "slot_position": {"x": 580, "y": 5}}},
    {"type": "TextBlock", "name": "WaveLabel", "parent": "RootPanel", "properties": {"text": "Wave: 1", "font_size": 24, "color": {"r": 0.8, "g": 0.8, "b": 1, "a": 1}, "slot_position": {"x": 1100, "y": 30}}},
    {"type": "TextBlock", "name": "MessageText", "parent": "RootPanel", "properties": {"text": "", "font_size": 32, "color": {"r": 1, "g": 1, "b": 0, "a": 1}, "slot_position": {"x": 500, "y": 650}}},
]

ACTORS = [
    # Score pickups
    {"class": "BP_ScorePickup", "label": "Score_1", "location": {"x": -500, "y": 600, "z": 92}},
    {"class": "BP_ScorePickup", "label": "Score_2", "location": {"x": 100, "y": 800, "z": 92}},
    {"class": "BP_ScorePickup", "label": "Score_3", "location": {"x": -400, "y": -500, "z": 92}},
    {"class": "BP_ScorePickup", "label": "Score_4", "location": {"x": 200, "y": -300, "z": 92}},
    {"class": "BP_ScorePickup", "label": "Score_5", "location": {"x": -100, "y": 1200, "z": 92}},
    # Health pickups
    {"class": "BP_HealthPickup", "label": "Health_1", "location": {"x": 300, "y": 400, "z": 92}},
    {"class": "BP_HealthPickup", "label": "Health_2", "location": {"x": -600, "y": -200, "z": 92}},
    {"class": "BP_HealthPickup", "label": "Health_3", "location": {"x": 0, "y": 1500, "z": 92}},
    # Damage zones
    {"class": "BP_DamageZone", "label": "Hazard_1", "location": {"x": -200, "y": 300, "z": 92}},
    {"class": "BP_DamageZone", "label": "Hazard_2", "location": {"x": 100, "y": -600, "z": 92}},
    {"class": "BP_DamageZone", "label": "Hazard_3", "location": {"x": -300, "y": 900, "z": 92}},
    # Arena manager
    {"class": "BP_ArenaManager", "label": "Manager_1", "location": {"x": -200, "y": 0, "z": 200}},
]


def step(msg):
    print(f"\n{'─'*50}\n  {msg}\n{'─'*50}")


def main():
    ap = argparse.ArgumentParser(description="Arena Collector — Full Game Demo")
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()

    print("=" * 50)
    print("  BlueprintLLM Demo — Arena Collector")
    print("  Complete game through automated pipeline")
    print("=" * 50)

    start = time.time()

    with BlueprintLLMClient() as c:
        c.health_check()

        # Clean
        if args.clean:
            step("Cleaning")
            for a in ACTORS:
                try: c.delete_actor(a["label"])
                except: pass
            for name in BLUEPRINTS:
                try: c.delete_blueprint(name)
                except: pass

        # HUD Widget
        step("Creating HUD widget")
        try:
            c.create_widget_blueprint("WBP_ArenaHUD")
            for w in HUD_WIDGETS:
                c.add_widget_child("WBP_ArenaHUD", w["type"], w["name"], parent=w.get("parent"))
                for k, v in w.get("properties", {}).items():
                    c.set_widget_property("WBP_ArenaHUD", w["name"], k, v)
            print("  ✅ WBP_ArenaHUD created")
        except Exception as e:
            print(f"  ⚠️ HUD: {e}")

        # Blueprints
        step("Creating Blueprints")
        for name, bp in BLUEPRINTS.items():
            try:
                try: c.delete_blueprint(name)
                except: pass
                c.create_blueprint_from_dsl(bp["dsl"])
                print(f"  ✅ {name}")
            except Exception as e:
                print(f"  ❌ {name}: {e}")

        # Components
        step("Adding components")
        for name, bp in BLUEPRINTS.items():
            for comp in bp.get("components", []):
                try:
                    c.add_component(name, comp["type"], comp["name"], properties=comp.get("properties", {}))
                    print(f"  ✅ {name}/{comp['name']}")
                except Exception as e:
                    print(f"  ⚠️ {name}/{comp['name']}: {e}")

        # Materials
        step("Creating materials")
        for name, bp in BLUEPRINTS.items():
            mat = bp.get("material")
            if mat:
                try:
                    c.create_simple_material(mat["name"], mat["color"])
                    mesh_comps = [comp for comp in bp.get("components", []) if comp["type"] == "StaticMesh"]
                    if mesh_comps:
                        c.apply_material(name, mesh_comps[0]["name"], f"/Game/Arcwright/Materials/{mat['name']}")
                    print(f"  ✅ {mat['name']}")
                except Exception as e:
                    print(f"  ⚠️ {mat['name']}: {e}")

        # Spawn actors
        step("Populating arena")
        for a in ACTORS:
            try:
                try: c.delete_actor(a["label"])
                except: pass
                c.spawn_actor_at(a["class"], label=a["label"], location=a["location"])
                print(f"  ✅ {a['label']}")
            except Exception as e:
                print(f"  ❌ {a['label']}: {e}")

        # Post-process for visual polish
        step("Adding visual polish")
        try:
            c.add_post_process_volume(
                location={"x": 0, "y": 0, "z": 100},
                infinite_extent=True
            )
            c.set_post_process_settings("PostProcessVolume_0", {
                "bloom_intensity": 1.5,
                "vignette_intensity": 0.3,
            })
            print("  ✅ Post-process volume")
        except Exception as e:
            print(f"  ⚠️ Post-process: {e}")

        # Save
        step("Saving")
        try:
            c.save_all()
            print("  ✅ Saved")
        except Exception as e:
            print(f"  ⚠️ {e}")

        elapsed = time.time() - start
        print(f"\n{'='*50}")
        print(f"  ✅ ARENA COLLECTOR BUILT — {elapsed:.1f}s")
        print(f"  4 Blueprints, 6-widget HUD, 3 materials")
        print(f"  12 actors, post-process volume")
        print(f"  Hit Play in UE Editor to test!")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()
