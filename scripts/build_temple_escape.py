#!/usr/bin/env python3
"""Temple Escape — Full build script for the demo puzzle game.
Executed phase by phase via --phase argument."""

import sys, json, time, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.mcp_client.blueprint_client import ArcwrightClient


def save_all_verified(c):
    """Save all packages and verify external actors were saved."""
    try:
        r = c.send_command('save_all', {})
        ext_saved = r.get('data', {}).get('external_actors_saved', 0)
        saved = r.get('data', {}).get('saved', False)
        return saved, ext_saved
    except Exception as e:
        print(f"  WARN: save_all failed: {e}")
        return False, 0


def graceful_shutdown(c):
    """Shut down editor gracefully — saves everything then exits cleanly."""
    try:
        r = c.send_command('quit_editor', {})
        ext_saved = r.get('data', {}).get('external_actors_saved', 0)
        print(f"  quit_editor: saved ({ext_saved} external actors), shutting down...")
        return True
    except Exception as e:
        print(f"  quit_editor failed: {e}")
        print(f"  Falling back to taskkill...")
        os.system('taskkill /F /IM "UnrealEditor.exe" 2>NUL')
        return False


def phase0_scene_lighting(c):
    """Set up scene lighting FIRST — prevents dark levels (Lesson #42)."""
    print("=== PHASE 0: SCENE LIGHTING ===")
    r = c.send_command('setup_scene_lighting', {
        'preset': 'indoor_dark',
        'directional_intensity': 2.0,
        'sky_intensity': 0.5,
        'directional_pitch': -45.0
    })
    if r.get('status') == 'ok':
        count = r['data'].get('actors_created', 0)
        print(f"  Scene lighting created: {count} actors ({r['data'].get('preset', '')} preset)")
        for a in r['data'].get('actors', []):
            print(f"    - {a.get('label', '?')}")
    else:
        print(f"  WARN: setup_scene_lighting failed: {r.get('message', '?')}")
        print("  Falling back to manual light spawning...")
        # Fallback: spawn manually
        c.send_command('spawn_actor_at', {
            'class': 'DirectionalLight', 'label': 'SceneDirectionalLight',
            'location': {'x': 0, 'y': 0, 'z': 1000},
            'rotation': {'pitch': -45, 'yaw': -30, 'roll': 0}
        })
        c.send_command('spawn_actor_at', {
            'class': 'SkyLight', 'label': 'SceneSkyLight',
            'location': {'x': 0, 'y': 0, 'z': 1000}
        })
        print("  Fallback lights spawned")


def phase0b_floor_and_fps(c):
    """Spawn ground floor, create FPS controller + GameMode (Lessons #43-44)."""
    print("=== PHASE 0b: FLOOR + FPS CONTROLS + GAMEMODE ===")

    # 1. Floor
    r = c.send_command('spawn_actor_at', {
        'class': 'StaticMeshActor',
        'label': 'TempleFloor',
        'location': {'x': 0, 'y': 2000, 'z': 0},
        'scale': {'x': 100, 'y': 100, 'z': 1},
        'mesh': '/Engine/BasicShapes/Plane.Plane'
    })
    print(f"  Floor: {r.get('status', 'error')}")

    # Apply stone material to floor
    c.send_command('create_simple_material', {
        'name': 'MAT_StoneFloor',
        'color': {'r': 0.35, 'g': 0.32, 'b': 0.28}
    })
    c.send_command('spawn_actor_at', {
        'class': 'StaticMeshActor',
        'label': 'TempleFloor',
        'location': {'x': 0, 'y': 2000, 'z': 0},
        'scale': {'x': 100, 'y': 100, 'z': 1},
        'mesh': '/Engine/BasicShapes/Plane.Plane',
        'material': '/Game/Arcwright/Materials/MAT_StoneFloor'
    })

    # 2. FPS Player Controller
    r = c.send_command('import_from_ir', {
        'file_path': 'C:/Arcwright/test_ir/bp_fps_player_controller.blueprint.json'
    })
    print(f"  FPS Controller: {r.get('status', 'error')} ({r.get('data', {}).get('nodes_created', 0)} nodes)")

    # Set CDO properties for mouse capture (Lesson #46)
    r = c.send_command('set_class_defaults', {
        'blueprint': 'BP_FPSPlayerController',
        'properties': {
            'bShowMouseCursor': 'false',
            'DefaultMouseCursor': 'None',
            'bEnableClickEvents': 'false',
            'bEnableMouseOverEvents': 'false'
        }
    })
    print(f"  CDO mouse capture: {r.get('data', {}).get('properties_set', [])}")

    # 3. GameMode
    r = c.send_command('import_from_ir', {
        'file_path': 'C:/Arcwright/test_ir/bp_temple_game_mode.blueprint.json'
    })
    print(f"  GameMode: {r.get('status', 'error')} ({r.get('data', {}).get('nodes_created', 0)} nodes)")

    # Set GameMode class defaults
    r = c.send_command('set_class_defaults', {
        'blueprint': 'BP_TempleGameMode',
        'properties': {
            'player_controller_class': 'BP_FPSPlayerController'
        }
    })
    print(f"  Set PlayerControllerClass: {r.get('status', 'error')}")

    # Set world GameMode
    r = c.set_game_mode('BP_TempleGameMode')
    print(f"  Set World GameMode: {r.get('status', 'error')}")


def phase1_clean_and_hud(c):
    """Clean existing assets and create WBP_TempleHUD."""
    print("=== PHASE 1a: CLEANING EXISTING ASSETS ===")

    # Delete temple Blueprints
    temple_bps = [
        'BP_TempleKey', 'BP_TempleDoor', 'BP_PressurePlate', 'BP_TempleLever',
        'BP_HazardZone', 'BP_HealthPickup', 'BP_TempleEnemy', 'BP_ExitPortal',
        'BP_Torch', 'BP_TempleGameManager', 'BP_TempleEnemyAIController'
    ]
    for name in temple_bps:
        r = c.send_command('delete_blueprint', {'name': name})
        if r.get('status') == 'ok':
            print(f"  Deleted: {name}")

    # Delete old arena assets
    for name in ['BP_ScorePickup', 'BP_DamageZone', 'BP_ArenaManager',
                 'BP_SimpleEnemy', 'BP_EnemyAIController']:
        c.send_command('delete_blueprint', {'name': name})

    # Delete widgets
    for wb in ['WBP_TempleHUD', 'WBP_ArenaHUD', 'WBP_GameHUD']:
        r = c.send_command('delete_blueprint', {'name': wb})
        if r.get('status') == 'ok':
            print(f"  Deleted widget: {wb}")

    # Clean actors from level (keep infrastructure)
    keep_labels = {
        'Floor', 'Sky', 'SkyAtmosphere', 'SkyLight', 'DirectionalLight',
        'AtmosphericFog', 'ExponentialHeightFog', 'VolumetricCloud',
        'WorldDataLayers', 'WorldPartitionMiniMap', 'LevelInstance',
        'NavMeshBoundsVolume'
    }
    r = c.send_command('get_actors', {})
    if r.get('status') == 'ok':
        actors = r['data'].get('actors', [])
        deleted = 0
        for actor in actors:
            label = actor.get('label', '')
            cls = actor.get('class', '')
            if label and label not in keep_labels and 'Light' not in cls:
                r2 = c.send_command('delete_actor', {'label': label})
                if r2.get('status') == 'ok':
                    deleted += 1
        print(f"  Deleted {deleted} actors from level")

    # Also remove PostProcessVolume if present
    c.send_command('delete_actor', {'label': 'PostProcessVolume'})
    c.send_command('delete_actor', {'label': 'PP_TempleAtmosphere'})

    print("  Scene cleaned.\n")

    # Phase 1b: Create WBP_TempleHUD
    print("=== PHASE 1b: CREATE WBP_TempleHUD ===")
    r = c.send_command('create_widget_blueprint', {'name': 'WBP_TempleHUD'})
    print(f"  Create WBP: {r.get('status')}")

    # Root CanvasPanel
    c.send_command('add_widget_child', {
        'widget_blueprint': 'WBP_TempleHUD',
        'widget_type': 'CanvasPanel', 'widget_name': 'RootPanel'
    })

    # KeysLabel - gold, top-left
    c.send_command('add_widget_child', {
        'widget_blueprint': 'WBP_TempleHUD', 'parent_widget': 'RootPanel',
        'widget_type': 'TextBlock', 'widget_name': 'KeysLabel'
    })
    for prop, val in [
        ('text', 'Keys: 0/3'),
        ('font_size', '24'),
        ('color', json.dumps({'r': 1.0, 'g': 0.8, 'b': 0.0, 'a': 1.0})),
        ('position', json.dumps({'x': 40, 'y': 30}))
    ]:
        c.send_command('set_widget_property', {
            'widget_blueprint': 'WBP_TempleHUD', 'widget_name': 'KeysLabel',
            'property': prop, 'value': val
        })
    print("  KeysLabel: OK")

    # HealthBar - green progress bar, top-center
    c.send_command('add_widget_child', {
        'widget_blueprint': 'WBP_TempleHUD', 'parent_widget': 'RootPanel',
        'widget_type': 'ProgressBar', 'widget_name': 'HealthBar'
    })
    for prop, val in [
        ('percent', '1.0'),
        ('fill_color', json.dumps({'r': 0.1, 'g': 1.0, 'b': 0.2, 'a': 1.0})),
        ('position', json.dumps({'x': 500, 'y': 25})),
        ('size', json.dumps({'x': 300, 'y': 25}))
    ]:
        c.send_command('set_widget_property', {
            'widget_blueprint': 'WBP_TempleHUD', 'widget_name': 'HealthBar',
            'property': prop, 'value': val
        })
    print("  HealthBar: OK")

    # HealthText - white, above bar
    c.send_command('add_widget_child', {
        'widget_blueprint': 'WBP_TempleHUD', 'parent_widget': 'RootPanel',
        'widget_type': 'TextBlock', 'widget_name': 'HealthText'
    })
    for prop, val in [
        ('text', 'Health: 100'),
        ('font_size', '16'),
        ('color', json.dumps({'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0})),
        ('position', json.dumps({'x': 580, 'y': 5}))
    ]:
        c.send_command('set_widget_property', {
            'widget_blueprint': 'WBP_TempleHUD', 'widget_name': 'HealthText',
            'property': prop, 'value': val
        })
    print("  HealthText: OK")

    # MessageText - yellow, bottom-center
    c.send_command('add_widget_child', {
        'widget_blueprint': 'WBP_TempleHUD', 'parent_widget': 'RootPanel',
        'widget_type': 'TextBlock', 'widget_name': 'MessageText'
    })
    for prop, val in [
        ('text', ''),
        ('font_size', '28'),
        ('color', json.dumps({'r': 1.0, 'g': 0.9, 'b': 0.0, 'a': 1.0})),
        ('position', json.dumps({'x': 400, 'y': 620}))
    ]:
        c.send_command('set_widget_property', {
            'widget_blueprint': 'WBP_TempleHUD', 'widget_name': 'MessageText',
            'property': prop, 'value': val
        })
    print("  MessageText: OK")

    # TitleText - dim white, bottom-right
    c.send_command('add_widget_child', {
        'widget_blueprint': 'WBP_TempleHUD', 'parent_widget': 'RootPanel',
        'widget_type': 'TextBlock', 'widget_name': 'TitleText'
    })
    for prop, val in [
        ('text', 'TEMPLE ESCAPE'),
        ('font_size', '14'),
        ('color', json.dumps({'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 0.5})),
        ('position', json.dumps({'x': 1050, 'y': 690}))
    ]:
        c.send_command('set_widget_property', {
            'widget_blueprint': 'WBP_TempleHUD', 'widget_name': 'TitleText',
            'property': prop, 'value': val
        })
    print("  TitleText: OK")

    # Verify
    r = c.send_command('get_widget_tree', {'widget_blueprint': 'WBP_TempleHUD'})
    if r.get('status') == 'ok':
        widgets = r['data']
        count = str(widgets).count("'name':")
        print(f"  Widget tree verified: {count} widgets")

    print("\n=== PHASE 1 COMPLETE ===")


def phase2_create_blueprints(c):
    """Create all 10 Blueprints from DSL via import_from_ir."""
    print("=== PHASE 2: CREATE BLUEPRINTS FROM DSL ===")

    # Write IR files for each blueprint
    blueprints = {}

    # BP_TempleKey - collectible key
    blueprints['BP_TempleKey'] = {
        "metadata": {"name": "BP_TempleKey", "parent_class": "Actor"},
        "variables": [],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Key Collected!"}},
            {"id": "n3", "dsl_type": "DestroyActor", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.Actor:K2_DestroyActor"}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"},
            {"src_node": "n2", "src_pin": "Then", "dst_node": "n3", "dst_pin": "Execute"}
        ]
    }

    # BP_TempleDoor - door that prints message on overlap
    blueprints['BP_TempleDoor'] = {
        "metadata": {"name": "BP_TempleDoor", "parent_class": "Actor"},
        "variables": [
            {"name": "IsOpen", "type": "Bool", "default": "false"},
            {"name": "RequiredKeys", "type": "Int", "default": "0"}
        ],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Door requires keys..."}}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"}
        ]
    }

    # BP_PressurePlate - toggles IsPressed on overlap
    blueprints['BP_PressurePlate'] = {
        "metadata": {"name": "BP_PressurePlate", "parent_class": "Actor"},
        "variables": [
            {"name": "IsPressed", "type": "Bool", "default": "false"}
        ],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap"},
            {"id": "n2", "dsl_type": "VariableSet", "ue_class": "UK2Node_VariableSet", "params": {"Variable": "IsPressed"}, "data_literals": {"IsPressed": "true"}},
            {"id": "n3", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Plate activated!"}},
            {"id": "n4", "dsl_type": "Event_ActorEndOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorEndOverlap"},
            {"id": "n5", "dsl_type": "VariableSet", "ue_class": "UK2Node_VariableSet", "params": {"Variable": "IsPressed"}, "data_literals": {"IsPressed": "false"}},
            {"id": "n6", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Plate deactivated"}}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"},
            {"src_node": "n2", "src_pin": "Then", "dst_node": "n3", "dst_pin": "Execute"},
            {"src_node": "n4", "src_pin": "Then", "dst_node": "n5", "dst_pin": "Execute"},
            {"src_node": "n5", "src_pin": "Then", "dst_node": "n6", "dst_pin": "Execute"}
        ]
    }

    # BP_TempleLever - FlipFlop toggle
    blueprints['BP_TempleLever'] = {
        "metadata": {"name": "BP_TempleLever", "parent_class": "Actor"},
        "variables": [
            {"name": "IsActive", "type": "Bool", "default": "false"}
        ],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap"},
            {"id": "n2", "dsl_type": "FlipFlop", "ue_class": "UK2Node_MacroInstance", "ue_macro": "FlipFlop"},
            {"id": "n3", "dsl_type": "VariableSet", "ue_class": "UK2Node_VariableSet", "params": {"Variable": "IsActive"}, "data_literals": {"IsActive": "true"}},
            {"id": "n4", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Lever ON"}},
            {"id": "n5", "dsl_type": "VariableSet", "ue_class": "UK2Node_VariableSet", "params": {"Variable": "IsActive"}, "data_literals": {"IsActive": "false"}},
            {"id": "n6", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Lever OFF"}}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"},
            {"src_node": "n2", "src_pin": "A", "dst_node": "n3", "dst_pin": "Execute"},
            {"src_node": "n3", "src_pin": "Then", "dst_node": "n4", "dst_pin": "Execute"},
            {"src_node": "n2", "src_pin": "B", "dst_node": "n5", "dst_pin": "Execute"},
            {"src_node": "n5", "src_pin": "Then", "dst_node": "n6", "dst_pin": "Execute"}
        ]
    }

    # BP_HazardZone - damage on overlap
    blueprints['BP_HazardZone'] = {
        "metadata": {"name": "BP_HazardZone", "parent_class": "Actor"},
        "variables": [],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "DANGER! Taking damage!"}},
            {"id": "n3", "dsl_type": "DestroyActor", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.Actor:K2_DestroyActor"}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"},
            {"src_node": "n2", "src_pin": "Then", "dst_node": "n3", "dst_pin": "Execute"}
        ]
    }

    # BP_HealthPickup - heal on overlap
    blueprints['BP_HealthPickup'] = {
        "metadata": {"name": "BP_HealthPickup", "parent_class": "Actor"},
        "variables": [],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Health restored!"}},
            {"id": "n3", "dsl_type": "DestroyActor", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.Actor:K2_DestroyActor"}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"},
            {"src_node": "n2", "src_pin": "Then", "dst_node": "n3", "dst_pin": "Execute"}
        ]
    }

    # BP_TempleEnemy - Pawn parent for AI
    blueprints['BP_TempleEnemy'] = {
        "metadata": {"name": "BP_TempleEnemy", "parent_class": "Pawn"},
        "variables": [],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_BeginPlay", "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Enemy spawned!"}}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"}
        ]
    }

    # BP_ExitPortal - victory trigger
    blueprints['BP_ExitPortal'] = {
        "metadata": {"name": "BP_ExitPortal", "parent_class": "Actor"},
        "variables": [],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "TEMPLE ESCAPED! You Win!"}}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"}
        ]
    }

    # BP_Torch - decorative, minimal logic
    blueprints['BP_Torch'] = {
        "metadata": {"name": "BP_Torch", "parent_class": "Actor"},
        "variables": [],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_BeginPlay", "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": ""}}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"}
        ]
    }

    # BP_TempleGameManager - creates HUD on BeginPlay
    blueprints['BP_TempleGameManager'] = {
        "metadata": {"name": "BP_TempleGameManager", "parent_class": "Actor"},
        "variables": [
            {"name": "KeysCollected", "type": "Int", "default": "0"},
            {"name": "Health", "type": "Float", "default": "100.0"},
            {"name": "GameWon", "type": "Bool", "default": "false"}
        ],
        "nodes": [
            {"id": "n1", "dsl_type": "Event_BeginPlay", "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay"},
            {"id": "n2", "dsl_type": "PrintString", "ue_class": "UK2Node_CallFunction", "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Find 3 keys to escape the temple..."}}
        ],
        "connections": [
            {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute"}
        ]
    }

    # Write IR files and import each
    ir_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test_ir')

    results = []
    for bp_name, ir_data in blueprints.items():
        ir_path = os.path.join(ir_dir, f"temple_{bp_name}.blueprint.json")
        with open(ir_path, 'w') as f:
            json.dump(ir_data, f, indent=2)

        # Import via TCP
        r = c.send_command('import_from_ir', {'path': ir_path.replace('\\', '/')})
        status = r.get('status', 'error')
        msg = r.get('data', {}).get('blueprint_name', '') if status == 'ok' else r.get('message', 'unknown error')
        results.append((bp_name, status, msg))

        # Check compile status
        if status == 'ok':
            info = c.send_command('get_blueprint_info', {'name': bp_name})
            compiled = info.get('data', {}).get('compiled', False) if info.get('status') == 'ok' else False
            nodes = info.get('data', {}).get('node_count', 0) if info.get('status') == 'ok' else 0
            print(f"  {bp_name}: {status} | {nodes} nodes | compiled={compiled}")
        else:
            print(f"  {bp_name}: {status} | {msg}")

    pass_count = sum(1 for _, s, _ in results if s == 'ok')
    print(f"\n  {pass_count}/{len(results)} Blueprints created successfully")
    print("\n=== PHASE 2 COMPLETE ===")


def phase3_add_components(c):
    """Add components (collision, mesh, lights) to each Blueprint."""
    print("=== PHASE 3: ADD COMPONENTS ===")

    component_specs = {
        'BP_TempleKey': [
            {'type': 'BoxCollision', 'name': 'KeyCollision', 'properties': {
                'extent': json.dumps({'x': 40, 'y': 40, 'z': 40}),
                'generate_overlap_events': 'true'
            }},
            {'type': 'StaticMesh', 'name': 'KeyMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cube.Cube',
                'scale': json.dumps({'x': 0.3, 'y': 0.15, 'z': 0.5})
            }},
            {'type': 'PointLight', 'name': 'KeyGlow', 'properties': {
                'intensity': '5000',
                'light_color': json.dumps({'r': 255, 'g': 200, 'b': 0}),
                'attenuation_radius': '400'
            }}
        ],
        'BP_TempleDoor': [
            {'type': 'BoxCollision', 'name': 'DoorCollision', 'properties': {
                'extent': json.dumps({'x': 150, 'y': 20, 'z': 200}),
                'generate_overlap_events': 'true'
            }},
            {'type': 'StaticMesh', 'name': 'DoorMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cube.Cube',
                'scale': json.dumps({'x': 3.0, 'y': 0.4, 'z': 4.0})
            }}
        ],
        'BP_PressurePlate': [
            {'type': 'BoxCollision', 'name': 'PlateCollision', 'properties': {
                'extent': json.dumps({'x': 100, 'y': 100, 'z': 10}),
                'generate_overlap_events': 'true'
            }},
            {'type': 'StaticMesh', 'name': 'PlateMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cube.Cube',
                'scale': json.dumps({'x': 2.0, 'y': 2.0, 'z': 0.2})
            }}
        ],
        'BP_TempleLever': [
            {'type': 'BoxCollision', 'name': 'LeverCollision', 'properties': {
                'extent': json.dumps({'x': 50, 'y': 50, 'z': 80}),
                'generate_overlap_events': 'true'
            }},
            {'type': 'StaticMesh', 'name': 'LeverMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cylinder.Cylinder',
                'scale': json.dumps({'x': 0.3, 'y': 0.3, 'z': 1.5})
            }}
        ],
        'BP_HazardZone': [
            {'type': 'BoxCollision', 'name': 'HazardCollision', 'properties': {
                'extent': json.dumps({'x': 100, 'y': 100, 'z': 30}),
                'generate_overlap_events': 'true'
            }},
            {'type': 'StaticMesh', 'name': 'HazardMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cube.Cube',
                'scale': json.dumps({'x': 2.0, 'y': 2.0, 'z': 0.3})
            }}
        ],
        'BP_HealthPickup': [
            {'type': 'BoxCollision', 'name': 'HealthCollision', 'properties': {
                'extent': json.dumps({'x': 40, 'y': 40, 'z': 40}),
                'generate_overlap_events': 'true'
            }},
            {'type': 'StaticMesh', 'name': 'HealthMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Sphere.Sphere',
                'scale': json.dumps({'x': 0.4, 'y': 0.4, 'z': 0.4})
            }},
            {'type': 'PointLight', 'name': 'HealthGlow', 'properties': {
                'intensity': '3000',
                'light_color': json.dumps({'r': 50, 'g': 255, 'b': 50}),
                'attenuation_radius': '300'
            }}
        ],
        'BP_TempleEnemy': [
            {'type': 'StaticMesh', 'name': 'EnemyMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cylinder.Cylinder',
                'scale': json.dumps({'x': 0.8, 'y': 0.8, 'z': 2.0})
            }},
            {'type': 'PointLight', 'name': 'EnemyGlow', 'properties': {
                'intensity': '2000',
                'light_color': json.dumps({'r': 255, 'g': 50, 'b': 0}),
                'attenuation_radius': '300'
            }},
            {'type': 'SphereCollision', 'name': 'EnemyCollision', 'properties': {
                'radius': '50',
                'generate_overlap_events': 'true'
            }}
        ],
        'BP_ExitPortal': [
            {'type': 'BoxCollision', 'name': 'PortalCollision', 'properties': {
                'extent': json.dumps({'x': 150, 'y': 150, 'z': 200}),
                'generate_overlap_events': 'true'
            }},
            {'type': 'StaticMesh', 'name': 'PortalMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cylinder.Cylinder',
                'scale': json.dumps({'x': 3.0, 'y': 3.0, 'z': 0.3})
            }},
            {'type': 'PointLight', 'name': 'PortalGlow', 'properties': {
                'intensity': '8000',
                'light_color': json.dumps({'r': 0, 'g': 255, 'b': 100}),
                'attenuation_radius': '600'
            }}
        ],
        'BP_Torch': [
            {'type': 'StaticMesh', 'name': 'TorchMesh', 'properties': {
                'static_mesh': '/Engine/BasicShapes/Cylinder.Cylinder',
                'scale': json.dumps({'x': 0.15, 'y': 0.15, 'z': 0.8})
            }},
            {'type': 'PointLight', 'name': 'TorchFlame', 'properties': {
                'intensity': '3000',
                'light_color': json.dumps({'r': 255, 'g': 150, 'b': 50}),
                'attenuation_radius': '500'
            }}
        ]
    }

    for bp_name, components in component_specs.items():
        ok_count = 0
        for comp in components:
            try:
                r = c.send_command('add_component', {
                    'blueprint': bp_name,
                    'component_type': comp['type'],
                    'component_name': comp['name']
                })
            except Exception as e:
                r = {'status': 'error', 'message': str(e)}
            if r.get('status') == 'ok' or 'already exists' in r.get('message', ''):
                ok_count += 1
                # Set properties
                for prop_name, prop_val in comp.get('properties', {}).items():
                    try:
                        c.send_command('set_component_property', {
                            'blueprint': bp_name,
                            'component_name': comp['name'],
                            'property_name': prop_name,
                            'value': prop_val
                        })
                    except Exception:
                        pass
            else:
                print(f"  WARN: {bp_name}.{comp['name']}: {r.get('message', 'error')}")

        print(f"  {bp_name}: {ok_count}/{len(components)} components added")

    # Add FloatingPawnMovement to enemy (needed for AI movement)
    try:
        r = c.send_command('add_component', {
            'blueprint': 'BP_TempleEnemy',
            'component_type': 'FloatingPawnMovement',
            'component_name': 'Movement'
        })
        if r.get('status') == 'ok':
            print(f"  BP_TempleEnemy: FloatingPawnMovement added")
    except Exception:
        print(f"  BP_TempleEnemy: FloatingPawnMovement (already exists)")

    print("\n=== PHASE 3 COMPLETE ===")


def phase4_materials(c):
    """Create 12 materials and apply them to Blueprint meshes."""
    print("=== PHASE 4: CREATE MATERIALS ===")

    # Material definitions: name, color RGB (0-1), emissive_boost
    materials = [
        ('MI_StoneFloor', {'r': 0.25, 'g': 0.22, 'b': 0.2}, 0),
        ('MI_StoneWall', {'r': 0.18, 'g': 0.16, 'b': 0.15}, 0),
        ('MI_StoneDoor', {'r': 0.15, 'g': 0.13, 'b': 0.12}, 0),
        ('MI_GoldKey', {'r': 1.0, 'g': 0.8, 'b': 0.0}, 3.0),
        ('MI_PlateCyan', {'r': 0.0, 'g': 0.8, 'b': 1.0}, 2.0),
        ('MI_LeverBlue', {'r': 0.1, 'g': 0.3, 'b': 1.0}, 1.5),
        ('MI_HazardRed', {'r': 1.0, 'g': 0.05, 'b': 0.0}, 2.5),
        ('MI_EnemyRed', {'r': 0.8, 'g': 0.1, 'b': 0.05}, 0.5),
        ('MI_HealthGreen', {'r': 0.1, 'g': 1.0, 'b': 0.2}, 2.0),
        ('MI_PortalGreen', {'r': 0.0, 'g': 1.0, 'b': 0.4}, 5.0),
        ('MI_TorchDark', {'r': 0.1, 'g': 0.06, 'b': 0.03}, 0),
        ('MI_Pillar', {'r': 0.3, 'g': 0.28, 'b': 0.25}, 0),
    ]

    for i, (mat_name, color, emissive) in enumerate(materials):
        params = {'name': mat_name, 'color': color}
        if emissive > 0:
            params['emissive'] = emissive
        try:
            r = c.send_command('create_simple_material', params)
            status = "OK" if r.get('status') == 'ok' else r.get('message', 'error')
        except Exception as e:
            status = f"ERROR: {e}"
            # Try to reconnect after editor recovers
            time.sleep(5)
            try:
                c.close()
            except Exception:
                pass
            c.sock = __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_STREAM)
            c.sock.settimeout(c.timeout)
            c._buffer = b""
            c.sock.connect((c.host, c.port))
            try:
                r = c.send_command('create_simple_material', params)
                status = "OK (retry)" if r.get('status') == 'ok' else r.get('message', 'error')
            except Exception as e2:
                status = f"ERROR (retry failed): {e2}"
        print(f"  {mat_name}: {status}")
        # Small delay between material creations to avoid overwhelming UE
        if i < len(materials) - 1:
            time.sleep(0.5)

    print()

    # Apply materials to Blueprint meshes
    print("  Applying materials to meshes...")
    mat_assignments = [
        ('BP_TempleKey', 'KeyMesh', 'MI_GoldKey'),
        ('BP_TempleDoor', 'DoorMesh', 'MI_StoneDoor'),
        ('BP_PressurePlate', 'PlateMesh', 'MI_PlateCyan'),
        ('BP_TempleLever', 'LeverMesh', 'MI_LeverBlue'),
        ('BP_HazardZone', 'HazardMesh', 'MI_HazardRed'),
        ('BP_HealthPickup', 'HealthMesh', 'MI_HealthGreen'),
        ('BP_TempleEnemy', 'EnemyMesh', 'MI_EnemyRed'),
        ('BP_ExitPortal', 'PortalMesh', 'MI_PortalGreen'),
        ('BP_Torch', 'TorchMesh', 'MI_TorchDark'),
    ]

    for bp, comp, mat in mat_assignments:
        try:
            r = c.send_command('apply_material', {
                'blueprint': bp,
                'component_name': comp,
                'material_path': f'/Game/Arcwright/Materials/{mat}'
            })
            status = "OK" if r.get('status') == 'ok' else r.get('message', 'error')
        except Exception as e:
            status = f"ERROR: {e}"
        print(f"    {bp}.{comp} <- {mat}: {status}")

    print("\n=== PHASE 4 COMPLETE ===")


def phase5_populate_level(c):
    """Spawn all ~60 actors at positions from game design doc."""
    print("=== PHASE 5: POPULATE LEVEL ===")

    def spawn(label, bp_class, x, y, z, scale=None):
        params = {
            'class': f'/Game/Arcwright/Generated/{bp_class}.{bp_class}',
            'label': label,
            'location': {'x': x, 'y': y, 'z': z}
        }
        if scale:
            params['scale'] = scale
        try:
            r = c.send_command('spawn_actor_at', params)
            return r.get('status') == 'ok'
        except Exception as e:
            print(f"    WARN: {label} spawn error: {e}")
            return False

    def spawn_basic(label, mesh_path, x, y, z, scale=None, mat=None):
        """Spawn a basic static mesh actor (for walls, floors, pillars)."""
        params = {
            'class': 'StaticMeshActor',
            'label': label,
            'location': {'x': x, 'y': y, 'z': z}
        }
        if scale:
            params['scale'] = scale
        r = c.send_command('spawn_actor_at', params)
        return r.get('status') == 'ok'

    spawned = 0
    failed = 0

    # --- Starting Room ---
    print("  Starting Room...")
    actors_starting = [
        ('Torch_S1', 'BP_Torch', -500, -400, 200),
        ('Torch_S2', 'BP_Torch', 500, -400, 200),
        ('GameManager', 'BP_TempleGameManager', 0, 0, 300),
    ]
    for label, cls, x, y, z in actors_starting:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # --- Corridor 1 ---
    print("  Corridor 1...")
    actors_c1 = [
        ('Torch_C1a', 'BP_Torch', -180, 600, 200),
        ('Torch_C1b', 'BP_Torch', 180, 600, 200),
        ('Torch_C1c', 'BP_Torch', -180, 1000, 200),
        ('Torch_C1d', 'BP_Torch', 180, 1000, 200),
        ('Health_C1', 'BP_HealthPickup', 0, 800, 50),
        ('Enemy_C1', 'BP_TempleEnemy', 0, 700, 50),
    ]
    for label, cls, x, y, z in actors_c1:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # --- Key 1 Room (West) ---
    print("  Key 1 Room (West)...")
    actors_k1 = [
        ('Key1', 'BP_TempleKey', -1500, 1200, 50),
        ('Plate_K1', 'BP_PressurePlate', -1200, 800, 0),
        ('Hazard_K1', 'BP_HazardZone', -1400, 1000, 50),
        ('Torch_K1a', 'BP_Torch', -1800, 800, 200),
        ('Torch_K1b', 'BP_Torch', -1200, 1200, 200),
        ('Enemy_K1', 'BP_TempleEnemy', -1500, 900, 50),
    ]
    for label, cls, x, y, z in actors_k1:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # --- Key 2 Room (East) ---
    print("  Key 2 Room (East)...")
    actors_k2 = [
        ('Key2', 'BP_TempleKey', 1500, 1200, 50),
        ('Lever_K2', 'BP_TempleLever', 1200, 800, 50),
        ('Torch_K2a', 'BP_Torch', 1200, 800, 200),
        ('Torch_K2b', 'BP_Torch', 1800, 1200, 200),
        ('Torch_K2c', 'BP_Torch', 1500, 1400, 200),
    ]
    for label, cls, x, y, z in actors_k2:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # --- Main Hall ---
    print("  Main Hall...")
    actors_mh = [
        ('Torch_MH1', 'BP_Torch', -800, 1600, 200),
        ('Torch_MH2', 'BP_Torch', 800, 1600, 200),
        ('Torch_MH3', 'BP_Torch', -800, 2400, 200),
        ('Torch_MH4', 'BP_Torch', 800, 2400, 200),
        ('Torch_MH5', 'BP_Torch', -400, 2000, 300),
        ('Torch_MH6', 'BP_Torch', 400, 2000, 300),
        ('Health_MH1', 'BP_HealthPickup', -600, 2200, 50),
        ('Health_MH2', 'BP_HealthPickup', 600, 1800, 50),
        ('Enemy_MH1', 'BP_TempleEnemy', -300, 1800, 50),
        ('Enemy_MH2', 'BP_TempleEnemy', 300, 2200, 50),
    ]
    for label, cls, x, y, z in actors_mh:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # --- Key 3 Room ---
    print("  Key 3 Room...")
    actors_k3 = [
        ('Key3', 'BP_TempleKey', -1000, 3200, 50),
        ('Plate_K3a', 'BP_PressurePlate', -1200, 2800, 0),
        ('Plate_K3b', 'BP_PressurePlate', -800, 2900, 0),
        ('Plate_K3c', 'BP_PressurePlate', -1000, 3000, 0),
        ('Torch_K3a', 'BP_Torch', -1200, 3200, 200),
        ('Torch_K3b', 'BP_Torch', -800, 3200, 200),
        ('Enemy_K3', 'BP_TempleEnemy', -1000, 2900, 50),
    ]
    for label, cls, x, y, z in actors_k3:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # --- Hazard Corridor ---
    print("  Hazard Corridor...")
    actors_hc = [
        ('Hazard_HC1', 'BP_HazardZone', 1000, 2800, 50),
        ('Hazard_HC2', 'BP_HazardZone', 1000, 3100, 50),
        ('Hazard_HC3', 'BP_HazardZone', 1000, 3400, 50),
    ]
    for label, cls, x, y, z in actors_hc:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # Hazard corridor red lights (PointLight actors, not Blueprint)
    # These are just for atmosphere - spawn as basic actors
    # (skip for now - torches already provide light coverage)

    # --- Exit Corridor + Room ---
    print("  Exit Corridor + Room...")
    actors_exit = [
        ('Door_Exit', 'BP_TempleDoor', 0, 3500, 0),
        ('Torch_EC1', 'BP_Torch', -180, 3600, 200),
        ('Torch_EC2', 'BP_Torch', 180, 3600, 200),
        ('Portal', 'BP_ExitPortal', 0, 4000, 0),
    ]
    for label, cls, x, y, z in actors_exit:
        if spawn(label, cls, x, y, z):
            spawned += 1
        else:
            failed += 1
            print(f"    FAIL: {label}")

    # --- Pillars in Main Hall (static mesh actors) ---
    print("  Main Hall Pillars...")
    for pillar_label, px, py, pz in [('Pillar_1', -400, 2000, 0), ('Pillar_2', 400, 2000, 0)]:
        r = c.send_command('spawn_actor_at', {
            'class': 'StaticMeshActor',
            'label': pillar_label,
            'location': {'x': px, 'y': py, 'z': pz},
            'scale': {'x': 1, 'y': 1, 'z': 5}
        })
        if r.get('status') == 'ok':
            spawned += 1
        else:
            print(f"    FAIL: {pillar_label}: {r.get('message', 'error')}")
            failed += 1

    print(f"\n  Total spawned: {spawned} | Failed: {failed}")
    print("\n=== PHASE 5 COMPLETE ===")


def phase6_atmosphere(c):
    """Add PostProcessVolume and NavMeshBoundsVolume."""
    print("=== PHASE 6: ATMOSPHERE ===")

    # PostProcessVolume
    print("  Adding PostProcessVolume...")
    r = c.send_command('add_post_process_volume', {
        'label': 'PP_TempleAtmosphere',
        'location': {'x': 0, 'y': 2000, 'z': 300},
        'infinite_extent': True,
        'settings': {
            'bloom_intensity': 1.5,
            'bloom_threshold': 0.8,
            'vignette_intensity': 0.5,
            'auto_exposure_min': 0.5,
            'auto_exposure_max': 2.0,
            'ambient_occlusion_intensity': 0.8
        }
    })
    print(f"    PostProcess: {r.get('status')}")

    # Apply additional post-process settings
    r = c.send_command('set_post_process_settings', {
        'label': 'PP_TempleAtmosphere',
        'settings': {
            'color_saturation': {'x': 0.85, 'y': 0.85, 'z': 0.9, 'w': 1.0},
            'color_contrast': {'x': 1.1, 'y': 1.1, 'z': 1.15, 'w': 1.0}
        }
    })
    print(f"    Color grading: {r.get('status')}")

    # NavMeshBoundsVolume for AI navigation (even though we use bUsePathfinding=false)
    print("  Spawning NavMeshBoundsVolume...")
    r = c.send_command('spawn_actor_at', {
        'class': 'NavMeshBoundsVolume',
        'label': 'NavMesh_Temple',
        'location': {'x': 0, 'y': 2000, 'z': 250},
        'scale': {'x': 50, 'y': 50, 'z': 10}
    })
    print(f"    NavMesh: {r.get('status')}")

    print("\n=== PHASE 6 COMPLETE ===")


def phase7_sequencer_and_save(c):
    """Create intro sequence and save everything."""
    print("=== PHASE 7: SEQUENCER + SAVE ===")

    # Create intro sequence
    print("  Creating intro sequence...")
    r = c.send_command('create_sequence', {
        'name': 'SEQ_TempleIntro',
        'duration': 5.0
    })
    print(f"    Sequence: {r.get('status')}")

    # Save all (avoid save_level which can trigger blocking dialog on untitled maps)
    print("  Saving all assets...")
    try:
        r = c.send_command('save_all', {})
        print(f"    save_all: {r.get('status')}")
    except Exception as e:
        print(f"    save_all: ERROR {e}")

    print("\n=== PHASE 7 COMPLETE ===")


def phase8_verify(c):
    """Verify all Blueprints compile, count actors, check widget tree."""
    print("=== PHASE 8: VERIFICATION ===")

    # Verify all Blueprints compile
    print("  Checking Blueprint compilation...")
    bp_names = [
        'BP_TempleKey', 'BP_TempleDoor', 'BP_PressurePlate', 'BP_TempleLever',
        'BP_HazardZone', 'BP_HealthPickup', 'BP_TempleEnemy', 'BP_ExitPortal',
        'BP_Torch', 'BP_TempleGameManager'
    ]
    compiled_count = 0
    for bp in bp_names:
        r = c.send_command('get_blueprint_info', {'name': bp})
        if r.get('status') == 'ok':
            compiled = r['data'].get('compiled', False)
            nodes = r['data'].get('node_count', 0)
            comps = len(r['data'].get('components', []))
            status_str = "COMPILED" if compiled else "NOT COMPILED"
            if compiled:
                compiled_count += 1
            print(f"    {bp}: {status_str} | {nodes} nodes | {comps} components")
        else:
            print(f"    {bp}: NOT FOUND")

    print(f"\n  Blueprints: {compiled_count}/{len(bp_names)} compiled")

    # Count actors in level
    print("\n  Checking level actors...")
    r = c.send_command('get_actors', {})
    if r.get('status') == 'ok':
        actors = r['data'].get('actors', [])
        print(f"    Total actors in level: {len(actors)}")

        # Count by type
        type_counts = {}
        for a in actors:
            cls = a.get('class', 'Unknown')
            short = cls.split('.')[-1] if '.' in cls else cls
            type_counts[short] = type_counts.get(short, 0) + 1

        for cls, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"      {cls}: {count}")

    # Verify widget tree
    print("\n  Checking WBP_TempleHUD...")
    r = c.send_command('get_widget_tree', {'widget_blueprint': 'WBP_TempleHUD'})
    if r.get('status') == 'ok':
        tree_str = json.dumps(r['data'])
        widget_count = tree_str.count('"name"')
        print(f"    Widget tree: {widget_count} widgets found")
    else:
        print(f"    Widget tree: {r.get('message', 'error')}")

    print("\n=== PHASE 8: VERIFICATION COMPLETE ===")
    print(f"\n{'='*50}")
    print("  TEMPLE ESCAPE BUILD COMPLETE!")
    print(f"  Blueprints: {compiled_count}/{len(bp_names)}")
    print(f"{'='*50}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build Temple Escape demo game')
    parser.add_argument('--phase', type=int, default=-1, help='Run specific phase (-1=all, 0=lighting)')
    args = parser.parse_args()

    c = ArcwrightClient()

    try:
        phases = {
            0: phase0_scene_lighting,
            1: phase1_clean_and_hud,
            2: phase2_create_blueprints,
            3: phase3_add_components,
            4: phase4_materials,
            5: phase5_populate_level,
            6: phase6_atmosphere,
            7: phase7_sequencer_and_save,
            8: phase8_verify,
        }

        if args.phase == -1:
            # Run all phases
            all_phases = [
                (0, phase0_scene_lighting),
                ("0b", phase0b_floor_and_fps),
                (1, phase1_clean_and_hud),
                (2, phase2_create_blueprints),
                (3, phase3_add_components),
                (4, phase4_materials),
                (5, phase5_populate_level),
                (6, phase6_atmosphere),
                (7, phase7_sequencer_and_save),
                (8, phase8_verify),
            ]
            for phase_id, phase_fn in all_phases:
                phase_fn(c)
                # Save between phases — includes external actors (World Partition)
                if phase_id != 8:
                    saved, ext_count = save_all_verified(c)
                    ext_msg = f" + {ext_count} external actors" if ext_count > 0 else ""
                    print(f"  [Saved after Phase {phase_id}{ext_msg}]")
                print()
        elif args.phase in phases:
            phases[args.phase](c)
        else:
            print(f"Unknown phase: {args.phase}")
    finally:
        c.close()


if __name__ == '__main__':
    main()
