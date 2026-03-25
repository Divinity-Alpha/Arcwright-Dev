"""
B31-B33 Asset Import Tests
Tests import_static_mesh, import_texture, import_sound TCP commands.
Includes full Blender → UE cross-tool pipeline test.
"""

import sys
import os
import json
import time

# Set up import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from blueprint_client import ArcwrightClient, BlueprintLLMError
from blender_mcp.blender_client import BlenderClient, BlenderClientError

EXPORTS_DIR = "C:/Arcwright/exports"


def run_tests():
    results = []

    def test(name, fn):
        try:
            fn()
            results.append(("PASS", name))
            print(f"  PASS: {name}")
        except Exception as e:
            results.append(("FAIL", name, str(e)))
            print(f"  FAIL: {name} — {e}")

    print("=" * 60)
    print("B31-B33 Asset Import Tests")
    print("=" * 60)

    # ── Phase 1: Blender export ──
    print("\n--- Phase 1: Blender mesh creation + FBX export ---")
    blender = None
    fbx_path = os.path.join(EXPORTS_DIR, "test_cone.fbx")

    try:
        blender = BlenderClient()
        blender.connect()

        def t_blender_clear():
            blender.clear_scene()
        test("Blender clear scene", t_blender_clear)

        def t_blender_create_cone():
            # Use create_custom_mesh to avoid Blender 5.0 active_object issue
            import math
            verts = [[0, 0, 1.5]]  # tip
            n = 16
            for i in range(n):
                a = 2 * math.pi * i / n
                verts.append([math.cos(a), math.sin(a), 0])
            faces = []
            for i in range(n):
                faces.append([0, i + 1, (i % n) + 2 if (i + 1) < n else 1])
            # bottom face
            faces.append(list(range(1, n + 1)))
            blender.create_custom_mesh("TestCone", verts, faces)
        test("Blender create cone", t_blender_create_cone)

        def t_blender_material():
            blender.create_material("TestGreen", color=[0.1, 0.9, 0.3, 1.0], roughness=0.3)
            blender.assign_material("TestCone", "TestGreen")
        test("Blender create + assign material", t_blender_material)

        def t_blender_export():
            blender.export_fbx(fbx_path)
            assert os.path.exists(fbx_path), f"FBX not found at {fbx_path}"
            size = os.path.getsize(fbx_path)
            print(f"    FBX size: {size:,} bytes")
            assert size > 100, "FBX file too small"
        test("Blender export FBX", t_blender_export)

    except (ConnectionRefusedError, OSError) as e:
        print(f"  SKIP Blender tests — not connected: {e}")
        # Try to find an existing FBX for UE tests
        if not os.path.exists(fbx_path):
            print("  No test FBX available. Creating minimal placeholder won't work.")
            print("  Will test error handling only.")
    finally:
        if blender:
            blender.close()

    # ── Phase 2: UE import tests ──
    print("\n--- Phase 2: UE asset import commands ---")
    ue = ArcwrightClient()

    # B31: import_static_mesh
    if os.path.exists(fbx_path):
        def t_import_mesh():
            r = ue.import_static_mesh(fbx_path, "SM_TestCone")
            data = r.get("data", {})
            assert data.get("asset_path"), f"No asset_path in response: {r}"
            print(f"    asset: {data['asset_path']}")
            print(f"    verts: {data.get('vertices', '?')}, tris: {data.get('triangles', '?')}")
        test("B31 import_static_mesh (FBX)", t_import_mesh)

    # B31: error - missing file
    def t_import_mesh_missing():
        try:
            ue.import_static_mesh("C:/nonexistent/missing.fbx", "SM_Missing")
            assert False, "Should have raised"
        except BlueprintLLMError as e:
            assert "not found" in str(e).lower() or "File not found" in str(e), f"Unexpected error: {e}"
    test("B31 import_static_mesh error (missing file)", t_import_mesh_missing)

    # B31: error - bad extension (must be an existing file to test ext check)
    bad_ext_path = os.path.join(EXPORTS_DIR, "bad_extension.txt")
    with open(bad_ext_path, "w") as f:
        f.write("not a mesh")

    def t_import_mesh_badext():
        try:
            ue.import_static_mesh(bad_ext_path, "SM_Bad")
            assert False, "Should have raised"
        except BlueprintLLMError as e:
            assert "unsupported" in str(e).lower() or "Unsupported" in str(e), f"Unexpected error: {e}"
    test("B31 import_static_mesh error (bad extension)", t_import_mesh_badext)

    # B32: import_texture — create a test PNG
    test_png = os.path.join(EXPORTS_DIR, "test_texture.png")
    try:
        # Create a minimal 4x4 red PNG
        import struct, zlib
        def make_png(w, h, r, g, b):
            raw = b""
            for _ in range(h):
                raw += b"\x00"  # filter byte
                for _ in range(w):
                    raw += bytes([r, g, b])
            compressed = zlib.compress(raw)

            def chunk(tag, data):
                c = tag + data
                return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

            ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
            return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")

        with open(test_png, "wb") as f:
            f.write(make_png(64, 64, 255, 0, 0))

        def t_import_texture():
            r = ue.import_texture(test_png, "T_TestRed")
            data = r.get("data", {})
            assert data.get("asset_path"), f"No asset_path: {r}"
            print(f"    asset: {data['asset_path']}")
            print(f"    size: {data.get('width', '?')}x{data.get('height', '?')}")
        test("B32 import_texture (PNG)", t_import_texture)
    except Exception as e:
        print(f"  SKIP texture test (PNG creation failed): {e}")

    # B32: error - missing file
    def t_import_texture_missing():
        try:
            ue.import_texture("C:/nonexistent/missing.png", "T_Missing")
            assert False, "Should have raised"
        except BlueprintLLMError as e:
            assert "not found" in str(e).lower() or "File not found" in str(e)
    test("B32 import_texture error (missing file)", t_import_texture_missing)

    # B33: import_sound — create a minimal WAV
    test_wav = os.path.join(EXPORTS_DIR, "test_sound.wav")
    try:
        import struct
        sample_rate = 44100
        duration = 0.5
        num_samples = int(sample_rate * duration)
        import math
        samples = bytes()
        for i in range(num_samples):
            # 440Hz sine wave
            val = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            samples += struct.pack("<h", val)

        with open(test_wav, "wb") as f:
            data_size = len(samples)
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + data_size))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
            f.write(b"data")
            f.write(struct.pack("<I", data_size))
            f.write(samples)

        def t_import_sound():
            r = ue.import_sound(test_wav, "SFX_TestTone")
            data = r.get("data", {})
            assert data.get("asset_path"), f"No asset_path: {r}"
            print(f"    asset: {data['asset_path']}")
            print(f"    duration: {data.get('duration', '?')}s, channels: {data.get('channels', '?')}")
        test("B33 import_sound (WAV)", t_import_sound)
    except Exception as e:
        print(f"  SKIP sound test (WAV creation failed): {e}")

    # B33: error - missing file
    def t_import_sound_missing():
        try:
            ue.import_sound("C:/nonexistent/missing.wav", "SFX_Missing")
            assert False, "Should have raised"
        except BlueprintLLMError as e:
            assert "not found" in str(e).lower() or "File not found" in str(e)
    test("B33 import_sound error (missing file)", t_import_sound_missing)

    # ── Phase 3: Cross-tool pipeline (Blender → UE) ──
    print("\n--- Phase 3: Full cross-tool pipeline ---")

    crystal_fbx = os.path.join(EXPORTS_DIR, "health_crystal.fbx")

    try:
        blender2 = BlenderClient()
        blender2.connect()

        def t_pipeline_blender():
            import math
            blender2.clear_scene()
            # Create crystal cone via custom mesh (avoids Blender 5.0 active_object issue)
            verts = [[0, 0, 1.2]]  # tip
            n = 16
            for i in range(n):
                a = 2 * math.pi * i / n
                verts.append([0.5 * math.cos(a), 0.5 * math.sin(a), 0])
            faces = []
            for i in range(n):
                faces.append([0, i + 1, (i % n) + 2 if (i + 1) < n else 1])
            faces.append(list(range(1, n + 1)))
            blender2.create_custom_mesh("HealthCrystal", verts, faces)
            blender2.create_material("CrystalGreen", color=[0.1, 0.9, 0.3, 1.0], roughness=0.2)
            blender2.assign_material("HealthCrystal", "CrystalGreen")
            blender2.export_fbx(crystal_fbx)
            assert os.path.exists(crystal_fbx), "Crystal FBX not exported"
            print(f"    FBX: {os.path.getsize(crystal_fbx):,} bytes")
        test("Pipeline: Blender create + export crystal", t_pipeline_blender)

        blender2.close()
    except (ConnectionRefusedError, OSError):
        print("  SKIP pipeline Blender step — not connected")

    if os.path.exists(crystal_fbx):
        def t_pipeline_import():
            r = ue.import_static_mesh(crystal_fbx, "SM_HealthCrystal")
            data = r.get("data", {})
            assert data.get("asset_path"), f"Import failed: {r}"
            print(f"    UE asset: {data['asset_path']}")
            print(f"    verts: {data.get('vertices', '?')}, tris: {data.get('triangles', '?')}")
        test("Pipeline: UE import SM_HealthCrystal", t_pipeline_import)

        def t_pipeline_blueprint():
            # Delete existing BP if any
            try:
                ue.delete_blueprint("BP_CrystalPickup")
            except BlueprintLLMError:
                pass

            # Create a simple Blueprint from DSL
            dsl = """BLUEPRINT: BP_CrystalPickup
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Crystal Pickup Ready"]
EXEC n1.Then -> n2.Execute"""
            r = ue.create_blueprint_from_dsl(dsl)
            assert r.get("status") == "ok" or r.get("data"), f"BP creation failed: {r}"
            print(f"    BP created")
        test("Pipeline: Create BP_CrystalPickup", t_pipeline_blueprint)

        def t_pipeline_component():
            r = ue.add_component(
                "BP_CrystalPickup", "StaticMesh", "CrystalMesh",
                properties={"mesh": "/Game/Arcwright/Meshes/SM_HealthCrystal"}
            )
            data = r.get("data", {})
            print(f"    Component: {data.get('component_name', '?')}")
        test("Pipeline: Add mesh component with imported mesh", t_pipeline_component)

        def t_pipeline_spawn():
            # Delete old actor if exists
            try:
                ue.delete_actor("Crystal_1")
            except BlueprintLLMError:
                pass

            r = ue.spawn_actor_at(
                "/Game/Arcwright/Generated/BP_CrystalPickup",
                location={"x": 0, "y": 500, "z": 92},
                label="Crystal_1"
            )
            data = r.get("data", {})
            print(f"    Spawned: {data.get('label', '?')} at ({data.get('location', {})})")
        test("Pipeline: Spawn crystal actor", t_pipeline_spawn)

        def t_pipeline_save():
            ue.save_all()
            print("    Saved all")
        test("Pipeline: Save all", t_pipeline_save)

    ue.close()

    # ── Summary ──
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    total = len(results)
    print(f"Results: {passed}/{total} PASS, {failed} FAIL")

    if failed:
        print("\nFailures:")
        for r in results:
            if r[0] == "FAIL":
                print(f"  - {r[1]}: {r[2]}")

    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
