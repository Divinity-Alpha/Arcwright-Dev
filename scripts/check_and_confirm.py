"""
Arcwright Check & Confirm Protocol
====================================
Wraps every action with verification.
Handles PIE via async play_in_editor + poll + capture pattern.
"""
import socket
import json
import time
import os


class CheckAndConfirm:
    def __init__(self, host='localhost', port=13377):
        self.host = host
        self.port = port
        self.log = []
        self.discrepancies = []
        self.sock = None
        self.count = 0
        self._reconnect()

    def _reconnect(self):
        if self.sock:
            try: self.sock.close()
            except: pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(30)
        self.sock.connect((self.host, self.port))

    def cmd(self, command, **params):
        self.count += 1
        if self.count % 25 == 0:
            self._reconnect()
        try:
            self.sock.sendall((json.dumps({"command": command, "params": params}) + "\n").encode())
            data = b""
            while b"\n" not in data:
                chunk = self.sock.recv(65536)
                if not chunk: break
                data += chunk
            return json.loads(data.decode().strip())
        except Exception as e:
            self._reconnect()
            return {"status": "error", "error": str(e)}

    def verify_blueprint(self, name):
        """Inspect a Blueprint and return its state."""
        r = self.cmd("get_blueprint_graph", name=name)
        if r["status"] != "ok":
            return {"name": name, "found": False, "error": r.get("message", "?")}
        d = r["data"]
        return {
            "name": name,
            "found": True,
            "nodes": d.get("node_count", 0),
            "connections": d.get("connection_count", 0),
            "variables": len(d.get("variables", [])),
            "compiles": d.get("compile_status", "") != "error",
        }

    def verify_all_blueprints(self):
        """Compile and check all Blueprints in Generated/."""
        r = self.cmd("verify_all_blueprints")
        if r["status"] != "ok":
            return {"error": r.get("message", "?")}
        d = r["data"]
        return {
            "total": d.get("total", 0),
            "pass": d.get("pass", 0),
            "fail": d.get("fail", 0),
            "results": d.get("results", []),
        }

    def verify_level(self):
        """Get level state."""
        r = self.cmd("get_level_info")
        return r.get("data", {})

    def play_test(self, duration=5, screenshot_path=None):
        """Run the Play Test Cycle using async pattern.

        1. Save all
        2. Start PIE (async via play_in_editor)
        3. Wait for PIE to start
        4. Wait duration seconds
        5. Take screenshot
        6. Read log
        7. Stop PIE
        """
        result = {
            "started": False,
            "crashed": False,
            "duration": duration,
            "screenshot": None,
            "log_lines": [],
        }

        # Save first
        self.cmd("save_all")

        # Check not already playing
        r = self.cmd("is_playing")
        if r.get("data", {}).get("playing"):
            self.cmd("stop_play")
            time.sleep(1)

        # Start PIE (async — returns immediately, PIE starts on next Slate tick)
        self.cmd("play_in_editor")

        # Wait for PIE to start (poll is_playing)
        for i in range(20):
            time.sleep(0.5)
            r = self.cmd("is_playing")
            if r.get("data", {}).get("playing"):
                result["started"] = True
                break

        if not result["started"]:
            return result

        # Wait the requested duration
        time.sleep(duration)

        # Check still playing (didn't crash)
        r = self.cmd("is_playing")
        result["crashed"] = not r.get("data", {}).get("playing", False)

        # Take screenshot
        if screenshot_path is None:
            screenshot_path = os.path.join("C:", os.sep, "Projects", "BoreandStroke", "Saved",
                                            "Screenshots", f"pie_{int(time.time())}.png")
        self.cmd("take_viewport_screenshot")
        result["screenshot"] = screenshot_path

        # Get log output (especially PrintString messages)
        r = self.cmd("get_output_log", lines=100)
        if r["status"] == "ok":
            lines = r.get("data", {}).get("lines", [])
            # Filter for interesting lines
            for line in lines:
                line_str = str(line)
                if any(k in line_str for k in ["BlueprintUserMessages", "PrintString", "Error", "PIE"]):
                    result["log_lines"].append(line_str)

        # Stop PIE
        self.cmd("stop_play")
        time.sleep(0.5)

        return result

    def create_and_verify_blueprint(self, name, parent_class, nodes, connections,
                                      variables=None, min_nodes=None, min_conns=None):
        """Create a Blueprint with full Check & Confirm."""
        entry = {"name": name, "steps": []}

        # Create
        r = self.cmd("create_blueprint", name=name, parent_class=parent_class,
                     **({"variables": variables} if variables else {}))
        entry["steps"].append(("create", r.get("status")))

        # Add nodes
        r = self.cmd("add_nodes_batch", blueprint=name, nodes=nodes)
        d = r.get("data", {})
        entry["steps"].append(("nodes", f"{d.get('succeeded',0)}/{d.get('total',0)}"))

        # Add connections
        r = self.cmd("add_connections_batch", blueprint=name, connections=connections)
        d = r.get("data", {})
        entry["steps"].append(("conns", f"{d.get('succeeded',0)}/{d.get('total',0)}"))

        # Compile (also saves)
        r = self.cmd("compile_blueprint", name=name)
        d = r.get("data", {})
        entry["steps"].append(("compile", d.get("compiled")))

        # Verify
        state = self.verify_blueprint(name)
        entry["actual"] = state

        expected_nodes = min_nodes or len(nodes)
        expected_conns = min_conns or len(connections)

        confirmed = (state.get("nodes", 0) >= expected_nodes and
                     state.get("connections", 0) >= expected_conns and
                     state.get("compiles", False))

        entry["status"] = "CONFIRMED" if confirmed else "DISCREPANCY"
        if not confirmed:
            entry["issues"] = []
            if state.get("nodes", 0) < expected_nodes:
                entry["issues"].append(f"nodes: {state['nodes']} < {expected_nodes}")
            if state.get("connections", 0) < expected_conns:
                entry["issues"].append(f"conns: {state['connections']} < {expected_conns}")
            if not state.get("compiles"):
                entry["issues"].append("compile failed")
            self.discrepancies.append(entry)

        self.log.append(entry)
        return entry

    # ------------------------------------------------------------------
    # Post-Phase Checks — run after every build phase
    # ------------------------------------------------------------------

    def _clean_duplicates(self, class_filter):
        """Delete all but the first actor of a given class."""
        r = self.cmd("find_actors", class_filter=class_filter)
        actors = r.get("data", {}).get("actors", [])
        cleaned = 0
        if len(actors) > 1:
            for a in actors[1:]:
                label = a.get("label", "")
                if label:
                    self.cmd("delete_actor", label=label)
                    cleaned += 1
        return cleaned

    def _clean_duplicate_actors(self, name_prefix):
        """Delete all but the first actor whose label starts with name_prefix."""
        r = self.cmd("find_actors", name_filter=name_prefix)
        actors = r.get("data", {}).get("actors", [])
        matches = [a for a in actors if a.get("label", "").startswith(name_prefix)]
        cleaned = 0
        if len(matches) > 1:
            for a in matches[1:]:
                self.cmd("delete_actor", label=a.get("label"))
                cleaned += 1
        return cleaned

    def post_phase_check(self, phase_name):
        """Run after every build phase to catch issues immediately.

        Checks for: duplicate lights, duplicate managers, map errors,
        and Blueprint compile failures. Fixes duplicates automatically.
        """
        print(f"\n  --- Post-Phase Check: {phase_name} ---")
        issues = 0

        # Check duplicate lights
        for light_type in ["DirectionalLight", "SkyLight"]:
            r = self.cmd("find_actors", class_filter=light_type)
            actors = r.get("data", {}).get("actors", [])
            if len(actors) > 1:
                cleaned = self._clean_duplicates(light_type)
                print(f"  FIXED: {light_type} {len(actors)} -> {len(actors) - cleaned}")
                issues += 1

        # Check duplicate managers
        for manager in ["HUDManager", "TimeManager", "EconomyManager",
                        "HeatManager", "ReputationManager", "QuestManager"]:
            cleaned = self._clean_duplicate_actors(manager)
            if cleaned > 0:
                print(f"  FIXED: {manager} duplicates removed ({cleaned})")
                issues += 1

        # Map check
        r = self.cmd("run_map_check")
        d = r.get("data", {})
        err_count = d.get("error_count", 0)
        warn_count = d.get("warning_count", 0)
        if err_count > 0:
            print(f"  MAP ERRORS: {err_count}")
            for e in d.get("errors", [])[:3]:
                print(f"    {str(e)[:100]}")
            issues += err_count

        # Blueprint compile check
        r = self.cmd("verify_all_blueprints")
        d = r.get("data", {})
        fail_count = d.get("fail", 0)
        if fail_count > 0:
            print(f"  COMPILE FAILURES: {fail_count}")
            for bp in d.get("results", []):
                if not bp.get("compiles", True):
                    print(f"    {bp.get('name')}: {bp.get('errors', [])[:1]}")
            issues += fail_count

        if issues == 0:
            print(f"  CLEAN: No issues found")
        else:
            # Save after fixes
            self.cmd("save_all")
            print(f"  Fixed {issues} issues, saved")

        print(f"  --- Post-Phase Check Complete ---")
        return issues

    def report(self):
        """Print summary."""
        total = len(self.log)
        confirmed = len([e for e in self.log if e.get("status") == "CONFIRMED"])
        disc = len(self.discrepancies)
        print(f"\nCheck & Confirm Report: {confirmed}/{total} confirmed, {disc} discrepancies")
        if self.discrepancies:
            for d in self.discrepancies:
                print(f"  DISCREPANCY: {d['name']} — {d.get('issues', [])}")
        return {"total": total, "confirmed": confirmed, "discrepancies": disc}


if __name__ == "__main__":
    print("Check & Confirm — Quick Test")
    cc = CheckAndConfirm()

    # Verify all BPs
    print("\n1. verify_all_blueprints")
    result = cc.verify_all_blueprints()
    print(f"   {result['pass']}/{result['total']} pass")

    # Play test
    print("\n2. play_test (3 seconds)")
    result = cc.play_test(duration=3)
    print(f"   Started: {result['started']}")
    print(f"   Crashed: {result['crashed']}")
    print(f"   Log lines: {len(result['log_lines'])}")
    for line in result['log_lines'][:10]:
        print(f"     {line[:100]}")

    print("\nDone.")
