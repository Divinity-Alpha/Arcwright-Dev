#!/usr/bin/env python3
"""
build_temple_walls.py — Build temple architecture from room definitions.

Creates wall, floor, and ceiling geometry using BasicShapes/Cube instances.
Spawns wall segments with doorway gaps, per-room floor/ceiling panels.
Optionally repositions torches to wall-adjacent positions.

Usage:
    python scripts/build_temple_walls.py [--no-torches] [--no-ceiling]
"""

import sys
import os
import json
import time
import tempfile
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.mcp_client.blueprint_client import ArcwrightClient

# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
WALL_HEIGHT = 500        # wall panel height (Z), units
WALL_THICKNESS = 20      # wall panel thickness, units
DOOR_WIDTH = 300         # doorway gap width, units
FLOOR_THICKNESS = 10     # floor/ceiling panel thickness, units
CEILING_Z = 500          # ceiling panel center Z position
MIN_SEGMENT = 30         # skip wall segments shorter than this

WALL_COLOR = {"r": 0.35, "g": 0.30, "b": 0.25}   # warm stone brown
FLOOR_COLOR = {"r": 0.25, "g": 0.22, "b": 0.18}  # darker stone

# ═══════════════════════════════════════════════════════════════════
# Room Definitions (from TempleEscape game design doc)
#
# center: (x, y) world position of room center
# size:   (width_x, depth_y) in units
# doors:  {direction: offset} — offset from room center along wall axis
#         direction = north|south|east|west
#         offset = 0 means centered on wall
# ═══════════════════════════════════════════════════════════════════
ROOMS = [
    {"name": "StartRoom",      "center": (0, 0),         "size": (1200, 1200), "doors": {"north": 0}},
    {"name": "Corridor1",      "center": (0, 1000),      "size": (400, 1000),  "doors": {"south": 0, "north": 0, "west": -500, "east": 500}},
    {"name": "Key1Room",       "center": (-1500, 1000),  "size": (1000, 1000), "doors": {"east": 0}},
    {"name": "Key2Room",       "center": (1500, 1000),   "size": (1000, 1000), "doors": {"west": 0}},
    {"name": "MainHall",       "center": (0, 2000),      "size": (2000, 1000), "doors": {"south": 0, "north": 0, "west": -500, "east": 500}},
    {"name": "Key3Room",       "center": (-1000, 3000),  "size": (800, 800),   "doors": {"east": 400}},
    {"name": "HazardCorridor", "center": (1000, 3000),   "size": (400, 800),   "doors": {"west": -400}},
    {"name": "Corridor3",      "center": (0, 3500),      "size": (400, 500),   "doors": {"south": 0, "north": 0}},
    {"name": "ExitRoom",       "center": (0, 4000),      "size": (800, 800),   "doors": {"south": 0}},
]


# ═══════════════════════════════════════════════════════════════════
# Geometry Generation (reusable)
# ═══════════════════════════════════════════════════════════════════

def _split_wall_with_doors(wall_start, wall_end, door_positions):
    """Split a wall range into segments, leaving gaps for doors.

    Args:
        wall_start: start coordinate along wall axis
        wall_end:   end coordinate along wall axis
        door_positions: list of absolute door-center positions on that axis

    Returns:
        list of (segment_start, segment_end) tuples
    """
    half_door = DOOR_WIDTH / 2

    # Build gap ranges, clamped to wall bounds
    gaps = []
    for dp in door_positions:
        gs = max(dp - half_door, wall_start)
        ge = min(dp + half_door, wall_end)
        if ge > gs:
            gaps.append((gs, ge))
    gaps.sort()

    # Merge overlapping gaps
    merged = []
    for g in gaps:
        if merged and g[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], g[1]))
        else:
            merged.append(list(g))

    # Collect solid wall segments between gaps
    segments = []
    pos = wall_start
    for gs, ge in merged:
        if gs - pos >= MIN_SEGMENT:
            segments.append((pos, gs))
        pos = ge
    if wall_end - pos >= MIN_SEGMENT:
        segments.append((pos, wall_end))

    return segments


def generate_wall_segments(room):
    """Generate wall geometry definitions for one room.

    Returns list of dicts: {pos, scale, type, dir, room}
    """
    cx, cy = room["center"]
    sx, sy = room["size"]
    doors = room.get("doors", {})
    segments = []
    half_sx, half_sy = sx / 2, sy / 2
    wall_z = WALL_HEIGHT / 2

    # ── Walls running along X (North / South) ──
    x_start, x_end = cx - half_sx, cx + half_sx
    for side, y_pos, door_key in [("N", cy + half_sy, "north"),
                                   ("S", cy - half_sy, "south")]:
        door_list = [cx + doors[door_key]] if door_key in doors else []
        for ss, se in _split_wall_with_doors(x_start, x_end, door_list):
            length = se - ss
            segments.append({
                "pos": ((ss + se) / 2, y_pos, wall_z),
                "scale": (length / 100, WALL_THICKNESS / 100, WALL_HEIGHT / 100),
                "type": "wall",
                "dir": side,
            })

    # ── Walls running along Y (East / West) ──
    y_start, y_end = cy - half_sy, cy + half_sy
    for side, x_pos, door_key in [("E", cx + half_sx, "east"),
                                   ("W", cx - half_sx, "west")]:
        door_list = [cy + doors[door_key]] if door_key in doors else []
        for ss, se in _split_wall_with_doors(y_start, y_end, door_list):
            length = se - ss
            segments.append({
                "pos": (x_pos, (ss + se) / 2, wall_z),
                "scale": (WALL_THICKNESS / 100, length / 100, WALL_HEIGHT / 100),
                "type": "wall",
                "dir": side,
            })

    return segments


def generate_floor_ceiling(room, include_ceiling=True):
    """Generate floor and ceiling panel definitions for one room."""
    cx, cy = room["center"]
    sx, sy = room["size"]
    thick = FLOOR_THICKNESS / 100

    panels = [{
        "pos": (cx, cy, FLOOR_THICKNESS / 2),
        "scale": (sx / 100, sy / 100, thick),
        "type": "floor",
    }]

    if include_ceiling:
        panels.append({
            "pos": (cx, cy, CEILING_Z),
            "scale": (sx / 100, sy / 100, thick),
            "type": "ceiling",
        })

    return panels


def build_rooms_from_layout(client, rooms_config, wall_bp="BP_WallBlock",
                            floor_bp="BP_FloorBlock", include_ceiling=True):
    """Reusable utility — spawn wall/floor/ceiling geometry from room definitions.

    Can be used by any game that defines rooms as center+size+doors.

    Args:
        client:          ArcwrightClient instance
        rooms_config:    list of room dicts {name, center, size, doors}
        wall_bp:         Blueprint name for walls and ceilings (must exist)
        floor_bp:        Blueprint name for floors (must exist)
        include_ceiling: whether to spawn ceiling panels

    Returns:
        dict with counts: {walls, floors, ceilings, total}
    """
    counts = {"walls": 0, "floors": 0, "ceilings": 0}
    wall_class = f"/Game/Arcwright/Generated/{wall_bp}.{wall_bp}"
    floor_class = f"/Game/Arcwright/Generated/{floor_bp}.{floor_bp}"

    for room in rooms_config:
        rn = room["name"]
        print(f"  Building {rn}...")

        # ── Walls ──
        wall_segs = generate_wall_segments(room)
        for i, seg in enumerate(wall_segs):
            px, py, pz = seg["pos"]
            sx, sy, sz = seg["scale"]
            label = f"Wall_{rn}_{seg['dir']}_{i}"

            client.send_command("spawn_actor_at", {
                "class": wall_class,
                "label": label,
                "location": {"x": px, "y": py, "z": pz},
                "scale": {"x": sx, "y": sy, "z": sz},
            })
            counts["walls"] += 1

        # ── Floor + Ceiling ──
        for panel in generate_floor_ceiling(room, include_ceiling):
            px, py, pz = panel["pos"]
            sx, sy, sz = panel["scale"]
            ptype = panel["type"]
            label = f"{ptype.capitalize()}_{rn}"
            bp_class = floor_class if ptype == "floor" else wall_class

            client.send_command("spawn_actor_at", {
                "class": bp_class,
                "label": label,
                "location": {"x": px, "y": py, "z": pz},
                "scale": {"x": sx, "y": sy, "z": sz},
            })
            counts[f"{ptype}s"] += 1

    counts["total"] = counts["walls"] + counts["floors"] + counts["ceilings"]
    return counts


# ═══════════════════════════════════════════════════════════════════
# Setup Helpers
# ═══════════════════════════════════════════════════════════════════

def create_block_bp(client, bp_name, material_path):
    """Create a minimal Actor Blueprint with a Cube mesh and material."""
    # Write minimal IR to a temp file (needs at least one node to avoid crash)
    ir = {
        "metadata": {"name": bp_name, "parent_class": "Actor"},
        "variables": [],
        "nodes": [
            {
                "id": "N1",
                "dsl_type": "Event_ReceiveBeginPlay",
                "ue_class": "UK2Node_Event",
                "ue_event": "ReceiveBeginPlay",
                "params": {}
            }
        ],
        "connections": [],
    }
    ir_path = os.path.join(tempfile.gettempdir(), f"{bp_name}.blueprint.json")
    with open(ir_path, "w") as f:
        json.dump(ir, f)

    # Delete existing (ignore errors if it doesn't exist)
    try:
        client.send_command("delete_blueprint", {"name": bp_name})
        time.sleep(0.3)
    except Exception:
        pass

    # Import empty Actor BP
    result = client.send_command("import_from_ir", {"path": ir_path})
    if result.get("status") != "ok":
        print(f"  WARNING: import_from_ir for {bp_name}: {result.get('message', 'unknown error')}")
        return False
    time.sleep(0.3)

    # Add Cube mesh component
    result = client.send_command("add_component", {
        "blueprint": bp_name,
        "component_type": "StaticMesh",
        "component_name": "BlockMesh",
        "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube"},
    })
    if result.get("status") != "ok":
        print(f"  WARNING: add_component for {bp_name}: {result.get('message', 'unknown error')}")
        return False
    time.sleep(0.2)

    # Apply material to the mesh component
    result = client.send_command("apply_material", {
        "blueprint": bp_name,
        "component_name": "BlockMesh",
        "material_path": material_path,
    })
    if result.get("status") != "ok":
        print(f"  WARNING: apply_material for {bp_name}: {result.get('message', 'unknown error')}")
    time.sleep(0.2)

    # Compile to lock in changes
    client.send_command("compile_blueprint", {"name": bp_name})
    time.sleep(0.2)

    mat_name = material_path.split("/")[-1]
    print(f"  Created {bp_name} (Cube mesh + {mat_name})")
    return True


def cleanup_old_geometry(client):
    """Delete existing wall/floor/ceiling actors from previous runs."""
    result = client.send_command("get_actors", {})
    actors = result.get("data", {}).get("actors", [])

    prefixes = ("Wall_", "Floor_", "Ceiling_")
    to_delete = [a["label"] for a in actors
                 if any(a.get("label", "").startswith(p) for p in prefixes)]

    if to_delete:
        print(f"Cleaning up {len(to_delete)} old geometry actors...")
        for label in to_delete:
            client.send_command("delete_actor", {"label": label})
        time.sleep(0.5)
    else:
        print("No old geometry to clean up.")
    return len(to_delete)


def reposition_torches(client, rooms):
    """Move torch actors to wall-adjacent positions inside rooms."""
    result = client.send_command("get_actors", {})
    actors = result.get("data", {}).get("actors", [])

    torches = [a for a in actors if "torch" in a.get("label", "").lower()]
    if not torches:
        print("No torches found to reposition.")
        return 0

    # Generate wall-adjacent torch positions (one per wall per room, inset 50 units)
    inset = 50
    torch_z = 200  # mid-wall height
    positions = []

    for room in rooms:
        cx, cy = room["center"]
        sx, sy = room["size"]
        hx, hy = sx / 2, sy / 2

        positions.extend([
            (cx, cy + hy - inset, torch_z),   # north wall
            (cx, cy - hy + inset, torch_z),   # south wall
            (cx + hx - inset, cy, torch_z),   # east wall
            (cx - hx + inset, cy, torch_z),   # west wall
        ])

    moved = 0
    for i, torch in enumerate(torches):
        if i >= len(positions):
            break
        px, py, pz = positions[i]
        client.send_command("set_actor_transform", {
            "label": torch["label"],
            "location": {"x": px, "y": py, "z": pz},
        })
        moved += 1

    print(f"Repositioned {moved}/{len(torches)} torches to wall positions.")
    return moved


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Build temple walls from room definitions")
    parser.add_argument("--no-torches", action="store_true", help="Skip torch repositioning")
    parser.add_argument("--no-ceiling", action="store_true", help="Skip ceiling panels")
    args = parser.parse_args()

    client = ArcwrightClient()

    try:
        # ── Connect ──
        print("Connecting to UE Editor...")
        health = client.health_check()
        print(f"Connected to {health.get('data', {}).get('server', 'UE')}\n")

        # ── Step 1: Clean up old geometry ──
        deleted = cleanup_old_geometry(client)

        # ── Step 2: Create materials (delete first to avoid partial-load crash) ──
        print("\nCreating materials...")
        for mat_name in ["MAT_StoneWall", "MAT_StoneFloor"]:
            try:
                client.send_command("delete_blueprint", {"name": mat_name})
                time.sleep(0.3)
            except Exception:
                pass
        client.send_command("create_simple_material", {
            "name": "MAT_StoneWall", "color": WALL_COLOR,
        })
        client.send_command("create_simple_material", {
            "name": "MAT_StoneFloor", "color": FLOOR_COLOR,
        })
        print("  MAT_StoneWall  (warm stone brown)")
        print("  MAT_StoneFloor (dark stone)")

        # ── Step 3: Create block Blueprints ──
        print("\nCreating block Blueprints...")
        wall_ok = create_block_bp(
            client, "BP_WallBlock",
            "/Game/Arcwright/Materials/MAT_StoneWall",
        )
        floor_ok = create_block_bp(
            client, "BP_FloorBlock",
            "/Game/Arcwright/Materials/MAT_StoneFloor",
        )

        if not (wall_ok and floor_ok):
            print("\nERROR: Failed to create block Blueprints. Aborting.")
            return

        # ── Step 4: Build all rooms ──
        print(f"\nBuilding {len(ROOMS)} rooms...")
        counts = build_rooms_from_layout(
            client, ROOMS,
            wall_bp="BP_WallBlock",
            floor_bp="BP_FloorBlock",
            include_ceiling=not args.no_ceiling,
        )

        print(f"\n{'=' * 50}")
        print(f"  GEOMETRY COMPLETE")
        print(f"  Walls:    {counts['walls']}")
        print(f"  Floors:   {counts['floors']}")
        print(f"  Ceilings: {counts['ceilings']}")
        print(f"  Total:    {counts['total']}")
        print(f"{'=' * 50}")

        # ── Step 5: Reposition torches ──
        if not args.no_torches:
            print("\nRepositioning torches...")
            reposition_torches(client, ROOMS)

        # ── Step 6: Save ──
        print("\nSaving all...")
        client.send_command("save_all", {})

        print("\nDone! Temple architecture built.")
        print(f"  {len(ROOMS)} rooms, {counts['total']} geometry actors spawned.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
