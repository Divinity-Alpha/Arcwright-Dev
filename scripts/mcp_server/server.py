"""
Arcwright MCP Server — stdio bridge to UE5 Command Server.

Architecture:
    Claude Desktop -> MCP Protocol (stdio) -> This Server -> TCP -> UE Command Server

This is a thin wrapper. All Blueprint creation logic lives in the UE plugin.
The DSL parser runs locally. The TCP client (blueprint_client.py) handles comms.

Usage:
    python scripts/mcp_server/server.py          # stdio mode (for Claude Desktop)
    python scripts/mcp_server/server.py --test    # quick self-test

Claude Desktop config (add to claude_desktop_config.json):
    {
      "mcpServers": {
        "blueprint-llm": {
          "command": "C:\\\\Arcwright\\\\venv\\\\Scripts\\\\python.exe",
          "args": ["C:\\\\Arcwright\\\\scripts\\\\mcp_server\\\\server.py"]
        }
      }
    }
"""
import sys
import os
import json
import logging
from typing import Optional

# Logging to stderr only — stdout is the MCP protocol channel
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("blueprintllm-mcp")

# Set up import paths for blueprint_client and dsl_parser
_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_MCP_CLIENT_DIR = os.path.join(_SCRIPTS_DIR, "mcp_client")
_PARSER_DIR = os.path.join(_SCRIPTS_DIR, "dsl_parser")
for p in [_SCRIPTS_DIR, _MCP_CLIENT_DIR, _PARSER_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from mcp.server.fastmcp import FastMCP
from blueprint_client import ArcwrightClient, BlueprintLLMError

# Pre-flight checks (non-blocking — adds warnings to responses)
try:
    from preflight_checks import check_blueprint, check_spawn, check_bt, check_ir_file, Status
    _HAS_PREFLIGHT = True
except ImportError:
    _HAS_PREFLIGHT = False

def _preflight_warnings(report) -> list:
    """Extract warning/fail messages from a preflight report."""
    if not report:
        return []
    return [str(r) for r in report.results if r.status != Status.PASS]

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "arcwright",
    instructions=(
        "Create and manage Unreal Engine 5 Blueprints via the Arcwright "
        "command server. Supports DSL-to-Blueprint creation, IR file import, "
        "level actor management, and Blueprint inspection."
    ),
)

# Default connection settings — overridable via env vars
UE_HOST = os.environ.get("BLUEPRINTLLM_HOST", "localhost")
UE_PORT = int(os.environ.get("BLUEPRINTLLM_PORT", "13377"))
UE_TIMEOUT = float(os.environ.get("BLUEPRINTLLM_TIMEOUT", "60"))

def _get_client() -> ArcwrightClient:
    """Create a fresh TCP connection to the UE command server."""
    return ArcwrightClient(host=UE_HOST, port=UE_PORT, timeout=UE_TIMEOUT)

def _safe_call(fn, tool_name: str = ""):
    """Execute fn(client) with proper connection management and error handling."""
    try:
        client = _get_client()
    except (ConnectionRefusedError, OSError, TimeoutError) as e:
        return json.dumps({
            "error": f"Cannot connect to UE command server at {UE_HOST}:{UE_PORT}. "
                     f"Is Unreal Editor running with the Arcwright plugin? ({e})"
        })
    try:
        result = fn(client)
        return json.dumps(result, indent=2)
    except BlueprintLLMError as e:
        return json.dumps({"error": str(e)})
    except (ConnectionError, OSError) as e:
        return json.dumps({"error": f"Connection lost during command: {e}"})
    finally:
        client.close()

# ---------------------------------------------------------------------------
# Tier Gating
# ---------------------------------------------------------------------------

# Free-tier commands — must match the set in TierGating.h

# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def health_check() -> str:
    """Check if the Unreal Engine command server is running and responsive.

    Call this first before any other tool to verify the UE Editor is reachable.
    A successful response confirms the Arcwright plugin is loaded and the TCP
    command server is accepting connections on localhost:13377.

    Parameters:
        (none)

    Returns:
        {"server": "Arcwright", "version": "1.0", "engine": "5.7.3", "commands": 150}

    Example:
        health_check()

    Notes:
        - If this fails with a connection error, ensure:
          1. Unreal Editor is running with the Arcwright plugin loaded
          2. The TCP command server is active on port 13377 (auto-starts on plugin load)
          3. No firewall is blocking localhost:13377
        - The "commands" field shows the total number of TCP commands the plugin supports
        - This tool has zero side effects -- safe to call repeatedly for polling
    """
    return _safe_call(lambda c: c.health_check())

@mcp.tool()
def create_blueprint_from_dsl(dsl_text: str, name: str = "") -> str:
    """Create a compiled Blueprint in Unreal Engine from raw Arcwright DSL text.

    Parses the DSL locally, converts to IR JSON, sends to UE, and creates a fully-wired
    Blueprint with nodes, connections, and variables. Pre-flight validation runs automatically.

    The DSL format:
        BLUEPRINT: BP_HelloWorld
        PARENT: Actor
        GRAPH: EventGraph
        NODE n1: Event_BeginPlay
        NODE n2: PrintString [InString="Hello World"]
        EXEC n1.Then -> n2.Execute

    Parameters:
        dsl_text (str): Complete DSL text describing the Blueprint. Must include BLUEPRINT,
            PARENT, GRAPH, NODE, and connection (EXEC/DATA) lines.
        name (str): Optional Blueprint name override. If empty, the name is extracted
            from the "BLUEPRINT:" line in the DSL.

    Returns:
        {"status": "ok", "blueprint": "BP_HelloWorld", "nodes_created": 2,
         "connections_wired": 1, "compile_status": "success", "preflight_warnings": []}

    Example:
        create_blueprint_from_dsl("BLUEPRINT: BP_Hello\\nPARENT: Actor\\nGRAPH: EventGraph\\nNODE n1: Event_BeginPlay\\nNODE n2: PrintString [InString=\\"Hello\\"]\\nEXEC n1.Then -> n2.Execute")

    Notes:
        - For importing from a .blueprint.json file on disk, use import_blueprint_ir instead
        - For Behavior Trees, use create_behavior_tree_from_dsl (different DSL format)
        - For Data Tables, use create_data_table_from_dsl (different DSL format)
        - Pre-flight checks warn about invalid node types but do not block creation
        - If a Blueprint with the same name exists, it is deleted and recreated
    """
    # Pre-flight: validate DSL before sending to UE
    warnings = []
    if _HAS_PREFLIGHT:
        report = check_blueprint(dsl_text)
        warnings = _preflight_warnings(report)
        if warnings:
            log.warning("Blueprint pre-flight warnings: %s", "; ".join(warnings))

    def _run(client):
        result = client.create_blueprint_from_dsl(
            dsl_text, name=name if name else None
        )
        if warnings and isinstance(result, dict):
            result["preflight_warnings"] = warnings
        return result
    return _safe_call(_run)

@mcp.tool()
def create_blueprint(name: str, parent_class: str = "Actor", variables: list = None) -> str:
    """Create a new Blueprint asset in the UE5 Content Browser.

    Creates a compiled Blueprint class that can be spawned into levels.
    Use add_nodes_batch to add logic nodes, then add_connections_batch to wire them.

    Parameters:
        name: Blueprint name (e.g. "BP_HealthPickup"). Created at /Game/Arcwright/Generated/{name}
        parent_class: UE parent class. Common: "Actor" (default), "Character", "Pawn",
                      "PlayerController", "GameModeBase", "AIController"
        variables: Optional list of variables. Each: {"name": "Health", "type": "Float", "default": "100.0"}
                   Types: Bool, Int, Float, String, Vector, Rotator, Name

    Returns:
        {"status": "ok", "blueprint_name": "BP_HealthPickup", "asset_path": "...", "compiled": true}

    Example:
        create_blueprint("BP_Enemy", "Character", [{"name": "Health", "type": "Float", "default": "100"}])
    """
    def _run(client):
        params = {"name": name, "parent_class": parent_class}
        if variables:
            params["variables"] = variables
        return client.send_command("create_blueprint", params)
    return _safe_call(_run)

@mcp.tool()
def import_blueprint_ir(ir_path: str) -> str:
    """Import a .blueprint.json IR file to create a fully-wired Blueprint in Unreal Engine.

    The IR (Intermediate Representation) is the JSON format produced by the DSL parser.
    It contains the Blueprint name, parent class, variables, nodes with positions/parameters,
    and all execution + data connections. This is the most powerful Blueprint creation method --
    it produces complete node graphs with full wiring. Pre-flight validation runs automatically.

    Parameters:
        ir_path (str): Absolute file path to the .blueprint.json file.
            Example: "C:/Arcwright/test_ir/BP_Coin.blueprint.json"

    Returns:
        {"status": "ok", "blueprint": "BP_Coin", "nodes_created": 8, "connections_wired": 12,
         "compile_status": "success", "warnings": []}

    Example:
        import_blueprint_ir("C:/Arcwright/test_ir/BP_HealthPickup.blueprint.json")

    Notes:
        - The IR file must use "src_node"/"src_pin"/"dst_node"/"dst_pin" field names for
          connections (NOT "source_node"/"target_node" -- wrong names silently fail)
        - If a Blueprint with the same name exists, it is deleted and recreated (Rule 8)
        - Pre-flight checks block on structural errors (malformed JSON, missing required fields)
          but allow warnings (e.g. unknown node types) to proceed
        - For simple Blueprints without node graphs, use create_blueprint_from_dsl instead
        - For Behavior Trees or Data Tables, use create_behavior_tree_from_dsl or
          create_data_table_from_dsl respectively

    Common mistakes:
        - Using a relative path instead of absolute path
        - Using "source_node"/"target_node" in the IR file instead of "src_node"/"dst_node"
    """
    # Pre-flight: validate IR file format
    warnings = []
    if _HAS_PREFLIGHT:
        report = check_ir_file(ir_path)
        warnings = _preflight_warnings(report)
        # Block on failures (wrong format = guaranteed crash)
        fails = [str(r) for r in report.results if r.status == Status.FAIL]
        if fails:
            return json.dumps({
                "error": "IR pre-flight BLOCKED: " + "; ".join(fails),
                "preflight_warnings": warnings,
            })

    def _run(client):
        result = client.import_from_ir(ir_path)
        if warnings and isinstance(result, dict):
            result["preflight_warnings"] = warnings
        return result
    return _safe_call(_run)

@mcp.tool()
def get_blueprint_info(name: str) -> str:
    """Query an existing Blueprint's full structure including nodes, connections, variables, and compile status.

    Use this to inspect a Blueprint before modifying it with add_node, add_connection,
    set_node_param, or modify_blueprint. Also useful for verifying that a Blueprint was
    created correctly after import_blueprint_ir or create_blueprint_from_dsl.

    Parameters:
        name (str): Blueprint asset name. Searches /Game/Arcwright/Generated/ first,
            then falls back to the full asset registry.
            Examples: "BP_HelloWorld", "BP_Enemy", "BP_HealthPickup"

    Returns:
        {
            "name": "BP_HelloWorld",
            "parent_class": "Actor",
            "compiled": true,
            "nodes": [{"id": "node_0", "type": "UK2Node_Event", "name": "ReceiveBeginPlay", "pins": [...]}],
            "connections": [{"source_node": "node_0", "source_pin": "Then", "target_node": "node_1", "target_pin": "execute"}],
            "variables": [{"name": "Health", "type": "float", "default": "100"}]
        }

    Example:
        get_blueprint_info("BP_Enemy")

    Notes:
        - Node IDs use "node_N" format (0-indexed). Use these IDs with add_connection,
          remove_node, and set_node_param
        - The "compiled" field indicates whether the last compile succeeded
        - Variables include name, type, and current default value
        - For a lighter-weight query on placed actors, use get_actor_properties instead
        - For detailed Blueprint inspection including CDO properties, use get_blueprint_details
    """
    def _run(client):
        return client.get_blueprint_info(name)
    return _safe_call(_run)

@mcp.tool()
def spawn_actor(
    actor_class: str,
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0,
    scale_x: float = 1.0, scale_y: float = 1.0, scale_z: float = 1.0,
    label: str = "",
) -> str:
    """Spawn an actor into the current Unreal Engine level at a specified location.

    This is the primary tool for placing objects in the game world. Use it after creating
    Blueprints, setting up lighting, and creating materials.

    Parameters:
        actor_class (str): Native class name or Blueprint asset path.
            Native classes: "StaticMeshActor", "PointLight", "SpotLight", "DirectionalLight",
                "CameraActor", "PlayerStart", "TargetPoint", "TriggerBox", "TriggerSphere",
                "PostProcessVolume", "ExponentialHeightFog", "SkyLight", "SkyAtmosphere"
            Blueprint classes: Use short name "BP_Enemy" (auto-resolves from /Game/Arcwright/Generated/)
                or full path "/Game/Arcwright/Generated/BP_Enemy.BP_Enemy"
        x (float): World X position in centimeters. UE uses cm -- 100 = 1 meter. Default: 0.0.
        y (float): World Y position in centimeters. Default: 0.0.
        z (float): World Z position in centimeters. Positive = up. Default: 0.0.
        pitch (float): Rotation pitch in degrees. Default: 0.0.
        yaw (float): Rotation yaw in degrees. Default: 0.0.
        roll (float): Rotation roll in degrees. Default: 0.0.
        scale_x (float): X scale multiplier. Default: 1.0.
        scale_y (float): Y scale multiplier. Default: 1.0.
        scale_z (float): Z scale multiplier. Default: 1.0.
        label (str): Display name in the Outliner. Auto-generated from class name if empty.

    Returns:
        {"status": "ok", "label": "BP_Enemy_1", "class": "BP_Enemy_C",
         "location": {"x": 200.0, "y": 0.0, "z": 50.0}}

    Example:
        spawn_actor("StaticMeshActor", x=0, y=0, z=0, scale_x=100, scale_y=100, scale_z=1, label="Floor")
        spawn_actor("BP_Enemy", x=500, y=200, z=50, yaw=180, label="Enemy_1")
        spawn_actor("PointLight", x=0, y=0, z=300, label="MainLight")

    Notes:
        - The returned "label" is what you pass to move_actor, delete_actor, set_actor_material,
          find_actors, attach_actor_to, and all other actor-targeting tools
        - For Blueprint classes, the plugin auto-resolves short names from /Game/Arcwright/Generated/
        - Use set_actor_material AFTER spawning to apply materials to placed actors (SCS template
          materials may not persist on spawned instances)
        - For spawning many actors at once, use spawn_actor_grid, spawn_actor_circle, or spawn_actor_line
        - For StaticMeshActor, set the mesh via set_component_property after spawning, or use the
          "properties" field in the underlying TCP command

    Common mistakes:
        - Forgetting that UE uses centimeters (a floor plane at scale 100,100,1 = 100 meters)
        - Passing 0-255 color values to lights instead of 0.0-1.0 range
        - Not calling set_actor_material after spawning if a material is needed
    """
    # Pre-flight: validate class path
    warnings = []
    if _HAS_PREFLIGHT:
        report = check_spawn(actor_class)
        warnings = _preflight_warnings(report)
        for w in warnings:
            log.warning("Spawn pre-flight: %s", w)

    def _run(client):
        result = client.spawn_actor_at(
            actor_class=actor_class,
            location={"x": x, "y": y, "z": z},
            rotation={"pitch": pitch, "yaw": yaw, "roll": roll},
            scale={"x": scale_x, "y": scale_y, "z": scale_z},
            label=label if label else None,
        )
        if warnings and isinstance(result, dict):
            result["preflight_warnings"] = warnings
        return result
    return _safe_call(_run)

@mcp.tool()
def get_actors(class_filter: str = "") -> str:
    """List all actors currently placed in the Unreal Engine level.

    Returns every actor's label, class, location, rotation, and scale. Use this to
    discover what exists in the level before modifying, spawning, or deleting actors.

    Parameters:
        class_filter (str): Optional class name substring to filter results.
            Examples: "Light" (all lights), "BP_Enemy" (all enemy instances),
            "StaticMeshActor" (all mesh actors). Empty string = return all actors.

    Returns:
        {"actors": [
            {"label": "Floor", "class": "StaticMeshActor", "location": {"x":0,"y":0,"z":0},
             "rotation": {"pitch":0,"yaw":0,"roll":0}, "scale": {"x":100,"y":100,"z":1}},
            ...
        ], "count": 48}

    Example:
        get_actors()                     # all actors
        get_actors("PointLight")         # only point lights
        get_actors("BP_")               # all Blueprint-based actors

    Notes:
        - For more advanced filtering (by tag, component, material, proximity), use find_actors
        - Actor labels are unique identifiers used by move_actor, delete_actor, set_actor_material, etc.
        - This returns ALL actors including editor infrastructure (WorldSettings, etc.)
        - For a count-only summary by class, use get_level_info instead
    """
    def _run(client):
        return client.get_actors(
            class_filter=class_filter if class_filter else None
        )
    return _safe_call(_run)

@mcp.tool()
def move_actor(
    label: str,
    x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None,
    pitch: Optional[float] = None, yaw: Optional[float] = None, roll: Optional[float] = None,
    scale_x: Optional[float] = None, scale_y: Optional[float] = None, scale_z: Optional[float] = None,
) -> str:
    """Move, rotate, or scale a placed actor in the level. Only provided values are changed;
    omitted values remain at their current setting.

    Parameters:
        label (str): Actor label in the Outliner (as returned by spawn_actor or get_actors).
        x (float, optional): New world X position in cm. Unchanged if not provided.
        y (float, optional): New world Y position in cm. Unchanged if not provided.
        z (float, optional): New world Z position in cm. Unchanged if not provided.
        pitch (float, optional): New rotation pitch in degrees. Unchanged if not provided.
        yaw (float, optional): New rotation yaw in degrees. Unchanged if not provided.
        roll (float, optional): New rotation roll in degrees. Unchanged if not provided.
        scale_x (float, optional): New X scale. Unchanged if not provided.
        scale_y (float, optional): New Y scale. Unchanged if not provided.
        scale_z (float, optional): New Z scale. Unchanged if not provided.

    Returns:
        {"status": "ok", "label": "Enemy_1", "location": {"x":500,"y":200,"z":50},
         "rotation": {"pitch":0,"yaw":180,"roll":0}, "scale": {"x":1,"y":1,"z":1}}

    Example:
        move_actor("Enemy_1", x=500, y=200)          # move to new XY, keep Z
        move_actor("Floor", scale_x=200, scale_y=200) # scale without moving
        move_actor("Turret_1", yaw=90)                # rotate only

    Notes:
        - This sets absolute world-space values, not relative offsets. For relative movement
          of multiple actors, use batch_move_actors with mode="relative"
        - For bulk repositioning, use batch_move_actors or batch_scale_actors instead
        - The label must match exactly (case-sensitive) as shown by get_actors
    """
    def _run(client):
        location = None
        if x is not None or y is not None or z is not None:
            location = {}
            if x is not None: location["x"] = x
            if y is not None: location["y"] = y
            if z is not None: location["z"] = z

        rotation = None
        if pitch is not None or yaw is not None or roll is not None:
            rotation = {}
            if pitch is not None: rotation["pitch"] = pitch
            if yaw is not None: rotation["yaw"] = yaw
            if roll is not None: rotation["roll"] = roll

        scale = None
        if scale_x is not None or scale_y is not None or scale_z is not None:
            scale = {}
            if scale_x is not None: scale["x"] = scale_x
            if scale_y is not None: scale["y"] = scale_y
            if scale_z is not None: scale["z"] = scale_z

        return client.set_actor_transform(
            label=label, location=location, rotation=rotation, scale=scale
        )
    return _safe_call(_run)

@mcp.tool()
def add_node(
    blueprint: str,
    node_type: str,
    node_id: str = "",
    params: str = "",
    pos_x: float = 0.0,
    pos_y: float = 0.0,
) -> str:
    """Add a single node to an existing Blueprint's EventGraph.

    Adds one node at a time. For complex Blueprints with many nodes and connections,
    use create_blueprint_from_dsl or import_blueprint_ir instead.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_HelloWorld").
        node_type (str): DSL node type name. Common types:
            Events: "Event_BeginPlay", "Event_ActorBeginOverlap", "Event_Tick", "Event_AnyDamage"
            Flow control: "Branch", "Sequence", "FlipFlop", "DoOnce", "Gate", "MultiGate"
            Loops: "ForLoop", "WhileLoop", "ForEachLoop"
            Functions: "PrintString", "Delay", "SetTimerByFunctionName", "SpawnActor",
                       "GetAllActorsOfClass", "DestroyActor", "SetActorLocation"
            Variables: "GetVar", "SetVar" (requires existing variable on the BP)
            Math: "Add_DoubleDouble", "Subtract_DoubleDouble", "Multiply_DoubleDouble"
            Or a full UE function path: "/Script/Engine.KismetSystemLibrary:PrintString"
        node_id (str): Optional custom ID for referencing this node in add_connection.
            Auto-generated GUID if empty.
        params (str): Optional JSON string of pin default values.
            Example: '{"Duration": "2.0"}' or '{"InString": "Hello World"}'
        pos_x (float): Graph editor X position (cosmetic). Default: 0.0.
        pos_y (float): Graph editor Y position (cosmetic). Default: 0.0.

    Returns:
        {"status": "ok", "node_id": "<guid>", "node_type": "PrintString", "blueprint": "BP_HelloWorld"}

    Example:
        add_node("BP_Hello", "Event_BeginPlay", node_id="beginplay")
        add_node("BP_Hello", "PrintString", node_id="print1", params='{"InString": "Hello World"}')
        add_node("BP_Hello", "Delay", params='{"Duration": "3.0"}')

    Notes:
        - After adding nodes, use add_connection to wire them together
        - Node types are resolved via the DSL node map (179 types + 24 aliases)
        - For Event nodes, use the "Event_" prefix (Event_BeginPlay, Event_Tick, etc.)
        - For UE functions not in the node map, use the full path format:
          "/Script/<Module>.<Class>:<FunctionName>"
        - VariableGet/Set nodes cannot be created via add_node -- use import_blueprint_ir instead
        - For adding many nodes at once, create_blueprint_from_dsl is more efficient

    Common mistakes:
        - Trying to create VariableGet/Set via add_node (use IR import instead)
        - Using Float function names instead of Double (UE 5.x uses Double: "Add_DoubleDouble")
    """
    import json as _json
    parsed_params = _json.loads(params) if params else None
    def _run(client):
        return client.add_node(blueprint, node_type, node_id=node_id,
                               params=parsed_params, pos_x=pos_x, pos_y=pos_y)
    return _safe_call(_run)

@mcp.tool()
def remove_node(blueprint: str, node_id: str) -> str:
    """Remove a node and all its connections from a Blueprint's EventGraph.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_HelloWorld").
        node_id (str): Node identifier -- either a GUID returned by add_node, or a "node_N"
            index from get_blueprint_info (e.g. "node_0", "node_3").

    Returns:
        {"status": "ok", "removed": "node_3", "blueprint": "BP_HelloWorld"}

    Example:
        remove_node("BP_Hello", "node_2")

    Notes:
        - All pin connections to/from this node are broken automatically before removal
        - Use get_blueprint_info to find node IDs before removing
        - Removing a node does not remove variables or components -- only the graph node
    """
    def _run(client):
        return client.remove_node(blueprint, node_id)
    return _safe_call(_run)

@mcp.tool()
def add_connection(
    blueprint: str,
    source_node: str,
    source_pin: str,
    target_node: str,
    target_pin: str,
) -> str:
    """Wire two pins together in a Blueprint's EventGraph.

    Uses TryCreateConnection which auto-inserts conversion nodes when needed
    (e.g. Float-to-String, Int-to-Float). Pin names support DSL aliases.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_HelloWorld").
        source_node (str): Source node ID (GUID from add_node, or "node_N" from get_blueprint_info).
        source_pin (str): Output pin name on the source node. Common names and aliases:
            Execution: "Then" (exec output), "Execute" (exec input)
            Branch: "True", "False", "C" (Condition)
            PrintString: "I" (InString)
            Math: "A", "B" (inputs), "ReturnValue" (output)
            Sequence: "A", "B", "C" (exec outputs, alias for "then 0", "then 1", etc.)
        target_node (str): Target node ID.
        target_pin (str): Input pin name on the target node.

    Returns:
        {"status": "ok", "connection": "node_0.Then -> node_1.execute"}

    Example:
        add_connection("BP_Hello", "node_0", "Then", "node_1", "execute")    # exec flow
        add_connection("BP_Hello", "node_2", "ReturnValue", "node_3", "A")   # data flow

    Notes:
        - Pin name aliases are resolved automatically (11 resolution strategies)
        - TryCreateConnection auto-inserts type conversion nodes when types differ
        - Use get_blueprint_info to discover available pins on each node
        - For removing a connection, use remove_connection with the same parameters
    """
    def _run(client):
        return client.add_connection(blueprint, source_node, source_pin,
                                     target_node, target_pin)
    return _safe_call(_run)

@mcp.tool()
def remove_connection(
    blueprint: str,
    source_node: str,
    source_pin: str,
    target_node: str,
    target_pin: str,
) -> str:
    """Disconnect two previously-wired pins in a Blueprint's EventGraph.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_HelloWorld").
        source_node (str): Source node ID (GUID or "node_N" index).
        source_pin (str): Output pin name on the source node (same aliases as add_connection).
        target_node (str): Target node ID.
        target_pin (str): Input pin name on the target node.

    Returns:
        {"status": "ok", "disconnected": "node_0.Then -> node_1.execute"}

    Example:
        remove_connection("BP_Hello", "node_0", "Then", "node_1", "execute")

    Notes:
        - Idempotent -- disconnecting pins that aren't connected returns success
        - Use get_blueprint_info to inspect current connections before modifying
    """
    def _run(client):
        return client.remove_connection(blueprint, source_node, source_pin,
                                        target_node, target_pin)
    return _safe_call(_run)

@mcp.tool()
def add_nodes_batch(blueprint: str, nodes: str) -> str:
    """Add multiple nodes to a Blueprint in a single call. Fault-tolerant: each node
    succeeds or fails independently. Single compile at end (much faster than individual add_node calls).

    This is the PRIMARY method for building complex Blueprints step-by-step.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_HealthPickup").
        nodes (str): JSON array of node definitions. Each node:
            {"node_type": "PrintString", "node_id": "print1", "params": {"InString": "Hello"}, "pos_x": 200, "pos_y": 0}
            Only node_type is required. node_id auto-generated if omitted.

    Returns:
        {"succeeded": 5, "failed": 0, "total": 5, "compiled": true,
         "results": [{"success": true, "node_id": "<guid>", "node_type": "PrintString", "pins": [...]}]}

    Example:
        add_nodes_batch("BP_Hello", '[
            {"node_type": "Event_BeginPlay", "node_id": "begin"},
            {"node_type": "PrintString", "node_id": "print1", "params": {"InString": "Hello"}},
            {"node_type": "Delay", "node_id": "delay1", "params": {"Duration": "2.0"}},
            {"node_type": "PrintString", "node_id": "print2", "params": {"InString": "World"}}
        ]')

    Notes:
        - Use with add_connections_batch for efficient Blueprint construction
        - Each failed node includes an error message; other nodes still succeed
        - Returns pin lists per node for use in add_connections_batch
        - Supports all node types from add_node (Events, Flow, Loops, Functions, Variables, Math)
    """
    import json as _json
    parsed_nodes = _json.loads(nodes) if isinstance(nodes, str) else nodes
    def _run(client):
        return client.add_nodes_batch(blueprint, parsed_nodes)
    return _safe_call(_run)

@mcp.tool()
def add_connections_batch(blueprint: str, connections: str) -> str:
    """Wire multiple connections in a Blueprint in a single call. Fault-tolerant: each connection
    succeeds or fails independently. Single compile at end.

    On pin-not-found errors, returns available_source_pins or available_target_pins to help debug.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_HealthPickup").
        connections (str): JSON array of connection definitions. Each:
            {"source_node": "begin", "source_pin": "Then", "target_node": "print1", "target_pin": "execute"}

    Returns:
        {"succeeded": 3, "failed": 0, "total": 3, "compiled": true,
         "results": [{"success": true, "source_node": "begin", "source_pin": "Then", ...}]}

    Example:
        add_connections_batch("BP_Hello", '[
            {"source_node": "begin", "source_pin": "Then", "target_node": "print1", "target_pin": "execute"},
            {"source_node": "print1", "source_pin": "Then", "target_node": "delay1", "target_pin": "execute"},
            {"source_node": "delay1", "source_pin": "Completed", "target_node": "print2", "target_pin": "execute"}
        ]')

    Notes:
        - Uses same pin name aliases as add_connection (11 resolution strategies)
        - TryCreateConnection auto-inserts type conversion nodes
        - Failed connections include pin mismatch details (available pins listed)
        - Node IDs can be GUIDs from add_nodes_batch or "node_N" indices from get_blueprint_info
    """
    import json as _json
    parsed_conns = _json.loads(connections) if isinstance(connections, str) else connections
    def _run(client):
        return client.add_connections_batch(blueprint, parsed_conns)
    return _safe_call(_run)

@mcp.tool()
def validate_blueprint(name: str) -> str:
    """Check a Blueprint for common issues without modifying it. Non-destructive analysis.

    Checks performed:
    - unconnected_exec_input: Nodes with no execution input (will never run)
    - orphan_node: Nodes with zero connections (completely disconnected)
    - unconnected_data_input: Data pins with no connection or default value
    - compile_error: Blueprint has compilation errors

    Parameters:
        name (str): Blueprint asset name (e.g. "BP_HealthPickup").

    Returns:
        {"valid": true, "error_count": 0, "warning_count": 2, "info_count": 1,
         "issues": [{"severity": "warning", "type": "orphan_node", "node_id": "node_5",
                     "node_title": "Print String", "message": "Node 'Print String' is completely disconnected"}]}

    Example:
        validate_blueprint("BP_HealthPickup")

    Notes:
        - Does NOT modify the Blueprint -- read-only analysis
        - Severity levels: "error" (must fix), "warning" (likely problem), "info" (suggestion)
        - Use after add_nodes_batch + add_connections_batch to verify correctness
        - "valid" is true when error_count == 0 (warnings/info don't affect validity)
    """
    def _run(client):
        return client.validate_blueprint(name)
    return _safe_call(_run)

@mcp.tool()
def get_capabilities() -> str:
    """Get a summary of all Arcwright capabilities — command counts, categories, version info.

    Returns a complete inventory of TCP commands and MCP tools organized by category.
    Useful for understanding what Arcwright can do and planning multi-step workflows.

    Returns:
        {"tcp_commands": 154, "mcp_tools": 186, "categories": {"blueprint_creation": [...], ...}}
    """
    def _run(client):
        return client.get_capabilities()
    return _safe_call(_run)

@mcp.tool()
def get_stats() -> str:
    """Get Arcwright usage statistics — session and lifetime.

    Returns session stats (commands this session, blueprints created, actors spawned,
    session duration) and lifetime stats (total commands, success rate, estimated time
    saved, first use date, total sessions). Stats persist across editor restarts.

    Returns:
        JSON with session {} and lifetime {} stat objects.
    """
    def _run(client):
        return client.get_stats()
    return _safe_call(_run)

@mcp.tool()
def reset_stats(scope: str = "session") -> str:
    """Reset Arcwright usage statistics.

    Parameters:
        scope: "session" to reset current session counters, "lifetime" to reset all
               persistent stats (totals, time saved, first use date). Default: "session".

    Returns:
        Confirmation of which scope was reset.
    """
    def _run(client):
        return client.reset_stats(scope)
    return _safe_call(_run)

@mcp.tool()
def get_node_reference(node_type: str) -> str:
    """Get complete reference for a Blueprint node type — pins, category, description.

    Use this before creating Blueprints to understand what pins a node has and how to wire it.
    Resolves aliases automatically (e.g. "Print" → "PrintString", "GetVar" → "VariableGet").
    Supports dynamic CastTo<X> patterns (e.g. "CastToCharacter").

    Parameters:
        node_type (str): Node type name. Examples:
            "SetTimerByFunctionName" — timer that calls a custom event
            "Branch" — if/else flow control
            "ForLoop" — loop from FirstIndex to LastIndex
            "Event_ActorBeginOverlap" — overlap event
            "SpawnActorFromClass" — spawn an actor
            "PrintString" — debug output

    Returns:
        {"node_type": "SetTimerByFunctionName", "category": "Timing",
         "description": "Starts a timer...",
         "input_pins": [{"name": "FunctionName", "type": "String", "description": "Name of..."}],
         "output_pins": [...], "aliases": ["TimerByFunction"]}

    Notes:
        - This uses local DSL reference data — no UE Editor connection needed
        - Pin descriptions help you understand what values each pin expects
        - The aliases field shows alternative names that resolve to this node
    """
    try:
        from node_reference import get_reference
        ref = get_reference(node_type)
        if ref is None:
            return json.dumps({"status": "error", "message": f"Unknown node type: {node_type}. Use list_node_types to see all available types."})
        return json.dumps({"status": "ok", "data": ref})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def list_node_types(category: str = "") -> str:
    """List all available Blueprint node types organized by category.

    Returns the complete catalog of ~130 canonical node types that can be used in Blueprints.
    Use this to discover what nodes are available before building a Blueprint.

    Parameters:
        category (str): Optional category filter. If empty, returns all categories.
            Available categories: Events, Flow Control, Loops, Casting, Variables, Switch,
            Debug, Timing, Actor, Gameplay, Physics, Math — Float, Math — Int,
            Math — Comparison, Math — Boolean, Math — Trig, Vector, Rotator, String,
            UI / Widget, Array, Movement, Trace, Misc

    Returns:
        {"total_types": 130, "categories": {"Events": [{"node_type": "Event_BeginPlay",
         "description": "Fires once when..."}], ...}}

    Notes:
        - This uses local DSL reference data — no UE Editor connection needed
        - Use get_node_reference(node_type) to get detailed pin information for a specific node
        - Aliases and duplicates are filtered out — only canonical names shown
    """
    try:
        from node_reference import list_types
        result = list_types()
        if category:
            filtered = {k: v for k, v in result["categories"].items() if k == category}
            count = sum(len(v) for v in filtered.values())
            result = {"total_types": count, "categories": filtered}
        return json.dumps({"status": "ok", "data": result})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def set_node_param(blueprint: str, node_id: str, pin_name: str, value: str) -> str:
    """Set a pin's default value on an existing node in a Blueprint.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_HelloWorld").
        node_id (str): Node ID (GUID or "node_N" index from get_blueprint_info).
        pin_name (str): Pin name to set. DSL aliases supported (e.g. "I" for InString,
            "Duration" for Delay, "ActorClass" for GetAllActorsOfClass).
        value (str): Value as string. Format depends on pin type:
            Strings: "Hello World"
            Numbers: "100.0"
            Bools: "true" or "false"
            Object/Class pins: Full asset path e.g. "/Game/Arcwright/Generated/BP_Enemy.BP_Enemy_C"

    Returns:
        {"status": "ok", "node_id": "node_1", "pin": "InString", "value": "Hello World"}

    Example:
        set_node_param("BP_Hello", "node_1", "InString", "Hello World")
        set_node_param("BP_Hello", "node_2", "Duration", "3.0")
        set_node_param("BP_Hello", "node_3", "ActorClass", "/Game/Arcwright/Generated/BP_Enemy.BP_Enemy_C")

    Notes:
        - For Object/Class pins, uses LoadObject + DefaultObject (not DefaultValue string)
        - Pin name aliases are resolved using the same 11-strategy resolution as add_connection
        - For setting Blueprint variable defaults (not pin defaults), use set_variable_default instead
    """
    def _run(client):
        return client.set_node_param(blueprint, node_id, pin_name, value)
    return _safe_call(_run)

@mcp.tool()
def set_variable_default(blueprint: str, variable_name: str, default_value: str) -> str:
    """Set a Blueprint variable's default value in the Class Defaults.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_Enemy").
        variable_name (str): Variable name exactly as it appears in get_blueprint_info
            (e.g. "Health", "Speed", "IsActive").
        default_value (str): Default value as a string. Format by type:
            Float: "100.0"   Int: "5"   Bool: "true"   String: "Hello"
            Vector: "100.0,200.0,50.0"   Rotator: "0.0,90.0,0.0"

    Returns:
        {"status": "ok", "blueprint": "BP_Enemy", "variable": "Health", "default": "200"}

    Example:
        set_variable_default("BP_Enemy", "Health", "200")
        set_variable_default("BP_Enemy", "IsHostile", "true")

    Notes:
        - The variable must already exist on the Blueprint. Use modify_blueprint to add variables first
        - For setting defaults on multiple BPs at once, use batch_set_variable instead
        - For setting pin defaults on nodes (not Blueprint variables), use set_node_param
    """
    def _run(client):
        return client.set_variable_default(blueprint, variable_name, default_value)
    return _safe_call(_run)

@mcp.tool()
def add_component(
    blueprint: str,
    component_type: str,
    component_name: str,
    parent: str = "",
    properties: str = "",
) -> str:
    """Add a component to a Blueprint's SimpleConstructionScript (SCS).

    Components are the physical building blocks of a Blueprint: collision volumes,
    meshes, lights, audio sources, cameras, etc. They define the actor's physical
    presence in the world. The Blueprint must already exist.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_Pickup", "BP_Enemy").
        component_type (str): One of the supported component types:
            "BoxCollision" -- UBoxComponent for box-shaped collision/overlap detection
            "SphereCollision" -- USphereComponent for sphere-shaped collision/overlap
            "CapsuleCollision" -- UCapsuleComponent for capsule collision (characters)
            "StaticMesh" -- UStaticMeshComponent for visible 3D geometry
            "PointLight" -- UPointLightComponent for omnidirectional light
            "SpotLight" -- USpotLightComponent for directional cone light
            "Audio" -- UAudioComponent for sound playback
            "Arrow" -- UArrowComponent for direction indicator (editor only)
            "Scene" -- USceneComponent for empty transform parent
            "Camera" -- UCameraComponent for camera views
            "SpringArm" -- USpringArmComponent for camera boom
        component_name (str): Unique name within this Blueprint (e.g. "PickupCollision", "EnemyMesh").
        parent (str): Parent component name to attach to. Defaults to DefaultSceneRoot if empty.
        properties (str): Optional JSON string of component-specific properties.
            BoxCollision: '{"extent": {"x":50,"y":50,"z":50}, "generate_overlap_events": true}'
            SphereCollision: '{"radius": 100.0, "generate_overlap_events": true}'
            PointLight: '{"intensity": 5000, "light_color": {"r":1,"g":0.8,"b":0.3}, "attenuation_radius": 500}'
            StaticMesh: '{"mesh": "/Engine/BasicShapes/Sphere.Sphere"}'
            All types: '{"location": {"x":0,"y":0,"z":50}, "rotation": {...}, "scale": {"x":1,"y":1,"z":1}}'

    Returns:
        {"status": "ok", "component": "PickupCollision", "type": "BoxCollision", "blueprint": "BP_Pickup"}

    Example:
        add_component("BP_Pickup", "SphereCollision", "OverlapSphere", properties='{"radius": 150, "generate_overlap_events": true}')
        add_component("BP_Pickup", "StaticMesh", "PickupMesh", properties='{"mesh": "/Engine/BasicShapes/Sphere.Sphere"}')
        add_component("BP_Torch", "PointLight", "TorchLight", parent="TorchMesh", properties='{"intensity": 3000}')

    Notes:
        - Components added via SCS update the Blueprint asset. Already-placed actors in the
          level do NOT pick up changes -- you must delete and re-spawn them
        - Use get_components to list existing components before adding
        - For adding the same component to multiple BPs at once, use batch_add_component
        - Component names must be unique within a Blueprint -- duplicates cause an error
        - Light colors use 0.0-1.0 range, NOT 0-255

    Common mistakes:
        - Using generate_overlap_events without also setting collision_profile to "OverlapAllDynamic"
        - Expecting already-spawned actors to update after add_component (they don't -- re-spawn)
        - Passing light color values in 0-255 range instead of 0.0-1.0
    """
    import json as _json
    parsed_props = _json.loads(properties) if properties else None
    def _run(client):
        return client.add_component(blueprint, component_type, component_name,
                                    parent=parent, properties=parsed_props)
    return _safe_call(_run)

@mcp.tool()
def get_components(blueprint: str) -> str:
    """List all components in a Blueprint's SimpleConstructionScript.

    Returns each component's name, class, and parent component.

    Args:
        blueprint: Blueprint asset name (e.g. "BP_Pickup").
    """
    def _run(client):
        return client.get_components(blueprint)
    return _safe_call(_run)

@mcp.tool()
def set_component_property(
    blueprint: str,
    component_name: str,
    property_name: str,
    value: str,
) -> str:
    """Set a property on a component in a Blueprint's SimpleConstructionScript.

    Modifies the component template on the Blueprint asset. The Blueprint is recompiled
    automatically after the change.

    Parameters:
        blueprint (str): Blueprint asset name (e.g. "BP_Pickup").
        component_name (str): Component name in the SCS (e.g. "PickupMesh"). Use get_components to find names.
        property_name (str): Property to set. Supported properties by component type:
            Any SceneComponent: "relative_location", "relative_rotation", "relative_scale", "visibility"
            StaticMesh: "static_mesh" (asset path), "material" (material asset path)
            BoxCollision: "box_extent", "generate_overlap_events", "collision_profile_name"
            SphereCollision: "sphere_radius", "generate_overlap_events"
            CapsuleCollision: "capsule_radius", "capsule_half_height"
            PointLight/SpotLight: "intensity", "light_color", "attenuation_radius"
            Camera: "field_of_view", "aspect_ratio"
            SpringArm: "target_arm_length", "socket_offset", "use_pawn_control_rotation"
            Any component: Also supports generic UPROPERTY reflection (bool, float, int, string)
        value (str): JSON-encoded value. Format depends on property type:
            Vectors: '{"x": 0, "y": 0, "z": 100}'
            Floats: '5000.0'
            Bools: 'true'
            Strings: '"OverlapAllDynamic"'
            Colors: '{"r": 1, "g": 0.8, "b": 0.3}'

    Returns:
        {"status": "ok", "blueprint": "BP_Pickup", "component": "PickupMesh", "property": "static_mesh"}

    Example:
        set_component_property("BP_Pickup", "PickupMesh", "static_mesh", '"/Engine/BasicShapes/Sphere.Sphere"')
        set_component_property("BP_Torch", "TorchLight", "intensity", '3000')
        set_component_property("BP_Torch", "TorchLight", "light_color", '{"r":1,"g":0.78,"b":0.31}')
        set_component_property("BP_Player", "Camera", "field_of_view", '90')

    Notes:
        - Changes apply to the Blueprint template, not to already-spawned actor instances.
          Re-spawn actors to see updated component properties
        - For setting materials on placed actors (not BP templates), use set_actor_material instead
        - Light colors use 0.0-1.0 range (NOT 0-255)
        - Generic UPROPERTY reflection works for any discoverable property via FindPropertyByName
    """
    import json as _json
    parsed_value = _json.loads(value)
    def _run(client):
        return client.set_component_property(blueprint, component_name, property_name, parsed_value)
    return _safe_call(_run)

@mcp.tool()
def create_material_instance(
    name: str,
    parent: str,
    scalar_params: str = "",
    vector_params: str = "",
) -> str:
    """Create a MaterialInstanceConstant asset derived from a parent material.

    WARNING: MaterialInstance vector parameters do NOT work with UE 5.7 Substrate rendering.
    BaseColor set via vector params will be silently ignored. For simple colored materials,
    use create_simple_material instead (works with Substrate). For textured materials,
    use create_textured_material.

    The asset is saved to /Game/Arcwright/Materials/<name>.

    Parameters:
        name (str): Asset name (e.g. "MI_GoldPickup", "MI_ShinyMetal"). No path prefix needed.
        parent (str): Parent material full asset path.
            Common parents: "/Engine/BasicShapes/BasicShapeMaterial"
        scalar_params (str): Optional JSON string of scalar parameter overrides.
            Example: '{"Metallic": 0.8, "Roughness": 0.2}'
        vector_params (str): Optional JSON string of vector parameter overrides.
            Example: '{"BaseColor": {"r":1,"g":0.8,"b":0,"a":1}}'
            WARNING: Does not work with Substrate rendering -- use create_simple_material instead.

    Returns:
        {"status": "ok", "material": "MI_GoldPickup", "path": "/Game/Arcwright/Materials/MI_GoldPickup"}

    Example:
        create_material_instance("MI_Shiny", "/Engine/BasicShapes/BasicShapeMaterial",
                                  scalar_params='{"Metallic": 1.0, "Roughness": 0.1}')

    Notes:
        - PREFER create_simple_material for solid colors -- it works with Substrate rendering
        - PREFER create_textured_material for textured surfaces
        - This tool is best for advanced material instances where you need specific scalar params
          (Metallic, Roughness, Opacity) on a known parent material
        - Apply the material via set_actor_material (placed actors) or apply_material (BP templates)
        - If the asset already exists and is partially loaded, SavePackage may crash the editor.
          Delete the existing material first via delete_blueprint if recreating

    Common mistakes:
        - Setting BaseColor via vector_params with Substrate rendering (silently fails)
        - Not using the full path when applying: "/Game/Arcwright/Materials/MI_GoldPickup"
    """
    import json as _json
    parsed_scalar = _json.loads(scalar_params) if scalar_params else None
    parsed_vector = _json.loads(vector_params) if vector_params else None
    def _run(client):
        return client.create_material_instance(name, parent,
                                                scalar_params=parsed_scalar,
                                                vector_params=parsed_vector)
    return _safe_call(_run)

@mcp.tool()
def create_simple_material(
    name: str,
    r: float = 1.0, g: float = 1.0, b: float = 1.0,
    emissive_strength: float = 0.0,
) -> str:
    """Create a UMaterial with a solid color. Works with UE 5.7 Substrate rendering.

    PREFERRED over create_material_instance for colored materials — MaterialInstance
    vector params don't work with Substrate rendering mode.

    Common colors (r, g, b):
        Gold: (1.0, 0.84, 0.0)    Red: (0.8, 0.1, 0.1)    Green: (0.1, 0.8, 0.2)
        Blue: (0.2, 0.4, 1.0)     White: (1,1,1)           Black: (0.02, 0.02, 0.02)
        Concrete: (0.5, 0.5, 0.45) Wood: (0.4, 0.26, 0.13)

    Saved to /Game/Arcwright/Materials/<name>. Apply via set_actor_material or apply_material.

    Args:
        name: Asset name (e.g. "MAT_Green", "MAT_Gold"). No path prefix needed.
        r: Red channel (0.0-1.0). NOT 0-255.
        g: Green channel (0.0-1.0).
        b: Blue channel (0.0-1.0).
        emissive_strength: Glow multiplier (0=none, 1.0=subtle, 5.0=strong neon).
    """
    def _run(client):
        return client.create_simple_material(
            name, {"r": r, "g": g, "b": b},
            emissive_strength=emissive_strength)
    return _safe_call(_run)

@mcp.tool()
def create_textured_material(
    name: str,
    texture_path: str,
    roughness: float = 0.5,
    metallic: float = 0.0,
    tiling: float = 1.0,
) -> str:
    """Create a UMaterial with a texture sample connected to Base Color.

    Use this after importing a texture with import_texture. The texture is
    sampled and connected to the material's BaseColor input, with optional
    roughness, metallic, and UV tiling controls.

    texture_path can be a full UE asset path OR a friendly name from the
    texture library (e.g. "stone_wall", "gold_metal", "lava").

    Args:
        name: Material asset name (e.g. "MAT_StoneWall").
        texture_path: UE asset path OR texture library friendly name.
        roughness: Surface roughness (0=mirror, 1=matte, default 0.5).
        metallic: Metallic value (0=dielectric, 1=metal, default 0.0).
        tiling: UV tiling multiplier (default 1.0, higher = smaller texture repeat).
    """
    def _run(client):
        return client.create_textured_material(
            name, texture_path,
            roughness=roughness, metallic=metallic, tiling=tiling)
    return _safe_call(_run)

@mcp.tool()
def apply_material(
    blueprint: str,
    component_name: str,
    material_path: str,
    slot_index: int = 0,
) -> str:
    """Apply a material to a Blueprint's SCS component template.

    IMPORTANT: SCS OverrideMaterials may not persist on spawned actor instances.
    For reliable material application on placed actors, use set_actor_material
    instead (operates on the live actor, not the template).

    This modifies the Blueprint asset — recompile happens automatically.

    Args:
        blueprint: Blueprint asset name (e.g. "BP_Pickup").
        component_name: Component name in the SCS (e.g. "PickupMesh").
        material_path: Full UE asset path (e.g. "/Game/Arcwright/Materials/MAT_Gold").
            Use find_assets(asset_type="Material") to discover available materials.
        slot_index: Material slot index (default 0). Most meshes only have slot 0.
    """
    def _run(client):
        return client.apply_material(blueprint, component_name, material_path, slot_index)
    return _safe_call(_run)

@mcp.tool()
def remove_component(blueprint: str, component_name: str) -> str:
    """Remove a component from a Blueprint. Idempotent — removing a
    nonexistent component returns success with deleted=false.

    Args:
        blueprint: Blueprint asset name.
        component_name: Name of the component to remove.
    """
    def _run(client):
        return client.remove_component(blueprint, component_name)
    return _safe_call(_run)

@mcp.tool()
def delete_actor(label: str) -> str:
    """Delete a single actor from the current level by its label.

    Parameters:
        label (str): Actor label in the Outliner (as returned by spawn_actor or get_actors).
            Must match exactly (case-sensitive).

    Returns:
        {"status": "ok", "deleted": "Enemy_1"}

    Example:
        delete_actor("Enemy_1")

    Notes:
        - For deleting multiple actors at once, use batch_delete_actors instead (supports
          labels list, class_filter, and tag-based deletion)
        - Deleting a Blueprint actor instance does not delete the Blueprint asset itself.
          Use delete_blueprint to remove the asset from the Content Browser
        - World Partition external actor files are cleaned up automatically
    """
    def _run(client):
        return client.delete_actor(label)
    return _safe_call(_run)

@mcp.tool()
def save_all() -> str:
    """Save all unsaved (dirty) packages to disk: Blueprints, materials, DataTables, the level,
    and World Partition external actor files.

    Call this after making any changes you want to persist. This is the equivalent of
    pressing Ctrl+Shift+S in the editor. Skips untitled maps to avoid blocking "Save As" dialogs.

    Parameters:
        (none)

    Returns:
        {"status": "ok", "saved_packages": 5, "external_actors_saved": 12}

    Example:
        save_all()

    Notes:
        - Always call this after a batch of changes (spawning actors, creating materials,
          importing Blueprints) to ensure they survive an editor restart
        - World Partition external actors are saved explicitly since they are stored as
          separate .uasset files, not embedded in the .umap
        - Untitled maps are skipped to avoid blocking Save As dialogs
        - For saving just the level map, use save_level instead
        - Calling save_all frequently is safe -- it only writes packages that have changed
    """
    return _safe_call(lambda c: c.save_all())

@mcp.tool()
def save_level() -> str:
    """Save just the current level (map) in Unreal Engine."""
    return _safe_call(lambda c: c.save_level())

@mcp.tool()
def get_level_info() -> str:
    """Get summary information about the current Unreal Engine level.

    Returns the level name, path, total actor count, PlayerStart location, and a breakdown
    of actor counts by class. Use this as a first step to understand the current level state
    before spawning actors, querying content, or deciding what to build.

    Parameters:
        (none)

    Returns:
        {
            "level_name": "ArenaLevel",
            "level_path": "/Game/Maps/ArenaLevel",
            "actor_count": 48,
            "player_start": {"x": 0, "y": 0, "z": 100},
            "class_breakdown": {"StaticMeshActor": 15, "PointLight": 5, "BP_Enemy_C": 3}
        }

    Example:
        get_level_info()

    Notes:
        - The class_breakdown shows how many actors of each type exist -- useful for
          understanding level composition at a glance
        - For detailed per-actor information (labels, positions), use get_actors instead
        - For advanced actor searching with filters, use find_actors
        - The player_start location tells you where the player will spawn during PIE
    """
    return _safe_call(lambda c: c.get_level_info())

@mcp.tool()
def duplicate_blueprint(source_name: str, new_name: str) -> str:
    """Duplicate an existing Blueprint asset to a new name.

    Creates a full copy (nodes, variables, components, connections) in /Game/Arcwright/Generated/.
    The copy is independent -- changes to the original do not affect the duplicate.

    Parameters:
        source_name (str): Source Blueprint asset name (e.g. "BP_Pickup").
        new_name (str): Name for the new Blueprint (e.g. "BP_Pickup_Copy").

    Returns:
        {"status": "ok", "source": "BP_Pickup", "duplicate": "BP_Pickup_Copy",
         "path": "/Game/Arcwright/Generated/BP_Pickup_Copy"}

    Example:
        duplicate_blueprint("BP_Enemy", "BP_BossEnemy")

    Notes:
        - Fails if the target name already exists. Delete the existing one first if needed
        - For duplicating and modifying in one step, use the compound tool duplicate_and_customize
        - The duplicate shares the same parent class and initial variable values
        - Use modify_blueprint to change the copy after duplication
    """
    def _run(client):
        return client.duplicate_blueprint(source_name, new_name)
    return _safe_call(_run)

@mcp.tool()
def play_in_editor() -> str:
    """Request a Play In Editor (PIE) session to start.

    WARNING: Known UE 5.7 limitation -- the PIE request is queued but may not actually
    start because FEngineLoop::Tick() does not process queued play requests. The user
    may need to click Play manually in the editor. The command returns success (request queued)
    regardless.

    Parameters:
        (none)

    Returns:
        {"status": "ok", "message": "PIE session requested"}

    Example:
        play_in_editor()

    Notes:
        - Use get_output_log to observe Blueprint PrintString output during PIE
        - Use stop_play to end the PIE session
        - Due to the UE 5.7 engine tick limitation, PIE may not actually start via this command
    """
    return _safe_call(lambda c: c.play_in_editor())

@mcp.tool()
def stop_play() -> str:
    """Stop the current Play In Editor (PIE) session.

    Parameters:
        (none)

    Returns:
        {"status": "ok", "stopped": true}

    Example:
        stop_play()

    Notes:
        - Idempotent -- if no PIE session is running, returns success with stopped=false
        - The quit_editor command also stops PIE automatically before shutting down
    """
    return _safe_call(lambda c: c.stop_play())

@mcp.tool()
def get_output_log(
    last_n_lines: int = 50,
    category: str = "",
    text_filter: str = "",
) -> str:
    """Read lines from the Unreal Engine output log file.

    Useful for checking PrintString output during PIE, monitoring errors, verifying
    Blueprint behavior, or debugging command failures.

    Parameters:
        last_n_lines (int): Number of matching lines to return. Default: 50. Max recommended: 200.
        category (str): Filter by UE log category. Common values:
            "LogBlueprintUserMessages" -- PrintString output from Blueprints
            "LogBlueprintLLM" -- Arcwright plugin log messages
            "LogTemp" -- general temporary messages
            Empty string = all categories.
        text_filter (str): Filter by text substring (case-insensitive).
            Example: "Hello" finds lines containing "Hello".

    Returns:
        {"lines": ["[2026.03.14-10.30.45] LogBlueprintUserMessages: Hello World", ...], "count": 1}

    Example:
        get_output_log()                                          # last 50 lines
        get_output_log(category="LogBlueprintUserMessages")        # PrintString output only
        get_output_log(text_filter="Error", last_n_lines=100)     # recent errors

    Notes:
        - Reads from the UE log file on disk (Saved/Logs/<project>.log), not from an in-memory buffer
        - During PIE, Blueprint PrintString output appears under "LogBlueprintUserMessages"
        - Arcwright plugin operations are logged under "LogBlueprintLLM"
    """
    def _run(client):
        return client.get_output_log(
            last_n_lines=last_n_lines,
            category=category if category else None,
            text_filter=text_filter if text_filter else None,
        )
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Editor Lifecycle
# ---------------------------------------------------------------------------

@mcp.tool()
def quit_editor(skip_save: bool = False) -> str:
    """Request a clean shutdown of the Unreal Editor.

    Stops any active PIE session, saves all dirty packages (unless skip_save),
    then requests a graceful exit. The editor process will terminate ~500ms
    after the response is sent. Use this instead of taskkill for clean shutdowns
    that avoid autosave restore prompts on next launch.

    Args:
        skip_save: If True, skip saving before exit (default: False = save first).
    """
    def _run(client):
        return client.quit_editor(skip_save=skip_save)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Widget Tools (B11)
# ---------------------------------------------------------------------------

@mcp.tool()
def create_widget_blueprint(name: str, parent_class: str = "") -> str:
    """Create a new Widget Blueprint (UUserWidget subclass) for UMG UI.

    Widget Blueprints are used for HUDs, menus, health bars, inventory screens, and all
    in-game UI. After creation, add child widgets with add_widget_child and configure
    them with set_widget_property. The asset is saved to /Game/UI/.

    Parameters:
        name (str): Asset name (e.g. "WBP_HUD", "WBP_MainMenu", "WBP_HealthBar"). Use WBP_ prefix by convention.
        parent_class (str): Optional parent class. Default: UUserWidget.

    Returns:
        {"status": "ok", "widget_blueprint": "WBP_HUD", "path": "/Game/UI/WBP_HUD"}

    Example:
        create_widget_blueprint("WBP_GameHUD")
        create_widget_blueprint("WBP_PauseMenu")

    Notes:
        - After creation, the widget is empty. Add child widgets with add_widget_child
        - Typical structure: CanvasPanel (root) -> layout containers -> content widgets
        - For quick pre-built HUDs, use the compound tools create_game_hud or create_menu_widget
        - For HTML-based UI design, use create_widget_from_html
        - If a widget with the same name exists, it is overwritten
    """
    def _run(client):
        return client.create_widget_blueprint(name, parent_class=parent_class)
    return _safe_call(_run)

@mcp.tool()
def add_widget_child(
    widget_blueprint: str,
    widget_type: str,
    widget_name: str,
    parent_widget: str = "",
) -> str:
    """Add a widget to a Widget Blueprint's hierarchy tree.

    Widgets are the visual elements of UMG UI. Use this to build up the widget
    hierarchy after creating a Widget Blueprint with create_widget_blueprint.

    Parameters:
        widget_blueprint (str): Widget Blueprint name (e.g. "WBP_HUD").
        widget_type (str): Widget type to add. Supported types:
            Layout containers (can have children):
                "CanvasPanel" -- root layout with absolute positioning (use as root)
                "VerticalBox" -- stacks children vertically
                "HorizontalBox" -- stacks children horizontally
                "Overlay" -- stacks children on top of each other
                "SizeBox" -- constrains child to fixed dimensions
            Content widgets (leaf nodes):
                "TextBlock" -- displays text (configure with text, font_size, color)
                "ProgressBar" -- health bars, loading bars (configure with percent, fill_color)
                "Image" -- displays texture or colored rectangle
                "Button" -- clickable button (add TextBlock child for label)
        widget_name (str): Unique name for the widget (e.g. "ScoreLabel", "HealthBar").
            Must be unique within this Widget Blueprint.
        parent_widget (str): Parent widget name to add this widget under. If empty, adds to
            root (or becomes root if no root exists). Parent must be a panel type.

    Returns:
        {"status": "ok", "widget": "HealthBar", "type": "ProgressBar", "parent": "RootCanvas"}

    Example:
        add_widget_child("WBP_HUD", "CanvasPanel", "RootCanvas")
        add_widget_child("WBP_HUD", "TextBlock", "ScoreLabel", parent_widget="RootCanvas")
        add_widget_child("WBP_HUD", "ProgressBar", "HealthBar", parent_widget="RootCanvas")
        add_widget_child("WBP_HUD", "Button", "StartBtn", parent_widget="RootCanvas")
        add_widget_child("WBP_HUD", "TextBlock", "StartBtnText", parent_widget="StartBtn")

    Notes:
        - Always create a CanvasPanel as the root widget first, then add children to it
        - Button widgets need a TextBlock child for visible text
        - Configure widgets after adding them with set_widget_property
        - Use get_widget_tree to inspect the current hierarchy
    """
    def _run(client):
        return client.add_widget_child(widget_blueprint, widget_type, widget_name,
                                       parent_widget=parent_widget)
    return _safe_call(_run)

@mcp.tool()
def set_widget_property(
    widget_blueprint: str,
    widget_name: str,
    property_name: str,
    value: str,
) -> str:
    """Set a property on a widget in a Widget Blueprint.

    Parameters:
        widget_blueprint (str): Widget Blueprint name (e.g. "WBP_HUD").
        widget_name (str): Widget name (e.g. "ScoreLabel"). Use get_widget_tree to find names.
        property_name (str): Property to set. Available properties by widget type:
            TextBlock: "text", "font_size", "color", "justification"
            ProgressBar: "percent" (0.0-1.0), "fill_color", "background_color"
            Image: "color_and_opacity", "brush_color"
            Button: "background_color"
            Any widget: "visibility", "is_enabled", "render_opacity"
            Layout slots: "padding", "horizontal_alignment", "vertical_alignment"
            CanvasPanel slots: "position", "size", "anchors", "alignment"
        value (str): JSON-encoded value. Format by property:
            text: "Score: 0"
            font_size: "24"
            color/fill_color: "1.0,0.8,0.2,1.0" (RGBA comma-separated) or '{"r":1,"g":0.8,"b":0.2,"a":1}'
            percent: "0.75"
            position: "20,20" (x,y)
            size: "200,30" (width,height)
            anchors: "0.5,0,0.5,0" (min_x,min_y,max_x,max_y)
            horizontal_alignment: "Center" (Left/Center/Right/Fill)

    Returns:
        {"status": "ok", "widget": "ScoreLabel", "property": "text"}

    Example:
        set_widget_property("WBP_HUD", "ScoreLabel", "text", "Score: 0")
        set_widget_property("WBP_HUD", "ScoreLabel", "font_size", "24")
        set_widget_property("WBP_HUD", "ScoreLabel", "color", "0.2,0.8,1.0,1.0")
        set_widget_property("WBP_HUD", "HealthBar", "percent", "1.0")
        set_widget_property("WBP_HUD", "HealthBar", "position", "20,20")
        set_widget_property("WBP_HUD", "HealthBar", "size", "300,25")

    Notes:
        - Colors use RGBA format with values 0.0-1.0 (NOT 0-255)
        - Position is relative to parent widget's coordinate space
        - For CanvasPanel children, position/size control absolute placement
        - Use get_widget_tree to inspect current property values
    """
    import json as _json
    parsed_value = _json.loads(value)
    def _run(client):
        return client.set_widget_property(widget_blueprint, widget_name,
                                          property_name, parsed_value)
    return _safe_call(_run)

@mcp.tool()
def get_widget_tree(widget_blueprint: str) -> str:
    """List all widgets in a Widget Blueprint with their hierarchy, types, and properties.

    Returns a nested tree structure showing each widget's name, type, depth, and
    type-specific properties (text content, percent, font size, etc.). Use this to
    inspect the widget hierarchy before modifying with set_widget_property or remove_widget.

    Parameters:
        widget_blueprint (str): Widget Blueprint name (e.g. "WBP_HUD").

    Returns:
        {"widgets": [
            {"name": "RootCanvas", "type": "CanvasPanel", "depth": 0, "children": [
                {"name": "HealthBar", "type": "ProgressBar", "depth": 1, "percent": 1.0},
                {"name": "ScoreLabel", "type": "TextBlock", "depth": 1, "text": "Score: 0"}
            ]}
        ]}

    Example:
        get_widget_tree("WBP_HUD")

    Notes:
        - Widget names shown here are used with set_widget_property and remove_widget
        - The depth field indicates nesting level (0 = root)
    """
    def _run(client):
        return client.get_widget_tree(widget_blueprint)
    return _safe_call(_run)

@mcp.tool()
def get_viewport_widgets() -> str:
    """List all UUserWidget instances currently in the viewport during PIE.

    Returns runtime widget state: class name, visibility, in_viewport status,
    and child widgets with their current text/percent values. Use this to verify
    HUD widgets are actually displaying during Play-In-Editor, since screenshots
    cannot capture the UMG overlay layer.

    Returns:
        JSON with total_user_widgets, in_viewport count, pie_running status,
        and widgets[] array with class, visible, children[{name, type, text, percent}].

    Notes:
        - Only finds widgets during active PIE session
        - Use get_widget_tree for design-time hierarchy; this shows runtime state
    """
    def _run(client):
        return client.cmd("get_viewport_widgets")
    return _safe_call(_run)

@mcp.tool()
def remove_widget(widget_blueprint: str, widget_name: str) -> str:
    """Remove a widget from a Widget Blueprint's hierarchy.

    Parameters:
        widget_blueprint (str): Widget Blueprint name (e.g. "WBP_HUD").
        widget_name (str): Name of the widget to remove.

    Returns:
        {"status": "ok", "deleted": true, "widget": "OldLabel"}

    Example:
        remove_widget("WBP_HUD", "OldLabel")

    Notes:
        - Idempotent -- removing a nonexistent widget returns success with deleted=false
        - Removing a panel widget also removes all its children
        - Use get_widget_tree to verify the current hierarchy before removing
    """
    def _run(client):
        return client.remove_widget(widget_blueprint, widget_name)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Behavior Tree Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_behavior_tree_from_dsl(dsl_text: str) -> str:
    """Create a BehaviorTree + Blackboard in Unreal Engine from BT DSL text.

    The BT DSL uses indentation to define tree hierarchy. Example:

        BEHAVIORTREE: BT_Guard
        BLACKBOARD: BB_Guard

        KEY TargetActor: Object
        KEY PatrolLocation: Vector

        TREE:

        SELECTOR: Root
          SEQUENCE: Chase
            DECORATOR: BlackboardBased [Key=TargetActor, Condition=IsSet, AbortMode=LowerPriority]
            TASK: MoveTo [Key=TargetActor, AcceptableRadius=200]
          SEQUENCE: Patrol
            TASK: MoveTo [Key=PatrolLocation, AcceptableRadius=50]
            TASK: Wait [Duration=3.0]

    This parses the DSL locally, converts to IR, and creates both a UBehaviorTree
    and UBlackboardData asset in UE. Assets are saved to /Game/Arcwright/BehaviorTrees/.

    Parameters:
        dsl_text (str): Raw BT DSL text with indentation-based hierarchy.

    Returns:
        {"status": "ok", "behavior_tree": "BT_Guard", "blackboard": "BB_Guard",
         "composites": 2, "tasks": 3, "decorators": 1, "services": 0,
         "bb_keys": [{"name": "TargetActor", "type": "Object"}, {"name": "PatrolLocation", "type": "Vector"}]}

    Example:
        create_behavior_tree_from_dsl("BEHAVIORTREE: BT_Patrol\\nBLACKBOARD: BB_Patrol\\n\\nKEY TargetLocation: Vector\\n\\nTREE:\\n\\nSEQUENCE: Root\\n  TASK: MoveTo [Key=TargetLocation]\\n  TASK: Wait [Duration=3.0]")

    Notes:
        - Supported composites: Selector, Sequence, SimpleParallel
        - Supported tasks: MoveTo, Wait, RotateToFaceBBEntry, PlaySound, FinishWithResult, + 8 more
        - Supported decorators: BlackboardBased, Cooldown, Loop, TimeLimit, ForceSuccess, + 7 more
        - Supported services: DefaultFocus, RunEQS, BlackboardBase, + 3 more
        - BB key types: Bool, Int, Float, String, Name, Vector, Rotator, Object, Class, Enum
        - A SelfActor key is auto-added to every Blackboard
        - Use setup_ai_for_pawn to wire the BT to a pawn after creation
        - For Blueprint DSL, use create_blueprint_from_dsl instead (different format)
        - For DataTable DSL, use create_data_table_from_dsl instead (different format)
    """
    # Pre-flight: validate BT DSL syntax and warn about MoveTo+NavMesh
    warnings = []
    if _HAS_PREFLIGHT:
        report = check_bt(dsl_text)
        warnings = _preflight_warnings(report)
        fails = [str(r) for r in report.results if r.status == Status.FAIL]
        if fails:
            return json.dumps({
                "error": "BT pre-flight BLOCKED: " + "; ".join(fails),
                "preflight_warnings": warnings,
            })

    def _run(client):
        result = client.create_behavior_tree_from_dsl(dsl_text)
        if warnings and isinstance(result, dict):
            result["preflight_warnings"] = warnings
        return result
    return _safe_call(_run)

@mcp.tool()
def get_behavior_tree_info(name: str) -> str:
    """Query an existing BehaviorTree asset's structure and Blackboard keys.

    Parameters:
        name (str): BehaviorTree asset name (e.g. "BT_PatrolGuard").
            Searches /Game/Arcwright/BehaviorTrees/ and the full asset registry.

    Returns:
        {"name": "BT_PatrolGuard", "blackboard": "BB_PatrolGuard",
         "bb_keys": [{"name": "TargetActor", "type": "Object"}],
         "composites": 2, "tasks": 3, "decorators": 1, "services": 0}

    Example:
        get_behavior_tree_info("BT_PatrolGuard")

    Notes:
        - Use this to verify a BehaviorTree was created correctly
        - The bb_keys list shows all Blackboard keys with their types
        - For querying Blueprint structure, use get_blueprint_info instead
    """
    def _run(client):
        return client.get_behavior_tree_info(name)
    return _safe_call(_run)

@mcp.tool()
def setup_ai_for_pawn(pawn_name: str, behavior_tree: str,
                      controller_name: str = "") -> str:
    """One-command AI setup: create AIController with RunBehaviorTree, assign to pawn, set AutoPossessAI.

    This replaces a 5-step manual process: create controller BP, add BeginPlay event,
    add RunBehaviorTree node, wire them, set AIControllerClass + AutoPossessAI on the pawn.

    Parameters:
        pawn_name (str): Name of the Pawn/Character Blueprint to attach AI to (e.g. "BP_Enemy").
            Must already exist.
        behavior_tree (str): Name of the BehaviorTree asset (e.g. "BT_PatrolGuard"). Must already exist.
            Create it first with create_behavior_tree_from_dsl.
        controller_name (str): Optional custom AIController name. Default: "BP_<pawn>_AIController"
            (e.g. "BP_Enemy_AIController"). If a controller with this name already exists, it is reused.

    Returns:
        {"status": "ok", "controller": "BP_Enemy_AIController", "pawn": "BP_Enemy",
         "behavior_tree": "BT_PatrolGuard", "auto_possess": "PlacedInWorldOrSpawned"}

    Example:
        setup_ai_for_pawn("BP_Enemy", "BT_PatrolGuard")
        setup_ai_for_pawn("BP_Guard", "BT_GuardPatrol", controller_name="BP_GuardAI")

    Notes:
        - The BehaviorTree and Pawn Blueprint must already exist
        - Sets AutoPossessAI to PlacedInWorldOrSpawned on the pawn
        - If the controller already exists, it is reused (not recreated)
        - For the compound tool that creates everything (pawn + BT + AI + spawn), use create_ai_enemy
        - The pawn needs a movement component (FloatingPawnMovement for simple AI, CharacterMovement for humanoids)
    """
    def _run(client):
        return client.setup_ai_for_pawn(
            pawn_name, behavior_tree,
            controller_name if controller_name else None
        )
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Data Table Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_data_table_from_dsl(dsl_text: str) -> str:
    """Create a DataTable + UserDefinedStruct in Unreal Engine from DT DSL text.

    The DT DSL defines a struct schema and table rows. Example:

        DATATABLE: DT_Weapons
        STRUCT: FWeaponData

        COLUMN Name: String
        COLUMN Damage: Float
        COLUMN Ammo: Int = 30

        ROW Pistol: "Pistol", 15.0, 12
        ROW Shotgun: "Shotgun", 45.0, 8

    Column types: String, Float, Int, Bool, Name, Text, Vector, Rotator, Color, SoftObject.
    Default values after '=' are optional.

    Parameters:
        dsl_text (str): Raw DT DSL text with DATATABLE, STRUCT, COLUMN, and ROW declarations.

    Returns:
        {"status": "ok", "data_table": "DT_Weapons", "struct": "FWeaponData",
         "columns": 3, "rows": 2}

    Example:
        create_data_table_from_dsl("DATATABLE: DT_Items\\nSTRUCT: FItemData\\n\\nCOLUMN Name: String\\nCOLUMN Value: Int = 0\\n\\nROW Gold: \\"Gold Coin\\", 100\\nROW Gem: \\"Ruby Gem\\", 500")

    Notes:
        - Assets saved to /Game/Arcwright/DataTables/
        - Column names become struct properties with GUID-suffixed internal names
        - ROW values must match column order (positional, not named)
        - For Blueprint DSL, use create_blueprint_from_dsl instead
        - For BehaviorTree DSL, use create_behavior_tree_from_dsl instead
        - Use get_data_table_info to verify the created table
        - Use add_data_table_row and edit_data_table_row for post-creation modifications
    """
    def _run(client):
        return client.create_data_table_from_dsl(dsl_text)
    return _safe_call(_run)

@mcp.tool()
def get_data_table_info(name: str) -> str:
    """Query an existing DataTable asset's structure, columns, and row data.

    Parameters:
        name (str): DataTable asset name (e.g. "DT_Weapons").
            Searches /Game/Arcwright/DataTables/ and the full asset registry.

    Returns:
        {"name": "DT_Weapons", "struct": "FWeaponData",
         "columns": [{"name": "Name", "type": "String"}, {"name": "Damage", "type": "Float"}],
         "row_count": 2, "rows": ["Pistol", "Shotgun"]}

    Example:
        get_data_table_info("DT_Weapons")

    Notes:
        - Use this to verify a DataTable was created correctly after create_data_table_from_dsl
        - For full row data with values, use get_data_table_rows instead
    """
    def _run(client):
        return client.get_data_table_info(name)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Scene Lighting
# ---------------------------------------------------------------------------

@mcp.tool()
def setup_scene_lighting(preset: str = "indoor_dark",
                          directional_intensity: float = None,
                          sky_intensity: float = None,
                          directional_pitch: float = None,
                          add_fog: bool = None) -> str:
    """Create standard scene lighting with DirectionalLight + SkyLight + optional atmosphere/fog.

    IMPORTANT: Use this as the FIRST step when building any level from scratch. Levels populated
    purely via spawn_actor have no ambient lighting -- everything will be dark without this.
    Replaces any existing DirectionalLight/SkyLight in the level.

    Parameters:
        preset (str): Lighting mood preset. One of:
            "indoor_dark" -- dim ambient, suitable for dungeons/caves (default)
            "indoor_bright" -- well-lit interior, suitable for offices/labs
            "outdoor_day" -- bright sun + sky, suitable for open worlds
            "outdoor_night" -- moonlight + dim ambient, suitable for nighttime
        directional_intensity (float, optional): Override sun/directional light intensity (lux).
        sky_intensity (float, optional): Override ambient sky light intensity.
        directional_pitch (float, optional): Override sun angle in degrees (negative = angled down).
        add_fog (bool, optional): Whether to add ExponentialHeightFog for atmospheric depth.

    Returns:
        {"status": "ok", "preset": "indoor_dark", "directional_light": "Sun", "sky_light": "Sky"}

    Example:
        setup_scene_lighting("outdoor_day")
        setup_scene_lighting("indoor_dark", directional_intensity=3.0, add_fog=True)

    Notes:
        - Call this BEFORE spawning actors so the scene is properly lit during placement
        - For the setup_playable_scene compound tool, lighting is handled automatically
        - Preset values can be overridden individually (e.g. outdoor_day with custom sun angle)
        - SkyAtmosphere is only added with outdoor presets
    """
    def _run(client):
        params = {}
        if directional_intensity is not None:
            params["directional_intensity"] = directional_intensity
        if sky_intensity is not None:
            params["sky_intensity"] = sky_intensity
        if directional_pitch is not None:
            params["directional_pitch"] = directional_pitch
        if add_fog is not None:
            params["add_fog"] = add_fog
        return client.setup_scene_lighting(preset, **params)
    return _safe_call(_run)

@mcp.tool()
def set_game_mode(game_mode: str) -> str:
    """Set the level's GameMode override in World Settings.

    The GameMode controls which player controller, pawn, and HUD classes are used when
    playing the level. The GameMode Blueprint must already exist and inherit from GameModeBase.

    Parameters:
        game_mode (str): Name of the GameMode Blueprint. Common values (after setup_game_base):
            "BP_FirstPersonGameMode" -- FPS: WASD + mouse look + jump
            "BP_ThirdPersonGameMode" -- Third person: camera behind character
            "BP_TopDownGameMode" -- Top-down: overhead camera + click-to-move
            "BP_VehicleAdvGameMode" -- Vehicle: car physics + dual cameras
            Or any custom GameMode BP you've created.

    Returns:
        {"status": "ok", "game_mode": "BP_FirstPersonGameMode"}

    Example:
        set_game_mode("BP_FirstPersonGameMode")
        set_game_mode("BP_TempleGameMode")

    Notes:
        - This sets a per-level override in World Settings. Each level can have a different GameMode
        - The GameMode BP must inherit from GameModeBase (use reparent_blueprint if needed)
        - Must be called AFTER the GameMode BP exists. If using setup_game_base, call it after
          building and relaunching the editor
        - The GameMode determines which DefaultPawnClass, PlayerControllerClass, and HUDClass are used
        - For the setup_playable_scene compound tool, game_mode is handled automatically

    Common mistakes:
        - Calling set_game_mode before the GameMode Blueprint exists in the project
        - Not rebuilding the project after setup_game_base (the C++ template must be compiled first)
    """
    def _run(client):
        return client.set_game_mode(game_mode)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Input Mapping Tools (B29)
# ---------------------------------------------------------------------------

@mcp.tool()
def setup_input_context(name: str) -> str:
    """Create a UInputMappingContext asset for Enhanced Input in Unreal Engine.

    Input Mapping Contexts group key/button bindings together. A player controller
    can have multiple contexts active simultaneously (e.g. IMC_Default for movement,
    IMC_Combat for weapon controls). Use add_input_mapping to bind keys to actions
    within this context.

    Parameters:
        name (str): Asset name for the context. Convention: "IMC_" prefix.
            Example: "IMC_Default", "IMC_Combat", "IMC_Vehicle"

    Returns:
        {"status": "ok", "name": "IMC_Default", "path": "/Game/Arcwright/Input/IMC_Default"}

    Example:
        setup_input_context("IMC_Default")

    Notes:
        - Create input actions first with add_input_action, then bind them with add_input_mapping
        - For FPS/TPS games, prefer setup_game_base.py which provides pre-configured input contexts
        - Use set_player_input_mapping to assign a context to a PlayerController Blueprint
    """
    def _run(client):
        return client.setup_input_context(name)
    return _safe_call(_run)

@mcp.tool()
def add_input_action(name: str, value_type: str = "bool") -> str:
    """Create a UInputAction asset for Enhanced Input.

    Input actions represent abstract game actions (jump, move, fire) that can be
    bound to physical keys via input mapping contexts. This is the Enhanced Input
    equivalent of the legacy ActionMapping/AxisMapping system.

    Parameters:
        name (str): Action name. Convention: "IA_" prefix.
            Examples: "IA_Jump", "IA_Move", "IA_Fire", "IA_Interact", "IA_Crouch"
        value_type (str): The type of input value this action produces. Default: "bool".
            "bool" -- button press (on/off). Use for Jump, Fire, Interact.
            "axis1d" -- single axis float. Use for Throttle, Zoom.
            "axis2d" -- two-axis vector. Use for WASD movement, mouse look (x,y).
            "axis3d" -- three-axis vector. Rare, used for 3D spatial input.

    Returns:
        {"status": "ok", "name": "IA_Jump", "path": "/Game/Arcwright/Input/IA_Jump"}

    Example:
        add_input_action("IA_Jump", "bool")
        add_input_action("IA_Move", "axis2d")

    Notes:
        - After creating, bind to a key with add_input_mapping
        - To wire into a Blueprint's event graph, use bind_input_to_blueprint
        - Also available as create_input_action (alias)
    """
    def _run(client):
        return client.add_input_action(name, value_type)
    return _safe_call(_run)

@mcp.tool()
def add_input_mapping(context: str, action: str, key: str) -> str:
    """Bind a physical key to an input action within a mapping context.

    Both the context and action must already exist (create with setup_input_context
    and add_input_action first).

    Parameters:
        context (str): Input mapping context name or path. Example: "IMC_Default"
        action (str): Input action name or path. Example: "IA_Jump"
        key (str): UE key name. Common values:
            Keyboard: "SpaceBar", "W", "A", "S", "D", "E", "F", "LeftShift", "LeftControl",
                      "Escape", "One", "Two", "Three"
            Mouse: "LeftMouseButton", "RightMouseButton", "MiddleMouseButton",
                   "MouseX", "MouseY", "MouseWheelUp", "MouseWheelDown"
            Gamepad: "Gamepad_FaceButton_Bottom" (A), "Gamepad_FaceButton_Right" (B),
                     "Gamepad_LeftTrigger", "Gamepad_RightTrigger",
                     "Gamepad_LeftThumbstick", "Gamepad_RightThumbstick"

    Returns:
        {"status": "ok", "context": "IMC_Default", "action": "IA_Jump", "key": "SpaceBar"}

    Example:
        add_input_mapping("IMC_Default", "IA_Jump", "SpaceBar")
        add_input_mapping("IMC_Default", "IA_Fire", "LeftMouseButton")

    Notes:
        - Multiple keys can be mapped to the same action (call this multiple times)
        - Key names are case-sensitive and must match UE's FKey names exactly
        - For FPS controls, prefer setup_game_base.py which provides pre-mapped inputs
    """
    def _run(client):
        return client.add_input_mapping(context, action, key)
    return _safe_call(_run)

@mcp.tool()
def get_input_actions(path: str = "") -> str:
    """List all UInputAction assets in the project.

    Searches the asset registry for Enhanced Input action assets. Use this to
    discover what input actions exist before binding them to keys or Blueprints.

    Parameters:
        path (str): Content path to search. Default: "/Game/Arcwright/Input".
            Use "/Game" to search all project assets.

    Returns:
        {"count": 3, "actions": [{"name": "IA_Jump", "path": "/Game/...", "value_type": "bool"}]}

    Example:
        get_input_actions()                     # list actions in default path
        get_input_actions("/Game")              # search entire project

    Notes:
        - Returns actions created by add_input_action / create_input_action
        - Also returns engine/template input actions if they exist under the search path
    """
    def _run(client):
        return client.get_input_actions(path=path if path else "")
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Audio Tools (B24)
# ---------------------------------------------------------------------------

@mcp.tool()
def play_sound_at_location(
    sound: str,
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    volume: float = 1.0, pitch: float = 1.0,
) -> str:
    """Play a sound effect at a world position (fire-and-forget, spatially attenuated).

    The sound plays once at the specified location with distance-based attenuation.
    No actor is created -- the sound is transient. For looping or persistent audio,
    use add_audio_component on a Blueprint instead.

    Parameters:
        sound (str): SoundWave or SoundCue asset path.
            Example: "/Game/Arcwright/Sounds/SFX_PickupChime"
        x (float): World X position in cm. Default: 0.
        y (float): World Y position in cm. Default: 0.
        z (float): World Z position in cm. Default: 0.
        volume (float): Volume multiplier. 0.0=silent, 1.0=normal, 2.0=double. Default: 1.0.
        pitch (float): Pitch multiplier. 0.5=half speed, 1.0=normal, 2.0=double speed. Default: 1.0.

    Returns:
        {"status": "ok", "sound": "/Game/.../SFX_PickupChime", "location": {"x":0,"y":0,"z":0}}

    Example:
        play_sound_at_location("/Game/Arcwright/Sounds/SFX_Explosion", 500.0, 200.0, 0.0)

    Notes:
        - Import sounds first with import_sound (.wav, .ogg, .mp3)
        - Use get_sound_assets or find_assets(asset_type="SoundWave") to discover available sounds
        - For ambient/looping sounds, add a UAudioComponent to a Blueprint instead
    """
    def _run(client):
        return client.play_sound_at_location(
            sound, {"x": x, "y": y, "z": z}, volume, pitch)
    return _safe_call(_run)

@mcp.tool()
def add_audio_component(
    blueprint: str,
    component_name: str = "Audio",
    sound: str = "",
    auto_activate: bool = True,
) -> str:
    """Add an audio component to a Blueprint for ambient or looping sound playback.

    The component is added to the Blueprint's SimpleConstructionScript (SCS). When
    actors are spawned from this Blueprint, they will have audio attached. Use
    set_audio_properties to fine-tune volume, pitch, and attenuation after adding.

    Parameters:
        blueprint (str): Blueprint asset name. Example: "BP_Campfire", "BP_Waterfall"
        component_name (str): Name for the audio component. Default: "Audio".
        sound (str): SoundWave or SoundCue asset path to assign. Leave empty to set later.
            Example: "/Game/Arcwright/Sounds/SFX_FireLoop"
        auto_activate (bool): Whether the sound plays automatically when spawned. Default: true.

    Returns:
        {"status": "ok", "blueprint": "BP_Campfire", "component": "Audio"}

    Example:
        add_audio_component("BP_Campfire", "FireSound", "/Game/Sounds/SFX_Fire", True)

    Notes:
        - For one-shot sounds at a location, use play_sound_at_location instead
        - Tune volume/pitch/attenuation with set_audio_properties after adding
        - Re-spawn actors after adding components to see changes on placed instances
    """
    def _run(client):
        return client.add_audio_component(
            blueprint, name=component_name, sound=sound,
            auto_activate=auto_activate)
    return _safe_call(_run)

@mcp.tool()
def get_sound_assets(path: str = "/Game", search_subfolders: bool = True) -> str:
    """List all SoundWave and SoundCue assets in the project.

    Use this to discover available audio assets before using them with
    play_sound_at_location or add_audio_component.

    Parameters:
        path (str): Content path to search. Default: "/Game" (entire project).
            Use "/Game/Arcwright/Sounds" for Arcwright-imported sounds only.
        search_subfolders (bool): Recursively search subdirectories. Default: true.

    Returns:
        {"count": 5, "assets": [{"name": "SFX_PickupChime", "path": "/Game/.../SFX_PickupChime", "type": "SoundWave"}]}

    Example:
        get_sound_assets()                                      # all sounds
        get_sound_assets("/Game/Arcwright/Sounds")           # imported sounds only

    Notes:
        - Import sounds with import_sound (.wav, .ogg, .mp3 supported)
        - Also available via find_assets(asset_type="SoundWave") for more filtering options
    """
    def _run(client):
        return client.get_sound_assets(path, search_subfolders)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Viewport Tools (B30)
# ---------------------------------------------------------------------------

@mcp.tool()
def set_viewport_camera(
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0,
    set_location: bool = True, set_rotation: bool = True,
) -> str:
    """Move the UE Editor viewport camera to a specific position and orientation.

    Controls the editor's perspective viewport camera (not a CameraActor in the level).
    Useful for framing screenshots or inspecting specific areas of the level.

    Parameters:
        x (float): World X position in cm. Default: 0.
        y (float): World Y position in cm. Default: 0.
        z (float): World Z position in cm. Default: 0.
        pitch (float): Vertical angle in degrees. Negative = look down, positive = look up.
        yaw (float): Horizontal angle in degrees. 0 = +X, 90 = +Y.
        roll (float): Roll angle in degrees. Usually 0.
        set_location (bool): Whether to update the camera position. Default: true.
        set_rotation (bool): Whether to update the camera rotation. Default: true.

    Returns:
        {"status": "ok", "location": {"x":0,"y":0,"z":500}, "rotation": {"pitch":-30,"yaw":0,"roll":0}}

    Example:
        set_viewport_camera(0, -500, 500, -30, 0, 0)    # bird's eye view from south
        set_viewport_camera(pitch=-90, set_location=False)  # look straight down without moving

    Notes:
        - This moves the EDITOR camera, not a game camera. It has no effect during PIE.
        - Combine with take_screenshot to capture specific views of your level
        - Use get_viewport_info to read the current camera state first
    """
    def _run(client):
        loc = {"x": x, "y": y, "z": z} if set_location else None
        rot = {"pitch": pitch, "yaw": yaw, "roll": roll} if set_rotation else None
        return client.set_viewport_camera(location=loc, rotation=rot)
    return _safe_call(_run)

@mcp.tool()
def take_screenshot(filename: str = "") -> str:
    """Capture the editor viewport as a PNG screenshot file.

    Saves to the project's Saved/Screenshots/BlueprintLLM/ directory. Use
    set_viewport_camera first to frame the shot.

    Parameters:
        filename (str): Filename for the screenshot (without extension). If empty,
            auto-generates a timestamped name like "screenshot_20260315_143022.png".

    Returns:
        {"status": "ok", "path": "C:/Junk/BlueprintLLMTest/Saved/Screenshots/BlueprintLLM/screenshot.png",
         "width": 1920, "height": 1080}

    Example:
        take_screenshot("level_overview")
        take_screenshot()                       # auto-named with timestamp

    Notes:
        - Uses FScreenshotRequest for reliable capture (ReadPixels returns blank from TCP context)
        - Position the camera first with set_viewport_camera for the desired angle
        - The screenshot captures the editor viewport, not the game view
    """
    def _run(client):
        return client.take_screenshot(filename)
    return _safe_call(_run)

@mcp.tool()
def get_viewport_info() -> str:
    """Get the current editor viewport camera position, rotation, FOV, and view mode.

    Returns:
        {"location": {"x":0,"y":-500,"z":300}, "rotation": {"pitch":-30,"yaw":0,"roll":0},
         "fov": 90.0, "view_mode": "Lit"}

    Example:
        get_viewport_info()

    Notes:
        - Reports the EDITOR viewport state, not any in-game camera
        - Use set_viewport_camera to reposition the camera
    """
    return _safe_call(lambda c: c.get_viewport_info())

# ---------------------------------------------------------------------------
# Niagara Tools (B25)
# ---------------------------------------------------------------------------

@mcp.tool()
def spawn_niagara_at_location(
    system: str,
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0,
    auto_destroy: bool = True,
) -> str:
    """Spawn a Niagara particle system at a world location as a one-shot effect.

    Creates an actor with a NiagaraComponent playing the specified system. If
    auto_destroy is true, the actor removes itself when the effect finishes.
    For persistent particle effects, use add_niagara_component on a Blueprint instead.

    Parameters:
        system (str): Niagara system asset path.
            Example: "/Game/Effects/NS_Explosion", "/Niagara/DefaultAssets/NS_Fire"
        x (float): World X position in cm. Default: 0.
        y (float): World Y position in cm. Default: 0.
        z (float): World Z position in cm. Default: 0.
        pitch (float): Rotation pitch in degrees. Default: 0.
        yaw (float): Rotation yaw in degrees. Default: 0.
        roll (float): Rotation roll in degrees. Default: 0.
        auto_destroy (bool): Destroy the actor when the effect completes. Default: true.

    Returns:
        {"status": "ok", "actor": "NiagaraActor_0", "system": "/Game/Effects/NS_Explosion"}

    Example:
        spawn_niagara_at_location("/Game/Effects/NS_Explosion", 500, 200, 0)

    Notes:
        - Use get_niagara_assets to discover available Niagara systems
        - For persistent effects attached to Blueprints, use add_niagara_component
        - Niagara parameters can be tuned with set_niagara_parameter after spawning
    """
    def _run(client):
        return client.spawn_niagara_at_location(
            system, {"x": x, "y": y, "z": z},
            rotation={"pitch": pitch, "yaw": yaw, "roll": roll},
            auto_destroy=auto_destroy)
    return _safe_call(_run)

@mcp.tool()
def add_niagara_component(
    blueprint: str,
    component_name: str = "Niagara",
    system: str = "",
    auto_activate: bool = True,
) -> str:
    """Add a Niagara particle system component to a Blueprint for persistent effects.

    The component is added to the Blueprint's SCS. When actors are spawned from this
    Blueprint, they will have the particle effect attached and (optionally) auto-playing.

    Parameters:
        blueprint (str): Blueprint asset name. Example: "BP_Campfire", "BP_Torch"
        component_name (str): Name for the Niagara component. Default: "Niagara".
        system (str): Niagara system asset path to assign. Leave empty to set later.
            Example: "/Game/Effects/NS_CampfireFlames"
        auto_activate (bool): Whether the effect plays when the actor spawns. Default: true.

    Returns:
        {"status": "ok", "blueprint": "BP_Campfire", "component": "Niagara"}

    Example:
        add_niagara_component("BP_Torch", "FlameEffect", "/Game/Effects/NS_TorchFlame")

    Notes:
        - For one-shot effects, use spawn_niagara_at_location instead
        - Tune parameters after adding with set_niagara_parameter
        - Re-spawn actors after adding components to see changes on placed instances
    """
    def _run(client):
        return client.add_niagara_component(
            blueprint, name=component_name, system=system,
            auto_activate=auto_activate)
    return _safe_call(_run)

@mcp.tool()
def get_niagara_assets(path: str = "/Game", search_subfolders: bool = True) -> str:
    """List all Niagara particle system assets in the project.

    Use this to discover available particle effects before spawning them or adding
    them to Blueprints.

    Parameters:
        path (str): Content path to search. Default: "/Game" (entire project).
        search_subfolders (bool): Recursively search subdirectories. Default: true.

    Returns:
        {"count": 3, "assets": [{"name": "NS_Fire", "path": "/Game/Effects/NS_Fire"}]}

    Example:
        get_niagara_assets()                                    # all Niagara systems
        get_niagara_assets("/Game/Effects")                     # effects folder only

    Notes:
        - Also available via find_assets(asset_type="NiagaraSystem")
        - Niagara systems can be spawned with spawn_niagara_at_location
          or added to Blueprints with add_niagara_component
    """
    def _run(client):
        return client.get_niagara_assets(path, search_subfolders)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Spline Tools (Batch 1.1)
# ---------------------------------------------------------------------------

@mcp.tool()
def create_spline_actor(
    blueprint_name: str,
    points: str = "[]",
    closed: bool = False,
) -> str:
    """Create a Blueprint with a SplineComponent for paths, rails, and routes.

    Splines define smooth curves through world space, used for moving platforms,
    AI patrol routes, camera rails, rivers, roads, and roller coasters.

    Parameters:
        blueprint_name (str): Name for the Blueprint. Example: "BP_RacePath", "BP_PatrolRoute"
        points (str): JSON array of {x,y,z} point positions defining the spline shape.
            Minimum 2 points required. Example: '[{"x":0,"y":0,"z":0},{"x":500,"y":0,"z":0},{"x":500,"y":500,"z":0}]'
        closed (bool): Whether the spline forms a closed loop (last point connects to first).
            Default: false. Set true for circular patrol paths or race tracks.

    Returns:
        {"status": "ok", "blueprint": "BP_RacePath", "path": "/Game/...",
         "point_count": 3, "closed": false}

    Example:
        create_spline_actor("BP_PatrolRoute", '[{"x":0,"y":0,"z":0},{"x":1000,"y":0,"z":0},{"x":1000,"y":1000,"z":0}]', True)

    Notes:
        - Add more points after creation with add_spline_point
        - Query spline data with get_spline_info
        - For the compound workflow create_patrol_path, which combines spline creation with AI setup
        - Points define the spline's control points; UE interpolates smooth curves between them
    """
    import json as _json
    parsed_points = _json.loads(points) if points else []
    def _run(client):
        return client.create_spline_actor(blueprint_name, parsed_points, closed)
    return _safe_call(_run)

@mcp.tool()
def add_spline_point(
    blueprint: str,
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    index: int = -1,
) -> str:
    """Add a point to an existing Blueprint's SplineComponent.

    Parameters:
        blueprint (str): Blueprint name that has a SplineComponent (created with create_spline_actor).
        x (float): Point X position in cm.
        y (float): Point Y position in cm.
        z (float): Point Z position in cm.
        index (int): Insert index in the point list. -1 = append to end (default).
            0 = insert at start. N = insert at position N.

    Returns:
        {"status": "ok", "blueprint": "BP_RacePath", "point_count": 4, "index": 3}

    Example:
        add_spline_point("BP_PatrolRoute", 2000, 0, 0)          # append point at end
        add_spline_point("BP_PatrolRoute", 500, 500, 0, 1)      # insert at position 1

    Notes:
        - The Blueprint must already have a SplineComponent (create with create_spline_actor)
        - UE interpolates smooth curves between control points
        - Use get_spline_info to see the current point list
    """
    def _run(client):
        return client.add_spline_point(blueprint, {"x": x, "y": y, "z": z}, index)
    return _safe_call(_run)

@mcp.tool()
def get_spline_info(blueprint: str) -> str:
    """Get spline data from a Blueprint's SplineComponent: points, length, and closed status.

    Parameters:
        blueprint (str): Blueprint name that has a SplineComponent.

    Returns:
        {"blueprint": "BP_RacePath", "point_count": 4, "spline_length": 2500.0,
         "closed": false, "points": [{"x":0,"y":0,"z":0}, {"x":1000,"y":0,"z":0}, ...]}

    Example:
        get_spline_info("BP_PatrolRoute")

    Notes:
        - spline_length is the total arc length in cm, NOT the straight-line distance
        - Points are the control points; the actual curve passes through/near them
        - Use create_spline_actor to create, add_spline_point to modify
    """
    def _run(client):
        return client.get_spline_info(blueprint)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Post-Process Tools (Batch 1.2)
# ---------------------------------------------------------------------------

@mcp.tool()
def add_post_process_volume(
    label: str = "",
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    infinite_extent: bool = True,
    settings: str = "{}",
) -> str:
    """Spawn a PostProcessVolume actor in the level for cinematic visual effects.

    Post-process volumes control full-screen effects: bloom, exposure, color grading,
    depth of field, vignette, ambient occlusion, and motion blur. An infinite extent
    volume affects the entire level; a bounded volume only affects cameras inside it.

    Parameters:
        label (str): Actor label in Outliner. Auto-generated if empty.
        x (float): World X position. Default: 0.
        y (float): World Y position. Default: 0.
        z (float): World Z position. Default: 0.
        infinite_extent (bool): If true, the volume affects the entire level regardless of
            camera position. If false, only cameras inside the volume's bounds are affected.
            Default: true.
        settings (str): JSON object of initial post-process settings. See set_post_process_settings
            for all available keys. Example: '{"bloom_intensity": 1.5, "vignette_intensity": 0.4}'

    Returns:
        {"status": "ok", "actor": "PostProcessVolume_0", "infinite_extent": true}

    Example:
        add_post_process_volume("MainPP", infinite_extent=True,
            settings='{"bloom_intensity": 0.8, "vignette_intensity": 0.3}')

    Notes:
        - Most levels need only ONE infinite-extent volume for global settings
        - Use bounded volumes for localized effects (underwater, toxic fog, etc.)
        - Adjust settings after creation with set_post_process_settings
        - The compound tool create_environment_zone creates bounded volumes with presets
    """
    import json as _json
    parsed_settings = _json.loads(settings) if settings and settings != "{}" else None
    def _run(client):
        loc = {"x": x, "y": y, "z": z}
        return client.add_post_process_volume(
            label=label, location=loc,
            infinite_extent=infinite_extent, settings=parsed_settings)
    return _safe_call(_run)

@mcp.tool()
def set_post_process_settings(label: str, settings: str) -> str:
    """Update visual settings on an existing PostProcessVolume.

    Only specified keys are changed; unspecified keys keep their current values.
    The volume must already exist (create with add_post_process_volume first).

    Parameters:
        label (str): Actor label of the PostProcessVolume.
        settings (str): JSON object with post-process settings. All keys are optional:
            bloom_intensity (float) -- bloom glow strength. 0=off, 0.5=subtle, 1.5=strong.
            bloom_threshold (float) -- brightness threshold for bloom. Lower = more bloom.
            auto_exposure_min (float) -- minimum auto exposure in EV units.
            auto_exposure_max (float) -- maximum auto exposure in EV units.
            ambient_occlusion_intensity (float) -- AO corner darkening. 0=off, 0.5=subtle, 1=strong.
            color_saturation ({x,y,z,w}) -- RGBA saturation multiplier. {1,1,1,1}=normal, {0,0,0,1}=grayscale.
            color_contrast ({x,y,z,w}) -- RGBA contrast. {1,1,1,1}=normal.
            color_gamma ({x,y,z,w}) -- RGBA gamma correction. {1,1,1,1}=normal.
            color_gain ({x,y,z,w}) -- RGBA gain/brightness. {1,1,1,1}=normal.
            vignette_intensity (float) -- screen edge darkening. 0=off, 0.4=cinematic, 1=heavy.
            depth_of_field_focal_distance (float) -- DoF focus distance in cm from camera.
            depth_of_field_fstop (float) -- DoF aperture f-stop. Lower = more blur.
            motion_blur_amount (float) -- motion blur strength. 0=off, 0.5=cinematic, 1=strong.
            motion_blur_max (float) -- max motion blur as screen percentage.

    Returns:
        {"status": "ok", "label": "MainPP", "settings_applied": 3}

    Example:
        set_post_process_settings("MainPP", '{"bloom_intensity": 0.8, "vignette_intensity": 0.3, "auto_exposure_min": 1.0, "auto_exposure_max": 3.0}')

    Notes:
        - Color settings use {x,y,z,w} vectors where x=R, y=G, z=B, w=A (all 0-2 range)
        - For quick cinematic presets, use the compound tool create_environment_zone
    """
    import json as _json
    parsed = _json.loads(settings)
    def _run(client):
        return client.set_post_process_settings(label, parsed)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Movement Defaults Tool (Batch 1.3)
# ---------------------------------------------------------------------------

@mcp.tool()
def set_movement_defaults(blueprint: str, settings: str) -> str:
    """Set movement properties on a Blueprint's CharacterMovement or FloatingPawnMovement component.

    Automatically detects whether the Blueprint has a CharacterMovementComponent (Character
    parent) or FloatingPawnMovement (Pawn parent) and applies the appropriate settings.

    Parameters:
        blueprint (str): Blueprint asset name. Example: "BP_Player", "BP_Enemy"
        settings (str): JSON object of movement settings. Only specified keys are changed.

            For CharacterMovementComponent (Character parent):
                max_walk_speed (float) -- Walk speed in cm/s. Default: 600. FPS typical: 450-600.
                max_acceleration (float) -- How fast the character reaches max speed. Default: 2048.
                jump_z_velocity (float) -- Jump height in cm/s. Default: 420. Higher = bigger jump.
                gravity_scale (float) -- Gravity multiplier. 1.0=normal, 0.5=moon, 2.0=heavy.
                air_control (float) -- Movement control while airborne. 0=none, 0.5=moderate, 1=full.
                braking_deceleration_walking (float) -- How fast character stops. Default: 2048.
                braking_friction (float) -- Friction coefficient when braking. Default: 0.

            For FloatingPawnMovement (Pawn parent):
                max_speed (float) -- Maximum speed in cm/s. Default: 1200.
                acceleration (float) -- Acceleration rate. Default: 4000.
                deceleration (float) -- Deceleration rate. Default: 8000.
                turning_boost (float) -- Extra speed during turns.

    Returns:
        {"status": "ok", "blueprint": "BP_Player", "component_type": "CharacterMovement",
         "settings_applied": 3}

    Example:
        set_movement_defaults("BP_Player", '{"max_walk_speed": 500, "jump_z_velocity": 600, "air_control": 0.5}')
        set_movement_defaults("BP_Enemy", '{"max_speed": 800, "acceleration": 2000}')

    Notes:
        - The Blueprint must already have a movement component (Characters get one automatically,
          Pawns need FloatingPawnMovement added manually or via scaffold_pawn_blueprint)
        - For FPS controls, use setup_game_base.py which configures movement in C++
        - This modifies the Blueprint CDO; all instances inherit the change after recompile
    """
    import json as _json
    parsed = _json.loads(settings)
    def _run(client):
        return client.set_movement_defaults(blueprint, parsed)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Physics Constraint Tools (Batch 1.4)
# ---------------------------------------------------------------------------

@mcp.tool()
def add_physics_constraint(
    label: str,
    actor1: str,
    actor2: str,
    constraint_type: str = "Fixed",
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
) -> str:
    """Spawn a physics constraint between two actors to create physical connections.

    Creates a PhysicsConstraintActor that binds two actors together with the specified
    joint type. Both actors must have physics-enabled components (use set_physics_enabled first).

    Parameters:
        label (str): Label for the constraint actor in the Outliner.
        actor1 (str): Label of the first connected actor.
        actor2 (str): Label of the second connected actor.
        constraint_type (str): Joint type. Default: "Fixed".
            "Fixed" -- rigid bond, no relative movement (welded together)
            "Hinge" -- rotates around one axis (doors, hinged panels)
            "Prismatic" -- slides along one axis (pistons, elevators)
            "BallSocket" -- rotates freely in all directions (ragdoll joints, chains)
        x (float): Constraint world X position. Default: 0 (uses midpoint of actors).
        y (float): Constraint world Y position.
        z (float): Constraint world Z position.

    Returns:
        {"status": "ok", "label": "HingeJoint", "type": "Hinge", "actor1": "...", "actor2": "..."}

    Example:
        add_physics_constraint("DoorHinge", "DoorFrame", "DoorPanel", "Hinge", 100, 0, 150)
        add_physics_constraint("ChainLink", "Link1", "Link2", "BallSocket")

    Notes:
        - Both actors need physics enabled: call set_physics_enabled(True, actor_label="...") first
        - Use break_constraint to release the connection at runtime
        - The compound tool create_physics_playground sets up multiple constrained actors
        - Position the constraint at the pivot point (hinge location, slider start, etc.)
    """
    def _run(client):
        loc = {"x": x, "y": y, "z": z} if (x != 0 or y != 0 or z != 0) else None
        return client.add_physics_constraint(label, actor1, actor2,
                                              constraint_type, loc)
    return _safe_call(_run)

@mcp.tool()
def break_constraint(label: str) -> str:
    """Break (disable) a physics constraint, releasing the connected actors.

    The constraint actor remains in the level but stops enforcing the connection.
    The two previously constrained actors will move freely under physics.

    Parameters:
        label (str): Label of the PhysicsConstraintActor to break.

    Returns:
        {"status": "ok", "label": "DoorHinge", "broken": true}

    Example:
        break_constraint("DoorHinge")

    Notes:
        - The constraint actor is not deleted, just disabled
        - Once broken, cannot be re-enabled via this API (would need recreation)
        - Use this for destructible environments, breakable bridges, etc.
    """
    def _run(client):
        return client.break_constraint(label)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Sequencer Tools (Batch 2.1)
# ---------------------------------------------------------------------------

@mcp.tool()
def create_sequence(name: str, duration: float = 5.0) -> str:
    """Create a Level Sequence asset for cinematic animations and cutscenes.

    Level Sequences are UE's timeline animation system. They animate actor transforms,
    visibility, and float properties over time with keyframes. After creating a sequence,
    bind actors with add_sequence_track and set keyframes with add_keyframe.

    Parameters:
        name (str): Sequence asset name. Convention: "LS_" or "Seq_" prefix.
            Examples: "LS_Intro", "Seq_CameraFly", "LS_BossEntrance"
        duration (float): Total duration in seconds. Default: 5.0.

    Returns:
        {"status": "ok", "name": "LS_Intro", "path": "/Game/Arcwright/Sequences/LS_Intro",
         "duration": 5.0}

    Example:
        create_sequence("LS_Intro", 10.0)

    Notes:
        - Workflow: create_sequence -> add_sequence_track -> add_keyframe (repeat)
        - Use get_sequence_info to inspect an existing sequence
        - play_sequence has the same PIE limitation as play_in_editor
        - The compound tool setup_cinematic_scene creates a sequence with camera and PP in one call
    """
    def _run(client):
        return client.create_sequence(name, duration)
    return _safe_call(_run)

@mcp.tool()
def add_sequence_track(
    sequence_name: str,
    actor_label: str,
    track_type: str = "Transform",
) -> str:
    """Bind an actor to a sequence and add an animation track.

    The actor must already exist in the level. It gets bound as a Possessable in
    the sequence, then the specified track type is added for keyframing.

    Parameters:
        sequence_name (str): Name of the Level Sequence asset.
        actor_label (str): Label of the actor in the Outliner to animate.
        track_type (str): Type of animation track to add. Default: "Transform".
            "Transform" -- animate location, rotation, and scale over time
            "Visibility" -- animate show/hide state over time
            "Float" -- animate any float property (advanced)

    Returns:
        {"status": "ok", "sequence": "LS_Intro", "actor": "CinematicCamera",
         "track_type": "Transform"}

    Example:
        add_sequence_track("LS_Intro", "CinematicCamera", "Transform")
        add_sequence_track("LS_Intro", "DoorActor", "Visibility")

    Notes:
        - The actor must be placed in the level before binding
        - One actor can have multiple track types (Transform + Visibility)
        - After adding a track, use add_keyframe to set animation keys
        - An actor only needs to be bound once per sequence (not once per track)
    """
    def _run(client):
        return client.add_sequence_track(sequence_name, actor_label, track_type)
    return _safe_call(_run)

@mcp.tool()
def add_keyframe(
    sequence_name: str,
    actor_label: str,
    track_type: str,
    time: float,
    value: str,
) -> str:
    """Add a keyframe to a sequence track at a specific time point.

    The actor must already be bound to the sequence with add_sequence_track.
    UE interpolates smoothly between keyframes.

    Parameters:
        sequence_name (str): Name of the Level Sequence asset.
        actor_label (str): Label of the bound actor.
        track_type (str): Track type matching what was added ("Transform", "Visibility", "Float").
        time (float): Time in seconds from sequence start. Must be within the sequence duration.
        value (str): JSON value appropriate for the track type:
            Transform: '{"location":{"x":0,"y":0,"z":100},"rotation":{"pitch":0,"yaw":45,"roll":0}}'
                Each sub-key (location, rotation, scale) is optional. Omitted = unchanged.
            Visibility: '"true"' or '"false"'
            Float: '"1.5"' (numeric value as string)

    Returns:
        {"status": "ok", "sequence": "LS_Intro", "actor": "CinematicCamera",
         "track_type": "Transform", "time": 2.5}

    Example:
        # Camera flies from origin to (0,0,500) over 5 seconds
        add_keyframe("LS_Intro", "Camera", "Transform", 0.0, '{"location":{"x":0,"y":0,"z":100}}')
        add_keyframe("LS_Intro", "Camera", "Transform", 5.0, '{"location":{"x":0,"y":0,"z":500}}')

        # Door becomes visible at 3 seconds
        add_keyframe("LS_Intro", "Door", "Visibility", 0.0, 'false')
        add_keyframe("LS_Intro", "Door", "Visibility", 3.0, 'true')

    Notes:
        - Multiple keyframes at different times create smooth animations
        - Transform values are in world space (cm for location, degrees for rotation)
        - Keyframes can be added in any order -- they are sorted by time internally
    """
    import json as _json
    parsed = _json.loads(value)
    def _run(client):
        return client.add_keyframe(sequence_name, actor_label, track_type, time, parsed)
    return _safe_call(_run)

@mcp.tool()
def get_sequence_info(name: str) -> str:
    """Query a Level Sequence's structure: duration, tracks, bound actors, and keyframe counts.

    Parameters:
        name (str): Sequence asset name. Example: "LS_Intro"

    Returns:
        {"name": "LS_Intro", "path": "/Game/...", "duration": 10.0,
         "tracks": [{"actor": "Camera", "type": "Transform", "keyframes": 3}],
         "bound_actors": ["Camera", "Door"]}

    Example:
        get_sequence_info("LS_Intro")

    Notes:
        - Use this to inspect a sequence before adding more keyframes
        - Bound actors must still exist in the level for the sequence to play
    """
    def _run(client):
        return client.get_sequence_info(name)
    return _safe_call(_run)

@mcp.tool()
def play_sequence(name: str) -> str:
    """Play a Level Sequence in editor preview mode.

    Parameters:
        name (str): Sequence asset name to play.

    Returns:
        {"status": "ok", "sequence": "LS_Intro"}

    Example:
        play_sequence("LS_Intro")

    Notes:
        - Has the same PIE limitation as play_in_editor: the request is queued but
          UE 5.7's engine tick may not process it. User must click Play manually.
        - The sequence will play using the bound actors currently in the level
    """
    def _run(client):
        return client.play_sequence(name)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Landscape/Foliage Tools (Batch 2.2)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_landscape_info() -> str:
    """Query whether a landscape exists in the current level and get its properties.

    Safe to call even if no landscape exists -- returns {"has_landscape": false}.

    Returns:
        If landscape exists:
            {"has_landscape": true, "bounds": {"min": {x,y,z}, "max": {x,y,z}},
             "component_count": 4, "material": "/Game/Materials/M_Landscape"}
        If no landscape:
            {"has_landscape": false}

    Example:
        get_landscape_info()

    Notes:
        - Landscapes must be created manually in the UE Editor (too complex for TCP creation)
        - Use set_landscape_material to apply materials to an existing landscape
        - For simple ground surfaces, use spawn_actor with a scaled Plane mesh instead
    """
    return _safe_call(lambda c: c.get_landscape_info())

@mcp.tool()
def set_landscape_material(material_path: str) -> str:
    """Apply a material to the level's landscape actor.

    A landscape must already exist in the level. Use get_landscape_info to verify first.

    Parameters:
        material_path (str): Full UE material asset path.
            Example: "/Game/Materials/M_Grass", "/Game/Arcwright/Materials/MAT_Terrain"

    Returns:
        {"status": "ok", "material": "/Game/Materials/M_Grass"}

    Example:
        set_landscape_material("/Game/Arcwright/Materials/MAT_Terrain")

    Notes:
        - Requires an existing landscape (created manually in editor)
        - Returns an error if no landscape exists -- check with get_landscape_info first
        - Landscape materials are typically multi-layer with blend masks
    """
    def _run(client):
        return client.set_landscape_material(material_path)
    return _safe_call(_run)

@mcp.tool()
def create_foliage_type(
    name: str,
    mesh: str = "",
    density: float = 100.0,
    scale_min: float = 1.0,
    scale_max: float = 1.0,
) -> str:
    """Create a foliage type asset that defines how a mesh is scattered procedurally.

    Foliage types specify the mesh, density, and scale randomization for procedural
    foliage placement. After creating a foliage type, use paint_foliage to place
    instances in the level.

    Parameters:
        name (str): Asset name. Convention: "FT_" prefix. Example: "FT_Rocks", "FT_Grass", "FT_Trees"
        mesh (str): Static mesh asset path for the foliage. Default: Sphere placeholder.
            Example: "/Game/Arcwright/Meshes/SM_Bush", "/Engine/BasicShapes/Cone.Cone"
        density (float): Instances per area unit (higher = denser placement). Default: 100.
        scale_min (float): Minimum random scale for instances. Default: 1.0.
        scale_max (float): Maximum random scale for instances. Default: 1.0.
            Use different min/max for natural size variation (e.g. 0.8 to 1.5).

    Returns:
        {"status": "ok", "name": "FT_Rocks", "path": "/Game/Arcwright/Foliage/FT_Rocks"}

    Example:
        create_foliage_type("FT_Rocks", "/Game/Arcwright/Meshes/SM_Rock", 50.0, 0.5, 2.0)
        create_foliage_type("FT_Grass", "/Game/Meshes/SM_GrassTuft", 200.0, 0.8, 1.2)

    Notes:
        - After creating, use paint_foliage to place instances in the level
        - Each instance gets a random scale between scale_min and scale_max
        - Foliage instances are optimized with instanced static mesh rendering
        - Use get_foliage_info to see all foliage types and instance counts
    """
    def _run(client):
        return client.create_foliage_type(name, mesh, density, scale_min, scale_max)
    return _safe_call(_run)

@mcp.tool()
def paint_foliage(
    foliage_type: str,
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    radius: float = 500.0,
    count: int = 10,
) -> str:
    """Paint foliage instances in a circular area around a center point.

    Places instances with random positions within the specified radius, performs a
    downward line trace to snap each to the ground surface, and applies random rotation
    and scale variation (defined by the foliage type's scale_min/scale_max).

    Parameters:
        foliage_type (str): Foliage type asset path from create_foliage_type.
            Example: "/Game/Arcwright/Foliage/FT_Rocks"
        x (float): Center X position in world space. Default: 0.
        y (float): Center Y position in world space. Default: 0.
        z (float): Center Z position in world space. Default: 0. (Ground trace starts from here.)
        radius (float): Placement radius in cm. Default: 500. Instances scatter randomly within this circle.
        count (int): Number of foliage instances to place. Default: 10.

    Returns:
        {"status": "ok", "foliage_type": "FT_Rocks", "instances_placed": 10}

    Example:
        paint_foliage("/Game/Arcwright/Foliage/FT_Rocks", 0, 0, 500, 1000, 25)
        paint_foliage("/Game/Arcwright/Foliage/FT_Grass", 2000, 0, 100, 800, 50)

    Notes:
        - The foliage type must be created first with create_foliage_type
        - Instances snap to whatever surface is below the center z -- place center above ground
        - Each instance gets random yaw rotation and random scale per the foliage type's range
        - Use get_foliage_info to verify placement counts after painting
        - For scattering game actors (not instanced meshes), use scatter_actors instead
    """
    def _run(client):
        return client.paint_foliage(foliage_type,
                                     {"x": x, "y": y, "z": z},
                                     radius, count)
    return _safe_call(_run)

@mcp.tool()
def get_foliage_info() -> str:
    """List all foliage types in the level and how many instances of each are placed.

    Returns a summary of every foliage type that has been painted into the current level,
    including the mesh used and the number of placed instances.

    Returns:
        {"foliage_types": 2, "total_instances": 35,
         "types": [
             {"path": "/Game/Arcwright/Foliage/FT_Rocks", "mesh": "SM_Rock", "instances": 25},
             {"path": "/Game/Arcwright/Foliage/FT_Grass", "mesh": "SM_GrassTuft", "instances": 10}
         ]}

    Example:
        get_foliage_info()

    Notes:
        - Returns empty list if no foliage has been painted
        - Instance counts include all paint_foliage calls (cumulative)
        - Use create_foliage_type + paint_foliage to add foliage to the level
    """
    return _safe_call(lambda c: c.get_foliage_info())

# ---------------------------------------------------------------------------
# Asset Import Tools (B31-B33)
# ---------------------------------------------------------------------------

@mcp.tool()
def import_static_mesh(file_path: str, asset_name: str, destination: str = "") -> str:
    """Import a .fbx or .obj 3D model file into Unreal Engine as a StaticMesh asset.

    Use this to bring 3D models from Blender, Maya, or other DCC tools into UE5.
    The resulting asset path can be used with add_component (mesh property),
    set_component_property (static_mesh), or create_foliage_type.

    Parameters:
        file_path (str): Absolute Windows file path to the .fbx or .obj file.
            Example: "C:/Arcwright/exports/Crystal.fbx"
        asset_name (str): Name for the UE asset. Convention: "SM_" prefix.
            Example: "SM_HealthCrystal", "SM_Rock", "SM_Table"
        destination (str): UE content path for the asset. Default: "/Game/Arcwright/Meshes/".
            Example: "/Game/Props/Meshes/"

    Returns:
        {"status": "ok", "asset_name": "SM_HealthCrystal",
         "asset_path": "/Game/Arcwright/Meshes/SM_HealthCrystal"}

    Example:
        import_static_mesh("C:/Arcwright/exports/Crystal.fbx", "SM_HealthCrystal")
        import_static_mesh("C:/Models/Table.obj", "SM_Table", "/Game/Props/Meshes/")

    Notes:
        - If an asset with the same name already exists, returns the existing asset info
          without re-importing (re-import crashes UE). Delete first with delete_blueprint
          if you need to re-import a changed file
        - For the full Blender-to-UE pipeline, use the compound tool import_and_apply_mesh
        - Uses UFactory::StaticImportObject (not ImportAssetsAutomated, which crashes in TCP context)
        - Supported formats: .fbx (recommended), .obj
    """
    def _run(client):
        return client.import_static_mesh(file_path, asset_name, destination)
    return _safe_call(_run)

@mcp.tool()
def import_texture(file_path: str, asset_name: str, destination: str = "") -> str:
    """Import a .png, .jpg, or .tga image file into Unreal Engine as a Texture2D asset.

    Use imported textures with create_textured_material or as texture parameters
    in material instances.

    Parameters:
        file_path (str): Absolute Windows file path to the image file.
            Example: "C:/Arcwright/exports/T_StoneWall.png"
        asset_name (str): Name for the UE asset. Convention: "T_" prefix.
            Example: "T_CrystalNormal", "T_BrickDiffuse", "T_WoodRoughness"
        destination (str): UE content path for the asset. Default: "/Game/Arcwright/Textures/".

    Returns:
        {"status": "ok", "asset_name": "T_StoneWall",
         "asset_path": "/Game/Arcwright/Textures/T_StoneWall"}

    Example:
        import_texture("C:/Arcwright/exports/T_StoneWall.png", "T_StoneWall")

    Notes:
        - If a texture with the same name exists, returns existing info without re-importing
        - For the full texture+material pipeline, use the compound tool import_texture_and_create_material
        - Supported formats: .png (recommended), .jpg, .tga
        - Textures from Blender procedural bakes should be 1024x1024 or 2048x2048
    """
    def _run(client):
        return client.import_texture(file_path, asset_name, destination)
    return _safe_call(_run)

@mcp.tool()
def import_sound(file_path: str, asset_name: str, destination: str = "") -> str:
    """Import a .wav, .ogg, or .mp3 audio file into Unreal Engine as a SoundWave asset.

    Imported sounds can be used with play_sound_at_location, add_audio_component,
    or referenced in Blueprints.

    Parameters:
        file_path (str): Absolute Windows file path to the audio file.
            Example: "C:/Arcwright/exports/PickupChime.wav"
        asset_name (str): Name for the UE asset. Convention: "SFX_" prefix.
            Example: "SFX_PickupChime", "SFX_Explosion", "SFX_Footstep"
        destination (str): UE content path for the asset. Default: "/Game/Arcwright/Sounds/".

    Returns:
        {"status": "ok", "asset_name": "SFX_PickupChime",
         "asset_path": "/Game/Arcwright/Sounds/SFX_PickupChime"}

    Example:
        import_sound("C:/Sounds/PickupChime.wav", "SFX_PickupChime")

    Notes:
        - If a sound with the same name exists, returns existing info without re-importing
          (re-import can hang on in-use audio assets)
        - To re-import: delete with delete_blueprint first, then import again
        - Supported formats: .wav (recommended), .ogg, .mp3
        - .wav files import fastest and most reliably
    """
    def _run(client):
        return client.import_sound(file_path, asset_name, destination)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# HTML → Widget Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_widget_from_html(html: str, widget_name: str = "WBP_Generated") -> str:
    """Create a Widget Blueprint in Unreal Engine from an HTML/CSS mockup.

    Design your game HUD in HTML and CSS, then this tool translates it into a real
    UE Widget Blueprint with all the visual elements positioned and styled to match.
    Combines create_widget_blueprint + add_widget_child + set_widget_property into one call.

    Parameters:
        html (str): HTML string with embedded CSS. Can be a full page or fragment.
            Supported elements:
                div (position:absolute) -> CanvasPanel
                div (display:flex, row) -> HorizontalBox
                div (display:flex, column) -> VerticalBox
                div (default) -> VerticalBox
                h1-h6, p, span, label -> TextBlock (font size from tag/CSS)
                button -> Button
                img -> Image
                input -> EditableText
                div[data-widget="progress"] -> ProgressBar
                div.health-bar (class heuristic) -> ProgressBar
            Supported CSS: color, font-size, text-align, position, width, height,
                opacity, display (flex/grid), flex-direction, visibility
        widget_name (str): Name for the Widget Blueprint. Convention: "WBP_" prefix.
            Default: "WBP_Generated". Example: "WBP_SciFiHUD", "WBP_MainMenu"

    Returns:
        {"widget_name": "WBP_SciFiHUD", "widget_count": 33,
         "commands_executed": 127, "commands_failed": 0,
         "errors": [], "warnings": []}

    Example:
        create_widget_from_html('<div style="position:absolute;left:20px;top:20px"><p style="color:white;font-size:24px">Score: 0</p></div>', "WBP_ScoreHUD")

    Notes:
        - Design at 1920x1080 resolution for standard game HUDs
        - Use data-widget-name="MyName" on elements to control UE widget names
        - Use data-widget="progress" with data-percent="75" for progress bars
        - Use id attributes for guaranteed unique widget names
        - CSS classes in <style> blocks are parsed automatically
        - For simpler HUDs, the compound tool create_game_hud provides a quicker preset
        - Tested: 33-widget sci-fi HUD with 127 commands, 0 failures
    """
    # Import the translator
    _html_widget_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "html_to_widget")
    if _html_widget_dir not in sys.path:
        sys.path.insert(0, _html_widget_dir)
    from html_to_widget import translate_html_to_widget as _translate, execute_commands as _execute

    # Step 1: Translate HTML to widget commands
    result = _translate(html, widget_name=widget_name)

    if not result["commands"]:
        return json.dumps({
            "error": "No widgets could be parsed from the HTML",
            "warnings": result.get("warnings", []),
        })

    # Step 2: Execute all commands against UE
    try:
        client = _get_client()
    except (ConnectionRefusedError, OSError, TimeoutError) as e:
        return json.dumps({
            "error": f"Cannot connect to UE command server at {UE_HOST}:{UE_PORT}. "
                     f"Is Unreal Editor running with the Arcwright plugin? ({e})",
            "commands_generated": len(result["commands"]),
            "widget_count": result["widget_count"],
        })

    try:
        exec_result = _execute(result["commands"], client)
    except Exception as e:
        return json.dumps({"error": f"Execution failed: {e}"})
    finally:
        client.close()

    return json.dumps({
        "widget_name": result["widget_name"],
        "widget_count": result["widget_count"],
        "commands_executed": exec_result["success"],
        "commands_failed": exec_result["failed"],
        "errors": exec_result["errors"][:10],  # Cap error list
        "warnings": result.get("warnings", []),
    }, indent=2)

# ---------------------------------------------------------------------------
# Query Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def find_blueprints(name_filter: str = "", parent_class: str = "",
                    has_variable: str = "", has_component: str = "",
                    path: str = "") -> str:
    """Search for Blueprint assets in the project by name, parent class, variables, or components.

    Returns matching Blueprints with their name, path, parent class, variables list,
    components list, and compile status. Use this to discover what Blueprints exist
    before modifying them with modify_blueprint, batch_set_variable, or batch_add_component.

    Parameters:
        name_filter (str): Case-insensitive substring to match Blueprint names.
            Example: "Enemy" matches BP_Enemy, BP_EnemyBoss, BP_SmallEnemy
        parent_class (str): Filter by parent class name.
            Common values: "Actor", "Pawn", "Character", "PlayerController", "GameModeBase", "AIController"
        has_variable (str): Only return BPs containing a variable with this name substring.
            Example: "Health" matches Blueprints with Health, MaxHealth, HealthRegen
        has_component (str): Only return BPs containing this component type.
            Example: "PointLight", "StaticMesh", "BoxCollision"
        path (str): Content path to search. Default: all under /Game/.
            Example: "/Game/Arcwright/Generated" for only Arcwright-generated BPs

    Returns:
        {"blueprints": [
            {"name": "BP_Enemy", "path": "/Game/Arcwright/Generated/BP_Enemy",
             "parent_class": "Pawn", "compiled": true,
             "variables": [{"name": "Health", "type": "Float"}],
             "components": [{"name": "EnemyMesh", "type": "StaticMeshComponent"}]}
        ], "count": 1}

    Example:
        find_blueprints(name_filter="Enemy")                    # find all enemy BPs
        find_blueprints(parent_class="Pawn")                    # find all Pawn BPs
        find_blueprints(has_variable="Health")                  # find BPs with Health variable
        find_blueprints(name_filter="BP_", has_component="PointLight")  # BPs with lights

    Notes:
        - All filters are combined with AND logic -- all specified filters must match
        - For searching placed actors in the level (not BP assets), use find_actors instead
        - For searching non-Blueprint assets (materials, textures, meshes), use find_assets
        - For a quick list of all Blueprint names without detail, use list_available_blueprints
    """
    def _run(client):
        return client.find_blueprints(
            name_filter=name_filter, parent_class=parent_class,
            has_variable=has_variable, has_component=has_component, path=path)
    return _safe_call(_run)

@mcp.tool()
def find_actors(name_filter: str = "", class_filter: str = "",
                tag: str = "", has_component: str = "",
                material_name: str = "", radius: float = 0,
                center_x: float = 0, center_y: float = 0, center_z: float = 0) -> str:
    """Search for placed actors in the current level with advanced filtering.

    More powerful than get_actors -- supports filtering by name, class, tags, component types,
    materials, and spatial proximity. Returns matching actors with their label, class, location,
    tags, and component list.

    Parameters:
        name_filter (str): Substring match on actor label (case-insensitive).
            Example: "Enemy" matches "Enemy_1", "BossEnemy_2"
        class_filter (str): Substring match on actor class name.
            Example: "BP_Enemy" matches BP_Enemy_C instances. "Light" matches all light types.
        tag (str): Only return actors with this exact tag.
            Example: "Destructible", "Team_Red". Tags are set via set_actor_tags.
        has_component (str): Only return actors containing this component type.
            Example: "PointLight", "AudioComponent", "NiagaraComponent"
        material_name (str): Only return actors with this material applied to any mesh.
            Example: "MAT_Gold", "MAT_Concrete"
        radius (float): Search within this distance (cm) of the center point. 0 = no spatial filter.
        center_x (float): X coordinate of spatial search center (used with radius).
        center_y (float): Y coordinate of spatial search center.
        center_z (float): Z coordinate of spatial search center.

    Returns:
        {"actors": [
            {"label": "Enemy_1", "class": "BP_Enemy_C",
             "location": {"x":500,"y":200,"z":50},
             "tags": ["Hostile"], "components": ["EnemyMesh", "OverlapSphere"]}
        ], "count": 1}

    Example:
        find_actors(class_filter="BP_Enemy")                     # all enemy instances
        find_actors(tag="Destructible")                          # all destructible actors
        find_actors(radius=1000, center_x=0, center_y=0, center_z=0)  # actors within 10m of origin
        find_actors(material_name="MAT_Gold")                    # actors with gold material

    Notes:
        - All filters are combined with AND logic
        - For simpler listing without filters, use get_actors instead
        - For searching Blueprint assets (not placed instances), use find_blueprints
        - The labels returned can be used with move_actor, delete_actor, set_actor_material,
          batch_delete_actors, batch_move_actors, etc.
        - Spatial search (radius) uses Euclidean distance in 3D
    """
    def _run(client):
        kwargs = {}
        if name_filter: kwargs["name_filter"] = name_filter
        if class_filter: kwargs["class_filter"] = class_filter
        if tag: kwargs["tag"] = tag
        if has_component: kwargs["has_component"] = has_component
        if material_name: kwargs["material_name"] = material_name
        if radius > 0:
            kwargs["radius"] = radius
            kwargs["center"] = {"x": center_x, "y": center_y, "z": center_z}
        return client.find_actors(**kwargs)
    return _safe_call(_run)

@mcp.tool()
def find_assets(asset_type: str = "", name_filter: str = "",
                path: str = "", max_results: int = 100) -> str:
    """Search the Unreal Engine asset registry for any type of asset by type, name, and path.

    This is the most versatile asset discovery tool -- it searches across all asset types.
    For type-specific searches, also consider list_available_materials or list_available_blueprints.

    Parameters:
        asset_type (str): Filter by asset type. Common values:
            "Blueprint" -- Blueprint class assets
            "Material" -- UMaterial assets (created by create_simple_material)
            "MaterialInstanceConstant" -- MaterialInstance assets
            "Texture2D" -- Imported texture assets
            "StaticMesh" -- Imported 3D mesh assets
            "SoundWave" -- Imported audio assets
            "BehaviorTree" -- AI behavior tree assets
            "DataTable" -- Data table assets
            "NiagaraSystem" -- Particle system assets
            "LevelSequence" -- Cinematic sequence assets
            "WidgetBlueprint" -- UMG Widget Blueprint assets
        name_filter (str): Case-insensitive substring to match asset names.
            Example: "Enemy" matches BP_Enemy, T_EnemySkin, MAT_EnemyArmor
        path (str): Content path to search. Default: "/Game/" (all project assets).
            Use "/Game/Arcwright/" for Arcwright-generated assets only.
        max_results (int): Maximum number of results to return. Default: 100.

    Returns:
        {"assets": [
            {"name": "MAT_Gold", "path": "/Game/Arcwright/Materials/MAT_Gold", "type": "Material"}
        ], "count": 1}

    Example:
        find_assets(asset_type="Material")                      # all materials in project
        find_assets(asset_type="StaticMesh", path="/Game/Arcwright/Meshes/")  # imported meshes
        find_assets(name_filter="Enemy")                        # any asset with "Enemy" in name
        find_assets(asset_type="SoundWave", name_filter="pickup")  # sound effects for pickups

    Notes:
        - This searches the asset registry (Content Browser), not placed actors in the level.
          For placed actors, use find_actors instead
        - For Blueprints specifically, find_blueprints provides richer detail (variables, components)
        - Asset paths returned can be used directly in set_actor_material, apply_material,
          set_component_property, import operations, etc.
        - The asset_type filter uses UE class names -- "Material" not "UMaterial"
    """
    def _run(client):
        return client.find_assets(asset_type=asset_type, name_filter=name_filter,
                                  path=path, max_results=max_results)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Batch Modify Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def batch_set_variable(operations_json: str) -> str:
    """Set variable default values on multiple Blueprints in a single batch call.

    Fault-tolerant: if one operation fails (e.g. Blueprint not found), the rest still succeed.
    All affected Blueprints are batch-compiled once after all operations complete.

    Parameters:
        operations_json (str): JSON array of operations. Each element must have:
            - "blueprint" (str): Blueprint name (e.g. "BP_Enemy")
            - "variable_name" (str): Variable name to set (must already exist on the BP)
            - "default_value" (str): New default value as string (e.g. "200", "true", "1.0,0.0,0.0")

    Returns:
        {"succeeded": 2, "failed": 0, "results": [{"blueprint": "BP_Enemy", "status": "ok"}, ...], "errors": []}

    Example:
        batch_set_variable('[{"blueprint":"BP_Enemy","variable_name":"Health","default_value":"200"},
                             {"blueprint":"BP_Boss","variable_name":"Health","default_value":"1000"},
                             {"blueprint":"BP_Boss","variable_name":"Speed","default_value":"300"}]')

    Notes:
        - Variables must already exist on the Blueprint. Use modify_blueprint to add new variables first
        - For setting a single variable, use set_variable_default instead
        - All affected Blueprints are batch-compiled (deduplicated) for efficiency
        - The default_value is always a string -- use "100" not 100, "true" not true
        - To find Blueprints with a specific variable, use find_blueprints(has_variable="Health")

    Common mistakes:
        - Passing raw JSON values instead of strings for default_value (use "200" not 200)
        - Trying to set variables that don't exist on the Blueprint (add them first with modify_blueprint)
    """
    def _run(client):
        ops = json.loads(operations_json)
        return client.batch_set_variable(ops)
    return _safe_call(_run)

@mcp.tool()
def batch_add_component(operations_json: str) -> str:
    """Add SCS components to multiple Blueprints in a single batch call.

    Fault-tolerant: if one operation fails (e.g., Blueprint not found), the rest still succeed.
    All affected Blueprints are batch-compiled once after all operations complete.

    Parameters:
        operations_json (str): JSON array of operations. Each element must have:
            - "blueprint" (str): Blueprint name (e.g. "BP_Enemy")
            - "component_type" (str): Component type to add. Valid types:
                "BoxCollision", "SphereCollision", "CapsuleCollision", "StaticMesh",
                "PointLight", "SpotLight", "Audio", "Arrow", "Scene", "Camera", "SpringArm"
            - "component_name" (str): Name for the new component (e.g. "OverlapBox")
            - "properties" (object, optional): Component-specific properties:
                BoxCollision: {"extent": {"x":50,"y":50,"z":50}, "generate_overlap_events": true}
                StaticMesh: {"mesh": "/Engine/BasicShapes/Sphere.Sphere"}
                PointLight: {"intensity": 5000, "light_color": {"r":1,"g":0.8,"b":0.5}}

    Returns:
        {"succeeded": 3, "failed": 0, "results": [...], "errors": []}

    Example:
        batch_add_component('[{"blueprint":"BP_Enemy","component_type":"SphereCollision","component_name":"DetectSphere","properties":{"radius":500}},
                              {"blueprint":"BP_Pickup","component_type":"PointLight","component_name":"Glow","properties":{"intensity":3000}}]')

    Notes:
        - Components are added to the Blueprint's SCS (SimpleConstructionScript)
        - Already-placed actors need to be re-spawned to pick up new components
        - For adding a single component, use add_component instead
        - For a full list of supported component types, see add_component
    """
    def _run(client):
        ops = json.loads(operations_json)
        return client.batch_add_component(ops)
    return _safe_call(_run)

@mcp.tool()
def batch_apply_material(operations_json: str) -> str:
    """Apply materials to multiple placed actors or Blueprint templates in a single batch call.

    Each operation targets either a placed actor (by actor_label) or a Blueprint component
    template (by blueprint + component_name). Fault-tolerant: individual failures do not
    abort the batch.

    Parameters:
        operations_json (str): JSON array of operations. Each element must have:
            For placed actors:
                - "actor_label" (str): Label of the placed actor (e.g. "Wall_1")
                - "material_path" (str): Full UE material path (e.g. "/Game/Arcwright/Materials/MAT_Concrete")
                - "slot" (int, optional): Material slot index. Default: 0
            For Blueprint templates:
                - "blueprint" (str): Blueprint name (e.g. "BP_Pickup")
                - "material_path" (str): Full UE material path
                - "component_name" (str): SCS component name (e.g. "PickupMesh")

    Returns:
        {"succeeded": 2, "failed": 0, "results": [{"actor_label": "Wall_1", "status": "ok"}, ...], "errors": []}

    Example:
        batch_apply_material('[{"actor_label":"Wall_1","material_path":"/Game/Arcwright/Materials/MAT_Concrete"},
                               {"actor_label":"Wall_2","material_path":"/Game/Arcwright/Materials/MAT_Concrete"},
                               {"actor_label":"Floor","material_path":"/Game/Arcwright/Materials/MAT_Stone"}]')

    Notes:
        - For placed actors, this calls set_actor_material under the hood (reliable, works on registered actors)
        - For Blueprint templates, SCS OverrideMaterials may not persist on spawned instances.
          Prefer actor_label targeting on placed actors for reliable results
        - To swap ALL occurrences of one material with another across the entire level,
          use batch_replace_material instead
        - Materials must already exist. Create them first with create_simple_material,
          create_textured_material, or create_material_instance
        - Use find_assets(asset_type="Material") to discover available material paths

    Common mistakes:
        - Using short material names instead of full paths (use "/Game/Arcwright/Materials/MAT_Gold")
        - Targeting Blueprint templates instead of placed actors (SCS materials may not persist)
    """
    def _run(client):
        ops = json.loads(operations_json)
        return client.batch_apply_material(ops)
    return _safe_call(_run)

@mcp.tool()
def batch_set_property(operations_json: str) -> str:
    """Set properties on multiple placed actors in one batch call.

    Supports location, rotation, scale, visibility, and tags. Can operate in absolute
    or relative mode (add to existing value). Fault-tolerant: individual failures do not
    abort the batch.

    Parameters:
        operations_json (str): JSON array of operations. Each element must have:
            - "actor_label" (str): Label of the placed actor
            - "property" (str): Property to set. Values:
                "location" -- world position {x,y,z}
                "rotation" -- rotation {pitch,yaw,roll}
                "scale" -- scale {x,y,z}
                "visibility" -- show/hide (bool)
                "tag" -- actor tag (string)
            - "value": Value appropriate for the property type (object, bool, or string)
            - "relative" (bool, optional): If true, adds to current value instead of replacing.
                Default: false. Only applies to location/rotation/scale.

    Returns:
        {"succeeded": 3, "failed": 0, "results": [...], "errors": []}

    Example:
        batch_set_property('[{"actor_label":"Enemy_1","property":"location","value":{"x":100,"y":0,"z":0},"relative":true},
                             {"actor_label":"Enemy_2","property":"scale","value":{"x":2,"y":2,"z":2}},
                             {"actor_label":"Wall_1","property":"visibility","value":false}]')

    Notes:
        - For bulk location changes, batch_move_actors is more convenient (supports filters)
        - For bulk scale changes, batch_scale_actors is more convenient (supports filters)
        - Tags set here can be used as filters in find_actors, batch_delete_actors, etc.
        - Relative mode is useful for "nudge all enemies 100 units right" patterns
    """
    def _run(client):
        ops = json.loads(operations_json)
        return client.batch_set_property(ops)
    return _safe_call(_run)

@mcp.tool()
def batch_delete_actors(labels: str = "", class_filter: str = "", tag: str = "") -> str:
    """Delete multiple actors from the level by labels, class filter, or tag.

    Idempotent: already-deleted or missing actors count as success (not errors).
    At least one filter parameter is required.

    Parameters:
        labels (str): Comma-separated actor labels to delete.
            Example: "Enemy_1,Enemy_2,Enemy_3"
        class_filter (str): Delete ALL actors whose class name contains this substring.
            Example: "BP_Enemy" deletes every BP_Enemy_C instance in the level.
            WARNING: this deletes all matching actors with no undo.
        tag (str): Delete ALL actors with this exact tag.
            Example: "Destructible" deletes every actor tagged "Destructible".

    Returns:
        {"deleted": 3, "not_found": 0, "details": [{"label": "Enemy_1", "status": "deleted"}, ...]}

    Example:
        batch_delete_actors(labels="Enemy_1,Enemy_2,Enemy_3")
        batch_delete_actors(class_filter="BP_Enemy")
        batch_delete_actors(tag="Destructible")

    Notes:
        - At least one parameter must be provided (labels, class_filter, or tag)
        - Filters can be combined (AND logic) but typically one is used
        - There is no batch_delete_blueprints command -- use delete_blueprint for assets
        - For selective removal, first use find_actors to see what matches your filter
        - The compound tool clear_and_rebuild_level deletes all and rebuilds from scratch
    """
    def _run(client):
        label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else None
        return client.batch_delete_actors(labels=label_list, class_filter=class_filter, tag=tag)
    return _safe_call(_run)

@mcp.tool()
def batch_replace_material(old_material: str, new_material: str) -> str:
    """Replace every occurrence of one material with another across all actors in the level.

    Scans all placed actors, finds any mesh component using the old material, and swaps
    it to the new material. Useful for global theme changes (e.g., replace all stone with brick).

    Parameters:
        old_material (str): Full UE path of the material to find and replace.
            Example: "/Game/Arcwright/Materials/MAT_Stone"
        new_material (str): Full UE path of the replacement material.
            Example: "/Game/Arcwright/Materials/MAT_Brick"

    Returns:
        {"status": "ok", "replacements": 12, "affected_actors": ["Wall_1", "Wall_2", "Floor"]}

    Example:
        batch_replace_material("/Game/Arcwright/Materials/MAT_Stone", "/Game/Arcwright/Materials/MAT_Brick")

    Notes:
        - Both materials must already exist. Create with create_simple_material first if needed
        - This replaces on placed actors, not on Blueprint templates
        - For applying different materials to specific actors, use batch_apply_material instead
        - Use find_assets(asset_type="Material") to discover available material paths
    """
    def _run(client):
        return client.batch_replace_material(old_material, new_material)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# In-Place Modify Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def modify_blueprint(name: str, add_variables_json: str = "",
                     remove_variables_json: str = "",
                     set_class_defaults_json: str = "") -> str:
    """Modify an existing Blueprint in-place: add/remove variables and set class defaults.

    Performs all operations in one call and compiles once after all changes. No need to
    delete and recreate the Blueprint.

    Parameters:
        name (str): Blueprint name to modify. Example: "BP_Enemy"
        add_variables_json (str): JSON array of variables to add. Each element:
            {"name": "Health", "type": "float", "default": "100"}
            Supported types: float, int, bool, string, name, text, vector, rotator
            Default: "" (no variables added)
        remove_variables_json (str): JSON array of variable name strings to remove.
            Example: '["OldVar", "UnusedVar"]'
            Default: "" (no variables removed)
        set_class_defaults_json (str): JSON object of CDO (Class Default Object) properties.
            Uses generic UPROPERTY reflection -- any property discoverable by FindPropertyByName.
            Example: '{"AutoPossessAI": "PlacedInWorldOrSpawned", "bCanBeDamaged": true}'
            Default: "" (no CDO changes)

    Returns:
        {"status": "ok", "blueprint": "BP_Enemy", "variables_added": 1,
         "variables_removed": 1, "defaults_set": 2, "compiled": true}

    Example:
        modify_blueprint("BP_Enemy",
            add_variables_json='[{"name":"Health","type":"float","default":"200"},{"name":"IsAlive","type":"bool","default":"true"}]',
            remove_variables_json='["OldScore"]',
            set_class_defaults_json='{"AutoPossessAI":"PlacedInWorldOrSpawned"}')

    Notes:
        - For setting variable defaults across multiple BPs, use batch_set_variable
        - Variables added here can then be used in batch_set_variable
        - CDO properties are the same ones accessible via set_class_defaults
        - Already-placed actors may need re-spawning to pick up variable changes
        - Use get_blueprint_details to inspect the Blueprint before/after modification
    """
    def _run(client):
        add_vars = json.loads(add_variables_json) if add_variables_json else None
        remove_vars = json.loads(remove_variables_json) if remove_variables_json else None
        class_defaults = json.loads(set_class_defaults_json) if set_class_defaults_json else None
        return client.modify_blueprint(name, add_variables=add_vars,
                                       remove_variables=remove_vars,
                                       set_class_defaults=class_defaults)
    return _safe_call(_run)

@mcp.tool()
def rename_asset(old_name: str, new_name: str) -> str:
    """Rename a Blueprint or other asset in the Content Browser.

    UE creates redirectors automatically so existing references (Blueprints, levels)
    continue to resolve. The asset is moved/renamed in-place.

    Parameters:
        old_name (str): Current asset name. Example: "BP_Pickup"
        new_name (str): Desired new name. Example: "BP_CoinPickup"

    Returns:
        {"status": "ok", "old_name": "BP_Pickup", "new_name": "BP_CoinPickup",
         "new_path": "/Game/Arcwright/Generated/BP_CoinPickup"}

    Example:
        rename_asset("BP_Pickup", "BP_CoinPickup")

    Notes:
        - UE creates a redirector from the old path to the new path
        - Already-placed actors referencing the old name should auto-update via the redirector
        - For Blueprints with complex references, test that placed instances still work after rename
        - To change a Blueprint's parent class (not name), use reparent_blueprint instead
    """
    def _run(client):
        return client.rename_asset(old_name, new_name)
    return _safe_call(_run)

@mcp.tool()
def reparent_blueprint(name: str, new_parent: str) -> str:
    """Change a Blueprint's parent class to a different native or Blueprint class.

    The Blueprint is recompiled after reparenting. Existing nodes are refreshed, but
    nodes incompatible with the new parent class may produce compile warnings.

    Parameters:
        name (str): Blueprint name to reparent. Example: "BP_Enemy"
        new_parent (str): New parent class. Can be a native class name or another Blueprint path.
            Native: "Actor", "Pawn", "Character", "PlayerController", "GameModeBase", "AIController"
            Blueprint: "/Game/Arcwright/Generated/BP_BaseEnemy"

    Returns:
        {"status": "ok", "blueprint": "BP_Enemy", "new_parent": "Character", "compiled": true}

    Example:
        reparent_blueprint("BP_Enemy", "Character")
        reparent_blueprint("BP_Boss", "/Game/Arcwright/Generated/BP_BaseEnemy")

    Notes:
        - Reparenting from Actor to Character adds movement/capsule/mesh components automatically
        - Reparenting from Character to Actor may leave orphaned component references
        - Use get_blueprint_details to inspect the result after reparenting
        - Already-placed actors may need re-spawning to reflect the new parent class
    """
    def _run(client):
        return client.reparent_blueprint(name, new_parent)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Actor Material Tool (operates on placed actors, not BP templates)
# ---------------------------------------------------------------------------

@mcp.tool()
def set_actor_material(actor_label: str, material_path: str,
                       component_name: str = "", slot_index: int = 0) -> str:
    """Apply a material to a placed actor's mesh component directly.

    Unlike apply_material (which modifies the Blueprint SCS template and may not persist
    on spawned instances), this operates on the actual placed actor in the level.
    Materials applied this way are reliable and visible immediately.
    THIS IS THE PREFERRED METHOD for coloring placed actors.

    Parameters:
        actor_label (str): Actor label in the Outliner.
            Example: "Wall_1", "Enemy_3" (from get_actors or spawn_actor return values)
        material_path (str): Full UE material asset path.
            Example: "/Game/Arcwright/Materials/MAT_Gold"
            Use find_assets(asset_type="Material") or list_available_materials() to discover paths.
        component_name (str): Specific mesh component to target. Default: "" (first mesh found).
            Only needed if the actor has multiple mesh components.
        slot_index (int): Material slot index for multi-material meshes. Default: 0.

    Returns:
        {"status": "ok", "actor_label": "Wall_1", "material_path": "/Game/.../MAT_Gold"}

    Example:
        set_actor_material("Wall_1", "/Game/Arcwright/Materials/MAT_Concrete")
        set_actor_material("Crystal_1", "/Game/Arcwright/Materials/MAT_GoldGlow", slot_index=1)

    Notes:
        - Must be called AFTER spawn_actor_at -- the actor must exist in the level
        - Must be re-applied after any re-spawn operation (materials are on the instance, not the BP)
        - For applying materials to many actors at once, use batch_apply_material
        - For replacing ALL occurrences of one material across the level, use batch_replace_material
        - apply_material modifies the Blueprint template (unreliable for spawned instances);
          set_actor_material modifies the placed instance (reliable)
    """
    def _run(client):
        params = {"actor_label": actor_label, "material_path": material_path, "slot_index": slot_index}
        if component_name:
            params["component_name"] = component_name
        return client.send_command("set_actor_material", params)
    return _safe_call(_run)

@mcp.tool()
def compile_blueprint(name: str) -> str:
    """Force-recompile a Blueprint asset.

    Most commands (import_blueprint_ir, modify_blueprint, add_component) auto-compile
    after changes. Use this only if you need an explicit recompile, such as after
    multiple sequential set_node_param or add_connection calls.

    Parameters:
        name (str): Blueprint asset name to recompile. Example: "BP_Enemy"

    Returns:
        {"status": "ok", "blueprint": "BP_Enemy", "compiled": true}

    Example:
        compile_blueprint("BP_Enemy")

    Notes:
        - Returns compile status (true/false) -- check for compile errors
        - If compilation fails, use get_blueprint_info to inspect the node graph
        - Most editing commands already compile automatically; this is rarely needed
    """
    def _run(client):
        return client.compile_blueprint(name)
    return _safe_call(_run)

@mcp.tool()
def delete_blueprint(name: str) -> str:
    """Delete a Blueprint or other asset from the project permanently.

    WARNING: Placed actors referencing this Blueprint become invalid after deletion.
    Delete placed instances first with batch_delete_actors if needed.

    Parameters:
        name (str): Asset name to delete. Example: "BP_OldEnemy"

    Returns:
        {"status": "ok", "deleted": "BP_OldEnemy"}

    Example:
        delete_blueprint("BP_OldEnemy")

    Notes:
        - Removes the asset from the Content Browser permanently
        - Delete placed actor instances first with batch_delete_actors(class_filter="BP_OldEnemy")
        - Other Blueprints referencing the deleted BP will have broken references
        - To re-import a mesh/texture/sound, delete the existing asset first, then re-import
        - Use this before import_blueprint_ir if you need to recreate a Blueprint from scratch
    """
    def _run(client):
        return client.delete_blueprint(name)
    return _safe_call(_run)

@mcp.tool()
def set_class_defaults(blueprint: str, properties_json: str) -> str:
    """Set class default (CDO) properties on a Blueprint.

    Modifies the Blueprint's Class Default Object -- these are the initial values
    for all spawned instances. Supports any UPROPERTY discoverable via reflection:
    bool, int, float, string, name, enum, and special shortcut properties.

    Parameters:
        blueprint (str): Blueprint name to modify. Example: "BP_GameMode"
        properties_json (str): JSON object of property:value pairs. All specified
            properties are set on the CDO and the Blueprint is recompiled.

            Special shortcut properties:
                "default_pawn_class" -- sets DefaultPawnClass on GameModeBase (short BP name)
                "player_controller_class" -- sets PlayerControllerClass on GameModeBase
                "ai_controller_class" -- sets AIControllerClass on Pawn/Character

            Generic UPROPERTY examples:
                "bShowMouseCursor": false -- bool property
                "DefaultMouseCursor": "None" -- enum property
                "AutoPossessAI": "PlacedInWorldOrSpawned" -- enum property
                "MaxWalkSpeed": 600.0 -- float property

    Returns:
        {"status": "ok", "blueprint": "BP_GameMode", "properties_set": 2}

    Example:
        set_class_defaults("BP_GameMode", '{"default_pawn_class":"BP_FPSCharacter","player_controller_class":"BP_FPSController"}')
        set_class_defaults("BP_Enemy", '{"AutoPossessAI":"PlacedInWorldOrSpawned","ai_controller_class":"BP_EnemyAI"}')
        set_class_defaults("BP_Controller", '{"bShowMouseCursor":false,"DefaultMouseCursor":"None"}')

    Notes:
        - CDO changes apply to ALL new instances of this Blueprint
        - Already-placed actors may need re-spawning to pick up CDO changes
        - The modify_blueprint tool can also set CDO properties (along with adding/removing variables)
        - For batch changes across multiple BPs, use batch_set_variable for variable defaults
    """
    def _run(client):
        props = json.loads(properties_json)
        return client.send_command("set_class_defaults", {"blueprint": blueprint, **props})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Phase 2: New Commands (v8.1)
# ---------------------------------------------------------------------------

@mcp.tool()
def set_collision_preset(preset: str, blueprint: str = "", component_name: str = "",
                         actor_label: str = "") -> str:
    """Set a collision preset on an actor's component or a Blueprint's SCS component.

    Collision presets define how the object interacts with other objects (block, overlap,
    or ignore). Specify either actor_label (placed actor) OR blueprint+component_name
    (Blueprint template).

    Parameters:
        preset (str): UE collision preset name. Common values:
            "NoCollision" -- no collision response at all
            "BlockAll" -- blocks everything (walls, floors)
            "OverlapAll" -- generates overlap events with everything (triggers, pickups)
            "BlockAllDynamic" -- blocks all dynamic objects only
            "OverlapAllDynamic" -- overlaps dynamic objects (common for collectibles)
            "Pawn" -- standard pawn collision profile
            "Spectator" -- no collision except world static geometry
            "CharacterMesh" -- for character skeletal mesh components
            "PhysicsActor" -- for physics-simulated objects
            "Trigger" -- trigger volume preset
        blueprint (str): Blueprint name for SCS component targeting. Use with component_name.
        component_name (str): SCS component name in the Blueprint.
        actor_label (str): Actor label in the level for placed actor targeting.

    Returns:
        {"status": "ok", "preset": "OverlapAllDynamic"}

    Example:
        set_collision_preset("OverlapAllDynamic", actor_label="Pickup_1")
        set_collision_preset("BlockAll", blueprint="BP_Wall", component_name="WallMesh")

    Notes:
        - For pickups/triggers, use "OverlapAllDynamic" with overlap events in the Blueprint
        - For physics objects, use "PhysicsActor" combined with set_physics_enabled
        - Target either actor_label (placed actor) OR blueprint+component_name, not both
        - Use set_collision_shape to resize the collision geometry
    """
    def _run(client):
        params = {"preset": preset}
        if actor_label:
            params["actor_label"] = actor_label
        if blueprint:
            params["blueprint"] = blueprint
        if component_name:
            params["component_name"] = component_name
        return client.send_command("set_collision_preset", params)
    return _safe_call(_run)

@mcp.tool()
def get_blueprint_details(name: str) -> str:
    """Get detailed Blueprint information: parent class, variables, components, events, and node breakdown.

    More detailed than get_blueprint_info -- includes variable categories, editability flags,
    and a node_types histogram showing how many of each node type exist. Use this to
    inspect a Blueprint before making modifications.

    Parameters:
        name (str): Blueprint asset name. Example: "BP_Enemy"

    Returns:
        {"name": "BP_Enemy", "parent_class": "Pawn",
         "variables": [{"name": "Health", "type": "Float", "default": "100",
                        "category": "Combat", "is_instance_editable": true}],
         "components": [{"name": "CollisionSphere", "class": "USphereComponent"}],
         "events": ["ReceiveBeginPlay", "ReceiveActorBeginOverlap"],
         "node_count": 12, "connection_count": 15,
         "node_types": {"UK2Node_Event": 2, "UK2Node_CallFunction": 5}}

    Example:
        get_blueprint_details("BP_Enemy")

    Notes:
        - Use before modify_blueprint to see current state
        - The node_types histogram helps understand Blueprint complexity
        - For simpler queries (just node/connection counts), use get_blueprint_info
        - For comparing two Blueprints, use the compound tool compare_blueprints
    """
    def _run(client):
        return client.send_command("get_blueprint_details", {"name": name})
    return _safe_call(_run)

@mcp.tool()
def set_camera_properties(blueprint: str, fov: float = None,
                          arm_length: float = None,
                          use_pawn_control_rotation: bool = None,
                          do_collision_test: bool = None,
                          camera_lag_speed: float = None,
                          camera_rotation_lag_speed: float = None) -> str:
    """Set camera and spring arm properties on a Blueprint's SCS components.

    Finds UCameraComponent and USpringArmComponent in the Blueprint's
    SimpleConstructionScript and sets the specified properties. Only specified
    parameters are changed; omitted parameters keep their current values.

    Parameters:
        blueprint (str): Blueprint name with camera/spring arm components. Example: "BP_Player"
        fov (float): Camera field of view in degrees. Default: 90.
            60=narrow/zoomed, 90=standard, 110=wide, 120=fisheye
        arm_length (float): Spring arm length in cm.
            0=first person, 300=close third person, 600=standard TPS, 800=top-down
        use_pawn_control_rotation (bool): Camera follows controller (mouse) rotation.
            true for FPS/TPS, false for fixed cameras.
        do_collision_test (bool): Spring arm retracts to prevent camera clipping into walls.
            true for TPS (recommended), false for top-down/fixed.
        camera_lag_speed (float): Camera position smoothing speed.
            0=instant (FPS), 3=smooth follow, 10=very laggy. Requires EnableCameraLag=true.
        camera_rotation_lag_speed (float): Camera rotation smoothing speed.

    Returns:
        {"status": "ok", "blueprint": "BP_Player", "properties_set": 3}

    Example:
        set_camera_properties("BP_Player", fov=90, arm_length=400, use_pawn_control_rotation=True)
        set_camera_properties("BP_TopDownCamera", arm_length=800, do_collision_test=False)

    Notes:
        - The Blueprint must already have Camera and/or SpringArm components (add with add_component)
        - For FPS games, use setup_game_base.py which configures camera in C++ (recommended)
        - For standard third-person camera, use scaffold_pawn_blueprint which adds these components
    """
    def _run(client):
        params = {"blueprint": blueprint}
        if fov is not None: params["fov"] = fov
        if arm_length is not None: params["arm_length"] = arm_length
        if use_pawn_control_rotation is not None: params["use_pawn_control_rotation"] = use_pawn_control_rotation
        if do_collision_test is not None: params["do_collision_test"] = do_collision_test
        if camera_lag_speed is not None: params["camera_lag_speed"] = camera_lag_speed
        if camera_rotation_lag_speed is not None: params["camera_rotation_lag_speed"] = camera_rotation_lag_speed
        return client.send_command("set_camera_properties", params)
    return _safe_call(_run)

@mcp.tool()
def create_input_action(name: str, value_type: str = "bool") -> str:
    """Create a UInputAction asset for UE5 Enhanced Input.

    Input actions represent abstract game actions (jump, fire, interact) that are
    bound to physical keys via input mapping contexts. Create the action first,
    then bind it to keys with add_input_mapping.

    Parameters:
        name (str): Action name. Convention: "IA_" prefix.
            Example: "IA_Jump", "IA_Fire", "IA_Interact", "IA_Crouch"
        value_type (str): Input value type. Default: "bool".
            "bool" -- discrete button press (jump, fire, interact)
            "axis1d" -- single axis float (trigger, throttle)
            "axis2d" -- 2D axis ({x,y}) (movement stick, WASD)
            "axis3d" -- 3D axis ({x,y,z}) (rare, VR controllers)

    Returns:
        {"status": "ok", "name": "IA_Jump", "path": "/Game/Arcwright/Input/IA_Jump"}

    Example:
        create_input_action("IA_Jump", "bool")
        create_input_action("IA_Move", "axis2d")

    Notes:
        - For FPS/TPS games, use setup_game_base.py which creates all input actions in C++
        - After creating, bind to keys with add_input_mapping
        - Wire to Blueprint logic with bind_input_to_blueprint
        - See also: setup_input_context for creating a full input mapping context
    """
    def _run(client):
        return client.send_command("create_input_action", {"name": name, "value_type": value_type})
    return _safe_call(_run)

@mcp.tool()
def bind_input_to_blueprint(blueprint: str, action: str, trigger: str = "Pressed") -> str:
    """Add an Enhanced Input event node to a Blueprint's EventGraph.

    Creates a UK2Node_InputAction that fires when the specified input action is triggered.
    Wire the output exec pin to your game logic (PrintString, movement, etc.).

    Parameters:
        blueprint (str): Blueprint asset name to add the event to. Example: "BP_Player"
        action (str): Input action name or full asset path.
            Short name: "IA_Jump" (searches /Game/Arcwright/Input/, /Game/Input/, /Game/)
            Full path: "/Game/Input/IA_Jump"
        trigger (str): When the event fires. Default: "Pressed".
            "Pressed" -- fires once on key down
            "Released" -- fires once on key up
            "Held" -- fires every frame while held

    Returns:
        {"status": "ok", "blueprint": "BP_Player", "action": "IA_Jump", "trigger": "Pressed"}

    Example:
        bind_input_to_blueprint("BP_Player", "IA_Jump", "Pressed")
        bind_input_to_blueprint("BP_Player", "IA_Fire", "Held")

    Notes:
        - The UInputAction asset must already exist (create with create_input_action first)
        - Use add_connection to wire the event node's output to your logic
        - For FPS/TPS games, setup_game_base.py handles input binding in C++ (preferred)
    """
    def _run(client):
        params = {"blueprint": blueprint, "action": action, "trigger": trigger}
        return client.send_command("bind_input_to_blueprint", params)
    return _safe_call(_run)

@mcp.tool()
def set_collision_shape(blueprint: str, component_name: str,
                        shape_params_json: str) -> str:
    """Resize a collision component on a Blueprint (box, sphere, or capsule).

    Sets the collision shape dimensions on an existing SCS collision component.
    The component must already exist (add with add_component first).

    Parameters:
        blueprint (str): Blueprint asset name. Example: "BP_Pickup"
        component_name (str): Collision component name in the SCS. Example: "OverlapBox"
        shape_params_json (str): JSON object with shape-specific dimensions:
            Box (UBoxComponent): '{"x": 50, "y": 50, "z": 50}' -- half-extents in cm
            Sphere (USphereComponent): '{"radius": 100}' -- radius in cm
            Capsule (UCapsuleComponent): '{"radius": 34, "half_height": 96}' -- in cm

    Returns:
        {"status": "ok", "blueprint": "BP_Pickup", "component": "OverlapBox"}

    Example:
        set_collision_shape("BP_Pickup", "OverlapSphere", '{"radius": 200}')
        set_collision_shape("BP_Wall", "WallCollision", '{"x": 100, "y": 10, "z": 150}')

    Notes:
        - The component must already be a collision type (BoxCollision, SphereCollision, CapsuleCollision)
        - Values are in centimeters; box uses half-extents (50 = 100cm wide)
        - Use set_collision_preset to change the collision response (Block vs Overlap)
        - For adding a new collision component, use add_component first
    """
    def _run(client):
        params = json.loads(shape_params_json)
        params["blueprint"] = blueprint
        params["component_name"] = component_name
        return client.send_command("set_collision_shape", params)
    return _safe_call(_run)

@mcp.tool()
def create_nav_mesh_bounds(x: float = 0, y: float = 0, z: float = 0,
                           extent_x: float = 2000, extent_y: float = 2000, extent_z: float = 500,
                           label: str = "") -> str:
    """Spawn a NavMeshBoundsVolume for AI pathfinding.

    NavMesh is required for AI MoveTo with pathfinding enabled. The volume defines
    the area where UE generates navigation data. Place it to cover all walkable
    areas of your level.

    Parameters:
        x (float): Center X position in cm. Default: 0.
        y (float): Center Y position in cm. Default: 0.
        z (float): Center Z position in cm. Default: 0.
        extent_x (float): Half-extent X in cm. Default: 2000 (= 40m wide).
        extent_y (float): Half-extent Y in cm. Default: 2000.
        extent_z (float): Half-extent Z in cm. Default: 500 (= 10m tall).
        label (str): Actor label in the Outliner. Default: auto-generated.

    Returns:
        {"status": "ok", "label": "NavMesh_1", "location": {...}, "extents": {...}}

    Example:
        create_nav_mesh_bounds(0, 0, 0, 5000, 5000, 500, "MainNavMesh")

    Notes:
        - Make the volume large enough to cover all walkable ground
        - AI MoveToLocation with bUsePathfinding=true requires NavMesh
        - In World Partition, NavMesh may not auto-build; use bUsePathfinding=false as a workaround
        - For simple AI movement without pathfinding, skip the NavMesh entirely
        - The compound tool create_ai_enemy creates NavMesh bounds automatically
    """
    def _run(client):
        params = {
            "location": {"x": x, "y": y, "z": z},
            "extents": {"x": extent_x, "y": extent_y, "z": extent_z},
        }
        if label:
            params["label"] = label
        return client.send_command("create_nav_mesh_bounds", params)
    return _safe_call(_run)

@mcp.tool()
def set_audio_properties(blueprint: str, component_name: str,
                         volume_multiplier: float = None,
                         pitch_multiplier: float = None,
                         auto_activate: bool = None,
                         is_ui_sound: bool = None) -> str:
    """Set properties on a UAudioComponent in a Blueprint's SCS.

    The audio component must already exist (add with add_component or add_audio_component).
    Only specified parameters are changed; omitted parameters keep current values.

    Parameters:
        blueprint (str): Blueprint asset name. Example: "BP_Torch"
        component_name (str): Audio component name in the SCS. Example: "FireSound"
        volume_multiplier (float): Volume scale. 0.0=silent, 1.0=normal, 2.0=double. Default: None (unchanged).
        pitch_multiplier (float): Pitch scale. 0.5=half speed/low pitch, 1.0=normal, 2.0=high pitch. Default: None.
        auto_activate (bool): Play automatically when actor spawns. Default: None (unchanged).
        is_ui_sound (bool): Treat as UI sound (ignores distance attenuation). Default: None.

    Returns:
        {"status": "ok", "blueprint": "BP_Torch", "component": "FireSound"}

    Example:
        set_audio_properties("BP_Torch", "FireSound", volume_multiplier=0.5, auto_activate=True)

    Notes:
        - The component must already exist; use add_component("Audio") to create one first
        - For playing one-shot sounds in the level, use play_sound_at_location instead
        - 3D spatialization is enabled by default; set is_ui_sound=true for non-spatial sounds
    """
    def _run(client):
        params = {"blueprint": blueprint, "component_name": component_name}
        if volume_multiplier is not None: params["volume_multiplier"] = volume_multiplier
        if pitch_multiplier is not None: params["pitch_multiplier"] = pitch_multiplier
        if auto_activate is not None: params["auto_activate"] = auto_activate
        if is_ui_sound is not None: params["is_ui_sound"] = is_ui_sound
        return client.send_command("set_audio_properties", params)
    return _safe_call(_run)

@mcp.tool()
def set_actor_tags(actor_label: str, tags_json: str) -> str:
    """Set tags on a placed actor for categorization and batch operations.

    Tags are used for querying (find_actors with tag filter), batch operations
    (batch_delete_actors with tag), and game logic. Replaces ALL existing tags.

    Parameters:
        actor_label (str): Actor label in the Outliner. Example: "Enemy_1"
        tags_json (str): JSON array of tag strings to set.
            Example: '["Enemy", "Destructible", "Wave1"]'

    Returns:
        {"status": "ok", "actor_label": "Enemy_1", "tags": ["Enemy", "Destructible", "Wave1"]}

    Example:
        set_actor_tags("Enemy_1", '["Hostile", "Wave1"]')
        set_actor_tags("Crate_3", '["Destructible", "Wooden"]')

    Notes:
        - Replaces all existing tags (not additive). Pass the complete tag list.
        - Tags can be queried with find_actors(tag="Hostile")
        - Tags can be used to delete actors: batch_delete_actors(tag="Wave1")
        - Tags set here also work with batch_set_property (property="tag")
    """
    def _run(client):
        tags = json.loads(tags_json)
        return client.send_command("set_actor_tags", {"actor_label": actor_label, "tags": tags})
    return _safe_call(_run)

@mcp.tool()
def get_actor_properties(actor_label: str) -> str:
    """Get comprehensive property details for a placed actor.

    Returns everything about the actor: label, class, transform (location/rotation/scale),
    tags, visibility, mobility, and all components with their relative transforms,
    collision profiles, mesh paths, and material paths. Much more detailed than get_actors.

    Parameters:
        actor_label (str): Actor label in the Outliner. Example: "Enemy_1"

    Returns:
        {"label": "Enemy_1", "class": "BP_Enemy_C",
         "location": {"x":500,"y":200,"z":50},
         "rotation": {"pitch":0,"yaw":90,"roll":0},
         "scale": {"x":1,"y":1,"z":1},
         "tags": ["Hostile"], "visible": true, "mobility": "Movable",
         "components": [
             {"name": "EnemyMesh", "class": "UStaticMeshComponent",
              "mesh": "/Engine/BasicShapes/Sphere.Sphere",
              "material": "/Game/Arcwright/Materials/MAT_Red",
              "collision_preset": "OverlapAllDynamic"}
         ]}

    Example:
        get_actor_properties("Enemy_1")

    Notes:
        - For a simple list of all actors, use get_actors instead
        - For searching actors with filters, use find_actors
        - The returned component details include mesh paths, materials, and collision presets
        - Use get_actor_class for class hierarchy info (parent classes, is_blueprint)
    """
    def _run(client):
        return client.send_command("get_actor_properties", {"actor_label": actor_label})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Discovery Tools (Phase 4)
# ---------------------------------------------------------------------------

@mcp.tool()
def list_available_materials(name_filter: str = "", max_results: int = 50) -> str:
    """List all Material and MaterialInstance assets in the project.

    Specialized material search -- faster and more targeted than find_assets.
    Use the returned paths with set_actor_material, batch_apply_material, etc.

    Parameters:
        name_filter (str): Case-insensitive name substring filter.
            Example: "Gold", "Stone", "MAT_", "Concrete"
        max_results (int): Maximum results to return. Default: 50.

    Returns:
        {"count": 3, "materials": [
            {"name": "MAT_Gold", "path": "/Game/Arcwright/Materials/MAT_Gold", "type": "Material"},
            {"name": "MAT_Stone", "path": "/Game/Arcwright/Materials/MAT_Stone", "type": "Material"}
        ]}

    Example:
        list_available_materials()
        list_available_materials(name_filter="MAT_")

    Notes:
        - Returns both UMaterial and MaterialInstanceConstant assets
        - For broader asset search, use find_assets(asset_type="Material")
        - Material paths returned can be used directly in set_actor_material
        - Create materials with create_simple_material before they appear here
    """
    def _run(client):
        params = {"max_results": max_results}
        if name_filter:
            params["name_filter"] = name_filter
        return client.send_command("list_available_materials", params)
    return _safe_call(_run)

@mcp.tool()
def list_available_blueprints(name_filter: str = "") -> str:
    """List all Blueprint assets in the project with their parent classes.

    Specialized Blueprint discovery -- returns name, path, and parent class tag.
    Faster than find_blueprints for simple name-based listing without variable/component details.

    Parameters:
        name_filter (str): Case-insensitive name substring filter. Default: "" (all Blueprints).
            Example: "Enemy", "BP_", "Controller"

    Returns:
        {"count": 5, "blueprints": [
            {"name": "BP_Enemy", "path": "/Game/Arcwright/Generated/BP_Enemy", "parent": "Pawn"},
            {"name": "BP_Pickup", "path": "/Game/Arcwright/Generated/BP_Pickup", "parent": "Actor"}
        ]}

    Example:
        list_available_blueprints()
        list_available_blueprints(name_filter="Enemy")

    Notes:
        - For detailed Blueprint inspection (variables, components, nodes), use get_blueprint_details
        - For filtered search with variable/component criteria, use find_blueprints
        - Blueprint names returned can be used with modify_blueprint, reparent_blueprint, etc.
    """
    def _run(client):
        params = {}
        if name_filter:
            params["name_filter"] = name_filter
        return client.send_command("list_available_blueprints", params)
    return _safe_call(_run)

@mcp.tool()
def get_last_error() -> str:
    """Get the last error that occurred on the UE command server.

    Returns the error message and which command caused it. Useful for debugging
    when a command returns an unexpected result or you suspect a silent failure.

    Returns:
        {"last_error": "Blueprint 'BP_Missing' not found",
         "last_error_command": "get_blueprint_info"}
        Or if no error has occurred:
        {"last_error": "", "last_error_command": ""}

    Example:
        get_last_error()

    Notes:
        - Only stores the most recent error (not a history)
        - Most commands return errors inline in their response; this is for edge cases
        - Cleared when a new error occurs (no explicit reset)
    """
    def _run(client):
        return client.send_command("get_last_error", {})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Phase 5: Actor Config & Utility Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def set_physics_enabled(
    enabled: bool,
    actor_label: str = "",
    blueprint: str = "",
    component_name: str = "",
) -> str:
    """Enable or disable physics simulation on a PrimitiveComponent.

    Works on placed actors (by actor_label) or Blueprint SCS templates
    (by blueprint + component_name). When enabling, also sets collision
    response to QueryAndPhysics so the object interacts with the world.

    Parameters:
        enabled (bool): True to enable physics simulation, False to disable.
        actor_label (str): Label of a placed actor in the level. Default: "".
        blueprint (str): Blueprint name (use with component_name). Default: "".
        component_name (str): Specific component name on the Blueprint. Default: "".

    Returns:
        {"status": "ok", "physics_enabled": true, "component": "StaticMeshComponent0"}

    Example:
        set_physics_enabled(True, actor_label="Crate_1")
        set_physics_enabled(True, blueprint="BP_Ball", component_name="BallMesh")
        set_physics_enabled(False, actor_label="Wall_1")

    Notes:
        - Target either actor_label (placed actor) OR blueprint+component_name, not both
        - For physics constraints between objects, use add_physics_constraint
        - Physics requires a mesh component with valid collision; use set_collision_preset first
        - Set mobility to "Movable" with set_actor_mobility before enabling physics
        - The compound tool create_physics_playground sets up multiple physics objects
    """
    def _run(client):
        params = {"enabled": enabled}
        if actor_label: params["actor_label"] = actor_label
        if blueprint: params["blueprint"] = blueprint
        if component_name: params["component_name"] = component_name
        return client.send_command("set_physics_enabled", params)
    return _safe_call(_run)

@mcp.tool()
def set_actor_visibility(
    actor_label: str,
    visible: bool,
    propagate: bool = True,
) -> str:
    """Show or hide a placed actor in the game world.

    Parameters:
        actor_label (str): Label of the actor in the level. Example: "Door_1"
        visible (bool): True to show the actor, False to hide it.
        propagate (bool): Apply visibility to all child components. Default: True.

    Returns:
        {"status": "ok", "actor": "Door_1", "visible": true, "propagate": true}

    Example:
        set_actor_visibility("Door_1", False)
        set_actor_visibility("SecretRoom", True, propagate=True)

    Notes:
        - Hidden actors are still present in the level (can still have collision, tick, etc.)
        - To fully disable an actor (hidden + no collision + no tick), use set_actor_enabled
        - For batch visibility changes, use batch_set_property with property="visibility"
        - Visibility can also be animated over time with add_sequence_track("Visibility")
    """
    def _run(client):
        params = {"actor_label": actor_label, "visible": visible, "propagate": propagate}
        return client.send_command("set_actor_visibility", params)
    return _safe_call(_run)

@mcp.tool()
def set_actor_mobility(
    actor_label: str,
    mobility: str,
) -> str:
    """Set a placed actor's mobility type (Static, Stationary, or Movable).

    Parameters:
        actor_label (str): Label of the actor in the level. Example: "Wall_1"
        mobility (str): Mobility type:
            "Static" -- cannot move at runtime, best performance, baked lighting
            "Stationary" -- does not move but has dynamic lighting/shadows
            "Movable" -- can move at runtime, required for physics and animation

    Returns:
        {"status": "ok", "actor": "Wall_1", "mobility": "Static"}

    Example:
        set_actor_mobility("Wall_1", "Static")
        set_actor_mobility("Platform_1", "Movable")

    Notes:
        - Physics-enabled actors MUST be "Movable"
        - Static actors get baked lighting (best quality + performance)
        - Lights set to "Stationary" cast baked shadows but can change intensity/color
        - Set mobility before enabling physics with set_physics_enabled
    """
    def _run(client):
        return client.send_command("set_actor_mobility", {
            "actor_label": actor_label, "mobility": mobility
        })
    return _safe_call(_run)

@mcp.tool()
def attach_actor_to(
    actor_label: str,
    parent_label: str,
    socket_name: str = "",
    rule: str = "KeepWorld",
) -> str:
    """Attach an actor to another actor as a child (parent-child hierarchy).

    The child actor moves with the parent. Useful for mounting weapons to characters,
    attaching items to actors, or creating composite objects.

    Parameters:
        actor_label (str): Label of the child actor to attach. Example: "Sword_1"
        parent_label (str): Label of the parent actor. Example: "Player_1"
        socket_name (str): Optional bone/socket name on the parent to attach to.
            Example: "hand_r" for a skeletal mesh socket. Default: "" (root).
        rule (str): How to handle the transform on attachment. Default: "KeepWorld".
            "KeepWorld" -- child stays at its current world position
            "KeepRelative" -- child keeps its relative offset from parent
            "SnapToTarget" -- child snaps to the parent's (or socket's) position

    Returns:
        {"status": "ok", "actor": "Sword_1", "parent": "Player_1", "rule": "KeepWorld"}

    Example:
        attach_actor_to("Sword_1", "Player_1", socket_name="hand_r", rule="SnapToTarget")
        attach_actor_to("Hat_1", "NPC_1", rule="KeepRelative")

    Notes:
        - To detach later, use detach_actor
        - "SnapToTarget" is most common for socket attachments (weapon in hand)
        - "KeepWorld" is best when you want the child to stay in place but follow the parent
        - Both actors must exist in the level
    """
    def _run(client):
        params = {"actor_label": actor_label, "parent_label": parent_label, "rule": rule}
        if socket_name: params["socket_name"] = socket_name
        return client.send_command("attach_actor_to", params)
    return _safe_call(_run)

@mcp.tool()
def detach_actor(
    actor_label: str,
    rule: str = "KeepWorld",
) -> str:
    """Detach an actor from its parent, making it independent again.

    Parameters:
        actor_label (str): Label of the actor to detach. Example: "Sword_1"
        rule (str): How to handle the transform on detachment. Default: "KeepWorld".
            "KeepWorld" -- actor stays at its current world position
            "KeepRelative" -- actor keeps the relative offset it had from the parent

    Returns:
        {"status": "ok", "actor": "Sword_1", "rule": "KeepWorld"}

    Example:
        detach_actor("Sword_1")
        detach_actor("DroppedItem", rule="KeepWorld")

    Notes:
        - "KeepWorld" is almost always what you want (actor stays in place)
        - Use attach_actor_to to re-attach to a different parent
        - No error if the actor has no parent (idempotent)
    """
    def _run(client):
        return client.send_command("detach_actor", {"actor_label": actor_label, "rule": rule})
    return _safe_call(_run)

@mcp.tool()
def list_project_assets(
    asset_type: str = "",
    path: str = "",
    name_filter: str = "",
    max_results: int = 100,
) -> str:
    """Search the UE Asset Registry for project assets by type, path, and name.

    Supports 8 asset types: Blueprint, Material, MaterialInstance, StaticMesh,
    Texture, Sound, BehaviorTree, DataTable.

    Parameters:
        asset_type (str): Filter by asset type. Default: "" (all types).
            Valid: "Blueprint", "Material", "MaterialInstance", "StaticMesh",
            "Texture", "Sound", "BehaviorTree", "DataTable"
        path (str): UE content path to search. Default: "" (all under /Game/).
            Example: "/Game/Arcwright/Meshes/"
        name_filter (str): Case-insensitive substring match. Default: "" (all names).
        max_results (int): Maximum results to return. Default: 100.

    Returns:
        {"count": 3, "assets": [
            {"name": "SM_Cube", "path": "/Game/Arcwright/Meshes/SM_Cube", "type": "StaticMesh"}
        ]}

    Example:
        list_project_assets(asset_type="StaticMesh")
        list_project_assets(asset_type="Material", path="/Game/Arcwright/Materials/")
        list_project_assets(name_filter="Enemy")

    Notes:
        - Similar to find_assets but accessed via a different TCP command path
        - For Blueprint-specific search with variable/component details, use find_blueprints
        - For material-specific search, list_available_materials is more convenient
        - Asset paths returned can be used in set_actor_material, add_component, etc.
    """
    def _run(client):
        params = {"max_results": max_results}
        if asset_type: params["asset_type"] = asset_type
        if path: params["path"] = path
        if name_filter: params["name_filter"] = name_filter
        return client.send_command("list_project_assets", params)
    return _safe_call(_run)

@mcp.tool()
def copy_actor(
    actor_label: str,
    new_label: str = "",
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    offset_z: float = 0.0,
) -> str:
    """Duplicate a placed actor in the level with an optional position offset.

    Creates an exact copy of the actor (same class, properties, materials) at the
    same or offset position. All properties are preserved on the copy.

    Parameters:
        actor_label (str): Label of the source actor to copy. Example: "Pillar_1"
        new_label (str): Label for the new copy. Default: "{source}_Copy".
        offset_x (float): X offset from the original position. Default: 0.
        offset_y (float): Y offset from the original position. Default: 0.
        offset_z (float): Z offset from the original position. Default: 0.

    Returns:
        {"status": "ok", "source": "Pillar_1", "copy": "Pillar_1_Copy",
         "location": {"x":100,"y":0,"z":0}}

    Example:
        copy_actor("Pillar_1", "Pillar_2", offset_x=200)
        copy_actor("Torch_1", "Torch_2", offset_x=0, offset_y=500, offset_z=0)

    Notes:
        - For creating many copies in a pattern, use spawn_actor_grid, spawn_actor_circle,
          or spawn_actor_line instead (more efficient)
        - Materials on the copy may need re-application with set_actor_material
        - The copy is a new independent actor (not linked to the original)
    """
    def _run(client):
        params = {"actor_label": actor_label}
        if new_label: params["new_label"] = new_label
        if offset_x != 0.0 or offset_y != 0.0 or offset_z != 0.0:
            params["offset"] = {"x": offset_x, "y": offset_y, "z": offset_z}
        return client.send_command("copy_actor", params)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Procedural spawn pattern commands
# ---------------------------------------------------------------------------

@mcp.tool()
def spawn_actor_grid(
    actor_class: str,
    rows: int = 3,
    cols: int = 3,
    spacing_x: float = 200.0,
    spacing_y: float = 200.0,
    origin_x: float = 0.0, origin_y: float = 0.0, origin_z: float = 0.0,
    center: bool = True,
    label_prefix: str = "",
    yaw: float = 0.0,
    scale: float = 1.0,
) -> str:
    """Spawn actors in a rows-by-cols grid pattern for walls, floors, arenas, and formations.

    Parameters:
        actor_class (str): Actor class or Blueprint path to spawn.
            Example: "StaticMeshActor", "/Game/Arcwright/Generated/BP_Wall"
        rows (int): Number of rows (Y axis). Default: 3. Max: 50.
        cols (int): Number of columns (X axis). Default: 3. Max: 50.
        spacing_x (float): Distance between columns in cm. Default: 200.
        spacing_y (float): Distance between rows in cm. Default: 200.
        origin_x (float): Grid origin X position. Default: 0.
        origin_y (float): Grid origin Y position. Default: 0.
        origin_z (float): Grid origin Z position. Default: 0.
        center (bool): Center the grid on the origin point. Default: True.
        label_prefix (str): Prefix for actor labels. Default: class-based.
            Example: "Wall" produces Wall_0_0, Wall_0_1, Wall_1_0, etc.
        yaw (float): Rotation yaw for all actors in degrees. Default: 0.
        scale (float): Uniform scale for all actors. Default: 1.0.

    Returns:
        {"spawned": 12, "rows": 3, "cols": 4, "actors": ["Wall_0_0", "Wall_0_1", ...]}

    Example:
        spawn_actor_grid("StaticMeshActor", rows=4, cols=10, spacing_x=300, label_prefix="Wall")
        spawn_actor_grid("/Game/Arcwright/Generated/BP_Pillar", rows=2, cols=2, spacing_x=1000, spacing_y=1000)

    Notes:
        - Total actors = rows x cols. Max 2500 (50x50).
        - For level layout, use the compound tool create_arena_layout or populate_level_grid
        - For circle layouts, use spawn_actor_circle
        - For line layouts, use spawn_actor_line
    """
    def _run(client):
        params = {"class": actor_class, "rows": rows, "cols": cols,
                  "spacing_x": spacing_x, "spacing_y": spacing_y,
                  "origin": {"x": origin_x, "y": origin_y, "z": origin_z},
                  "center": center}
        if label_prefix: params["label_prefix"] = label_prefix
        if yaw != 0.0: params["rotation"] = {"pitch": 0, "yaw": yaw, "roll": 0}
        if scale != 1.0: params["scale"] = {"x": scale, "y": scale, "z": scale}
        return client.send_command("spawn_actor_grid", params)
    return _safe_call(_run)

@mcp.tool()
def spawn_actor_circle(
    actor_class: str,
    count: int = 8,
    radius: float = 500.0,
    center_x: float = 0.0, center_y: float = 0.0, center_z: float = 0.0,
    face_center: bool = False,
    start_angle: float = 0.0,
    label_prefix: str = "",
    scale: float = 1.0,
) -> str:
    """Spawn actors evenly distributed around a circle for arenas, pillars, and formations.

    Parameters:
        actor_class (str): Actor class or Blueprint path to spawn.
            Example: "StaticMeshActor", "/Game/Arcwright/Generated/BP_Pillar"
        count (int): Number of actors to place. Default: 8. Max: 100.
        radius (float): Circle radius in cm. Default: 500.
        center_x (float): Circle center X position. Default: 0.
        center_y (float): Circle center Y position. Default: 0.
        center_z (float): Circle center Z position. Default: 0.
        face_center (bool): Rotate each actor to face the center point. Default: False.
        start_angle (float): Starting angle in degrees (0 = +X axis, 90 = +Y). Default: 0.
        label_prefix (str): Prefix for actor labels. Example: "Pillar" -> Pillar_0, Pillar_1...
        scale (float): Uniform scale for all actors. Default: 1.0.

    Returns:
        {"spawned": 8, "actors": ["Pillar_0", "Pillar_1", ...]}

    Example:
        spawn_actor_circle("StaticMeshActor", count=12, radius=1000, label_prefix="Pillar")
        spawn_actor_circle("/Game/Arcwright/Generated/BP_Enemy", count=6, radius=500, face_center=True)

    Notes:
        - Actors are evenly spaced (360/count degrees apart)
        - face_center=True is useful for enemies surrounding a point, pillars facing inward
        - For grid layouts, use spawn_actor_grid
        - For line layouts, use spawn_actor_line
    """
    def _run(client):
        params = {"class": actor_class, "count": count, "radius": radius,
                  "center": {"x": center_x, "y": center_y, "z": center_z}}
        if face_center: params["face_center"] = True
        if start_angle != 0.0: params["start_angle"] = start_angle
        if label_prefix: params["label_prefix"] = label_prefix
        if scale != 1.0: params["scale"] = {"x": scale, "y": scale, "z": scale}
        return client.send_command("spawn_actor_circle", params)
    return _safe_call(_run)

@mcp.tool()
def spawn_actor_line(
    actor_class: str,
    count: int,
    start_x: float = 0.0, start_y: float = 0.0, start_z: float = 0.0,
    end_x: float = 1000.0, end_y: float = 0.0, end_z: float = 0.0,
    face_direction: bool = False,
    label_prefix: str = "",
    scale: float = 1.0,
) -> str:
    """Spawn actors evenly spaced along a line from start to end.

    Useful for fences, corridors, paths, bridges, and linear formations.

    Parameters:
        actor_class (str): Actor class or Blueprint path. Example: "/Game/Arcwright/Generated/BP_Fence"
        count (int): Number of actors to place along the line.
        start_x (float): Line start X. Default: 0.
        start_y (float): Line start Y. Default: 0.
        start_z (float): Line start Z. Default: 0.
        end_x (float): Line end X. Default: 1000.
        end_y (float): Line end Y. Default: 0.
        end_z (float): Line end Z. Default: 0.
        face_direction (bool): Rotate actors to face along the line. Default: False.
        label_prefix (str): Prefix for labels. Example: "Fence" -> Fence_0, Fence_1...
        scale (float): Uniform scale. Default: 1.0.

    Returns:
        {"spawned": 5, "actors": ["Fence_0", "Fence_1", ...]}

    Example:
        spawn_actor_line("StaticMeshActor", 10, start_x=-500, end_x=500, label_prefix="Post")
        spawn_actor_line("/Game/Arcwright/Generated/BP_Torch", 8, start_x=0, start_y=0, end_x=0, end_y=2000, face_direction=True)

    Notes:
        - Actors are evenly distributed from start to end (inclusive)
        - face_direction=True rotates each actor to point from start toward end
        - For grid patterns, use spawn_actor_grid
        - For circular patterns, use spawn_actor_circle
    """
    def _run(client):
        params = {"class": actor_class, "count": count,
                  "start": {"x": start_x, "y": start_y, "z": start_z},
                  "end": {"x": end_x, "y": end_y, "z": end_z}}
        if face_direction: params["face_direction"] = True
        if label_prefix: params["label_prefix"] = label_prefix
        if scale != 1.0: params["scale"] = {"x": scale, "y": scale, "z": scale}
        return client.send_command("spawn_actor_line", params)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Relative transform batch commands
# ---------------------------------------------------------------------------

@mcp.tool()
def batch_scale_actors(
    scale_x: float = 1.0, scale_y: float = 1.0, scale_z: float = 1.0,
    labels_json: str = "",
    name_filter: str = "", class_filter: str = "", tag: str = "",
    mode: str = "multiply",
) -> str:
    """Scale multiple actors matched by label list, name, class, or tag filters.

    Parameters:
        scale_x (float): X scale factor. Default: 1.0.
        scale_y (float): Y scale factor. Default: 1.0.
        scale_z (float): Z scale factor. Default: 1.0.
        labels_json (str): JSON array of exact actor labels. Example: '["Wall_0","Wall_1"]'
        name_filter (str): Substring match on actor labels. Example: "Wall"
        class_filter (str): Substring match on actor class names. Example: "BP_Wall"
        tag (str): Exact tag match. Example: "Destructible"
        mode (str): Scale mode. Default: "multiply".
            "multiply" -- multiply current scale by the factors (2.0 = double current size)
            "set" -- set absolute scale values (2.0 = always 2x regardless of current)

    Returns:
        {"status": "ok", "scaled": 5, "mode": "multiply"}

    Example:
        batch_scale_actors(2.0, 2.0, 2.0, class_filter="BP_Pillar")
        batch_scale_actors(1.0, 1.0, 2.0, tag="Tall", mode="multiply")
        batch_scale_actors(0.5, 0.5, 0.5, labels_json='["Crate_1","Crate_2"]', mode="set")

    Notes:
        - At least one filter required (labels_json, name_filter, class_filter, or tag)
        - "multiply" mode is useful for relative resizing ("make all pillars 50% taller")
        - "set" mode is useful for uniform sizing ("make all crates exactly half scale")
        - For single actor scaling, use set_actor_scale or move_actor
    """
    def _run(client):
        params = {"scale": {"x": scale_x, "y": scale_y, "z": scale_z}, "mode": mode}
        if labels_json:
            params["labels"] = json.loads(labels_json)
        if name_filter: params["name_filter"] = name_filter
        if class_filter: params["class_filter"] = class_filter
        if tag: params["tag"] = tag
        return client.send_command("batch_scale_actors", params)
    return _safe_call(_run)

@mcp.tool()
def batch_move_actors(
    x: float = 0.0, y: float = 0.0, z: float = 0.0,
    labels_json: str = "",
    name_filter: str = "", class_filter: str = "", tag: str = "",
    mode: str = "relative",
) -> str:
    """Move multiple actors matched by label list, name, class, or tag filters.

    Parameters:
        x (float): X offset (relative) or X position (set). Default: 0.
        y (float): Y offset (relative) or Y position (set). Default: 0.
        z (float): Z offset (relative) or Z position (set). Default: 0.
        labels_json (str): JSON array of exact actor labels. Example: '["Enemy_0","Enemy_1"]'
        name_filter (str): Substring match on actor labels. Example: "Enemy"
        class_filter (str): Substring match on actor class names. Example: "BP_Enemy"
        tag (str): Exact tag match. Example: "Wave1"
        mode (str): Movement mode. Default: "relative".
            "relative" -- add offset to each actor's current position
            "set" -- move all matched actors to the same absolute position

    Returns:
        {"status": "ok", "moved": 5, "mode": "relative"}

    Example:
        batch_move_actors(0, 0, 100, class_filter="BP_Enemy", mode="relative")
        batch_move_actors(0, 0, 50, tag="Floating", mode="relative")
        batch_move_actors(0, 0, 0, labels_json='["Boss_1"]', mode="set")

    Notes:
        - At least one filter required (labels_json, name_filter, class_filter, or tag)
        - "relative" mode is most common: "move all enemies up 100 units"
        - "set" mode moves all matching actors to the SAME position (rarely desired for multiple actors)
        - For single actor movement, use move_actor instead
        - For per-actor different positions, use batch_set_property with property="location"
    """
    def _run(client):
        if mode == "relative":
            params = {"offset": {"x": x, "y": y, "z": z}, "mode": "relative"}
        else:
            params = {"location": {"x": x, "y": y, "z": z}, "mode": "set"}
        if labels_json:
            params["labels"] = json.loads(labels_json)
        if name_filter: params["name_filter"] = name_filter
        if class_filter: params["class_filter"] = class_filter
        if tag: params["tag"] = tag
        return client.send_command("batch_move_actors", params)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Actor config & lifecycle
# ---------------------------------------------------------------------------

@mcp.tool()
def set_player_input_mapping(blueprint: str, context: str) -> str:
    """Set the default InputMappingContext on a PlayerController Blueprint.

    Configures which input mapping context (key bindings) the controller uses.

    Parameters:
        blueprint (str): PlayerController Blueprint name. Example: "BP_FPSController"
        context (str): InputMappingContext asset name or path.
            Example: "IMC_Default", "/Game/Input/IMC_Default"

    Returns:
        {"status": "ok", "blueprint": "BP_FPSController", "context": "IMC_Default"}

    Example:
        set_player_input_mapping("BP_FPSController", "IMC_Default")

    Notes:
        - For FPS/TPS games, setup_game_base.py configures this in C++ (preferred)
        - The IMC asset must already exist in the project
        - Use create_input_action + add_input_mapping to create custom input bindings
    """
    def _run(client):
        return client.send_command("set_player_input_mapping", {"blueprint": blueprint, "context": context})
    return _safe_call(_run)

@mcp.tool()
def set_actor_tick(actor_label: str, enabled: bool = True, interval: float = None) -> str:
    """Enable or disable tick on a placed actor, with optional tick interval.

    Tick fires every frame (or at the specified interval) and drives continuous logic
    like movement, timers, and polling.

    Parameters:
        actor_label (str): Label of the actor. Example: "Enemy_1"
        enabled (bool): Whether tick should fire. Default: True.
        interval (float): Tick interval in seconds. None = every frame (~0.016s at 60fps).
            Example: 0.5 = tick twice per second

    Returns:
        {"status": "ok", "actor": "Enemy_1", "tick_enabled": true, "interval": 0.5}

    Example:
        set_actor_tick("Enemy_1", True, interval=0.1)
        set_actor_tick("Background_1", False)

    Notes:
        - Disabling tick on static actors improves performance
        - Use set_actor_enabled to disable tick, collision, AND visibility together
        - Most actors have tick enabled by default; disable it for purely decorative actors
    """
    def _run(client):
        params = {"actor_label": actor_label, "enabled": enabled}
        if interval is not None:
            params["interval"] = interval
        return client.send_command("set_actor_tick", params)
    return _safe_call(_run)

@mcp.tool()
def set_actor_lifespan(actor_label: str, lifespan: float = 0.0) -> str:
    """Set an auto-destroy timer on a placed actor.

    After the specified time elapses, the actor is automatically destroyed.
    Set to 0 for infinite lifespan (no auto-destroy).

    Parameters:
        actor_label (str): Label of the actor. Example: "Projectile_1"
        lifespan (float): Time in seconds before auto-destroy. Default: 0.0 (infinite).
            Example: 5.0 = destroy after 5 seconds

    Returns:
        {"status": "ok", "actor": "Projectile_1", "lifespan": 5.0}

    Example:
        set_actor_lifespan("Projectile_1", 3.0)
        set_actor_lifespan("TemporaryEffect", 10.0)
        set_actor_lifespan("PermanentActor", 0.0)

    Notes:
        - Useful for projectiles, particle effects, temporary pickups
        - 0 = infinite (actor persists until manually destroyed)
        - The timer starts from when this command is called, not from spawn time
    """
    def _run(client):
        return client.send_command("set_actor_lifespan", {"actor_label": actor_label, "lifespan": lifespan})
    return _safe_call(_run)

@mcp.tool()
def get_actor_bounds(actor_label: str) -> str:
    """Get the axis-aligned bounding box of a placed actor.

    Returns the bounding box center (origin), half-extents, and min/max corners.
    Useful for calculating spacing, overlap detection, and layout planning.

    Parameters:
        actor_label (str): Label of the actor. Example: "Wall_1"

    Returns:
        {"actor": "Wall_1",
         "origin": {"x":500, "y":0, "z":100},
         "extent": {"x":50, "y":200, "z":100},
         "min": {"x":450, "y":-200, "z":0},
         "max": {"x":550, "y":200, "z":200}}

    Example:
        get_actor_bounds("Wall_1")

    Notes:
        - extent is the HALF-extent (full size = extent * 2)
        - Bounds include all visible components (meshes, collision)
        - Useful before spawn_actor_grid to calculate spacing from actor size
    """
    def _run(client):
        return client.send_command("get_actor_bounds", {"actor_label": actor_label})
    return _safe_call(_run)

@mcp.tool()
def set_actor_enabled(actor_label: str, enabled: bool = True) -> str:
    """Enable or disable an actor entirely: toggles visibility, collision, and tick together.

    When disabled, the actor becomes invisible, ignores all collision, and stops ticking.
    Useful for object pooling or conditional gameplay elements (e.g., hidden doors, inactive traps).

    Parameters:
        actor_label (str): Label of the placed actor. Example: "SecretDoor_1"
        enabled (bool): True = visible + collidable + ticking. False = hidden + no collision + no tick.
            Default: True.

    Returns:
        {"status": "ok", "actor": "SecretDoor_1", "enabled": true}

    Example:
        set_actor_enabled("SecretDoor_1", False)
        set_actor_enabled("SecretDoor_1", True)

    Notes:
        - This is a convenience wrapper that sets 3 properties at once
        - For individual control, use set_actor_visibility (show/hide only),
          set_actor_tick (tick only), or set_collision_preset (collision only)
        - Disabled actors still exist in the level; use delete_actor to remove permanently
    """
    def _run(client):
        return client.send_command("set_actor_enabled", {"actor_label": actor_label, "enabled": enabled})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# SaveGame
# ---------------------------------------------------------------------------

@mcp.tool()
def create_save_game(name: str, variables: str = "") -> str:
    """Create a SaveGame Blueprint for persisting game state across play sessions.

    Creates a Blueprint with USaveGame as the parent class and adds typed variables
    for storing player progress, scores, settings, etc.

    Parameters:
        name (str): Name for the SaveGame Blueprint. Example: "SG_PlayerProgress"
        variables (str): JSON array of variable definitions. Each has "name" and "type".
            Supported types: "int", "float", "bool", "string", "vector".
            Example: '[{"name": "Score", "type": "int"}, {"name": "PlayerPos", "type": "vector"}]'
            Default: "" (no variables, add later with modify_blueprint).

    Returns:
        {"status": "ok", "name": "SG_PlayerProgress",
         "path": "/Game/Arcwright/Generated/SG_PlayerProgress"}

    Example:
        create_save_game("SG_PlayerProgress",
            '[{"name":"HighScore","type":"int"},{"name":"CheckpointPos","type":"vector"},{"name":"HasKey","type":"bool"}]')
        create_save_game("SG_Settings",
            '[{"name":"MusicVolume","type":"float"},{"name":"PlayerName","type":"string"}]')

    Notes:
        - The Blueprint uses USaveGame as its parent class (required for UE save/load system)
        - At runtime, use CreateSaveGameObject + SaveGameToSlot / LoadGameFromSlot in Blueprint nodes
        - Variables can be added later with modify_blueprint if needed
        - For DataTable-based persistence (structured rows), use create_data_table_from_dsl instead
    """
    def _run(client):
        params = {"name": name}
        if variables:
            params["variables"] = json.loads(variables)
        return client.send_command("create_save_game", params)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# DataTable row operations
# ---------------------------------------------------------------------------

@mcp.tool()
def add_data_table_row(table_name: str, row_name: str, values_json: str = "{}") -> str:
    """Add a new row to an existing DataTable created with create_data_table_from_dsl.

    Each row has a unique name (key) and column values matching the table's struct definition.
    Columns not specified use their default values.

    Parameters:
        table_name (str): Name of the DataTable asset. Example: "DT_Weapons"
        row_name (str): Unique key for the new row. Example: "Shotgun"
        values_json (str): JSON object mapping column names to values.
            Use the friendly column names defined when the table was created.
            Example: '{"Name": "Shotgun", "Damage": 80.0, "FireRate": 0.5, "IsAutomatic": false}'
            Default: "{}" (all defaults).

    Returns:
        {"status": "ok", "table": "DT_Weapons", "row": "Shotgun", "added": true}

    Example:
        add_data_table_row("DT_Weapons", "Shotgun",
            '{"Name":"Shotgun","Damage":80.0,"FireRate":0.5,"IsAutomatic":false}')
        add_data_table_row("DT_EnemyStats", "Boss",
            '{"Health":500,"Speed":150.0,"AttackDamage":40}')

    Notes:
        - The DataTable must already exist (create with create_data_table_from_dsl)
        - Column names must match the struct definition exactly (case-sensitive)
        - Duplicate row names are rejected
        - To update an existing row, use edit_data_table_row instead
        - To read all rows, use get_data_table_rows
    """
    def _run(client):
        params = {"table_name": table_name, "row_name": row_name, "values": json.loads(values_json)}
        return client.send_command("add_data_table_row", params)
    return _safe_call(_run)

@mcp.tool()
def edit_data_table_row(table_name: str, row_name: str, values_json: str = "{}") -> str:
    """Edit specific column values in an existing DataTable row (partial update).

    Only the columns you specify are changed; all other columns keep their current values.
    The row must already exist (use add_data_table_row to create new rows).

    Parameters:
        table_name (str): Name of the DataTable asset. Example: "DT_Weapons"
        row_name (str): Key of the row to update. Example: "Shotgun"
        values_json (str): JSON object of columns to update. Only specified columns change.
            Example: '{"Damage": 100.0}' (updates Damage, leaves all other columns untouched)

    Returns:
        {"status": "ok", "table": "DT_Weapons", "row": "Shotgun", "updated": true}

    Example:
        edit_data_table_row("DT_Weapons", "Shotgun", '{"Damage": 100.0}')
        edit_data_table_row("DT_EnemyStats", "Boss", '{"Health": 1000, "Speed": 50.0}')

    Notes:
        - Row must exist; use add_data_table_row to create new rows
        - Unspecified columns retain their previous values (partial update)
        - Column names are case-sensitive and must match the struct definition
        - To read current values before editing, use get_data_table_rows
    """
    def _run(client):
        params = {"table_name": table_name, "row_name": row_name, "values": json.loads(values_json)}
        return client.send_command("edit_data_table_row", params)
    return _safe_call(_run)

@mcp.tool()
def get_data_table_rows(table_name: str) -> str:
    """Read all rows and column values from a DataTable asset.

    Returns the full table contents including the struct column definitions and all row data.
    Use this to inspect table contents before editing or to verify data after modifications.

    Parameters:
        table_name (str): Name of the DataTable asset. Example: "DT_Weapons"

    Returns:
        {"status": "ok", "table": "DT_Weapons", "row_count": 3,
         "columns": [{"name": "Name", "type": "String"}, {"name": "Damage", "type": "Float"}],
         "rows": [
            {"_row_name": "Pistol", "Name": "Pistol", "Damage": 25.0, "FireRate": 2.0},
            {"_row_name": "Rifle", "Name": "Rifle", "Damage": 15.0, "FireRate": 8.0}
         ]}

    Example:
        get_data_table_rows("DT_Weapons")
        get_data_table_rows("DT_EnemyStats")

    Notes:
        - Each row includes a "_row_name" field with the row key
        - Column types match the struct definition: String, Float, Int, Boolean, etc.
        - For large tables, all rows are returned (no pagination)
        - To modify rows, use edit_data_table_row; to add, use add_data_table_row
        - To see just the structure without data, use get_data_table_info
    """
    def _run(client):
        return client.send_command("get_data_table_rows", {"table_name": table_name})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Animation Blueprint & Montage
# ---------------------------------------------------------------------------

@mcp.tool()
def create_anim_blueprint(name: str, skeleton: str) -> str:
    """Create an Animation Blueprint (AnimBP) for driving skeletal mesh animations.

    An AnimBP contains a state machine that transitions between animation states
    based on gameplay conditions (idle, walk, run, jump, etc.).

    Parameters:
        name (str): Name for the AnimBlueprint. Convention: "ABP_" prefix.
            Example: "ABP_Character", "ABP_Enemy"
        skeleton (str): Full UE asset path to the USkeleton this AnimBP targets.
            Example: "/Game/Characters/Mannequins/Meshes/SKM_Manny"

    Returns:
        {"status": "ok", "name": "ABP_Character",
         "path": "/Game/Arcwright/Generated/ABP_Character"}

    Example:
        create_anim_blueprint("ABP_Character", "/Game/Characters/Mannequins/Meshes/SKM_Manny")

    Notes:
        - After creation, add states with add_anim_state, transitions with add_anim_transition,
          and assign animations to states with set_anim_state_animation
        - The skeleton must already exist in the project (import with import_static_mesh or
          use existing project skeletons)
        - Use get_skeleton_bones to inspect available bones on the skeleton
        - Use get_available_animations to find animation assets compatible with the skeleton
    """
    def _run(client):
        return client.send_command("create_anim_blueprint", {"name": name, "skeleton": skeleton})
    return _safe_call(_run)

@mcp.tool()
def add_anim_state(anim_blueprint: str, state_name: str) -> str:
    """Add a state node to an Animation Blueprint's state machine.

    Each state represents a distinct animation pose (Idle, Walking, Running, Jumping, etc.).
    After adding states, wire them together with add_anim_transition and assign animations
    with set_anim_state_animation.

    Parameters:
        anim_blueprint (str): Name of the AnimBlueprint. Example: "ABP_Character"
        state_name (str): Name of the state to create. Example: "Idle", "Running", "Jumping"

    Returns:
        {"status": "ok", "anim_blueprint": "ABP_Character", "state": "Running"}

    Example:
        add_anim_state("ABP_Character", "Idle")
        add_anim_state("ABP_Character", "Running")
        add_anim_state("ABP_Character", "Jumping")

    Notes:
        - Create the AnimBP first with create_anim_blueprint
        - State names should be descriptive and unique within the AnimBP
        - After adding states, use add_anim_transition to define when states switch
        - Use set_anim_state_animation to assign which animation plays in each state
    """
    def _run(client):
        return client.send_command("add_anim_state", {"anim_blueprint": anim_blueprint, "state_name": state_name})
    return _safe_call(_run)

@mcp.tool()
def add_anim_transition(anim_blueprint: str, from_state: str, to_state: str) -> str:
    """Add a transition rule between two states in an Animation Blueprint's state machine.

    Transitions define when the state machine switches from one animation state to another
    (e.g., Idle -> Running when speed > 0, Running -> Jumping when IsJumping is true).

    Parameters:
        anim_blueprint (str): Name of the AnimBlueprint. Example: "ABP_Character"
        from_state (str): Source state name. Example: "Idle"
        to_state (str): Destination state name. Example: "Running"

    Returns:
        {"status": "ok", "anim_blueprint": "ABP_Character", "from": "Idle", "to": "Running"}

    Example:
        add_anim_transition("ABP_Character", "Idle", "Running")
        add_anim_transition("ABP_Character", "Running", "Idle")
        add_anim_transition("ABP_Character", "Running", "Jumping")

    Notes:
        - Both states must already exist (created with add_anim_state)
        - Transitions are one-directional; add the reverse transition separately for bidirectional
        - Transition conditions (when to switch) are configured in the AnimBP editor
        - Typical workflow: create_anim_blueprint -> add_anim_state (x N) ->
          add_anim_transition (x N) -> set_anim_state_animation (x N)
    """
    def _run(client):
        return client.send_command("add_anim_transition", {
            "anim_blueprint": anim_blueprint, "from_state": from_state, "to_state": to_state
        })
    return _safe_call(_run)

@mcp.tool()
def set_anim_state_animation(anim_blueprint: str, state_name: str, animation: str) -> str:
    """Assign an animation sequence to a state in an Animation Blueprint.

    Sets which UAnimSequence plays when the state machine enters this state.
    The animation must be compatible with the AnimBP's target skeleton.

    Parameters:
        anim_blueprint (str): Name of the AnimBlueprint. Example: "ABP_Character"
        state_name (str): Name of the state to assign animation to. Example: "Idle"
        animation (str): Full UE asset path to the AnimSequence.
            Example: "/Game/Characters/Animations/Idle_Anim"

    Returns:
        {"status": "ok", "anim_blueprint": "ABP_Character", "state": "Idle",
         "animation": "/Game/Characters/Animations/Idle_Anim"}

    Example:
        set_anim_state_animation("ABP_Character", "Idle", "/Game/Characters/Animations/Idle_Anim")
        set_anim_state_animation("ABP_Character", "Running", "/Game/Characters/Animations/Run_Fwd")

    Notes:
        - The animation must target the same skeleton as the AnimBP
        - Use get_available_animations to find compatible animations
        - The state must already exist (created with add_anim_state)
        - For animation blending between multiple clips, use create_blend_space instead
    """
    def _run(client):
        return client.send_command("set_anim_state_animation", {
            "anim_blueprint": anim_blueprint, "state_name": state_name, "animation": animation
        })
    return _safe_call(_run)

@mcp.tool()
def create_anim_montage(name: str, animation: str) -> str:
    """Create an Animation Montage from a source AnimSequence for gameplay-triggered animations.

    Montages are used for one-shot gameplay animations like attacks, reloads, hit reactions,
    and ability effects. Unlike state machine animations, montages are played explicitly
    from Blueprint or C++ code via PlayMontage.

    Parameters:
        name (str): Name for the montage. Convention: "AM_" prefix.
            Example: "AM_Attack", "AM_Reload", "AM_HitReact"
        animation (str): Full UE asset path to the source AnimSequence.
            Example: "/Game/Characters/Animations/Attack_Slash"

    Returns:
        {"status": "ok", "name": "AM_Attack",
         "path": "/Game/Arcwright/Generated/AM_Attack"}

    Example:
        create_anim_montage("AM_Attack", "/Game/Characters/Animations/Attack_Slash")
        create_anim_montage("AM_Reload", "/Game/Characters/Animations/Reload_Rifle")

    Notes:
        - After creation, add sections with add_montage_section for timeline markers
        - Montages support animation notify events for triggering effects mid-animation
        - The source animation determines the skeleton; montage inherits it
        - For continuous state-driven animations, use create_anim_blueprint instead
        - At runtime, use PlayAnimMontage in Blueprint nodes to trigger playback
    """
    def _run(client):
        return client.send_command("create_anim_montage", {"name": name, "animation": animation})
    return _safe_call(_run)

@mcp.tool()
def add_montage_section(montage_name: str, section_name: str, start_time: float = 0.0) -> str:
    """Add a named section marker to an Animation Montage at a specific timestamp.

    Sections divide a montage into labeled segments that can be jumped to, looped,
    or branched between at runtime. Common pattern: "WindUp" -> "Strike" -> "Recovery".

    Parameters:
        montage_name (str): Name of the montage. Example: "AM_Attack"
        section_name (str): Name of the section. Example: "WindUp", "Strike", "Recovery"
        start_time (float): Time in seconds where this section begins.
            Default: 0.0.
            Example: 0.5 = section starts at 0.5 seconds into the animation

    Returns:
        {"status": "ok", "montage": "AM_Attack", "section": "Strike", "start_time": 0.5}

    Example:
        add_montage_section("AM_Attack", "WindUp", 0.0)
        add_montage_section("AM_Attack", "Strike", 0.3)
        add_montage_section("AM_Attack", "Recovery", 0.8)

    Notes:
        - The montage must exist (created with create_anim_montage)
        - Sections can be jumped to at runtime via JumpToSection in Blueprint nodes
        - Section names must be unique within the montage
        - Use sections for combo systems: WindUp -> Strike, or Strike -> Strike -> Finisher
    """
    def _run(client):
        return client.send_command("add_montage_section", {
            "montage_name": montage_name, "section_name": section_name, "start_time": start_time
        })
    return _safe_call(_run)

@mcp.tool()
def create_blend_space(
    name: str,
    skeleton: str,
    dimensions: int = 2,
    axis_x: str = "Speed",
    axis_y: str = "Direction",
    x_min: float = -180.0,
    x_max: float = 180.0,
    y_min: float = -180.0,
    y_max: float = 180.0,
) -> str:
    """Create a 1D or 2D Blend Space for smooth animation blending based on gameplay variables.

    Blend Spaces interpolate between multiple animations based on one or two continuous
    parameters (e.g., speed for walk/run blending, or speed+direction for 8-way locomotion).

    Parameters:
        name (str): Name for the blend space. Convention: "BS_" prefix.
            Example: "BS_Locomotion", "BS_AimOffset"
        skeleton (str): Full UE asset path to USkeleton.
            Example: "/Game/Characters/Mannequins/Meshes/SKM_Manny"
        dimensions (int): 1 for 1D blend (single axis), 2 for 2D blend (two axes). Default: 2.
        axis_x (str): Label for the X axis. Default: "Speed". Example: "Speed", "Lean"
        axis_y (str): Label for the Y axis (ignored for 1D). Default: "Direction".
        x_min (float): Minimum X axis value. Default: -180.0.
        x_max (float): Maximum X axis value. Default: 180.0.
        y_min (float): Minimum Y axis value (ignored for 1D). Default: -180.0.
        y_max (float): Maximum Y axis value (ignored for 1D). Default: 180.0.

    Returns:
        {"status": "ok", "name": "BS_Locomotion",
         "path": "/Game/Arcwright/Generated/BS_Locomotion", "dimensions": 2}

    Example:
        create_blend_space("BS_Locomotion", "/Game/Characters/SKM_Manny",
                           dimensions=2, axis_x="Speed", axis_y="Direction",
                           x_min=0, x_max=600, y_min=-180, y_max=180)
        create_blend_space("BS_WalkRun", "/Game/Characters/SKM_Manny",
                           dimensions=1, axis_x="Speed", x_min=0, x_max=600)

    Notes:
        - After creation, add animation samples with add_blend_space_sample
        - 1D: good for walk-to-run blending (single speed parameter)
        - 2D: good for 8-way locomotion (speed + direction), aim offsets (pitch + yaw)
        - The skeleton must match the animations you plan to add as samples
        - Blend Spaces are referenced in Animation Blueprints for continuous blending
    """
    def _run(client):
        params = {
            "name": name, "skeleton": skeleton, "dimensions": dimensions,
            "axis_x": axis_x, "axis_y": axis_y,
            "x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max,
        }
        return client.send_command("create_blend_space", params)
    return _safe_call(_run)

@mcp.tool()
def add_blend_space_sample(blend_space: str, animation: str, x: float = 0.0, y: float = 0.0) -> str:
    """Add an animation sample point to a Blend Space at a specific axis coordinate.

    Each sample maps an animation to a position in the blend space. The blend space
    interpolates between nearby samples based on the runtime parameter value.

    Parameters:
        blend_space (str): Name of the blend space. Example: "BS_Locomotion"
        animation (str): Full UE asset path to AnimSequence.
            Example: "/Game/Characters/Animations/Walk_Fwd"
        x (float): X-axis coordinate for this sample. Default: 0.0.
            Example: 0.0 for idle, 200.0 for walk, 600.0 for run
        y (float): Y-axis coordinate (ignored for 1D blend spaces). Default: 0.0.
            Example: 0.0 for forward, -90.0 for left, 90.0 for right

    Returns:
        {"status": "ok", "blend_space": "BS_Locomotion",
         "animation": "/Game/Characters/Animations/Walk_Fwd", "x": 200.0, "y": 0.0}

    Example:
        add_blend_space_sample("BS_Locomotion", "/Game/Animations/Idle", x=0, y=0)
        add_blend_space_sample("BS_Locomotion", "/Game/Animations/Walk_Fwd", x=200, y=0)
        add_blend_space_sample("BS_Locomotion", "/Game/Animations/Run_Fwd", x=600, y=0)
        add_blend_space_sample("BS_Locomotion", "/Game/Animations/Walk_Left", x=200, y=-90)

    Notes:
        - The blend space must exist (created with create_blend_space)
        - Animation must target the same skeleton as the blend space
        - Place samples at extremes and key points; the engine interpolates between them
        - For 2D: typically place samples in a grid (idle center, directional at edges)
        - Sample positions should fall within the axis min/max ranges defined at creation
    """
    def _run(client):
        return client.send_command("add_blend_space_sample", {
            "blend_space": blend_space, "animation": animation, "x": x, "y": y
        })
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Skeletal mesh & animation playback
# ---------------------------------------------------------------------------

@mcp.tool()
def set_skeletal_mesh(
    mesh: str,
    actor_label: str = "",
    blueprint: str = "",
    component_name: str = "",
) -> str:
    """Set the skeletal mesh asset on an actor's or Blueprint's SkeletalMeshComponent.

    Assigns a SkeletalMesh (character model, weapon, etc.) to either a placed actor
    in the level or a Blueprint template component. Provide either actor_label or blueprint,
    not both.

    Parameters:
        mesh (str): Full UE asset path to the SkeletalMesh.
            Example: "/Game/Characters/Mannequins/Meshes/SKM_Manny"
        actor_label (str): Label of a placed actor in the level. Mutually exclusive with blueprint.
            Example: "Enemy_1"
        blueprint (str): Name of a Blueprint asset. Mutually exclusive with actor_label.
            Example: "BP_Enemy"
        component_name (str): Name of the specific SkeletalMeshComponent. Default: "" (first found).
            Example: "CharacterMesh0", "WeaponMesh"

    Returns:
        {"status": "ok", "mesh": "/Game/Characters/Meshes/SKM_Manny", "target": "Enemy_1"}

    Example:
        set_skeletal_mesh("/Game/Characters/Meshes/SKM_Manny", actor_label="Enemy_1")
        set_skeletal_mesh("/Game/Weapons/SM_Sword", blueprint="BP_Weapon", component_name="WeaponMesh")

    Notes:
        - For Blueprint templates: changes affect all future spawns of that BP
        - For placed actors: changes affect only that specific actor instance
        - The mesh must have a compatible skeleton for animations to work
        - For StaticMesh (non-animated), use set_component_property with static_mesh instead
    """
    def _run(client):
        params = {"mesh": mesh}
        if actor_label: params["actor_label"] = actor_label
        if blueprint: params["blueprint"] = blueprint
        if component_name: params["component_name"] = component_name
        return client.send_command("set_skeletal_mesh", params)
    return _safe_call(_run)

@mcp.tool()
def play_animation(actor_label: str, animation: str, looping: bool = False) -> str:
    """Play an animation sequence on a placed actor's SkeletalMeshComponent.

    Directly plays an AnimSequence on the actor, bypassing any Animation Blueprint.
    Useful for previewing animations in the editor or for simple one-shot playback.

    Parameters:
        actor_label (str): Label of the actor with a SkeletalMeshComponent. Example: "Enemy_1"
        animation (str): Full UE asset path to the AnimSequence to play.
            Example: "/Game/Characters/Animations/Dance"
        looping (bool): Whether the animation should loop continuously. Default: False.

    Returns:
        {"status": "ok", "actor": "Enemy_1",
         "animation": "/Game/Characters/Animations/Dance", "looping": false}

    Example:
        play_animation("Enemy_1", "/Game/Characters/Animations/Idle_Anim", looping=True)
        play_animation("NPC_1", "/Game/Characters/Animations/Wave")

    Notes:
        - This overrides any Animation Blueprint on the actor while playing
        - For gameplay animation systems, use create_anim_blueprint with state machines instead
        - For one-shot gameplay animations (attacks, reloads), use Animation Montages
        - The animation must target the same skeleton as the actor's skeletal mesh
        - Editor preview only; runtime playback requires Blueprint or C++ code
    """
    def _run(client):
        return client.send_command("play_animation", {
            "actor_label": actor_label, "animation": animation, "looping": looping
        })
    return _safe_call(_run)

@mcp.tool()
def get_skeleton_bones(skeleton: str) -> str:
    """List all bones in a skeleton's hierarchy, including parent relationships and indices.

    Use this to discover bone names for attach_actor_to (socket parameter),
    create_anim_blueprint, or any bone-specific operations.

    Parameters:
        skeleton (str): Full UE asset path to the USkeleton.
            Example: "/Game/Characters/Mannequins/Meshes/SKM_Manny"

    Returns:
        {"status": "ok", "skeleton": "/Game/Characters/Meshes/SKM_Manny",
         "bone_count": 67,
         "bones": [
            {"name": "root", "index": 0, "parent": ""},
            {"name": "pelvis", "index": 1, "parent": "root"},
            {"name": "spine_01", "index": 2, "parent": "pelvis"}
         ],
         "sockets": [{"name": "hand_r_socket", "bone": "hand_r"}]}

    Example:
        get_skeleton_bones("/Game/Characters/Mannequins/Meshes/SKM_Manny")

    Notes:
        - Use bone names with attach_actor_to (socket_name parameter)
        - Bone hierarchy is useful for understanding character rig structure
        - Sockets are named attachment points on specific bones (for weapons, props, etc.)
        - To find animations for this skeleton, use get_available_animations
    """
    def _run(client):
        return client.send_command("get_skeleton_bones", {"skeleton": skeleton})
    return _safe_call(_run)

@mcp.tool()
def get_available_animations(skeleton: str = "", name_filter: str = "", max_results: int = 100) -> str:
    """Search for animation assets in the project, optionally filtered by skeleton or name.

    Returns a list of AnimSequence assets with their paths and durations. Use this to
    discover available animations before assigning them to states or blend spaces.

    Parameters:
        skeleton (str): Full UE asset path to filter by skeleton compatibility.
            Example: "/Game/Characters/Mannequins/Meshes/SKM_Manny"
            Default: "" (all skeletons).
        name_filter (str): Substring to match against animation names (case-insensitive).
            Example: "Walk", "Idle", "Attack"
            Default: "" (no filter).
        max_results (int): Maximum number of results to return. Default: 100.

    Returns:
        {"status": "ok", "count": 12,
         "animations": [
            {"name": "Idle_Anim", "path": "/Game/Characters/Animations/Idle_Anim", "duration": 3.2},
            {"name": "Walk_Fwd", "path": "/Game/Characters/Animations/Walk_Fwd", "duration": 1.0}
         ]}

    Example:
        get_available_animations(skeleton="/Game/Characters/Meshes/SKM_Manny")
        get_available_animations(name_filter="Walk")
        get_available_animations(skeleton="/Game/Characters/Meshes/SKM_Manny", name_filter="Attack")

    Notes:
        - Filter by skeleton to find only compatible animations for a specific character
        - Use the returned paths with set_anim_state_animation, add_blend_space_sample,
          create_anim_montage, or play_animation
        - Duration is in seconds
        - Results come from the UE Asset Registry (searches all project content)
    """
    def _run(client):
        params = {"max_results": max_results}
        if skeleton: params["skeleton"] = skeleton
        if name_filter: params["name_filter"] = name_filter
        return client.send_command("get_available_animations", params)
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Niagara particle system commands
# ---------------------------------------------------------------------------

@mcp.tool()
def set_niagara_parameter(
    actor_label: str,
    parameter_name: str,
    float_value: float = None,
    int_value: int = None,
    bool_value: bool = None,
    vector_json: str = "",
    color_json: str = "",
) -> str:
    """Set a user-exposed parameter on an actor's Niagara particle system component.

    Niagara user parameters control particle behavior at runtime: spawn rate, color,
    size, velocity, etc. Provide exactly ONE value type parameter.

    Parameters:
        actor_label (str): Label of the actor with a NiagaraComponent. Example: "Fire_1"
        parameter_name (str): Name of the user parameter defined in the Niagara system.
            Example: "SpawnRate", "ParticleColor", "ParticleSize"
        float_value (float): Float value. Example: 100.0 for spawn rate.
        int_value (int): Integer value. Example: 50 for particle count.
        bool_value (bool): Boolean value. Example: True for enabling a feature.
        vector_json (str): JSON vector for position/velocity/scale parameters.
            Example: '{"x": 0, "y": 0, "z": 500}' for upward velocity
        color_json (str): JSON color for color parameters (0-1 range per channel).
            Example: '{"r": 1.0, "g": 0.3, "b": 0.0, "a": 1.0}' for orange

    Returns:
        {"status": "ok", "actor": "Fire_1", "parameter": "SpawnRate",
         "type": "float", "value": 100.0}

    Example:
        set_niagara_parameter("Fire_1", "SpawnRate", float_value=200.0)
        set_niagara_parameter("Fire_1", "ParticleColor", color_json='{"r":1,"g":0.5,"b":0,"a":1}')
        set_niagara_parameter("Fountain_1", "Velocity", vector_json='{"x":0,"y":0,"z":800}')

    Notes:
        - Provide exactly one value type (float_value, int_value, bool_value, vector_json, or color_json)
        - Parameter names must match the Niagara system's user parameter names exactly
        - Use get_niagara_parameters to discover available parameters and their types
        - Colors use 0-1 range per channel, not 0-255
    """
    def _run(client):
        params = {"actor_label": actor_label, "parameter_name": parameter_name}
        if float_value is not None: params["float_value"] = float_value
        if int_value is not None: params["int_value"] = int_value
        if bool_value is not None: params["bool_value"] = bool_value
        if vector_json: params["vector_value"] = json.loads(vector_json)
        if color_json: params["color_value"] = json.loads(color_json)
        return client.send_command("set_niagara_parameter", params)
    return _safe_call(_run)

@mcp.tool()
def activate_niagara(actor_label: str, activate: bool = True, component_name: str = "") -> str:
    """Activate or deactivate a Niagara particle system component on a placed actor.

    Activating starts particle emission; deactivating stops spawning new particles
    (existing particles may finish their lifetime).

    Parameters:
        actor_label (str): Label of the actor with a NiagaraComponent. Example: "Fire_1"
        activate (bool): True = start emitting, False = stop emitting. Default: True.
        component_name (str): Name of the specific NiagaraComponent if actor has multiple.
            Default: "" (first NiagaraComponent found).

    Returns:
        {"status": "ok", "actor": "Fire_1", "activated": true}

    Example:
        activate_niagara("Fire_1", True)
        activate_niagara("Fire_1", False)
        activate_niagara("MagicEffect_1", True, component_name="TrailParticles")

    Notes:
        - Deactivating stops new particle spawning but existing particles finish naturally
        - Use set_actor_enabled to fully hide an actor including its particles
        - To spawn a new Niagara system, use spawn_niagara_at_location or add_niagara_component
    """
    def _run(client):
        params = {"actor_label": actor_label, "activate": activate}
        if component_name: params["component_name"] = component_name
        return client.send_command("activate_niagara", params)
    return _safe_call(_run)

@mcp.tool()
def get_niagara_parameters(actor_label: str) -> str:
    """List all user-exposed parameters on an actor's Niagara particle system component.

    Returns the parameter names, types, and current values. Use this to discover
    what parameters are available before calling set_niagara_parameter.

    Parameters:
        actor_label (str): Label of the actor with a NiagaraComponent. Example: "Fire_1"

    Returns:
        {"status": "ok", "actor": "Fire_1",
         "parameters": [
            {"name": "SpawnRate", "type": "float", "value": 100.0},
            {"name": "ParticleColor", "type": "color", "value": {"r":1,"g":0.5,"b":0,"a":1}},
            {"name": "Enabled", "type": "bool", "value": true}
         ]}

    Example:
        get_niagara_parameters("Fire_1")

    Notes:
        - Only user-exposed parameters are listed (not internal system parameters)
        - Use the returned parameter names with set_niagara_parameter
        - Parameter types determine which value argument to use in set_niagara_parameter
        - To list available Niagara system assets, use get_niagara_assets
    """
    def _run(client):
        return client.send_command("get_niagara_parameters", {"actor_label": actor_label})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Sublevel / streaming level commands
# ---------------------------------------------------------------------------

@mcp.tool()
def create_sublevel(name: str) -> str:
    """Create a new streaming sublevel and add it to the current persistent world.

    Sublevels allow organizing a large world into logical sections that can be
    loaded/unloaded independently (e.g., separate enemy areas, indoor rooms, boss arenas).

    Parameters:
        name (str): Name for the sublevel. Example: "Sublevel_Enemies", "Sublevel_BossRoom"

    Returns:
        {"status": "ok", "name": "Sublevel_Enemies",
         "path": "/Game/Maps/Sublevel_Enemies"}

    Example:
        create_sublevel("Sublevel_Enemies")
        create_sublevel("Sublevel_Interior")
        create_sublevel("Sublevel_BossArena")

    Notes:
        - The sublevel is created as a streaming level added to the current persistent world
        - Use move_actor_to_sublevel to move actors into the sublevel
        - Use set_level_visibility to show/hide sublevels in the editor
        - Use get_sublevel_list to see all sublevels and their status
        - At runtime, streaming levels can be loaded/unloaded based on proximity or triggers
    """
    def _run(client):
        return client.send_command("create_sublevel", {"name": name})
    return _safe_call(_run)

@mcp.tool()
def set_level_visibility(level_name: str, visible: bool = True) -> str:
    """Show or hide a streaming sublevel in the editor viewport.

    Controls whether a sublevel's actors are visible and interactable in the editor.
    This is an editor-time setting; runtime streaming is controlled separately.

    Parameters:
        level_name (str): Name of the sublevel. Example: "Sublevel_Enemies"
        visible (bool): True = show in editor, False = hide in editor. Default: True.

    Returns:
        {"status": "ok", "level": "Sublevel_Enemies", "visible": true}

    Example:
        set_level_visibility("Sublevel_Enemies", False)
        set_level_visibility("Sublevel_Interior", True)

    Notes:
        - Hiding a sublevel in the editor does NOT unload it; actors still exist
        - Useful for decluttering the editor when working on specific areas
        - Use get_sublevel_list to see current visibility states
        - This is editor visibility only; runtime streaming uses different mechanisms
    """
    def _run(client):
        return client.send_command("set_level_visibility", {"level_name": level_name, "visible": visible})
    return _safe_call(_run)

@mcp.tool()
def get_sublevel_list() -> str:
    """List all levels in the world: the persistent level plus all streaming sublevels.

    Returns each level's name, visibility, load status, and whether it is the persistent
    (main) level. Use this to discover existing sublevels before moving actors or toggling visibility.

    Returns:
        {"status": "ok", "count": 3,
         "levels": [
            {"name": "MainLevel", "visible": true, "loaded": true, "persistent": true},
            {"name": "Sublevel_Enemies", "visible": true, "loaded": true, "persistent": false},
            {"name": "Sublevel_Interior", "visible": false, "loaded": true, "persistent": false}
         ]}

    Example:
        get_sublevel_list()

    Notes:
        - The persistent level (persistent=true) is always loaded and cannot be unloaded
        - Streaming sublevels (persistent=false) can be shown/hidden with set_level_visibility
        - "loaded" indicates whether the level's content is in memory
        - Use create_sublevel to add new streaming sublevels
        - Use move_actor_to_sublevel to organize actors across levels
    """
    def _run(client):
        return client.send_command("get_sublevel_list", {})
    return _safe_call(_run)

@mcp.tool()
def move_actor_to_sublevel(actor_label: str, level_name: str) -> str:
    """Move a placed actor from its current level into a different streaming sublevel.

    Transfers the actor between levels for organizational or streaming purposes.
    The actor retains its position, properties, and components.

    Parameters:
        actor_label (str): Label of the actor to move. Example: "Enemy_1"
        level_name (str): Name of the destination sublevel. Example: "Sublevel_Enemies"

    Returns:
        {"status": "ok", "actor": "Enemy_1", "level": "Sublevel_Enemies"}

    Example:
        move_actor_to_sublevel("Enemy_1", "Sublevel_Enemies")
        move_actor_to_sublevel("TreasureChest_1", "Sublevel_Interior")

    Notes:
        - The destination sublevel must exist (create with create_sublevel)
        - Actor keeps its world position and all properties
        - Useful for organizing large levels: group enemies, props, lighting per sublevel
        - At runtime, unloading the sublevel will remove the actor from the world
        - Use get_sublevel_list to find available sublevels
    """
    def _run(client):
        return client.send_command("move_actor_to_sublevel", {"actor_label": actor_label, "level_name": level_name})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# World & Actor Utilities (150 target)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_world_settings() -> str:
    """Query the world's global physics and gameplay settings.

    Returns gravity, kill Z height, default game mode, and time dilation values.
    Use this to understand the current world configuration before making changes.

    Returns:
        {"status": "ok", "world_name": "ArenaLevel",
         "global_gravity_z": -980.0, "kill_z": -10000.0,
         "default_game_mode": "BP_FirstPersonGameMode",
         "time_dilation": 1.0, "world_gravity_z": -980.0}

    Example:
        get_world_settings()

    Notes:
        - global_gravity_z: -980 is Earth gravity (default), -490 is moon gravity, 0 is zero-G
        - kill_z: actors below this Z height are automatically destroyed (fall-off-map safety)
        - time_dilation: 1.0 = normal speed, 0.5 = slow motion, 2.0 = double speed
        - Use set_world_settings to modify these values
        - Game mode can be changed per-level with set_game_mode
    """
    def _run(client):
        return client.send_command("get_world_settings", {})
    return _safe_call(_run)

@mcp.tool()
def set_world_settings(gravity: float = None, kill_z: float = None, time_dilation: float = None) -> str:
    """Modify world physics and pacing settings (gravity, kill Z, time dilation).

    Only the parameters you provide are changed; unspecified settings keep their current values.

    Parameters:
        gravity (float): Global gravity Z value. Negative = downward. Default: None (unchanged).
            -980 = Earth gravity (UE default), -490 = moon gravity, 0 = zero-G,
            -1960 = heavy gravity (2x Earth)
        kill_z (float): Height below which actors are auto-destroyed. Default: None (unchanged).
            -10000 = UE default. Set lower for deep levels, higher for arenas with pits.
        time_dilation (float): Global time scale. Default: None (unchanged).
            1.0 = normal, 0.5 = slow-mo, 2.0 = double speed. Range: 0.0001 to 20.0.

    Returns:
        {"status": "ok", "changed": "gravity=-490.0, time_dilation=0.5", "count": 2}

    Example:
        set_world_settings(gravity=-490.0)
        set_world_settings(time_dilation=0.5)
        set_world_settings(gravity=0, kill_z=-50000)

    Notes:
        - Gravity affects all physics-simulated actors (falling, projectiles, ragdolls)
        - Time dilation affects all gameplay (animations, physics, timers) uniformly
        - Use get_world_settings to check current values before changing
        - Gravity is world-wide; there's no per-actor gravity override (use force/impulse instead)
    """
    def _run(client):
        params = {}
        if gravity is not None: params["gravity"] = gravity
        if kill_z is not None: params["kill_z"] = kill_z
        if time_dilation is not None: params["time_dilation"] = time_dilation
        return client.send_command("set_world_settings", params)
    return _safe_call(_run)

@mcp.tool()
def get_actor_class(actor_label: str) -> str:
    """Get class information and Blueprint ancestry of a placed actor.

    Returns the actor's class name, whether it was spawned from a Blueprint, the Blueprint
    name, and the full parent class chain. Useful for inspecting unknown actors in a level.

    Parameters:
        actor_label (str): Label of the actor in the level. Example: "Enemy_1"

    Returns:
        {"status": "ok", "actor": "Enemy_1",
         "class_name": "BP_Enemy_C", "class_path": "/Game/Arcwright/Generated/BP_Enemy",
         "is_blueprint": true, "blueprint_name": "BP_Enemy",
         "parent_classes": ["Pawn", "Actor", "Object"]}

    Example:
        get_actor_class("Enemy_1")
        get_actor_class("Floor")

    Notes:
        - is_blueprint=true means the actor was spawned from a Blueprint asset
        - parent_classes shows the full inheritance chain (most derived first)
        - For non-Blueprint actors (e.g., StaticMeshActor), is_blueprint=false
        - Useful with find_actors to understand what class of actors exist in a level
        - The class_path can be used with spawn_actor to create more instances
    """
    def _run(client):
        return client.send_command("get_actor_class", {"actor_label": actor_label})
    return _safe_call(_run)

@mcp.tool()
def set_actor_scale(actor_label: str, scale_x: float = 1.0, scale_y: float = 1.0, scale_z: float = 1.0, uniform: float = None, relative: bool = False) -> str:
    """Set the scale of a placed actor (uniform or per-axis).

    Scales the entire actor and all its components. For scaling multiple actors at once,
    use batch_scale_actors instead.

    Parameters:
        actor_label (str): Label of the actor to scale. Example: "Tree_1"
        scale_x (float): X axis scale factor. Default: 1.0.
        scale_y (float): Y axis scale factor. Default: 1.0.
        scale_z (float): Z axis scale factor. Default: 1.0.
        uniform (float): If set, applies this value to all three axes (overrides x/y/z).
            Example: 2.0 = double size in all directions.
        relative (bool): If True, multiplies current scale (e.g., 2.0 doubles current size).
            If False, replaces current scale. Default: False.

    Returns:
        {"status": "ok", "actor": "Tree_1",
         "old_scale": {"x": 1.0, "y": 1.0, "z": 1.0},
         "new_scale": {"x": 2.0, "y": 2.0, "z": 2.0}}

    Example:
        set_actor_scale("Tree_1", uniform=2.0)
        set_actor_scale("Pillar_1", scale_x=1.0, scale_y=1.0, scale_z=3.0)
        set_actor_scale("Enemy_1", uniform=1.5, relative=True)

    Notes:
        - uniform=2.0 is shorthand for scale_x=2.0, scale_y=2.0, scale_z=2.0
        - relative=True multiplies current scale (useful for "make 50% bigger" operations)
        - relative=False sets absolute scale (1.0, 1.0, 1.0 resets to original size)
        - For batch scaling, use batch_scale_actors with filters
        - Non-uniform scaling (different x/y/z) can cause visual artifacts on some meshes
    """
    def _run(client):
        if uniform is not None:
            scale = uniform
        else:
            scale = {"x": scale_x, "y": scale_y, "z": scale_z}
        return client.send_command("set_actor_scale", {"actor_label": actor_label, "scale": scale, "relative": relative})
    return _safe_call(_run)

# ---------------------------------------------------------------------------
# Compound Workflow Tools (combine multiple TCP commands into one MCP tool)
# ---------------------------------------------------------------------------

def _parse_json_param(value: str, param_name: str):
    """Parse a JSON string parameter, returning empty list on failure."""
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise BlueprintLLMError(f"Invalid JSON in '{param_name}': {e}")

def _compound_call(fn):
    """Execute fn(client) for compound tools — same error handling as _safe_call."""
    try:
        client = _get_client()
    except (ConnectionRefusedError, OSError, TimeoutError) as e:
        return json.dumps({"error": f"Cannot connect to UE command server: {e}"})
    try:
        result = fn(client)
        return json.dumps(result, indent=2)
    except BlueprintLLMError as e:
        return json.dumps({"error": str(e)})
    except (ConnectionError, OSError) as e:
        return json.dumps({"error": f"Connection lost: {e}"})
    finally:
        client.close()

# -- Category 1: Scene Setup --

@mcp.tool()
def setup_playable_scene(lighting_preset: str = "outdoor_day", floor_size: float = 100.0,
                         floor_color_r: float = 0.3, floor_color_g: float = 0.3,
                         floor_color_b: float = 0.3, game_mode: str = "",
                         save: bool = True) -> str:
    """Set up a complete playable level from scratch: lighting, floor, game mode, and save.

    This is typically the FIRST tool to call when building a new level. It combines 4-6 TCP
    commands into one call: setup_scene_lighting, create_simple_material, spawn_actor_at (floor),
    set_actor_material, optionally set_game_mode, and optionally save_all.

    Parameters:
        lighting_preset (str): Lighting environment preset.
            Valid values: "indoor_dark", "indoor_bright", "outdoor_day", "outdoor_night".
            Default: "outdoor_day".
        floor_size (float): Scale multiplier for the ground plane. 100 = 10000x10000 cm area.
            Default: 100.0.
        floor_color_r (float): Floor material red component (0.0-1.0). Default: 0.3.
        floor_color_g (float): Floor material green component (0.0-1.0). Default: 0.3.
        floor_color_b (float): Floor material blue component (0.0-1.0). Default: 0.3.
        game_mode (str): Game mode Blueprint name to set on the level.
            Example: "BP_FirstPersonGameMode". Empty string = skip. Default: "".
        save (bool): Whether to call save_all after setup completes. Default: True.

    Returns:
        {"summary": "Playable scene created", "steps": [{"step": "lighting", "status": "ok"}, ...]}

    Example:
        setup_playable_scene("outdoor_day", 100.0, 0.3, 0.3, 0.3, "BP_FirstPersonGameMode", True)
        setup_playable_scene("indoor_bright", 50.0, 0.8, 0.8, 0.8)

    Notes:
        - Always call this before placing any game actors — without lighting and a floor,
          actors are invisible and fall through the void
        - Creates material "MAT_Floor" at /Game/Arcwright/Materials/
        - Floor spawns at origin (0,0,0) as a StaticMeshActor with Plane mesh
        - For more control over individual steps, use setup_scene_lighting, spawn_actor,
          create_simple_material, set_game_mode separately
        - See also: clear_and_rebuild_level to tear down and rebuild
    """
    def _run(client):
        steps = []
        # 1. Scene lighting
        r = client.send_command("setup_scene_lighting", {"preset": lighting_preset})
        steps.append({"step": "lighting", "status": r.get("status", "error")})

        # 2. Floor material
        client.send_command("create_simple_material", {
            "name": "MAT_Floor", "color": {"r": floor_color_r, "g": floor_color_g, "b": floor_color_b}
        })
        steps.append({"step": "floor_material", "status": "ok"})

        # 3. Floor plane
        r = client.send_command("spawn_actor_at", {
            "class": "StaticMeshActor",
            "location": {"x": 0, "y": 0, "z": 0},
            "label": "Floor",
            "properties": {"mesh": "/Engine/BasicShapes/Plane.Plane",
                           "scale": {"x": floor_size, "y": floor_size, "z": 1}}
        })
        steps.append({"step": "floor_spawn", "status": r.get("status", "error")})

        # 4. Apply floor material
        client.send_command("set_actor_material", {
            "actor_label": "Floor",
            "material_path": "/Game/Arcwright/Materials/MAT_Floor"
        })
        steps.append({"step": "floor_material_apply", "status": "ok"})

        # 5. Game mode (optional)
        if game_mode:
            r = client.send_command("set_game_mode", {"game_mode": game_mode})
            steps.append({"step": "game_mode", "status": r.get("status", "error")})

        # 6. Save
        if save:
            client.send_command("save_all", {})
            steps.append({"step": "save", "status": "ok"})

        return {"summary": "Playable scene created", "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def setup_cinematic_scene(lighting_preset: str = "outdoor_day",
                          sequence_name: str = "Seq_Cinematic",
                          duration: float = 10.0, bloom_intensity: float = 0.5,
                          vignette_intensity: float = 0.3,
                          camera_x: float = 0.0, camera_y: float = -500.0,
                          camera_z: float = 200.0) -> str:
    """Create a scene optimized for cinematic capture: lighting, post-process, camera, and sequence.

    Combines 5-6 TCP commands: setup_scene_lighting, add_post_process_volume,
    set_post_process_settings, create_sequence, spawn_actor_at (CameraActor),
    and optionally add_sequence_track (Transform track on camera).

    Parameters:
        lighting_preset (str): Lighting environment preset.
            Valid values: "indoor_dark", "indoor_bright", "outdoor_day", "outdoor_night".
            Default: "outdoor_day".
        sequence_name (str): Name for the Level Sequence asset.
            Created at /Game/Arcwright/Sequences/. Default: "Seq_Cinematic".
        duration (float): Sequence duration in seconds. Default: 10.0.
        bloom_intensity (float): Bloom effect strength (0.0-5.0). Default: 0.5.
        vignette_intensity (float): Vignette darkening at screen edges (0.0-1.0). Default: 0.3.
        camera_x (float): Camera start position X in cm. Default: 0.0.
        camera_y (float): Camera start position Y in cm. Default: -500.0.
        camera_z (float): Camera start position Z in cm. Default: 200.0.

    Returns:
        {"summary": "Cinematic scene created", "sequence": "Seq_Cinematic",
         "steps": [{"step": "lighting", "status": "ok"}, ...]}

    Example:
        setup_cinematic_scene("outdoor_day", "Seq_Intro", 15.0, 0.8, 0.4, 0, -800, 300)
        setup_cinematic_scene()  # all defaults

    Notes:
        - Creates a CameraActor labeled "CinematicCamera" and binds it to the sequence
          with a Transform track for keyframe animation
        - Post-process volume is set to infinite extent (covers entire level)
        - After setup, use add_keyframe to animate camera movement along the sequence
        - Auto-saves the level after setup
        - For custom post-process settings, use set_post_process_settings on "CinematicPP"
    """
    def _run(client):
        steps = []
        client.send_command("setup_scene_lighting", {"preset": lighting_preset})
        steps.append({"step": "lighting", "status": "ok"})

        client.send_command("add_post_process_volume", {
            "label": "CinematicPP", "location": {"x": 0, "y": 0, "z": 0},
            "infinite_extent": True
        })
        client.send_command("set_post_process_settings", {
            "label": "CinematicPP", "bloom_intensity": bloom_intensity,
            "vignette_intensity": vignette_intensity
        })
        steps.append({"step": "post_process", "status": "ok"})

        client.send_command("create_sequence", {"name": sequence_name, "duration": duration})
        steps.append({"step": "sequence", "status": "ok"})

        client.send_command("spawn_actor_at", {
            "class": "CameraActor", "label": "CinematicCamera",
            "location": {"x": camera_x, "y": camera_y, "z": camera_z}
        })
        steps.append({"step": "camera", "status": "ok"})

        try:
            client.send_command("add_sequence_track", {
                "sequence": sequence_name, "actor_label": "CinematicCamera",
                "track_type": "Transform"
            })
            steps.append({"step": "camera_track", "status": "ok"})
        except Exception:
            steps.append({"step": "camera_track", "status": "skipped"})

        client.send_command("save_all", {})
        return {"summary": "Cinematic scene created", "sequence": sequence_name, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def populate_level_grid(actor_class: str, rows: int = 3, cols: int = 3,
                        spacing_x: float = 200.0, spacing_y: float = 200.0,
                        origin_x: float = 0.0, origin_y: float = 0.0, origin_z: float = 50.0,
                        material_color_r: float = -1.0, material_color_g: float = 0.5,
                        material_color_b: float = 0.5, tag: str = "",
                        label_prefix: str = "Grid") -> str:
    """Spawn actors in a grid pattern with optional material and tagging.

    Combines spawn_actor_at (rows*cols calls), optionally create_simple_material +
    set_actor_material, and optionally batch_set_property for tagging.

    Parameters:
        actor_class (str): Blueprint class path or native class to spawn.
            Example: "/Game/Arcwright/Generated/BP_Coin" or "StaticMeshActor".
        rows (int): Number of rows in the grid. Default: 3.
        cols (int): Number of columns in the grid. Default: 3.
        spacing_x (float): Distance between actors on X axis in cm. Default: 200.0.
        spacing_y (float): Distance between actors on Y axis in cm. Default: 200.0.
        origin_x (float): Grid origin X position in cm. Default: 0.0.
        origin_y (float): Grid origin Y position in cm. Default: 0.0.
        origin_z (float): Grid origin Z position in cm. Default: 50.0.
        material_color_r (float): If >= 0, creates and applies a colored material to all actors.
            Set to -1.0 to skip material creation. Default: -1.0 (no material).
        material_color_g (float): Material green component (0.0-1.0). Default: 0.5.
        material_color_b (float): Material blue component (0.0-1.0). Default: 0.5.
        tag (str): Tag applied to all spawned actors (useful for batch operations later).
            Empty string = no tag. Default: "".
        label_prefix (str): Prefix for actor labels. Actors are labeled "{prefix}_{row}_{col}".
            Default: "Grid".

    Returns:
        {"summary": "Spawned 9 actors in 3x3 grid", "actors": ["Grid_0_0", "Grid_0_1", ...]}

    Example:
        populate_level_grid("/Game/Arcwright/Generated/BP_Coin", 3, 5, 200, 200, 0, 0, 50,
                            1.0, 0.8, 0.0, "coins", "Coin")

    Notes:
        - For more advanced patterns, use spawn_actor_grid (single TCP command, faster)
          or spawn_actor_circle / spawn_actor_line
        - Material is created at /Game/Arcwright/Materials/MAT_{label_prefix}
        - This tool spawns one-by-one with individual set_actor_material calls;
          spawn_actor_grid is more efficient for large grids without material application
    """
    def _run(client):
        spawned = []
        mat_path = None
        if material_color_r >= 0:
            mat_name = f"MAT_{label_prefix}"
            client.send_command("create_simple_material", {
                "name": mat_name,
                "color": {"r": material_color_r, "g": material_color_g, "b": material_color_b}
            })
            mat_path = f"/Game/Arcwright/Materials/{mat_name}"

        for r in range(rows):
            for c in range(cols):
                lbl = f"{label_prefix}_{r}_{c}"
                x = origin_x + c * spacing_x
                y = origin_y + r * spacing_y
                client.send_command("spawn_actor_at", {
                    "class": actor_class, "label": lbl,
                    "location": {"x": x, "y": y, "z": origin_z}
                })
                if mat_path:
                    try:
                        client.send_command("set_actor_material", {
                            "actor_label": lbl, "material_path": mat_path
                        })
                    except Exception:
                        pass
                if tag:
                    try:
                        client.send_command("batch_set_property", {
                            "operations": [{"actor_label": lbl, "property": "tag", "value": tag}]
                        })
                    except Exception:
                        pass
                spawned.append(lbl)

        return {"summary": f"Spawned {len(spawned)} actors in {rows}x{cols} grid", "actors": spawned}
    return _compound_call(_run)

@mcp.tool()
def clear_and_rebuild_level(delete_tag: str = "", delete_class: str = "",
                            delete_labels: str = "",
                            lighting_preset: str = "outdoor_day",
                            floor_size: float = 100.0,
                            floor_color_r: float = 0.3, floor_color_g: float = 0.3,
                            floor_color_b: float = 0.3) -> str:
    """Delete actors matching a filter, then rebuild with lighting and floor.

    Combines batch_delete_actors, setup_scene_lighting, create_simple_material,
    spawn_actor_at (floor), set_actor_material, and save_all. Useful for rapid iteration
    on level designs without restarting the editor.

    Parameters:
        delete_tag (str): Delete all actors with this tag. Default: "".
        delete_class (str): Delete all actors of this class. Default: "".
        delete_labels (str): Comma-separated actor labels to delete.
            Example: "Enemy_0,Enemy_1,OldFloor". Default: "".
        lighting_preset (str): Lighting preset for rebuilt scene.
            Valid values: "indoor_dark", "indoor_bright", "outdoor_day", "outdoor_night".
            Default: "outdoor_day".
        floor_size (float): Scale multiplier for ground plane. Default: 100.0.
        floor_color_r (float): Floor color red (0.0-1.0). Default: 0.3.
        floor_color_g (float): Floor color green (0.0-1.0). Default: 0.3.
        floor_color_b (float): Floor color blue (0.0-1.0). Default: 0.3.

    Returns:
        {"summary": "Level cleared and rebuilt",
         "steps": [{"step": "delete", "deleted": 12}, {"step": "lighting", "status": "ok"}, ...]}

    Example:
        clear_and_rebuild_level("game_objects", "", "", "outdoor_day", 100.0, 0.4, 0.4, 0.4)
        clear_and_rebuild_level("", "StaticMeshActor", "", "indoor_bright")
        clear_and_rebuild_level("", "", "Wall_N,Wall_S,Wall_E,Wall_W")

    Notes:
        - Must specify at least one of delete_tag, delete_class, or delete_labels;
          otherwise no actors are deleted and only the scene is rebuilt
        - Deletion is idempotent: missing actors count as successfully deleted
        - Floor is always spawned at origin (0,0,0) labeled "Floor"
        - Does NOT delete Blueprint assets from the Content Browser, only placed actors
        - For selective deletion without rebuild, use batch_delete_actors directly
    """
    def _run(client):
        steps = []
        # Delete
        params = {}
        if delete_tag:
            params["tag"] = delete_tag
        if delete_class:
            params["class_filter"] = delete_class
        if delete_labels:
            params["labels"] = [l.strip() for l in delete_labels.split(",") if l.strip()]
        if params:
            r = client.send_command("batch_delete_actors", params)
            steps.append({"step": "delete", "deleted": r.get("data", {}).get("deleted", 0)})

        # Rebuild
        client.send_command("setup_scene_lighting", {"preset": lighting_preset})
        steps.append({"step": "lighting", "status": "ok"})

        client.send_command("create_simple_material", {
            "name": "MAT_Floor", "color": {"r": floor_color_r, "g": floor_color_g, "b": floor_color_b}
        })
        client.send_command("spawn_actor_at", {
            "class": "StaticMeshActor", "label": "Floor",
            "location": {"x": 0, "y": 0, "z": 0},
            "properties": {"mesh": "/Engine/BasicShapes/Plane.Plane",
                           "scale": {"x": floor_size, "y": floor_size, "z": 1}}
        })
        client.send_command("set_actor_material", {
            "actor_label": "Floor", "material_path": "/Game/Arcwright/Materials/MAT_Floor"
        })
        steps.append({"step": "floor", "status": "ok"})

        client.send_command("save_all", {})
        return {"summary": "Level cleared and rebuilt", "steps": steps}
    return _compound_call(_run)

# -- Category 2: Game Object Presets --

def _collectible_dsl(name, message):
    return f"""BLUEPRINT: {name}
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="{message}"]
NODE n3: DestroyActor
EXEC n1.Then -> n2.Execute
EXEC n2.Then -> n3.Execute"""

def _hazard_dsl(name, message):
    return f"""BLUEPRINT: {name}
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_ActorBeginOverlap
NODE n2: PrintString [InString="{message}"]
EXEC n1.Then -> n2.Execute"""

def _trigger_dsl(name, message, destroy=False):
    lines = [f"BLUEPRINT: {name}", "PARENT: Actor", "GRAPH: EventGraph",
             "NODE n1: Event_ActorBeginOverlap",
             f'NODE n2: PrintString [InString="{message}"]']
    execs = ["EXEC n1.Then -> n2.Execute"]
    if destroy:
        lines.append("NODE n3: DestroyActor")
        execs.append("EXEC n2.Then -> n3.Execute")
    return "\n".join(lines + [""] + execs)

def _manager_dsl(name):
    return f"""BLUEPRINT: {name}
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Game Manager Active"]
EXEC n1.Then -> n2.Execute"""

@mcp.tool()
def create_collectible(name: str = "BP_Collectible", message: str = "Collected!",
                       color_r: float = 1.0, color_g: float = 0.8, color_b: float = 0.0,
                       mesh: str = "/Engine/BasicShapes/Sphere.Sphere",
                       mesh_scale: float = 0.5, collision_extent: float = 50.0,
                       emissive: float = 0.0,
                       spawn_x: float = None, spawn_y: float = None,
                       spawn_z: float = None) -> str:
    """Create a complete collectible pickup: Blueprint with overlap-destroy logic, mesh,
    collision, colored material, and optional level spawn.

    Combines 4-6 TCP commands: create_blueprint_from_dsl (overlap→PrintString→DestroyActor),
    add_component (BoxCollision + StaticMesh), create_simple_material, and optionally
    spawn_actor_at + set_actor_material.

    Parameters:
        name (str): Blueprint name. Created at /Game/Arcwright/Generated/.
            Default: "BP_Collectible".
        message (str): Message printed when the player overlaps the collectible.
            Default: "Collected!".
        color_r (float): Material color red (0.0-1.0). Default: 1.0 (gold).
        color_g (float): Material color green (0.0-1.0). Default: 0.8.
        color_b (float): Material color blue (0.0-1.0). Default: 0.0.
        mesh (str): Static mesh asset path for the visual representation.
            Default: "/Engine/BasicShapes/Sphere.Sphere".
        mesh_scale (float): Uniform mesh scale. Default: 0.5.
        collision_extent (float): Box collision half-extent in cm. Default: 50.0.
        emissive (float): Emissive glow strength. 0 = no glow, 1.0+ = visible glow.
            Default: 0.0.
        spawn_x (float): X position to spawn the collectible. All three coordinates (x, y, z)
            must be provided to spawn. Default: None (no spawn).
        spawn_y (float): Y position. Default: None.
        spawn_z (float): Z position. Default: None.

    Returns:
        {"summary": "Collectible 'BP_Coin' created", "blueprint": "BP_Coin",
         "steps": [{"step": "blueprint", "status": "ok"}, ...]}

    Example:
        create_collectible("BP_Coin", "Coin collected! +10 points", 1.0, 0.8, 0.0,
                           "/Engine/BasicShapes/Sphere.Sphere", 0.3, 40.0, 0.5, 0, 0, 100)
        create_collectible("BP_HealthPickup", "Health restored!", 0.0, 1.0, 0.3)

    Notes:
        - Blueprint logic: ActorBeginOverlap → PrintString → DestroyActor (self-destructs)
        - Material created at /Game/Arcwright/Materials/MAT_{name}
        - For collectibles without self-destruct, use create_interactive_trigger instead
        - For batch-spawning multiple collectibles, create the BP once, then use
          spawn_actor_grid or populate_level_grid
    """
    def _run(client):
        steps = []
        dsl = _collectible_dsl(name, message)
        r = client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        steps.append({"step": "blueprint", "status": r.get("status", "error")})

        client.send_command("add_component", {
            "blueprint": name, "component_type": "BoxCollision", "component_name": "PickupCollision",
            "properties": {"extent": collision_extent, "generate_overlap_events": True}
        })
        client.send_command("add_component", {
            "blueprint": name, "component_type": "StaticMesh", "component_name": "PickupMesh",
            "properties": {"mesh": mesh, "scale": {"x": mesh_scale, "y": mesh_scale, "z": mesh_scale}}
        })
        steps.append({"step": "components", "status": "ok"})

        mat_name = f"MAT_{name}"
        params = {"name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}}
        if emissive > 0:
            params["emissive"] = emissive
        client.send_command("create_simple_material", params)
        steps.append({"step": "material", "status": "ok"})

        if spawn_x is not None and spawn_y is not None and spawn_z is not None:
            lbl = name.replace("BP_", "")
            client.send_command("spawn_actor_at", {
                "class": f"/Game/Arcwright/Generated/{name}.{name}",
                "label": lbl, "location": {"x": spawn_x, "y": spawn_y, "z": spawn_z}
            })
            client.send_command("set_actor_material", {
                "actor_label": lbl,
                "material_path": f"/Game/Arcwright/Materials/{mat_name}"
            })
            steps.append({"step": "spawn", "actor": lbl, "status": "ok"})

        return {"summary": f"Collectible '{name}' created", "blueprint": name, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_hazard_zone(name: str = "BP_HazardZone",
                       damage_message: str = "Taking Damage!",
                       color_r: float = 1.0, color_g: float = 0.1, color_b: float = 0.1,
                       mesh: str = "/Engine/BasicShapes/Cube.Cube",
                       mesh_scale: float = 2.0, collision_extent: float = 100.0,
                       spawn_x: float = None, spawn_y: float = None,
                       spawn_z: float = None) -> str:
    """Create a damage/hazard zone: Blueprint with overlap-damage logic, glowing red material,
    mesh, collision, and optional level spawn.

    Combines 4-6 TCP commands: create_blueprint_from_dsl (overlap→PrintString),
    add_component (BoxCollision + StaticMesh), create_simple_material (with emissive glow),
    and optionally spawn_actor_at + set_actor_material.

    Parameters:
        name (str): Blueprint name. Default: "BP_HazardZone".
        damage_message (str): Message displayed when the player enters the zone.
            Default: "Taking Damage!".
        color_r (float): Material color red (0.0-1.0). Default: 1.0 (red).
        color_g (float): Material color green (0.0-1.0). Default: 0.1.
        color_b (float): Material color blue (0.0-1.0). Default: 0.1.
        mesh (str): Static mesh for the hazard volume visual.
            Default: "/Engine/BasicShapes/Cube.Cube".
        mesh_scale (float): Uniform mesh scale. Default: 2.0.
        collision_extent (float): Box collision half-extent in cm. Default: 100.0.
        spawn_x (float): X position to spawn. All three (x, y, z) required to spawn.
            Default: None (no spawn).
        spawn_y (float): Y position. Default: None.
        spawn_z (float): Z position. Default: None.

    Returns:
        {"summary": "Hazard zone 'BP_HazardZone' created", "blueprint": "BP_HazardZone",
         "steps": [{"step": "blueprint", "status": "ok"}, ...]}

    Example:
        create_hazard_zone("BP_LavaPool", "Burning!", 1.0, 0.3, 0.0,
                           "/Engine/BasicShapes/Cube.Cube", 3.0, 150.0, 500, 0, 10)
        create_hazard_zone()  # defaults: red glowing cube

    Notes:
        - Unlike collectibles, hazard zones do NOT self-destruct on overlap
        - Material is created with emissive=1.0 for a glowing danger effect
        - For hazards that destroy themselves after triggering, use create_interactive_trigger
          with destroy_on_trigger=True
        - This creates a visual indicator only; actual damage requires Blueprint logic
          using ApplyDamage or modifying health variables
    """
    def _run(client):
        steps = []
        dsl = _hazard_dsl(name, damage_message)
        client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        steps.append({"step": "blueprint", "status": "ok"})

        client.send_command("add_component", {
            "blueprint": name, "component_type": "BoxCollision", "component_name": "DamageCollision",
            "properties": {"extent": collision_extent, "generate_overlap_events": True}
        })
        client.send_command("add_component", {
            "blueprint": name, "component_type": "StaticMesh", "component_name": "HazardMesh",
            "properties": {"mesh": mesh, "scale": {"x": mesh_scale, "y": mesh_scale, "z": mesh_scale}}
        })
        steps.append({"step": "components", "status": "ok"})

        mat_name = f"MAT_{name}"
        client.send_command("create_simple_material", {
            "name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}, "emissive": 1.0
        })
        steps.append({"step": "material", "status": "ok"})

        if spawn_x is not None and spawn_y is not None and spawn_z is not None:
            lbl = name.replace("BP_", "")
            client.send_command("spawn_actor_at", {
                "class": f"/Game/Arcwright/Generated/{name}.{name}",
                "label": lbl, "location": {"x": spawn_x, "y": spawn_y, "z": spawn_z}
            })
            client.send_command("set_actor_material", {
                "actor_label": lbl, "material_path": f"/Game/Arcwright/Materials/{mat_name}"
            })
            steps.append({"step": "spawn", "actor": lbl, "status": "ok"})

        return {"summary": f"Hazard zone '{name}' created", "blueprint": name, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_interactive_trigger(name: str = "BP_Trigger", trigger_type: str = "victory",
                               message: str = "", destroy_on_trigger: bool = False,
                               color_r: float = 0.0, color_g: float = 1.0, color_b: float = 0.0,
                               collision_extent: float = 100.0,
                               spawn_x: float = None, spawn_y: float = None,
                               spawn_z: float = None) -> str:
    """Create a trigger zone (victory, checkpoint, teleporter, or custom) with overlap event,
    message display, colored material with emissive glow, and optional level spawn.

    Combines 3-5 TCP commands: create_blueprint_from_dsl (overlap→PrintString, optionally
    DestroyActor), add_component (BoxCollision), create_simple_material (emissive=0.5),
    and optionally spawn_actor_at + set_actor_material.

    Parameters:
        name (str): Blueprint name. Default: "BP_Trigger".
        trigger_type (str): Trigger preset type. Controls default message and semantics.
            Valid values: "victory", "checkpoint", "teleporter", "custom".
            Default: "victory".
        message (str): Message displayed when triggered. If empty, auto-generated from
            trigger_type: "You Win!", "Checkpoint Reached!", "Teleporting...", or "Triggered!".
            Default: "".
        destroy_on_trigger (bool): If True, the trigger destroys itself after first overlap
            (one-time trigger). Default: False.
        color_r (float): Material color red (0.0-1.0). Default: 0.0 (green).
        color_g (float): Material color green (0.0-1.0). Default: 1.0.
        color_b (float): Material color blue (0.0-1.0). Default: 0.0.
        collision_extent (float): Box collision half-extent in cm. Default: 100.0.
        spawn_x (float): X position to spawn. All three (x, y, z) required. Default: None.
        spawn_y (float): Y position. Default: None.
        spawn_z (float): Z position. Default: None.

    Returns:
        {"summary": "Trigger 'BP_Trigger' (victory) created", "blueprint": "BP_Trigger",
         "steps": [{"step": "blueprint", "status": "ok"}, ...]}

    Example:
        create_interactive_trigger("BP_VictoryZone", "victory", "Level Complete!", False,
                                   0.0, 1.0, 0.0, 150.0, 2000, 0, 50)
        create_interactive_trigger("BP_Checkpoint", "checkpoint", "", False,
                                   0.0, 0.5, 1.0, 100.0, 1000, 0, 50)
        create_interactive_trigger("BP_Pickup", "custom", "Got it!", True)

    Notes:
        - Material is created with emissive=0.5 for a soft glow effect
        - No collision mesh is added (invisible trigger); add a mesh component separately
          with add_component if visual representation is needed
        - For collectibles (overlap→destroy), use create_collectible instead (includes mesh)
        - For damage zones (persistent overlap), use create_hazard_zone
    """
    def _run(client):
        steps = []
        msg = message or {"victory": "You Win!", "checkpoint": "Checkpoint Reached!",
                          "teleporter": "Teleporting...", "custom": "Triggered!"}.get(trigger_type, "Triggered!")
        dsl = _trigger_dsl(name, msg, destroy_on_trigger)
        client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        steps.append({"step": "blueprint", "status": "ok"})

        client.send_command("add_component", {
            "blueprint": name, "component_type": "BoxCollision", "component_name": "TriggerCollision",
            "properties": {"extent": collision_extent, "generate_overlap_events": True}
        })
        steps.append({"step": "components", "status": "ok"})

        mat_name = f"MAT_{name}"
        client.send_command("create_simple_material", {
            "name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}, "emissive": 0.5
        })
        steps.append({"step": "material", "status": "ok"})

        if spawn_x is not None and spawn_y is not None and spawn_z is not None:
            lbl = name.replace("BP_", "")
            client.send_command("spawn_actor_at", {
                "class": f"/Game/Arcwright/Generated/{name}.{name}",
                "label": lbl, "location": {"x": spawn_x, "y": spawn_y, "z": spawn_z}
            })
            client.send_command("set_actor_material", {
                "actor_label": lbl, "material_path": f"/Game/Arcwright/Materials/{mat_name}"
            })
            steps.append({"step": "spawn", "actor": lbl, "status": "ok"})

        return {"summary": f"Trigger '{name}' ({trigger_type}) created", "blueprint": name, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_game_manager(name: str = "BP_GameManager", track_score: bool = True,
                        track_health: bool = True, track_waves: bool = False,
                        create_hud: bool = False, spawn: bool = True) -> str:
    """Create a game manager Blueprint with score/health/wave variables, optional HUD widget,
    and optional level spawn.

    Combines 3-15 TCP commands depending on options: create_blueprint_from_dsl (BeginPlay→Print),
    modify_blueprint (add variables), optionally create_widget_blueprint + add_widget_child +
    set_widget_property (HUD), and optionally spawn_actor_at.

    Parameters:
        name (str): Blueprint name for the game manager. Default: "BP_GameManager".
        track_score (bool): Add an integer "Score" variable (default value 0). Default: True.
        track_health (bool): Add a float "Health" variable (default value 100.0). Default: True.
        track_waves (bool): Add an integer "WaveNumber" variable (default value 1). Default: False.
        create_hud (bool): Also create a "WBP_GameHUD" Widget Blueprint with a HealthBar
            (ProgressBar at top-left) and ScoreText (TextBlock at top-right). Default: False.
        spawn (bool): Spawn the manager actor in the level at origin. Default: True.

    Returns:
        {"summary": "Game manager 'BP_GameManager' created", "blueprint": "BP_GameManager",
         "steps": [{"step": "blueprint", "status": "ok"}, {"step": "variables", "count": 2, ...}, ...]}

    Example:
        create_game_manager("BP_GameManager", True, True, True, True, True)
        create_game_manager("BP_ScoreTracker", True, False, False, False, True)

    Notes:
        - The manager Blueprint has a BeginPlay→PrintString stub by default
        - Variables are added via modify_blueprint; connect them to game logic separately
        - HUD widget positions assume 1920x1080 resolution (HealthBar at 20,20; ScoreText at 1600,20)
        - For a more complete HUD with crosshair, ammo, and wave display, use create_game_hud
        - Manager is spawned at (0, 0, 50) with label "GameManager"
    """
    def _run(client):
        steps = []
        dsl = _manager_dsl(name)
        client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        steps.append({"step": "blueprint", "status": "ok"})

        variables = []
        if track_score:
            variables.append({"name": "Score", "type": "int", "default": "0"})
        if track_health:
            variables.append({"name": "Health", "type": "float", "default": "100.0"})
        if track_waves:
            variables.append({"name": "WaveNumber", "type": "int", "default": "1"})
        if variables:
            client.send_command("modify_blueprint", {"name": name, "add_variables": variables})
            steps.append({"step": "variables", "count": len(variables), "status": "ok"})

        if create_hud:
            hud_name = "WBP_GameHUD"
            client.send_command("create_widget_blueprint", {"name": hud_name})
            client.send_command("add_widget_child", {
                "widget_blueprint": hud_name, "widget_type": "CanvasPanel",
                "widget_name": "RootCanvas"
            })
            if track_health:
                client.send_command("add_widget_child", {
                    "widget_blueprint": hud_name, "parent": "RootCanvas",
                    "widget_type": "ProgressBar", "widget_name": "HealthBar"
                })
                client.send_command("set_widget_property", {
                    "widget_blueprint": hud_name, "widget_name": "HealthBar",
                    "property": "percent", "value": "1.0"
                })
                client.send_command("set_widget_property", {
                    "widget_blueprint": hud_name, "widget_name": "HealthBar",
                    "property": "position", "value": "20,20"
                })
                client.send_command("set_widget_property", {
                    "widget_blueprint": hud_name, "widget_name": "HealthBar",
                    "property": "size", "value": "300,30"
                })
            if track_score:
                client.send_command("add_widget_child", {
                    "widget_blueprint": hud_name, "parent": "RootCanvas",
                    "widget_type": "TextBlock", "widget_name": "ScoreText"
                })
                client.send_command("set_widget_property", {
                    "widget_blueprint": hud_name, "widget_name": "ScoreText",
                    "property": "text", "value": "Score: 0"
                })
                client.send_command("set_widget_property", {
                    "widget_blueprint": hud_name, "widget_name": "ScoreText",
                    "property": "position", "value": "1600,20"
                })
                client.send_command("set_widget_property", {
                    "widget_blueprint": hud_name, "widget_name": "ScoreText",
                    "property": "font_size", "value": "24"
                })
            steps.append({"step": "hud", "widget": hud_name, "status": "ok"})

        if spawn:
            client.send_command("spawn_actor_at", {
                "class": f"/Game/Arcwright/Generated/{name}.{name}",
                "label": "GameManager", "location": {"x": 0, "y": 0, "z": 50}
            })
            steps.append({"step": "spawn", "status": "ok"})

        return {"summary": f"Game manager '{name}' created", "blueprint": name, "steps": steps}
    return _compound_call(_run)

# -- Category 3: Blueprint Scaffolding --

@mcp.tool()
def scaffold_actor_blueprint(name: str, parent_class: str = "Actor",
                             variables: str = "", components: str = "",
                             has_overlap_event: bool = False, has_tick: bool = False,
                             has_begin_play: bool = True) -> str:
    """Create a fully scaffolded Actor Blueprint with variables, components, and starter events
    in one call.

    Combines 3-5 TCP commands: create_blueprint_from_dsl (with selected event stubs),
    modify_blueprint (add variables), add_component (per component), and compile_blueprint.

    Parameters:
        name (str): Blueprint name. Example: "BP_Door", "BP_TreasureChest". Required.
        parent_class (str): UE parent class for the Blueprint.
            Common values: "Actor" (default), "Pawn", "Character", "PlayerController",
            "GameModeBase", "AIController". Default: "Actor".
        variables (str): JSON array string of variables to add.
            Each object: {"name": "Health", "type": "Float", "default": "100.0"}.
            Supported types: Bool, Int, Float, String, Vector, Rotator, Name.
            Default: "" (no variables).
        components (str): JSON array string of components to add.
            Each object: {"type": "StaticMesh", "name": "DoorMesh",
            "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube"}}.
            Supported types: BoxCollision, SphereCollision, StaticMesh, PointLight, SpotLight,
            Audio, Arrow, Scene, Camera, SpringArm, CapsuleCollision.
            Default: "" (no components).
        has_overlap_event (bool): Add an ActorBeginOverlap event stub with PrintString.
            Default: False.
        has_tick (bool): Add a Tick event node (no connected logic). Default: False.
        has_begin_play (bool): Add a BeginPlay event stub with PrintString. Default: True.

    Returns:
        {"summary": "Blueprint 'BP_Door' scaffolded", "blueprint": "BP_Door",
         "steps": [{"step": "blueprint", "status": "ok"}, {"step": "variables", "count": 2}, ...]}

    Example:
        scaffold_actor_blueprint("BP_Door", "Actor",
            '[{"name":"IsOpen","type":"Bool","default":"false"}]',
            '[{"type":"StaticMesh","name":"DoorMesh","properties":{"mesh":"/Engine/BasicShapes/Cube.Cube"}},{"type":"BoxCollision","name":"DoorTrigger","properties":{"extent":100}}]',
            True, False, True)
        scaffold_actor_blueprint("BP_SimpleActor")

    Notes:
        - Event stubs include a PrintString for quick testing; replace with real logic later
        - Blueprint is auto-compiled after all modifications
        - For AI pawns specifically, use scaffold_pawn_blueprint (adds collision + movement)
        - For creating from existing DSL with full node graphs, use create_blueprint_from_dsl
        - Variables and components parameters must be valid JSON strings
    """
    def _run(client):
        steps = []
        # Build DSL with requested events
        events = []
        if has_begin_play:
            events.append('NODE n_bp: Event_BeginPlay\nNODE n_bp_p: PrintString [InString="BeginPlay"]\nEXEC n_bp.Then -> n_bp_p.Execute')
        if has_overlap_event:
            events.append('NODE n_ov: Event_ActorBeginOverlap\nNODE n_ov_p: PrintString [InString="Overlap"]\nEXEC n_ov.Then -> n_ov_p.Execute')
        if has_tick:
            events.append('NODE n_tk: Event_Tick')

        dsl_lines = [f"BLUEPRINT: {name}", f"PARENT: {parent_class}", "GRAPH: EventGraph"]
        for evt in events:
            for line in evt.split("\n"):
                dsl_lines.append(line)
        dsl = "\n".join(dsl_lines)
        client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        steps.append({"step": "blueprint", "status": "ok"})

        # Variables
        vars_list = _parse_json_param(variables, "variables")
        if vars_list:
            client.send_command("modify_blueprint", {"name": name, "add_variables": vars_list})
            steps.append({"step": "variables", "count": len(vars_list), "status": "ok"})

        # Components
        comp_list = _parse_json_param(components, "components")
        for comp in comp_list:
            client.send_command("add_component", {
                "blueprint": name,
                "component_type": comp.get("type", "Scene"),
                "component_name": comp.get("name", comp.get("type", "Component")),
                "properties": comp.get("properties", {})
            })
        if comp_list:
            steps.append({"step": "components", "count": len(comp_list), "status": "ok"})

        client.send_command("compile_blueprint", {"name": name})
        steps.append({"step": "compile", "status": "ok"})

        return {"summary": f"Blueprint '{name}' scaffolded", "blueprint": name, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def scaffold_pawn_blueprint(name: str = "BP_AIPawn",
                            mesh: str = "/Engine/BasicShapes/Cylinder.Cylinder",
                            mesh_scale_x: float = 1.0, mesh_scale_y: float = 1.0,
                            mesh_scale_z: float = 2.0, collision_radius: float = 50.0,
                            variables: str = "",
                            color_r: float = 1.0, color_g: float = 0.1,
                            color_b: float = 0.1) -> str:
    """Create a Pawn Blueprint pre-configured for AI use: mesh, sphere collision,
    and colored material. Uses the proven Pawn + FloatingPawnMovement pattern for simple AI.

    Combines 4-5 TCP commands: create_blueprint_from_dsl (Pawn parent, BeginPlay stub),
    add_component (SphereCollision + StaticMesh), optionally modify_blueprint (variables),
    create_simple_material, and compile_blueprint.

    Parameters:
        name (str): Blueprint name. Default: "BP_AIPawn".
        mesh (str): Visual mesh asset path.
            Default: "/Engine/BasicShapes/Cylinder.Cylinder".
        mesh_scale_x (float): Mesh scale X. Default: 1.0.
        mesh_scale_y (float): Mesh scale Y. Default: 1.0.
        mesh_scale_z (float): Mesh scale Z. Default: 2.0.
        collision_radius (float): Sphere collision radius in cm. Default: 50.0.
        variables (str): JSON array string of additional variables.
            Example: '[{"name":"Health","type":"Float","default":"100.0"}]'.
            Default: "" (no extra variables).
        color_r (float): Material color red (0.0-1.0). Default: 1.0 (red).
        color_g (float): Material color green (0.0-1.0). Default: 0.1.
        color_b (float): Material color blue (0.0-1.0). Default: 0.1.

    Returns:
        {"summary": "AI Pawn 'BP_AIPawn' scaffolded", "blueprint": "BP_AIPawn",
         "steps": [{"step": "blueprint", "status": "ok"}, ...]}

    Example:
        scaffold_pawn_blueprint("BP_Grunt", "/Engine/BasicShapes/Cylinder.Cylinder",
                                1.0, 1.0, 2.0, 40.0,
                                '[{"name":"Health","type":"Float","default":"50.0"}]',
                                1.0, 0.0, 0.0)
        scaffold_pawn_blueprint()  # red cylinder pawn with defaults

    Notes:
        - Creates material at /Game/Arcwright/Materials/MAT_{name}
        - Does NOT attach a BehaviorTree or AIController; use setup_ai_for_pawn or
          create_ai_enemy for full AI setup
        - For Character-based pawns (humanoid locomotion, capsule collision), use
          scaffold_actor_blueprint with parent_class="Character" instead
        - Pawn + FloatingPawnMovement is simpler and more reliable for non-humanoid AI
    """
    def _run(client):
        steps = []
        dsl = f"""BLUEPRINT: {name}
PARENT: Pawn
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="{name} Spawned"]
EXEC n1.Then -> n2.Execute"""
        client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        steps.append({"step": "blueprint", "status": "ok"})

        client.send_command("add_component", {
            "blueprint": name, "component_type": "SphereCollision", "component_name": "PawnCollision",
            "properties": {"radius": collision_radius, "generate_overlap_events": True}
        })
        client.send_command("add_component", {
            "blueprint": name, "component_type": "StaticMesh", "component_name": "PawnMesh",
            "properties": {"mesh": mesh, "scale": {"x": mesh_scale_x, "y": mesh_scale_y, "z": mesh_scale_z}}
        })
        steps.append({"step": "components", "status": "ok"})

        vars_list = _parse_json_param(variables, "variables")
        if vars_list:
            client.send_command("modify_blueprint", {"name": name, "add_variables": vars_list})
            steps.append({"step": "variables", "count": len(vars_list), "status": "ok"})

        mat_name = f"MAT_{name}"
        client.send_command("create_simple_material", {
            "name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}
        })
        steps.append({"step": "material", "status": "ok"})

        client.send_command("compile_blueprint", {"name": name})
        return {"summary": f"AI Pawn '{name}' scaffolded", "blueprint": name, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def duplicate_and_customize(source_name: str, new_name: str,
                            add_variables: str = "", remove_variables: str = "",
                            set_defaults: str = "", add_components: str = "",
                            material_color_r: float = -1.0, material_color_g: float = 0.5,
                            material_color_b: float = 0.5) -> str:
    """Duplicate an existing Blueprint and apply modifications in one call. Ideal for creating
    enemy variants, collectible tiers, or themed copies of a base template.

    Combines 3-6 TCP commands: duplicate_blueprint, modify_blueprint (add/remove variables,
    set CDO defaults), add_component (per new component), optionally create_simple_material,
    and compile_blueprint.

    Parameters:
        source_name (str): Name of the Blueprint to duplicate. Must exist in the Content Browser.
            Required.
        new_name (str): Name for the new copy. Required.
        add_variables (str): JSON array of variables to add to the copy.
            Example: '[{"name":"Damage","type":"Float","default":"25.0"}]'. Default: "".
        remove_variables (str): Comma-separated names of variables to remove from the copy.
            Example: "OldHealth,DeprecatedVar". Default: "".
        set_defaults (str): JSON object of CDO defaults to set on the copy.
            Example: '{"MaxSpeed": "600.0"}'. Default: "".
        add_components (str): JSON array of components to add to the copy.
            Example: '[{"type":"PointLight","name":"GlowLight","properties":{"intensity":5000}}]'.
            Default: "".
        material_color_r (float): If >= 0, creates a new colored material for the copy.
            Set to -1.0 to skip. Default: -1.0.
        material_color_g (float): Material green (0.0-1.0). Default: 0.5.
        material_color_b (float): Material blue (0.0-1.0). Default: 0.5.

    Returns:
        {"summary": "Duplicated 'BP_Enemy' -> 'BP_FastEnemy'", "blueprint": "BP_FastEnemy",
         "steps": [{"step": "duplicate", "status": "ok"}, ...]}

    Example:
        duplicate_and_customize("BP_Enemy", "BP_FastEnemy",
                                '[{"name":"SpeedBoost","type":"Float","default":"2.0"}]',
                                "", '{"MaxSpeed": "800.0"}', "", 0.0, 0.0, 1.0)
        duplicate_and_customize("BP_Coin", "BP_GoldCoin", "", "", "", "",
                                1.0, 0.8, 0.0)

    Notes:
        - The source Blueprint is not modified; only the copy receives changes
        - Material is created at /Game/Arcwright/Materials/MAT_{new_name}
        - The copy inherits all nodes, variables, and components from the source
        - For creating from scratch rather than duplicating, use scaffold_actor_blueprint
        - Creates an asset redirector from old name; use rename_asset for clean renames
    """
    def _run(client):
        steps = []
        client.send_command("duplicate_blueprint", {"name": source_name, "new_name": new_name})
        steps.append({"step": "duplicate", "status": "ok"})

        modify_params = {"name": new_name}
        add_vars = _parse_json_param(add_variables, "add_variables")
        if add_vars:
            modify_params["add_variables"] = add_vars
        rm_vars = [v.strip() for v in remove_variables.split(",") if v.strip()] if remove_variables else []
        if rm_vars:
            modify_params["remove_variables"] = rm_vars
        defaults = _parse_json_param(set_defaults, "set_defaults") if set_defaults else {}
        if isinstance(defaults, dict) and defaults:
            modify_params["set_class_defaults"] = defaults

        if len(modify_params) > 1:
            client.send_command("modify_blueprint", modify_params)
            steps.append({"step": "modify", "status": "ok"})

        comp_list = _parse_json_param(add_components, "add_components")
        for comp in comp_list:
            client.send_command("add_component", {
                "blueprint": new_name,
                "component_type": comp.get("type", "Scene"),
                "component_name": comp.get("name", comp.get("type", "Component")),
                "properties": comp.get("properties", {})
            })
        if comp_list:
            steps.append({"step": "add_components", "count": len(comp_list), "status": "ok"})

        if material_color_r >= 0:
            mat_name = f"MAT_{new_name}"
            client.send_command("create_simple_material", {
                "name": mat_name,
                "color": {"r": material_color_r, "g": material_color_g, "b": material_color_b}
            })
            steps.append({"step": "material", "status": "ok"})

        client.send_command("compile_blueprint", {"name": new_name})
        return {"summary": f"Duplicated '{source_name}' → '{new_name}'", "blueprint": new_name, "steps": steps}
    return _compound_call(_run)

# -- Category 4: Level Population --

@mcp.tool()
def create_arena_layout(width: float = 2000.0, depth: float = 2000.0,
                        wall_height: float = 300.0, wall_thickness: float = 50.0,
                        floor_color_r: float = 0.3, floor_color_g: float = 0.3,
                        floor_color_b: float = 0.3,
                        wall_color_r: float = 0.5, wall_color_g: float = 0.5,
                        wall_color_b: float = 0.5,
                        center_x: float = 0.0, center_y: float = 0.0, center_z: float = 0.0,
                        lighting_preset: str = "indoor_bright",
                        label_prefix: str = "Arena") -> str:
    """Create a complete enclosed arena/room: floor, 4 walls, 2 materials, and lighting.

    Combines 8+ TCP commands: setup_scene_lighting, create_simple_material (floor + wall),
    spawn_actor_at (1 floor + 4 walls), set_actor_material (5 actors), and save_all.

    Parameters:
        width (float): Arena width on X axis in cm. Default: 2000.0.
        depth (float): Arena depth on Y axis in cm. Default: 2000.0.
        wall_height (float): Wall height in cm. Default: 300.0.
        wall_thickness (float): Wall thickness in cm. Default: 50.0.
        floor_color_r (float): Floor material red (0.0-1.0). Default: 0.3.
        floor_color_g (float): Floor material green (0.0-1.0). Default: 0.3.
        floor_color_b (float): Floor material blue (0.0-1.0). Default: 0.3.
        wall_color_r (float): Wall material red (0.0-1.0). Default: 0.5.
        wall_color_g (float): Wall material green (0.0-1.0). Default: 0.5.
        wall_color_b (float): Wall material blue (0.0-1.0). Default: 0.5.
        center_x (float): Arena center X position in cm. Default: 0.0.
        center_y (float): Arena center Y position in cm. Default: 0.0.
        center_z (float): Arena floor Z position in cm. Default: 0.0.
        lighting_preset (str): Lighting preset for the arena.
            Valid values: "indoor_dark", "indoor_bright", "outdoor_day", "outdoor_night".
            Default: "indoor_bright".
        label_prefix (str): Prefix for all spawned actor labels. Produces: {prefix}_Floor,
            {prefix}_WallN, {prefix}_WallS, {prefix}_WallE, {prefix}_WallW.
            Default: "Arena".

    Returns:
        {"summary": "Arena 2000x2000x300 created",
         "steps": [{"step": "lighting", "status": "ok"}, {"step": "walls", "count": 4}, ...]}

    Example:
        create_arena_layout(3000, 2000, 400, 60, 0.4, 0.4, 0.4, 0.6, 0.6, 0.6,
                            0, 0, 0, "indoor_bright", "Arena")
        create_arena_layout()  # 2000x2000 default arena

    Notes:
        - Walls are Cube meshes scaled to fit; positioned at the edges of the floor
        - Materials created: MAT_{prefix}_Floor and MAT_{prefix}_Wall
        - No ceiling is created; add one manually if needed
        - Auto-saves after creation
        - For open-air levels, use setup_playable_scene instead (no walls)
    """
    def _run(client):
        steps = []
        client.send_command("setup_scene_lighting", {"preset": lighting_preset})
        steps.append({"step": "lighting", "status": "ok"})

        # Materials
        client.send_command("create_simple_material", {
            "name": f"MAT_{label_prefix}_Floor",
            "color": {"r": floor_color_r, "g": floor_color_g, "b": floor_color_b}
        })
        client.send_command("create_simple_material", {
            "name": f"MAT_{label_prefix}_Wall",
            "color": {"r": wall_color_r, "g": wall_color_g, "b": wall_color_b}
        })

        # Floor
        fx = width / 100.0
        fy = depth / 100.0
        client.send_command("spawn_actor_at", {
            "class": "StaticMeshActor", "label": f"{label_prefix}_Floor",
            "location": {"x": center_x, "y": center_y, "z": center_z},
            "properties": {"mesh": "/Engine/BasicShapes/Plane.Plane",
                           "scale": {"x": fx, "y": fy, "z": 1}}
        })
        client.send_command("set_actor_material", {
            "actor_label": f"{label_prefix}_Floor",
            "material_path": f"/Game/Arcwright/Materials/MAT_{label_prefix}_Floor"
        })

        # Walls: North, South, East, West
        hw = width / 2.0
        hd = depth / 2.0
        wh = wall_height / 2.0
        wsx = width / 100.0
        wsy = depth / 100.0
        wt = wall_thickness / 100.0
        wh_s = wall_height / 100.0
        walls = [
            (f"{label_prefix}_WallN", center_x, center_y + hd, center_z + wh, wsx, wt, wh_s),
            (f"{label_prefix}_WallS", center_x, center_y - hd, center_z + wh, wsx, wt, wh_s),
            (f"{label_prefix}_WallE", center_x + hw, center_y, center_z + wh, wt, wsy, wh_s),
            (f"{label_prefix}_WallW", center_x - hw, center_y, center_z + wh, wt, wsy, wh_s),
        ]
        for lbl, wx, wy, wz, sx, sy, sz in walls:
            client.send_command("spawn_actor_at", {
                "class": "StaticMeshActor", "label": lbl,
                "location": {"x": wx, "y": wy, "z": wz},
                "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube",
                               "scale": {"x": sx, "y": sy, "z": sz}}
            })
            client.send_command("set_actor_material", {
                "actor_label": lbl,
                "material_path": f"/Game/Arcwright/Materials/MAT_{label_prefix}_Wall"
            })
        steps.append({"step": "walls", "count": 4, "status": "ok"})

        client.send_command("save_all", {})
        return {"summary": f"Arena {width}x{depth}x{wall_height} created", "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def scatter_actors(actor_class: str, count: int = 8, radius: float = 500.0,
                   center_x: float = 0.0, center_y: float = 0.0, center_z: float = 50.0,
                   face_center: bool = False, tag: str = "",
                   label_prefix: str = "Scatter") -> str:
    """Spawn actors in a circular/ring pattern. Useful for placing collectibles, enemies,
    pillars, or decorations in an evenly-spaced ring.

    Combines spawn_actor_at (count calls) and optionally batch_set_property for tagging.
    Calculates positions using trigonometry for even angular distribution.

    Parameters:
        actor_class (str): Blueprint class path or native class to spawn.
            Example: "/Game/Arcwright/Generated/BP_Coin". Required.
        count (int): Number of actors to spawn in the circle. Default: 8.
        radius (float): Circle radius in cm. Default: 500.0.
        center_x (float): Circle center X position. Default: 0.0.
        center_y (float): Circle center Y position. Default: 0.0.
        center_z (float): Circle center Z position. Default: 50.0.
        face_center (bool): If True, each actor's yaw rotation faces the center point.
            Default: False.
        tag (str): Tag applied to all spawned actors for batch operations.
            Default: "" (no tag).
        label_prefix (str): Prefix for actor labels. Actors labeled "{prefix}_{index}".
            Default: "Scatter".

    Returns:
        {"summary": "Scattered 8 actors in radius 500", "actors": ["Scatter_0", "Scatter_1", ...]}

    Example:
        scatter_actors("/Game/Arcwright/Generated/BP_Coin", 12, 800, 0, 0, 50,
                        False, "coins", "Coin")
        scatter_actors("StaticMeshActor", 6, 300, 0, 0, 100, True, "pillars", "Pillar")

    Notes:
        - For grid patterns, use populate_level_grid or spawn_actor_grid
        - For line patterns, use spawn_actor_line
        - This tool spawns one-by-one; for large counts without tagging or facing,
          spawn_actor_circle (single TCP command) is more efficient
        - Does not apply materials; use batch_apply_material afterward if needed
    """
    def _run(client):
        import math
        spawned = []
        for i in range(count):
            angle = (2 * math.pi * i) / count
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            lbl = f"{label_prefix}_{i}"
            params = {
                "class": actor_class, "label": lbl,
                "location": {"x": x, "y": y, "z": center_z}
            }
            if face_center:
                # Face toward center
                face_angle = math.degrees(math.atan2(center_y - y, center_x - x))
                params["rotation"] = {"pitch": 0, "yaw": face_angle, "roll": 0}
            client.send_command("spawn_actor_at", params)
            if tag:
                try:
                    client.send_command("batch_set_property", {
                        "operations": [{"actor_label": lbl, "property": "tag", "value": tag}]
                    })
                except Exception:
                    pass
            spawned.append(lbl)
        return {"summary": f"Scattered {len(spawned)} actors in radius {radius}", "actors": spawned}
    return _compound_call(_run)

@mcp.tool()
def create_obstacle_course(hazard_count: int = 5,
                           start_x: float = 0.0, start_y: float = 0.0, start_z: float = 0.0,
                           end_x: float = 2000.0, end_y: float = 0.0, end_z: float = 0.0,
                           hazard_class: str = "", hazard_scale: float = 1.0,
                           color_r: float = 1.0, color_g: float = 0.1, color_b: float = 0.1,
                           label_prefix: str = "Obstacle") -> str:
    """Create an obstacle course: evenly spaced hazard zones along a line from start to end.

    If no hazard_class is provided, auto-creates a "BP_ObstacleCourse" hazard Blueprint
    (overlap→PrintString, BoxCollision, Cube mesh, emissive red material). Combines
    create_blueprint_from_dsl + add_component + create_simple_material + spawn_actor_at
    (hazard_count calls) + optionally set_actor_scale + set_actor_material.

    Parameters:
        hazard_count (int): Number of hazard obstacles to place. Default: 5.
        start_x (float): Course start X position. Default: 0.0.
        start_y (float): Course start Y position. Default: 0.0.
        start_z (float): Course start Z position. Default: 0.0.
        end_x (float): Course end X position. Default: 2000.0.
        end_y (float): Course end Y position. Default: 0.0.
        end_z (float): Course end Z position. Default: 0.0.
        hazard_class (str): Existing hazard Blueprint class path. If empty, creates one
            automatically. Example: "/Game/Arcwright/Generated/BP_LavaPool.BP_LavaPool".
            Default: "" (auto-create).
        hazard_scale (float): Uniform scale for each hazard actor. Default: 1.0.
        color_r (float): Hazard material red (0.0-1.0). Only used for auto-created BP.
            Default: 1.0.
        color_g (float): Hazard material green (0.0-1.0). Default: 0.1.
        color_b (float): Hazard material blue (0.0-1.0). Default: 0.1.
        label_prefix (str): Label prefix for spawned obstacles.
            Actors labeled "{prefix}_{index}". Default: "Obstacle".

    Returns:
        {"summary": "Obstacle course: 5 hazards",
         "actors": ["Obstacle_0", "Obstacle_1", ...],
         "steps": [{"step": "hazard_blueprint", "status": "ok"}, {"step": "spawn", "count": 5}]}

    Example:
        create_obstacle_course(8, 0, 0, 50, 3000, 0, 50, "", 1.5, 1.0, 0.2, 0.0, "Hazard")
        create_obstacle_course(5, 0, -500, 50, 0, 500, 50)  # perpendicular course

    Notes:
        - Obstacles are evenly spaced along the line from start to end using linear interpolation
        - The auto-created hazard BP uses overlap→PrintString("Ouch!") logic
        - For custom hazard behavior, create the BP first with create_hazard_zone, then
          pass its class path as hazard_class
        - Place a floor and victory trigger at each end to complete the course
    """
    def _run(client):
        steps = []
        bp_class = hazard_class
        if not bp_class:
            dsl = _hazard_dsl("BP_ObstacleCourse", "Ouch!")
            client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
            client.send_command("add_component", {
                "blueprint": "BP_ObstacleCourse", "component_type": "BoxCollision",
                "component_name": "Col", "properties": {"extent": 50, "generate_overlap_events": True}
            })
            client.send_command("add_component", {
                "blueprint": "BP_ObstacleCourse", "component_type": "StaticMesh",
                "component_name": "Mesh",
                "properties": {"mesh": "/Engine/BasicShapes/Cube.Cube"}
            })
            mat_name = "MAT_ObstacleCourse"
            client.send_command("create_simple_material", {
                "name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}, "emissive": 1.0
            })
            bp_class = "/Game/Arcwright/Generated/BP_ObstacleCourse.BP_ObstacleCourse"
            steps.append({"step": "hazard_blueprint", "status": "ok"})

        spawned = []
        for i in range(hazard_count):
            t = i / max(hazard_count - 1, 1)
            x = start_x + t * (end_x - start_x)
            y = start_y + t * (end_y - start_y)
            z = start_z + t * (end_z - start_z)
            lbl = f"{label_prefix}_{i}"
            client.send_command("spawn_actor_at", {
                "class": bp_class, "label": lbl,
                "location": {"x": x, "y": y, "z": z}
            })
            if hazard_scale != 1.0:
                client.send_command("set_actor_scale", {
                    "actor_label": lbl, "scale": hazard_scale
                })
            if not hazard_class:
                try:
                    client.send_command("set_actor_material", {
                        "actor_label": lbl,
                        "material_path": "/Game/Arcwright/Materials/MAT_ObstacleCourse"
                    })
                except Exception:
                    pass
            spawned.append(lbl)
        steps.append({"step": "spawn", "count": len(spawned), "status": "ok"})

        return {"summary": f"Obstacle course: {hazard_count} hazards", "actors": spawned, "steps": steps}
    return _compound_call(_run)

# -- Category 5: Query & Report --

@mcp.tool()
def audit_level(include_actor_details: bool = False, include_materials: bool = True,
                check_common_issues: bool = True) -> str:
    """Generate a comprehensive audit report of the current level: actor counts by class,
    Blueprint inventory, material list, world settings, and common issue diagnostics.

    Combines 4-5 TCP query commands: get_level_info, get_world_settings, find_actors,
    find_blueprints, and optionally find_assets (for materials).

    Parameters:
        include_actor_details (bool): Include per-actor transform, components, and class info
            (up to 100 actors). Default: False.
        include_materials (bool): Include a list of all Material assets in the project.
            Default: True.
        check_common_issues (bool): Run diagnostics that check for missing lighting,
            missing floor/ground, and other common problems. Default: True.

    Returns:
        {"level": {"name": "ArenaLevel", "path": "/Game/Maps/ArenaLevel", "actor_count": 42},
         "world_settings": {"global_gravity_z": -980.0, ...},
         "actor_count": 42,
         "actors_by_class": {"StaticMeshActor": 15, "PointLight": 3, ...},
         "blueprints": ["BP_Enemy", "BP_Coin", ...],
         "materials": ["MAT_Floor", "MAT_Wall", ...],
         "diagnostics": ["WARNING: No light actors found"]}

    Example:
        audit_level(True, True, True)   # full audit with actor details
        audit_level(False, False, True)  # quick diagnostics only

    Notes:
        - Diagnostics check for: no light actors (level may be dark),
          no floor/plane actors (players may fall through)
        - Actor details are capped at 100 to avoid oversized responses
        - Use this to verify level state before and after making changes
        - For per-actor property inspection, use get_actor_properties on specific actors
        - For Blueprint-only inspection, use get_blueprint_info or compare_blueprints
    """
    def _run(client):
        report = {}

        # Level info
        level = client.send_command("get_level_info", {})
        report["level"] = level.get("data", {})

        # World settings
        ws = client.send_command("get_world_settings", {})
        report["world_settings"] = ws.get("data", {})

        # Actors
        actors = client.send_command("find_actors", {"name_filter": ""})
        actor_list = actors.get("data", {}).get("actors", [])
        report["actor_count"] = len(actor_list)

        # Class breakdown
        class_counts = {}
        for a in actor_list:
            cls = a.get("class", "Unknown")
            class_counts[cls] = class_counts.get(cls, 0) + 1
        report["actors_by_class"] = class_counts

        if include_actor_details:
            report["actors"] = actor_list[:100]

        # Blueprints
        bps = client.send_command("find_blueprints", {})
        report["blueprints"] = [b.get("name", "") for b in bps.get("data", {}).get("blueprints", [])]

        # Materials
        if include_materials:
            mats = client.send_command("find_assets", {"type": "Material"})
            report["materials"] = [m.get("name", "") for m in mats.get("data", {}).get("assets", [])]

        # Diagnostics
        if check_common_issues:
            issues = []
            has_light = any("Light" in cls for cls in class_counts)
            if not has_light:
                issues.append("WARNING: No light actors found — level may be dark")
            has_floor = any("Floor" in a.get("label", "") or "Plane" in a.get("class", "")
                           for a in actor_list)
            if not has_floor:
                issues.append("WARNING: No floor/plane found — players may fall through")
            report["diagnostics"] = issues

        return report
    return _compound_call(_run)

@mcp.tool()
def compare_blueprints(blueprint_a: str, blueprint_b: str) -> str:
    """Compare two Blueprints side-by-side: parent class, variables, node counts, and components.

    Combines 4 TCP commands: get_blueprint_info (x2) and get_components (x2).

    Parameters:
        blueprint_a (str): First Blueprint name. Must exist. Required.
        blueprint_b (str): Second Blueprint name. Must exist. Required.

    Returns:
        {"blueprint_a": {"name": "BP_Enemy", "parent": "Pawn", "variables": [...],
                          "node_count": 5, "components": [...]},
         "blueprint_b": {"name": "BP_FastEnemy", "parent": "Pawn", "variables": [...],
                          "node_count": 5, "components": [...]},
         "differences": {"parent_class": false, "variable_count": true, "component_count": false}}

    Example:
        compare_blueprints("BP_Enemy", "BP_FastEnemy")
        compare_blueprints("BP_Coin", "BP_GoldCoin")

    Notes:
        - The "differences" section flags simple count/type mismatches, not deep content diffs
        - For detailed node-level inspection, use get_blueprint_info on each BP separately
        - Use this to verify that duplicate_and_customize produced the expected changes
    """
    def _run(client):
        info_a = client.send_command("get_blueprint_info", {"name": blueprint_a})
        info_b = client.send_command("get_blueprint_info", {"name": blueprint_b})
        comp_a = client.send_command("get_components", {"blueprint": blueprint_a})
        comp_b = client.send_command("get_components", {"blueprint": blueprint_b})

        da = info_a.get("data", {})
        db = info_b.get("data", {})

        return {
            "blueprint_a": {
                "name": blueprint_a,
                "parent": da.get("parent_class", ""),
                "variables": da.get("variables", []),
                "node_count": da.get("node_count", len(da.get("nodes", []))),
                "components": comp_a.get("data", {}).get("components", []),
            },
            "blueprint_b": {
                "name": blueprint_b,
                "parent": db.get("parent_class", ""),
                "variables": db.get("variables", []),
                "node_count": db.get("node_count", len(db.get("nodes", []))),
                "components": comp_b.get("data", {}).get("components", []),
            },
            "differences": {
                "parent_class": da.get("parent_class") != db.get("parent_class"),
                "variable_count": len(da.get("variables", [])) != len(db.get("variables", [])),
                "component_count": len(comp_a.get("data", {}).get("components", [])) !=
                                   len(comp_b.get("data", {}).get("components", [])),
            }
        }
    return _compound_call(_run)

@mcp.tool()
def inventory_game_objects(categories: str = "collectible,enemy,hazard,trigger,manager",
                           include_locations: bool = True,
                           max_per_category: int = 50) -> str:
    """Scan the level and categorize game objects by type using name-based search.

    Calls find_actors once per category, searching actor labels for the category keyword.
    Useful for getting a quick overview of what game objects exist in the level.

    Parameters:
        categories (str): Comma-separated category keywords to search for.
            Each keyword is matched against actor labels via find_actors name_filter.
            Default: "collectible,enemy,hazard,trigger,manager".
        include_locations (bool): Include per-actor location {x, y, z} in results.
            Default: True.
        max_per_category (int): Maximum actors returned per category. Default: 50.

    Returns:
        {"inventory": {
            "collectible": [{"label": "Coin_0", "class": "BP_Coin_C", "location": {...}}, ...],
            "enemy": [{"label": "Enemy_0", "class": "BP_Enemy_C", "location": {...}}, ...],
            ...
         },
         "total": 24}

    Example:
        inventory_game_objects("collectible,enemy,hazard,trigger", True, 100)
        inventory_game_objects("door,light,camera", False, 25)

    Notes:
        - Searches by label substring match, not class type; actors must have descriptive labels
        - For class-based search, use find_actors with class_filter directly
        - For a full level audit including non-game actors, use audit_level
        - Returns at most max_per_category actors per category to keep response size manageable
    """
    def _run(client):
        cats = [c.strip() for c in categories.split(",") if c.strip()]
        result = {}
        for cat in cats:
            r = client.send_command("find_actors", {"name_filter": cat})
            actors = r.get("data", {}).get("actors", [])[:max_per_category]
            if include_locations:
                result[cat] = [{"label": a.get("label", ""), "class": a.get("class", ""),
                                "location": a.get("location", {})} for a in actors]
            else:
                result[cat] = [{"label": a.get("label", ""), "class": a.get("class", "")}
                               for a in actors]
        return {"inventory": result, "total": sum(len(v) for v in result.values())}
    return _compound_call(_run)

# -- Category 6: Asset Pipeline --

@mcp.tool()
def import_and_apply_mesh(mesh_path: str, asset_name: str = "",
                          blueprint_name: str = "",
                          color_r: float = -1.0, color_g: float = 0.5, color_b: float = 0.5,
                          spawn_x: float = None, spawn_y: float = None,
                          spawn_z: float = None, scale: float = 1.0) -> str:
    """Import a 3D mesh file (.fbx/.obj), optionally wrap it in a Blueprint, apply a colored
    material, and spawn it in the level. Full Blender-to-UE-to-level pipeline in one call.

    Combines 2-6 TCP commands: import_static_mesh, optionally create_simple_material,
    optionally create_blueprint_from_dsl + add_component (mesh wrapper BP), optionally
    spawn_actor_at + set_actor_material.

    Parameters:
        mesh_path (str): Local file path to .fbx or .obj file.
            Example: "C:/Arcwright/exports/SM_Crystal.fbx". Required.
        asset_name (str): UE asset name. Derived from filename if empty.
            Imported to /Game/Arcwright/Meshes/. Default: "".
        blueprint_name (str): If non-empty, creates an Actor Blueprint with this mesh as a
            StaticMesh component. Example: "BP_Crystal". Default: "" (no BP wrapper).
        color_r (float): Material color red. If >= 0, creates a colored material.
            Set to -1.0 to skip material creation. Default: -1.0.
        color_g (float): Material color green (0.0-1.0). Default: 0.5.
        color_b (float): Material color blue (0.0-1.0). Default: 0.5.
        spawn_x (float): X position to spawn. All three (x, y, z) required. Default: None.
        spawn_y (float): Y position. Default: None.
        spawn_z (float): Z position. Default: None.
        scale (float): Uniform spawn scale. Default: 1.0.

    Returns:
        {"summary": "Mesh imported and applied",
         "mesh_path": "/Game/Arcwright/Meshes/SM_Crystal",
         "steps": [{"step": "import_mesh", "path": "...", "status": "ok"}, ...]}

    Example:
        import_and_apply_mesh("C:/Arcwright/exports/SM_Crystal.fbx", "SM_Crystal",
                              "BP_Crystal", 0.2, 0.8, 1.0, 0, 0, 100, 2.0)
        import_and_apply_mesh("C:/exports/mesh.fbx")  # import only, no BP/material/spawn

    Notes:
        - If the mesh already exists in UE, returns the existing asset path without re-importing
        - Without blueprint_name, spawns as StaticMeshActor (raw mesh placement)
        - With blueprint_name, spawns the BP which includes the mesh as a component
        - Material created at /Game/Arcwright/Materials/MAT_{asset_name}
        - For texture import, use import_texture_and_create_material
    """
    def _run(client):
        steps = []
        r = client.send_command("import_static_mesh", {"file_path": mesh_path, "asset_name": asset_name})
        mesh_ue_path = r.get("data", {}).get("asset_path", "")
        steps.append({"step": "import_mesh", "path": mesh_ue_path, "status": r.get("status", "error")})

        mat_path = None
        if color_r >= 0:
            mat_name = f"MAT_{asset_name or 'ImportedMesh'}"
            client.send_command("create_simple_material", {
                "name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}
            })
            mat_path = f"/Game/Arcwright/Materials/{mat_name}"
            steps.append({"step": "material", "status": "ok"})

        if blueprint_name:
            dsl = f"BLUEPRINT: {blueprint_name}\nPARENT: Actor\nGRAPH: EventGraph\nNODE n1: Event_BeginPlay"
            client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
            client.send_command("add_component", {
                "blueprint": blueprint_name, "component_type": "StaticMesh",
                "component_name": "ImportedMesh",
                "properties": {"mesh": mesh_ue_path}
            })
            steps.append({"step": "blueprint", "status": "ok"})

        if spawn_x is not None and spawn_y is not None and spawn_z is not None:
            spawn_class = f"/Game/Arcwright/Generated/{blueprint_name}.{blueprint_name}" if blueprint_name else "StaticMeshActor"
            lbl = blueprint_name or asset_name or "ImportedMesh"
            sp = {"class": spawn_class, "label": lbl,
                  "location": {"x": spawn_x, "y": spawn_y, "z": spawn_z}}
            if scale != 1.0:
                sp["properties"] = {"scale": {"x": scale, "y": scale, "z": scale}}
            if not blueprint_name and mesh_ue_path:
                sp.setdefault("properties", {})["mesh"] = mesh_ue_path
            client.send_command("spawn_actor_at", sp)
            if mat_path:
                client.send_command("set_actor_material", {
                    "actor_label": lbl, "material_path": mat_path
                })
            steps.append({"step": "spawn", "status": "ok"})

        return {"summary": "Mesh imported and applied", "mesh_path": mesh_ue_path, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_material_library(materials: str) -> str:
    """Batch-create multiple colored materials in one call. Ideal for setting up a project's
    material palette at the start of level building.

    Calls create_simple_material once per material definition. Fault-tolerant: individual
    failures do not abort the batch.

    Parameters:
        materials (str): JSON array of material definitions. Each object requires "name"
            and optional "r", "g", "b" (0.0-1.0, default 0.5) and "emissive" (float).
            Example: '[{"name":"MAT_Gold","r":1.0,"g":0.8,"b":0.0},
                        {"name":"MAT_Danger","r":1.0,"g":0.1,"b":0.1,"emissive":2.0},
                        {"name":"MAT_Ice","r":0.6,"g":0.8,"b":1.0}]'.
            Required.

    Returns:
        {"summary": "Created 3/3 materials",
         "created": ["MAT_Gold", "MAT_Danger", "MAT_Ice"],
         "errors": []}

    Example:
        create_material_library('[{"name":"MAT_Gold","r":1.0,"g":0.8,"b":0.0},{"name":"MAT_Stone","r":0.4,"g":0.4,"b":0.4},{"name":"MAT_Lava","r":1.0,"g":0.2,"b":0.0,"emissive":3.0}]')

    Notes:
        - Materials are created at /Game/Arcwright/Materials/{name}
        - Uses create_simple_material (works with UE 5.7 Substrate rendering)
        - For textured materials (from image files), use import_texture_and_create_material
        - Apply created materials to actors with set_actor_material or batch_apply_material
        - Existing materials with the same name are overwritten
    """
    def _run(client):
        mat_list = _parse_json_param(materials, "materials")
        created = []
        errors = []
        for m in mat_list:
            try:
                params = {
                    "name": m["name"],
                    "color": {"r": m.get("r", 0.5), "g": m.get("g", 0.5), "b": m.get("b", 0.5)}
                }
                if m.get("emissive"):
                    params["emissive"] = m["emissive"]
                client.send_command("create_simple_material", params)
                created.append(m["name"])
            except Exception as e:
                errors.append({"name": m.get("name", "?"), "error": str(e)})
        return {"summary": f"Created {len(created)}/{len(mat_list)} materials",
                "created": created, "errors": errors}
    return _compound_call(_run)

@mcp.tool()
def import_texture_and_create_material(texture_path: str, material_name: str = "",
                                       roughness: float = 0.5, metallic: float = 0.0,
                                       tiling: float = 1.0, apply_to_actor: str = "",
                                       apply_to_blueprint: str = "") -> str:
    """Import a texture file, create a textured material from it, and optionally apply it
    to an actor or Blueprint.

    Combines 2-4 TCP commands: import_texture, create_textured_material, optionally
    set_actor_material and/or apply_material.

    Parameters:
        texture_path (str): Local file path to an image file.
            Supported formats: .png, .jpg, .tga.
            Example: "C:/Arcwright/exports/T_StoneWall.png". Required.
        material_name (str): Name for the material. If empty, derived from the texture filename.
            Auto-prefixed with "MAT_" if not already prefixed. Default: "".
        roughness (float): Material roughness (0.0 = mirror, 1.0 = matte). Default: 0.5.
        metallic (float): Material metallic value (0.0 = non-metal, 1.0 = full metal).
            Default: 0.0.
        tiling (float): UV tiling multiplier. Higher values repeat the texture more often.
            Default: 1.0.
        apply_to_actor (str): Actor label to apply the material to via set_actor_material.
            Default: "" (don't apply).
        apply_to_blueprint (str): Blueprint name to apply the material to via apply_material.
            Default: "" (don't apply).

    Returns:
        {"summary": "Texture imported and material created",
         "material": "/Game/Arcwright/Materials/MAT_StoneWall",
         "steps": [{"step": "import_texture", "path": "...", "status": "ok"},
                    {"step": "material", "path": "...", "status": "ok"}, ...]}

    Example:
        import_texture_and_create_material("C:/exports/T_BrickWall.png", "MAT_Brick",
                                           0.8, 0.0, 2.0, "Wall_N", "")
        import_texture_and_create_material("C:/exports/T_Metal.png", "", 0.2, 0.9, 1.0)

    Notes:
        - Texture imported to /Game/Arcwright/Textures/
        - Material created at /Game/Arcwright/Materials/
        - If texture already exists in UE, returns existing path without re-importing
        - For simple solid-color materials (no texture), use create_simple_material
        - For batch color materials, use create_material_library
    """
    def _run(client):
        steps = []
        r = client.send_command("import_texture", {"file_path": texture_path, "asset_name": material_name})
        tex_path = r.get("data", {}).get("asset_path", "")
        steps.append({"step": "import_texture", "path": tex_path, "status": r.get("status", "error")})

        mat_name = material_name or os.path.splitext(os.path.basename(texture_path))[0]
        mat_name = f"MAT_{mat_name}" if not mat_name.startswith("MAT_") else mat_name
        client.send_command("create_textured_material", {
            "name": mat_name, "texture": tex_path,
            "roughness": roughness, "metallic": metallic, "tiling": tiling
        })
        mat_ue_path = f"/Game/Arcwright/Materials/{mat_name}"
        steps.append({"step": "material", "path": mat_ue_path, "status": "ok"})

        if apply_to_actor:
            client.send_command("set_actor_material", {
                "actor_label": apply_to_actor, "material_path": mat_ue_path
            })
            steps.append({"step": "apply_to_actor", "actor": apply_to_actor, "status": "ok"})

        if apply_to_blueprint:
            client.send_command("apply_material", {
                "blueprint": apply_to_blueprint, "material_path": mat_ue_path
            })
            steps.append({"step": "apply_to_blueprint", "bp": apply_to_blueprint, "status": "ok"})

        return {"summary": "Texture imported and material created", "material": mat_ue_path, "steps": steps}
    return _compound_call(_run)

# -- Category 7: AI Setup --

@mcp.tool()
def create_ai_enemy(name: str = "BP_Enemy", bt_name: str = "BT_EnemyPatrol",
                    mesh: str = "/Engine/BasicShapes/Cylinder.Cylinder",
                    color_r: float = 1.0, color_g: float = 0.1, color_b: float = 0.1,
                    move_speed: float = 400.0, collision_radius: float = 50.0,
                    spawn_x: float = None, spawn_y: float = None,
                    spawn_z: float = None) -> str:
    """Create a complete AI enemy end-to-end: Pawn Blueprint, BehaviorTree, AIController,
    material, movement settings, all wired together, and optionally spawned in the level.

    Combines 6-8 TCP commands: create_blueprint_from_dsl (Pawn), add_component (SphereCollision
    + StaticMesh), create_simple_material, create_behavior_tree (patrol: MoveTo→Wait loop),
    setup_ai_for_pawn (creates AIController + wires BT + sets AutoPossessAI), optionally
    set_movement_defaults, spawn_actor_at, and set_actor_material.

    Parameters:
        name (str): Pawn Blueprint name. Default: "BP_Enemy".
        bt_name (str): Behavior Tree asset name. Creates a simple patrol loop
            (MoveTo PatrolLocation → Wait 2s). Default: "BT_EnemyPatrol".
        mesh (str): Visual mesh asset path for the enemy. Default: "/Engine/BasicShapes/Cylinder.Cylinder".
        color_r (float): Enemy material red (0.0-1.0). Default: 1.0 (red).
        color_g (float): Enemy material green (0.0-1.0). Default: 0.1.
        color_b (float): Enemy material blue (0.0-1.0). Default: 0.1.
        move_speed (float): Maximum movement speed via set_movement_defaults.
            Default: 400.0.
        collision_radius (float): Sphere collision radius in cm. Default: 50.0.
        spawn_x (float): X position to spawn. All three (x, y, z) required. Default: None.
        spawn_y (float): Y position. Default: None.
        spawn_z (float): Z position. Default: None.

    Returns:
        {"summary": "AI enemy 'BP_Enemy' created with BT 'BT_EnemyPatrol'",
         "steps": [{"step": "pawn_blueprint", "status": "ok"},
                    {"step": "behavior_tree", "status": "ok"},
                    {"step": "ai_controller", "status": "ok"}, ...]}

    Example:
        create_ai_enemy("BP_Grunt", "BT_GruntPatrol",
                         "/Engine/BasicShapes/Cylinder.Cylinder",
                         1.0, 0.0, 0.0, 300.0, 40.0, 500, 0, 100)
        create_ai_enemy()  # red cylinder enemy with defaults

    Notes:
        - Uses the proven Pawn + FloatingPawnMovement pattern (not Character)
        - BT includes a Blackboard with PatrolLocation (Vector) key
        - AIController is auto-created with RunBehaviorTree wired to BeginPlay
        - For stationary or non-hostile NPCs, use create_ai_npc instead
        - For custom BehaviorTrees, create the BT separately with create_behavior_tree_from_dsl
          and pass its name as bt_name, or skip bt_name and use setup_ai_for_pawn later
        - BT/AI setup steps are fault-tolerant and report errors without aborting
    """
    def _run(client):
        steps = []
        # 1. Pawn BP
        dsl = f"""BLUEPRINT: {name}
PARENT: Pawn
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="{name} Active"]
EXEC n1.Then -> n2.Execute"""
        client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        client.send_command("add_component", {
            "blueprint": name, "component_type": "SphereCollision", "component_name": "EnemyCollision",
            "properties": {"radius": collision_radius, "generate_overlap_events": True}
        })
        client.send_command("add_component", {
            "blueprint": name, "component_type": "StaticMesh", "component_name": "EnemyMesh",
            "properties": {"mesh": mesh}
        })
        steps.append({"step": "pawn_blueprint", "status": "ok"})

        # 2. Material
        mat_name = f"MAT_{name}"
        client.send_command("create_simple_material", {
            "name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}
        })
        steps.append({"step": "material", "status": "ok"})

        # 3. BehaviorTree
        bt_dsl = f"""BEHAVIORTREE: {bt_name}
BLACKBOARD: BB_{name}

KEY PatrolLocation: Vector

TREE:

SEQUENCE: PatrolLoop
  TASK: MoveTo [Key=PatrolLocation, AcceptableRadius=50]
  TASK: Wait [Duration=2.0]"""
        try:
            from bt_parser import bt_parser
            ir = bt_parser.parse_bt_dsl(bt_dsl)
            import json as _json
            client.send_command("create_behavior_tree", {"ir_json": _json.dumps(ir)})
            steps.append({"step": "behavior_tree", "status": "ok"})
        except Exception as e:
            steps.append({"step": "behavior_tree", "status": "error", "error": str(e)})

        # 4. AI Controller
        try:
            client.send_command("setup_ai_for_pawn", {
                "pawn_name": name, "behavior_tree": bt_name
            })
            steps.append({"step": "ai_controller", "status": "ok"})
        except Exception as e:
            steps.append({"step": "ai_controller", "status": "error", "error": str(e)})

        # 5. Movement
        try:
            client.send_command("set_movement_defaults", {
                "blueprint": name, "max_speed": move_speed
            })
            steps.append({"step": "movement", "status": "ok"})
        except Exception:
            pass

        # 6. Spawn
        if spawn_x is not None and spawn_y is not None and spawn_z is not None:
            lbl = name.replace("BP_", "")
            client.send_command("spawn_actor_at", {
                "class": f"/Game/Arcwright/Generated/{name}.{name}",
                "label": lbl, "location": {"x": spawn_x, "y": spawn_y, "z": spawn_z}
            })
            client.send_command("set_actor_material", {
                "actor_label": lbl, "material_path": f"/Game/Arcwright/Materials/{mat_name}"
            })
            steps.append({"step": "spawn", "actor": lbl, "status": "ok"})

        return {"summary": f"AI enemy '{name}' created with BT '{bt_name}'", "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_ai_npc(name: str = "BP_NPC", bt_name: str = "BT_NPCPatrol",
                  mesh: str = "/Engine/BasicShapes/Cylinder.Cylinder",
                  color_r: float = 0.2, color_g: float = 0.5, color_b: float = 1.0,
                  stationary: bool = False, move_speed: float = 200.0,
                  spawn_x: float = None, spawn_y: float = None,
                  spawn_z: float = None) -> str:
    """Create a non-hostile NPC: Pawn Blueprint, patrol or idle BehaviorTree, AIController,
    material, and optional level spawn.

    Combines 5-7 TCP commands: create_blueprint_from_dsl (Pawn), add_component (SphereCollision
    + StaticMesh), create_simple_material, create_behavior_tree (patrol or idle), setup_ai_for_pawn,
    optionally spawn_actor_at + set_actor_material.

    Parameters:
        name (str): Pawn Blueprint name. Default: "BP_NPC".
        bt_name (str): Behavior Tree asset name. Creates either a patrol loop (MoveTo→Wait)
            or idle loop (Wait only) depending on the stationary flag. Default: "BT_NPCPatrol".
        mesh (str): Visual mesh asset path. Default: "/Engine/BasicShapes/Cylinder.Cylinder".
        color_r (float): NPC material red (0.0-1.0). Default: 0.2 (blue tint).
        color_g (float): NPC material green (0.0-1.0). Default: 0.5.
        color_b (float): NPC material blue (0.0-1.0). Default: 1.0.
        stationary (bool): If True, the NPC idles in place (Wait 5s loop, no movement).
            If False, patrols between waypoints (MoveTo PatrolLocation → Wait 3s).
            Default: False.
        move_speed (float): Movement speed if not stationary. Default: 200.0.
        spawn_x (float): X position to spawn. All three (x, y, z) required. Default: None.
        spawn_y (float): Y position. Default: None.
        spawn_z (float): Z position. Default: None.

    Returns:
        {"summary": "NPC 'BP_NPC' created",
         "steps": [{"step": "pawn_blueprint", "status": "ok"},
                    {"step": "behavior_tree", "status": "ok"},
                    {"step": "ai_controller", "status": "ok"}, ...]}

    Example:
        create_ai_npc("BP_Villager", "BT_VillagerPatrol",
                       "/Engine/BasicShapes/Cylinder.Cylinder",
                       0.2, 0.7, 0.3, False, 150.0, 300, 200, 50)
        create_ai_npc("BP_Shopkeeper", "BT_ShopIdle",
                       "/Engine/BasicShapes/Cylinder.Cylinder",
                       0.8, 0.6, 0.2, True)

    Notes:
        - Colored differently from enemies by default (blue vs red) for visual distinction
        - Uses the same Pawn + FloatingPawnMovement pattern as enemies
        - For hostile enemies with faster movement, use create_ai_enemy instead
        - BT/AI steps are fault-tolerant and won't abort the entire workflow on failure
        - Collision radius is fixed at 40 cm; modify via add_component after creation
    """
    def _run(client):
        steps = []
        dsl = f"""BLUEPRINT: {name}
PARENT: Pawn
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="{name} Ready"]
EXEC n1.Then -> n2.Execute"""
        client.send_command("create_blueprint_from_dsl", {"dsl": dsl})
        client.send_command("add_component", {
            "blueprint": name, "component_type": "SphereCollision", "component_name": "NPCCollision",
            "properties": {"radius": 40, "generate_overlap_events": True}
        })
        client.send_command("add_component", {
            "blueprint": name, "component_type": "StaticMesh", "component_name": "NPCMesh",
            "properties": {"mesh": mesh}
        })
        steps.append({"step": "pawn_blueprint", "status": "ok"})

        mat_name = f"MAT_{name}"
        client.send_command("create_simple_material", {
            "name": mat_name, "color": {"r": color_r, "g": color_g, "b": color_b}
        })

        if stationary:
            bt_dsl = f"""BEHAVIORTREE: {bt_name}
BLACKBOARD: BB_{name}

TREE:

SEQUENCE: Idle
  TASK: Wait [Duration=5.0]"""
        else:
            bt_dsl = f"""BEHAVIORTREE: {bt_name}
BLACKBOARD: BB_{name}

KEY PatrolLocation: Vector

TREE:

SEQUENCE: PatrolLoop
  TASK: MoveTo [Key=PatrolLocation, AcceptableRadius=50]
  TASK: Wait [Duration=3.0]"""

        try:
            from bt_parser import bt_parser
            ir = bt_parser.parse_bt_dsl(bt_dsl)
            import json as _json
            client.send_command("create_behavior_tree", {"ir_json": _json.dumps(ir)})
            steps.append({"step": "behavior_tree", "status": "ok"})
        except Exception as e:
            steps.append({"step": "behavior_tree", "status": "error", "error": str(e)})

        try:
            client.send_command("setup_ai_for_pawn", {
                "pawn_name": name, "behavior_tree": bt_name
            })
            steps.append({"step": "ai_controller", "status": "ok"})
        except Exception as e:
            steps.append({"step": "ai_controller", "status": "error", "error": str(e)})

        if spawn_x is not None and spawn_y is not None and spawn_z is not None:
            lbl = name.replace("BP_", "")
            client.send_command("spawn_actor_at", {
                "class": f"/Game/Arcwright/Generated/{name}.{name}",
                "label": lbl, "location": {"x": spawn_x, "y": spawn_y, "z": spawn_z}
            })
            client.send_command("set_actor_material", {
                "actor_label": lbl, "material_path": f"/Game/Arcwright/Materials/{mat_name}"
            })
            steps.append({"step": "spawn", "actor": lbl, "status": "ok"})

        return {"summary": f"NPC '{name}' created", "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_patrol_path(name: str = "BP_PatrolPath", points: str = "",
                       closed: bool = True, show_markers: bool = False,
                       marker_scale: float = 0.2,
                       marker_color_r: float = 1.0, marker_color_g: float = 1.0,
                       marker_color_b: float = 0.0) -> str:
    """Create a spline-based patrol path with waypoints and optional visual markers.

    Combines 2-N TCP commands: create_spline_actor + add_spline_point (per extra point),
    optionally create_simple_material + spawn_actor_at (per marker) + set_actor_material,
    and get_spline_info for the final spline data.

    Parameters:
        name (str): Spline Blueprint name. Default: "BP_PatrolPath".
        points (str): JSON array of waypoint positions. Minimum 2 points required.
            Example: '[{"x":0,"y":0,"z":50},{"x":500,"y":0,"z":50},{"x":500,"y":500,"z":50}]'.
            Required (empty string returns an error).
        closed (bool): Whether the spline loops back to the first point. Default: True.
        show_markers (bool): Spawn small glowing spheres at each waypoint for visual debugging.
            Default: False.
        marker_scale (float): Uniform scale for marker spheres. Default: 0.2.
        marker_color_r (float): Marker material red (0.0-1.0). Default: 1.0 (yellow).
        marker_color_g (float): Marker material green (0.0-1.0). Default: 1.0.
        marker_color_b (float): Marker material blue (0.0-1.0). Default: 0.0.

    Returns:
        {"summary": "Patrol path 'BP_PatrolPath' with 4 points",
         "spline_info": {"point_count": 4, "spline_length": 1500.0, "closed": true, ...},
         "steps": [{"step": "spline", "status": "ok"}, ...]}

    Example:
        create_patrol_path("BP_EnemyRoute",
            '[{"x":0,"y":0,"z":50},{"x":500,"y":0,"z":50},{"x":500,"y":500,"z":50},{"x":0,"y":500,"z":50}]',
            True, True, 0.3, 1.0, 0.0, 0.0)
        create_patrol_path("BP_CameraPath",
            '[{"x":0,"y":-800,"z":200},{"x":1000,"y":-800,"z":300}]', False)

    Notes:
        - Markers are labeled {name}_Marker_{index} and use emissive material for visibility
        - For general-purpose splines (not patrol-specific), use create_spline_path
        - To wire this path to an AI pawn, set a Blackboard key to spline point locations
          in the BehaviorTree, or use direct MoveToLocation with path points
        - Returns spline info including total length, useful for timing patrol loops
    """
    def _run(client):
        steps = []
        pts = _parse_json_param(points, "points")
        if len(pts) < 2:
            return {"error": "Need at least 2 points for a patrol path"}

        client.send_command("create_spline_actor", {
            "name": name, "initial_points": pts[:2], "closed": closed
        })
        steps.append({"step": "spline", "status": "ok"})

        for pt in pts[2:]:
            client.send_command("add_spline_point", {
                "blueprint": name, "point": pt
            })

        if show_markers:
            mat_name = f"MAT_{name}_Marker"
            client.send_command("create_simple_material", {
                "name": mat_name,
                "color": {"r": marker_color_r, "g": marker_color_g, "b": marker_color_b},
                "emissive": 1.0
            })
            for i, pt in enumerate(pts):
                lbl = f"{name}_Marker_{i}"
                client.send_command("spawn_actor_at", {
                    "class": "StaticMeshActor", "label": lbl,
                    "location": pt,
                    "properties": {"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                                   "scale": {"x": marker_scale, "y": marker_scale, "z": marker_scale}}
                })
                client.send_command("set_actor_material", {
                    "actor_label": lbl,
                    "material_path": f"/Game/Arcwright/Materials/{mat_name}"
                })
            steps.append({"step": "markers", "count": len(pts), "status": "ok"})

        info = client.send_command("get_spline_info", {"blueprint": name})
        return {"summary": f"Patrol path '{name}' with {len(pts)} points",
                "spline_info": info.get("data", {}), "steps": steps}
    return _compound_call(_run)

# -- Category 8: UI Presets --

@mcp.tool()
def create_game_hud(name: str = "WBP_GameHUD", show_health_bar: bool = True,
                    show_score: bool = True, show_wave: bool = False,
                    show_ammo: bool = False, show_crosshair: bool = False,
                    primary_color_r: float = 0.2, primary_color_g: float = 0.8,
                    primary_color_b: float = 1.0) -> str:
    """Create a complete game HUD Widget Blueprint with selectable elements: health bar, score,
    wave counter, ammo display, and crosshair at standard screen positions.

    Combines 5-20+ TCP commands: create_widget_blueprint, add_widget_child (CanvasPanel root
    + each element), and set_widget_property (text, color, position, size, percent per element).
    Positions assume 1920x1080 resolution.

    Parameters:
        name (str): Widget Blueprint name. Created at /Game/UI/. Default: "WBP_GameHUD".
        show_health_bar (bool): Include a green ProgressBar at top-left (20, 20), 300x25.
            Widget name: "HealthBar". Default: True.
        show_score (bool): Include score TextBlock at top-right (1600, 20), font size 24.
            Widget name: "ScoreText". Default: True.
        show_wave (bool): Include wave counter TextBlock at top-center (860, 20), font size 28.
            Widget name: "WaveText". Default: False.
        show_ammo (bool): Include ammo TextBlock at bottom-right (1650, 980), font size 20.
            Widget name: "AmmoText". Default: False.
        show_crosshair (bool): Include "+" TextBlock at screen center (948, 528), font size 24.
            Widget name: "Crosshair". Default: False.
        primary_color_r (float): Accent color red for score and wave text (0.0-1.0).
            Default: 0.2.
        primary_color_g (float): Accent color green (0.0-1.0). Default: 0.8.
        primary_color_b (float): Accent color blue (0.0-1.0). Default: 1.0.

    Returns:
        {"summary": "HUD 'WBP_GameHUD' created with 3 elements",
         "widget": "WBP_GameHUD",
         "elements": ["HealthBar", "ScoreText", "Crosshair"],
         "steps": [...]}

    Example:
        create_game_hud("WBP_GameHUD", True, True, True, True, True, 0.2, 0.8, 1.0)
        create_game_hud("WBP_MinimalHUD", True, True, False, False, False)

    Notes:
        - All widgets are children of a "RootCanvas" CanvasPanel
        - HealthBar starts at 100% (percent=1.0) with green fill color
        - Score text starts at "Score: 0"; update via Blueprint event bindings
        - Crosshair is a simple "+" text; for image crosshairs, modify with set_widget_property
        - For more complex HUD layouts, use create_widget_from_html with an HTML mockup
        - For menu screens, use create_menu_widget; for dialog boxes, use create_dialog_widget
    """
    def _run(client):
        steps = []
        client.send_command("create_widget_blueprint", {"name": name})
        client.send_command("add_widget_child", {
            "widget_blueprint": name, "widget_type": "CanvasPanel", "widget_name": "RootCanvas"
        })
        steps.append({"step": "widget_blueprint", "status": "ok"})
        color_str = f"{primary_color_r},{primary_color_g},{primary_color_b},1.0"

        widgets_added = []
        if show_health_bar:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "RootCanvas",
                "widget_type": "ProgressBar", "widget_name": "HealthBar"
            })
            for prop, val in [("percent", "1.0"), ("position", "20,20"),
                              ("size", "300,25"), ("fill_color", "0.1,0.8,0.2,1.0")]:
                client.send_command("set_widget_property", {
                    "widget_blueprint": name, "widget_name": "HealthBar",
                    "property": prop, "value": val
                })
            widgets_added.append("HealthBar")

        if show_score:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "RootCanvas",
                "widget_type": "TextBlock", "widget_name": "ScoreText"
            })
            for prop, val in [("text", "Score: 0"), ("position", "1600,20"),
                              ("font_size", "24"), ("color", color_str)]:
                client.send_command("set_widget_property", {
                    "widget_blueprint": name, "widget_name": "ScoreText",
                    "property": prop, "value": val
                })
            widgets_added.append("ScoreText")

        if show_wave:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "RootCanvas",
                "widget_type": "TextBlock", "widget_name": "WaveText"
            })
            for prop, val in [("text", "Wave 1"), ("position", "860,20"),
                              ("font_size", "28"), ("color", color_str)]:
                client.send_command("set_widget_property", {
                    "widget_blueprint": name, "widget_name": "WaveText",
                    "property": prop, "value": val
                })
            widgets_added.append("WaveText")

        if show_ammo:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "RootCanvas",
                "widget_type": "TextBlock", "widget_name": "AmmoText"
            })
            for prop, val in [("text", "30 / 90"), ("position", "1650,980"),
                              ("font_size", "20"), ("color", "1.0,1.0,1.0,1.0")]:
                client.send_command("set_widget_property", {
                    "widget_blueprint": name, "widget_name": "AmmoText",
                    "property": prop, "value": val
                })
            widgets_added.append("AmmoText")

        if show_crosshair:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "RootCanvas",
                "widget_type": "TextBlock", "widget_name": "Crosshair"
            })
            for prop, val in [("text", "+"), ("position", "948,528"),
                              ("font_size", "24"), ("color", "1.0,1.0,1.0,0.8")]:
                client.send_command("set_widget_property", {
                    "widget_blueprint": name, "widget_name": "Crosshair",
                    "property": prop, "value": val
                })
            widgets_added.append("Crosshair")

        steps.append({"step": "widgets", "added": widgets_added})
        return {"summary": f"HUD '{name}' created with {len(widgets_added)} elements",
                "widget": name, "elements": widgets_added, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_menu_widget(name: str = "WBP_Menu", title: str = "Game Title",
                       subtitle: str = "", buttons: str = "Start Game,Options,Quit",
                       title_font_size: int = 48,
                       title_color_r: float = 1.0, title_color_g: float = 1.0,
                       title_color_b: float = 1.0) -> str:
    """Create a menu screen Widget Blueprint: title, optional subtitle, and vertically stacked
    buttons. Suitable for main menus, pause screens, or game over screens.

    Combines 10-20+ TCP commands: create_widget_blueprint, add_widget_child (CanvasPanel +
    VerticalBox + title TextBlock + subtitle TextBlock + Button + child TextBlock per button),
    and set_widget_property (text, font_size, color, position, size).

    Parameters:
        name (str): Widget Blueprint name. Default: "WBP_Menu".
        title (str): Main title text displayed at the top. Default: "Game Title".
        subtitle (str): Subtitle text below the title. Empty = no subtitle. Default: "".
        buttons (str): Comma-separated button label text. Each creates a Button widget with
            a TextBlock child. Default: "Start Game,Options,Quit".
        title_font_size (int): Font size for the title text. Default: 48.
        title_color_r (float): Title color red (0.0-1.0). Default: 1.0 (white).
        title_color_g (float): Title color green (0.0-1.0). Default: 1.0.
        title_color_b (float): Title color blue (0.0-1.0). Default: 1.0.

    Returns:
        {"summary": "Menu 'WBP_Menu' with 3 buttons",
         "widget": "WBP_Menu",
         "steps": [{"step": "menu", "buttons": ["Start Game", "Options", "Quit"], "status": "ok"}]}

    Example:
        create_menu_widget("WBP_MainMenu", "My Game", "An Epic Adventure",
                           "New Game,Continue,Settings,Quit", 56, 1.0, 0.8, 0.2)
        create_menu_widget("WBP_PauseMenu", "PAUSED", "", "Resume,Settings,Quit to Menu")
        create_menu_widget("WBP_GameOver", "GAME OVER", "Better luck next time", "Retry,Main Menu")

    Notes:
        - Layout uses a VerticalBox ("MenuLayout") positioned at (660, 200), 600x700
        - Buttons are named "Btn_{label}" (spaces removed); text inside named "BtnText_{index}"
        - Subtitle font is fixed at size 20; button text at size 22
        - No click handlers are wired; connect button OnClicked events in Blueprint editor
        - For in-game HUDs, use create_game_hud; for dialog boxes, use create_dialog_widget
    """
    def _run(client):
        steps = []
        client.send_command("create_widget_blueprint", {"name": name})
        client.send_command("add_widget_child", {
            "widget_blueprint": name, "widget_type": "CanvasPanel", "widget_name": "Root"
        })
        client.send_command("add_widget_child", {
            "widget_blueprint": name, "parent": "Root",
            "widget_type": "VerticalBox", "widget_name": "MenuLayout"
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "MenuLayout",
            "property": "position", "value": "660,200"
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "MenuLayout",
            "property": "size", "value": "600,700"
        })

        # Title
        color_str = f"{title_color_r},{title_color_g},{title_color_b},1.0"
        client.send_command("add_widget_child", {
            "widget_blueprint": name, "parent": "MenuLayout",
            "widget_type": "TextBlock", "widget_name": "TitleText"
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "TitleText",
            "property": "text", "value": title
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "TitleText",
            "property": "font_size", "value": str(title_font_size)
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "TitleText",
            "property": "color", "value": color_str
        })

        if subtitle:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "MenuLayout",
                "widget_type": "TextBlock", "widget_name": "SubtitleText"
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": "SubtitleText",
                "property": "text", "value": subtitle
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": "SubtitleText",
                "property": "font_size", "value": "20"
            })

        # Buttons
        btn_list = [b.strip() for b in buttons.split(",") if b.strip()]
        for i, btn in enumerate(btn_list):
            w_name = f"Btn_{btn.replace(' ', '')}"
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "MenuLayout",
                "widget_type": "Button", "widget_name": w_name
            })
            txt_name = f"BtnText_{i}"
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": w_name,
                "widget_type": "TextBlock", "widget_name": txt_name
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": txt_name,
                "property": "text", "value": btn
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": txt_name,
                "property": "font_size", "value": "22"
            })

        steps.append({"step": "menu", "buttons": btn_list, "status": "ok"})
        return {"summary": f"Menu '{name}' with {len(btn_list)} buttons",
                "widget": name, "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_dialog_widget(name: str = "WBP_Dialog", speaker_name: str = "",
                         body_text: str = "Hello, adventurer!",
                         show_dismiss_button: bool = True,
                         dismiss_text: str = "Continue",
                         position: str = "bottom",
                         width: float = 600.0, height: float = 200.0) -> str:
    """Create a dialog/notification Widget Blueprint with speaker name, body text, and
    optional dismiss button. Useful for NPC dialog, tutorial popups, or in-game notifications.

    Combines 8-14 TCP commands: create_widget_blueprint, add_widget_child (CanvasPanel +
    VerticalBox + optional speaker TextBlock + body TextBlock + optional Button + ButtonText),
    and set_widget_property (text, font_size, color, position, size).

    Parameters:
        name (str): Widget Blueprint name. Default: "WBP_Dialog".
        speaker_name (str): Speaker label displayed above the body text in cyan.
            Empty = no speaker line. Default: "".
        body_text (str): Main dialog body text. Default: "Hello, adventurer!".
        show_dismiss_button (bool): Show a "Continue" dismiss button below the text.
            Default: True.
        dismiss_text (str): Label text for the dismiss button. Default: "Continue".
        position (str): Vertical position of the dialog box on screen.
            Valid values: "top" (y=50), "center" (y=390), "bottom" (y=780).
            Default: "bottom".
        width (float): Dialog box width in pixels. Centered horizontally. Default: 600.0.
        height (float): Dialog box height in pixels. Default: 200.0.

    Returns:
        {"summary": "Dialog widget 'WBP_Dialog' created", "widget": "WBP_Dialog",
         "steps": [{"step": "dialog", "position": "bottom", "status": "ok"}]}

    Example:
        create_dialog_widget("WBP_NPCDialog", "Old Wizard",
                              "The dungeon lies beneath the castle...", True, "Continue",
                              "bottom", 700, 250)
        create_dialog_widget("WBP_Tutorial", "",
                              "Press WASD to move. Press Space to jump.", True, "Got it!",
                              "top", 800, 150)
        create_dialog_widget("WBP_Notification", "", "Achievement Unlocked!", False,
                              "", "top", 400, 80)

    Notes:
        - Speaker name is displayed in cyan (0.3, 0.8, 1.0) with font size 20
        - Body text uses font size 16
        - Dialog is horizontally centered at any resolution assuming 1920 width
        - Button named "DismissBtn" with child "DismissBtnText" (font size 18)
        - No click handler is wired; connect DismissBtn OnClicked in Blueprint editor
        - For full menu screens with multiple buttons, use create_menu_widget
    """
    def _run(client):
        steps = []
        client.send_command("create_widget_blueprint", {"name": name})
        client.send_command("add_widget_child", {
            "widget_blueprint": name, "widget_type": "CanvasPanel", "widget_name": "Root"
        })

        pos_y = {"top": 50, "center": 390, "bottom": 780}.get(position, 780)
        pos_x = int((1920 - width) / 2)

        client.send_command("add_widget_child", {
            "widget_blueprint": name, "parent": "Root",
            "widget_type": "VerticalBox", "widget_name": "DialogBox"
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "DialogBox",
            "property": "position", "value": f"{pos_x},{pos_y}"
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "DialogBox",
            "property": "size", "value": f"{int(width)},{int(height)}"
        })

        if speaker_name:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "DialogBox",
                "widget_type": "TextBlock", "widget_name": "SpeakerName"
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": "SpeakerName",
                "property": "text", "value": speaker_name
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": "SpeakerName",
                "property": "font_size", "value": "20"
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": "SpeakerName",
                "property": "color", "value": "0.3,0.8,1.0,1.0"
            })

        client.send_command("add_widget_child", {
            "widget_blueprint": name, "parent": "DialogBox",
            "widget_type": "TextBlock", "widget_name": "BodyText"
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "BodyText",
            "property": "text", "value": body_text
        })
        client.send_command("set_widget_property", {
            "widget_blueprint": name, "widget_name": "BodyText",
            "property": "font_size", "value": "16"
        })

        if show_dismiss_button:
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "DialogBox",
                "widget_type": "Button", "widget_name": "DismissBtn"
            })
            client.send_command("add_widget_child", {
                "widget_blueprint": name, "parent": "DismissBtn",
                "widget_type": "TextBlock", "widget_name": "DismissBtnText"
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": "DismissBtnText",
                "property": "text", "value": dismiss_text
            })
            client.send_command("set_widget_property", {
                "widget_blueprint": name, "widget_name": "DismissBtnText",
                "property": "font_size", "value": "18"
            })

        steps.append({"step": "dialog", "position": position, "status": "ok"})
        return {"summary": f"Dialog widget '{name}' created", "widget": name, "steps": steps}
    return _compound_call(_run)

# -- Category 9: Physics & Environment --

@mcp.tool()
def create_physics_playground(gravity: float = -980.0, object_count: int = 5,
                              object_type: str = "cube", object_scale: float = 0.5,
                              spawn_height: float = 500.0, floor_size: float = 50.0,
                              object_color_r: float = 0.3, object_color_g: float = 0.6,
                              object_color_b: float = 1.0) -> str:
    """Set up a physics test environment: floor, configurable gravity, colored physics objects
    spawned in a circle at a drop height.

    Combines 5+ TCP commands: setup_scene_lighting, spawn_actor_at (floor), set_world_settings
    (gravity), create_simple_material, spawn_actor_at (per object) + set_actor_material,
    and save_all.

    Parameters:
        gravity (float): World gravity in cm/s^2 (negative = downward).
            -980 = Earth gravity, -490 = moon, -1960 = heavy, 0 = zero-G.
            Default: -980.0.
        object_count (int): Number of physics objects to spawn. Default: 5.
        object_type (str): Shape of each physics object.
            Valid values: "cube", "sphere", "cylinder". Default: "cube".
        object_scale (float): Uniform scale for objects. Default: 0.5.
        spawn_height (float): Height in cm to spawn objects (they drop from here).
            Default: 500.0.
        floor_size (float): Floor plane scale multiplier. Default: 50.0.
        object_color_r (float): Object material red (0.0-1.0). Default: 0.3.
        object_color_g (float): Object material green (0.0-1.0). Default: 0.6.
        object_color_b (float): Object material blue (0.0-1.0). Default: 1.0.

    Returns:
        {"summary": "Physics playground: 5 cubes, gravity=-980",
         "objects": ["PhysObj_0", "PhysObj_1", ...],
         "steps": [{"step": "floor", "status": "ok"}, {"step": "gravity", "value": -980.0}, ...]}

    Example:
        create_physics_playground(-490, 10, "sphere", 0.3, 800, 50, 0.8, 0.2, 0.2)
        create_physics_playground(0, 20, "cube", 0.2, 300, 30, 0.3, 0.6, 1.0)  # zero-G

    Notes:
        - Objects are arranged in a circle of radius 200 cm at the spawn height
        - Material created at /Game/Arcwright/Materials/MAT_PhysObj
        - Physics simulation must be enabled on each object separately (use set_physics_enabled
          after spawn, or enable via PIE play mode)
        - Uses "indoor_bright" lighting preset
        - Floor labeled "PhysFloor"; objects labeled "PhysObj_{index}"
        - Auto-saves after setup
    """
    def _run(client):
        steps = []
        # Floor
        client.send_command("setup_scene_lighting", {"preset": "indoor_bright"})
        client.send_command("spawn_actor_at", {
            "class": "StaticMeshActor", "label": "PhysFloor",
            "location": {"x": 0, "y": 0, "z": 0},
            "properties": {"mesh": "/Engine/BasicShapes/Plane.Plane",
                           "scale": {"x": floor_size, "y": floor_size, "z": 1}}
        })
        steps.append({"step": "floor", "status": "ok"})

        # Gravity
        client.send_command("set_world_settings", {"gravity": gravity})
        steps.append({"step": "gravity", "value": gravity})

        # Material
        client.send_command("create_simple_material", {
            "name": "MAT_PhysObj",
            "color": {"r": object_color_r, "g": object_color_g, "b": object_color_b}
        })

        # Objects
        mesh_map = {
            "cube": "/Engine/BasicShapes/Cube.Cube",
            "sphere": "/Engine/BasicShapes/Sphere.Sphere",
            "cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
        }
        mesh = mesh_map.get(object_type, mesh_map["cube"])
        spawned = []
        import math
        for i in range(object_count):
            angle = (2 * math.pi * i) / max(object_count, 1)
            x = 200 * math.cos(angle)
            y = 200 * math.sin(angle)
            lbl = f"PhysObj_{i}"
            client.send_command("spawn_actor_at", {
                "class": "StaticMeshActor", "label": lbl,
                "location": {"x": x, "y": y, "z": spawn_height},
                "properties": {"mesh": mesh,
                               "scale": {"x": object_scale, "y": object_scale, "z": object_scale}}
            })
            try:
                client.send_command("set_actor_material", {
                    "actor_label": lbl, "material_path": "/Game/Arcwright/Materials/MAT_PhysObj"
                })
            except Exception:
                pass
            spawned.append(lbl)

        steps.append({"step": "objects", "count": len(spawned)})
        client.send_command("save_all", {})
        return {"summary": f"Physics playground: {object_count} {object_type}s, gravity={gravity}",
                "objects": spawned, "steps": steps}
    return _compound_call(_run)

_ENV_PRESETS = {
    "underwater": {"bloom_intensity": 0.8, "vignette_intensity": 0.6,
                   "color_saturation": 0.7, "scene_tint": {"r": 0.3, "g": 0.6, "b": 1.0}},
    "toxic": {"bloom_intensity": 0.4, "vignette_intensity": 0.5,
              "color_saturation": 1.3, "scene_tint": {"r": 0.5, "g": 1.0, "b": 0.2}},
    "dark_dungeon": {"bloom_intensity": 0.1, "vignette_intensity": 0.8,
                     "color_saturation": 0.5, "scene_tint": {"r": 0.5, "g": 0.4, "b": 0.6}},
    "dream": {"bloom_intensity": 1.5, "vignette_intensity": 0.3,
              "color_saturation": 0.6, "scene_tint": {"r": 0.9, "g": 0.7, "b": 1.0}},
}

@mcp.tool()
def create_environment_zone(label: str = "EnvZone",
                            x: float = 0.0, y: float = 0.0, z: float = 0.0,
                            preset: str = "custom", infinite: bool = False,
                            bloom_intensity: float = -1.0, vignette_intensity: float = -1.0,
                            color_saturation: float = -1.0,
                            color_tint_r: float = -1.0, color_tint_g: float = -1.0,
                            color_tint_b: float = -1.0) -> str:
    """Create a post-process volume defining a visual environment zone with preset or custom
    atmosphere settings. Use for underwater, toxic, dungeon, or dream areas.

    Combines 2 TCP commands: add_post_process_volume and set_post_process_settings.
    Preset values can be individually overridden.

    Parameters:
        label (str): Volume actor label. Default: "EnvZone".
        x (float): Volume X position in cm. Default: 0.0.
        y (float): Volume Y position in cm. Default: 0.0.
        z (float): Volume Z position in cm. Default: 0.0.
        preset (str): Visual atmosphere preset. Overrides can be applied on top.
            Valid values: "underwater" (blue tint, high bloom), "toxic" (green tint, high saturation),
            "dark_dungeon" (purple tint, heavy vignette, low saturation), "dream" (pink tint,
            extreme bloom, low saturation), "custom" (no preset, only overrides).
            Default: "custom".
        infinite (bool): If True, volume covers entire level. If False, bounded area only.
            Default: False.
        bloom_intensity (float): Override bloom intensity (0.0-5.0). If < 0, uses preset value.
            Default: -1.0.
        vignette_intensity (float): Override vignette (0.0-1.0). If < 0, uses preset value.
            Default: -1.0.
        color_saturation (float): Override color saturation (0.0 = grayscale, 1.0 = normal,
            >1.0 = oversaturated). If < 0, uses preset value. Default: -1.0.
        color_tint_r (float): Scene color tint red override. All three (r, g, b) must be >= 0
            to apply tint. Default: -1.0.
        color_tint_g (float): Scene color tint green override. Default: -1.0.
        color_tint_b (float): Scene color tint blue override. Default: -1.0.

    Returns:
        {"summary": "Environment zone 'EnvZone' (underwater)",
         "steps": [{"step": "volume", "status": "ok"},
                    {"step": "settings", "applied": ["bloom_intensity", "vignette_intensity", ...]}]}

    Example:
        create_environment_zone("UnderwaterZone", 0, 0, -200, "underwater", False)
        create_environment_zone("ToxicSwamp", 1000, 500, 0, "toxic", False)
        create_environment_zone("GlobalDream", 0, 0, 0, "dream", True)
        create_environment_zone("CustomZone", 0, 0, 0, "custom", False,
                                0.3, 0.7, 0.5, 0.8, 0.4, 0.6)

    Notes:
        - Presets: underwater (bloom=0.8, vignette=0.6, saturation=0.7, blue tint),
          toxic (bloom=0.4, vignette=0.5, saturation=1.3, green tint),
          dark_dungeon (bloom=0.1, vignette=0.8, saturation=0.5, purple tint),
          dream (bloom=1.5, vignette=0.3, saturation=0.6, pink tint)
        - Individual parameter overrides (>= 0) take precedence over preset values
        - For full post-process control, use add_post_process_volume + set_post_process_settings
        - Multiple zones can overlap; UE blends their settings based on volume priority
    """
    def _run(client):
        steps = []
        client.send_command("add_post_process_volume", {
            "label": label, "location": {"x": x, "y": y, "z": z},
            "infinite_extent": infinite
        })
        steps.append({"step": "volume", "status": "ok"})

        # Start with preset settings
        settings = {}
        if preset in _ENV_PRESETS:
            settings = dict(_ENV_PRESETS[preset])
            tint = settings.pop("scene_tint", None)
            if tint:
                settings["scene_color_tint"] = tint

        # Apply overrides
        if bloom_intensity >= 0:
            settings["bloom_intensity"] = bloom_intensity
        if vignette_intensity >= 0:
            settings["vignette_intensity"] = vignette_intensity
        if color_saturation >= 0:
            settings["color_saturation"] = color_saturation
        if color_tint_r >= 0 and color_tint_g >= 0 and color_tint_b >= 0:
            settings["scene_color_tint"] = {"r": color_tint_r, "g": color_tint_g, "b": color_tint_b}

        if settings:
            client.send_command("set_post_process_settings", {"label": label, **settings})
            steps.append({"step": "settings", "applied": list(settings.keys())})

        return {"summary": f"Environment zone '{label}' ({preset})", "steps": steps}
    return _compound_call(_run)

@mcp.tool()
def create_spline_path(name: str = "BP_SplinePath", points: str = "",
                       closed: bool = False, show_markers: bool = False,
                       marker_scale: float = 0.2,
                       marker_color_r: float = 1.0, marker_color_g: float = 1.0,
                       marker_color_b: float = 0.0) -> str:
    """Create a general-purpose spline path with multiple waypoints. Useful for camera paths,
    moving platform tracks, or any path-following behavior. Optionally spawns marker spheres
    at each waypoint for visual debugging.

    Combines 2-N TCP commands: create_spline_actor + add_spline_point (per extra point beyond
    the first two), optionally create_simple_material + spawn_actor_at (per marker) +
    set_actor_material, and get_spline_info for final path data.

    Parameters:
        name (str): Spline Blueprint name. Default: "BP_SplinePath".
        points (str): JSON array of waypoint positions. Minimum 2 points required.
            Example: '[{"x":0,"y":0,"z":50},{"x":500,"y":0,"z":50},{"x":500,"y":500,"z":100}]'.
            Required (empty string returns an error).
        closed (bool): Whether the spline loops back to the first point. Default: False.
        show_markers (bool): Spawn small glowing spheres at each waypoint for visual debugging.
            Default: False.
        marker_scale (float): Uniform scale for marker spheres. Default: 0.2.
        marker_color_r (float): Marker material red (0.0-1.0). Default: 1.0 (yellow).
        marker_color_g (float): Marker material green (0.0-1.0). Default: 1.0.
        marker_color_b (float): Marker material blue (0.0-1.0). Default: 0.0.

    Returns:
        {"summary": "Spline path 'BP_SplinePath' with 3 points",
         "spline_info": {"point_count": 3, "spline_length": 707.1, "closed": false, ...},
         "steps": [{"step": "spline", "point_count": 3, "status": "ok"}, ...]}

    Example:
        create_spline_path("BP_CameraRail",
            '[{"x":0,"y":-500,"z":200},{"x":1000,"y":-500,"z":300},{"x":2000,"y":0,"z":400}]',
            False, True, 0.3, 0.0, 1.0, 0.0)
        create_spline_path("BP_PlatformTrack",
            '[{"x":0,"y":0,"z":100},{"x":0,"y":500,"z":100}]', True)

    Notes:
        - Markers are labeled {name}_Pt_{index} with emissive material for visibility
        - For AI patrol paths specifically, use create_patrol_path (same functionality,
          different semantic naming and closed=True default)
        - Returns spline length, useful for timing movement along the path
        - Spline Blueprint is created at /Game/Arcwright/Generated/
        - Marker material at /Game/Arcwright/Materials/MAT_{name}_Marker
    """
    def _run(client):
        steps = []
        pts = _parse_json_param(points, "points")
        if len(pts) < 2:
            return {"error": "Need at least 2 points for a spline path"}

        client.send_command("create_spline_actor", {
            "name": name, "initial_points": pts[:2], "closed": closed
        })
        for pt in pts[2:]:
            client.send_command("add_spline_point", {"blueprint": name, "point": pt})
        steps.append({"step": "spline", "point_count": len(pts), "status": "ok"})

        if show_markers:
            mat_name = f"MAT_{name}_Marker"
            client.send_command("create_simple_material", {
                "name": mat_name,
                "color": {"r": marker_color_r, "g": marker_color_g, "b": marker_color_b},
                "emissive": 1.0
            })
            for i, pt in enumerate(pts):
                lbl = f"{name}_Pt_{i}"
                client.send_command("spawn_actor_at", {
                    "class": "StaticMeshActor", "label": lbl,
                    "location": pt,
                    "properties": {"mesh": "/Engine/BasicShapes/Sphere.Sphere",
                                   "scale": {"x": marker_scale, "y": marker_scale, "z": marker_scale}}
                })
                client.send_command("set_actor_material", {
                    "actor_label": lbl,
                    "material_path": f"/Game/Arcwright/Materials/{mat_name}"
                })
            steps.append({"step": "markers", "count": len(pts), "status": "ok"})

        info = client.send_command("get_spline_info", {"blueprint": name})
        return {"summary": f"Spline path '{name}' with {len(pts)} points",
                "spline_info": info.get("data", {}), "steps": steps}
    return _compound_call(_run)

# ---------------------------------------------------------------------------
# Live Preview
# ---------------------------------------------------------------------------

@mcp.tool()
def take_viewport_screenshot(path: str = "", width: int = 1920, height: int = 1080) -> str:
    """Capture the current UE viewport as a PNG image so the AI can see what was built.

    Takes a screenshot of the active level editor viewport and saves it to disk.
    The AI can then read the returned file path to visually inspect the scene.

    Parameters:
        path (str): Output file path. Defaults to a temp file (arcwright_preview.png).
            If provided, must end in .png. Parent directory is auto-created.
        width (int): Desired width in pixels (currently uses viewport's native size).
        height (int): Desired height in pixels (currently uses viewport's native size).

    Returns:
        {"status": "ok", "path": "/tmp/arcwright_preview.png", "width": 1920,
         "height": 1080, "size_bytes": 245000}

    Example:
        take_viewport_screenshot()
        take_viewport_screenshot(path="C:/screenshots/my_level.png")

    Notes:
        - Uses FScreenshotRequest which hooks into UE's render pipeline
        - Falls back to ReadPixels if FScreenshotRequest fails
        - The viewport must be visible (non-zero size) for capture to work
        - Free tier command — no Pro license required
    """
    params = {}
    if path:
        params["path"] = path
    return _safe_call(lambda c: c.send_command("take_viewport_screenshot", params))

# ---------------------------------------------------------------------------
# Undo / Redo
# ---------------------------------------------------------------------------

@mcp.tool()
def undo(count: int = 1) -> str:
    """Undo the last N editor operations.

    Wraps UE's built-in transaction/undo system. Each undone operation is
    reported with its description so the AI knows what was reversed.

    Parameters:
        count (int): Number of operations to undo. Default 1, max 50.

    Returns:
        {"status": "ok", "undone_count": 1, "requested": 1,
         "undone": [{"index": 0, "description": "Move Actors"}],
         "can_undo_more": true}

    Example:
        undo()          # Undo last operation
        undo(count=5)   # Undo last 5 operations

    Notes:
        - Stops early if the undo stack is exhausted
        - Use get_undo_history to see what can be undone before calling
        - Free tier command
    """
    return _safe_call(lambda c: c.send_command("undo", {"count": count}))

@mcp.tool()
def redo(count: int = 1) -> str:
    """Redo the last N undone editor operations.

    Re-applies operations that were previously undone. Each redone operation
    is reported with its description.

    Parameters:
        count (int): Number of operations to redo. Default 1, max 50.

    Returns:
        {"status": "ok", "redone_count": 1, "requested": 1,
         "redone": [{"index": 0, "description": "Move Actors"}],
         "can_redo_more": true}

    Example:
        redo()          # Redo last undone operation
        redo(count=3)   # Redo last 3

    Notes:
        - The redo stack is cleared when new operations are performed
        - Free tier command
    """
    return _safe_call(lambda c: c.send_command("redo", {"count": count}))

@mcp.tool()
def get_undo_history(max_entries: int = 20) -> str:
    """Get the recent undo history with operation descriptions.

    Returns the last N entries from the editor's undo buffer. Use this to
    inspect what operations can be undone before calling undo().

    Parameters:
        max_entries (int): Maximum entries to return. Default 20, max 100.

    Returns:
        {"status": "ok", "total_entries": 45, "returned": 20,
         "can_undo": true, "can_redo": false,
         "history": [{"index": 44, "title": "Move Actors", "context": "..."}]}

    Example:
        get_undo_history()
        get_undo_history(max_entries=5)

    Notes:
        - History is ordered newest-first
        - Free tier command
    """
    return _safe_call(lambda c: c.send_command("get_undo_history", {"max_entries": max_entries}))

@mcp.tool()
def begin_undo_group(description: str = "Arcwright Operation") -> str:
    """Begin a grouped undo transaction.

    All editor operations between begin_undo_group and end_undo_group
    are treated as a single undo-able operation. This means complex
    multi-step builds (e.g., "create arena with enemies and pickups")
    can be undone with a single undo() call.

    Parameters:
        description (str): Human-readable description shown in the undo history.
            Default: "Arcwright Operation".

    Returns:
        {"status": "ok", "description": "Build Arena", "status": "transaction_open"}

    Example:
        begin_undo_group(description="Build Arena")
        # ... spawn actors, create blueprints, apply materials ...
        end_undo_group()
        # All operations above are now one undo step

    Notes:
        - MUST be paired with end_undo_group() — forgetting to close leaves the
          transaction open and can corrupt the undo stack
        - Nested groups are supported by UE's transaction system
        - Free tier command
    """
    return _safe_call(lambda c: c.send_command("begin_undo_group", {"description": description}))

@mcp.tool()
def end_undo_group() -> str:
    """End a grouped undo transaction started by begin_undo_group.

    Closes the current transaction group. All operations since the matching
    begin_undo_group are now a single entry in the undo history.

    Parameters:
        (none)

    Returns:
        {"status": "ok", "status": "transaction_closed"}

    Example:
        begin_undo_group(description="Populate Level")
        # ... multiple operations ...
        end_undo_group()

    Notes:
        - Must be called after begin_undo_group
        - Free tier command
    """
    return _safe_call(lambda c: c.send_command("end_undo_group", {}))

# ---------------------------------------------------------------------------
# Widget DSL v2 — Phase 2 Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def set_widget_anchor(widget_blueprint: str, widget_name: str, anchor: str = "",
                      offset_x: float = 0, offset_y: float = 0,
                      size_x: float = 0, size_y: float = 0) -> str:
    """Set the anchor, position offset, and size of a widget in a CanvasPanel.

    Parameters:
        widget_blueprint: Name of the Widget Blueprint (e.g. "WBP_GameHUD")
        widget_name: Name of the target widget
        anchor: Preset name — TopLeft, TopCenter, TopRight, CenterLeft, Center,
                CenterRight, BottomLeft, BottomCenter, BottomRight, Fill, FillX, FillY
        offset_x: X position offset from anchor (pixels)
        offset_y: Y position offset from anchor (pixels)
        size_x: Widget width (pixels, 0 = auto)
        size_y: Widget height (pixels, 0 = auto)

    Returns:
        {"status": "ok", "widget_name": "HealthBar", "anchor": "BottomLeft"}

    Notes:
        - Widget must be a child of a CanvasPanel
        - Pro tier command
    """
    params = {"widget_blueprint": widget_blueprint, "widget_name": widget_name}
    if anchor: params["anchor"] = anchor
    if offset_x: params["offset_x"] = offset_x
    if offset_y: params["offset_y"] = offset_y
    if size_x: params["size_x"] = size_x
    if size_y: params["size_y"] = size_y
    return _safe_call(lambda c: c.send_command("set_widget_anchor", params), "set_widget_anchor")

@mcp.tool()
def set_widget_binding(widget_blueprint: str, widget_name: str, property: str,
                       variable_name: str, variable_type: str = "Float") -> str:
    """Create a Blueprint variable and bind it to a widget property.

    Creates the variable on the Widget Blueprint so it can drive UI at runtime.
    For example, bind a "Health" Float variable to a ProgressBar's percent.

    Parameters:
        widget_blueprint: Widget Blueprint name
        widget_name: Target widget name
        property: Widget property to bind (Text, Percent, Visibility, ColorAndOpacity)
        variable_name: Blueprint variable name to create (e.g. "Health")
        variable_type: Float, String, Bool, Integer, Text

    Returns:
        {"status": "ok", "variable_created": true, "variable_name": "Health"}

    Notes:
        - Pro tier command
    """
    return _safe_call(lambda c: c.send_command("set_widget_binding", {
        "widget_blueprint": widget_blueprint, "widget_name": widget_name,
        "property": property, "variable_name": variable_name,
        "variable_type": variable_type,
    }), "set_widget_binding")

@mcp.tool()
def create_widget_animation(widget_blueprint: str, animation_name: str,
                            duration: float = 1.0) -> str:
    """Create a UWidgetAnimation on a Widget Blueprint.

    Parameters:
        widget_blueprint: Widget Blueprint name
        animation_name: Name for the animation (e.g. "FadeIn", "DamageFlash")
        duration: Animation length in seconds

    Returns:
        {"status": "ok", "animation_name": "FadeIn", "duration": 1.0}

    Notes:
        - Use add_animation_track to add property tracks after creation
        - Pro tier command
    """
    return _safe_call(lambda c: c.send_command("create_widget_animation", {
        "widget_blueprint": widget_blueprint, "animation_name": animation_name,
        "duration": duration,
    }), "create_widget_animation")

@mcp.tool()
def add_animation_track(widget_blueprint: str, animation_name: str,
                        target_widget: str, property: str = "RenderOpacity") -> str:
    """Add a property track to an existing widget animation.

    Parameters:
        widget_blueprint: Widget Blueprint name
        animation_name: Existing animation name
        target_widget: Widget to animate
        property: Property to animate (RenderOpacity, RenderTransform, ColorAndOpacity)

    Returns:
        {"status": "ok", "animation_name": "FadeIn", "property": "RenderOpacity"}

    Notes:
        - Pro tier command
    """
    return _safe_call(lambda c: c.send_command("add_animation_track", {
        "widget_blueprint": widget_blueprint, "animation_name": animation_name,
        "target_widget": target_widget, "property": property,
    }), "add_animation_track")

@mcp.tool()
def set_widget_brush(widget_blueprint: str, widget_name: str,
                     brush_type: str = "Color", brush_value: str = "#FFFFFF",
                     tint: str = "") -> str:
    """Set the visual brush on an Image, Border, or Button widget.

    Parameters:
        widget_blueprint: Widget Blueprint name
        widget_name: Target widget (must be Image, Border, or Button)
        brush_type: "Color" (hex), "Texture" (asset path), or "Material" (asset path)
        brush_value: Hex color (e.g. "#FF0088") or asset path
        tint: Optional tint color (hex) applied over the brush

    Returns:
        {"status": "ok", "brush_type": "Color", "applied_to": "Image"}

    Notes:
        - Pro tier command
    """
    params = {"widget_blueprint": widget_blueprint, "widget_name": widget_name,
              "brush_type": brush_type, "brush_value": brush_value}
    if tint: params["tint"] = tint
    return _safe_call(lambda c: c.send_command("set_widget_brush", params), "set_widget_brush")

@mcp.tool()
def set_widget_font(widget_blueprint: str, widget_name: str,
                    font_size: int = 16, font_family: str = "",
                    font_style: str = "", letter_spacing: float = 0) -> str:
    """Set font properties on a TextBlock widget.

    Parameters:
        widget_blueprint: Widget Blueprint name
        widget_name: Target TextBlock widget
        font_size: Font size in pixels
        font_family: Font family name (looks in Content/Fonts/ then engine fonts)
        font_style: Regular, Bold, Italic, or BoldItalic
        letter_spacing: Extra spacing between characters

    Returns:
        {"status": "ok", "font_size": 24, "typeface": "Bold"}

    Notes:
        - Pro tier command
    """
    params = {"widget_blueprint": widget_blueprint, "widget_name": widget_name}
    if font_size: params["font_size"] = font_size
    if font_family: params["font_family"] = font_family
    if font_style: params["font_style"] = font_style
    if letter_spacing: params["letter_spacing"] = letter_spacing
    return _safe_call(lambda c: c.send_command("set_widget_font", params), "set_widget_font")

@mcp.tool()
def preview_widget(widget_blueprint: str) -> str:
    """Open a Widget Blueprint in the UMG designer for visual preview.

    Parameters:
        widget_blueprint: Widget Blueprint name to preview

    Returns:
        {"status": "ok", "preview_opened": true}

    Notes:
        - Opens the Blueprint editor's Designer tab
        - Pro tier command
    """
    return _safe_call(lambda c: c.send_command("preview_widget", {
        "widget_blueprint": widget_blueprint,
    }), "preview_widget")

@mcp.tool()
def get_widget_screenshot(widget_blueprint: str, output_path: str = "",
                          width: int = 1920, height: int = 1080) -> str:
    """Render a Widget Blueprint to a PNG image for AI visual inspection.

    Creates a temporary widget instance, renders it to a texture, and saves as PNG.

    Parameters:
        widget_blueprint: Widget Blueprint name
        output_path: Output file path (defaults to temp directory)
        width: Render width in pixels
        height: Render height in pixels

    Returns:
        {"status": "ok", "path": "C:/tmp/arcwright_widget_WBP_HUD.png",
         "width": 1920, "height": 1080, "size_bytes": 150000}

    Notes:
        - Pro tier command
    """
    params = {"widget_blueprint": widget_blueprint}
    if output_path: params["output_path"] = output_path
    if width != 1920: params["width"] = width
    if height != 1080: params["height"] = height
    return _safe_call(lambda c: c.send_command("get_widget_screenshot", params), "get_widget_screenshot")

# ---------------------------------------------------------------------------
# Audio System Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def create_sound_class(name: str, volume: float = 1.0, pitch: float = 1.0, parent_class: str = "") -> str:
    """Create a USoundClass asset for audio categorization (Master, Music, SFX, Voice, etc.)."""
    params = {"name": name, "volume": volume, "pitch": pitch}
    if parent_class: params["parent_class"] = parent_class
    return _safe_call(lambda c: c.send_command("create_sound_class", params), "create_sound_class")

@mcp.tool()
def create_sound_mix(name: str, modifiers: list = None) -> str:
    """Create a USoundMix that adjusts volume/pitch of sound classes (e.g. CombatMix boosts SFX, lowers Music)."""
    params = {"name": name}
    if modifiers: params["modifiers"] = modifiers
    return _safe_call(lambda c: c.send_command("create_sound_mix", params), "create_sound_mix")

@mcp.tool()
def set_sound_class_volume(sound_class: str, volume: float = 1.0) -> str:
    """Adjust volume of a sound class at runtime. Volume range: 0.0-1.0."""
    return _safe_call(lambda c: c.send_command("set_sound_class_volume", {"sound_class": sound_class, "volume": volume}), "set_sound_class_volume")

@mcp.tool()
def create_attenuation_settings(name: str, inner_radius: float = 200, outer_radius: float = 2000, spatialization: bool = True) -> str:
    """Create a USoundAttenuation asset defining how sound fades with distance."""
    return _safe_call(lambda c: c.send_command("create_attenuation_settings", {"name": name, "inner_radius": inner_radius, "outer_radius": outer_radius, "spatialization": spatialization}), "create_attenuation_settings")

@mcp.tool()
def create_ambient_sound(sound_asset: str, location: dict = None, attenuation: str = "", auto_play: bool = True, label: str = "") -> str:
    """Spawn an AAmbientSound actor in the level with optional 3D attenuation."""
    params = {"sound_asset": sound_asset, "auto_play": auto_play}
    if location: params["location"] = location
    if attenuation: params["attenuation"] = attenuation
    if label: params["label"] = label
    return _safe_call(lambda c: c.send_command("create_ambient_sound", params), "create_ambient_sound")

@mcp.tool()
def create_audio_volume(location: dict = None, reverb_preset: str = "None", label: str = "") -> str:
    """Create an AAudioVolume actor with reverb settings (Cathedral, Cave, Hallway, etc.)."""
    params = {"reverb_preset": reverb_preset}
    if location: params["location"] = location
    if label: params["label"] = label
    return _safe_call(lambda c: c.send_command("create_audio_volume", params), "create_audio_volume")

@mcp.tool()
def set_reverb_settings(audio_volume: str, preset: str = "None", volume: float = 1.0, fade_time: float = 0.5) -> str:
    """Modify reverb on an existing Audio Volume actor."""
    return _safe_call(lambda c: c.send_command("set_reverb_settings", {"audio_volume": audio_volume, "preset": preset, "volume": volume, "fade_time": fade_time}), "set_reverb_settings")

@mcp.tool()
def play_sound_2d(sound_asset: str, volume: float = 1.0, pitch: float = 1.0) -> str:
    """Play a non-spatialized sound (for UI, music, stingers). Uses PlaySound2D."""
    return _safe_call(lambda c: c.send_command("play_sound_2d", {"sound_asset": sound_asset, "volume": volume, "pitch": pitch}), "play_sound_2d")

@mcp.tool()
def set_sound_concurrency(name: str, max_count: int = 4, resolution_rule: str = "StopOldest") -> str:
    """Create a USoundConcurrency asset limiting simultaneous sounds (PreventNew/StopOldest/StopQuietest/StopLowestPriority)."""
    return _safe_call(lambda c: c.send_command("set_sound_concurrency", {"name": name, "max_count": max_count, "resolution_rule": resolution_rule}), "set_sound_concurrency")

@mcp.tool()
def create_sound_cue(name: str, sounds: list = None, randomize: bool = False, loop: bool = False) -> str:
    """Create a USoundCue asset with wave players for each sound, optional randomization."""
    params = {"name": name, "randomize": randomize, "loop": loop}
    if sounds: params["sounds"] = sounds
    return _safe_call(lambda c: c.send_command("create_sound_cue", params), "create_sound_cue")

@mcp.tool()
def import_audio_file(file_path: str, asset_name: str = "", destination: str = "/Game/Audio/Imported/") -> str:
    """Import a WAV/OGG audio file into UE Content Browser as USoundWave."""
    params = {"file_path": file_path, "destination": destination}
    if asset_name: params["asset_name"] = asset_name
    return _safe_call(lambda c: c.send_command("import_audio_file", params), "import_audio_file")

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _save_audio(audio_bytes: bytes, filename: str, subdir: str = "SFX") -> str:
    """Save audio bytes to Arcwright audio directory. Returns file path."""
    import tempfile
    base = os.path.join(tempfile.gettempdir(), "arcwright_audio", subdir)
    os.makedirs(base, exist_ok=True)
    if not filename.endswith((".wav", ".mp3")):
        filename += ".mp3"
    path = os.path.join(base, filename)
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return path

def _import_to_ue(file_path: str, asset_name: str, destination: str) -> dict:
    """Import audio file to UE via TCP command."""
    try:
        client = _get_client()
        result = client.send_command("import_audio_file", {
            "file_path": file_path, "asset_name": asset_name, "destination": destination
        })
        client.close()
        return result
    except Exception as e:
        return {"error": f"UE import failed: {e}"}

def _load_voice_library():
    if os.path.isfile(lib_path):
        with open(lib_path, "r") as f:
            return json.load(f)
    return {}

@mcp.tool()
def create_audio_plan_table(table_name: str = "DT_AudioPlan") -> str:
    """Create a Data Table in UE for tracking all game audio (dialogue, SFX, ambient, music). Pro tier."""
    dsl = f"""DATATABLE: {table_name}
STRUCT: AudioPlanEntry

COLUMN ID: String
COLUMN Category: String
COLUMN Character: String
COLUMN Line: String
COLUMN Emotion: String
COLUMN Context: String
COLUMN VoiceID: String
COLUMN Status: String = Pending
COLUMN AudioAsset: String"""

    try:
        _dt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dt_parser")
        if _dt_dir not in sys.path: sys.path.insert(0, _dt_dir)
        from dt_parser import parse_dt_dsl
        ir = parse_dt_dsl(dsl)
        return _safe_call(lambda c: c.send_command("create_data_table", {"ir": json.dumps(ir)}), "create_audio_plan_table")
    except Exception as e:
        return json.dumps({"error": f"Failed to create audio plan table: {e}"})

@mcp.tool()
def add_audio_plan_entry(table_name: str, id: str, category: str, line: str,
                         character: str = "", emotion: str = "", context: str = "",
                         voice_id: str = "") -> str:
    """Add one entry to the audio plan table. Pro tier."""
    values = {"ID": id, "Category": category, "Line": line, "Character": character,
              "Emotion": emotion, "Context": context, "VoiceID": voice_id,
              "Status": "Pending", "AudioAsset": ""}
    return _safe_call(lambda c: c.send_command("add_data_table_row", {
        "table_name": table_name, "row_name": id, "values": values
    }), "add_audio_plan_entry")

@mcp.tool()
def add_audio_plan_batch(table_name: str, entries: list = None) -> str:
    """Add multiple entries to the audio plan table at once. Pro tier."""
    if not entries: return json.dumps({"error": "Missing entries parameter"})
    results = []
    try:
        client = _get_client()
        for entry in entries:
            row_id = entry.get("ID", entry.get("id", ""))
            r = client.send_command("add_data_table_row", {
                "table_name": table_name, "row_name": row_id, "values": entry
            })
            results.append({"id": row_id, "status": r.get("status", "error")})
        client.close()
        return json.dumps({"count_added": len(results), "results": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "added_before_error": len(results)})

@mcp.tool()
def import_audio_plan_csv(csv_path: str, table_name: str = "DT_AudioPlan") -> str:
    """Import audio plan entries from a CSV file. Creates table if needed. Pro tier."""
    import csv
    if not os.path.isfile(csv_path):
        return json.dumps({"error": f"CSV file not found: {csv_path}"})
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            entries = [dict(row) for row in reader]
        # Attempt to create table (ignore error if exists)
        create_audio_plan_table(table_name)
        result = add_audio_plan_batch(table_name, entries)
        r = json.loads(result)
        r["rows_imported"] = r.get("count_added", 0)
        r["source"] = csv_path
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_plan_status(table_name: str = "DT_AudioPlan") -> str:
    """Get status summary of the audio plan — pending, generated, imported, errors by category. Pro tier."""
    try:
        client = _get_client()
        rows_resp = client.send_command("get_data_table_rows", {"table_name": table_name})
        client.close()
        rows = rows_resp.get("data", {}).get("rows", [])
        status = {"total": len(rows), "by_category": {}}
        for row in rows:
            vals = row.get("values", {})
            cat = vals.get("Category", "Other")
            st = vals.get("Status", "Unknown")
            if cat not in status["by_category"]:
                status["by_category"][cat] = {"Pending": 0, "Generated": 0, "Imported": 0, "Error": 0}
            status["by_category"][cat][st] = status["by_category"][cat].get(st, 0) + 1
        return json.dumps(status, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def preview_character_lineup(table_name: str = "DT_AudioPlan") -> str:
    """Generate one preview line for each character in the plan using their assigned voice. Pro tier."""
    try:
        client = _get_client()
        rows_resp = client.send_command("get_data_table_rows", {"table_name": table_name})
        client.close()
        rows = rows_resp.get("data", {}).get("rows", [])

        # Get unique characters with voice IDs
        chars = {}
        for row in rows:
            vals = row.get("values", {})
            name = vals.get("Character", "")
            voice = vals.get("VoiceID", "")
            line = vals.get("Line", "")
            if name and voice and name not in chars:
                chars[name] = {"voice_id": voice, "sample_line": line}

        if el_err: return el_err

        previews = []
        for name, info in chars.items():
            try:
                audio = el_client.text_to_speech(info["voice_id"], info["sample_line"])
                path = _save_audio(audio, f"preview_{name}", "Previews")
                previews.append({"name": name, "voice_id": info["voice_id"],
                                "preview_path": path, "sample_line": info["sample_line"][:50]})
            except Exception as e:
                previews.append({"name": name, "error": str(e)})

        return json.dumps({"characters": previews, "count": len(previews)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# ---------------------------------------------------------------------------
# Bridge-Only DSL Systems (11 systems with generic config pattern)
# ---------------------------------------------------------------------------

_DSL_SYSTEMS_LIST = [
    ("input", "Enhanced Input"), ("smartobject", "Smart Object"), ("sound", "Sound Design"),
    ("replication", "Multiplayer Replication"), ("controlrig", "Control Rig"),
    ("statetree", "State Tree"), ("vehicle", "Chaos Vehicle"),
    ("worldpartition", "World Partition"), ("landscape", "Landscape"),
    ("foliage", "Foliage"), ("massentity", "Mass Entity"),
    ("shader", "Shader/HLSL"), ("procmesh", "Procedural Mesh"),
    ("paper2d", "Paper2D"), ("composure", "Composure"), ("dmx", "DMX Stage Lighting"),
]

for _sid, _sname in _DSL_SYSTEMS_LIST:
    exec(f"""
@mcp.tool()
def create_{_sid}_config(name: str) -> str:
    'Create a {_sname} configuration. Pro tier.'
    return _safe_call(lambda c: c.send_command("create_{_sid}_config", {{"name": name}}), "create_{_sid}_config")

@mcp.tool()
def add_{_sid}_element(config: str, element_type: str, element_name: str = "") -> str:
    'Add an element to a {_sname} config. Pro tier.'
    return _safe_call(lambda c: c.send_command("add_{_sid}_element", {{"config": config, "element_type": element_type, "element_name": element_name}}), "add_{_sid}_element")
""")

@mcp.tool()
def get_input_dsl_guide() -> str:
    """Get Enhanced Input DSL format guide. Free tier."""
    return "INPUT: ConfigName\\nACTION: IA_Name @type=Axis2D|Bool\\nMAPPING: IMC_Name\\n  MAP: IA_Name @key=W @modifiers=SwizzleYXZ"

@mcp.tool()
def get_smartobject_dsl_guide() -> str:
    """Get Smart Object DSL format guide. Free tier."""
    return "SMART_OBJECT: SO_Name @actor=BP_Actor\\nSLOT: Name @type=Interaction @animation=AM_Anim @tags_required=NPC.Type"

@mcp.tool()
def get_sound_design_dsl_guide() -> str:
    """Get Sound Design DSL format guide. Free tier."""
    return "SOUND_DESIGN: Name\\nSOUND_CLASS: Name @volume=0.7\\nATTENUATION: Name @inner_radius=200\\nAMBIENT: Name @sound=Asset"

@mcp.tool()
def get_replication_dsl_guide() -> str:
    """Get Replication DSL format guide. Free tier."""
    return "REPLICATION: Name @class=BP_Actor\\nREPLICATED_PROPERTY: Health @type=Float @condition=OwnerOnly\\nRPC: Name @authority=Server @reliable=true"

@mcp.tool()
def get_controlrig_dsl_guide() -> str:
    """Get Control Rig DSL format guide. Free tier."""
    return "CONTROL_RIG: Name @skeleton=SK_Mesh\\nIK_CHAIN: Name @root=bone @tip=bone\\nFK_CONTROL: Name @bone=bone_name"

@mcp.tool()
def get_statetree_dsl_guide() -> str:
    """Get State Tree DSL format guide. Free tier."""
    return "STATE_TREE: Name\\nSTATE: Name @priority=High\\n  TASK: Name @ability=GA_Name\\n  CONDITION: Name @type=Perception"

@mcp.tool()
def get_vehicle_dsl_guide() -> str:
    """Get Vehicle DSL format guide. Free tier."""
    return "VEHICLE: Name @chassis_mass=1500\\nWHEEL: FL @position=-80,-130,0 @radius=35\\nENGINE: V8 @max_torque=750"

@mcp.tool()
def get_worldpartition_dsl_guide() -> str:
    """Get World Partition DSL format guide. Free tier."""
    return "WORLD_PARTITION: Name @cell_size=12800\\nREGION: Name @bounds=x1,y1,x2,y2 @priority=High\\nDATA_LAYER: Name @type=Runtime"

@mcp.tool()
def get_landscape_dsl_guide() -> str:
    """Get Landscape DSL format guide. Free tier."""
    return "LANDSCAPE: Name @size=4033\\nLAYER: Grass @material=M_Grass\\nPAINT_RULE: Name @slope_threshold=35\\nWATER_BODY: River @type=River"

@mcp.tool()
def get_foliage_dsl_guide() -> str:
    """Get Foliage DSL format guide. Free tier."""
    return "FOLIAGE_CONFIG: Name\\nFOLIAGE_TYPE: Trees @mesh=SM_Tree @density=0.01\\nPLACEMENT_RULE: Name @boost_near=WaterBody"

@mcp.tool()
def get_massentity_dsl_guide() -> str:
    """Get Mass Entity DSL format guide. Free tier."""
    return "MASS_CONFIG: Name\\nARCHETYPE: Name\\n  TRAIT: Transform\\n  TRAIT: Movement @speed=300\\nPROCESSOR: Name @requires=Transform\\nSPAWNER: Name @count=100"

@mcp.tool()
def get_shader_dsl_guide() -> str:
    """Get Shader/HLSL DSL format guide. Free tier."""
    return "SHADER: Name @type=MaterialFunction\\nINPUT: Name @type=Float @default=0.5\\nHLSL: Name @code=shader_code\\nOUTPUT: Color @source=Node.rgb"

@mcp.tool()
def get_procmesh_dsl_guide() -> str:
    """Get Procedural Mesh DSL format guide. Free tier."""
    return "PROC_MESH: Name @collision=true\\nSHAPE: Name @type=Cylinder|Sphere|Box @radius=20 @height=100\\nDEFORM: Name @type=PerlinNoise @amplitude=3.0"

@mcp.tool()
def get_paper2d_dsl_guide() -> str:
    """Get Paper2D DSL format guide. Free tier."""
    return "PAPER2D: Name\\nSPRITE: Name @texture=T_Sheet @source_x=0 @source_width=64\\nFLIPBOOK: Name @fps=12 @loop=true\\nTILEMAP: Name @tile_width=32 @map_width=40"

@mcp.tool()
def get_composure_dsl_guide() -> str:
    """Get Composure (compositing) DSL format guide. Free tier."""
    return "COMPOSURE: Name\\nELEMENT: Name @type=MediaPlate|CapturePass\\nPASS: Name @type=ChromaKeyer @key_color=0,1,0\\nCOMPOSITE: Name @layers=A,B,C"

@mcp.tool()
def get_dmx_dsl_guide() -> str:
    """Get DMX (stage lighting) DSL format guide. Free tier."""
    return "DMX: Name\\nUNIVERSE: Name @protocol=sACN @port=5568\\nFIXTURE: Name @type=GenericDimmer @start_channel=1\\nCUE: Name @fade_time=2.0"

# ---------------------------------------------------------------------------
# AI Perception DSL

@mcp.tool()
def create_ai_perception(name: str, owner: str = "") -> str:
    """Create AI perception config with senses. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_ai_perception", {"name": name, "owner": owner}), "create_ai_perception")

@mcp.tool()
def add_perception_sense(perception: str, sense_type: str, **kwargs) -> str:
    """Add a sense (Sight/Hearing/Damage) to an AI perception config. Pro tier."""
    params = {"perception": perception, "sense_type": sense_type}
    return _safe_call(lambda c: c.send_command("add_perception_sense", params), "add_perception_sense")

# ---------------------------------------------------------------------------
# Physics Constraints DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def create_physics_setup(name: str, actor: str = "") -> str:
    """Create a physics config with constraints and destructibles. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_physics_setup", {"name": name, "actor": actor}), "create_physics_setup")

@mcp.tool()
def add_physics_constraint_config(setup: str, constraint_name: str, constraint_type: str = "Hinge") -> str:
    """Add a physics constraint (Hinge/Ball/Prismatic/Fixed). Pro tier."""
    return _safe_call(lambda c: c.send_command("add_physics_constraint_dsl", {"setup": setup, "constraint_name": constraint_name, "type": constraint_type}), "add_physics_constraint_dsl")

@mcp.tool()
def add_destructible(setup: str, target: str, health: str = "100") -> str:
    """Add a destructible object with health and break effects. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_destructible", {"setup": setup, "target": target, "health": health}), "add_destructible")

# ---------------------------------------------------------------------------
# Gameplay Tags DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def create_tag_hierarchy(name: str = "GameplayTags") -> str:
    """Create a gameplay tag hierarchy. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_tag_hierarchy", {"name": name}), "create_tag_hierarchy")

@mcp.tool()
def add_gameplay_tag(tag: str) -> str:
    """Register a gameplay tag (e.g. Ability.Active.Fire). Pro tier."""
    return _safe_call(lambda c: c.send_command("add_gameplay_tag", {"tag": tag}), "add_gameplay_tag")

# ---------------------------------------------------------------------------
# GAS (Gameplay Ability System) DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def create_ability_system(name: str, owner: str = "") -> str:
    """Create a GAS configuration with attribute sets and abilities. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_ability_system", {"name": name, "owner": owner}), "create_ability_system")

@mcp.tool()
def add_gas_attribute(system: str, set_name: str, attribute_name: str, base: float = 0, min_val: float = 0, max_val: float = 9999) -> str:
    """Add an attribute (Health, Mana, etc.) to a GAS attribute set. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_attribute", {"system": system, "set_name": set_name, "attribute_name": attribute_name, "base": base, "min": min_val, "max": max_val}), "add_attribute")

@mcp.tool()
def add_gas_ability(system: str, ability_name: str, display_name: str = "", cooldown: float = 0, cost_attribute: str = "", cost_amount: float = 0, tags: str = "") -> str:
    """Add a gameplay ability with cooldown, cost, and tags. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_ability", {"system": system, "ability_name": ability_name, "display_name": display_name, "cooldown": cooldown, "cost_attribute": cost_attribute, "cost_amount": cost_amount, "tags": tags}), "add_ability")

@mcp.tool()
def add_gas_ability_effect(system: str, ability_name: str, effect_name: str, effect_type: str = "Instant", duration: float = 0, target: str = "Enemy", modifiers: str = "[]") -> str:
    """Add an effect (damage, heal, buff) to a gameplay ability. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_ability_effect", {"system": system, "ability_name": ability_name, "effect_name": effect_name, "type": effect_type, "duration": duration, "target": target, "modifiers": modifiers}), "add_ability_effect")

@mcp.tool()
def get_ability_data(system: str) -> str:
    """Get full GAS configuration as JSON. Pro tier."""
    return _safe_call(lambda c: c.send_command("get_ability_data", {"system": system}), "get_ability_data")

# ---------------------------------------------------------------------------
# Sequence (Cinematic) DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def add_sequence_camera(sequence: str, camera_name: str = "CineCam", fov: float = 90) -> str:
    """Add a camera track to a level sequence. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_sequence_camera", {"sequence": sequence, "camera_name": camera_name, "fov": fov}), "add_sequence_camera")

@mcp.tool()
def add_sequence_audio(sequence: str, audio_name: str, sound: str = "", volume: float = 1.0) -> str:
    """Add an audio track to a level sequence. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_sequence_audio", {"sequence": sequence, "audio_name": audio_name, "sound": sound, "volume": volume}), "add_sequence_audio")

@mcp.tool()
def add_sequence_fade(sequence: str) -> str:
    """Add a fade track to a level sequence. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_sequence_fade", {"sequence": sequence}), "add_sequence_fade")

@mcp.tool()
def add_sequence_event(sequence: str, time: float, action: str = "") -> str:
    """Add an event trigger at a specific time in a sequence. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_sequence_event", {"sequence": sequence, "time": time, "action": action}), "add_sequence_event")

# ---------------------------------------------------------------------------
# Quest DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def create_quest(name: str, title: str = "", description: str = "", giver: str = "", category: str = "Main", reward_xp: int = 0, reward_gold: int = 0) -> str:
    """Create a quest with metadata. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_quest", {"name": name, "title": title, "description": description, "giver": giver, "category": category, "reward_xp": reward_xp, "reward_gold": reward_gold}), "create_quest")

@mcp.tool()
def add_quest_stage(quest: str, stage_id: str, description: str = "", stage_type: str = "Custom") -> str:
    """Add a stage to a quest. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_quest_stage", {"quest": quest, "stage_id": stage_id, "description": description, "type": stage_type}), "add_quest_stage")

@mcp.tool()
def add_quest_objective(quest: str, stage_id: str, objective_id: str, text: str = "", target: str = "", count: int = 1, optional: bool = False) -> str:
    """Add an objective to a quest stage. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_quest_objective", {"quest": quest, "stage_id": stage_id, "objective_id": objective_id, "text": text, "target": target, "count": count, "optional": optional}), "add_quest_objective")

@mcp.tool()
def get_quest_data(quest: str) -> str:
    """Get quest data as JSON. Pro tier."""
    return _safe_call(lambda c: c.send_command("get_quest_data", {"quest": quest}), "get_quest_data")

# ---------------------------------------------------------------------------
# Dialogue DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def create_dialogue(name: str) -> str:
    """Create a dialogue data table for branching conversations. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_dialogue", {"name": name}), "create_dialogue")

@mcp.tool()
def add_dialogue_node(dialogue: str, node_id: str, speaker: str, text: str,
                      choices: str = "[]", conditions: str = "", actions: str = "",
                      next_node: str = "", flags: str = "") -> str:
    """Add a dialogue node with text, choices, conditions. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_dialogue_node", {
        "dialogue": dialogue, "node_id": node_id, "speaker": speaker, "text": text,
        "choices": choices, "conditions": conditions, "actions": actions,
        "next_node": next_node, "flags": flags
    }), "add_dialogue_node")

@mcp.tool()
def get_dialogue_tree(dialogue: str) -> str:
    """Get the full dialogue tree as JSON for inspection. Pro tier."""
    return _safe_call(lambda c: c.send_command("get_dialogue_tree", {"dialogue": dialogue}), "get_dialogue_tree")

# ---------------------------------------------------------------------------
# Material Graph DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def create_material_graph(name: str) -> str:
    """Create an empty UMaterial asset for building a node graph. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_material_graph", {"name": name}), "create_material_graph")

@mcp.tool()
def add_material_node(material: str, type: str, name: str = "", **kwargs) -> str:
    """Add an expression node to a material (CONSTANT3, MULTIPLY, SCALAR_PARAM, etc.). Pro tier."""
    params = {"material": material, "type": type, "name": name}
    return _safe_call(lambda c: c.send_command("add_material_node", params), "add_material_node")

@mcp.tool()
def connect_material_nodes(material: str, source_index: int, dest_index: int, input_name: str = "A") -> str:
    """Connect one material node's output to another's input. Pro tier."""
    return _safe_call(lambda c: c.send_command("connect_material_nodes", {"material": material, "source_index": source_index, "dest_index": dest_index, "input_name": input_name}), "connect_material_nodes")

@mcp.tool()
def set_material_output(material: str, node_index: int, output_pin: str) -> str:
    """Connect a node to a material output (BaseColor, Roughness, Metallic, Normal, Emissive). Pro tier."""
    return _safe_call(lambda c: c.send_command("set_material_output", {"material": material, "node_index": node_index, "output_pin": output_pin}), "set_material_output")

@mcp.tool()
def compile_material_graph(material: str) -> str:
    """Compile a material after building its node graph. Pro tier."""
    return _safe_call(lambda c: c.send_command("compile_material_graph", {"material": material}), "compile_material_graph")

# ---------------------------------------------------------------------------
# Animation Blueprint DSL
# ---------------------------------------------------------------------------

@mcp.tool()
def create_anim_blueprint_full(name: str, skeleton_path: str, mesh_path: str = "") -> str:
    """Create a UAnimBlueprint with full DSL support (state machines, transitions). Pro tier."""
    params = {"name": name, "skeleton_path": skeleton_path}
    if mesh_path: params["mesh_path"] = mesh_path
    return _safe_call(lambda c: c.send_command("create_anim_blueprint_dsl", params), "create_anim_blueprint_dsl")

@mcp.tool()
def add_state_machine(anim_bp: str, machine_name: str) -> str:
    """Add a state machine node to an AnimBlueprint's AnimGraph. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_state_machine", {"anim_bp": anim_bp, "machine_name": machine_name}), "add_state_machine")

@mcp.tool()
def add_anim_state_full(anim_bp: str, machine_name: str, state_name: str, animation_path: str = "", is_entry: bool = False) -> str:
    """Add a state to an AnimBP state machine with full wiring. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_anim_state_2", {"anim_bp": anim_bp, "machine_name": machine_name, "state_name": state_name, "animation_path": animation_path, "is_entry": is_entry}), "add_anim_state_2")

@mcp.tool()
def add_anim_transition_full(anim_bp: str, from_state: str, to_state: str, condition: str = "", blend_duration: float = 0.2) -> str:
    """Add a wired transition between AnimBP states with condition. Pro tier."""
    return _safe_call(lambda c: c.send_command("add_anim_transition_2", {"anim_bp": anim_bp, "from_state": from_state, "to_state": to_state, "condition": condition, "blend_duration": blend_duration}), "add_anim_transition_2")

@mcp.tool()
def add_anim_layer(anim_bp: str, layer_name: str, bone_mask_root: str = "spine_01", slot_name: str = "DefaultSlot", blend_mode: str = "Override") -> str:
    """Add a layered bone blend to an AnimBP (e.g. upper body combat). Pro tier."""
    return _safe_call(lambda c: c.send_command("add_anim_layer", {"anim_bp": anim_bp, "layer_name": layer_name, "bone_mask_root": bone_mask_root, "slot_name": slot_name, "blend_mode": blend_mode}), "add_anim_layer")

@mcp.tool()
def create_aim_offset(name: str, skeleton_path: str) -> str:
    """Create a UAimOffsetBlendSpace asset. Pro tier."""
    return _safe_call(lambda c: c.send_command("create_aim_offset", {"name": name, "skeleton_path": skeleton_path}), "create_aim_offset")

@mcp.tool()
def set_anim_notify(montage_path: str, time_percent: float, notify_type: str = "Custom", event_name: str = "") -> str:
    """Add a notify event to an animation montage. Pro tier."""
    return _safe_call(lambda c: c.send_command("set_anim_notify_2", {"montage_name": montage_path, "section_name": event_name, "start_time": time_percent}), "set_anim_notify_2")

@mcp.tool()
def compile_anim_blueprint(anim_bp: str) -> str:
    """Compile an Animation Blueprint. Pro tier."""
    return _safe_call(lambda c: c.send_command("compile_anim_blueprint", {"anim_bp": anim_bp}), "compile_anim_blueprint")

# ---------------------------------------------------------------------------
# Built-in Documentation (Teaching Tools)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_blueprint_dsl_guide() -> str:
    """Get the complete Blueprint creation guide — DSL format, step-by-step TCP workflow, AND UFunction paths.

    Call this before creating any Blueprint. Returns:
    - Step-by-step TCP workflow (create_blueprint → add_nodes_batch → add_connections_batch)
    - DSL format for create_blueprint_from_dsl / import_from_ir
    - 200+ UFunction paths for CallFunction nodes
    - 3 working game logic examples (not just PrintString)
    - Pin naming conventions
    """
    return """# Arcwright Blueprint Creation Guide

## RECOMMENDED: Step-by-step TCP workflow

### Step 1: Create empty Blueprint
```json
{"command": "create_blueprint", "params": {"name": "BP_HealthPickup", "parent_class": "Actor", "variables": [{"name": "HealAmount", "type": "Float", "default": "25.0"}]}}
```

### Step 2: Add nodes in batch
```json
{"command": "add_nodes_batch", "params": {"blueprint": "BP_HealthPickup", "nodes": [
  {"id": "n1", "type": "Event", "event": "ReceiveActorBeginOverlap"},
  {"id": "n2", "type": "CallFunction", "function": "/Script/Engine.Actor:K2_DestroyActor"},
  {"id": "n3", "type": "CallFunction", "function": "/Script/Engine.KismetSystemLibrary:PrintString", "params": {"InString": "Healed!"}}
]}}
```

### Step 3: Wire connections
```json
{"command": "add_connections_batch", "params": {"blueprint": "BP_HealthPickup", "connections": [
  {"src_node": "n1", "src_pin": "Then", "dst_node": "n3", "dst_pin": "execute"},
  {"src_node": "n3", "src_pin": "then", "dst_node": "n2", "dst_pin": "execute"}
]}}
```

### Step 4: Compile
```json
{"command": "compile_blueprint", "params": {"blueprint": "BP_HealthPickup"}}
```

## ALTERNATIVE: Single-command IR JSON via create_blueprint_from_dsl

## Blueprint DSL Format

## Structure
```
BLUEPRINT: BP_Name
PARENT: Actor|Character|Pawn|PlayerController|GameModeBase|AIController
VAR VariableName: Type = DefaultValue
GRAPH: EventGraph
NODE id: NodeType [Param=Value, Param="String Value"]
EXEC source_id.OutPin -> target_id.InPin
DATA source_id.OutPin -> target_id.InPin
```

## Rules
- Every Blueprint needs BLUEPRINT, PARENT, GRAPH lines
- Node IDs must be unique (use n1, n2, n3...)
- EXEC = execution flow (white wires), DATA = data flow (colored wires)
- String params use quotes: [InString="Hello World"]
- Numeric params are bare: [Duration=2.5]

## Variable Types
Bool, Int, Float, String, Vector, Rotator, Name, Text

## Common Node Types
Events: Event_BeginPlay, Event_ActorBeginOverlap, Event_Tick, Event_AnyDamage
Custom: CustomEvent (define), CallCustomEvent (call)
Flow: Branch, Sequence, ForLoop, WhileLoop, FlipFlop, DoOnce, Gate, MultiGate
Actions: PrintString, Delay, SpawnActorFromClass, DestroyActor, SetTimerByFunctionName
Movement: AddMovementInput, GetActorLocation, SetActorLocation, GetActorForwardVector
Math: Add, Subtract, Multiply, Divide, LessThan, GreaterThan, EqualEqual
Variables: VariableGet_X, VariableSet_X (where X is the variable name)
Arrays: Array_Add, Array_Contains, Array_Length, ForEachLoop
UI: CreateWidget, AddToViewport, RemoveFromParent, SetText
Physics: AddImpulse, AddForce, SetSimulatePhysics
Casting: CastTo_Character, CastTo_Pawn, IsValid
Input: InputAction_Jump, InputAction_Fire, InputAxisEvent_MoveForward

## Example 1: Simple Collectible
```
BLUEPRINT: BP_Coin
PARENT: Actor
VAR PointValue: Int = 10
GRAPH: EventGraph
NODE n1: Event_ActorBeginOverlap
NODE n2: DestroyActor
NODE n3: PrintString [InString="Coin collected!"]
EXEC n1.Then -> n3.Execute
EXEC n3.Then -> n2.Execute
```

## Example 2: Enemy with Health
```
BLUEPRINT: BP_Enemy
PARENT: Pawn
VAR Health: Float = 100.0
VAR IsDead: Bool = false
GRAPH: EventGraph
NODE n1: Event_AnyDamage
NODE n2: VariableGet_Health
NODE n3: Subtract
NODE n4: VariableSet_Health
NODE n5: LessThan
NODE n6: Branch
NODE n7: DestroyActor
NODE n8: PrintString [InString="Enemy died!"]
EXEC n1.Then -> n4.Execute
DATA n2.Health -> n3.A
DATA n1.Damage -> n3.B
DATA n3.ReturnValue -> n4.Health
EXEC n4.Then -> n6.Execute
DATA n4.Health -> n5.A
DATA n5.ReturnValue -> n6.Condition
EXEC n6.True -> n8.Execute
EXEC n8.Then -> n7.Execute
```

## Example 3: Spawner System
```
BLUEPRINT: BP_Spawner
PARENT: Actor
VAR SpawnCount: Int = 0
VAR MaxSpawns: Int = 5
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: SetTimerByFunctionName [FunctionName="DoSpawn", Time=3.0, bLooping=true]
NODE n3: CustomEvent [EventName="DoSpawn"]
NODE n4: VariableGet_SpawnCount
NODE n5: VariableGet_MaxSpawns
NODE n6: LessThan
NODE n7: Branch
NODE n8: SpawnActorFromClass
NODE n9: Add
NODE n10: VariableSet_SpawnCount
EXEC n1.Then -> n2.Execute
EXEC n3.Then -> n7.Execute
DATA n4.SpawnCount -> n6.A
DATA n5.MaxSpawns -> n6.B
DATA n6.ReturnValue -> n7.Condition
EXEC n7.True -> n8.Execute
EXEC n8.Then -> n10.Execute
DATA n4.SpawnCount -> n9.A
DATA n9.ReturnValue -> n10.SpawnCount
```

## CallFunction UFunction Path Reference
Format: /Script/<Module>.<Class>:<FunctionName>
The C++ auto-creates ALL pins from the UFunction signature. Just provide the path.

### System / Utility
/Script/Engine.KismetSystemLibrary:PrintString
/Script/Engine.KismetSystemLibrary:Delay
/Script/Engine.KismetSystemLibrary:SetTimerByFunctionName
/Script/Engine.KismetSystemLibrary:ClearTimerByFunctionName
/Script/Engine.KismetSystemLibrary:IsValid
/Script/Engine.KismetSystemLibrary:GetDisplayName
/Script/Engine.KismetSystemLibrary:LineTraceSingle

### Math (UE5 uses Double not Float)
/Script/Engine.KismetMathLibrary:Add_DoubleDouble
/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble
/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble
/Script/Engine.KismetMathLibrary:Divide_DoubleDouble
/Script/Engine.KismetMathLibrary:Clamp
/Script/Engine.KismetMathLibrary:RandomIntegerInRange
/Script/Engine.KismetMathLibrary:RandomFloatInRange
/Script/Engine.KismetMathLibrary:Lerp

### Comparison
/Script/Engine.KismetMathLibrary:Less_DoubleDouble
/Script/Engine.KismetMathLibrary:Greater_DoubleDouble
/Script/Engine.KismetMathLibrary:EqualEqual_DoubleDouble
/Script/Engine.KismetMathLibrary:EqualEqual_IntInt
/Script/Engine.KismetMathLibrary:BooleanAND
/Script/Engine.KismetMathLibrary:BooleanOR
/Script/Engine.KismetMathLibrary:Not_PreBool

### String
/Script/Engine.KismetStringLibrary:Concat_StrStr
/Script/Engine.KismetStringLibrary:Conv_IntToString
/Script/Engine.KismetStringLibrary:Conv_DoubleToString

### Actor
/Script/Engine.Actor:GetActorLocation
/Script/Engine.Actor:SetActorLocation
/Script/Engine.Actor:K2_DestroyActor
/Script/Engine.Actor:GetDistanceTo
/Script/Engine.Actor:SetActorHiddenInGame
/Script/Engine.Actor:SetLifeSpan
/Script/Engine.Actor:GetActorForwardVector

### Gameplay Statics
/Script/Engine.GameplayStatics:GetPlayerCharacter
/Script/Engine.GameplayStatics:GetPlayerController
/Script/Engine.GameplayStatics:ApplyDamage
/Script/Engine.GameplayStatics:PlaySoundAtLocation
/Script/Engine.GameplayStatics:SpawnEmitterAtLocation
/Script/Engine.GameplayStatics:GetAllActorsOfClass
/Script/Engine.GameplayStatics:GetWorldDeltaSeconds
/Script/Engine.GameplayStatics:OpenLevel
/Script/Engine.GameplayStatics:SaveGameToSlot
/Script/Engine.GameplayStatics:LoadGameFromSlot

### Physics
/Script/Engine.PrimitiveComponent:AddImpulse
/Script/Engine.PrimitiveComponent:AddForce
/Script/Engine.PrimitiveComponent:SetSimulatePhysics

### Character / Movement
/Script/Engine.Character:Jump
/Script/Engine.Character:LaunchCharacter
/Script/Engine.CharacterMovementComponent:SetMaxWalkSpeed

### AI
/Script/AIModule.AIController:MoveToLocation
/Script/AIModule.AIController:MoveToActor
/Script/AIModule.AIController:StopMovement
/Script/AIModule.AIController:RunBehaviorTree

### Widget / UI (Runtime)
/Script/UMG.UserWidget:AddToViewport
/Script/UMG.UserWidget:RemoveFromParent
/Script/UMG.TextBlock:SetText
/Script/UMG.ProgressBar:SetPercent

### Vector Math
/Script/Engine.KismetMathLibrary:MakeVector
/Script/Engine.KismetMathLibrary:BreakVector
/Script/Engine.KismetMathLibrary:Add_VectorVector
/Script/Engine.KismetMathLibrary:VSize
/Script/Engine.KismetMathLibrary:Normal
/Script/Engine.KismetMathLibrary:FindLookAtRotation

For the complete 200+ function path list, call get_arcwright_quickstart."""

@mcp.tool()
def get_behavior_tree_dsl_guide() -> str:
    """Get the Behavior Tree DSL format guide with examples.

    Call this before generating any BT DSL. Returns syntax, 2 examples,
    and all valid composite/task/decorator/service types.
    """
    return """# Arcwright Behavior Tree DSL Format

## Structure
```
BEHAVIORTREE: BT_Name
BLACKBOARD: BB_Name

KEY KeyName: Type

TREE:

COMPOSITE_TYPE: NodeName
  DECORATOR: Type [Param=Value]
  TASK: Type [Param=Value]
```

## Blackboard Key Types
Bool, Int, Float, String, Name, Vector, Rotator, Object, Class, Enum

## Composites (indent children under them)
Selector: tries children left-to-right, succeeds on first success
Sequence: runs children left-to-right, fails on first failure
SimpleParallel: runs main task and background tree simultaneously

## Tasks
MoveTo [Key=TargetKey, AcceptableRadius=100]
Wait [Duration=3.0]
RotateToFaceBBEntry [Key=TargetKey]
FinishWithResult [Result=Succeeded|Failed]
PlaySound, PlayAnimation, RunBehavior, MakeNoise
SetTagCooldown [Tag=Name, Duration=5.0]

## Decorators (attach to the composite's child entry)
BlackboardBased [Key=KeyName, Condition=IsSet|IsNotSet, AbortMode=LowerPriority|Self|Both]
Cooldown [Duration=5.0]
Loop [NumLoops=3]  (0 = infinite)
TimeLimit [Limit=10.0]
ForceSuccess, IsAtLocation, ConeCheck, CompareBBEntries

## Services (run periodically while parent is active)
DefaultFocus [Key=TargetKey]

## Example 1: Patrol and Chase
```
BEHAVIORTREE: BT_PatrolChase
BLACKBOARD: BB_PatrolChase

KEY TargetActor: Object
KEY PatrolLocation: Vector

TREE:

SELECTOR: Root
  SEQUENCE: Chase
    DECORATOR: BlackboardBased [Key=TargetActor, Condition=IsSet, AbortMode=LowerPriority]
    TASK: MoveTo [Key=TargetActor, AcceptableRadius=200]
  SEQUENCE: Patrol
    TASK: MoveTo [Key=PatrolLocation, AcceptableRadius=50]
    TASK: Wait [Duration=3.0]
```

## Example 2: Guard with Cooldown
```
BEHAVIORTREE: BT_Guard
BLACKBOARD: BB_Guard

KEY EnemyActor: Object
KEY GuardLocation: Vector

TREE:

SELECTOR: Root
  SEQUENCE: Attack
    DECORATOR: BlackboardBased [Key=EnemyActor, Condition=IsSet, AbortMode=Both]
    DECORATOR: Cooldown [Duration=2.0]
    TASK: RotateToFaceBBEntry [Key=EnemyActor]
    TASK: Wait [Duration=0.5]
  SEQUENCE: ReturnToPost
    TASK: MoveTo [Key=GuardLocation, AcceptableRadius=50]
    TASK: Wait [Duration=5.0]
```"""

@mcp.tool()
def get_data_table_dsl_guide() -> str:
    """Get the Data Table DSL format guide with examples.

    Call this before generating any DT DSL. Returns syntax, 2 examples,
    and all valid column types.
    """
    return """# Arcwright Data Table DSL Format

## Structure
```
DATATABLE: DT_Name
STRUCT: StructName

COLUMN ColumnName: Type = DefaultValue

ROW RowName: Col1=Value1, Col2=Value2
```

## Column Types
String, Float, Int, Boolean, Name, Text, Vector, Rotator, Transform, Color

## Default Values
- String: "text" or empty
- Float/Int: numeric (0.0, 100)
- Boolean: true/false
- Vector: (X=0,Y=0,Z=0)

## Example 1: Weapon Stats
```
DATATABLE: DT_Weapons
STRUCT: WeaponData

COLUMN Name: String
COLUMN Damage: Float = 0.0
COLUMN FireRate: Float = 1.0
COLUMN MaxAmmo: Int = 30
COLUMN IsAutomatic: Boolean = false

ROW Pistol: Name=Pistol, Damage=25.0, FireRate=2.0, MaxAmmo=12, IsAutomatic=false
ROW Rifle: Name=Rifle, Damage=15.0, FireRate=8.0, MaxAmmo=30, IsAutomatic=true
ROW Shotgun: Name=Shotgun, Damage=80.0, FireRate=0.8, MaxAmmo=8, IsAutomatic=false
```

## Example 2: Enemy Configuration
```
DATATABLE: DT_Enemies
STRUCT: EnemyConfig

COLUMN DisplayName: String
COLUMN Health: Float = 100.0
COLUMN Speed: Float = 300.0
COLUMN Damage: Float = 10.0
COLUMN XPReward: Int = 50

ROW Zombie: DisplayName=Zombie, Health=80.0, Speed=200.0, Damage=15.0, XPReward=25
ROW Skeleton: DisplayName=Skeleton, Health=60.0, Speed=400.0, Damage=10.0, XPReward=35
ROW Boss: DisplayName=Dark Knight, Health=500.0, Speed=250.0, Damage=50.0, XPReward=500
```"""

@mcp.tool()
def get_perception_dsl_guide() -> str:
    """Get the AI Perception DSL format guide. Free tier."""
    return """# Arcwright AI Perception DSL
```
PERCEPTION: APC_Name
@owner=BP_Character
SENSE: Sight
  @range=1500
  @fov=90
  @max_age=5.0
SENSE: Hearing
  @range=3000
SENSE: Damage
  @max_age=10.0
TEAM:
  @team_id=1
  @attitude_to_0=Hostile
```
Sense types: Sight, Hearing, Damage, Touch, Prediction"""

@mcp.tool()
def get_physics_dsl_guide() -> str:
    """Get the Physics Constraints DSL format guide. Free tier."""
    return """# Arcwright Physics DSL
```
PHYSICS: PHY_Name
@actor=BP_Actor
CONSTRAINT: HingeName
  @type=Hinge|Ball|Prismatic|Fixed
  @component1=PartA
  @component2=PartB
  @angle_min=-120
  @angle_max=0
  @breakable=true
  @break_threshold=5000
DESTRUCTIBLE: PartName
  @health=100
  @on_break=SpawnFragments:3
  @on_break=PlaySound:SFX_Break
```"""

@mcp.tool()
def get_tags_dsl_guide() -> str:
    """Get the Gameplay Tags DSL format guide. Free tier."""
    return """# Arcwright Gameplay Tags DSL
```
TAGS: GameplayTags
HIERARCHY: Ability
  Active
    Fire
    Ice
  Passive
    Buff
HIERARCHY: Status
  Burning
  Stunned
```
Indent = nesting. Ability.Active.Fire is auto-generated from the hierarchy."""

@mcp.tool()
def get_gas_dsl_guide() -> str:
    """Get the Gameplay Ability System DSL format guide. Free tier."""
    return """# Arcwright GAS (Gameplay Ability System) DSL

## Structure
```
ABILITY_SYSTEM: GAS_Name
@owner=BP_Character

ATTRIBUTE_SET: AS_Stats
  ATTRIBUTE: Health
    @base=100
    @min=0
    @max=100

ABILITY: GA_Name
  @display_name="Ability Name"
  @cooldown=2.0
  @cost_attribute=Mana
  @cost_amount=15
  @tags=Ability.Active.Fire
  EFFECT: EffectName
    @type=Instant|Duration
    @duration=5.0
    @target=Self|Enemy
    @tags_granted=Status.Burning
    @modifier=DamageMod
      @attribute=Health
      @operation=Add|Multiply|Override
      @magnitude=-50
      @scale_attribute=AttackPower
      @scale_factor=1.5
```

## Effect Types
Instant: applies once immediately
Duration: applies over time (@duration + @period for ticking)

## Modifier Operations
Add: attribute += magnitude (use negative for damage)
Multiply: attribute *= magnitude (2.0 = double speed)
Override: attribute = magnitude (0 = lock to zero)

## Example: Melee Fighter
```
ABILITY_SYSTEM: GAS_Fighter
ATTRIBUTE_SET: AS_Fighter
  ATTRIBUTE: Health
    @base=150
    @max=150
  ATTRIBUTE: Stamina
    @base=100
    @max=100

ABILITY: GA_Slash
  @cooldown=0.5
  @cost_attribute=Stamina
  @cost_amount=10
  EFFECT: SlashDamage
    @type=Instant
    @target=Enemy
    @modifier=Damage
      @attribute=Health
      @operation=Add
      @magnitude=-25
```"""

@mcp.tool()
def get_sequence_dsl_guide() -> str:
    """Get the Level Sequence (Cinematic) DSL format guide. Free tier."""
    return """# Arcwright Sequence DSL Format

## Structure
```
SEQUENCE: LS_Name
@duration=10.0
@framerate=30

CAMERA: CameraName
  @fov=70
  KEYFRAME: 0.0
    @location=X,Y,Z
    @rotation=P,Y,R
    @fov=70
  KEYFRAME: 5.0
    @location=X,Y,Z

ACTOR: ActorName
  @binding=ActorLabel
  TRACK: Transform
    KEYFRAME: 0.0
      @location=X,Y,Z
    KEYFRAME: 3.0
      @rotation=P,Y,R

AUDIO: TrackName
  @sound=SoundAssetPath
  @volume=0.8
  @fade_in=2.0

FADE:
  KEYFRAME: 0.0
    @opacity=1.0
  KEYFRAME: 1.0
    @opacity=0.0

EVENT: 5.0
  @action=PlaySound:SFX_Name
```

## Example: Simple Camera Pan
```
SEQUENCE: LS_LevelIntro
@duration=5.0

CAMERA: MainCam
  KEYFRAME: 0.0
    @location=0,0,500
    @rotation=-45,0,0
  KEYFRAME: 5.0
    @location=500,0,200
    @rotation=-15,0,45
```"""

@mcp.tool()
def get_quest_dsl_guide() -> str:
    """Get the Quest System DSL format guide. Free tier."""
    return """# Arcwright Quest DSL Format

## Structure
```
QUEST: Q_Name
@title="Quest Title"
@description="What the player needs to do"
@giver=NPC_Name
@category=Main|Side|Daily
@reward_xp=100
@reward_gold=50

STAGE: StageName
  @description="Stage description"
  @type=Collect|TalkTo|Kill|Explore|Wait|Custom
  OBJECTIVE: ObjectiveID
    @text="What to do"
    @target=TargetName
    @count=3
    @optional=true

ON_COMPLETE:
  @set_flag=QuestDone
  @unlock_quest=Q_NextQuest

ON_ABANDON:
  @return_items=true
```

## Objective Types
Collect: gather items (@target=ItemName, @count=N)
TalkTo: speak to NPC (@target=NPCName)
Kill: defeat enemies (@target=EnemyClass, @count=N)
Explore: reach location (@target=LocationName)
Wait: time-based (@seconds=N)

## Example: Fetch Quest
```
QUEST: Q_HerbGathering
@title="Herbal Remedy"
@giver=NPC_Healer
@reward_xp=50

STAGE: GatherHerbs
  @type=Collect
  OBJECTIVE: GetHerbs
    @text="Gather Moonpetal Flowers"
    @target=Item_Moonpetal
    @count=5

STAGE: ReturnToHealer
  @type=TalkTo
  OBJECTIVE: Deliver
    @text="Bring herbs to the Healer"
    @target=NPC_Healer

ON_COMPLETE:
  @set_flag=HerbQuestDone
```"""

@mcp.tool()
def get_dialogue_dsl_guide() -> str:
    """Get the Dialogue Tree DSL format guide. Free tier."""
    return """# Arcwright Dialogue DSL Format

## Structure
```
DIALOGUE: DLG_Name
@speaker_default=NPC_Name

NODE: NodeID
  @speaker=CharacterName
  @text="What the character says"
  @condition=FlagName
  @set_flag=FlagName
  @action=ActionName
  @next=NextNodeID
  CHOICE: "Player response text"
    @next=TargetNodeID
    @condition=OptionalCondition
```

## Rules
- Each NODE has a unique ID
- @next=END terminates the conversation
- @condition checks game flags (NOT FlagName for negation)
- @set_flag sets a persistent flag
- @action triggers game events (OpenShopUI, StartQuest:QuestName)
- CHOICEs are player response options with their own @next targets
- First NODE is the entry point

## Example: Simple Merchant
```
DIALOGUE: DLG_Merchant
@speaker_default=Merchant

NODE: Greeting
  @speaker=Merchant
  @text="Welcome! Care to browse my wares?"
  CHOICE: "Show me what you have."
    @next=Shop
  CHOICE: "Not today."
    @next=Goodbye

NODE: Shop
  @text="Take your time!"
  @action=OpenShopUI
  @next=END

NODE: Goodbye
  @text="Come back anytime!"
  @next=END
```"""

@mcp.tool()
def get_material_dsl_guide() -> str:
    """Get the Material Graph DSL format guide with examples. Free tier."""
    return """# Arcwright Material Graph DSL Format

## Structure
```
MATERIAL: M_Name
@domain=Surface
@blend_mode=Opaque
@shading_model=DefaultLit

NODE_TYPE: NodeName
  @param=value

OUTPUT:
  @BaseColor=NodeName
  @Roughness=NodeName
  @Metallic=NodeName
  @Normal=NodeName
```

## Node Types
CONSTANT (float), CONSTANT3 (RGB), CONSTANT4 (RGBA)
SCALAR_PARAM, VECTOR_PARAM, TEXTURE_SAMPLE, TEXTURE_PARAM
MULTIPLY, ADD, SUBTRACT, DIVIDE, LERP, CLAMP, POWER, ABS, ONE_MINUS
FRESNEL, PANNER, TEX_COORD, TIME, NOISE, DESATURATION, MASK, APPEND

## Connection Syntax
@A=SourceNode (or @A=SourceNode.RGB for channel)
@B=SourceNode
@Alpha=SourceNode (for LERP)

## Example: Simple PBR Metal
```
MATERIAL: M_BrushedMetal
VECTOR_PARAM: BaseColor
  @default=0.7,0.7,0.75
SCALAR_PARAM: Roughness
  @default=0.3
SCALAR_PARAM: Metallic
  @default=1.0
OUTPUT:
  @BaseColor=BaseColor
  @Roughness=Roughness
  @Metallic=Metallic
```"""

@mcp.tool()
def get_animation_dsl_guide() -> str:
    """Get the Animation Blueprint DSL format guide with examples.

    Call this before generating any Animation DSL. Returns syntax, examples,
    and valid node types for state machines, transitions, blend spaces, and montages.
    """
    return """# Arcwright Animation Blueprint DSL Format

## Structure
```
ANIMBP: ABP_Name
SKELETON: /Game/Path/To/SkeletalMesh
MESH: /Game/Path/To/SkeletalMesh

VARIABLES:
  Speed: Float = 0.0
  IsJumping: Bool = false

STATE_MACHINE: MachineName
  STATE: StateName
    @entry: true
    @animation: /Game/Path/To/Animation
    @loop: true
  TRANSITION: StateA -> StateB
    @condition: Speed > 0
    @blend_duration: 0.2

BLEND_SPACE: BS_Name
  @type: 1D
  @axis_x: Speed
  @axis_x_min: 0
  @axis_x_max: 600
  SAMPLE: position=0 animation=/Game/Path/Idle
  SAMPLE: position=600 animation=/Game/Path/Run

MONTAGE: AM_Name
  @animation: /Game/Path/To/Animation
  @slot: DefaultSlot
```

## Example: Simple Locomotion
```
ANIMBP: ABP_Character
SKELETON: /Game/Characters/Mannequins/Meshes/SKM_Manny

VARIABLES:
  Speed: Float = 0.0

STATE_MACHINE: Locomotion
  STATE: Idle
    @entry: true
    @animation: /Game/Characters/Mannequins/Animations/MM_Idle
    @loop: true
  STATE: Walk
    @animation: /Game/Characters/Mannequins/Animations/MM_Walk_Fwd
  STATE: Run
    @animation: /Game/Characters/Mannequins/Animations/MM_Run_Fwd
  TRANSITION: Idle -> Walk
    @condition: Speed > 0
    @blend_duration: 0.2
  TRANSITION: Walk -> Run
    @condition: Speed >= 300
    @blend_duration: 0.15
  TRANSITION: Walk -> Idle
    @condition: Speed == 0
    @blend_duration: 0.25
```

## Valid Types
States: @animation (asset path), @loop (bool), @entry (bool)
Transitions: @condition (expression), @blend_duration (float)
Blend Space: @type (1D/2D), @axis_x/y (name, min, max)
Montage: @animation, @slot (DefaultSlot), notifies
Layer: @bone_mask (bone name), @slot, @blend_mode (Override/Additive)"""

@mcp.tool()
def get_arcwright_quickstart() -> str:
    """Get the Arcwright AI Best Practices guide — the MOST IMPORTANT reference for building games.

    Call this FIRST in every session. Returns the complete guide covering:
    - Blueprint creation workflow (create_blueprint -> add_nodes_batch -> add_connections_batch)
    - 200+ UFunction paths for CallFunction nodes
    - Widget UI creation, Data Table creation
    - Common mistakes to avoid, debugging tips
    - Default event handling (Event_ prefix rules)

    ALSO READ: Call get_check_and_confirm_guide() for the verification protocol.
    The Check & Confirm SOP tells you how to verify every action you take.

    After every phase, verify with: verify_all_blueprints, get_level_snapshot, play_test.
    After everything, run the QA Tour: teleport_to_actor for each key actor, get_player_view.
    """
    guide_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ARCWRIGHT_AI_GUIDE.md")
    if os.path.isfile(guide_path):
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Guide file not found. See scripts/ARCWRIGHT_AI_GUIDE.md in the plugin directory."


@mcp.tool()
def get_check_and_confirm_guide() -> str:
    """Get the Check & Confirm Standard Operating Procedure.

    This SOP defines the verification protocol for every action:
    - After creating a Blueprint: inspect with get_blueprint_graph, verify node/connection counts
    - After building a level: inspect with get_level_snapshot, verify actor positions
    - After all phases: run verify_all_blueprints, play_test, and QA Tour
    - QA Tour: teleport_to_actor for each station, get_player_view screenshots, analyze brightness

    Inspection commands available:
    - get_blueprint_graph(name) — full node graph with connections
    - get_compile_status(name) — compile result with error messages
    - verify_all_blueprints() — batch compile all Blueprints
    - get_level_snapshot() — level name, actor count, class breakdown
    - get_actor_details(actor_label) — position, rotation, scale, components
    - get_player_view(filename) — screenshot from player POV during PIE
    - teleport_player(x,y,z) — move player during PIE
    - teleport_to_actor(actor,distance) — teleport near an actor, face it
    - look_at(x,y,z) or look_at(actor) — rotate camera to face target
    - get_player_location() — current player position and rotation
    - is_playing() — check if PIE is active

    Call this after get_arcwright_quickstart to learn the full verification workflow.
    """
    sop_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "CHECK_AND_CONFIRM.md")
    if os.path.isfile(sop_path):
        with open(sop_path, "r", encoding="utf-8") as f:
            return f.read()
    return "SOP file not found. See scripts/CHECK_AND_CONFIRM.md in the plugin directory."

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if "--test" in sys.argv:
        # Quick self-test: connect, health_check, list tools
        print("Arcwright MCP Server — Self Test")
        print("=" * 50)
        print(f"Target: {UE_HOST}:{UE_PORT}")
        print(f"Tools registered: {len(mcp._tool_manager._tools)}")
        for name in sorted(mcp._tool_manager._tools.keys()):
            print(f"  - {name}")
        print()
        print("Testing health_check...")
        result = health_check()
        print(result)
        print()
        print("Self-test complete.")
    else:
        log.info("Arcwright MCP Server starting (stdio mode)")
        log.info(f"UE target: {UE_HOST}:{UE_PORT}")
        mcp.run(transport="stdio")
