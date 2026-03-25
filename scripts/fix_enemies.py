"""Fix temple enemies: lower to floor, add patrol+chase AI with short detection radius."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.mcp_client.blueprint_client import ArcwrightClient

c = ArcwrightClient()
c.health_check()
print("Connected to UE")

ENEMIES = [
    ("Enemy_C1", {"x": 0, "y": 700}),
    ("Enemy_K1", {"x": -1500, "y": 900}),
    ("Enemy_K3", {"x": -1000, "y": 2900}),
]

# 1. Create AI Controller BP with patrol + chase (detection radius: 400)
try:
    c.delete_blueprint("BP_TempleEnemyAI")
    time.sleep(0.3)
except:
    pass

ir = {
    "metadata": {
        "name": "BP_TempleEnemyAI",
        "parent_class": "AIController",
    },
    "variables": [],
    "nodes": [
        # Patrol chain: BeginPlay -> Print -> MoveToA -> Delay -> MoveToB -> Delay -> loop
        {"id": "node_0", "dsl_type": "Event", "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay", "params": {}},
        {"id": "node_1", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString",
         "params": {"InString": "Temple Enemy Patrol"}},
        {"id": "node_2", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/AIModule.AIController:MoveToLocation",
         "params": {"bUsePathfinding": "false"}},
        {"id": "node_3", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.KismetSystemLibrary:Delay",
         "params": {"Duration": "2.0"}},
        {"id": "node_4", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/AIModule.AIController:MoveToLocation",
         "params": {"bUsePathfinding": "false"}},
        {"id": "node_5", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.KismetSystemLibrary:Delay",
         "params": {"Duration": "2.0"}},

        # Chase chain: Tick -> GetPlayerPawn -> GetDistanceTo -> Less(400) -> Branch -> Chase
        {"id": "node_6", "dsl_type": "Event", "ue_class": "UK2Node_Event", "ue_event": "ReceiveTick", "params": {}},
        {"id": "node_7", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.GameplayStatics:GetPlayerPawn", "params": {}},
        {"id": "node_8", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.Actor:GetDistanceTo", "params": {}},
        {"id": "node_9", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.KismetMathLibrary:Less_DoubleDouble",
         "params": {"B": "400.0"}},
        {"id": "node_10", "dsl_type": "Branch", "ue_class": "UK2Node_IfThenElse", "params": {}},
        {"id": "node_11", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString",
         "params": {"InString": "CHASING!"}},
        {"id": "node_12", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/Engine.Actor:GetActorLocation", "params": {}},
        {"id": "node_13", "dsl_type": "CallFunction", "ue_class": "UK2Node_CallFunction",
         "ue_function": "/Script/AIModule.AIController:MoveToLocation",
         "params": {"bUsePathfinding": "false"}},
    ],
    "connections": [
        # Patrol: BeginPlay -> Print -> MoveToA -> Delay -> MoveToB -> Delay -> loop
        {"src_node": "node_0", "src_pin": "then", "dst_node": "node_1", "dst_pin": "execute"},
        {"src_node": "node_1", "src_pin": "then", "dst_node": "node_2", "dst_pin": "execute"},
        {"src_node": "node_2", "src_pin": "then", "dst_node": "node_3", "dst_pin": "execute"},
        {"src_node": "node_3", "src_pin": "then", "dst_node": "node_4", "dst_pin": "execute"},
        {"src_node": "node_4", "src_pin": "then", "dst_node": "node_5", "dst_pin": "execute"},
        {"src_node": "node_5", "src_pin": "then", "dst_node": "node_2", "dst_pin": "execute"},

        # Chase: Tick -> Branch(GetDistanceTo < 400)
        {"src_node": "node_6", "src_pin": "then", "dst_node": "node_10", "dst_pin": "execute"},
        {"src_node": "node_7", "src_pin": "ReturnValue", "dst_node": "node_8", "dst_pin": "OtherActor"},
        {"src_node": "node_8", "src_pin": "ReturnValue", "dst_node": "node_9", "dst_pin": "A"},
        {"src_node": "node_9", "src_pin": "ReturnValue", "dst_node": "node_10", "dst_pin": "Condition"},
        # True -> Print "CHASING!" -> MoveToLocation(player pos)
        {"src_node": "node_10", "src_pin": "True", "dst_node": "node_11", "dst_pin": "execute"},
        {"src_node": "node_11", "src_pin": "then", "dst_node": "node_13", "dst_pin": "execute"},
        # Player pawn -> GetActorLocation -> MoveToLocation Dest
        {"src_node": "node_7", "src_pin": "ReturnValue", "dst_node": "node_12", "dst_pin": "T"},
        {"src_node": "node_12", "src_pin": "ReturnValue", "dst_node": "node_13", "dst_pin": "Dest"},
    ],
}

ir_path = os.path.abspath("test_ir/bp_temple_enemy_ai.blueprint.json")
with open(ir_path, "w") as f:
    json.dump(ir, f, indent=2)
print(f"Wrote IR: {ir_path}")

r = c.import_from_ir(ir_path)
print(f"Import BP_TempleEnemyAI: {r['status']}")
if r["status"] != "ok":
    print(f"  Error: {r.get('message', '?')}")

time.sleep(1)

# 2. Wire BP_TempleEnemy to use this AI controller
r = c.send_command("set_class_defaults", {
    "blueprint": "BP_TempleEnemy",
    "properties": {
        "ai_controller_class": "BP_TempleEnemyAI",
        "auto_possess_ai": "PlacedInWorldOrSpawned",
    }
})
print(f"Set class defaults: {r['status']}")

# 3. Re-spawn enemies at z=85
time.sleep(0.5)
for label, loc in ENEMIES:
    c.send_command("delete_actor", {"label": label})
    time.sleep(0.05)

time.sleep(0.5)
for label, loc in ENEMIES:
    c.send_command("spawn_actor_at", {
        "class": "/Game/Arcwright/Generated/BP_TempleEnemy.BP_TempleEnemy",
        "label": label,
        "location": {"x": loc["x"], "y": loc["y"], "z": 85},
    })
    time.sleep(0.05)
    # Re-apply enemy material
    c.send_command("set_actor_material", {
        "actor_label": label,
        "material_path": "/Game/Arcwright/Materials/MAT_EnemyDarkRed",
    })

print("Re-spawned 3 enemies at z=85 with AI controller")

# 4. Re-apply concrete to all walls
actors = c.send_command("get_actors", {}).get("data", {}).get("actors", [])
walls = [a for a in actors if "Wall" in a.get("label", "")]
for w in walls:
    c.send_command("set_actor_material", {
        "actor_label": w["label"],
        "material_path": "/Game/Arcwright/Materials/MAT_Concrete",
    })
print(f"Re-applied concrete to {len(walls)} walls")

# 5. Save
c.send_command("save_all", {})
print("Saved")

# 6. Screenshot
time.sleep(1)
c.send_command("set_viewport_camera", {
    "location": {"x": 200, "y": 700, "z": 150},
    "rotation": {"pitch": -10, "yaw": 180, "roll": 0},
})
time.sleep(1)
r = c.send_command("take_screenshot", {
    "output_path": "C:/Arcwright/exports/enemy_floor_ai.png"
})
print(f"Screenshot: {r.get('data', {}).get('file_path', '?')}")

c.close()
