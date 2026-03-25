"""
Rebuild Arena v2 — Dynamic HUD + Variable Tracking
Deletes old game BPs, imports new IRs with variables/custom events,
builds WBP_ArenaHUD, adds components/materials, spawns actors.
"""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.mcp_client.blueprint_client import ArcwrightClient

IR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_ir")

GAME_BPS = ["BP_ArenaManager", "BP_ScorePickup", "BP_DamageZone", "BP_HealthPickup"]
GAME_IR_FILES = {
    "BP_ArenaManager": "game_arena_manager_v2.blueprint.json",
    "BP_ScorePickup": "game_score_pickup_v2.blueprint.json",
    "BP_DamageZone": "game_damage_zone_v2.blueprint.json",
    "BP_HealthPickup": "game_health_pickup_v2.blueprint.json",
}

# Actor spawn layout
SPAWN_LIST = [
    # Score pickups (gold cubes) - scattered around arena
    {"bp": "BP_ScorePickup", "label": "ScorePickup_1", "loc": {"x": 800, "y": 300, "z": 80}},
    {"bp": "BP_ScorePickup", "label": "ScorePickup_2", "loc": {"x": -600, "y": 500, "z": 80}},
    {"bp": "BP_ScorePickup", "label": "ScorePickup_3", "loc": {"x": 200, "y": -700, "z": 80}},
    {"bp": "BP_ScorePickup", "label": "ScorePickup_4", "loc": {"x": -400, "y": -400, "z": 80}},
    {"bp": "BP_ScorePickup", "label": "ScorePickup_5", "loc": {"x": 1000, "y": -200, "z": 80}},
    # Health pickups (green spheres) - spread out
    {"bp": "BP_HealthPickup", "label": "HealthPickup_1", "loc": {"x": -800, "y": 0, "z": 80}},
    {"bp": "BP_HealthPickup", "label": "HealthPickup_2", "loc": {"x": 500, "y": 800, "z": 80}},
    {"bp": "BP_HealthPickup", "label": "HealthPickup_3", "loc": {"x": 0, "y": -900, "z": 80}},
    # Damage zones (red cubes) - obstacles
    {"bp": "BP_DamageZone", "label": "DamageZone_1", "loc": {"x": 300, "y": 0, "z": 50}},
    {"bp": "BP_DamageZone", "label": "DamageZone_2", "loc": {"x": -300, "y": 300, "z": 50}},
    {"bp": "BP_DamageZone", "label": "DamageZone_3", "loc": {"x": 0, "y": 500, "z": 50}},
    # Arena Manager (invisible, at origin)
    {"bp": "BP_ArenaManager", "label": "ArenaManager", "loc": {"x": 0, "y": 0, "z": 200}},
]


def step(n, msg):
    print(f"\n{'='*60}")
    print(f"  STEP {n}: {msg}")
    print(f"{'='*60}")


def main():
    client = ArcwrightClient()

    # ── Step 1: Health check ──
    step(1, "Health Check")
    r = client.health_check()
    print(f"  Connected: {r['data']['server']} v{r['data']['version']} ({r['data']['engine_version']})")

    # ── Step 1b: Scene Lighting (Lesson #42) ──
    step("1b", "Setup Scene Lighting")
    try:
        r = client.setup_scene_lighting('indoor_bright')
        print(f"  Scene lighting: {r.get('data', {}).get('actors_created', 0)} actors ({r.get('data', {}).get('preset', '')})")
    except Exception as e:
        print(f"  WARN: setup_scene_lighting not available: {e}")
        print("  (Plugin may need rebuild for this command)")

    # ── Step 1c: Floor (Lesson #43) ──
    step("1c", "Spawn Ground Floor")
    client.send_command('spawn_actor_at', {
        'class': 'StaticMeshActor',
        'label': 'ArenaFloor',
        'location': {'x': 0, 'y': 0, 'z': 0},
        'scale': {'x': 100, 'y': 100, 'z': 1},
        'mesh': '/Engine/BasicShapes/Plane.Plane'
    })

    # ── Step 2: Delete old game actors ──
    step(2, "Delete Old Game Actors")
    actors_resp = client.get_actors()
    if actors_resp.get("status") == "ok":
        actors = actors_resp["data"].get("actors", [])
        labels_to_delete = []
        for a in actors:
            label = a.get("label", "")
            # Match any of our game actors
            for prefix in ["ScorePickup_", "HealthPickup_", "DamageZone_", "ArenaManager",
                           "BP_ScorePickup", "BP_HealthPickup", "BP_DamageZone", "BP_ArenaManager"]:
                if label.startswith(prefix):
                    labels_to_delete.append(label)
                    break
        print(f"  Found {len(labels_to_delete)} game actors to delete")
        for label in labels_to_delete:
            r = client.delete_actor(label)
            status = "deleted" if r.get("data", {}).get("deleted") else "not found"
            print(f"    {label}: {status}")
    else:
        print("  WARNING: Could not list actors, continuing...")

    # ── Step 3: Delete old game Blueprints ──
    step(3, "Delete Old Game Blueprints")
    for bp_name in GAME_BPS:
        r = client.delete_blueprint(bp_name)
        if r.get("status") == "ok":
            print(f"  Deleted: {bp_name}")
        else:
            print(f"  {bp_name}: {r.get('message', 'not found / already gone')}")
    time.sleep(1)  # let asset registry settle

    # ── Step 4: Build WBP_ArenaHUD Widget ──
    step(4, "Build WBP_ArenaHUD Widget")
    # Delete existing widget BP if any
    client.delete_blueprint("WBP_ArenaHUD")
    time.sleep(0.5)

    r = client.create_widget_blueprint("WBP_ArenaHUD")
    print(f"  Created widget: {r.get('status')}")

    # Root canvas
    r = client.add_widget_child("WBP_ArenaHUD", "CanvasPanel", "RootCanvas")
    print(f"  Added RootCanvas: {r.get('status')}")

    # Title text
    r = client.add_widget_child("WBP_ArenaHUD", "TextBlock", "TitleLabel", parent_widget="RootCanvas")
    print(f"  Added TitleLabel: {r.get('status')}")
    client.set_widget_property("WBP_ArenaHUD", "TitleLabel", "text", "ARENA COLLECTOR")
    client.set_widget_property("WBP_ArenaHUD", "TitleLabel", "font_size", "28")
    client.set_widget_property("WBP_ArenaHUD", "TitleLabel", "color",
                               {"r": 1.0, "g": 0.85, "b": 0.0, "a": 1.0})
    client.set_widget_property("WBP_ArenaHUD", "TitleLabel", "position", {"x": 20, "y": 10})

    # Score label
    r = client.add_widget_child("WBP_ArenaHUD", "TextBlock", "ScoreLabel", parent_widget="RootCanvas")
    print(f"  Added ScoreLabel: {r.get('status')}")
    client.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "text", "Score: 0")
    client.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "font_size", "22")
    client.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "color",
                               {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0})
    client.set_widget_property("WBP_ArenaHUD", "ScoreLabel", "position", {"x": 20, "y": 50})

    # Health label
    r = client.add_widget_child("WBP_ArenaHUD", "TextBlock", "HealthLabel", parent_widget="RootCanvas")
    print(f"  Added HealthLabel: {r.get('status')}")
    client.set_widget_property("WBP_ArenaHUD", "HealthLabel", "text", "Health: 100")
    client.set_widget_property("WBP_ArenaHUD", "HealthLabel", "font_size", "20")
    client.set_widget_property("WBP_ArenaHUD", "HealthLabel", "color",
                               {"r": 0.3, "g": 1.0, "b": 0.3, "a": 1.0})
    client.set_widget_property("WBP_ArenaHUD", "HealthLabel", "position", {"x": 20, "y": 85})

    # Health bar
    r = client.add_widget_child("WBP_ArenaHUD", "ProgressBar", "HealthBar", parent_widget="RootCanvas")
    print(f"  Added HealthBar: {r.get('status')}")
    client.set_widget_property("WBP_ArenaHUD", "HealthBar", "percent", "1.0")
    client.set_widget_property("WBP_ArenaHUD", "HealthBar", "fill_color",
                               {"r": 0.0, "g": 0.9, "b": 0.1, "a": 1.0})
    client.set_widget_property("WBP_ArenaHUD", "HealthBar", "position", {"x": 20, "y": 115})
    client.set_widget_property("WBP_ArenaHUD", "HealthBar", "size", {"x": 300, "y": 25})

    print("  WBP_ArenaHUD complete")

    # ── Step 5: Import Blueprint IRs ──
    step(5, "Import Blueprint IRs")
    import_results = {}
    for bp_name, ir_file in GAME_IR_FILES.items():
        ir_path = os.path.join(IR_DIR, ir_file)
        # Use forward slashes for UE
        ir_path_ue = ir_path.replace("\\", "/")
        print(f"  Importing {bp_name} from {ir_file}...")
        r = client.import_from_ir(ir_path_ue)
        if r.get("status") == "ok":
            d = r.get("data", {})
            nodes = d.get("nodes_created", "?")
            conns = d.get("connections_wired", "?")
            compiled = d.get("compiled", "?")
            print(f"    OK: {nodes} nodes, {conns} connections, compiled={compiled}")
            import_results[bp_name] = True
        else:
            print(f"    FAILED: {r.get('message', 'unknown error')}")
            import_results[bp_name] = False

    # Print import summary
    passed = sum(1 for v in import_results.values() if v)
    print(f"\n  Import summary: {passed}/{len(import_results)} succeeded")
    for bp, ok in import_results.items():
        print(f"    {'PASS' if ok else 'FAIL'}: {bp}")

    if not all(import_results.values()):
        print("\n  WARNING: Some imports failed. Continuing with what we have...")

    # ── Step 6: Add Components ──
    step(6, "Add Components to Game BPs")

    component_configs = {
        "BP_ScorePickup": [
            {"type": "SphereCollision", "name": "OverlapSphere",
             "props": {"radius": 120.0, "generate_overlap_events": True}},
            {"type": "StaticMesh", "name": "CubeMesh",
             "props": {"mesh": "/Engine/BasicShapes/Cube.Cube",
                       "scale": {"x": 0.5, "y": 0.5, "z": 0.5}}},
        ],
        "BP_HealthPickup": [
            {"type": "SphereCollision", "name": "OverlapSphere",
             "props": {"radius": 120.0, "generate_overlap_events": True}},
            {"type": "StaticMesh", "name": "SphereMesh",
             "props": {"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                       "scale": {"x": 0.7, "y": 0.7, "z": 0.7}}},
        ],
        "BP_DamageZone": [
            {"type": "BoxCollision", "name": "OverlapBox",
             "props": {"extent": {"x": 200.0, "y": 200.0, "z": 100.0},
                       "generate_overlap_events": True}},
            {"type": "StaticMesh", "name": "PlaneMesh",
             "props": {"mesh": "/Engine/BasicShapes/Cube.Cube",
                       "scale": {"x": 4.0, "y": 4.0, "z": 0.1}}},
        ],
    }

    for bp_name, components in component_configs.items():
        if not import_results.get(bp_name, False):
            print(f"  Skipping {bp_name} (import failed)")
            continue
        for comp in components:
            r = client.add_component(bp_name, comp["type"], comp["name"],
                                     properties=comp["props"])
            status = r.get("status", "error")
            print(f"  {bp_name}/{comp['name']}: {status}")

    # ── Step 7: Create Materials ──
    step(7, "Create Materials")
    materials = {
        "MAT_Gold": {"color": {"r": 1.0, "g": 0.84, "b": 0.0}, "emissive": 2.0},
        "MAT_Red": {"color": {"r": 1.0, "g": 0.1, "b": 0.1}, "emissive": 3.0},
        "MAT_Green": {"color": {"r": 0.1, "g": 1.0, "b": 0.2}, "emissive": 2.0},
    }
    for mat_name, params in materials.items():
        r = client.create_simple_material(mat_name, params["color"], params["emissive"])
        print(f"  {mat_name}: {r.get('status', 'error')}")

    # ── Step 8: Apply Materials ──
    step(8, "Apply Materials to Meshes")
    material_assignments = {
        "BP_ScorePickup": {"component": "CubeMesh",
                           "material": "/Game/Arcwright/Materials/MAT_Gold"},
        "BP_HealthPickup": {"component": "SphereMesh",
                            "material": "/Game/Arcwright/Materials/MAT_Green"},
        "BP_DamageZone": {"component": "PlaneMesh",
                          "material": "/Game/Arcwright/Materials/MAT_Red"},
    }
    for bp_name, assign in material_assignments.items():
        if not import_results.get(bp_name, False):
            continue
        r = client.apply_material(bp_name, assign["component"], assign["material"])
        print(f"  {bp_name}/{assign['component']}: {r.get('status', 'error')}")

    # Recompile all BPs after component/material changes
    print("\n  Recompiling all game BPs...")
    for bp_name in GAME_BPS:
        if import_results.get(bp_name, False):
            client.compile_blueprint(bp_name)
    time.sleep(0.5)

    # ── Step 9: Spawn Actors ──
    step(9, "Spawn Game Actors")
    for spawn in SPAWN_LIST:
        bp = spawn["bp"]
        if not import_results.get(bp, False):
            print(f"  Skipping {spawn['label']} ({bp} import failed)")
            continue
        class_path = f"/Game/Arcwright/Generated/{bp}.{bp}"
        r = client.spawn_actor_at(
            actor_class=class_path,
            label=spawn["label"],
            location=spawn["loc"]
        )
        if r.get("status") == "ok":
            print(f"  Spawned: {spawn['label']} at ({spawn['loc']['x']}, {spawn['loc']['y']}, {spawn['loc']['z']})")
        else:
            print(f"  FAILED: {spawn['label']}: {r.get('message', '?')}")

    # ── Step 10: Save ──
    step(10, "Save All")
    r = client.save_all()
    print(f"  save_all: {r.get('status', 'error')}")

    # ── Summary ──
    print(f"\n{'='*60}")
    print("  ARENA REBUILD v2 COMPLETE")
    print(f"{'='*60}")
    print(f"  Blueprints imported: {passed}/{len(import_results)}")
    print(f"  Widget: WBP_ArenaHUD (Title + Score + Health + HealthBar)")
    print(f"  Actors spawned: {len(SPAWN_LIST)} total")
    print(f"    5 score pickups (gold cubes)")
    print(f"    3 health pickups (green spheres)")
    print(f"    3 damage zones (red platforms)")
    print(f"    1 arena manager (invisible)")
    print()
    print("  BP_ArenaManager has 3 custom events:")
    print("    - AddScore:   Score += 1, prints 'Score +1!'")
    print("    - TakeDamage: Health -= 5, prints '-5 HP!', checks GAME OVER")
    print("    - HealPlayer: Health += 25, prints '+25 Health!'")
    print()
    print("  NEXT STEPS:")
    print("    - Cross-BP communication needs manual wiring in editor")
    print("    - Each pickup/zone has self-contained PrintString on overlap")
    print("    - ArenaManager events work when called directly (right-click)")
    print("    - HUD widget visual binding is a follow-up task")

    client.close()


if __name__ == "__main__":
    main()
