#!/usr/bin/env python3
"""
demo_video_build.py — "Zero to Playable in 5 Minutes" demo builder.

Executes the exact sequence from the Arcwright demo video, creating a
complete playable arena level via TCP commands against a running UE Editor.

Usage:
    python scripts/demo_video_build.py                  # full run, 3s pauses
    python scripts/demo_video_build.py --delay 5        # 5s pauses (for recording)
    python scripts/demo_video_build.py --delay 0        # no pauses (test run)
    python scripts/demo_video_build.py --skip-to 3      # restart from Phase 3
    python scripts/demo_video_build.py --dry-run        # print plan without executing
"""

import argparse
import json
import sys
import time
import os

# Fix Windows cp1252 encoding crash on Unicode characters (Lesson #54)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mcp_client"))

from scripts.mcp_client.blueprint_client import ArcwrightClient


# ── Formatting helpers ───────────────────────────────────────────────────────

def banner(phase_num: int, title: str):
    """Print a phase banner."""
    line = "═" * 55
    print(f"\n{line}")
    print(f"  PHASE {phase_num}: {title}")
    print(f"{line}\n")


def step(msg: str):
    """Print a step within a phase."""
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}]  {msg}")


def ok(msg: str = "OK"):
    """Print success indicator."""
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}]  -> {msg}")


def fail(msg: str):
    """Print failure indicator."""
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}]  !! FAILED: {msg}")


def check(result: dict, label: str) -> dict:
    """Check a TCP command result. Print OK or FAIL. Return result."""
    status = result.get("status", "error")
    if status == "ok":
        ok(label)
    else:
        err = result.get("message", str(result))
        fail(f"{label}: {err}")
    return result


def stabilize():
    """Short pause to let UE process rendering commands (Lesson #40).

    Rapid sequential commands (materials, BPs, components) cause D3D12
    FlushRenderingCommands recursion crashes. 0.5s between heavy ops
    prevents the crash while keeping the demo fast.
    """
    time.sleep(0.5)


def phase_delay(seconds: float):
    """Pause between phases for visual clarity."""
    if seconds > 0:
        print(f"\n  ... pausing {seconds}s for viewport update ...\n")
        time.sleep(seconds)


# ── Phase implementations ───────────────────────────────────────────────────

def phase_0_connect(client: ArcwrightClient):
    """Verify connection to UE Editor."""
    banner(0, "Connecting to Unreal Editor")
    step("Health check on localhost:13377")
    r = client.health_check()
    check(r, f"Arcwright v{r.get('data', {}).get('version', '?')} — "
             f"UE {r.get('data', {}).get('engine', '?')}")

    step("Querying current level")
    r = client.get_level_info()
    d = r.get("data", {})
    ok(f"Level: {d.get('level_name', '?')}, Actors: {d.get('actor_count', '?')}")


def phase_1_setup(client: ArcwrightClient):
    """Shot 3: Scene setup — lighting + game mode."""
    banner(1, "Scene Setup — Lighting & Controls")

    step("Setting up dark indoor lighting")
    r = client.setup_scene_lighting("indoor_dark")
    check(r, "indoor_dark lighting (DirectionalLight + SkyLight + Fog)")

    step("Setting game mode to first-person")
    r = client.set_game_mode("BP_FirstPersonGameMode")
    check(r, "GameMode = BP_FirstPersonGameMode")


def phase_2_arena(client: ArcwrightClient):
    """Shot 4: Build the arena — floor, walls, torches, materials."""
    banner(2, "Building the Arena")

    # ── Materials ─────────────────────────────────────────────────────────
    step("Creating stone floor material")
    r = client.create_simple_material("MAT_StoneFloor",
                                      {"r": 0.35, "g": 0.32, "b": 0.28})
    check(r, "MAT_StoneFloor (warm stone gray)")
    stabilize()

    step("Creating brick wall material")
    r = client.create_simple_material("MAT_BrickWall",
                                      {"r": 0.55, "g": 0.25, "b": 0.15})
    check(r, "MAT_BrickWall (dark brick red)")
    stabilize()

    # ── Floor ─────────────────────────────────────────────────────────────
    step("Spawning stone floor (100m × 100m)")
    r = client.send_command("spawn_actor_at", {
        "class": "StaticMeshActor",
        "location": {"x": 0, "y": 0, "z": 0},
        "label": "Arena_Floor",
        "mesh": "/Engine/BasicShapes/Plane.Plane",
        "scale": {"x": 100, "y": 100, "z": 1}
    })
    floor_label = r.get("data", {}).get("label", "Arena_Floor")
    check(r, f"Floor spawned as '{floor_label}'")

    step("Applying stone material to floor")
    r = client.send_command("set_actor_material", {
        "actor_label": floor_label,
        "material_path": "/Game/Arcwright/Materials/MAT_StoneFloor"
    })
    check(r, "Stone material applied to floor")

    # ── Perimeter Walls ────────────────────────────────────────────────────
    # Arena is 10000×10000 cm (100m). Cube at scale 1 = 100cm per axis.
    # Wall height = 4 (400cm). Center-Z = 200 (half of 400).
    wall_defs = [
        # Perimeter
        ("Arena_WallN", 0, 5000, 200, 100, 1, 4),    # North
        ("Arena_WallS", 0, -5000, 200, 100, 1, 4),   # South
        ("Arena_WallE", 5000, 0, 200, 1, 100, 4),    # East
        ("Arena_WallW", -5000, 0, 200, 1, 100, 4),   # West
        # ── Internal geometry ──────────────────────────────────────────────
        # Center pillar — solid 400×400×400 cover block
        ("Cover_Pillar", 0, 0, 200, 4, 4, 4),
        # NW L-wall (long arm east-west, short arm drops south from west end)
        ("Cover_NW_Long", -2000, 2500, 200, 18, 1, 4),
        ("Cover_NW_Short", -2900, 1600, 200, 1, 9, 4),
        # SE L-wall (mirror of NW)
        ("Cover_SE_Long", 2000, -2500, 200, 18, 1, 4),
        ("Cover_SE_Short", 2900, -1600, 200, 1, 9, 4),
        # NE barrier — single wall creating a sight-line break
        ("Cover_NE_Wall", 2500, 1800, 200, 1, 14, 4),
        # West raised platform — half-height block for elevation change
        ("Cover_WestPlat", -3500, 0, 100, 15, 18, 2),
    ]

    step("Spawning perimeter + internal walls (11 pieces)")
    for label, x, y, z, sx, sy, sz in wall_defs:
        r = client.send_command("spawn_actor_at", {
            "class": "StaticMeshActor",
            "location": {"x": x, "y": y, "z": z},
            "label": label,
            "mesh": "/Engine/BasicShapes/Cube.Cube",
            "scale": {"x": sx, "y": sy, "z": sz}
        })
        client.send_command("set_actor_material", {
            "actor_label": label,
            "material_path": "/Game/Arcwright/Materials/MAT_BrickWall"
        })
    ok("4 perimeter + 7 internal walls spawned with brick material")

    # ── Torches ───────────────────────────────────────────────────────────
    step("Creating torch Blueprint with point light")
    r = client.create_blueprint_from_dsl("""
BLUEPRINT: BP_Torch
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_BeginPlay
""".strip())
    check(r, "BP_Torch created")
    stabilize()

    client.add_component("BP_Torch", "StaticMesh", "TorchMesh",
                         properties={"mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
                                     "scale": {"x": 0.3, "y": 0.3, "z": 1.0}})
    stabilize()
    client.add_component("BP_Torch", "PointLight", "TorchLight",
                         properties={"intensity": 8000.0,
                                     "light_color": {"r": 1.0, "g": 0.7, "b": 0.3},
                                     "attenuation_radius": 1500.0,
                                     "location": {"x": 0, "y": 0, "z": 120}})
    stabilize()
    ok("Torch mesh + warm point light added")

    step("Spawning 10 torches along walls and near cover")
    torch_class = "/Game/Arcwright/Generated/BP_Torch.BP_Torch"
    torch_positions = [
        (-3000, 4900, 50), (0, 4900, 50), (3000, 4900, 50),     # North wall
        (-3000, -4900, 50), (0, -4900, 50), (3000, -4900, 50),  # South wall
        (-2900, 2600, 50),   # NW L-wall corner (lights the corridor)
        (2900, -2600, 50),   # SE L-wall corner (mirror)
        (2600, 2600, 50),    # NE barrier top
        (-4200, 0, 250),     # West platform edge (elevated)
    ]
    for i, (tx, ty, tz) in enumerate(torch_positions):
        client.spawn_actor_at(torch_class,
                              location={"x": tx, "y": ty, "z": tz},
                              label=f"Torch_{i+1}")
    ok("10 torches placed along walls and near cover points")

    step("Saving arena")
    client.save_all()
    ok("Arena saved")
    stabilize()
    stabilize()  # Extra settling time after save_all (Lesson #40)


def phase_3_objects(client: ArcwrightClient):
    """Shot 5: Game objects — gold coins + health pickups."""
    banner(3, "Game Objects — Coins & Health Pickups")

    # ── Gold Coin ─────────────────────────────────────────────────────────
    step("Creating BP_GoldCoin Blueprint")
    r = client.create_blueprint_from_dsl("""
BLUEPRINT: BP_GoldCoin
PARENT: Actor
VAR PointValue: Integer = 10
GRAPH: EventGraph
NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="+10 Points!"]
NODE n3: DestroyActor
EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
""".strip())
    check(r, "BP_GoldCoin created with pickup logic")
    stabilize()

    step("Adding collision + mesh components")
    client.add_component("BP_GoldCoin", "SphereCollision", "PickupZone",
                         properties={"radius": 80,
                                     "generate_overlap_events": True})
    stabilize()
    client.add_component("BP_GoldCoin", "StaticMesh", "CoinMesh",
                         properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                                     "scale": {"x": 0.5, "y": 0.5, "z": 0.5}})
    stabilize()
    client.compile_blueprint("BP_GoldCoin")
    ok("SphereCollision + Sphere mesh + overlap logic compiled")

    step("Creating gold material for coins")
    client.create_simple_material("MAT_Gold",
                                  {"r": 1.0, "g": 0.85, "b": 0.0},
                                  emissive_strength=0.3)
    ok("MAT_Gold (emissive glow)")
    stabilize()

    step("Spawning 12 gold coins in tactical positions")
    coin_class = "/Game/Arcwright/Generated/BP_GoldCoin.BP_GoldCoin"
    coin_positions = [
        # NW corridor (inside the L-wall)
        ("Coin_NW1", -2500, 2000, 50),
        ("Coin_NW2", -1500, 2500, 50),
        ("Coin_NW3", -2900, 1200, 50),
        # SE corridor (inside the mirror L-wall)
        ("Coin_SE1", 2500, -2000, 50),
        ("Coin_SE2", 1500, -2500, 50),
        ("Coin_SE3", 2900, -1200, 50),
        # Flanking the center pillar
        ("Coin_C1", -600, 400, 50),
        ("Coin_C2", 600, -400, 50),
        # Along the NE barrier (have to go around it)
        ("Coin_NE1", 2000, 2200, 50),
        ("Coin_NE2", 3000, 1200, 50),
        # On top of the west platform (reward for climbing up)
        ("Coin_W1", -3500, 400, 250),
        ("Coin_W2", -3500, -400, 250),
    ]
    for label, cx, cy, cz in coin_positions:
        client.spawn_actor_at(coin_class,
                              location={"x": cx, "y": cy, "z": cz},
                              label=label)
        client.send_command("set_actor_material", {
            "actor_label": label,
            "material_path": "/Game/Arcwright/Materials/MAT_Gold"
        })
    ok("12 coins placed in corridors, behind cover, and on platform")

    # ── Health Pickup ─────────────────────────────────────────────────────
    step("Creating BP_HealthPickup Blueprint")
    r = client.create_blueprint_from_dsl("""
BLUEPRINT: BP_HealthPickup
PARENT: Actor
VAR HealAmount: Float = 25.0
GRAPH: EventGraph
NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="Healed +25 HP!"]
NODE n3: DestroyActor
EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute
""".strip())
    check(r, "BP_HealthPickup created with pickup logic")
    stabilize()

    client.add_component("BP_HealthPickup", "SphereCollision", "PickupZone",
                         properties={"radius": 80,
                                     "generate_overlap_events": True})
    stabilize()
    client.add_component("BP_HealthPickup", "StaticMesh", "HealthMesh",
                         properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                                     "scale": {"x": 0.6, "y": 0.6, "z": 0.6}})
    stabilize()
    client.compile_blueprint("BP_HealthPickup")
    ok("Health pickup compiled with collision + mesh")

    step("Creating green health material")
    client.create_simple_material("MAT_HealthGreen",
                                  {"r": 0.1, "g": 0.9, "b": 0.3},
                                  emissive_strength=0.4)
    ok("MAT_HealthGreen (emissive glow)")
    stabilize()

    step("Spawning 4 health pickups tucked behind cover")
    hp_class = "/Game/Arcwright/Generated/BP_HealthPickup.BP_HealthPickup"
    hp_positions = [
        # NW: deep inside the L-wall corner — have to enter the corridor
        ("Health_NW", -3200, 2800, 50),
        # SE: deep inside the mirror L-wall corner
        ("Health_SE", 3200, -2800, 50),
        # NE: behind the NE barrier wall (sheltered side)
        ("Health_NE", 3200, 2500, 50),
        # SW: behind the west platform (have to go around it)
        ("Health_SW", -4200, -1500, 50),
    ]
    for label, cx, cy, cz in hp_positions:
        client.spawn_actor_at(hp_class,
                              location={"x": cx, "y": cy, "z": cz},
                              label=label)
        client.send_command("set_actor_material", {
            "actor_label": label,
            "material_path": "/Game/Arcwright/Materials/MAT_HealthGreen"
        })
    ok("4 health pickups tucked behind cover walls")

    step("Saving game objects")
    client.save_all()
    ok("Game objects saved")
    stabilize()
    stabilize()


def phase_4_enemies(client: ArcwrightClient):
    """Shot 6: Enemies — BP + Behavior Tree + AI wiring + spawn."""
    banner(4, "Enemies — Patrol + Chase AI")

    # ── Enemy Blueprint ───────────────────────────────────────────────────
    step("Creating BP_PatrolEnemy (Pawn)")
    r = client.create_blueprint_from_dsl("""
BLUEPRINT: BP_PatrolEnemy
PARENT: Pawn
VAR Health: Float = 100.0
VAR Damage: Float = 15.0
VAR Speed: Float = 300.0
GRAPH: EventGraph
NODE n1: Event_BeginPlay
""".strip())
    check(r, "BP_PatrolEnemy created (Health=100, Damage=15, Speed=300)")
    stabilize()

    step("Adding movement + collision + mesh")
    client.add_component("BP_PatrolEnemy", "SphereCollision", "BodyCollision",
                         properties={"radius": 50,
                                     "generate_overlap_events": True})
    stabilize()
    client.add_component("BP_PatrolEnemy", "StaticMesh", "EnemyMesh",
                         properties={"mesh": "/Engine/BasicShapes/Cube.Cube",
                                     "scale": {"x": 1.0, "y": 1.0, "z": 2.0}})
    stabilize()
    # FloatingPawnMovement — for simple AI movement without NavMesh
    client.send_command("add_component", {
        "blueprint": "BP_PatrolEnemy",
        "component_type": "FloatingPawnMovement",
        "component_name": "Movement"
    })
    stabilize()
    ok("FloatingPawnMovement + SphereCollision + Cube mesh")

    step("Creating enemy red material")
    client.create_simple_material("MAT_EnemyRed",
                                  {"r": 0.9, "g": 0.1, "b": 0.1},
                                  emissive_strength=0.2)
    ok("MAT_EnemyRed (subtle glow)")
    stabilize()

    # ── Behavior Tree ─────────────────────────────────────────────────────
    step("Creating patrol+chase behavior tree")
    bt_dsl = """BEHAVIORTREE: BT_PatrolChase
BLACKBOARD: BB_PatrolChase

KEY TargetActor: Object
KEY PatrolLocation: Vector

TREE:

SELECTOR: Root
  SEQUENCE: Chase
    DECORATOR: BlackboardBased [Key=TargetActor, Condition=IsSet, AbortMode=LowerPriority]
    TASK: MoveTo [Key=TargetActor, AcceptableRadius=200]
  SEQUENCE: Patrol
    TASK: MoveTo [Key=PatrolLocation, AcceptableRadius=100]
    TASK: Wait [Duration=2.0]
"""
    r = client.create_behavior_tree_from_dsl(bt_dsl)
    check(r, "BT_PatrolChase + BB_PatrolChase created")

    # ── Wire AI to Pawn ───────────────────────────────────────────────────
    step("Wiring AI controller to pawn")
    r = client.setup_ai_for_pawn("BP_PatrolEnemy", "BT_PatrolChase")
    check(r, "AIController → BT_PatrolChase → BP_PatrolEnemy")

    client.compile_blueprint("BP_PatrolEnemy")

    # ── Spawn Enemies at tactical positions ────────────────────────────────
    step("Spawning 5 enemies patrolling between cover")
    enemy_class = "/Game/Arcwright/Generated/BP_PatrolEnemy.BP_PatrolEnemy"
    enemy_positions = [
        # Between center pillar and NW L-wall
        ("Enemy_NW", -1200, 1500, 50),
        # Between center pillar and SE L-wall
        ("Enemy_SE", 1200, -1500, 50),
        # Guarding NE barrier corridor
        ("Enemy_NE", 2500, 800, 50),
        # On the west raised platform
        ("Enemy_WPlat", -3500, 300, 250),
        # Open south corridor (between SE L-wall and south perimeter)
        ("Enemy_S", 0, -4000, 50),
    ]
    for label, ex, ey, ez in enemy_positions:
        client.spawn_actor_at(enemy_class,
                              location={"x": ex, "y": ey, "z": ez},
                              label=label)
        client.send_command("set_actor_material", {
            "actor_label": label,
            "material_path": "/Game/Arcwright/Materials/MAT_EnemyRed"
        })
    ok("5 enemies placed at patrol positions near cover")

    step("Saving enemies")
    client.save_all()
    ok("Enemies saved")
    stabilize()
    stabilize()


def phase_5_hud(client: ArcwrightClient):
    """Shot 7: Game HUD with health bar and score counter."""
    banner(5, "Game HUD — Health Bar & Score")

    step("Creating WBP_GameHUD widget blueprint")
    r = client.create_widget_blueprint("WBP_GameHUD")
    check(r, "WBP_GameHUD created")

    step("Adding root CanvasPanel")
    client.add_widget_child("WBP_GameHUD", "CanvasPanel", "RootCanvas")

    # ── Health Section (top-left) ─────────────────────────────────────────
    step("Adding health label and bar (top-left)")
    client.add_widget_child("WBP_GameHUD", "TextBlock", "HealthLabel",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "HealthLabel",
                               "text", "HEALTH")
    client.set_widget_property("WBP_GameHUD", "HealthLabel",
                               "font_size", 18)
    client.set_widget_property("WBP_GameHUD", "HealthLabel",
                               "color", {"r": 0.2, "g": 1.0, "b": 0.4, "a": 1.0})
    client.set_widget_property("WBP_GameHUD", "HealthLabel",
                               "position", {"x": 40, "y": 30})

    client.add_widget_child("WBP_GameHUD", "ProgressBar", "HealthBar",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "HealthBar",
                               "percent", 0.75)
    client.set_widget_property("WBP_GameHUD", "HealthBar",
                               "fill_color", {"r": 0.2, "g": 0.9, "b": 0.3, "a": 1.0})
    client.set_widget_property("WBP_GameHUD", "HealthBar",
                               "position", {"x": 40, "y": 55})
    client.set_widget_property("WBP_GameHUD", "HealthBar",
                               "size", {"x": 250, "y": 20})
    ok("Health bar at 75% (top-left)")

    # ── Score Section (top-right) ─────────────────────────────────────────
    step("Adding score counter (top-right)")
    client.add_widget_child("WBP_GameHUD", "TextBlock", "ScoreLabel",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "ScoreLabel",
                               "text", "SCORE")
    client.set_widget_property("WBP_GameHUD", "ScoreLabel",
                               "font_size", 18)
    client.set_widget_property("WBP_GameHUD", "ScoreLabel",
                               "color", {"r": 1.0, "g": 0.85, "b": 0.0, "a": 1.0})
    client.set_widget_property("WBP_GameHUD", "ScoreLabel",
                               "position", {"x": 1680, "y": 30})

    client.add_widget_child("WBP_GameHUD", "TextBlock", "ScoreValue",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "ScoreValue",
                               "text", "0")
    client.set_widget_property("WBP_GameHUD", "ScoreValue",
                               "font_size", 36)
    client.set_widget_property("WBP_GameHUD", "ScoreValue",
                               "color", {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0})
    client.set_widget_property("WBP_GameHUD", "ScoreValue",
                               "position", {"x": 1690, "y": 52})
    ok("Score counter (top-right)")

    # ── Crosshair (center) ────────────────────────────────────────────────
    step("Adding crosshair indicator (center)")
    client.add_widget_child("WBP_GameHUD", "TextBlock", "Crosshair",
                            parent_widget="RootCanvas")
    client.set_widget_property("WBP_GameHUD", "Crosshair",
                               "text", "+")
    client.set_widget_property("WBP_GameHUD", "Crosshair",
                               "font_size", 24)
    client.set_widget_property("WBP_GameHUD", "Crosshair",
                               "color", {"r": 1.0, "g": 1.0, "b": 1.0, "a": 0.6})
    client.set_widget_property("WBP_GameHUD", "Crosshair",
                               "position", {"x": 950, "y": 530})
    ok("Crosshair at center")

    step("Saving HUD")
    client.save_all()
    ok("WBP_GameHUD saved")


def phase_6_modify(client: ArcwrightClient):
    """Shot 8: Live modification — buff enemies, swap floor material."""
    banner(6, "Live Modification — Buff & Restyle")

    # ── Buff enemies ──────────────────────────────────────────────────────
    step("Buffing enemies: Health 100→200, Damage 15→25")
    r = client.batch_set_variable([
        {"blueprint": "BP_PatrolEnemy", "variable_name": "Health",
         "default_value": "200.0"},
        {"blueprint": "BP_PatrolEnemy", "variable_name": "Damage",
         "default_value": "25.0"},
    ])
    d = r.get("data", {})
    check(r, f"Batch variable update: {d.get('succeeded', '?')} succeeded")

    # ── Swap floor material ───────────────────────────────────────────────
    step("Creating marble floor material")
    client.create_simple_material("MAT_MarbleFloor",
                                  {"r": 0.85, "g": 0.82, "b": 0.78})
    ok("MAT_MarbleFloor (polished white)")
    stabilize()

    step("Finding floor actor")
    actors = client.find_actors(name_filter="Arena_Floor")
    floor_actors = actors.get("data", {}).get("actors", [])
    if floor_actors:
        floor_label = floor_actors[0]["label"]
        step(f"Replacing floor material on '{floor_label}'")
        r = client.send_command("set_actor_material", {
            "actor_label": floor_label,
            "material_path": "/Game/Arcwright/Materials/MAT_MarbleFloor"
        })
        check(r, "Floor material → marble")
    else:
        fail("Floor actor not found!")

    # ── Final save ────────────────────────────────────────────────────────
    step("Final save")
    client.save_all()
    ok("All changes saved")


def phase_7_summary(client: ArcwrightClient):
    """Print a final summary of everything created."""
    banner(7, "Build Complete — Summary")

    step("Auditing level contents")
    r = client.get_level_info()
    d = r.get("data", {})
    print(f"\n  Level: {d.get('level_name', '?')}")
    print(f"  Total actors: {d.get('actor_count', '?')}")

    # Count by category
    actors = client.get_actors()
    all_actors = actors.get("data", {}).get("actors", [])
    categories = {}
    for a in all_actors:
        cls = a.get("class", "Unknown")
        categories[cls] = categories.get(cls, 0) + 1

    print(f"\n  Actors by class:")
    for cls, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    {cls}: {count}")

    print(f"""
  ╔═══════════════════════════════════════════╗
  ║  DEMO BUILD COMPLETE                      ║
  ║                                           ║
  ║  Blueprints: BP_GoldCoin                  ║
  ║              BP_HealthPickup              ║
  ║              BP_PatrolEnemy               ║
  ║              BP_Torch                     ║
  ║  BT:         BT_PatrolChase              ║
  ║  Widget:     WBP_GameHUD                  ║
  ║  Materials:  MAT_StoneFloor               ║
  ║              MAT_BrickWall                ║
  ║              MAT_Gold                     ║
  ║              MAT_HealthGreen              ║
  ║              MAT_EnemyRed                 ║
  ║              MAT_MarbleFloor              ║
  ║                                           ║
  ║  Click PLAY in the editor to test!        ║
  ╚═══════════════════════════════════════════╝
""")


# ── Main ─────────────────────────────────────────────────────────────────────

PHASES = [
    (0, "Connect", phase_0_connect),
    (1, "Scene Setup", phase_1_setup),
    (2, "Build Arena", phase_2_arena),
    (3, "Game Objects", phase_3_objects),
    (4, "Enemies", phase_4_enemies),
    (5, "HUD", phase_5_hud),
    (6, "Modification", phase_6_modify),
    (7, "Summary", phase_7_summary),
]


def main():
    parser = argparse.ArgumentParser(
        description="Arcwright Demo Video Builder — Zero to Playable in 5 Minutes")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Seconds to pause between phases (default: 3)")
    parser.add_argument("--skip-to", type=int, default=0,
                        help="Skip to phase N (0=connect, 1=setup, 2=arena, ...)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print phase plan without executing")
    parser.add_argument("--host", default="localhost",
                        help="UE command server host (default: localhost)")
    parser.add_argument("--port", type=int, default=13377,
                        help="UE command server port (default: 13377)")
    args = parser.parse_args()

    print("=" * 55)
    print("  ARCWRIGHT — Zero to Playable in 5 Minutes")
    print("  Demo Video Build Script")
    print(f"  Delay: {args.delay}s | Skip-to: Phase {args.skip_to}")
    print("=" * 55)

    if args.dry_run:
        print("\n  DRY RUN — Phase plan:\n")
        for num, name, _ in PHASES:
            marker = "  SKIP" if num < args.skip_to else "  RUN "
            print(f"  {marker}  Phase {num}: {name}")
        print("\n  No commands sent. Use without --dry-run to execute.")
        return

    # Connect
    print(f"\n  Connecting to {args.host}:{args.port}...")
    try:
        client = ArcwrightClient(host=args.host, port=args.port, timeout=60.0)
    except Exception as e:
        print(f"\n  !! FAILED to connect: {e}")
        print("  Is the UE Editor running with the Arcwright plugin?")
        sys.exit(1)

    start_time = time.time()
    failed_phases = []

    try:
        for num, name, func in PHASES:
            if num < args.skip_to:
                continue
            try:
                func(client)
            except Exception as e:
                fail(f"Phase {num} ({name}) failed: {e}")
                failed_phases.append((num, name, str(e)))

            # Delay between phases (except last)
            if num < len(PHASES) - 1 and num >= args.skip_to:
                phase_delay(args.delay)

    finally:
        elapsed = time.time() - start_time
        client.close()

    # Final report
    print(f"\n  Total time: {elapsed:.1f}s")
    if failed_phases:
        print(f"\n  !! {len(failed_phases)} phase(s) had errors:")
        for num, name, err in failed_phases:
            print(f"     Phase {num} ({name}): {err}")
        sys.exit(1)
    else:
        print("  All phases completed successfully!")


if __name__ == "__main__":
    main()
