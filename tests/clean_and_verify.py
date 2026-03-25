"""Clean all duplicates, verify clean state."""
import sys
sys.path.insert(0, "C:/BlueprintLLM")
from scripts.state_manager import StateManager

sm = StateManager(project_dir="C:/Projects/BoreandStroke")
arc = sm.arc

print("=" * 60)
print("PHASE 1: Inventory before cleanup")
print("=" * 60)

# Count all duplicates
dupes = {}
for actor_type in ["DirectionalLight", "SkyLight", "PointLight"]:
    r = arc.cmd("find_actors", class_filter=actor_type)
    actors = r.get("data", {}).get("actors", [])
    dupes[actor_type] = [a.get("label") for a in actors]
    print(f"  {actor_type}: {len(actors)}")

managers = ["HUDManager", "TimeManager", "EconomyManager", "HeatManager",
            "ReputationManager", "QuestManager"]
r = arc.cmd("find_actors")
all_actors = r.get("data", {}).get("actors", [])

for mgr in managers:
    matches = [a for a in all_actors if a.get("label", "").startswith(mgr)]
    dupes[mgr] = [a.get("label") for a in matches]
    if len(matches) > 1:
        print(f"  {mgr}: {len(matches)} (DUPLICATE)")
    else:
        print(f"  {mgr}: {len(matches)}")

print(f"\n  Total actors: {len(all_actors)}")

print("\n" + "=" * 60)
print("PHASE 2: Clean duplicates")
print("=" * 60)

cleaned = 0

# Clean duplicate lights (keep first of each)
for light_type in ["DirectionalLight", "SkyLight"]:
    labels = dupes[light_type]
    if len(labels) > 1:
        for label in labels[1:]:
            arc.cmd("delete_actor", label=label)
            cleaned += 1
            print(f"  Deleted duplicate {light_type}: {label}")

# Clean duplicate managers (keep first of each)
for mgr in managers:
    labels = dupes[mgr]
    if len(labels) > 1:
        for label in labels[1:]:
            arc.cmd("delete_actor", label=label)
            cleaned += 1
            print(f"  Deleted duplicate {mgr}: {label}")

# Clean test artifacts
test_bps = ["BP_StressTest50", "BP_ParamTest", "BP_EventParamTest", "BP_Receiver", "BP_Sender"]
for label in ["StressTest50", "ParamTest", "EventParamTest", "Receiver1", "Sender1"]:
    r = arc.cmd("find_actors", name_filter=label)
    for a in r.get("data", {}).get("actors", []):
        arc.cmd("delete_actor", label=a.get("label"))
        cleaned += 1
        print(f"  Deleted test actor: {a.get('label')}")

arc.cmd("save_all")
print(f"\n  Cleaned {cleaned} actors")

print("\n" + "=" * 60)
print("PHASE 3: Verify clean state")
print("=" * 60)

for light_type in ["DirectionalLight", "SkyLight"]:
    r = arc.cmd("find_actors", class_filter=light_type)
    count = len(r.get("data", {}).get("actors", []))
    print(f"  {light_type}: {count} {'OK' if count == 1 else 'ISSUE'}")

for mgr in managers:
    r = arc.cmd("find_actors", name_filter=mgr)
    matches = [a for a in r.get("data", {}).get("actors", []) if a.get("label", "").startswith(mgr)]
    count = len(matches)
    expected = 1 if mgr != "QuestManager" else 1
    print(f"  {mgr}: {count} {'OK' if count <= 1 else 'DUPLICATE'}")

# Station count
r = arc.cmd("find_actors", name_filter="Station_")
stations = [a for a in r.get("data", {}).get("actors", [])
            if a.get("class") == "BP_StationBase_C"]
print(f"  BP_StationBase stations: {len(stations)}")

# Blueprint compile check
r = arc.cmd("verify_all_blueprints")
d = r.get("data", {})
print(f"  Blueprints: {d.get('pass')}/{d.get('total')} compile")

r = arc.cmd("get_level_info")
print(f"  Total actors: {r.get('data',{}).get('actor_count')}")

# Map check
r = arc.cmd("run_map_check")
d = r.get("data", {})
print(f"  Map check: {d.get('error_count',0)} errors, {d.get('warning_count',0)} warnings")

print("\n" + "=" * 60)
print("CLEANUP COMPLETE")
print("=" * 60)
