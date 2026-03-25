"""
Step 2: Visual layer for B&S Original — materials, lighting, environment polish.
Does NOT touch C++ game logic. Only visual elements via Arcwright.
Uses StateManager + post_phase_check.
"""
import sys, time, json, os
sys.path.insert(0, "C:/Arcwright")
from scripts.state_manager import StateManager
from scripts.check_and_confirm import CheckAndConfirm

sm = StateManager(project_dir="C:/Projects/BoreAndStroke_Original")
arc = sm.arc
cc = CheckAndConfirm()

print("=" * 70)
print("B&S ORIGINAL — VISUAL LAYER BUILD")
print("=" * 70)

# Phase 0: Diagnose current state
print("\n--- Phase 0: Current State ---")
sm.report()
sm.clean_duplicate_lights()
cc.post_phase_check("Pre-Build Cleanup")

# Phase 1: Materials — dark industrial theme from GDD
print("\n--- Phase 1: Materials ---")

materials = [
    ("MAT_ShopFloor", {"r": 0.15, "g": 0.14, "b": 0.13}),      # Dark concrete
    ("MAT_ShopWall", {"r": 0.22, "g": 0.21, "b": 0.20}),        # Grey concrete walls
    ("MAT_ShopCeiling", {"r": 0.18, "g": 0.17, "b": 0.16}),     # Dark ceiling
    ("MAT_Workbench", {"r": 0.35, "g": 0.25, "b": 0.15}),       # Worn wood workbench
    ("MAT_Metal", {"r": 0.5, "g": 0.5, "b": 0.52}),             # Brushed metal
    ("MAT_Safety", {"r": 0.8, "g": 0.6, "b": 0.0}),             # Safety yellow stripe
]

for name, color in materials:
    sm.safe_create_material(name, color)

cc.post_phase_check("Materials")

# Phase 2: Apply materials to existing floor/wall geometry
print("\n--- Phase 2: Apply Materials to Level Geometry ---")

r = arc.cmd("find_actors", class_filter="StaticMeshActor")
mesh_actors = r.get("data", {}).get("actors", [])
print(f"  StaticMeshActors in level: {len(mesh_actors)}")
for a in mesh_actors:
    label = a.get("label", "")
    loc = a.get("location", {})
    z = loc.get("z", 0)
    # Heuristic: floor actors are at z~0, walls are taller, ceiling is highest
    if "floor" in label.lower() or (z < 5 and abs(loc.get("x", 0)) < 50):
        arc.cmd("set_actor_material", actor_label=label, material_path="/Game/Arcwright/Materials/MAT_ShopFloor")
        print(f"    {label}: floor material")
    elif "wall" in label.lower():
        arc.cmd("set_actor_material", actor_label=label, material_path="/Game/Arcwright/Materials/MAT_ShopWall")
        print(f"    {label}: wall material")
    elif "ceil" in label.lower():
        arc.cmd("set_actor_material", actor_label=label, material_path="/Game/Arcwright/Materials/MAT_ShopCeiling")
        print(f"    {label}: ceiling material")

# Apply workbench material to station meshes
r = arc.cmd("find_actors", name_filter="Station")
stations = r.get("data", {}).get("actors", [])
for s in stations:
    label = s.get("label", "")
    if "Station" in s.get("class", ""):
        arc.cmd("set_actor_material", actor_label=label, material_path="/Game/Arcwright/Materials/MAT_Workbench")
        print(f"    {label}: workbench material")

cc.post_phase_check("Material Application")

# Phase 3: Lighting — industrial fluorescent feel
print("\n--- Phase 3: Lighting ---")

# Check existing lights
r = arc.cmd("find_actors", class_filter="PointLight")
existing_lights = r.get("data", {}).get("actors", [])
print(f"  Existing PointLights: {len(existing_lights)}")

# If no overhead lights exist, add per-station task lighting
if len(existing_lights) < 5:
    for s in stations:
        label = s.get("label", "")
        loc = s.get("location", {})
        if "Station" in s.get("class", ""):
            light_label = f"Light_{label}"
            sm.safe_spawn_actor(light_label,
                x=loc.get("x", 0), y=loc.get("y", 0), z=loc.get("z", 0) + 250,
                **{"class": "PointLight"})
    print("  Added per-station overhead lights")

    # Set light properties (warm industrial)
    r = arc.cmd("find_actors", class_filter="PointLight")
    for light in r.get("data", {}).get("actors", []):
        arc.cmd("set_component_property",
                actor_label=light.get("label"),
                component_name="PointLightComponent0",
                property="intensity", value="8000")
        arc.cmd("set_component_property",
                actor_label=light.get("label"),
                component_name="PointLightComponent0",
                property="light_color", value={"r": 1.0, "g": 0.9, "b": 0.75})
        arc.cmd("set_component_property",
                actor_label=light.get("label"),
                component_name="PointLightComponent0",
                property="attenuation_radius", value="800")
else:
    print("  Existing lights sufficient, skipping")

cc.post_phase_check("Lighting")

# Phase 4: Save
print("\n--- Phase 4: Save ---")
arc.cmd("save_all")
print("  Saved")

# Phase 5: PIE + QA Tour
print("\n--- Phase 5: PIE + QA Tour ---")

arc.cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = arc.cmd("is_playing")
    if r.get("data", {}).get("playing"):
        started = True
        break

if started:
    print("  PIE running")
    time.sleep(4)

    # Check subsystems initialized
    r = arc.cmd("get_output_log", lines=200)
    lines = r.get("data", {}).get("lines", [])
    init_msgs = [str(l) for l in lines if "Initialized" in str(l)]
    print(f"  Subsystems initialized: {len(init_msgs)}")
    data_msg = [str(l) for l in lines if "BSData" in str(l)]
    if data_msg:
        print(f"  Data: {data_msg[0][:120]}")

    # QA Tour
    os.makedirs("C:/Arcwright/screenshots", exist_ok=True)
    print("\n  QA TOUR:")

    # Start from player spawn
    arc.cmd("get_player_view", filename="C:/Arcwright/screenshots/bs_spawn.png")
    print("    Spawn point captured")

    # Visit each station
    for s in stations:
        label = s.get("label", "")
        if "Station" in s.get("class", ""):
            arc.cmd("teleport_to_actor", actor=label, distance=200)
            time.sleep(1.5)
            arc.cmd("get_player_view", filename=f"C:/Arcwright/screenshots/bs_{label}.png")
            print(f"    {label}: captured")

    # Overview from center high
    arc.cmd("teleport_player", x=400, y=200, z=400, pitch=-30, yaw=0)
    time.sleep(1)
    arc.cmd("get_player_view", filename="C:/Arcwright/screenshots/bs_overview.png")
    print("    Overview captured")

    # Final summary
    r = arc.cmd("get_output_log", lines=100)
    bp_msgs = [str(l) for l in r.get("data", {}).get("lines", []) if "BlueprintUserMessages" in str(l)]
    errors = [str(l) for l in r.get("data", {}).get("lines", [])
              if "Error" in str(l) and "PIE" not in str(l) and "google" not in str(l).lower()]

    print(f"\n  Summary:")
    print(f"    Blueprint messages: {len(bp_msgs)}")
    print(f"    Errors: {len(errors)}")
    for e in errors[:3]:
        print(f"      {e[:120]}")

    arc.cmd("stop_play")
else:
    print("  PIE did not start!")

print("\n" + "=" * 70)
print("VISUAL LAYER BUILD COMPLETE")
print("=" * 70)
sm.report()
