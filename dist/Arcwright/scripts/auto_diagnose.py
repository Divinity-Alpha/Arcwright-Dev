"""
Arcwright Auto-Diagnose — scans all UE message sources and attempts fixes.
Usage: PYTHONIOENCODING=utf-8 python scripts/auto_diagnose.py
"""
import socket, json, time

def cmd(command, **params):
    s = socket.socket(); s.settimeout(15)
    s.connect(('localhost', 13377))
    s.sendall(json.dumps({"command": command, "params": params}).encode() + b'\n')
    data = b''
    while b'\n' not in data:
        chunk = s.recv(65536)
        if not chunk: break
        data += chunk
    s.close()
    return json.loads(data.decode().strip())

KNOWN_FIXES = {
    "multiple skylight": {
        "diagnosis": "Multiple SkyLight actors — only one needed",
        "action": "delete_extra_skylights"
    },
    "multiple directionallight": {
        "diagnosis": "Multiple DirectionalLight actors — competing shadows",
        "action": "delete_extra_dirlights"
    },
    "no playerstart": {
        "diagnosis": "No PlayerStart — player spawns at origin",
        "action": "spawn_playerstart"
    },
    "compile error": {
        "diagnosis": "Blueprint has compile errors",
        "action": "report_only"
    },
    "no mesh": {
        "diagnosis": "StaticMeshActor with no mesh assigned",
        "action": "report_only"
    },
}


def scan_all():
    """Scan all message sources."""
    issues = []

    # 1. Map check
    print("  Scanning: Map Check...")
    r = cmd("run_map_check")
    if r["status"] == "ok":
        d = r["data"]
        for err in d.get("errors", []):
            issues.append({"source": "MapCheck", "severity": "error", "text": str(err)})
        for warn in d.get("warnings", []):
            issues.append({"source": "MapCheck", "severity": "warning", "text": str(warn)})
        print(f"    {d.get('error_count',0)} errors, {d.get('warning_count',0)} warnings")

    # 2. Blueprint compilation
    print("  Scanning: Blueprint compilation...")
    r = cmd("verify_all_blueprints")
    if r["status"] == "ok":
        d = r["data"]
        fail_count = d.get("fail", 0)
        for bp in d.get("results", []):
            if not bp.get("compiles", True):
                for err in bp.get("errors", []):
                    issues.append({"source": "Blueprint", "severity": "error",
                                   "text": f"{bp.get('name','?')}: {err}"})
        print(f"    {d.get('pass',0)}/{d.get('total',0)} pass, {fail_count} fail")

    # 3. Message log (errors and warnings)
    print("  Scanning: Message Log...")
    r = cmd("get_message_log", severity="error", lines=50)
    if r["status"] == "ok":
        msgs = r["data"].get("messages", [])
        for m in msgs:
            issues.append({"source": "Log", "severity": m.get("severity","error"),
                           "text": m.get("text","")[:200]})
        print(f"    {len(msgs)} error messages")

    r = cmd("get_message_log", severity="warning", lines=50)
    if r["status"] == "ok":
        msgs = r["data"].get("messages", [])
        for m in msgs:
            # Skip common noise
            text = m.get("text", "")
            if "ButtonHoverHint" in text or "FilterPlugin" in text:
                continue
            issues.append({"source": "Log", "severity": "warning",
                           "text": text[:200]})
        print(f"    {len(msgs)} warning messages (after filtering noise)")

    return issues


def attempt_fixes(issues):
    """Try to auto-fix known issues."""
    fixed = 0
    for issue in issues:
        text = issue["text"].lower()

        if "multiple skylight" in text:
            print(f"  FIX: Removing extra SkyLights...")
            r = cmd("find_actors", class_filter="SkyLight")
            actors = r.get("data", {}).get("actors", [])
            if len(actors) > 1:
                for a in actors[1:]:
                    label = a.get("label", "")
                    if label:
                        cmd("delete_actor", label=label)
                        print(f"    Deleted: {label}")
                        fixed += 1

        elif "multiple directionallight" in text:
            print(f"  FIX: Removing extra DirectionalLights...")
            r = cmd("find_actors", class_filter="DirectionalLight")
            actors = r.get("data", {}).get("actors", [])
            if len(actors) > 1:
                for a in actors[1:]:
                    label = a.get("label", "")
                    if label:
                        cmd("delete_actor", label=label)
                        print(f"    Deleted: {label}")
                        fixed += 1

        elif "no playerstart" in text:
            print(f"  FIX: Spawning PlayerStart...")
            cmd("spawn_actor_at", label="PlayerStart", x=0, y=0, z=100,
                **{"class": "PlayerStart"})
            fixed += 1

    return fixed


if __name__ == "__main__":
    print("=" * 60)
    print("ARCWRIGHT AUTO-DIAGNOSE")
    print("=" * 60)

    print("\nPhase 1: Scanning all message sources...")
    issues = scan_all()

    print(f"\nFound {len(issues)} issues:")
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    for issue in issues:
        marker = "ERROR" if issue["severity"] == "error" else "WARN"
        print(f"  [{marker}] {issue['source']}: {issue['text'][:100]}")

    print(f"\nPhase 2: Attempting auto-fixes...")
    fixed = attempt_fixes(issues)
    print(f"  Fixed: {fixed}")

    if fixed > 0:
        print(f"\nPhase 3: Re-scanning after fixes...")
        issues_after = scan_all()
        remaining = len(issues_after)
        print(f"  Before: {len(issues)} issues")
        print(f"  After:  {remaining} issues")
        print(f"  Fixed:  {len(issues) - remaining}")

    print(f"\n{'='*60}")
    print("AUTO-DIAGNOSE COMPLETE")
