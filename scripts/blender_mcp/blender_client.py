"""
Arcwright — Blender TCP Client
Connects to the Blender command server on port 13378.
Mirrors blueprint_client.py for consistency.
"""

import socket
import json


class BlenderClientError(Exception):
    pass


class BlenderClient:
    """TCP client for the Blender command server."""
    
    def __init__(self, host="localhost", port=13378, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
    
    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def _send(self, command: str, params: dict = None) -> dict:
        request = json.dumps({"command": command, "params": params or {}}) + "\n"
        self.sock.sendall(request.encode("utf-8"))
        
        buffer = b""
        while b"\n" not in buffer:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise BlenderClientError("Connection closed")
            buffer += chunk
        
        line = buffer.split(b"\n")[0]
        response = json.loads(line.decode("utf-8"))
        
        if response.get("status") == "error":
            raise BlenderClientError(response.get("message", "Unknown error"))
        
        return response.get("data", {})
    
    # ─── Health ──────────────────────────────────────────────────────────
    
    def health_check(self):
        return self._send("health_check")
    
    # ─── Mesh Creation ───────────────────────────────────────────────────
    
    def create_mesh(self, mesh_type="cube", name="", location=None, rotation=None, scale=None, **kwargs):
        params = {"type": mesh_type}
        if name: params["name"] = name
        if location: params["location"] = location
        if rotation: params["rotation"] = rotation
        if scale: params["scale"] = scale
        params.update(kwargs)
        return self._send("blender_create_mesh", params)
    
    def create_custom_mesh(self, name, vertices, faces, edges=None, location=None):
        params = {"name": name, "vertices": vertices, "faces": faces}
        if edges: params["edges"] = edges
        if location: params["location"] = location
        return self._send("blender_create_custom_mesh", params)
    
    # ─── Object Operations ───────────────────────────────────────────────
    
    def get_objects(self, obj_type=None):
        params = {}
        if obj_type: params["type"] = obj_type
        return self._send("blender_get_objects", params)
    
    def delete_object(self, name):
        return self._send("blender_delete_object", {"name": name})
    
    def duplicate_object(self, name, new_name=""):
        return self._send("blender_duplicate_object", {"name": name, "new_name": new_name})
    
    def set_transform(self, name, location=None, rotation=None, scale=None):
        params = {"name": name}
        if location: params["location"] = location
        if rotation: params["rotation"] = rotation
        if scale: params["scale"] = scale
        return self._send("blender_set_transform", params)
    
    def select_object(self, name, select=True):
        return self._send("blender_select_object", {"name": name, "select": select})

    def join_objects(self, target, names=None):
        params = {"target": target}
        if names:
            params["names"] = names
        return self._send("blender_join_objects", params)

    # ─── Modifiers ───────────────────────────────────────────────────────
    
    def add_modifier(self, name, modifier_type, modifier_name="", properties=None):
        params = {"name": name, "modifier_type": modifier_type}
        if modifier_name: params["modifier_name"] = modifier_name
        if properties: params["properties"] = properties
        return self._send("blender_add_modifier", params)
    
    def remove_modifier(self, name, modifier_name):
        return self._send("blender_remove_modifier", {"name": name, "modifier_name": modifier_name})
    
    # ─── Materials ───────────────────────────────────────────────────────
    
    def create_material(self, name, color=None, metallic=0.0, roughness=0.5):
        params = {"name": name, "metallic": metallic, "roughness": roughness}
        if color: params["color"] = color
        return self._send("blender_create_material", params)
    
    def assign_material(self, object_name, material_name, slot=0):
        return self._send("blender_assign_material", {"object_name": object_name, "material_name": material_name, "slot": slot})
    
    # ─── Edit Mode ───────────────────────────────────────────────────────
    
    def extrude(self, name, value=1.0):
        return self._send("blender_extrude", {"name": name, "value": value})
    
    def bevel(self, name, width=0.1, segments=3):
        return self._send("blender_bevel", {"name": name, "width": width, "segments": segments})
    
    def subdivide(self, name, cuts=1):
        return self._send("blender_subdivide", {"name": name, "cuts": cuts})
    
    # ─── Export ──────────────────────────────────────────────────────────
    
    def export_fbx(self, filepath, selected_only=False):
        return self._send("blender_export_fbx", {"filepath": filepath, "selected_only": selected_only})
    
    def export_obj(self, filepath):
        return self._send("blender_export_obj", {"filepath": filepath})
    
    def export_gltf(self, filepath):
        return self._send("blender_export_gltf", {"filepath": filepath})
    
    # ─── Scene ───────────────────────────────────────────────────────────
    
    def get_scene_info(self):
        return self._send("blender_get_scene_info")
    
    def clear_scene(self, keep_camera=True, keep_lights=False):
        return self._send("blender_clear_scene", {"keep_camera": keep_camera, "keep_lights": keep_lights})
    
    def save_file(self, filepath=""):
        params = {}
        if filepath: params["filepath"] = filepath
        return self._send("blender_save_file", params)
    
    # ─── UV ──────────────────────────────────────────────────────────────

    def smart_uv_project(self, name, angle_limit=66.0):
        return self._send("blender_smart_uv_project", {"name": name, "angle_limit": angle_limit})

    # ─── Procedural Textures ─────────────────────────────────────────────

    def create_procedural_material(self, preset, name="", color1=None, color2=None,
                                    scale=None, roughness=None, **kwargs):
        params = {"preset": preset}
        if name: params["name"] = name
        if color1: params["color1"] = color1
        if color2: params["color2"] = color2
        if scale is not None: params["scale"] = scale
        if roughness is not None: params["roughness"] = roughness
        params.update(kwargs)
        return self._send("blender_create_procedural_material", params)

    def bake_material_to_texture(self, object_name, material_name, output_path,
                                  resolution=1024, bake_type="DIFFUSE"):
        return self._send("blender_bake_material_to_texture", {
            "object_name": object_name,
            "material_name": material_name,
            "output_path": output_path,
            "resolution": resolution,
            "bake_type": bake_type,
        })

    def list_procedural_presets(self):
        return self._send("blender_list_procedural_presets")
