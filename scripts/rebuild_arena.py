"""Rebuild Arena Collector with fully functional Blueprints.

Fully self-contained: creates materials, imports BPs, adds components,
spawns actors, sets up environment (lighting + floor), and saves.

Any user can run this against a fresh UE project with the BlueprintLLM plugin
to get the complete Arena Collector game in one command.

Usage:
    python scripts/rebuild_arena.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.mcp_client.blueprint_client import ArcwrightClient


def main():
    c = ArcwrightClient()
    c.sock.settimeout(30)

    r = c.health_check()
    print(f"Server: {r['status']}\n")

    # == Step 1: Create materials (idempotent - overwrites if exist) ==
    print("=== Step 1: Create materials ===")
    materials = [
        ('MAT_Green', {'r': 0.0, 'g': 0.8, 'b': 0.2}, 2.0),
        ('MAT_Gold',  {'r': 1.0, 'g': 0.8, 'b': 0.0}, 2.0),
        ('MAT_Red',   {'r': 0.9, 'g': 0.1, 'b': 0.1}, 1.0),
        ('MAT_Floor', {'r': 0.3, 'g': 0.3, 'b': 0.35}, 0.0),
    ]
    for name, color, emissive in materials:
        r = c.create_simple_material(name, color, emissive_strength=emissive)
        print(f"  {name}: {r.get('status')}")

    # == Step 2: Delete old BPs ==
    print("\n=== Step 2: Delete old Blueprints ===")
    for bp in ['BP_HealthPickup', 'BP_ScorePickup', 'BP_DamageZone',
               'BP_ArenaManager', 'BP_Floor']:
        try:
            c.delete_blueprint(bp)
            print(f"  deleted {bp}")
        except Exception:
            print(f"  {bp} not found (ok)")

    # == Step 3: Import BPs with gameplay logic ==
    print("\n=== Step 3: Import Blueprints ===")
    ir_dir = 'C:/BlueprintLLM/test_ir'
    ir_files = {
        'BP_HealthPickup': f'{ir_dir}/game_health_pickup.blueprint.json',
        'BP_ScorePickup':  f'{ir_dir}/game_score_pickup.blueprint.json',
        'BP_DamageZone':   f'{ir_dir}/game_damage_zone.blueprint.json',
        'BP_ArenaManager': f'{ir_dir}/game_arena_manager.blueprint.json',
        'BP_Floor':        f'{ir_dir}/arena_floor.blueprint.json',
    }
    for name, path in ir_files.items():
        r = c.import_from_ir(path)
        print(f"  {name}: {r.get('status')}")

    # == Step 4: Add components ==
    print("\n=== Step 4: Add components ===")

    # -- BP_HealthPickup: green sphere + collision + light --
    for comp in [
        ('BP_HealthPickup', 'SphereCollision', 'PickupCollision'),
        ('BP_HealthPickup', 'StaticMesh', 'PickupMesh'),
        ('BP_HealthPickup', 'PointLight', 'PickupLight'),
    ]:
        c.add_component(*comp)

    c.set_component_property('BP_HealthPickup', 'PickupCollision',
                             'generate_overlap_events', True)
    c.set_component_property('BP_HealthPickup', 'PickupCollision',
                             'radius', 80.0)
    c.set_component_property('BP_HealthPickup', 'PickupMesh',
                             'static_mesh', '/Engine/BasicShapes/Sphere.Sphere')
    c.set_component_property('BP_HealthPickup', 'PickupMesh',
                             'scale', {'x': 0.5, 'y': 0.5, 'z': 0.5})
    c.set_component_property('BP_HealthPickup', 'PickupMesh',
                             'material', '/Game/Arcwright/Materials/MAT_Green')
    c.set_component_property('BP_HealthPickup', 'PickupLight',
                             'light_color', {'r': 0, 'g': 255, 'b': 50})
    c.set_component_property('BP_HealthPickup', 'PickupLight',
                             'intensity', 5000.0)
    c.set_component_property('BP_HealthPickup', 'PickupLight',
                             'attenuation_radius', 300.0)
    c.compile_blueprint('BP_HealthPickup')
    print("  BP_HealthPickup: components set + compiled")

    # -- BP_ScorePickup: gold cube + collision + light --
    for comp in [
        ('BP_ScorePickup', 'SphereCollision', 'PickupCollision'),
        ('BP_ScorePickup', 'StaticMesh', 'PickupMesh'),
        ('BP_ScorePickup', 'PointLight', 'PickupLight'),
    ]:
        c.add_component(*comp)

    c.set_component_property('BP_ScorePickup', 'PickupCollision',
                             'generate_overlap_events', True)
    c.set_component_property('BP_ScorePickup', 'PickupCollision',
                             'radius', 80.0)
    c.set_component_property('BP_ScorePickup', 'PickupMesh',
                             'static_mesh', '/Engine/BasicShapes/Cube.Cube')
    c.set_component_property('BP_ScorePickup', 'PickupMesh',
                             'scale', {'x': 0.3, 'y': 0.3, 'z': 0.3})
    c.set_component_property('BP_ScorePickup', 'PickupMesh',
                             'material', '/Game/Arcwright/Materials/MAT_Gold')
    c.set_component_property('BP_ScorePickup', 'PickupLight',
                             'light_color', {'r': 255, 'g': 200, 'b': 0})
    c.set_component_property('BP_ScorePickup', 'PickupLight',
                             'intensity', 5000.0)
    c.set_component_property('BP_ScorePickup', 'PickupLight',
                             'attenuation_radius', 300.0)
    c.compile_blueprint('BP_ScorePickup')
    print("  BP_ScorePickup: components set + compiled")

    # -- BP_DamageZone: red flat cylinder + large collision --
    for comp in [
        ('BP_DamageZone', 'BoxCollision', 'ZoneCollision'),
        ('BP_DamageZone', 'StaticMesh', 'ZoneMesh'),
    ]:
        c.add_component(*comp)

    c.set_component_property('BP_DamageZone', 'ZoneCollision',
                             'generate_overlap_events', True)
    c.set_component_property('BP_DamageZone', 'ZoneCollision',
                             'extent', {'x': 300, 'y': 300, 'z': 50})
    c.set_component_property('BP_DamageZone', 'ZoneMesh',
                             'static_mesh', '/Engine/BasicShapes/Cylinder.Cylinder')
    c.set_component_property('BP_DamageZone', 'ZoneMesh',
                             'scale', {'x': 3.0, 'y': 3.0, 'z': 0.1})
    c.set_component_property('BP_DamageZone', 'ZoneMesh',
                             'material', '/Game/Arcwright/Materials/MAT_Red')
    c.compile_blueprint('BP_DamageZone')
    print("  BP_DamageZone: components set + compiled")

    # -- BP_ArenaManager: no visible components --
    c.compile_blueprint('BP_ArenaManager')
    print("  BP_ArenaManager: compiled")

    # -- BP_Floor: large flat platform --
    c.add_component('BP_Floor', 'StaticMesh', 'FloorMesh')
    c.set_component_property('BP_Floor', 'FloorMesh',
                             'static_mesh', '/Engine/BasicShapes/Cube.Cube')
    c.set_component_property('BP_Floor', 'FloorMesh',
                             'scale', {'x': 30.0, 'y': 30.0, 'z': 0.2})
    c.set_component_property('BP_Floor', 'FloorMesh',
                             'material', '/Game/Arcwright/Materials/MAT_Floor')
    c.compile_blueprint('BP_Floor')
    print("  BP_Floor: components set + compiled")

    # == Step 5: Delete old actors ==
    print("\n=== Step 5: Delete old actors ===")
    labels = [
        'HealthPickup_1', 'HealthPickup_2', 'HealthPickup_3', 'HealthPickup_4',
        'ScorePickup_1', 'ScorePickup_2', 'ScorePickup_3', 'ScorePickup_4',
        'DamageZone_1', 'DamageZone_2', 'DamageZone_3', 'ArenaManager',
        'Floor', 'Sun', 'SkyLight', 'Sky', 'Fog', 'PlayerStart',
    ]
    for label in labels:
        try:
            c.delete_actor(label)
            print(f"  deleted {label}")
        except Exception:
            print(f"  {label} not found (ok)")

    # == Step 6: Spawn environment ==
    print("\n=== Step 6: Spawn environment ===")
    env_actors = [
        ('DirectionalLight', 'Sun',         {'x': 0, 'y': 0, 'z': 1000},
         {'pitch': -45, 'yaw': 45, 'roll': 0}),
        ('SkyLight',         'SkyLight',     {'x': 0, 'y': 0, 'z': 1000}, None),
        ('SkyAtmosphere',    'Sky',          {'x': 0, 'y': 0, 'z': 0},    None),
        ('ExponentialHeightFog', 'Fog',      {'x': 0, 'y': 0, 'z': 100},  None),
        ('PlayerStart',      'PlayerStart',  {'x': 0, 'y': 0, 'z': 100},  None),
    ]
    for cls, label, loc, rot in env_actors:
        r = c.spawn_actor_at(actor_class=cls, location=loc,
                             rotation=rot, label=label)
        print(f"  {label}: {r.get('status')}")

    # == Step 7: Spawn game actors ==
    print("\n=== Step 7: Spawn game actors ===")
    gen = '/Game/Arcwright/Generated'
    actors = [
        (f'{gen}/BP_Floor',         'Floor',          {'x': 0, 'y': 0, 'z': -10}),
        (f'{gen}/BP_HealthPickup',  'HealthPickup_1', {'x': 500, 'y': 300, 'z': 50}),
        (f'{gen}/BP_HealthPickup',  'HealthPickup_2', {'x': -500, 'y': -300, 'z': 50}),
        (f'{gen}/BP_HealthPickup',  'HealthPickup_3', {'x': 300, 'y': -500, 'z': 50}),
        (f'{gen}/BP_HealthPickup',  'HealthPickup_4', {'x': -300, 'y': 500, 'z': 50}),
        (f'{gen}/BP_ScorePickup',   'ScorePickup_1',  {'x': 200, 'y': 200, 'z': 50}),
        (f'{gen}/BP_ScorePickup',   'ScorePickup_2',  {'x': -200, 'y': -200, 'z': 50}),
        (f'{gen}/BP_ScorePickup',   'ScorePickup_3',  {'x': 400, 'y': -100, 'z': 50}),
        (f'{gen}/BP_ScorePickup',   'ScorePickup_4',  {'x': -400, 'y': 100, 'z': 50}),
        (f'{gen}/BP_DamageZone',    'DamageZone_1',   {'x': 0, 'y': 600, 'z': 0}),
        (f'{gen}/BP_DamageZone',    'DamageZone_2',   {'x': 600, 'y': 0, 'z': 0}),
        (f'{gen}/BP_DamageZone',    'DamageZone_3',   {'x': -600, 'y': -600, 'z': 0}),
        (f'{gen}/BP_ArenaManager',  'ArenaManager',   {'x': 0, 'y': 0, 'z': 200}),
    ]

    ok = 0
    for bp_path, label, loc in actors:
        r = c.spawn_actor_at(actor_class=bp_path, location=loc, label=label)
        s = r.get('status')
        print(f"  {label}: {s}")
        if s == 'ok':
            ok += 1
    print(f"  Spawned: {ok}/{len(actors)}")

    # == Step 8: Save everything ==
    print("\n=== Step 8: Save ===")
    c.sock.settimeout(120)
    r = c.send_command('save_level', {'name': 'ArenaLevel'})
    print(f"  save_level: {r.get('status')}")
    r = c.save_all()
    print(f"  save_all: {r.get('status')}")

    # == Step 9: Verify ==
    print("\n=== Step 9: Verify ===")
    c.sock.settimeout(15)
    actors_result = c.get_actors()
    all_actors = actors_result.get('data', {}).get('actors', [])
    arena_actors = [a for a in all_actors if any(
        prefix in a.get('label', '')
        for prefix in ['HealthPickup', 'ScorePickup', 'DamageZone',
                        'ArenaManager', 'Floor']
    )]
    print(f"  Arena actors: {len(arena_actors)}")

    for bp in ['BP_HealthPickup', 'BP_ScorePickup', 'BP_DamageZone',
               'BP_ArenaManager', 'BP_Floor']:
        info = c.get_blueprint_info(bp)
        nodes = info.get('data', {}).get('node_count', '?')
        comps_r = c.get_components(bp)
        comps = len(comps_r.get('data', {}).get('components', []))
        print(f"  {bp}: {nodes} nodes, {comps} components")

    c.close()
    print("\n=== ARENA COLLECTOR REBUILT ===")
    print("Press Play in the editor to test:")
    print("  - Green spheres: '+25 Health!' + disappear on touch")
    print("  - Gold cubes: '+10 Score!' + disappear on touch")
    print("  - Red zones: 'DANGER! -10 HP!' / 'Escaped danger zone'")
    print("  - On start: '=== ARENA COLLECTOR STARTED ==='")


if __name__ == '__main__':
    main()
