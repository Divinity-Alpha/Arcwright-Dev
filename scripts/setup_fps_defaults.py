#!/usr/bin/env python3
"""
setup_fps_defaults.py — Reusable FPS player setup for BlueprintLLMTest.

Creates BP_FPSCharacter (Camera, WASD movement, Jump), BP_FPSPlayerController
(mouse hidden/captured), and BP_FPSGameMode (wires them together).

Based on UE5's built-in First Person template, adapted for Blueprint TCP creation.

Usage:
    python scripts/setup_fps_defaults.py          # Full FPS setup
    python scripts/setup_fps_defaults.py --test    # Verify existing setup
"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.mcp_client.blueprint_client import ArcwrightClient

# ─── Paths ───────────────────────────────────────────────────────────────────
IR_DIR = os.path.join(os.path.dirname(__file__), '..', 'test_ir')
FPS_CHARACTER_IR = os.path.join(IR_DIR, 'bp_fps_character.blueprint.json')
FPS_CONTROLLER_IR = os.path.join(IR_DIR, 'bp_fps_player_controller.blueprint.json')
FPS_GAMEMODE_IR = os.path.join(IR_DIR, 'bp_temple_game_mode.blueprint.json')


def setup_fps(client=None, verbose=True):
    """
    Complete FPS player setup. Call with an existing ArcwrightClient or None to create one.

    Creates:
      - BP_FPSCharacter: Character with Camera, WASD movement, Jump
      - BP_FPSPlayerController: Mouse hidden, game-only input
      - BP_FPSGameMode: Wires Character + Controller together
      - Sets world GameMode

    Returns dict with setup results.
    """
    own_client = client is None
    if own_client:
        client = ArcwrightClient()

    results = {'steps': [], 'success': True}

    def log(msg):
        if verbose:
            print(f"  [FPS] {msg}")
        results['steps'].append(msg)

    try:
        # ── Step 1: Health check ──────────────────────────────────────────
        log("Checking UE connection...")
        r = client.health_check()
        log(f"Connected to {r.get('server', '?')} v{r.get('version', '?')}")

        # ── Step 2: Clean up existing FPS Blueprints ─────────────────────
        for bp_name in ['BP_FPSCharacter', 'BP_FPSPlayerController', 'BP_FPSGameMode']:
            try:
                client.delete_blueprint(bp_name)
                log(f"Deleted existing {bp_name}")
            except Exception:
                pass  # Doesn't exist yet, fine

        time.sleep(0.5)

        # ── Step 3: Create BP_FPSCharacter ───────────────────────────────
        log("Creating BP_FPSCharacter from IR...")
        ir_path = os.path.abspath(FPS_CHARACTER_IR).replace('\\', '/')
        r = client.import_from_ir(ir_path)
        log(f"  IR import: {r.get('status', r)}")

        # Add Camera component at eye height
        log("Adding Camera component...")
        r = client.send_command('add_component', {
            'blueprint': 'BP_FPSCharacter',
            'component_type': 'CameraComponent',
            'component_name': 'FPSCamera',
            'location': {'x': 0, 'y': 0, 'z': 64}
        })
        log(f"  Camera added: {r.get('status', r)}")

        # Set Camera: bUsePawnControlRotation = true (via generic reflection)
        log("Setting Camera bUsePawnControlRotation...")
        r = client.send_command('set_component_property', {
            'blueprint': 'BP_FPSCharacter',
            'component_name': 'FPSCamera',
            'property_name': 'bUsePawnControlRotation',
            'value': True
        })
        log(f"  bUsePawnControlRotation: {r.get('status', r)}")

        # Set Camera FOV
        log("Setting Camera FieldOfView = 90...")
        r = client.send_command('set_component_property', {
            'blueprint': 'BP_FPSCharacter',
            'component_name': 'FPSCamera',
            'property_name': 'FieldOfView',
            'value': 90.0
        })
        log(f"  FieldOfView: {r.get('status', r)}")

        # Set Character CDO: bUseControllerRotationYaw = true
        log("Setting Character CDO properties...")
        r = client.send_command('set_class_defaults', {
            'blueprint': 'BP_FPSCharacter',
            'properties': {
                'bUseControllerRotationYaw': 'true',
                'bUseControllerRotationPitch': 'false',
                'bUseControllerRotationRoll': 'false'
            }
        })
        log(f"  CDO rotation: {r.get('status', r)}")

        # Set movement defaults (nested 'properties' object required)
        log("Setting movement defaults...")
        r = client.send_command('set_movement_defaults', {
            'blueprint': 'BP_FPSCharacter',
            'properties': {
                'max_walk_speed': 600.0,
                'jump_z_velocity': 420.0,
                'air_control': 0.5,
                'gravity_scale': 1.0,
                'braking_deceleration_falling': 1500.0,
                'max_acceleration': 2048.0
            }
        })
        log(f"  Movement: {r.get('status', r)}")

        # Verify Character compiled
        r = client.get_blueprint_info('BP_FPSCharacter')
        node_count = len(r.get('nodes', []))
        compiled = r.get('compile_status', 'unknown')
        log(f"  BP_FPSCharacter: {node_count} nodes, compile={compiled}")

        # ── Step 4: Create BP_FPSPlayerController ────────────────────────
        log("Creating BP_FPSPlayerController...")
        # Import from IR if it exists, otherwise create minimal
        if os.path.exists(FPS_CONTROLLER_IR):
            ir_path = os.path.abspath(FPS_CONTROLLER_IR).replace('\\', '/')
            r = client.import_from_ir(ir_path)
            log(f"  IR import: {r.get('status', r)}")
        else:
            # Create empty PlayerController Blueprint
            r = client.send_command('import_from_ir', {
                'ir_json': json.dumps({
                    'metadata': {
                        'name': 'BP_FPSPlayerController',
                        'parent_class': 'PlayerController'
                    },
                    'variables': [],
                    'nodes': [],
                    'connections': []
                })
            })
            log(f"  Created empty controller")

        # Set Controller CDO: mouse hidden, captured, game-only input
        log("Setting Controller CDO properties (mouse hidden, captured)...")
        r = client.send_command('set_class_defaults', {
            'blueprint': 'BP_FPSPlayerController',
            'properties': {
                'bShowMouseCursor': 'false',
                'DefaultMouseCursor': '0',
                'bEnableClickEvents': 'false',
                'bEnableMouseOverEvents': 'false'
            }
        })
        log(f"  Controller CDO: {r.get('status', r)}")

        # ── Step 5: Create BP_FPSGameMode ────────────────────────────────
        log("Creating BP_FPSGameMode...")
        import tempfile
        gm_json = {
            'metadata': {'name': 'BP_FPSGameMode', 'parent_class': 'GameModeBase'},
            'variables': [], 'nodes': [], 'connections': []
        }
        tmp_path = os.path.join(tempfile.gettempdir(), 'bp_fps_gamemode.blueprint.json')
        with open(tmp_path, 'w') as f:
            json.dump(gm_json, f)
        r = client.import_from_ir(tmp_path.replace('\\', '/'))
        log(f"  GameMode created: compiled={r.get('data', {}).get('compiled')}")
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        # Set GameMode CDO: wire Character + Controller
        log("Setting GameMode class defaults...")
        r = client.send_command('set_class_defaults', {
            'blueprint': 'BP_FPSGameMode',
            'properties': {
                'default_pawn_class': 'BP_FPSCharacter',
                'player_controller_class': 'BP_FPSPlayerController'
            }
        })
        log(f"  GameMode CDO: {r.get('status', r)}")

        # ── Step 6: Set world GameMode ───────────────────────────────────
        log("Setting world GameMode override...")
        r = client.send_command('set_game_mode', {
            'game_mode': 'BP_FPSGameMode'
        })
        log(f"  World GameMode: {r.get('status', r)}")

        # ── Step 7: Save ─────────────────────────────────────────────────
        log("Saving all...")
        r = client.send_command('save_all', {})
        log(f"  Save: {r.get('status', r)}")

        log("FPS setup complete!")
        log("  BP_FPSCharacter: Camera + WASD + Jump")
        log("  BP_FPSPlayerController: Mouse hidden/captured")
        log("  BP_FPSGameMode: Wires Character + Controller")
        log("  World GameMode set. Press Play to test!")

    except Exception as e:
        log(f"ERROR: {e}")
        results['success'] = False
        raise
    finally:
        if own_client:
            client.close()

    return results


def verify_fps(client=None, verbose=True):
    """Verify existing FPS setup is correct."""
    own_client = client is None
    if own_client:
        client = ArcwrightClient()

    issues = []

    def check(label, condition, detail=""):
        status = "OK" if condition else "FAIL"
        if verbose:
            msg = f"  [{status}] {label}"
            if detail:
                msg += f" — {detail}"
            print(msg)
        if not condition:
            issues.append(label)

    try:
        if verbose:
            print("\n=== FPS Setup Verification ===\n")

        # Check BP_FPSCharacter
        try:
            r = client.get_blueprint_info('BP_FPSCharacter')
            check("BP_FPSCharacter exists", True)
            check("BP_FPSCharacter compiled", r.get('compile_status') != 'Error',
                  r.get('compile_status', 'unknown'))
            nodes = r.get('nodes', [])
            check("BP_FPSCharacter has movement nodes", len(nodes) >= 5,
                  f"{len(nodes)} nodes")
        except Exception:
            check("BP_FPSCharacter exists", False)

        # Check BP_FPSPlayerController
        try:
            r = client.get_blueprint_info('BP_FPSPlayerController')
            check("BP_FPSPlayerController exists", True)
        except Exception:
            check("BP_FPSPlayerController exists", False)

        # Check BP_FPSGameMode
        try:
            r = client.get_blueprint_info('BP_FPSGameMode')
            check("BP_FPSGameMode exists", True)
        except Exception:
            check("BP_FPSGameMode exists", False)

        # Check actors
        try:
            r = client.send_command('get_actors', {})
            actors = r.get('data', {}).get('actors', []) if isinstance(r, dict) and 'data' in r else r.get('actors', [])
            has_player_start = any('PlayerStart' in str(a) for a in actors)
            check("PlayerStart in level", has_player_start)
        except Exception:
            check("PlayerStart in level", False, "Could not query actors")

        if verbose:
            total = 5
            passed = total - len(issues)
            print(f"\n{passed}/{total} checks passed.")
            if issues:
                print(f"Issues: {', '.join(issues)}")
            else:
                print("FPS setup looks good! Press Play to test.")

    finally:
        if own_client:
            client.close()

    return len(issues) == 0


if __name__ == '__main__':
    if '--test' in sys.argv or '--verify' in sys.argv:
        verify_fps()
    else:
        print("=== FPS Player Setup ===\n")
        setup_fps()
