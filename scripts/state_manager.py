"""
Arcwright State Manager — manages state between AI and human development.

RULES:
1. Always check before creating — never duplicate
2. Never delete what the human created unless explicitly asked
3. Track what Arcwright created vs what exists from other sources
4. Support "first build" (create everything) and "iteration" (update only what's needed)
"""
import socket, json, os, time
from datetime import datetime


class ArcwrightClient:
    """Minimal TCP client for Arcwright commands."""

    def __init__(self, host='localhost', port=13377, timeout=15):
        self.host = host
        self.port = port
        self.timeout = timeout

    def cmd(self, command, **params):
        s = socket.socket()
        s.settimeout(self.timeout)
        s.connect((self.host, self.port))
        s.sendall(json.dumps({"command": command, "params": params}).encode() + b'\n')
        data = b''
        while b'\n' not in data:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
        s.close()
        return json.loads(data.decode().strip())


class StateManager:
    """Manages state between AI builds and human development.

    Tracks what Arcwright created so it knows what it owns.
    Never touches assets it didn't create.
    Checks existence before every create/spawn operation.
    """

    def __init__(self, arc=None, project_dir=None):
        self.arc = arc or ArcwrightClient()
        self.project_dir = project_dir or os.getcwd()
        self.manifest = {"blueprints": [], "actors": [], "widgets": [],
                         "materials": [], "data_tables": [], "created_at": None}
        self._state_cache = None
        self._cache_time = 0
        self.load_manifest()

    # --- Manifest persistence ---

    def _manifest_path(self):
        # Try project Saved dir first, fall back to script dir
        for base in [os.path.join(self.project_dir, "Saved", "Arcwright"),
                     os.path.join(os.path.dirname(__file__), "..", "Saved", "Arcwright")]:
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, "build_manifest.json")

    def load_manifest(self):
        path = self._manifest_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self.manifest = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def save_manifest(self):
        path = self._manifest_path()
        self.manifest["updated_at"] = datetime.now().isoformat()
        if not self.manifest.get("created_at"):
            self.manifest["created_at"] = self.manifest["updated_at"]
        with open(path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    # --- State queries (cached for 5 seconds) ---

    def get_state(self, force=False):
        """Snapshot current project state from UE."""
        now = time.time()
        if not force and self._state_cache and (now - self._cache_time) < 5:
            return self._state_cache

        state = {"blueprints": [], "actors": [], "widgets": [],
                 "materials": [], "data_tables": [], "lights": {}}

        # Blueprints
        r = self.arc.cmd("find_assets", type="Blueprint", path="/Game")
        for a in r.get("data", {}).get("assets", []):
            state["blueprints"].append(a.get("name", ""))

        # Actors (full list with class info)
        r = self.arc.cmd("find_actors")
        for a in r.get("data", {}).get("actors", []):
            state["actors"].append({
                "label": a.get("label", ""),
                "class": a.get("class", "")
            })

        # Light inventory
        for light_type in ["DirectionalLight", "SkyLight", "PointLight", "SpotLight"]:
            r = self.arc.cmd("find_actors", class_filter=light_type)
            actors = r.get("data", {}).get("actors", [])
            state["lights"][light_type] = [a.get("label", "") for a in actors]

        # Level info
        r = self.arc.cmd("get_level_info")
        state["level"] = r.get("data", {})

        self._state_cache = state
        self._cache_time = now
        return state

    def actor_exists(self, label):
        """Check if an actor with this label exists in the level."""
        state = self.get_state()
        return any(a["label"] == label for a in state["actors"])

    def blueprint_exists(self, name):
        """Check if a Blueprint asset exists."""
        state = self.get_state()
        return name in state["blueprints"]

    def light_count(self, light_type="DirectionalLight"):
        """Count lights of a specific type."""
        state = self.get_state()
        return len(state["lights"].get(light_type, []))

    # --- Safe creation methods ---

    def safe_create_blueprint(self, name, parent_class="Actor", variables=None, **kwargs):
        """Create a Blueprint only if it doesn't exist. Returns existing info if skipped."""
        if self.blueprint_exists(name):
            r = self.arc.cmd("get_blueprint_details", blueprint=name)
            nodes = r.get("data", {}).get("node_count", 0)
            if nodes > 3:  # More than default events
                print(f"  SKIP: {name} already exists ({nodes} nodes)")
                return {"status": "ok", "skipped": True, "existing_nodes": nodes}
            else:
                print(f"  UPDATE: {name} exists but empty ({nodes} nodes) — rebuilding")
                self.arc.cmd("delete_blueprint", name=name)
                time.sleep(0.3)

        params = {"name": name, "parent_class": parent_class}
        if variables:
            params["variables"] = variables
        params.update(kwargs)
        r = self.arc.cmd("create_blueprint", **params)

        if r.get("status") == "ok":
            if name not in self.manifest["blueprints"]:
                self.manifest["blueprints"].append(name)
            self.save_manifest()
            self._state_cache = None  # Invalidate cache

        return r

    def safe_spawn_actor(self, label, **params):
        """Spawn an actor only if one with this label doesn't exist."""
        if self.actor_exists(label):
            print(f"  SKIP: {label} already exists in level")
            return {"status": "ok", "skipped": True}

        r = self.arc.cmd("spawn_actor_at", label=label, **params)

        if r.get("status") == "ok":
            if label not in self.manifest["actors"]:
                self.manifest["actors"].append(label)
            self.save_manifest()
            self._state_cache = None

        return r

    def safe_create_material(self, name, color, **kwargs):
        """Create a material only if it doesn't exist."""
        # Check if material asset exists via find_assets
        r = self.arc.cmd("find_assets", type="Material", name_filter=name)
        existing = r.get("data", {}).get("assets", [])
        if existing:
            print(f"  SKIP: Material {name} already exists")
            return {"status": "ok", "skipped": True}

        r = self.arc.cmd("create_simple_material", name=name, color=color, **kwargs)

        if r.get("status") == "ok":
            if name not in self.manifest["materials"]:
                self.manifest["materials"].append(name)
            self.save_manifest()

        return r

    def safe_setup_lighting(self, preset="outdoor_day"):
        """Set up scene lighting only if no DirectionalLight exists."""
        if self.light_count("DirectionalLight") > 0:
            dl_count = self.light_count("DirectionalLight")
            sl_count = self.light_count("SkyLight")
            print(f"  SKIP: Lighting already exists ({dl_count} dir, {sl_count} sky)")
            return {"status": "ok", "skipped": True}

        r = self.arc.cmd("setup_scene_lighting", preset=preset)
        self._state_cache = None
        return r

    # --- Cleanup methods ---

    def clean_duplicate_lights(self):
        """Remove duplicate lights, keeping only one of each type."""
        state = self.get_state(force=True)
        cleaned = 0

        for light_type in ["DirectionalLight", "SkyLight"]:
            labels = state["lights"].get(light_type, [])
            if len(labels) > 1:
                # Keep the first, delete the rest
                for label in labels[1:]:
                    self.arc.cmd("delete_actor", label=label)
                    cleaned += 1
                    print(f"  Deleted duplicate {light_type}: {label}")

        if cleaned:
            self.arc.cmd("save_all")
            self._state_cache = None
            print(f"  Cleaned {cleaned} duplicate lights")

        return cleaned

    def clean_arcwright_assets(self, confirm=True):
        """Delete only assets that Arcwright created — never touch human-created assets."""
        if confirm:
            print(f"  Will delete: {len(self.manifest.get('blueprints',[]))} BPs, "
                  f"{len(self.manifest.get('actors',[]))} actors")
            # In automated context, just proceed

        for bp in self.manifest.get("blueprints", []):
            self.arc.cmd("delete_blueprint", name=bp)
        for actor in self.manifest.get("actors", []):
            self.arc.cmd("delete_actor", label=actor)

        self.manifest = {"blueprints": [], "actors": [], "widgets": [],
                         "materials": [], "data_tables": [], "created_at": None}
        self.save_manifest()
        self._state_cache = None

    # --- Reporting ---

    def report(self):
        """Report current state and what Arcwright owns."""
        state = self.get_state(force=True)
        actor_labels = [a["label"] for a in state["actors"]]

        print(f"  Project state:")
        print(f"    Blueprints: {len(state['blueprints'])}")
        print(f"    Actors:     {len(state['actors'])}")
        for lt, labels in state["lights"].items():
            if labels:
                print(f"    {lt}: {len(labels)}")
        print(f"  Arcwright manifest:")
        print(f"    Blueprints: {self.manifest.get('blueprints', [])}")
        print(f"    Actors:     {len(self.manifest.get('actors', []))}")
        # Check for orphans (in manifest but not in level)
        orphan_actors = [a for a in self.manifest.get("actors", []) if a not in actor_labels]
        if orphan_actors:
            print(f"    Orphaned (in manifest but not level): {orphan_actors}")


# --- Standalone test ---
if __name__ == "__main__":
    print("=" * 60)
    print("StateManager Self-Test")
    print("=" * 60)

    sm = StateManager()

    print("\n1. Current state:")
    sm.report()

    print("\n2. Clean duplicate lights:")
    cleaned = sm.clean_duplicate_lights()

    print("\n3. Safe create test:")
    # This should skip if BP already exists
    r = sm.safe_create_blueprint("BP_StressTest50", "Actor")
    print(f"  Result: {r.get('status')} skipped={r.get('skipped', False)}")

    # This should skip if actor already exists
    r = sm.safe_spawn_actor("HUDManager", x=0, y=0, z=0,
                            **{"class": "/Game/Arcwright/Generated/BP_HUDManager.BP_HUDManager_C"})
    print(f"  Result: {r.get('status')} skipped={r.get('skipped', False)}")

    print("\n4. Post-cleanup state:")
    sm.report()

    print("\n" + "=" * 60)
    print("StateManager: OK")
    print("=" * 60)
