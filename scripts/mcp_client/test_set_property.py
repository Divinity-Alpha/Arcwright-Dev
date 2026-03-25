"""Test set_component_property + make game BPs visible with meshes and lights."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError

results = []
def test(name, fn):
    try:
        r = fn()
        results.append(("PASS", name, r))
        print(f"  [PASS] {name}")
    except Exception as e:
        results.append(("FAIL", name, str(e)))
        print(f"  [FAIL] {name} -- {e}")

client = ArcwrightClient(timeout=60)

print("=" * 60)
print("set_component_property + Game BP Visibility Tests")
print("=" * 60)

# --- Phase 1: Test set_component_property ---
print("\n--- Phase 1: Test set_component_property ---")

test("create_test_bp", lambda: client.send_command("create_blueprint_from_dsl", {
    "ir_json": json.dumps({"name": "BP_PropTest", "type": "Actor", "nodes": [], "connections": [], "variables": []}),
    "name": "BP_PropTest"
}))

test("add_box", lambda: client.add_component("BP_PropTest", "BoxCollision", "TestBox", properties={
    "extent": {"x": 50, "y": 50, "z": 50}
}))

test("set_relative_location", lambda: client.set_component_property(
    "BP_PropTest", "TestBox", "relative_location", {"x": 100, "y": 0, "z": 50}
))

test("set_overlap_events", lambda: client.set_component_property(
    "BP_PropTest", "TestBox", "generate_overlap_events", True
))

test("set_visibility", lambda: client.set_component_property(
    "BP_PropTest", "TestBox", "visibility", False
))

test("add_light", lambda: client.add_component("BP_PropTest", "PointLight", "TestLight"))
test("set_intensity", lambda: client.set_component_property(
    "BP_PropTest", "TestLight", "intensity", 8000.0
))
test("set_light_color", lambda: client.set_component_property(
    "BP_PropTest", "TestLight", "light_color", {"r": 1.0, "g": 0.5, "b": 0.0}
))
test("set_attenuation", lambda: client.set_component_property(
    "BP_PropTest", "TestLight", "attenuation_radius", 1500.0
))

test("add_mesh", lambda: client.add_component("BP_PropTest", "StaticMesh", "TestMesh"))
test("set_static_mesh", lambda: client.set_component_property(
    "BP_PropTest", "TestMesh", "static_mesh", "/Engine/BasicShapes/Sphere.Sphere"
))
test("set_relative_scale", lambda: client.set_component_property(
    "BP_PropTest", "TestMesh", "relative_scale", {"x": 0.5, "y": 0.5, "z": 0.5}
))

client.delete_blueprint("BP_PropTest")
print("  Cleaned up BP_PropTest")

# --- Phase 2: Make game BPs visible ---
print("\n--- Phase 2: Make Game BPs Visible ---")

game_bps = [
    {
        "name": "BP_Pickup",
        "mesh": "/Engine/BasicShapes/Sphere.Sphere",
        "mesh_name": "VisualMesh",
        "scale": {"x": 0.5, "y": 0.5, "z": 0.5},
        "light_color": {"r": 1.0, "g": 0.8, "b": 0.0},
        "light_name": "PickupGlow",
        "intensity": 3000.0,
    },
    {
        "name": "BP_HazardZone",
        "mesh": "/Engine/BasicShapes/Cube.Cube",
        "mesh_name": "VisualMesh",
        "scale": {"x": 4, "y": 4, "z": 2},
        "light_color": {"r": 1.0, "g": 0.0, "b": 0.0},
        "light_name": "HazardGlow",
        "intensity": 5000.0,
    },
    {
        "name": "BP_VictoryZone",
        "mesh": "/Engine/BasicShapes/Cube.Cube",
        "mesh_name": "VisualMesh",
        "scale": {"x": 4, "y": 4, "z": 4},
        "light_color": {"r": 0.0, "g": 1.0, "b": 0.0},
        "light_name": "VictoryGlow",
        "intensity": 5000.0,
    },
]

for bp in game_bps:
    print(f"\n  --- {bp['name']} ---")

    try:
        existing = client.get_components(bp["name"])
        existing_names = [c["name"] for c in existing.get("data", {}).get("components", [])]
        print(f"  Existing components: {existing_names}")
    except BlueprintLLMError as e:
        print(f"  Warning: {e}")
        existing_names = []

    # Remove old mesh/light if present (to avoid duplicates on re-run)
    for comp_name in [bp["mesh_name"], bp["light_name"]]:
        if comp_name in existing_names:
            try:
                client.remove_component(bp["name"], comp_name)
                print(f"  Removed existing {comp_name}")
            except:
                pass

    # Add StaticMesh
    test(f"{bp['name']}_add_mesh", lambda bp=bp: client.add_component(
        bp["name"], "StaticMesh", bp["mesh_name"], properties={
            "static_mesh": bp["mesh"]
        }
    ))
    test(f"{bp['name']}_set_scale", lambda bp=bp: client.set_component_property(
        bp["name"], bp["mesh_name"], "relative_scale", bp["scale"]
    ))

    # Add PointLight
    test(f"{bp['name']}_add_light", lambda bp=bp: client.add_component(
        bp["name"], "PointLight", bp["light_name"], properties={
            "intensity": bp["intensity"],
            "light_color": bp["light_color"]
        }
    ))

# Verify
print("\n--- Phase 3: Verify ---")
for bp in game_bps:
    resp = client.get_components(bp["name"])
    comps = resp.get("data", {}).get("components", [])
    comp_names = [c["name"] for c in comps]
    print(f"  {bp['name']}: components={comp_names}")

# Re-spawn actors
print("\n--- Phase 4: Re-spawn actors ---")
for label in ["Pickup_1", "Pickup_2", "Pickup_3", "HazardZone", "VictoryZone"]:
    try:
        client.delete_actor(label)
    except:
        pass

actors = [
    {"class": "/Game/Arcwright/Generated/BP_Pickup",      "label": "Pickup_1",    "loc": {"x": 300,  "y": 0,    "z": 50}},
    {"class": "/Game/Arcwright/Generated/BP_Pickup",      "label": "Pickup_2",    "loc": {"x": -300, "y": 200,  "z": 50}},
    {"class": "/Game/Arcwright/Generated/BP_Pickup",      "label": "Pickup_3",    "loc": {"x": 0,    "y": -400, "z": 50}},
    {"class": "/Game/Arcwright/Generated/BP_HazardZone",  "label": "HazardZone",  "loc": {"x": 600,  "y": 0,    "z": 50}},
    {"class": "/Game/Arcwright/Generated/BP_VictoryZone", "label": "VictoryZone", "loc": {"x": -600, "y": 0,    "z": 50}},
]

for a in actors:
    resp = client.spawn_actor_at(actor_class=a["class"], location=a["loc"], label=a["label"])
    loc = resp.get("data", {}).get("location", {})
    print(f"  {a['label']}: ({loc.get('x',0):.0f}, {loc.get('y',0):.0f}, {loc.get('z',0):.0f})")

# PointLight actor near VictoryZone
print("\n--- Phase 5: PointLight actor near VictoryZone ---")
try:
    client.delete_actor("VictoryLight")
except:
    pass
test("spawn_victory_light", lambda: client.spawn_actor_at(
    actor_class="PointLight",
    location={"x": -200, "y": 3000, "z": 400},
    label="VictoryLight"
))

# Summary
print("\n" + "=" * 60)
passes = sum(1 for r in results if r[0] == "PASS")
fails = sum(1 for r in results if r[0] == "FAIL")
print(f"Results: {passes} PASS, {fails} FAIL out of {len(results)} tests")
if fails:
    print("\nFailed tests:")
    for r in results:
        if r[0] == "FAIL":
            print(f"  {r[1]}: {r[2]}")
print("=" * 60)

client.close()
