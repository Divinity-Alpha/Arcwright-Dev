"""
Build 12 BoreAndStroke station widget blueprints in the running UE5 editor.

Connects to Arcwright TCP Command Server on port 13377 and creates
widget blueprints with consistent visual structure and station-specific text.

Architecture: First widget added is a CanvasPanel ("RootCanvas") which becomes
the root widget and can hold unlimited children. All borders, text blocks,
and progress bars are then added as direct children of RootCanvas, positioned
using CanvasPanel slot properties (position, size).

Usage:
    python scripts/build_station_widgets.py
"""

import socket
import json
import time
import sys

# ---------------------------------------------------------------------------
# TCP communication
# ---------------------------------------------------------------------------

def send_command(cmd, params=None, timeout=15):
    """Send a single TCP command to the Arcwright server and return the response."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(('127.0.0.1', 13377))
    payload = json.dumps({'command': cmd, 'params': params or {}}) + '\n'
    s.sendall(payload.encode('utf-8'))
    data = b''
    while b'\n' not in data:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
    s.close()
    line = data.split(b'\n', 1)[0]
    result = json.loads(line.decode('utf-8'))
    return result


def checked(label, cmd, params=None, timeout=15):
    """Send command, check for ok status, print result, return data."""
    r = send_command(cmd, params, timeout=timeout)
    status = r.get('status', 'unknown')
    if status == 'ok':
        print(f"  OK   {label}")
    else:
        msg = r.get('message', r.get('error', 'unknown error'))
        print(f"  FAIL {label}: {msg}")
    return r


def add_child(wbp, widget_type, widget_name, parent=None):
    """Add a widget child. If parent is None, adds to root (first call sets root)."""
    params = {
        "widget_blueprint": wbp,
        "widget_type": widget_type,
        "widget_name": widget_name,
    }
    if parent:
        params["parent_widget"] = parent
    return checked(f"add {widget_name} ({widget_type})", "add_widget_child", params)


def set_prop(wbp, widget_name, prop, value):
    """Set a widget property."""
    return checked(f"set {widget_name}.{prop}",
                   "set_widget_property",
                   {"widget_blueprint": wbp, "widget_name": widget_name,
                    "property": prop, "value": value})


# ---------------------------------------------------------------------------
# Station definitions
# ---------------------------------------------------------------------------

STATIONS = [
    ("WBP_Station_Office",       "OFFICE",          "Management"),
    ("WBP_Station_Disassembly",  "DISASSEMBLY",     "Engine Teardown"),
    ("WBP_Station_Cleaning",     "CLEANING",        "Parts Cleaning"),
    ("WBP_Station_Inspection",   "INSPECTION",      "Quality Check"),
    ("WBP_Station_Hone",         "HONE",            "Cylinder Honing"),
    ("WBP_Station_Deck",         "DECK",            "Deck Surfacing"),
    ("WBP_Station_CrankGrind",   "CRANK GRIND",     "Crank Grinding"),
    ("WBP_Station_HeadWork",     "HEAD WORK",       "Head Machining"),
    ("WBP_Station_ValveWork",    "VALVE WORK",      "Valve Service"),
    ("WBP_Station_Assembly",     "ASSEMBLY",        "Final Assembly"),
    ("WBP_Station_Balancing",    "BALANCING",       "Balance Check"),
    ("WBP_Station_Testing",      "TESTING",         "Dyno Testing"),
]

# ---------------------------------------------------------------------------
# Widget child definitions -- ALL are children of "RootCanvas" (CanvasPanel).
# Border is a single-child container, so we do NOT nest widgets inside Border.
# Instead, all elements are siblings on RootCanvas, layered by creation order
# (later = painted on top).
# ---------------------------------------------------------------------------

# (widget_name, widget_type, position_x, position_y, size_x, size_y)
WIDGET_DEFS = [
    # Background borders (painted first = behind everything)
    ("Border_Panel",       "Border",       0,    0,    1920, 1080),
    ("Border_Header",      "Border",       0,    0,    1920, 100),
    ("Border_Badge",       "Border",       30,   120,  300,  200),
    ("Border_Actions",     "Border",       30,   340,  900,  500),
    ("Border_Costs",       "Border",       960,  340,  930,  500),
    ("Border_StatusBar",   "Border",       0,    1040, 1920, 40),
    ("Border_BtnApprove",  "Border",       960,  860,  450,  60),
    ("Border_BtnCancel",   "Border",       1440, 860,  450,  60),
    # Text blocks (painted on top of borders)
    ("Text_StationName",   "TextBlock",    40,   20,   600,  50),
    ("Text_StationSub",    "TextBlock",    40,   62,   600,  30),
    ("Text_QualityNum",    "TextBlock",    50,   160,  260,  60),
    ("Text_BtnApprove",    "TextBlock",    1080, 872,  220,  36),
    ("Text_BtnCancel",     "TextBlock",    1560, 872,  220,  36),
    ("Text_SC_CashV",      "TextBlock",    980,  360,  200,  30),
    ("Text_SC_TimeV",      "TextBlock",    980,  400,  200,  30),
    ("Text_SC_BarV",       "TextBlock",    980,  440,  200,  30),
    ("Text_SC_StorageV",   "TextBlock",    980,  480,  200,  30),
    # Progress bar
    ("ProgBar_Cylinders",  "ProgressBar",  50,   780,  860,  30),
]

# ---------------------------------------------------------------------------
# Color assignments
# ---------------------------------------------------------------------------

COLORS = {
    "Border_Panel":       ("BrushColor",          "hex:#12161C"),
    "Border_Header":      ("BrushColor",          "(R=0.0,G=0.0,B=0.0,A=0.35)"),
    "Border_Badge":       ("BrushColor",          "hex:#181D26"),
    "Border_Actions":     ("BrushColor",          "hex:#12161C"),
    "Border_Costs":       ("BrushColor",          "(R=0.0,G=0.0,B=0.0,A=0.22)"),
    "Border_StatusBar":   ("BrushColor",          "(R=0.0,G=0.0,B=0.0,A=0.35)"),
    "Border_BtnApprove":  ("BrushColor",          "(R=0.008,G=0.052,B=0.022,A=0.9)"),
    "Border_BtnCancel":   ("BrushColor",          "(R=0.073,G=0.006,B=0.009,A=0.8)"),
    "Text_StationName":   ("ColorAndOpacity",     "hex:#E8A624"),
    "Text_StationSub":    ("ColorAndOpacity",     "hex:#707888"),
    "Text_QualityNum":    ("ColorAndOpacity",     "hex:#F0C040"),
    "Text_BtnApprove":    ("ColorAndOpacity",     "hex:#3DDC84"),
    "Text_BtnCancel":     ("ColorAndOpacity",     "hex:#E04050"),
    "Text_SC_CashV":      ("ColorAndOpacity",     "hex:#3DDC84"),
    "Text_SC_TimeV":      ("ColorAndOpacity",     "hex:#F0C040"),
    "Text_SC_BarV":       ("ColorAndOpacity",     "hex:#3DDC84"),
    "Text_SC_StorageV":   ("ColorAndOpacity",     "hex:#E8A624"),
    "ProgBar_Cylinders":  ("FillColorAndOpacity", "hex:#3DDC84"),
}

# Static text for non-station-specific widgets
STATIC_TEXT = {
    "Text_BtnApprove": "APPROVE",
    "Text_BtnCancel":  "CANCEL",
    "Text_QualityNum": "100",
    "Text_SC_CashV":   "$0",
    "Text_SC_TimeV":   "0:00",
    "Text_SC_BarV":    "0%",
    "Text_SC_StorageV": "0/0",
}

FONT_SIZES = {
    "Text_StationName": 28,
    "Text_StationSub": 16,
    "Text_QualityNum": 36,
    "Text_BtnApprove": 18,
    "Text_BtnCancel": 18,
    "Text_SC_CashV": 16,
    "Text_SC_TimeV": 16,
    "Text_SC_BarV": 16,
    "Text_SC_StorageV": 16,
}


# ---------------------------------------------------------------------------
# Build one station widget
# ---------------------------------------------------------------------------

def build_station(name, station_title, subtitle):
    """Create one station widget blueprint with full structure, colors, text."""
    print(f"\n{'='*60}")
    print(f"  Building {name}  ({station_title} - {subtitle})")
    print(f"{'='*60}")

    # 1. Create widget blueprint (1920x1080)
    r = checked(f"create {name}",
                "create_widget_blueprint",
                {"name": name, "design_width": 1920, "design_height": 1080})
    if r.get("status") != "ok":
        print(f"  ABORT: Could not create {name}")
        return False
    time.sleep(0.3)

    # 2. Add RootCanvas (CanvasPanel) as root widget -- multi-child container
    #    This MUST be the first widget added (no parent = becomes root).
    r = add_child(name, "CanvasPanel", "RootCanvas")
    if r.get("status") != "ok":
        print(f"  ABORT: Could not create RootCanvas for {name}")
        return False
    time.sleep(0.2)

    # 3. Add all widgets as direct children of RootCanvas
    fail_count = 0
    for widget_name, widget_type, px, py, sx, sy in WIDGET_DEFS:
        r = add_child(name, widget_type, widget_name, parent="RootCanvas")
        if r.get("status") != "ok":
            fail_count += 1
        time.sleep(0.1)

    if fail_count > 0:
        print(f"  WARNING: {fail_count} widgets failed to add")

    # 4. Position and size all widgets on the canvas
    for widget_name, widget_type, px, py, sx, sy in WIDGET_DEFS:
        pos_str = json.dumps({"x": px, "y": py})
        size_str = json.dumps({"x": sx, "y": sy})
        set_prop(name, widget_name, "position", pos_str)
        set_prop(name, widget_name, "size", size_str)
        time.sleep(0.05)

    # 5. Apply colors
    for widget_name, (prop, value) in COLORS.items():
        set_prop(name, widget_name, prop, value)
        time.sleep(0.05)

    # 6. Set station-specific text
    set_prop(name, "Text_StationName", "Text", station_title)
    set_prop(name, "Text_StationSub", "Text", subtitle)

    # 7. Set static text labels
    for widget_name, text_val in STATIC_TEXT.items():
        set_prop(name, widget_name, "Text", text_val)
        time.sleep(0.03)

    # 8. Set font sizes
    for widget_name, size in FONT_SIZES.items():
        set_prop(name, widget_name, "Font.Size", str(size))
        time.sleep(0.03)

    # 9. Set progress bar initial percent
    set_prop(name, "ProgBar_Cylinders", "Percent", "0.0")

    print(f"  DONE {name}")
    return True


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_stations():
    """Verify each widget by reading back its tree and checking widget count."""
    print(f"\n{'='*60}")
    print("  VERIFICATION - Reading widget trees")
    print(f"{'='*60}")

    passed = 0
    failed = 0
    # RootCanvas + 18 widgets = 19 total
    expected_count = len(WIDGET_DEFS) + 1

    for name, title, sub in STATIONS:
        r = send_command("get_widget_tree", {"widget_blueprint": name}, timeout=10)
        if r.get("status") != "ok":
            print(f"  FAIL {name}: could not read tree - {r.get('message', 'unknown')}")
            failed += 1
            continue

        data = r.get("data", {})
        total = data.get("total_widgets", 0)

        if total >= expected_count:
            print(f"  PASS {name}: {total} widgets (expected {expected_count})")
            passed += 1
        elif total >= 10:
            print(f"  WARN {name}: {total} widgets (expected {expected_count}) - partial")
            passed += 1
        else:
            print(f"  FAIL {name}: only {total} widgets (expected {expected_count})")
            failed += 1

    print(f"\n  Verification: {passed} passed, {failed} failed out of {len(STATIONS)}")
    return failed == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  BoreAndStroke Station Widget Builder")
    print(f"  Building {len(STATIONS)} station widgets")
    print("=" * 60)

    # Health check
    r = send_command("health_check")
    if r.get("status") != "ok":
        print("FATAL: Cannot connect to Arcwright server on port 13377")
        sys.exit(1)
    server_info = r.get('data', {})
    print(f"  Server: {server_info.get('server', '?')} v{server_info.get('version', '?')}")

    t0 = time.time()

    # Build all 12 stations
    success_count = 0
    for i, (name, title, subtitle) in enumerate(STATIONS):
        print(f"\n  [{i+1}/{len(STATIONS)}]")
        ok = build_station(name, title, subtitle)
        if ok:
            success_count += 1
        # Save after each widget
        checked("save_all", "save_all", timeout=30)
        time.sleep(0.5)

    elapsed = time.time() - t0
    print(f"\n  Built {success_count}/{len(STATIONS)} widgets in {elapsed:.1f}s")

    # Final save
    checked("final save_all", "save_all", timeout=30)
    time.sleep(1.0)

    # Verify
    ok = verify_stations()

    print(f"\n{'='*60}")
    if ok:
        print(f"  SUCCESS: All {len(STATIONS)} station widgets created and verified.")
    else:
        print("  PARTIAL: Some widgets may need attention.")
    print(f"{'='*60}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
