"""Fix game Blueprints: remove Cast To Character (fails with DefaultPawn),
wire overlap events directly to PrintString."""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError


def fix_blueprint(client, bp_name, print_message):
    """Remove Cast To Character from a BP, wire overlap directly to first PrintString."""
    print(f"\n=== Fixing {bp_name} ===")

    resp = client.get_blueprint_info(bp_name)
    data = resp["data"]
    nodes = data["nodes"]
    conns = data.get("connections", [])

    # Find nodes by title
    cast_id = None
    overlap_id = None
    for n in nodes:
        title = n.get("title", "")
        if "Cast To Character" in title:
            cast_id = n["id"]
        if "ActorBeginOverlap" in title:
            overlap_id = n["id"]

    if not cast_id:
        print(f"  No Cast To Character found - skipping")
        return
    if not overlap_id:
        print(f"  No ActorBeginOverlap found - skipping")
        return

    print(f"  Found Cast={cast_id}, Overlap={overlap_id}")

    # Remove all connections involving the Cast node
    for c in conns:
        if c["source_node"] == cast_id or c["target_node"] == cast_id:
            try:
                client.remove_connection(
                    bp_name,
                    c["source_node"], c["source_pin"],
                    c["target_node"], c["target_pin"],
                )
                print(f"  Removed: {c['source_node']}.{c['source_pin']} -> {c['target_node']}.{c['target_pin']}")
            except BlueprintLLMError as e:
                print(f"  Skip: {e}")

    # Remove the Cast node
    client.remove_node(bp_name, cast_id)
    print(f"  Removed Cast node")

    # Re-query (node indices changed after removal)
    resp = client.get_blueprint_info(bp_name)
    nodes = resp["data"]["nodes"]

    overlap_id = None
    print_nodes = []
    destroy_id = None
    for n in nodes:
        title = n.get("title", "")
        if "ActorBeginOverlap" in title:
            overlap_id = n["id"]
        if "Print String" in title:
            print_nodes.append(n["id"])
        if "Destroy Actor" in title:
            destroy_id = n["id"]

    print(f"  After removal: overlap={overlap_id}, prints={print_nodes}, destroy={destroy_id}")

    # Wire: Overlap -> first PrintString
    if overlap_id and print_nodes:
        client.add_connection(bp_name, overlap_id, "then", print_nodes[0], "execute")
        print(f"  Wired: {overlap_id}.then -> {print_nodes[0]}.execute")
        client.set_node_param(bp_name, print_nodes[0], "InString", print_message)
        print(f'  Set InString = "{print_message}"')

    # Wire: PrintString -> DestroyActor (for BP_Pickup)
    if destroy_id and print_nodes:
        # Check if already wired
        resp2 = client.get_blueprint_info(bp_name)
        existing = resp2["data"].get("connections", [])
        already_wired = any(
            c["source_node"] == print_nodes[0] and c["target_node"] == destroy_id
            for c in existing
        )
        if not already_wired:
            client.add_connection(bp_name, print_nodes[0], "then", destroy_id, "execute")
            print(f"  Wired: {print_nodes[0]}.then -> {destroy_id}.execute")

    # Final state
    resp = client.get_blueprint_info(bp_name)
    final_conns = resp["data"].get("connections", [])
    print(f"  Result: compiled={resp['data']['compiled']}, connections={len(final_conns)}")
    for c in final_conns:
        print(f"    {c['source_node']}.{c['source_pin']} -> {c['target_node']}.{c['target_pin']}")


def fix_hazard_endoverlap(client):
    """Re-wire BP_HazardZone EndOverlap -> second PrintString."""
    print("\n=== Fixing BP_HazardZone EndOverlap ===")
    resp = client.get_blueprint_info("BP_HazardZone")
    nodes = resp["data"]["nodes"]
    conns = resp["data"].get("connections", [])

    end_overlap_id = None
    print_nodes = []
    for n in nodes:
        title = n.get("title", "")
        if "ActorEndOverlap" in title:
            end_overlap_id = n["id"]
        if "Print String" in title:
            print_nodes.append(n["id"])

    if end_overlap_id and len(print_nodes) >= 2:
        # Check if already wired
        already = any(c["source_node"] == end_overlap_id for c in conns)
        if not already:
            client.add_connection("BP_HazardZone", end_overlap_id, "then", print_nodes[1], "execute")
            print(f"  Wired: {end_overlap_id}.then -> {print_nodes[1]}.execute")
            client.set_node_param("BP_HazardZone", print_nodes[1], "InString", "Left hazard zone")
            print('  Set InString = "Left hazard zone"')
        else:
            print("  EndOverlap already wired")


def respawn_actors(client):
    """Delete and re-spawn all game actors to pick up BP changes."""
    print("\n=== Re-spawning actors ===")

    for label in ["Pickup_1", "Pickup_2", "Pickup_3", "HazardZone", "VictoryZone"]:
        client.delete_actor(label)

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


def main():
    client = ArcwrightClient(timeout=60)

    try:
        # Fix all 3 BPs
        fix_blueprint(client, "BP_Pickup", "Picked up!")
        fix_blueprint(client, "BP_HazardZone", "Entering hazard zone!")
        fix_blueprint(client, "BP_VictoryZone", "Victory! You win!")

        # Re-wire HazardZone EndOverlap
        fix_hazard_endoverlap(client)

        # Re-spawn actors
        respawn_actors(client)

        # Final summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        for bp in ["BP_Pickup", "BP_HazardZone", "BP_VictoryZone"]:
            resp = client.get_blueprint_info(bp)
            d = resp["data"]
            has_cast = any("Cast" in n.get("title", "") for n in d["nodes"])
            print(f"  {bp}: compiled={d['compiled']}, cast_removed={not has_cast}, conns={len(d.get('connections', []))}")

        print("\nDone! Hit Play to test. Overlaps should fire with DefaultPawn now.")
        print("TIP: Click the viewport when Play starts to capture the mouse.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
