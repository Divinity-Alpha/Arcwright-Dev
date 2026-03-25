"""
Arcwright — Blender TCP Command Server (Blender Addon)
======================================================
Runs inside Blender as an addon. Listens on TCP port 13378 for JSON commands.
Mirrors the architecture of the UE5 Command Server (port 13377).

Install: Edit → Preferences → Add-ons → Install from Disk → select this file
Enable: Check "Arcwright Blender Server" in add-ons list

Protocol: Newline-delimited JSON (same as UE server)
    Request:  {"command": "health_check", "params": {}}
    Response: {"status": "ok", "data": {...}}
    Error:    {"status": "error", "message": "..."}
"""

bl_info = {
    "name": "Arcwright Blender Server",
    "author": "Divinity Alpha",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Arcwright",
    "description": "TCP command server for AI-driven 3D asset creation",
    "category": "Development",
}

import bpy
import json
import os
import socket
import sys
import threading
import traceback
from math import radians
from mathutils import Vector, Euler


# ─── Server Core ─────────────────────────────────────────────────────────────

SERVER_PORT = 13378
server_instance = None


class BlenderCommandServer:
    """TCP server that accepts JSON commands and dispatches to handlers."""
    
    def __init__(self, port=SERVER_PORT):
        self.port = port
        self.running = False
        self.thread = None
        self.sock = None
        self.handlers = {
            "health_check": self.handle_health_check,
            # Mesh creation
            "blender_create_mesh": self.handle_create_mesh,
            "blender_create_custom_mesh": self.handle_create_custom_mesh,
            # Object operations
            "blender_get_objects": self.handle_get_objects,
            "blender_delete_object": self.handle_delete_object,
            "blender_duplicate_object": self.handle_duplicate_object,
            "blender_set_transform": self.handle_set_transform,
            "blender_select_object": self.handle_select_object,
            "blender_join_objects": self.handle_join_objects,
            # Modifiers
            "blender_add_modifier": self.handle_add_modifier,
            "blender_remove_modifier": self.handle_remove_modifier,
            # Materials
            "blender_create_material": self.handle_create_material,
            "blender_assign_material": self.handle_assign_material,
            # Edit mode operations
            "blender_extrude": self.handle_extrude,
            "blender_bevel": self.handle_bevel,
            "blender_subdivide": self.handle_subdivide,
            # Export
            "blender_export_fbx": self.handle_export_fbx,
            "blender_export_obj": self.handle_export_obj,
            "blender_export_gltf": self.handle_export_gltf,
            # Scene
            "blender_get_scene_info": self.handle_get_scene_info,
            "blender_clear_scene": self.handle_clear_scene,
            "blender_save_file": self.handle_save_file,
            # UV
            "blender_smart_uv_project": self.handle_smart_uv_project,
        }
    
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print(f"[Arcwright] Blender server started on port {self.port}")
    
    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        print("[Arcwright] Blender server stopped")
    
    def _listen(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(1.0)
        self.sock.bind(("localhost", self.port))
        self.sock.listen(5)
        
        while self.running:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Arcwright] Accept error: {e}")
    
    def _handle_client(self, conn):
        buffer = b""
        try:
            while True:
                data = conn.recv(65536)
                if not data:
                    break
                buffer += data
                
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        request = json.loads(line.decode("utf-8"))
                        response = self._dispatch(request)
                    except json.JSONDecodeError as e:
                        response = {"status": "error", "message": f"Invalid JSON: {e}"}
                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                    
                    conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[Arcwright] Client error: {e}")
        finally:
            conn.close()
    
    def _dispatch(self, request):
        command = request.get("command", "")
        params = request.get("params", {})

        handler = self.handlers.get(command)
        if not handler:
            return {"status": "error", "message": f"Unknown command: {command}"}

        # Run handler on Blender's main thread via timer dispatch.
        # bpy.ops.* calls fail from background threads — they need
        # the main thread's context (active object, mode, etc.).
        result_box = [None]
        error_box = [None]
        done_event = threading.Event()

        def _main_thread_run():
            try:
                result_box[0] = handler(params)
            except Exception as e:
                traceback.print_exc()
                error_box[0] = str(e)
            done_event.set()
            return None  # Don't repeat the timer

        bpy.app.timers.register(_main_thread_run, first_interval=0.0)
        done_event.wait(timeout=120)  # 2 min timeout for bake operations

        if not done_event.is_set():
            return {"status": "error", "message": f"Command '{command}' timed out (120s)"}
        if error_box[0]:
            return {"status": "error", "message": error_box[0]}
        return {"status": "ok", "data": result_box[0]}
    
    # ─── Handlers ────────────────────────────────────────────────────────
    
    def handle_health_check(self, params):
        return {
            "server": "Arcwright-Blender",
            "version": "1.0",
            "blender_version": ".".join(str(x) for x in bpy.app.version),
            "file": bpy.data.filepath or "(unsaved)",
            "objects": len(bpy.data.objects),
        }
    
    # ─── Mesh Creation ───────────────────────────────────────────────────
    
    def handle_create_mesh(self, params):
        """Create a primitive mesh. Types: cube, sphere, cylinder, cone, plane, torus, monkey."""
        mesh_type = params.get("type", "cube").lower()
        name = params.get("name", "")
        location = params.get("location", [0, 0, 0])
        rotation = params.get("rotation", [0, 0, 0])
        scale = params.get("scale", [1, 1, 1])
        
        loc = tuple(location) if isinstance(location, list) else (location.get("x", 0), location.get("y", 0), location.get("z", 0))
        rot = tuple(radians(r) for r in (rotation if isinstance(rotation, list) else [rotation.get("pitch", 0), rotation.get("yaw", 0), rotation.get("roll", 0)]))
        
        creators = {
            "cube": lambda: bpy.ops.mesh.primitive_cube_add(size=params.get("size", 2), location=loc, rotation=rot),
            "sphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=params.get("radius", 1), segments=params.get("segments", 32), ring_count=params.get("rings", 16), location=loc, rotation=rot),
            "cylinder": lambda: bpy.ops.mesh.primitive_cylinder_add(radius=params.get("radius", 1), depth=params.get("depth", 2), vertices=params.get("vertices", 32), location=loc, rotation=rot),
            "cone": lambda: bpy.ops.mesh.primitive_cone_add(radius1=params.get("radius", 1), depth=params.get("depth", 2), vertices=params.get("vertices", 32), location=loc, rotation=rot),
            "plane": lambda: bpy.ops.mesh.primitive_plane_add(size=params.get("size", 2), location=loc, rotation=rot),
            "torus": lambda: bpy.ops.mesh.primitive_torus_add(major_radius=params.get("major_radius", 1), minor_radius=params.get("minor_radius", 0.25), location=loc, rotation=rot),
            "monkey": lambda: bpy.ops.mesh.primitive_monkey_add(size=params.get("size", 2), location=loc, rotation=rot),
        }
        
        creator = creators.get(mesh_type)
        if not creator:
            raise ValueError(f"Unknown mesh type: {mesh_type}. Valid: {list(creators.keys())}")
        
        creator()
        # Blender 5.0+ removed context.active_object — use view_layer.objects.active
        obj = getattr(bpy.context, 'active_object', None) or bpy.context.view_layer.objects.active
        obj.scale = tuple(scale) if isinstance(scale, list) else (scale.get("x", 1), scale.get("y", 1), scale.get("z", 1))
        
        if name:
            obj.name = name
            obj.data.name = name
        
        return {
            "name": obj.name,
            "type": mesh_type,
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "location": list(obj.location),
        }
    
    def handle_create_custom_mesh(self, params):
        """Create a mesh from raw vertices and faces."""
        name = params.get("name", "CustomMesh")
        vertices = params.get("vertices", [])  # [[x,y,z], ...]
        faces = params.get("faces", [])  # [[v1,v2,v3], ...]
        edges = params.get("edges", [])  # [[v1,v2], ...]
        location = params.get("location", [0, 0, 0])
        
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, edges, faces)
        mesh.update()
        
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = tuple(location) if isinstance(location, list) else (location.get("x", 0), location.get("y", 0), location.get("z", 0))
        
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        return {
            "name": obj.name,
            "vertices": len(mesh.vertices),
            "faces": len(mesh.polygons),
            "edges": len(mesh.edges),
        }
    
    # ─── Object Operations ───────────────────────────────────────────────
    
    def handle_get_objects(self, params):
        """List all objects in the scene."""
        filter_type = params.get("type", None)  # MESH, LIGHT, CAMERA, EMPTY, etc.
        objects = []
        for obj in bpy.data.objects:
            if filter_type and obj.type != filter_type.upper():
                continue
            objects.append({
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation": [round(r, 4) for r in obj.rotation_euler],
                "scale": list(obj.scale),
                "vertices": len(obj.data.vertices) if hasattr(obj.data, "vertices") else 0,
                "visible": obj.visible_get(),
            })
        return {"objects": objects, "count": len(objects)}
    
    def handle_delete_object(self, params):
        """Delete an object by name."""
        name = params.get("name", "")
        obj = bpy.data.objects.get(name)
        if not obj:
            return {"deleted": False, "message": f"Object '{name}' not found"}
        
        bpy.data.objects.remove(obj, do_unlink=True)
        return {"deleted": True, "name": name}
    
    def handle_duplicate_object(self, params):
        """Duplicate an object."""
        name = params.get("name", "")
        new_name = params.get("new_name", "")
        
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object '{name}' not found")
        
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        if new_name:
            new_obj.name = new_name
            new_obj.data.name = new_name
        
        bpy.context.collection.objects.link(new_obj)
        return {"name": new_obj.name, "source": name}
    
    def handle_set_transform(self, params):
        """Set object location, rotation, and/or scale."""
        name = params.get("name", "")
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object '{name}' not found")
        
        if "location" in params:
            loc = params["location"]
            obj.location = tuple(loc) if isinstance(loc, list) else (loc.get("x", 0), loc.get("y", 0), loc.get("z", 0))
        
        if "rotation" in params:
            rot = params["rotation"]
            if isinstance(rot, list):
                obj.rotation_euler = tuple(radians(r) for r in rot)
            else:
                obj.rotation_euler = Euler((radians(rot.get("x", 0)), radians(rot.get("y", 0)), radians(rot.get("z", 0))))
        
        if "scale" in params:
            sc = params["scale"]
            obj.scale = tuple(sc) if isinstance(sc, list) else (sc.get("x", 1), sc.get("y", 1), sc.get("z", 1))
        
        return {"name": name, "location": list(obj.location), "rotation": list(obj.rotation_euler), "scale": list(obj.scale)}
    
    def handle_select_object(self, params):
        """Select/deselect an object."""
        name = params.get("name", "")
        select = params.get("select", True)
        
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object '{name}' not found")
        
        obj.select_set(select)
        if select:
            bpy.context.view_layer.objects.active = obj
        
        return {"name": name, "selected": select}
    
    def handle_join_objects(self, params):
        """Join multiple objects into one. All mesh objects are joined into target."""
        target_name = params.get("target", "")
        names = params.get("names", [])  # Optional: specific objects to join

        target = bpy.data.objects.get(target_name)
        if not target or target.type != "MESH":
            raise ValueError(f"Target mesh '{target_name}' not found")

        # Deselect all first
        bpy.ops.object.select_all(action='DESELECT')

        # Select objects to join
        if names:
            for n in names:
                obj = bpy.data.objects.get(n)
                if obj and obj.type == "MESH":
                    obj.select_set(True)
        else:
            # Join all mesh objects
            for obj in bpy.data.objects:
                if obj.type == "MESH":
                    obj.select_set(True)

        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.join()

        return {"name": target.name, "vertices": len(target.data.vertices)}

    # ─── Modifiers ───────────────────────────────────────────────────────

    def handle_add_modifier(self, params):
        """Add a modifier to an object. Types: SUBSURF, MIRROR, BEVEL, ARRAY, BOOLEAN, SOLIDIFY, DECIMATE."""
        name = params.get("name", "")
        mod_type = params.get("modifier_type", "SUBSURF").upper()
        mod_name = params.get("modifier_name", "")
        
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object '{name}' not found")
        
        mod = obj.modifiers.new(name=mod_name or mod_type, type=mod_type)
        
        # Apply common properties
        properties = params.get("properties", {})
        for key, val in properties.items():
            if hasattr(mod, key):
                setattr(mod, key, val)
        
        return {"name": name, "modifier": mod.name, "type": mod_type}
    
    def handle_remove_modifier(self, params):
        """Remove a modifier by name."""
        name = params.get("name", "")
        mod_name = params.get("modifier_name", "")
        
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object '{name}' not found")
        
        mod = obj.modifiers.get(mod_name)
        if not mod:
            return {"removed": False, "message": f"Modifier '{mod_name}' not found on '{name}'"}
        
        obj.modifiers.remove(mod)
        return {"removed": True, "name": name, "modifier": mod_name}
    
    # ─── Materials ───────────────────────────────────────────────────────
    
    def handle_create_material(self, params):
        """Create a Principled BSDF material."""
        name = params.get("name", "Material")
        color = params.get("color", [0.8, 0.8, 0.8, 1.0])
        metallic = params.get("metallic", 0.0)
        roughness = params.get("roughness", 0.5)
        
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        
        if bsdf:
            if isinstance(color, dict):
                color = [color.get("r", 0.8), color.get("g", 0.8), color.get("b", 0.8), color.get("a", 1.0)]
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Metallic"].default_value = metallic
            bsdf.inputs["Roughness"].default_value = roughness
        
        return {"name": mat.name, "color": list(color), "metallic": metallic, "roughness": roughness}
    
    def handle_assign_material(self, params):
        """Assign a material to an object."""
        obj_name = params.get("object_name", "")
        mat_name = params.get("material_name", "")
        slot = params.get("slot", 0)
        
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            raise ValueError(f"Object '{obj_name}' not found")
        
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            raise ValueError(f"Material '{mat_name}' not found")
        
        if len(obj.data.materials) > slot:
            obj.data.materials[slot] = mat
        else:
            obj.data.materials.append(mat)
        
        return {"object": obj_name, "material": mat_name, "slot": slot}
    
    # ─── Edit Mode Operations ────────────────────────────────────────────
    
    def handle_extrude(self, params):
        """Extrude selected faces of an object."""
        name = params.get("name", "")
        value = params.get("value", 1.0)
        
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            raise ValueError(f"Mesh object '{name}' not found")
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, value)})
        bpy.ops.object.mode_set(mode="OBJECT")
        
        return {"name": name, "extruded": value, "vertices": len(obj.data.vertices)}
    
    def handle_bevel(self, params):
        """Bevel edges of an object."""
        name = params.get("name", "")
        width = params.get("width", 0.1)
        segments = params.get("segments", 3)
        
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            raise ValueError(f"Mesh object '{name}' not found")
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.bevel(offset=width, segments=segments)
        bpy.ops.object.mode_set(mode="OBJECT")
        
        return {"name": name, "width": width, "segments": segments}
    
    def handle_subdivide(self, params):
        """Subdivide mesh."""
        name = params.get("name", "")
        cuts = params.get("cuts", 1)
        
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            raise ValueError(f"Mesh object '{name}' not found")
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.subdivide(number_cuts=cuts)
        bpy.ops.object.mode_set(mode="OBJECT")
        
        return {"name": name, "cuts": cuts, "vertices": len(obj.data.vertices)}
    
    # ─── Export ───────────────────────────────────────────────────────────
    
    def handle_export_fbx(self, params):
        """Export selected or all objects as FBX."""
        filepath = params.get("filepath", "")
        selected_only = params.get("selected_only", False)
        
        if not filepath:
            raise ValueError("filepath is required")
        if not filepath.lower().endswith(".fbx"):
            filepath += ".fbx"
        
        # Blender 5.0+ changed FBX export API — build kwargs dynamically
        kwargs = {
            "filepath": filepath,
            "use_selection": selected_only,
        }
        # apply_modifiers was renamed/removed in Blender 5.0
        try:
            bpy.ops.export_scene.fbx(**kwargs, apply_modifiers=params.get("apply_modifiers", True),
                                     mesh_smooth_type=params.get("smoothing", "FACE"))
        except TypeError:
            # Blender 5.0+: no apply_modifiers/mesh_smooth_type params
            bpy.ops.export_scene.fbx(**kwargs)
        
        return {"filepath": filepath, "selected_only": selected_only}
    
    def handle_export_obj(self, params):
        """Export as OBJ."""
        filepath = params.get("filepath", "")
        if not filepath:
            raise ValueError("filepath is required")
        if not filepath.lower().endswith(".obj"):
            filepath += ".obj"
        
        bpy.ops.wm.obj_export(filepath=filepath)
        return {"filepath": filepath}
    
    def handle_export_gltf(self, params):
        """Export as glTF/GLB."""
        filepath = params.get("filepath", "")
        if not filepath:
            raise ValueError("filepath is required")
        
        export_format = "GLB" if filepath.lower().endswith(".glb") else "GLTF_SEPARATE"
        bpy.ops.export_scene.gltf(filepath=filepath, export_format=export_format)
        return {"filepath": filepath, "format": export_format}
    
    # ─── Scene ───────────────────────────────────────────────────────────
    
    def handle_get_scene_info(self, params):
        """Get scene information."""
        return {
            "name": bpy.context.scene.name,
            "objects": len(bpy.data.objects),
            "meshes": len(bpy.data.meshes),
            "materials": len(bpy.data.materials),
            "frame_current": bpy.context.scene.frame_current,
            "frame_start": bpy.context.scene.frame_start,
            "frame_end": bpy.context.scene.frame_end,
            "render_engine": bpy.context.scene.render.engine,
            "resolution": [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y],
        }
    
    def handle_clear_scene(self, params):
        """Remove all objects from the scene."""
        keep_camera = params.get("keep_camera", True)
        keep_lights = params.get("keep_lights", False)
        
        removed = 0
        for obj in list(bpy.data.objects):
            if keep_camera and obj.type == "CAMERA":
                continue
            if keep_lights and obj.type == "LIGHT":
                continue
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
        
        return {"removed": removed}
    
    def handle_save_file(self, params):
        """Save the current Blender file."""
        filepath = params.get("filepath", "")
        if filepath:
            bpy.ops.wm.save_as_mainfile(filepath=filepath)
        else:
            bpy.ops.wm.save_mainfile()
        
        return {"filepath": bpy.data.filepath}
    
    # ─── UV ──────────────────────────────────────────────────────────────
    
    def handle_smart_uv_project(self, params):
        """Auto UV unwrap an object."""
        name = params.get("name", "")
        angle_limit = params.get("angle_limit", 66.0)
        
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            raise ValueError(f"Mesh object '{name}' not found")
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=radians(angle_limit))
        bpy.ops.object.mode_set(mode="OBJECT")
        
        return {"name": name, "angle_limit": angle_limit}


# ─── Blender Addon Registration ─────────────────────────────────────────────

class BLUEPRINTLLM_OT_start_server(bpy.types.Operator):
    bl_idname = "blueprintllm.start_server"
    bl_label = "Start Server"
    bl_description = "Start the Arcwright TCP command server"
    
    def execute(self, context):
        global server_instance
        if server_instance is None:
            server_instance = BlenderCommandServer()
        server_instance.start()
        self.report({"INFO"}, f"Server started on port {SERVER_PORT}")
        return {"FINISHED"}


class BLUEPRINTLLM_OT_stop_server(bpy.types.Operator):
    bl_idname = "blueprintllm.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the Arcwright TCP command server"
    
    def execute(self, context):
        global server_instance
        if server_instance:
            server_instance.stop()
            self.report({"INFO"}, "Server stopped")
        return {"FINISHED"}


class BLUEPRINTLLM_PT_panel(bpy.types.Panel):
    bl_label = "Arcwright"
    bl_idname = "BLUEPRINTLLM_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Arcwright"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("blueprintllm.start_server", icon="PLAY")
        layout.operator("blueprintllm.stop_server", icon="PAUSE")
        
        global server_instance
        if server_instance and server_instance.running:
            layout.label(text=f"Port: {SERVER_PORT}", icon="CHECKMARK")
            layout.label(text=f"Commands: {len(server_instance.handlers)}")
        else:
            layout.label(text="Server stopped", icon="X")


classes = (
    BLUEPRINTLLM_OT_start_server,
    BLUEPRINTLLM_OT_stop_server,
    BLUEPRINTLLM_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Patch procedural texture handlers onto the server class
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    if addon_dir not in sys.path:
        sys.path.insert(0, addon_dir)
    try:
        from blender_procedural_textures import _patch_server, register_procedural_handlers
        _patch_server(BlenderCommandServer)
    except ImportError:
        print("[Arcwright] Warning: blender_procedural_textures.py not found — procedural textures disabled")

    # Auto-start server
    global server_instance
    server_instance = BlenderCommandServer()

    # Register procedural handlers on the instance
    try:
        from blender_procedural_textures import register_procedural_handlers
        register_procedural_handlers(server_instance)
    except (ImportError, NameError):
        pass

    server_instance.start()


def unregister():
    global server_instance
    if server_instance:
        server_instance.stop()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
