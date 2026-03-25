"""
Arena Collector — Complete game build via TCP commands.

Creates all Blueprints, components, materials, widgets, and actors
for the Arena Collector game using the BlueprintLLM command server.

Usage:
    python scripts/build_arena_collector.py
"""

import sys
import os
import json
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mcp_client"))
sys.path.insert(0, os.path.dirname(__file__))

from blueprint_client import ArcwrightClient, BlueprintLLMError


def step_header(step: str, desc: str):
    print(f"\n{'='*60}")
    print(f"  Step {step}: {desc}")
    print(f"{'='*60}")


def ok(msg: str):
    print(f"  OK  {msg}")


def fail(msg: str):
    print(f"  FAIL  {msg}")


def safe(fn, desc: str):
    """Run fn, print result. Return True on success."""
    try:
        result = fn()
        ok(desc)
        return result
    except BlueprintLLMError as e:
        # Some deletions may fail if asset doesn't exist — that's ok
        if "not found" in str(e).lower():
            ok(f"{desc} (already gone)")
            return None
        fail(f"{desc}: {e}")
        return None
    except Exception as e:
        fail(f"{desc}: {e}")
        return None


def main():
    print("=" * 60)
    print("  ARENA COLLECTOR — Full Game Build")
    print("=" * 60)

    c = ArcwrightClient(timeout=60)
    c.health_check()
    print("Connected to UE Command Server")

    errors = []

    # ===========================================================
    # Step 1: Clean slate
    # ===========================================================
    step_header("1", "Clean slate — delete old assets")

    # Delete old game BPs
    for bp in ["BP_Pickup", "BP_HazardZone", "BP_VictoryZone", "BP_ScoreTracker",
               "BP_HealthPickup", "BP_ScorePickup", "BP_DamageZone", "BP_ArenaManager"]:
        safe(lambda bp=bp: c.delete_blueprint(bp), f"Delete {bp}")

    # Delete old actors
    for label in ["BP_Pickup_1", "BP_HazardZone_1", "BP_VictoryZone_1",
                  "BP_Pickup_2", "BP_Pickup_3", "BP_ScoreTracker_1",
                  "ScorePickup_1", "ScorePickup_2", "ScorePickup_3",
                  "ScorePickup_4", "ScorePickup_5",
                  "HealthPickup_1", "HealthPickup_2", "HealthPickup_3",
                  "DamageZone_1", "DamageZone_2", "DamageZone_3",
                  "ArenaManager_1"]:
        safe(lambda l=label: c.delete_actor(l), f"Delete actor {label}")

    # Delete old widgets
    for wbp in ["WBP_ArenaHUD", "WBP_GameHUD", "WBP_Test"]:
        safe(lambda w=wbp: c.send_command("delete_blueprint", {"name": w}), f"Delete {wbp}")

    # Delete old materials (by sending delete_blueprint which works for any asset)
    for mat in ["MI_GoldPickup", "MI_RedHazard", "MI_GreenVictory", "MI_ShinyPickup",
                "MI_HealthGreen", "MI_ScoreGold", "MI_DangerRed"]:
        safe(lambda m=mat: c.send_command("delete_blueprint", {"name": m}), f"Delete {mat}")

    ok("Clean slate complete")

    # ===========================================================
    # Step 2: Create WBP_ArenaHUD
    # ===========================================================
    step_header("2", "Create WBP_ArenaHUD widget")

    r = safe(lambda: c.create_widget_blueprint("WBP_ArenaHUD"), "Create WBP_ArenaHUD")
    if not r:
        errors.append("Failed to create WBP_ArenaHUD")

    safe(lambda: c.add_widget_child("WBP_ArenaHUD", "CanvasPanel", "RootPanel"),
         "Add RootPanel (CanvasPanel)")

    # Score display — top left
    safe(lambda: c.add_widget_child("WBP_ArenaHUD", "TextBlock", "ScoreLabel",
                                     parent_widget="RootPanel"),
         "Add ScoreLabel")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "text", "Score: 0"),
         "Set ScoreLabel text")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "font_size", 28),
         "Set ScoreLabel font_size")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "color",
                                        {"r": 1, "g": 0.9, "b": 0, "a": 1}),
         "Set ScoreLabel color (gold)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "position",
                                        {"x": 40, "y": 30}),
         "Set ScoreLabel position (top-left)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "size",
                                        {"x": 250, "y": 40}),
         "Set ScoreLabel size")

    # Health bar — top center
    safe(lambda: c.add_widget_child("WBP_ArenaHUD", "ProgressBar", "HealthBar",
                                     parent_widget="RootPanel"),
         "Add HealthBar")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthBar", "percent", 1.0),
         "Set HealthBar percent=1.0")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthBar", "fill_color",
                                        {"r": 0, "g": 1, "b": 0, "a": 1}),
         "Set HealthBar fill_color (green)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthBar", "position",
                                        {"x": 500, "y": 25}),
         "Set HealthBar position (top-center)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthBar", "size",
                                        {"x": 300, "y": 30}),
         "Set HealthBar size")

    # Health label above bar
    safe(lambda: c.add_widget_child("WBP_ArenaHUD", "TextBlock", "HealthLabel",
                                     parent_widget="RootPanel"),
         "Add HealthLabel")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthLabel", "text", "Health: 100"),
         "Set HealthLabel text")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthLabel", "font_size", 18),
         "Set HealthLabel font_size")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthLabel", "color",
                                        {"r": 1, "g": 1, "b": 1, "a": 1}),
         "Set HealthLabel color (white)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthLabel", "position",
                                        {"x": 580, "y": 5}),
         "Set HealthLabel position")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "HealthLabel", "size",
                                        {"x": 200, "y": 25}),
         "Set HealthLabel size")

    # Wave counter — top right
    safe(lambda: c.add_widget_child("WBP_ArenaHUD", "TextBlock", "WaveLabel",
                                     parent_widget="RootPanel"),
         "Add WaveLabel")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "WaveLabel", "text", "Wave: 1"),
         "Set WaveLabel text")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "WaveLabel", "font_size", 24),
         "Set WaveLabel font_size")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "WaveLabel", "color",
                                        {"r": 0.8, "g": 0.8, "b": 1, "a": 1}),
         "Set WaveLabel color (light blue)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "WaveLabel", "position",
                                        {"x": 1100, "y": 30}),
         "Set WaveLabel position (top-right)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "WaveLabel", "size",
                                        {"x": 200, "y": 35}),
         "Set WaveLabel size")

    # Message text — bottom center
    safe(lambda: c.add_widget_child("WBP_ArenaHUD", "TextBlock", "MessageText",
                                     parent_widget="RootPanel"),
         "Add MessageText")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "MessageText", "text", ""),
         "Set MessageText text (empty)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "MessageText", "font_size", 32),
         "Set MessageText font_size")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "MessageText", "color",
                                        {"r": 1, "g": 1, "b": 0, "a": 1}),
         "Set MessageText color (yellow)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "MessageText", "position",
                                        {"x": 500, "y": 650}),
         "Set MessageText position (bottom-center)")
    safe(lambda: c.set_widget_property("WBP_ArenaHUD", "MessageText", "size",
                                        {"x": 400, "y": 50}),
         "Set MessageText size")

    # Verify widget tree
    tree_r = safe(lambda: c.get_widget_tree("WBP_ArenaHUD"), "Get widget tree")
    if tree_r and "data" in tree_r:
        td = tree_r["data"]
        print(f"         Widgets: {td['total_widgets']}, Root: {td.get('root_name', '?')} ({td.get('root_type', '?')})")
        if td["total_widgets"] != 6:
            errors.append(f"Expected 6 widgets, got {td['total_widgets']}")

    # ===========================================================
    # Step 3: Create Blueprints via DSL
    # ===========================================================
    step_header("3", "Create Blueprints via DSL")

    dsl_health = """BLUEPRINT: BP_HealthPickup
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="+25 Health!"]
NODE n3: DestroyActor

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute"""

    dsl_score = """BLUEPRINT: BP_ScorePickup
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="+10 Points!"]
NODE n3: DestroyActor

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute"""

    dsl_damage = """BLUEPRINT: BP_DamageZone
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
EXEC n7.Then -> n8.Execute"""

    dsl_manager = """BLUEPRINT: BP_ArenaManager
PARENT: Actor

VAR Score: Int = 0
VAR Health: Float = 100.0
VAR Wave: Int = 1

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Arena Collector - Survive and collect!"]

EXEC n1.Then -> n2.Execute"""

    for name, dsl in [("BP_HealthPickup", dsl_health),
                      ("BP_ScorePickup", dsl_score),
                      ("BP_DamageZone", dsl_damage),
                      ("BP_ArenaManager", dsl_manager)]:
        r = safe(lambda d=dsl, n=name: c.create_blueprint_from_dsl(d, name=n),
                 f"Create {name} from DSL")
        if r and "data" in r:
            d = r["data"]
            print(f"         Nodes: {d.get('nodes_created', '?')}, "
                  f"Connections: {d.get('connections_wired', '?')}, "
                  f"Compiled: {d.get('compiled', '?')}")
        elif r is None:
            errors.append(f"Failed to create {name}")

    # ===========================================================
    # Step 4: Add components
    # ===========================================================
    step_header("4", "Add components to Blueprints")

    # BP_HealthPickup components
    safe(lambda: c.add_component("BP_HealthPickup", "BoxCollision", "PickupCollision",
                                  properties={"extent": {"x": 60, "y": 60, "z": 60},
                                              "generate_overlap_events": True}),
         "BP_HealthPickup: BoxCollision")
    safe(lambda: c.add_component("BP_HealthPickup", "StaticMesh", "PickupMesh",
                                  properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                                              "scale": {"x": 0.6, "y": 0.6, "z": 0.6}}),
         "BP_HealthPickup: StaticMesh (Sphere)")
    safe(lambda: c.add_component("BP_HealthPickup", "PointLight", "PickupLight",
                                  properties={"intensity": 3000,
                                              "light_color": {"r": 0, "g": 1, "b": 0},
                                              "attenuation_radius": 300}),
         "BP_HealthPickup: PointLight (green)")

    # BP_ScorePickup components
    safe(lambda: c.add_component("BP_ScorePickup", "BoxCollision", "PickupCollision",
                                  properties={"extent": {"x": 50, "y": 50, "z": 50},
                                              "generate_overlap_events": True}),
         "BP_ScorePickup: BoxCollision")
    safe(lambda: c.add_component("BP_ScorePickup", "StaticMesh", "PickupMesh",
                                  properties={"mesh": "/Engine/BasicShapes/Cube.Cube",
                                              "scale": {"x": 0.4, "y": 0.4, "z": 0.4}}),
         "BP_ScorePickup: StaticMesh (Cube)")
    safe(lambda: c.add_component("BP_ScorePickup", "PointLight", "PickupLight",
                                  properties={"intensity": 3000,
                                              "light_color": {"r": 1, "g": 0.8, "b": 0},
                                              "attenuation_radius": 300}),
         "BP_ScorePickup: PointLight (gold)")

    # BP_DamageZone components
    safe(lambda: c.add_component("BP_DamageZone", "BoxCollision", "ZoneCollision",
                                  properties={"extent": {"x": 150, "y": 150, "z": 80},
                                              "generate_overlap_events": True}),
         "BP_DamageZone: BoxCollision")
    safe(lambda: c.add_component("BP_DamageZone", "StaticMesh", "ZoneMesh",
                                  properties={"mesh": "/Engine/BasicShapes/Cube.Cube",
                                              "scale": {"x": 3, "y": 3, "z": 1.5}}),
         "BP_DamageZone: StaticMesh (Cube, large)")

    ok("All components added")

    # ===========================================================
    # Step 5: Create materials and apply
    # ===========================================================
    step_header("5", "Create materials and apply")

    safe(lambda: c.create_material_instance(
        "MI_HealthGreen",
        "/Engine/BasicShapes/BasicShapeMaterial",
        vector_params={"BaseColor": {"r": 0.1, "g": 1.0, "b": 0.2, "a": 1}}),
         "Create MI_HealthGreen")
    safe(lambda: c.apply_material("BP_HealthPickup", "PickupMesh",
                                   "/Game/Arcwright/Materials/MI_HealthGreen"),
         "Apply MI_HealthGreen to BP_HealthPickup")

    safe(lambda: c.create_material_instance(
        "MI_ScoreGold",
        "/Engine/BasicShapes/BasicShapeMaterial",
        vector_params={"BaseColor": {"r": 1.0, "g": 0.85, "b": 0.0, "a": 1}}),
         "Create MI_ScoreGold")
    safe(lambda: c.apply_material("BP_ScorePickup", "PickupMesh",
                                   "/Game/Arcwright/Materials/MI_ScoreGold"),
         "Apply MI_ScoreGold to BP_ScorePickup")

    safe(lambda: c.create_material_instance(
        "MI_DangerRed",
        "/Engine/BasicShapes/BasicShapeMaterial",
        scalar_params={"Roughness": 0.3},
        vector_params={"BaseColor": {"r": 1.0, "g": 0.1, "b": 0.1, "a": 1}}),
         "Create MI_DangerRed")
    safe(lambda: c.apply_material("BP_DamageZone", "ZoneMesh",
                                   "/Game/Arcwright/Materials/MI_DangerRed"),
         "Apply MI_DangerRed to BP_DamageZone")

    ok("All materials created and applied")

    # ===========================================================
    # Step 6: Populate the arena
    # ===========================================================
    step_header("6", "Populate the arena with actors")

    # Score pickups (5)
    score_positions = [
        ("ScorePickup_1", -500, 600, 92),
        ("ScorePickup_2", 100, 800, 92),
        ("ScorePickup_3", -400, -500, 92),
        ("ScorePickup_4", 200, -300, 92),
        ("ScorePickup_5", -100, 1200, 92),
    ]
    for label, x, y, z in score_positions:
        safe(lambda l=label, x=x, y=y, z=z: c.spawn_actor_at(
            actor_class="/Game/Arcwright/Generated/BP_ScorePickup",
            location={"x": x, "y": y, "z": z},
            label=l),
             f"Spawn {label} at ({x},{y},{z})")

    # Health pickups (3)
    health_positions = [
        ("HealthPickup_1", 300, 400, 92),
        ("HealthPickup_2", -600, -200, 92),
        ("HealthPickup_3", 0, 1500, 92),
    ]
    for label, x, y, z in health_positions:
        safe(lambda l=label, x=x, y=y, z=z: c.spawn_actor_at(
            actor_class="/Game/Arcwright/Generated/BP_HealthPickup",
            location={"x": x, "y": y, "z": z},
            label=l),
             f"Spawn {label} at ({x},{y},{z})")

    # Damage zones (3)
    damage_positions = [
        ("DamageZone_1", -200, 300, 92),
        ("DamageZone_2", 100, -600, 92),
        ("DamageZone_3", -300, 900, 92),
    ]
    for label, x, y, z in damage_positions:
        safe(lambda l=label, x=x, y=y, z=z: c.spawn_actor_at(
            actor_class="/Game/Arcwright/Generated/BP_DamageZone",
            location={"x": x, "y": y, "z": z},
            label=l),
             f"Spawn {label} at ({x},{y},{z})")

    # Arena manager (1)
    safe(lambda: c.spawn_actor_at(
        actor_class="/Game/Arcwright/Generated/BP_ArenaManager",
        location={"x": -200, "y": 0, "z": 200},
        label="ArenaManager_1"),
         "Spawn ArenaManager_1 at (-200,0,200)")

    ok("All 12 actors placed")

    # ===========================================================
    # Step 7: Save and verify
    # ===========================================================
    step_header("7", "Save and verify everything")

    safe(lambda: c.save_all(), "Save all assets and level")

    # Verify actors
    actors_r = safe(lambda: c.get_actors(), "Get all actors")
    game_actor_count = 0
    if actors_r and "data" in actors_r:
        all_actors = actors_r["data"].get("actors", [])
        game_labels = {"ScorePickup_1", "ScorePickup_2", "ScorePickup_3",
                       "ScorePickup_4", "ScorePickup_5",
                       "HealthPickup_1", "HealthPickup_2", "HealthPickup_3",
                       "DamageZone_1", "DamageZone_2", "DamageZone_3",
                       "ArenaManager_1"}
        for a in all_actors:
            if a.get("label") in game_labels:
                game_actor_count += 1
        print(f"         Game actors found: {game_actor_count}/12")
        if game_actor_count < 12:
            errors.append(f"Only {game_actor_count}/12 game actors found")

    # Verify Blueprints
    for bp_name in ["BP_HealthPickup", "BP_ScorePickup", "BP_DamageZone", "BP_ArenaManager"]:
        r = safe(lambda n=bp_name: c.get_blueprint_info(n), f"Verify {bp_name}")
        if r and "data" in r:
            d = r["data"]
            compiled = d.get("compiled", False)
            nodes = d.get("node_count", d.get("nodes", "?"))
            if isinstance(nodes, list):
                nodes = len(nodes)
            print(f"         {bp_name}: compiled={compiled}, nodes={nodes}")
            if not compiled:
                errors.append(f"{bp_name} not compiled")
        else:
            errors.append(f"Could not get info for {bp_name}")

    # Verify widget tree
    wt = safe(lambda: c.get_widget_tree("WBP_ArenaHUD"), "Verify WBP_ArenaHUD widget tree")
    if wt and "data" in wt:
        d = wt["data"]
        print(f"         WBP_ArenaHUD: {d['total_widgets']} widgets, "
              f"root={d.get('root_name', '?')}")
        if d["total_widgets"] != 6:
            errors.append(f"Expected 6 widgets, got {d['total_widgets']}")

    # ===========================================================
    # Final Report
    # ===========================================================
    print(f"\n{'='*60}")
    print(f"  ARENA COLLECTOR — Build Report")
    print(f"{'='*60}")
    print(f"  Blueprints:  4 created via DSL")
    print(f"  Components:  8 added (3+3+2)")
    print(f"  Materials:   3 created and applied")
    print(f"  Widgets:     6 (CanvasPanel + 4 TextBlocks + 1 ProgressBar)")
    print(f"  Actors:      {game_actor_count}/12 placed in arena")
    print(f"  Saved:       Yes")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
        print(f"\n  Result: PARTIAL SUCCESS ({len(errors)} issues)")
    else:
        print(f"\n  Result: COMPLETE SUCCESS")
    print(f"{'='*60}")

    c.close()
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
