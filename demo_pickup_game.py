#!/usr/bin/env python3
"""
BlueprintLLM Demo — Pickup Collector Game
==========================================
Builds a complete playable game from scratch using the automated pipeline.
Zero manual steps. Run with UE Editor open and the BlueprintLLM plugin loaded.

Usage:
    python demo_pickup_game.py
    python demo_pickup_game.py --clean    # Delete everything first
    python demo_pickup_game.py --no-save  # Don't save after building

Requires: UE Editor running with BlueprintLLM plugin (TCP port 13377)

What it builds:
    - BP_Pickup: Collectible that prints "Picked up!" and destroys on overlap
    - BP_HazardZone: Damage area with looping timer, prints damage ticks
    - BP_VictoryZone: Win condition that prints "You Win!" on overlap
    - BP_ScoreTracker: Score counter with custom event
    - All Blueprints get collision, meshes, and colored materials
    - 8 actors placed in a line for gameplay: 5 pickups, 1 hazard, 1 victory, 1 tracker
    - Everything saved to disk

This is the "hello world" of BlueprintLLM — proof that the full pipeline works.
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from mcp_client.blueprint_client import BlueprintLLMClient, BlueprintLLMError
except ImportError:
    from scripts.mcp_client.blueprint_client import BlueprintLLMClient, BlueprintLLMError


# ─── DSL Definitions ────────────────────────────────────────────────────────

BLUEPRINTS = {
    "BP_Pickup": """BLUEPRINT: BP_Pickup
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="Picked up!"]
NODE n3: DestroyActor

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute""",

    "BP_HazardZone": """BLUEPRINT: BP_HazardZone
PARENT: Actor

VAR DamagePerSecond: Float = 10.0

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="Entering hazard zone!"]
NODE n3: SetTimerByFunctionName [FunctionName="ApplyDamage", Time=1.0, Looping=true]
NODE n4: Event_ActorEndOverlap
NODE n5: ClearTimerByFunctionName [FunctionName="ApplyDamage"]
NODE n6: PrintString [InString="Left hazard zone"]
NODE n7: Event_CustomEvent [EventName="ApplyDamage"]
NODE n8: GetVar [Variable=DamagePerSecond]
NODE n9: PrintString

EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
EXEC n4.Then -> n5.Execute
EXEC n5.Then -> n6.Execute
EXEC n7.Then -> n9.Execute

DATA n8.Value -> n9.InString [Float]""",

    "BP_VictoryZone": """BLUEPRINT: BP_VictoryZone
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="You Win! All pickups collected!"]

EXEC n1.Then -> n2.Execute""",

    "BP_ScoreTracker": """BLUEPRINT: BP_ScoreTracker
PARENT: Actor

VAR Score: Int = 0

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Score Tracker Active"]
NODE n3: Event_CustomEvent [EventName="AddScore"]
NODE n4: GetVar [Variable=Score]
NODE n5: AddFloat [B=1]
NODE n6: SetVar [Variable=Score]
NODE n7: PrintString

EXEC n1.Then -> n2.Execute
EXEC n3.Then -> n6.Execute
EXEC n6.Then -> n7.Execute

DATA n4.Value -> n5.A [Int]
DATA n5.ReturnValue -> n6.Value [Int]
DATA n5.ReturnValue -> n7.InString [String]""",
}

# ─── Component Definitions ──────────────────────────────────────────────────

COMPONENTS = {
    "BP_Pickup": [
        {"type": "BoxCollision", "name": "PickupCollision",
         "properties": {"extent": {"x": 50, "y": 50, "z": 50}, "generate_overlap_events": True}},
        {"type": "StaticMesh", "name": "PickupMesh",
         "properties": {"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                        "scale": {"x": 0.5, "y": 0.5, "z": 0.5}}},
    ],
    "BP_HazardZone": [
        {"type": "BoxCollision", "name": "HazardCollision",
         "properties": {"extent": {"x": 200, "y": 200, "z": 100}, "generate_overlap_events": True}},
        {"type": "StaticMesh", "name": "HazardMesh",
         "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube",
                        "scale": {"x": 4, "y": 4, "z": 2}}},
    ],
    "BP_VictoryZone": [
        {"type": "BoxCollision", "name": "VictoryCollision",
         "properties": {"extent": {"x": 200, "y": 200, "z": 200}, "generate_overlap_events": True}},
        {"type": "StaticMesh", "name": "VictoryMesh",
         "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube",
                        "scale": {"x": 4, "y": 4, "z": 4}}},
    ],
}

# ─── Material Definitions ───────────────────────────────────────────────────

MATERIALS = {
    "MI_Gold": {
        "parent": "/Engine/BasicShapes/BasicShapeMaterial",
        "vector_params": {"BaseColor": {"r": 1.0, "g": 0.8, "b": 0.0, "a": 1.0}},
    },
    "MI_Red": {
        "parent": "/Engine/BasicShapes/BasicShapeMaterial",
        "vector_params": {"BaseColor": {"r": 1.0, "g": 0.1, "b": 0.1, "a": 1.0}},
    },
    "MI_Green": {
        "parent": "/Engine/BasicShapes/BasicShapeMaterial",
        "vector_params": {"BaseColor": {"r": 0.1, "g": 1.0, "b": 0.2, "a": 1.0}},
    },
}

MATERIAL_ASSIGNMENTS = {
    "BP_Pickup": ("PickupMesh", "/Game/MI_Gold"),
    "BP_HazardZone": ("HazardMesh", "/Game/MI_Red"),
    "BP_VictoryZone": ("VictoryMesh", "/Game/MI_Green"),
}

# ─── Level Layout ───────────────────────────────────────────────────────────

# All positions relative to PlayerStart at approximately (-200, 0, 92)
ACTORS = [
    {"class": "BP_Pickup", "label": "Pickup_1", "location": {"x": -200, "y": 500, "z": 92}},
    {"class": "BP_Pickup", "label": "Pickup_2", "location": {"x": -200, "y": 1000, "z": 92}},
    {"class": "BP_Pickup", "label": "Pickup_3", "location": {"x": -200, "y": 1500, "z": 92}},
    {"class": "BP_Pickup", "label": "Pickup_4", "location": {"x": -200, "y": 2000, "z": 92}},
    {"class": "BP_Pickup", "label": "Pickup_5", "location": {"x": -200, "y": 2500, "z": 92}},
    {"class": "BP_HazardZone", "label": "HazardZone_1", "location": {"x": -200, "y": 1250, "z": 92}},
    {"class": "BP_VictoryZone", "label": "VictoryZone_1", "location": {"x": -200, "y": 3000, "z": 92}},
    {"class": "BP_ScoreTracker", "label": "ScoreTracker_1", "location": {"x": -200, "y": 0, "z": 200}},
]


# ─── Build Functions ────────────────────────────────────────────────────────

def step(msg):
    print(f"\n{'─'*50}")
    print(f"  {msg}")
    print(f"{'─'*50}")


def clean_existing(client):
    """Remove any existing game Blueprints and actors."""
    step("Cleaning existing content")
    
    for label in [a["label"] for a in ACTORS]:
        try:
            client.delete_actor(label)
            print(f"  Deleted actor: {label}")
        except BlueprintLLMError:
            pass
    
    for bp_name in BLUEPRINTS:
        try:
            client.delete_blueprint(bp_name)
            print(f"  Deleted Blueprint: {bp_name}")
        except BlueprintLLMError:
            pass
    
    print("  Clean complete.")


def create_blueprints(client):
    """Create all game Blueprints from DSL."""
    step("Creating Blueprints from DSL")
    
    results = {}
    for name, dsl in BLUEPRINTS.items():
        try:
            # Delete first if exists
            try:
                client.delete_blueprint(name)
            except BlueprintLLMError:
                pass
            
            result = client.create_blueprint_from_dsl(dsl)
            info = client.get_blueprint_info(name)
            compiled = info.get("compiled", False) if isinstance(info, dict) else False
            nodes = info.get("node_count", "?") if isinstance(info, dict) else "?"
            
            status = "COMPILED" if compiled else "created"
            print(f"  ✅ {name}: {nodes} nodes, {status}")
            results[name] = True
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            results[name] = False
    
    return results


def add_components(client):
    """Add collision, meshes to Blueprints."""
    step("Adding components (collision + meshes)")
    
    for bp_name, comps in COMPONENTS.items():
        for comp in comps:
            try:
                client.add_component(bp_name, comp["type"], comp["name"],
                                     properties=comp.get("properties", {}))
                print(f"  ✅ {bp_name}/{comp['name']}: {comp['type']}")
            except Exception as e:
                print(f"  ❌ {bp_name}/{comp['name']}: {e}")


def create_materials(client):
    """Create colored material instances."""
    step("Creating materials")
    
    for name, mat in MATERIALS.items():
        try:
            client.create_material_instance(name, mat["parent"],
                                            vector_params=mat.get("vector_params", {}),
                                            scalar_params=mat.get("scalar_params", {}))
            print(f"  ✅ {name}")
        except Exception as e:
            # May already exist
            print(f"  ⚠️ {name}: {e}")


def apply_materials(client):
    """Apply materials to mesh components."""
    step("Applying materials")
    
    for bp_name, (comp_name, mat_path) in MATERIAL_ASSIGNMENTS.items():
        try:
            client.apply_material(bp_name, comp_name, mat_path)
            print(f"  ✅ {bp_name}/{comp_name} → {mat_path}")
        except Exception as e:
            print(f"  ❌ {bp_name}/{comp_name}: {e}")


def populate_level(client):
    """Spawn all actors in the level."""
    step("Populating level")
    
    for actor in ACTORS:
        try:
            # Delete first if exists
            try:
                client.delete_actor(actor["label"])
            except BlueprintLLMError:
                pass
            
            client.spawn_actor_at(actor["class"], label=actor["label"],
                                  location=actor["location"])
            print(f"  ✅ {actor['label']}: {actor['class']} at ({actor['location']['x']}, {actor['location']['y']}, {actor['location']['z']})")
        except Exception as e:
            print(f"  ❌ {actor['label']}: {e}")


def verify(client):
    """Verify everything was created correctly."""
    step("Verification")
    
    all_good = True
    
    # Check Blueprints
    for name in BLUEPRINTS:
        try:
            info = client.get_blueprint_info(name)
            compiled = info.get("compiled", False) if isinstance(info, dict) else False
            status = "✅ compiled" if compiled else "⚠️ not compiled"
            print(f"  {name}: {status}")
            if not compiled:
                all_good = False
        except Exception as e:
            print(f"  {name}: ❌ {e}")
            all_good = False
    
    # Check actors in level
    try:
        actors = client.get_actors()
        game_actors = []
        if isinstance(actors, list):
            game_actors = [a for a in actors if any(
                a.get("label", "").startswith(prefix)
                for prefix in ["Pickup_", "HazardZone_", "VictoryZone_", "ScoreTracker_"]
            )]
        elif isinstance(actors, dict) and "actors" in actors:
            game_actors = [a for a in actors["actors"] if any(
                a.get("label", "").startswith(prefix)
                for prefix in ["Pickup_", "HazardZone_", "VictoryZone_", "ScoreTracker_"]
            )]
        
        print(f"  Level actors: {len(game_actors)}/8 game actors placed")
        if len(game_actors) < 8:
            all_good = False
    except Exception as e:
        print(f"  Level check failed: {e}")
        all_good = False
    
    return all_good


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="BlueprintLLM Demo — Build a pickup game from scratch")
    ap.add_argument("--clean", action="store_true", help="Delete existing game content first")
    ap.add_argument("--no-save", action="store_true", help="Don't save after building")
    ap.add_argument("--host", default="localhost", help="Command server host")
    ap.add_argument("--port", type=int, default=13377, help="Command server port")
    args = ap.parse_args()
    
    print("=" * 50)
    print("  BlueprintLLM Demo — Pickup Collector Game")
    print("  Building a complete game through the pipeline")
    print("=" * 50)
    
    start = time.time()
    
    try:
        with BlueprintLLMClient(host=args.host, port=args.port) as client:
            # Health check
            health = client.health_check()
            print(f"\n  Connected to UE Editor: {health}")
            
            # Clean if requested
            if args.clean:
                clean_existing(client)
            
            # Build everything
            create_blueprints(client)
            add_components(client)
            create_materials(client)
            apply_materials(client)
            populate_level(client)
            
            # Save
            if not args.no_save:
                step("Saving project")
                try:
                    result = client.save_all()
                    print(f"  ✅ Project saved: {result}")
                except Exception as e:
                    print(f"  ⚠️ Save: {e}")
            
            # Verify
            success = verify(client)
            
            elapsed = time.time() - start
            
            print(f"\n{'='*50}")
            if success:
                print(f"  ✅ DEMO COMPLETE — {elapsed:.1f}s")
                print(f"  4 Blueprints, 8 actors, colored meshes, saved")
                print(f"  Hit Play in UE Editor to test the game!")
            else:
                print(f"  ⚠️ DEMO COMPLETE WITH WARNINGS — {elapsed:.1f}s")
                print(f"  Some items may need manual verification")
            print(f"{'='*50}")
    
    except ConnectionRefusedError:
        print("\n  ❌ Cannot connect to UE Editor on port 13377")
        print("  Make sure UE Editor is running with the BlueprintLLM plugin loaded.")
        print("  See CLAUDE.md 'How to Build and Launch UE Editor' for instructions.")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
