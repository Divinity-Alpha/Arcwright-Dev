"""
Arcwright TCP Client Library.

Connects to the Arcwright Command Server running inside UE5 Editor
on localhost:13377. Sends JSON commands and receives JSON responses.

Usage:
    from blueprint_client import ArcwrightClient

    client = ArcwrightClient()
    result = client.health_check()
    print(result)

    result = client.import_from_ir("C:/Arcwright/test_ir/T1_01_HelloWorld.blueprint.json")
    print(result)

    client.close()
"""

import socket
import json
import time
from typing import Optional


class BlueprintLLMError(Exception):
    """Raised when the server returns an error response."""
    pass


class ArcwrightClient:
    def __init__(self, host: str = "localhost", port: int = 13377, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self._buffer = b""

    def send_command(self, command: str, params: Optional[dict] = None) -> dict:
        """Send a command and return the parsed response dict."""
        msg = json.dumps({"command": command, "params": params or {}})
        self.sock.sendall((msg + "\n").encode("utf-8"))
        response = self._read_response()
        parsed = json.loads(response)
        if parsed.get("status") == "error":
            raise BlueprintLLMError(parsed.get("message", "Unknown error"))
        return parsed

    def _read_response(self) -> str:
        """Read a newline-terminated JSON response."""
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("Server closed connection")
            self._buffer += chunk

        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode("utf-8").strip()

    # ---- High-level commands ----

    def health_check(self) -> dict:
        """Check server health. Returns server info."""
        return self.send_command("health_check")

    def import_from_ir(self, ir_path: str) -> dict:
        """Import a .blueprint.json IR file into UE5.

        Args:
            ir_path: Absolute path to the IR file.

        Returns:
            dict with status, data containing blueprint_name, nodes_created,
            connections_wired, compiled, etc.
        """
        return self.send_command("import_from_ir", {"path": ir_path})

    def get_blueprint_info(self, name: str) -> dict:
        """Query an existing Blueprint's full structure.

        Args:
            name: Blueprint asset name (e.g. "BP_HelloWorld").

        Returns:
            dict with nodes, connections, variables, compiled status.
        """
        return self.send_command("get_blueprint_info", {"name": name})

    def compile_blueprint(self, name: str) -> dict:
        """Recompile a Blueprint.

        Args:
            name: Blueprint asset name.

        Returns:
            dict with compiled status.
        """
        return self.send_command("compile_blueprint", {"name": name})

    def delete_blueprint(self, name: str) -> dict:
        """Delete a Blueprint asset.

        Args:
            name: Blueprint asset name.

        Returns:
            dict with deleted status.
        """
        return self.send_command("delete_blueprint", {"name": name})

    # ---- Level actor commands ----

    def spawn_actor_at(self, actor_class: str = "", location: Optional[dict] = None,
                       rotation: Optional[dict] = None, scale: Optional[dict] = None,
                       label: Optional[str] = None) -> dict:
        """Spawn an actor in the editor level.

        Args:
            actor_class: Native class name (e.g. "StaticMeshActor") or
                        Blueprint path (e.g. "/Game/Arcwright/Generated/BP_Hello").
            location: {x, y, z} dict. Defaults to origin.
            rotation: {pitch, yaw, roll} dict. Defaults to zero.
            scale: {x, y, z} dict. Defaults to (1,1,1).
            label: Display label in Outliner. Auto-generated if omitted.

        Returns:
            dict with label, class, location, rotation, scale.
        """
        params = {"class": actor_class}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        if label is not None:
            params["label"] = label
        return self.send_command("spawn_actor_at", params)

    def get_actors(self, class_filter: Optional[str] = None) -> dict:
        """List actors in the editor level.

        Args:
            class_filter: Optional case-insensitive substring to filter by class name.

        Returns:
            dict with count and actors array.
        """
        params = {}
        if class_filter is not None:
            params["class_filter"] = class_filter
        return self.send_command("get_actors", params)

    def set_actor_transform(self, label: str, location: Optional[dict] = None,
                            rotation: Optional[dict] = None,
                            scale: Optional[dict] = None) -> dict:
        """Update an actor's transform. Only provided fields are changed.

        Args:
            label: Actor label in Outliner.
            location: {x, y, z} dict.
            rotation: {pitch, yaw, roll} dict.
            scale: {x, y, z} dict.

        Returns:
            dict with resulting label, location, rotation, scale.
        """
        params = {"label": label}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        return self.send_command("set_actor_transform", params)

    def delete_actor(self, label: str) -> dict:
        """Delete an actor from the level by label. Idempotent.

        Args:
            label: Actor label in Outliner.

        Returns:
            dict with label and deleted (true/false).
        """
        return self.send_command("delete_actor", {"label": label})

    # ---- Individual node/connection editing (B5+B6) ----

    def add_node(self, blueprint: str, node_type: str, node_id: str = "",
                 params: Optional[dict] = None,
                 pos_x: float = 0, pos_y: float = 0) -> dict:
        """Add a single node to an existing Blueprint's EventGraph.

        Args:
            blueprint: Blueprint asset name (e.g. "BP_HelloWorld").
            node_type: DSL node type (e.g. "Delay", "Branch", "PrintString").
            node_id: Optional ID for the node. Auto-generated if empty.
            params: Optional dict of pin default values (e.g. {"Duration": "2.0"}).
            pos_x: Graph X position.
            pos_y: Graph Y position.

        Returns:
            dict with node_id (GUID), node_type, class, pins, compiled.
        """
        cmd_params = {"blueprint": blueprint, "node_type": node_type}
        if node_id:
            cmd_params["node_id"] = node_id
        if params:
            cmd_params["params"] = params
        if pos_x != 0:
            cmd_params["pos_x"] = pos_x
        if pos_y != 0:
            cmd_params["pos_y"] = pos_y
        return self.send_command("add_node", cmd_params)

    def remove_node(self, blueprint: str, node_id: str) -> dict:
        """Remove a node from a Blueprint. Also removes all its connections.

        Args:
            blueprint: Blueprint asset name.
            node_id: Node GUID or index (e.g. "node_3" from get_blueprint_info).

        Returns:
            dict with node_id, deleted, compiled.
        """
        return self.send_command("remove_node", {
            "blueprint": blueprint,
            "node_id": node_id,
        })

    def add_connection(self, blueprint: str, source_node: str, source_pin: str,
                       target_node: str, target_pin: str) -> dict:
        """Wire two pins together. Uses TryCreateConnection for auto-conversion.

        Args:
            blueprint: Blueprint asset name.
            source_node: Source node GUID or index.
            source_pin: Source pin name (DSL aliases supported).
            target_node: Target node GUID or index.
            target_pin: Target pin name (DSL aliases supported).

        Returns:
            dict with connected, source/target details, compiled.
        """
        return self.send_command("add_connection", {
            "blueprint": blueprint,
            "source_node": source_node,
            "source_pin": source_pin,
            "target_node": target_node,
            "target_pin": target_pin,
        })

    def remove_connection(self, blueprint: str, source_node: str, source_pin: str,
                          target_node: str, target_pin: str) -> dict:
        """Disconnect two pins.

        Args:
            blueprint: Blueprint asset name.
            source_node: Source node GUID or index.
            source_pin: Source pin name (DSL aliases supported).
            target_node: Target node GUID or index.
            target_pin: Target pin name (DSL aliases supported).

        Returns:
            dict with disconnected, source/target details, compiled.
        """
        return self.send_command("remove_connection", {
            "blueprint": blueprint,
            "source_node": source_node,
            "source_pin": source_pin,
            "target_node": target_node,
            "target_pin": target_pin,
        })

    def add_nodes_batch(self, blueprint: str, nodes: list) -> dict:
        """Add multiple nodes in one call. Fault-tolerant: each node succeeds/fails independently.
        Single compile at end.

        Args:
            blueprint: Blueprint asset name.
            nodes: List of node defs, each: {"node_type": "...", "node_id": "...", "params": {...}, "pos_x": 0, "pos_y": 0}

        Returns:
            dict with succeeded, failed, total, compiled, results[] (per-node with success/error/pins).
        """
        return self.send_command("add_nodes_batch", {
            "blueprint": blueprint,
            "nodes": nodes,
        })

    def add_connections_batch(self, blueprint: str, connections: list) -> dict:
        """Wire multiple connections in one call. Fault-tolerant: each connection succeeds/fails independently.
        Single compile at end. On pin-not-found, returns available_source_pins or available_target_pins.

        Args:
            blueprint: Blueprint asset name.
            connections: List of connection defs, each:
                {"source_node": "...", "source_pin": "...", "target_node": "...", "target_pin": "..."}

        Returns:
            dict with succeeded, failed, total, compiled, results[] (per-connection with success/error/pin details).
        """
        return self.send_command("add_connections_batch", {
            "blueprint": blueprint,
            "connections": connections,
        })

    def validate_blueprint(self, name: str) -> dict:
        """Check a Blueprint for common issues without modifying it.

        Checks: unconnected exec inputs, orphan nodes, unconnected data inputs, compile status.

        Args:
            name: Blueprint asset name.

        Returns:
            dict with valid (bool), error_count, warning_count, info_count, issues[] (each with severity/type/message).
        """
        return self.send_command("validate_blueprint", {"name": name})

    def get_capabilities(self) -> dict:
        """Get a summary of all Arcwright capabilities.

        Returns:
            dict with tcp_commands count, mcp_tools count, categories with command lists, version info.
        """
        return self.send_command("get_capabilities")

    def get_stats(self) -> dict:
        """Get Arcwright usage statistics (session + lifetime).

        Returns:
            dict with session stats (commands, blueprints, actors, duration)
            and lifetime stats (totals, success rate, time saved, first use date).
        """
        return self.send_command("get_stats")

    def reset_stats(self, scope: str = "session") -> dict:
        """Reset Arcwright usage statistics.

        Args:
            scope: "session" to reset current session stats, "lifetime" to reset all persistent stats.
        """
        return self.send_command("reset_stats", {"scope": scope})

    def get_node_reference(self, node_type: str) -> dict:
        """Get complete reference for a Blueprint node type.

        Returns category, description, input/output pins with types and descriptions.
        Uses local DSL reference data (no TCP roundtrip needed).

        Args:
            node_type: Node type name (e.g. "SetTimerByFunctionName", "Branch", "ForLoop").
                       Aliases and CastTo<X> patterns are resolved automatically.

        Returns:
            dict with node_type, category, description, input_pins[], output_pins[], aliases[].
            Each pin has: name, type, description.

        Raises:
            BlueprintLLMError: If node type is unknown.
        """
        import sys as _sys, os as _os
        _scripts = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
        if _scripts not in _sys.path:
            _sys.path.insert(0, _scripts)
        from node_reference import get_reference
        ref = get_reference(node_type)
        if ref is None:
            raise BlueprintLLMError(f"Unknown node type: {node_type}")
        return {"status": "ok", "data": ref}

    def list_node_types(self, category: str = None) -> dict:
        """List all available Blueprint node types organized by category.

        Uses local DSL reference data (no TCP roundtrip needed).

        Args:
            category: Optional category filter (e.g. "Events", "Flow Control").
                      If None, returns all categories.

        Returns:
            dict with total_types count and categories dict mapping category names
            to lists of {node_type, description}.
        """
        import sys as _sys, os as _os
        _scripts = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
        if _scripts not in _sys.path:
            _sys.path.insert(0, _scripts)
        from node_reference import list_types
        result = list_types()
        if category:
            filtered = {k: v for k, v in result["categories"].items() if k == category}
            count = sum(len(v) for v in filtered.values())
            result = {"total_types": count, "categories": filtered}
        return {"status": "ok", "data": result}

    def set_node_param(self, blueprint: str, node_id: str,
                       pin_name: str, value: str) -> dict:
        """Set a pin's default value on a node.

        Args:
            blueprint: Blueprint asset name.
            node_id: Node GUID or index.
            pin_name: Pin name (DSL aliases supported).
            value: String value to set.

        Returns:
            dict with node_id, pin_name, value, compiled.
        """
        return self.send_command("set_node_param", {
            "blueprint": blueprint,
            "node_id": node_id,
            "pin_name": pin_name,
            "value": value,
        })

    def set_variable_default(self, blueprint: str, variable_name: str,
                             default_value: str) -> dict:
        """Set a Blueprint variable's default value.

        Args:
            blueprint: Blueprint asset name.
            variable_name: Variable name.
            default_value: Default value as string.

        Returns:
            dict with variable_name, default_value, type, compiled.
        """
        return self.send_command("set_variable_default", {
            "blueprint": blueprint,
            "variable_name": variable_name,
            "default_value": default_value,
        })

    # ---- Component management ----

    def add_component(self, blueprint: str, component_type: str,
                      component_name: str, parent: str = "",
                      properties: Optional[dict] = None) -> dict:
        """Add a component to a Blueprint's SimpleConstructionScript.

        Args:
            blueprint: Blueprint asset name (e.g. "BP_Pickup").
            component_type: Friendly type name. Supported:
                BoxCollision, SphereCollision, CapsuleCollision,
                StaticMesh, PointLight, SpotLight, Audio, Arrow, Scene.
            component_name: Name for the new component.
            parent: Optional parent component name. Attaches to root if empty.
            properties: Optional dict of component-specific properties.
                Box: extent={x,y,z}, generate_overlap_events=bool, collision_profile=str
                Sphere: radius=float, generate_overlap_events=bool
                Capsule: radius=float, half_height=float
                StaticMesh: mesh=str (asset path)
                Light: intensity=float, light_color={r,g,b}, attenuation_radius=float
                All: location={x,y,z}, rotation={pitch,yaw,roll}, scale={x,y,z}

        Returns:
            dict with component_name, component_class, parent, compiled.
        """
        params = {
            "blueprint": blueprint,
            "component_type": component_type,
            "component_name": component_name,
        }
        if parent:
            params["parent"] = parent
        if properties:
            params["properties"] = properties
        return self.send_command("add_component", params)

    def get_components(self, blueprint: str) -> dict:
        """List all components in a Blueprint's SimpleConstructionScript.

        Args:
            blueprint: Blueprint asset name.

        Returns:
            dict with count and components array (name, class, parent).
        """
        return self.send_command("get_components", {"blueprint": blueprint})

    def remove_component(self, blueprint: str, component_name: str) -> dict:
        """Remove a component from a Blueprint. Idempotent (missing = ok).

        Args:
            blueprint: Blueprint asset name.
            component_name: Name of the component to remove.

        Returns:
            dict with component_name, deleted (bool), compiled (bool).
        """
        return self.send_command("remove_component", {
            "blueprint": blueprint,
            "component_name": component_name,
        })

    def set_component_property(self, blueprint: str, component_name: str,
                               property_name: str, value) -> dict:
        """Set a property on an existing Blueprint component.

        Args:
            blueprint: Blueprint asset name.
            component_name: Component name in the SCS.
            property_name: Property to set. Supported:
                Any: relative_location, relative_rotation, relative_scale, visibility
                StaticMesh: static_mesh (asset path)
                Box: box_extent, generate_overlap_events, collision_profile_name
                Sphere: sphere_radius, generate_overlap_events
                Light: intensity, light_color, attenuation_radius
                Collision: collision_enabled, collision_profile_name
            value: Property value. Type depends on property:
                Vectors: {"x": 0, "y": 0, "z": 0}
                Rotators: {"pitch": 0, "yaw": 0, "roll": 0}
                Colors: {"r": 1, "g": 0, "b": 0}
                Floats: 5000.0
                Bools: True/False
                Strings: "OverlapAllDynamic"

        Returns:
            dict with component_name, property_name, compiled.
        """
        return self.send_command("set_component_property", {
            "blueprint": blueprint,
            "component_name": component_name,
            "property_name": property_name,
            "value": value,
        })

    # ---- Material commands ----

    def create_material_instance(self, name: str, parent: str,
                                  scalar_params: Optional[dict] = None,
                                  vector_params: Optional[dict] = None) -> dict:
        """Create a MaterialInstanceConstant asset in UE.

        Args:
            name: Asset name (e.g. "MI_GoldPickup").
            parent: Parent material path (e.g. "/Engine/BasicShapes/BasicShapeMaterial").
            scalar_params: Optional dict of scalar parameter overrides.
            vector_params: Optional dict of vector parameter overrides (each {r,g,b,a}).

        Returns:
            dict with name, asset_path, parent, scalar_params_set, vector_params_set.
        """
        params = {"name": name, "parent": parent}
        if scalar_params:
            params["scalar_params"] = scalar_params
        if vector_params:
            params["vector_params"] = vector_params
        return self.send_command("create_material_instance", params)

    def create_simple_material(self, name: str, color: dict,
                               emissive_strength: float = 0.0) -> dict:
        """Create a UMaterial with a solid color (Substrate-compatible).

        Unlike create_material_instance, this creates a full UMaterial with
        UMaterialExpressionConstant3Vector nodes, which works with UE 5.7's
        Substrate rendering system.

        Args:
            name: Asset name (e.g. "MAT_Green").
            color: {r, g, b} color values (0-1 range).
            emissive_strength: Optional emissive multiplier (0 = no glow).

        Returns:
            dict with name, asset_path, color, emissive_strength.
        """
        params = {"name": name, "color": color}
        if emissive_strength > 0.0:
            params["emissive_strength"] = emissive_strength
        return self.send_command("create_simple_material", params)

    def create_textured_material(self, name: str, texture_path: str,
                                  roughness: float = 0.5, metallic: float = 0.0,
                                  tiling: float = 1.0) -> dict:
        """Create a UMaterial with a texture sample node connected to BaseColor.

        texture_path can be a full UE asset path (e.g. "/Game/Arcwright/Textures/T_StoneWall")
        or a friendly name from the texture library (e.g. "stone_wall").

        Args:
            name: Asset name (e.g. "MAT_StoneWall").
            texture_path: UE asset path OR texture library friendly name.
            roughness: Roughness value (0-1, default 0.5).
            metallic: Metallic value (0-1, default 0.0).
            tiling: UV tiling multiplier (default 1.0).

        Returns:
            dict with name, asset_path, texture.
        """
        if not texture_path.startswith("/"):
            from scripts.texture_library import resolve_texture
            resolved = resolve_texture(texture_path)
            if resolved:
                texture_path = resolved
        params = {"name": name, "texture_path": texture_path,
                  "roughness": roughness, "metallic": metallic, "tiling": tiling}
        return self.send_command("create_textured_material", params)

    def apply_material(self, blueprint: str, component_name: str,
                       material_path: str, slot_index: int = 0) -> dict:
        """Apply a material to a Blueprint's mesh/primitive component.

        Args:
            blueprint: Blueprint asset name.
            component_name: Component name in the SCS.
            material_path: Material asset path (e.g. "/Game/Arcwright/Materials/MI_Gold").
            slot_index: Material slot index (default 0).

        Returns:
            dict with blueprint, component_name, material_path, slot_index, compiled.
        """
        return self.send_command("apply_material", {
            "blueprint": blueprint,
            "component_name": component_name,
            "material_path": material_path,
            "slot_index": slot_index,
        })

    # ---- Save / level info / duplicate ----

    def save_all(self) -> dict:
        """Save all dirty packages (assets + level)."""
        return self.send_command("save_all")

    def save_level(self) -> dict:
        """Save the current level."""
        return self.send_command("save_level")

    def get_level_info(self) -> dict:
        """Get level name, path, actor count, class types, player start."""
        return self.send_command("get_level_info")

    def duplicate_blueprint(self, source_name: str, new_name: str) -> dict:
        """Duplicate an existing Blueprint to a new name.

        Args:
            source_name: Source Blueprint asset name.
            new_name: Name for the duplicate.

        Returns:
            dict with source_name, new_name, asset_path, compiled.
        """
        return self.send_command("duplicate_blueprint", {
            "source_name": source_name,
            "new_name": new_name,
        })

    # ---- PIE + log ----

    def play_in_editor(self) -> dict:
        """Start a Play In Editor (PIE) session."""
        return self.send_command("play_in_editor")

    def stop_play(self) -> dict:
        """Stop the current PIE session. Idempotent."""
        return self.send_command("stop_play")

    def get_output_log(self, last_n_lines: int = 50,
                       category: Optional[str] = None,
                       text_filter: Optional[str] = None) -> dict:
        """Read the UE output log.

        Args:
            last_n_lines: Number of lines to return (default 50).
            category: Filter by log category (e.g. "LogBlueprintUserMessages").
            text_filter: Filter by text substring.

        Returns:
            dict with lines array, total/filtered/returned counts.
        """
        params = {"last_n_lines": last_n_lines}
        if category:
            params["category"] = category
        if text_filter:
            params["text_filter"] = text_filter
        return self.send_command("get_output_log", params)

    # ---- Input mapping commands (B29) ----

    def setup_input_context(self, name: str) -> dict:
        """Create a UInputMappingContext asset."""
        return self.send_command("setup_input_context", {"name": name})

    def add_input_action(self, name: str, value_type: str = "bool") -> dict:
        """Create a UInputAction asset.

        Args:
            name: Action name (e.g. "IA_Jump").
            value_type: "bool", "axis1d", "axis2d", or "axis3d".
        """
        return self.send_command("add_input_action", {
            "name": name, "value_type": value_type
        })

    def add_input_mapping(self, context: str, action: str, key: str) -> dict:
        """Add a key mapping to an input mapping context.

        Args:
            context: Context name or asset path.
            action: Action name or asset path.
            key: Key name (e.g. "SpaceBar", "E", "W").
        """
        return self.send_command("add_input_mapping", {
            "context": context, "action": action, "key": key
        })

    def get_input_actions(self, path: str = "") -> dict:
        """List all UInputAction assets."""
        params = {}
        if path:
            params["path"] = path
        return self.send_command("get_input_actions", params)

    # ---- Audio commands (B24) ----

    def play_sound_at_location(self, sound: str, location: dict,
                                volume: float = 1.0, pitch: float = 1.0) -> dict:
        """Play a sound at a world location (fire-and-forget)."""
        return self.send_command("play_sound_at_location", {
            "sound": sound, "location": location,
            "volume": volume, "pitch": pitch,
        })

    def add_audio_component(self, blueprint: str, name: str = "Audio",
                             sound: str = "", auto_activate: bool = True) -> dict:
        """Add a UAudioComponent to a Blueprint's SCS."""
        params = {"blueprint": blueprint, "name": name,
                  "auto_activate": auto_activate}
        if sound:
            params["sound"] = sound
        return self.send_command("add_audio_component", params)

    def get_sound_assets(self, path: str = "/Game",
                          search_subfolders: bool = True) -> dict:
        """List available sound assets."""
        return self.send_command("get_sound_assets", {
            "path": path, "search_subfolders": search_subfolders
        })

    # ---- Viewport commands (B30) ----

    def set_viewport_camera(self, location: Optional[dict] = None,
                             rotation: Optional[dict] = None) -> dict:
        """Move the editor viewport camera."""
        params = {}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        return self.send_command("set_viewport_camera", params)

    def take_screenshot(self, filename: str = "") -> dict:
        """Capture the editor viewport to a PNG file."""
        params = {}
        if filename:
            params["filename"] = filename
        return self.send_command("take_screenshot", params)

    def get_viewport_info(self) -> dict:
        """Get current viewport camera position and settings."""
        return self.send_command("get_viewport_info")

    # ---- Niagara commands (B25) ----

    def spawn_niagara_at_location(self, system: str, location: dict,
                                   rotation: Optional[dict] = None,
                                   auto_destroy: bool = True) -> dict:
        """Spawn a Niagara particle system in the world."""
        params = {"system": system, "location": location,
                  "auto_destroy": auto_destroy}
        if rotation is not None:
            params["rotation"] = rotation
        return self.send_command("spawn_niagara_at_location", params)

    def add_niagara_component(self, blueprint: str, name: str = "Niagara",
                               system: str = "",
                               auto_activate: bool = True) -> dict:
        """Add a UNiagaraComponent to a Blueprint's SCS."""
        params = {"blueprint": blueprint, "name": name,
                  "auto_activate": auto_activate}
        if system:
            params["system"] = system
        return self.send_command("add_niagara_component", params)

    def get_niagara_assets(self, path: str = "/Game",
                            search_subfolders: bool = True) -> dict:
        """List available Niagara system assets."""
        return self.send_command("get_niagara_assets", {
            "path": path, "search_subfolders": search_subfolders
        })

    # ---- Editor lifecycle ----

    def quit_editor(self, skip_save: bool = False) -> dict:
        """Request a clean editor shutdown. Saves all, stops PIE, then exits.

        Args:
            skip_save: If True, skip saving dirty packages before exit.

        Returns:
            dict with saved (bool), message. Editor will exit ~500ms after response.
        """
        params = {}
        if skip_save:
            params["skip_save"] = True
        return self.send_command("quit_editor", params)

    # ---- Widget commands (B11) ----

    def create_widget_blueprint(self, name: str, parent_class: str = "") -> dict:
        """Create a Widget Blueprint (UUserWidget subclass).

        Args:
            name: Asset name (e.g. "WBP_HUD").
            parent_class: Optional parent class. Defaults to UUserWidget.

        Returns:
            dict with name, asset_path, parent_class, compiled.
        """
        params = {"name": name}
        if parent_class:
            params["parent_class"] = parent_class
        return self.send_command("create_widget_blueprint", params)

    def add_widget_child(self, widget_blueprint: str, widget_type: str,
                         widget_name: str, parent_widget: str = "") -> dict:
        """Add a widget to a Widget Blueprint's hierarchy.

        Args:
            widget_blueprint: Widget Blueprint name (e.g. "WBP_HUD").
            widget_type: Widget type. Supported:
                TextBlock, ProgressBar, Image, Button,
                VerticalBox, HorizontalBox, CanvasPanel, Overlay, SizeBox.
            widget_name: Name for the new widget (must be unique).
            parent_widget: Optional parent widget name. Added to root if empty.

        Returns:
            dict with widget_blueprint, widget_name, widget_type, parent, compiled.
        """
        params = {
            "widget_blueprint": widget_blueprint,
            "widget_type": widget_type,
            "widget_name": widget_name,
        }
        if parent_widget:
            params["parent_widget"] = parent_widget
        return self.send_command("add_widget_child", params)

    def set_widget_property(self, widget_blueprint: str, widget_name: str,
                            property_name: str, value) -> dict:
        """Set a property on a widget in a Widget Blueprint.

        Args:
            widget_blueprint: Widget Blueprint name.
            widget_name: Widget name.
            property_name: Property to set. Supported:
                TextBlock: text, font_size, color ({r,g,b,a}), justification
                ProgressBar: percent (0-1), fill_color, background_color
                Image: color_and_opacity, brush_color
                Button: background_color
                Any: visibility, is_enabled, render_opacity
                Layout: padding, horizontal_alignment, vertical_alignment
                CanvasPanel slot: position ({x,y}), size ({x,y}), anchors, alignment
            value: Property value (type depends on property).

        Returns:
            dict with widget_blueprint, widget_name, property, compiled.
        """
        return self.send_command("set_widget_property", {
            "widget_blueprint": widget_blueprint,
            "widget_name": widget_name,
            "property": property_name,
            "value": value,
        })

    def get_widget_tree(self, widget_blueprint: str) -> dict:
        """List all widgets in a Widget Blueprint with hierarchy and properties.

        Args:
            widget_blueprint: Widget Blueprint name.

        Returns:
            dict with widget_blueprint, total_widgets, tree (nested), has_root.
        """
        return self.send_command("get_widget_tree", {
            "widget_blueprint": widget_blueprint,
        })

    def remove_widget(self, widget_blueprint: str, widget_name: str) -> dict:
        """Remove a widget from a Widget Blueprint. Idempotent.

        Args:
            widget_blueprint: Widget Blueprint name.
            widget_name: Name of the widget to remove.

        Returns:
            dict with widget_blueprint, widget_name, deleted, compiled.
        """
        return self.send_command("remove_widget", {
            "widget_blueprint": widget_blueprint,
            "widget_name": widget_name,
        })

    # ---- Behavior Tree commands ----

    def create_behavior_tree_from_dsl(self, dsl_text: str) -> dict:
        """Parse BT DSL text and create a BehaviorTree + Blackboard in UE.

        Runs the Python BT parser locally, then sends the IR JSON to the
        server's create_behavior_tree command.

        Args:
            dsl_text: Raw BT DSL text.

        Returns:
            dict with tree_asset_path, blackboard_asset_path, node counts,
            and parser_result (errors, warnings, stats).

        Raises:
            BlueprintLLMError: If the server returns an error.
        """
        import sys as _sys
        import os as _os
        _scripts_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
        if _scripts_dir not in _sys.path:
            _sys.path.insert(0, _scripts_dir)
        from bt_parser.bt_parser import parse as _parse_bt

        parse_result = _parse_bt(dsl_text)
        ir = parse_result.get("ir")
        errors = parse_result.get("errors", [])
        warnings = parse_result.get("warnings", [])
        stats = parse_result.get("stats", {})

        if ir is None or not ir.get("tree"):
            raise BlueprintLLMError(
                f"BT parser produced no valid tree. Errors: {errors}")

        ir_json = json.dumps(ir)
        server_result = self.send_command("create_behavior_tree", {"ir_json": ir_json})

        server_result["parser_result"] = {
            "errors": errors,
            "warnings": warnings,
            "stats": stats,
        }
        return server_result

    def get_behavior_tree_info(self, name: str) -> dict:
        """Query an existing BehaviorTree asset.

        Args:
            name: BehaviorTree asset name (e.g. "BT_PatrolGuard").

        Returns:
            dict with tree name, blackboard info, node counts, key list.
        """
        return self.send_command("get_behavior_tree_info", {"name": name})

    def setup_ai_for_pawn(self, pawn_name: str, behavior_tree: str,
                           controller_name: Optional[str] = None) -> dict:
        """One-command AI setup: create AIController with RunBehaviorTree,
        wire it to a pawn, set AutoPossessAI.

        Args:
            pawn_name: Name of the Pawn Blueprint to attach AI to.
            behavior_tree: Name of the BehaviorTree asset to run.
            controller_name: Optional custom controller Blueprint name.
                Defaults to BP_<pawn_name>_AIController.

        Returns:
            dict with pawn, controller, behavior_tree, controller_created,
            auto_possess.
        """
        params = {"pawn_name": pawn_name, "behavior_tree": behavior_tree}
        if controller_name:
            params["controller_name"] = controller_name
        return self.send_command("setup_ai_for_pawn", params)

    # ---- Data Table commands ----

    def create_data_table(self, ir_json: str) -> dict:
        """Create a DataTable + UserDefinedStruct from IR JSON.

        Args:
            ir_json: JSON string of the DT IR (metadata, columns, rows).

        Returns:
            dict with table_asset_path, struct_asset_path, column_count, row_count.
        """
        return self.send_command("create_data_table", {"ir_json": ir_json})

    def create_data_table_from_dsl(self, dsl_text: str) -> dict:
        """Parse DT DSL text and create a DataTable + Struct in UE.

        Runs the Python DT parser locally, then sends the IR JSON to the
        server's create_data_table command.

        Args:
            dsl_text: Raw DT DSL text.

        Returns:
            dict with table_asset_path, struct_asset_path, column_count,
            row_count, and parser_result (errors, warnings, stats).

        Raises:
            BlueprintLLMError: If the server returns an error.
        """
        import sys as _sys
        import os as _os
        _scripts_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
        if _scripts_dir not in _sys.path:
            _sys.path.insert(0, _scripts_dir)
        from dt_parser.dt_parser import parse as _parse_dt

        parse_result = _parse_dt(dsl_text)
        ir = parse_result.get("ir")
        errors = parse_result.get("errors", [])
        warnings = parse_result.get("warnings", [])
        stats = parse_result.get("stats", {})

        if ir is None:
            raise BlueprintLLMError(
                f"DT parser produced no valid IR. Errors: {errors}")

        ir_json = json.dumps(ir)
        server_result = self.send_command("create_data_table", {"ir_json": ir_json})

        server_result["parser_result"] = {
            "errors": errors,
            "warnings": warnings,
            "stats": stats,
        }
        return server_result

    def get_data_table_info(self, name: str) -> dict:
        """Query an existing DataTable asset.

        Args:
            name: DataTable asset name (e.g. "DT_Weapons").

        Returns:
            dict with table name, struct name, columns, row_count, row_names.
        """
        return self.send_command("get_data_table_info", {"name": name})

    # ---- Scene Lighting ----

    def setup_scene_lighting(self, preset: str = "indoor_dark", **kwargs) -> dict:
        """Create standard scene lighting setup.

        Spawns DirectionalLight + SkyLight, optionally SkyAtmosphere and
        ExponentialHeightFog.  Removes existing lights of the same type first.

        Args:
            preset: One of "indoor_dark", "indoor_bright", "outdoor_day",
                    "outdoor_night".  Defaults to "indoor_dark".
            directional_intensity: Override directional light intensity (lux).
            sky_intensity: Override sky light intensity.
            directional_pitch: Override sun pitch angle (degrees, negative = angled down).
            directional_yaw: Override sun yaw angle.
            directional_color: Override light color as {r, g, b} (0-1 floats).
            add_atmosphere: Whether to add a SkyAtmosphere (bool).
            add_fog: Whether to add ExponentialHeightFog (bool).
            fog_density: Override fog density.

        Returns:
            dict with preset, actors_created count, and actors array.
        """
        params = {"preset": preset}
        params.update(kwargs)
        return self.send_command("setup_scene_lighting", params)

    def set_game_mode(self, game_mode: str) -> dict:
        """Set the level's GameMode override in World Settings.

        Args:
            game_mode: Name of a GameMode Blueprint (e.g. "BP_TempleGameMode").
        """
        return self.send_command("set_game_mode", {"game_mode": game_mode})

    # ---- Spline commands (Batch 1.1) ----

    def create_spline_actor(self, blueprint_name: str,
                             points: Optional[list] = None,
                             closed: bool = False) -> dict:
        """Create a Blueprint with a SplineComponent and set initial points.

        Args:
            blueprint_name: Name for the new Blueprint (e.g. "BP_RacePath").
            points: Optional list of {x,y,z} dicts for spline points.
            closed: Whether the spline forms a closed loop.

        Returns:
            dict with blueprint_name, spline_component, point_count, closed, compiled.
        """
        params = {"name": blueprint_name, "closed": closed}
        if points:
            params["initial_points"] = points
        return self.send_command("create_spline_actor", params)

    def add_spline_point(self, blueprint: str, point: dict,
                          index: int = -1) -> dict:
        """Add a point to an existing Blueprint's SplineComponent.

        Args:
            blueprint: Blueprint asset name.
            point: {x,y,z} location for the new point.
            index: Insert index (-1 = append to end).

        Returns:
            dict with blueprint, point_index, total_points, compiled.
        """
        params = {"blueprint": blueprint, "point": point}
        if index >= 0:
            params["index"] = index
        return self.send_command("add_spline_point", params)

    def get_spline_info(self, blueprint: str) -> dict:
        """Get spline information from a Blueprint's SplineComponent.

        Args:
            blueprint: Blueprint asset name.

        Returns:
            dict with blueprint, point_count, spline_length, closed, points array.
        """
        return self.send_command("get_spline_info", {"blueprint": blueprint})

    # ---- Post-process commands (Batch 1.2) ----

    def add_post_process_volume(self, label: str = "",
                                 location: Optional[dict] = None,
                                 infinite_extent: bool = True,
                                 settings: Optional[dict] = None) -> dict:
        """Spawn a PostProcessVolume in the level.

        Args:
            label: Actor label in Outliner.
            location: {x,y,z} location.
            infinite_extent: Whether the volume has infinite bounds (default True).
            settings: Optional dict of post-process settings to apply immediately.

        Returns:
            dict with label, location, infinite_extent.
        """
        params = {"infinite_extent": infinite_extent}
        if label:
            params["label"] = label
        if location:
            params["location"] = location
        if settings:
            params["settings"] = settings
        return self.send_command("add_post_process_volume", params)

    def set_post_process_settings(self, label: str, settings: dict) -> dict:
        """Update settings on an existing PostProcessVolume.

        Args:
            label: Actor label of the PostProcessVolume.
            settings: Dict of settings. Supported keys:
                bloom_intensity (float), bloom_threshold (float),
                auto_exposure_min (float), auto_exposure_max (float),
                ambient_occlusion_intensity (float),
                color_saturation ({x,y,z,w}), color_contrast ({x,y,z,w}),
                color_gamma ({x,y,z,w}), color_gain ({x,y,z,w}),
                vignette_intensity (float),
                depth_of_field_focal_distance (float),
                depth_of_field_fstop (float),
                motion_blur_amount (float), motion_blur_max (float).

        Returns:
            dict with label, settings_applied count.
        """
        return self.send_command("set_post_process_settings", {
            "label": label, "settings": settings,
        })

    # ---- Movement defaults (Batch 1.3) ----

    def set_movement_defaults(self, blueprint: str, settings: dict) -> dict:
        """Set movement properties on a Blueprint's movement component.

        Works with CharacterMovementComponent (Character parents) or
        FloatingPawnMovement (Pawn parents).

        Args:
            blueprint: Blueprint asset name.
            settings: Dict of movement settings. Supported keys:
                CharacterMovement: max_walk_speed, max_acceleration,
                    jump_z_velocity, gravity_scale, air_control,
                    braking_deceleration_walking, braking_friction.
                FloatingPawnMovement: max_speed, acceleration,
                    deceleration, turning_boost.

        Returns:
            dict with blueprint, movement_class, settings_applied.
        """
        return self.send_command("set_movement_defaults", {
            "blueprint": blueprint, "properties": settings,
        })

    # ---- Physics constraint commands (Batch 1.4) ----

    def add_physics_constraint(self, label: str,
                                actor1: str, actor2: str,
                                constraint_type: str = "Fixed",
                                location: Optional[dict] = None) -> dict:
        """Spawn a physics constraint between two actors.

        Args:
            label: Label for the constraint actor.
            actor1: Label of first constrained actor.
            actor2: Label of second constrained actor.
            constraint_type: "Fixed", "Hinge", "Prismatic", or "BallSocket".
            location: {x,y,z} override (default: midpoint of actors).

        Returns:
            dict with label, actor1, actor2, constraint_type, location.
        """
        params = {
            "label": label,
            "actor_a": actor1,
            "actor_b": actor2,
            "constraint_type": constraint_type,
        }
        if location:
            params["location"] = location
        return self.send_command("add_physics_constraint", params)

    def break_constraint(self, label: str) -> dict:
        """Break (disable) a physics constraint.

        Args:
            label: Label of the constraint actor.

        Returns:
            dict with label, broken (bool).
        """
        return self.send_command("break_constraint", {"label": label})

    # ---- Asset import commands (B31-B33) ----

    def import_static_mesh(self, file_path: str, asset_name: str,
                           destination: str = "") -> dict:
        """Import a .fbx or .obj file as a UStaticMesh asset.

        Args:
            file_path: Absolute path to the source file.
            asset_name: Name for the UE asset.
            destination: Destination folder (default "/Game/Arcwright/Meshes").

        Returns:
            dict with asset_path, vertices, triangles, imported_count.
        """
        params = {"file_path": file_path, "asset_name": asset_name}
        if destination:
            params["destination"] = destination
        return self.send_command("import_static_mesh", params)

    def import_texture(self, file_path: str, asset_name: str,
                       destination: str = "") -> dict:
        """Import a .png/.jpg/.tga as a UTexture2D asset.

        Args:
            file_path: Absolute path to the image file.
            asset_name: Name for the UE asset.
            destination: Destination folder (default "/Game/Arcwright/Textures").

        Returns:
            dict with asset_path, width, height, format, imported_count.
        """
        params = {"file_path": file_path, "asset_name": asset_name}
        if destination:
            params["destination"] = destination
        return self.send_command("import_texture", params)

    def import_sound(self, file_path: str, asset_name: str,
                     destination: str = "") -> dict:
        """Import a .wav/.ogg/.mp3 as a USoundWave asset.

        Args:
            file_path: Absolute path to the audio file.
            asset_name: Name for the UE asset.
            destination: Destination folder (default "/Game/Arcwright/Sounds").

        Returns:
            dict with asset_path, duration, channels, sample_rate, imported_count.
        """
        params = {"file_path": file_path, "asset_name": asset_name}
        if destination:
            params["destination"] = destination
        return self.send_command("import_sound", params)

    # ---- Sequencer commands (Batch 2.1) ----

    def create_sequence(self, name: str, duration: float = 5.0) -> dict:
        """Create a ULevelSequence asset.

        Args:
            name: Sequence name (e.g. "LS_Intro").
            duration: Duration in seconds (default 5.0).

        Returns:
            dict with name, asset_path, duration, track_count.
        """
        return self.send_command("create_sequence", {
            "name": name, "duration": duration,
        })

    def add_sequence_track(self, sequence_name: str, actor_label: str,
                            track_type: str = "Transform") -> dict:
        """Add a track to a sequence for a specific actor.

        Args:
            sequence_name: Name of the sequence.
            actor_label: Label of the actor to bind.
            track_type: "Transform", "Visibility", or "Float".

        Returns:
            dict with sequence_name, actor_label, track_type, binding_guid.
        """
        return self.send_command("add_sequence_track", {
            "sequence_name": sequence_name,
            "actor_label": actor_label,
            "track_type": track_type,
        })

    def add_keyframe(self, sequence_name: str, actor_label: str,
                      track_type: str, time: float, value) -> dict:
        """Add a keyframe to a sequence track.

        Args:
            sequence_name: Name of the sequence.
            actor_label: Label of the bound actor.
            track_type: "Transform", "Visibility", or "Float".
            time: Time in seconds.
            value: For Transform: {location:{x,y,z}, rotation:{p,y,r}, scale:{x,y,z}}.
                   For Visibility: bool. For Float: float.

        Returns:
            dict with sequence_name, actor_label, track_type, time, keys_added.
        """
        return self.send_command("add_keyframe", {
            "sequence_name": sequence_name,
            "actor_label": actor_label,
            "track_type": track_type,
            "time": time,
            "value": value,
        })

    def get_sequence_info(self, name: str) -> dict:
        """Query a sequence's structure.

        Args:
            name: Sequence name.

        Returns:
            dict with name, duration, total_tracks, bound_actors.
        """
        return self.send_command("get_sequence_info", {"name": name})

    def play_sequence(self, name: str) -> dict:
        """Play a sequence in editor preview.

        Note: May have same limitations as play_in_editor.
        """
        return self.send_command("play_sequence", {"name": name})

    # ---- Landscape/Foliage commands (Batch 2.2) ----

    def get_landscape_info(self) -> dict:
        """Query if a landscape exists and get its properties.

        Returns:
            dict with exists (bool), bounds, component_count, material.
        """
        return self.send_command("get_landscape_info")

    def set_landscape_material(self, material_path: str) -> dict:
        """Apply a material to the landscape.

        Args:
            material_path: Material asset path.

        Returns:
            dict with landscape, material_path.
        """
        return self.send_command("set_landscape_material", {
            "material_path": material_path,
        })

    def create_foliage_type(self, name: str, mesh: str = "",
                             density: float = 100.0,
                             scale_min: float = 1.0,
                             scale_max: float = 1.0) -> dict:
        """Create a UFoliageType_InstancedStaticMesh asset.

        Args:
            name: Asset name.
            mesh: Static mesh path (default: Sphere).
            density: Foliage density.
            scale_min: Minimum random scale.
            scale_max: Maximum random scale.

        Returns:
            dict with name, asset_path, mesh, density, scale_min, scale_max.
        """
        params = {"name": name, "density": density,
                  "scale_min": scale_min, "scale_max": scale_max}
        if mesh:
            params["mesh"] = mesh
        return self.send_command("create_foliage_type", params)

    def paint_foliage(self, foliage_type: str, center: dict,
                       radius: float = 500.0, count: int = 10) -> dict:
        """Paint foliage instances in a radius.

        Args:
            foliage_type: Foliage type asset path.
            center: {x,y,z} center position.
            radius: Placement radius.
            count: Number of instances to place.

        Returns:
            dict with foliage_type, placed, center, radius.
        """
        return self.send_command("paint_foliage", {
            "foliage_type": foliage_type,
            "center": center,
            "radius": radius,
            "count": count,
        })

    def get_foliage_info(self) -> dict:
        """List foliage types and instance counts.

        Returns:
            dict with foliage_type_count, total_instances, foliage_types array.
        """
        return self.send_command("get_foliage_info")

    # ---- DSL-to-Blueprint single command ----

    def create_blueprint_from_dsl(self, dsl_text: str, name: Optional[str] = None) -> dict:
        """Parse raw DSL text and create a Blueprint in UE in one call.

        Runs the Python DSL parser locally, then sends the IR JSON to the
        server's create_blueprint_from_dsl command. No intermediate files.

        Args:
            dsl_text: Raw DSL text (the format the LLM generates).
            name: Optional Blueprint name override.

        Returns:
            dict with status, data (blueprint_name, nodes_created,
            connections_wired, compiled, etc.), and parser_result
            (errors, warnings, stats from the Python parser).

        Raises:
            BlueprintLLMError: If the server returns an error.
            ImportError: If the DSL parser module is not found.
        """
        # Lazy import of the parser — keeps the client usable without it
        import sys as _sys
        import os as _os
        _scripts_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
        _parser_dir = _os.path.join(_scripts_dir, "dsl_parser")
        if _scripts_dir not in _sys.path:
            _sys.path.insert(0, _scripts_dir)
        if _parser_dir not in _sys.path:
            _sys.path.insert(0, _parser_dir)
        from dsl_parser.parser import parse as _parse_dsl

        # Parse DSL → IR
        parse_result = _parse_dsl(dsl_text)
        ir = parse_result.get("ir")
        errors = parse_result.get("errors", [])
        warnings = parse_result.get("warnings", [])
        stats = parse_result.get("stats", {})

        if ir is None:
            raise BlueprintLLMError(
                f"DSL parser produced no IR. Errors: {errors}")

        # Serialize IR to JSON string for the server
        ir_json = json.dumps(ir)

        # Send to server
        params = {"ir_json": ir_json}
        if name is not None:
            params["name"] = name
        server_result = self.send_command("create_blueprint_from_dsl", params)

        # Attach parser metadata to the response
        server_result["parser_result"] = {
            "errors": errors,
            "warnings": warnings,
            "stats": stats,
        }

        return server_result

    # ---- Query commands ----

    def find_blueprints(self, name_filter="", parent_class="", has_variable="",
                        has_component="", path=""):
        """Search for Blueprint assets by name, parent class, variables, or components."""
        params = {}
        if name_filter: params["name_filter"] = name_filter
        if parent_class: params["parent_class"] = parent_class
        if has_variable: params["has_variable"] = has_variable
        if has_component: params["has_component"] = has_component
        if path: params["path"] = path
        return self.send_command("find_blueprints", params)

    def find_actors(self, name_filter="", class_filter="", tag="",
                    has_component="", material_name="", radius=None, center=None):
        """Search for actors in the level by name, class, tag, component, material, or proximity."""
        params = {}
        if name_filter: params["name_filter"] = name_filter
        if class_filter: params["class_filter"] = class_filter
        if tag: params["tag"] = tag
        if has_component: params["has_component"] = has_component
        if material_name: params["material_name"] = material_name
        if radius is not None: params["radius"] = radius
        if center is not None: params["center"] = center
        return self.send_command("find_actors", params)

    def find_assets(self, asset_type="", name_filter="", path="", max_results=100):
        """Search the asset registry by type and name."""
        params = {"max_results": max_results}
        if asset_type: params["type"] = asset_type
        if name_filter: params["name_filter"] = name_filter
        if path: params["path"] = path
        return self.send_command("find_assets", params)

    # ---- Batch modify commands ----

    def batch_set_variable(self, operations):
        """Set variable defaults on multiple Blueprints.
        operations: [{"blueprint": str, "variable_name": str, "default_value": str}, ...]"""
        return self.send_command("batch_set_variable", {"operations": operations})

    def batch_add_component(self, operations):
        """Add components to multiple Blueprints.
        operations: [{"blueprint": str, "component_type": str, "component_name": str, "properties": {}}, ...]"""
        return self.send_command("batch_add_component", {"operations": operations})

    def batch_apply_material(self, operations):
        """Apply materials to multiple actors or Blueprints.
        operations: [{"actor_label": str, "material_path": str, "slot": int}, ...] or
                     [{"blueprint": str, "material_path": str}, ...]"""
        return self.send_command("batch_apply_material", {"operations": operations})

    def batch_set_property(self, operations):
        """Set properties on multiple actors (location, rotation, scale, visibility, tag).
        operations: [{"actor_label": str, "property": str, "value": ..., "relative": bool}, ...]"""
        return self.send_command("batch_set_property", {"operations": operations})

    def batch_delete_actors(self, labels=None, class_filter="", tag=""):
        """Delete multiple actors by label list, class filter, or tag."""
        params = {}
        if labels: params["labels"] = labels
        if class_filter: params["class_filter"] = class_filter
        if tag: params["tag"] = tag
        return self.send_command("batch_delete_actors", params)

    def batch_replace_material(self, old_material, new_material):
        """Replace all occurrences of one material with another across all level actors."""
        return self.send_command("batch_replace_material", {
            "old_material": old_material,
            "new_material": new_material,
        })

    # ---- In-place modify commands ----

    def modify_blueprint(self, name, add_variables=None, remove_variables=None,
                         set_class_defaults=None):
        """Modify a Blueprint in-place: add/remove variables, set class defaults."""
        params = {"name": name}
        if add_variables: params["add_variables"] = add_variables
        if remove_variables: params["remove_variables"] = remove_variables
        if set_class_defaults: params["set_class_defaults"] = set_class_defaults
        return self.send_command("modify_blueprint", params)

    def rename_asset(self, old_name, new_name):
        """Rename a Blueprint or other asset."""
        return self.send_command("rename_asset", {
            "old_name": old_name, "new_name": new_name,
        })

    def reparent_blueprint(self, name, new_parent):
        """Change a Blueprint's parent class."""
        return self.send_command("reparent_blueprint", {
            "name": name, "new_parent": new_parent,
        })

    # ---- Procedural spawn pattern commands ----

    def spawn_actor_grid(self, actor_class, rows=3, cols=3, spacing_x=200.0,
                         spacing_y=200.0, origin=None, center=True,
                         label_prefix="", rotation=None, scale=None):
        """Spawn actors in a rows×cols grid pattern."""
        params = {"class": actor_class, "rows": rows, "cols": cols,
                  "spacing_x": spacing_x, "spacing_y": spacing_y, "center": center}
        if origin: params["origin"] = origin
        if label_prefix: params["label_prefix"] = label_prefix
        if rotation: params["rotation"] = rotation
        if scale: params["scale"] = scale
        return self.send_command("spawn_actor_grid", params)

    def spawn_actor_circle(self, actor_class, count=8, radius=500.0, center=None,
                           face_center=False, start_angle=0.0, label_prefix="",
                           scale=None):
        """Spawn actors in a circle pattern."""
        params = {"class": actor_class, "count": count, "radius": radius}
        if center: params["center"] = center
        if face_center: params["face_center"] = face_center
        if start_angle != 0.0: params["start_angle"] = start_angle
        if label_prefix: params["label_prefix"] = label_prefix
        if scale: params["scale"] = scale
        return self.send_command("spawn_actor_circle", params)

    def spawn_actor_line(self, actor_class, count, start, end, label_prefix="",
                         face_direction=False, scale=None):
        """Spawn actors along a line from start to end."""
        params = {"class": actor_class, "count": count, "start": start, "end": end}
        if label_prefix: params["label_prefix"] = label_prefix
        if face_direction: params["face_direction"] = face_direction
        if scale: params["scale"] = scale
        return self.send_command("spawn_actor_line", params)

    # ---- Relative transform batch commands ----

    def batch_scale_actors(self, scale, labels=None, name_filter="",
                           class_filter="", tag="", mode="multiply"):
        """Scale multiple actors by filter."""
        params = {"scale": scale, "mode": mode}
        if labels: params["labels"] = labels
        if name_filter: params["name_filter"] = name_filter
        if class_filter: params["class_filter"] = class_filter
        if tag: params["tag"] = tag
        return self.send_command("batch_scale_actors", params)

    def batch_move_actors(self, offset=None, location=None, labels=None,
                          name_filter="", class_filter="", tag="", mode="relative"):
        """Move multiple actors by filter. Use offset for relative, location for set mode."""
        params = {"mode": mode}
        if offset: params["offset"] = offset
        if location: params["location"] = location
        if labels: params["labels"] = labels
        if name_filter: params["name_filter"] = name_filter
        if class_filter: params["class_filter"] = class_filter
        if tag: params["tag"] = tag
        return self.send_command("batch_move_actors", params)

    def close(self):
        """Close the connection."""
        try:
            self.sock.close()
        except OSError:
            pass

    # ---- HTML → Widget ----

    def create_widget_from_html(self, html: str, widget_name: str = "WBP_Generated") -> dict:
        """Translate HTML/CSS to a UE Widget Blueprint and create it.

        Runs the html_to_widget translator locally, then executes all resulting
        widget commands (create_widget_blueprint, add_widget_child, set_widget_property)
        against the UE command server.

        Args:
            html: HTML string with embedded CSS.
            widget_name: Name for the Widget Blueprint.

        Returns:
            dict with widget_name, widget_count, commands_executed, commands_failed, errors.
        """
        import sys, os
        _html_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "html_to_widget")
        if _html_dir not in sys.path:
            sys.path.insert(0, _html_dir)
        from html_to_widget import translate_html_to_widget, execute_commands

        result = translate_html_to_widget(html, widget_name=widget_name)
        if not result["commands"]:
            return {"widget_name": widget_name, "widget_count": 0,
                    "commands_executed": 0, "commands_failed": 0,
                    "errors": result.get("warnings", ["No widgets parsed"])}

        exec_result = execute_commands(result["commands"], self)
        return {
            "widget_name": result["widget_name"],
            "widget_count": result["widget_count"],
            "commands_executed": exec_result["success"],
            "commands_failed": exec_result["failed"],
            "errors": exec_result["errors"],
        }

    # ==========================================================
    # Batch 1: Inspector Commands
    # ==========================================================

    def get_blueprint_details(self, name):
        """Get detailed Blueprint info: variables, components, events, node counts."""
        return self.send_command("get_blueprint_details", {"name": name})

    def get_actor_properties(self, actor_label):
        """Get detailed actor info: transform, tags, components, visibility, mobility."""
        return self.send_command("get_actor_properties", {"actor_label": actor_label})

    def get_all_materials(self, name_filter="", max_results=50):
        """List all material assets in the project."""
        params = {"max_results": max_results}
        if name_filter:
            params["name_filter"] = name_filter
        return self.send_command("list_available_materials", params)

    def get_all_blueprints(self, name_filter="", max_results=50):
        """List all Blueprint assets in the project."""
        params = {"max_results": max_results}
        if name_filter:
            params["name_filter"] = name_filter
        return self.send_command("list_available_blueprints", params)

    # ==========================================================
    # Batch 2: Collision & Physics
    # ==========================================================

    def set_collision_preset(self, preset_name, actor_label="", blueprint="", component_name=""):
        """Set collision profile on an actor or Blueprint component."""
        params = {"preset_name": preset_name}
        if actor_label:
            params["actor_label"] = actor_label
        if blueprint:
            params["blueprint"] = blueprint
        if component_name:
            params["component_name"] = component_name
        return self.send_command("set_collision_preset", params)

    def set_collision_shape(self, actor_label="", blueprint="", component_name="", **kwargs):
        """Set collision shape dimensions (extents, radius, half_height)."""
        params = {}
        if actor_label:
            params["actor_label"] = actor_label
        if blueprint:
            params["blueprint"] = blueprint
        if component_name:
            params["component_name"] = component_name
        for key in ("extents", "radius", "half_height"):
            if key in kwargs:
                params[key] = kwargs[key]
        return self.send_command("set_collision_shape", params)

    def set_physics_enabled(self, enabled, actor_label="", blueprint="", component_name=""):
        """Enable or disable physics simulation on a component."""
        params = {"enabled": enabled}
        if actor_label:
            params["actor_label"] = actor_label
        if blueprint:
            params["blueprint"] = blueprint
        if component_name:
            params["component_name"] = component_name
        return self.send_command("set_physics_enabled", params)

    # ==========================================================
    # Batch 3: Camera & Input
    # ==========================================================

    def set_camera_properties(self, blueprint, **kwargs):
        """Set camera/spring arm properties on a Blueprint."""
        params = {"blueprint": blueprint}
        for key in ("fov", "arm_length", "use_pawn_control_rotation",
                     "do_collision_test", "camera_lag_speed", "camera_rotation_lag_speed"):
            if key in kwargs:
                params[key] = kwargs[key]
        return self.send_command("set_camera_properties", params)

    def create_input_action(self, name, value_type="bool"):
        """Create an Enhanced Input Action asset."""
        return self.send_command("create_input_action", {"name": name, "value_type": value_type})

    def create_input_mapping(self, context, action, key):
        """Create or update an Input Mapping Context with an action+key binding."""
        return self.send_command("add_input_mapping", {
            "context": context,
            "action": action,
            "key": key,
        })

    # ==========================================================
    # Batch 4: Actor Configuration
    # ==========================================================

    def set_actor_tags(self, actor_label, tags):
        """Set tags on a level actor (replaces existing tags)."""
        return self.send_command("set_actor_tags", {
            "actor_label": actor_label,
            "tags": tags,
        })

    def set_actor_visibility(self, actor_label, visible, propagate=True):
        """Set actor visibility in the level."""
        params = {"actor_label": actor_label, "visible": visible}
        if not propagate:
            params["propagate"] = False
        return self.send_command("set_actor_visibility", params)

    def set_actor_mobility(self, actor_label, mobility):
        """Set actor mobility: Static, Stationary, or Movable."""
        return self.send_command("set_actor_mobility", {
            "actor_label": actor_label,
            "mobility": mobility,
        })

    def attach_actor_to(self, actor_label, parent_label, socket_name="", rule="KeepWorld"):
        """Attach an actor to another actor."""
        params = {"actor_label": actor_label, "parent_label": parent_label}
        if socket_name:
            params["socket_name"] = socket_name
        if rule != "KeepWorld":
            params["rule"] = rule
        return self.send_command("attach_actor_to", params)

    def detach_actor(self, actor_label, rule="KeepWorld"):
        """Detach an actor from its parent."""
        params = {"actor_label": actor_label}
        if rule != "KeepWorld":
            params["rule"] = rule
        return self.send_command("detach_actor", params)

    # ==========================================================
    # Batch 5: Navigation & Audio
    # ==========================================================

    def create_nav_mesh_bounds(self, location=None, extents=None, label="NavMeshBounds"):
        """Create a NavMeshBoundsVolume in the level."""
        params = {"label": label}
        if location:
            params["location"] = location
        if extents:
            params["extents"] = extents
        return self.send_command("create_nav_mesh_bounds", params)

    def set_audio_properties(self, actor_label="", blueprint="", component_name="", **kwargs):
        """Set audio component properties (volume, pitch, auto_activate, is_ui_sound)."""
        params = {}
        if actor_label:
            params["actor_label"] = actor_label
        if blueprint:
            params["blueprint"] = blueprint
        if component_name:
            params["component_name"] = component_name
        for key in ("volume_multiplier", "pitch_multiplier", "auto_activate", "is_ui_sound"):
            if key in kwargs:
                params[key] = kwargs[key]
        return self.send_command("set_audio_properties", params)

    # play_sound_at_location already exists via send_command

    # ==========================================================
    # Batch 6: Project Utilities
    # ==========================================================

    def list_project_assets(self, asset_type="", path="", name_filter="", max_results=100):
        """List project assets by type, path, or name filter."""
        params = {"max_results": max_results}
        if asset_type:
            params["asset_type"] = asset_type
        if path:
            params["path"] = path
        if name_filter:
            params["name_filter"] = name_filter
        return self.send_command("list_project_assets", params)

    def copy_actor(self, actor_label, new_label="", offset=None):
        """Duplicate a level actor with optional new label and position offset."""
        params = {"actor_label": actor_label}
        if new_label:
            params["new_label"] = new_label
        if offset:
            params["offset"] = offset
        return self.send_command("copy_actor", params)

    # ==========================================================
    # Enhanced Input
    # ==========================================================

    def set_player_input_mapping(self, blueprint, context):
        return self.send_command("set_player_input_mapping", {"blueprint": blueprint, "context": context})

    # ==========================================================
    # Advanced Actor Config
    # ==========================================================

    def set_actor_tick(self, actor_label, enabled=True, interval=None):
        params = {"actor_label": actor_label, "enabled": enabled}
        if interval is not None: params["interval"] = interval
        return self.send_command("set_actor_tick", params)

    def set_actor_lifespan(self, actor_label, lifespan=0.0):
        return self.send_command("set_actor_lifespan", {"actor_label": actor_label, "lifespan": lifespan})

    def get_actor_bounds(self, actor_label):
        return self.send_command("get_actor_bounds", {"actor_label": actor_label})

    def set_actor_enabled(self, actor_label, enabled=True):
        return self.send_command("set_actor_enabled", {"actor_label": actor_label, "enabled": enabled})

    # ==========================================================
    # Data & Persistence
    # ==========================================================

    def create_save_game(self, name, variables=None):
        params = {"name": name}
        if variables: params["variables"] = variables
        return self.send_command("create_save_game", params)

    def add_data_table_row(self, table_name, row_name, values):
        return self.send_command("add_data_table_row", {"table_name": table_name, "row_name": row_name, "values": values})

    def edit_data_table_row(self, table_name, row_name, values):
        return self.send_command("edit_data_table_row", {"table_name": table_name, "row_name": row_name, "values": values})

    def get_data_table_rows(self, table_name):
        return self.send_command("get_data_table_rows", {"table_name": table_name})

    # ==========================================================
    # Animation
    # ==========================================================

    def create_anim_blueprint(self, name, skeleton):
        return self.send_command("create_anim_blueprint", {"name": name, "skeleton": skeleton})

    def add_anim_state(self, anim_blueprint, state_name):
        return self.send_command("add_anim_state", {"anim_blueprint": anim_blueprint, "state_name": state_name})

    def add_anim_transition(self, anim_blueprint, from_state, to_state):
        return self.send_command("add_anim_transition", {"anim_blueprint": anim_blueprint, "from_state": from_state, "to_state": to_state})

    def set_anim_state_animation(self, anim_blueprint, state_name, animation):
        return self.send_command("set_anim_state_animation", {"anim_blueprint": anim_blueprint, "state_name": state_name, "animation": animation})

    def create_anim_montage(self, name, animation):
        return self.send_command("create_anim_montage", {"name": name, "animation": animation})

    def add_montage_section(self, montage_name, section_name, start_time=0.0):
        return self.send_command("add_montage_section", {"montage_name": montage_name, "section_name": section_name, "start_time": start_time})

    def create_blend_space(self, name, skeleton, dimensions=2, axis_x="Speed", axis_y="Direction", x_min=-180, x_max=180, y_min=-180, y_max=180):
        params = {"name": name, "skeleton": skeleton, "dimensions": dimensions, "axis_x": axis_x}
        if dimensions == 2:
            params.update({"axis_y": axis_y, "y_min": y_min, "y_max": y_max})
        params.update({"x_min": x_min, "x_max": x_max})
        return self.send_command("create_blend_space", params)

    def add_blend_space_sample(self, blend_space, animation, x=0.0, y=0.0):
        return self.send_command("add_blend_space_sample", {"blend_space": blend_space, "animation": animation, "x": x, "y": y})

    def set_skeletal_mesh(self, mesh, actor_label="", blueprint="", component_name=""):
        params = {"mesh": mesh}
        if actor_label: params["actor_label"] = actor_label
        if blueprint: params["blueprint"] = blueprint
        if component_name: params["component_name"] = component_name
        return self.send_command("set_skeletal_mesh", params)

    def play_animation(self, actor_label, animation, looping=False):
        return self.send_command("play_animation", {"actor_label": actor_label, "animation": animation, "looping": looping})

    def get_skeleton_bones(self, skeleton):
        return self.send_command("get_skeleton_bones", {"skeleton": skeleton})

    def get_available_animations(self, skeleton="", name_filter="", max_results=100):
        params = {"max_results": max_results}
        if skeleton: params["skeleton"] = skeleton
        if name_filter: params["name_filter"] = name_filter
        return self.send_command("get_available_animations", params)

    # ==========================================================
    # Niagara
    # ==========================================================

    def set_niagara_parameter(self, actor_label, parameter_name, float_value=None, int_value=None, bool_value=None, vector_value=None, color_value=None):
        params = {"actor_label": actor_label, "parameter_name": parameter_name}
        if float_value is not None: params["float_value"] = float_value
        if int_value is not None: params["int_value"] = int_value
        if bool_value is not None: params["bool_value"] = bool_value
        if vector_value is not None: params["vector_value"] = vector_value
        if color_value is not None: params["color_value"] = color_value
        return self.send_command("set_niagara_parameter", params)

    def activate_niagara(self, actor_label, activate=True, component_name=""):
        params = {"actor_label": actor_label, "activate": activate}
        if component_name: params["component_name"] = component_name
        return self.send_command("activate_niagara", params)

    def get_niagara_parameters(self, actor_label):
        return self.send_command("get_niagara_parameters", {"actor_label": actor_label})

    # ==========================================================
    # Level Management
    # ==========================================================

    def create_sublevel(self, name):
        return self.send_command("create_sublevel", {"name": name})

    def set_level_visibility(self, level_name, visible=True):
        return self.send_command("set_level_visibility", {"level_name": level_name, "visible": visible})

    def get_sublevel_list(self):
        return self.send_command("get_sublevel_list", {})

    def move_actor_to_sublevel(self, actor_label, level_name):
        return self.send_command("move_actor_to_sublevel", {"actor_label": actor_label, "level_name": level_name})

    # ==========================================================
    # World & Actor Utilities (150 target)
    # ==========================================================

    def get_world_settings(self):
        return self.send_command("get_world_settings", {})

    def set_world_settings(self, gravity=None, kill_z=None, time_dilation=None):
        params = {}
        if gravity is not None: params["gravity"] = gravity
        if kill_z is not None: params["kill_z"] = kill_z
        if time_dilation is not None: params["time_dilation"] = time_dilation
        return self.send_command("set_world_settings", params)

    def get_actor_class(self, actor_label):
        return self.send_command("get_actor_class", {"actor_label": actor_label})

    def set_actor_scale(self, actor_label, scale, relative=False):
        params = {"actor_label": actor_label, "relative": relative}
        if isinstance(scale, (int, float)):
            params["scale"] = scale
        else:
            params["scale"] = scale  # dict {x, y, z}
        return self.send_command("set_actor_scale", params)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()


if __name__ == "__main__":
    # Quick test
    with ArcwrightClient() as client:
        result = client.health_check()
        print(json.dumps(result, indent=2))
