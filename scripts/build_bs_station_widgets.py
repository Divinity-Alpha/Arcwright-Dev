"""Build styled station widgets in BoreAndStroke project via Arcwright TCP."""
import socket
import json
import time


def send(cmd, params=None):
    if params is None:
        params = {}
    s = socket.socket()
    s.settimeout(30)
    s.connect(("localhost", 13377))
    s.send((json.dumps({"command": cmd, "params": params}) + "\n").encode())
    resp = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        resp += chunk
        if b"\n" in resp:
            break
    s.close()
    return json.loads(resp.decode().strip())


def add_text(wb, name, parent, text, size, color, auto_wrap=False):
    params = {
        "widget_blueprint": wb,
        "widget_type": "TextBlock",
        "widget_name": name,
    }
    if parent:
        params["parent_widget"] = parent
    send("add_widget_child", params)
    send("set_widget_property", {
        "widget_blueprint": wb,
        "widget_name": name,
        "property": "Text",
        "value": text,
    })
    send("set_widget_property", {
        "widget_blueprint": wb,
        "widget_name": name,
        "property": "Font.Size",
        "value": str(size),
    })
    send("set_widget_property", {
        "widget_blueprint": wb,
        "widget_name": name,
        "property": "ColorAndOpacity",
        "value": color,
    })
    if auto_wrap:
        send("set_widget_property", {
            "widget_blueprint": wb,
            "widget_name": name,
            "property": "AutoWrapText",
            "value": "true",
        })


def add_border(wb, name, parent, bg_color, padding=None):
    params = {
        "widget_blueprint": wb,
        "widget_type": "Border",
        "widget_name": name,
    }
    if parent:
        params["parent_widget"] = parent
    send("add_widget_child", params)
    send("set_widget_property", {
        "widget_blueprint": wb,
        "widget_name": name,
        "property": "BrushColor",
        "value": bg_color,
    })
    if padding:
        send("set_widget_property", {
            "widget_blueprint": wb,
            "widget_name": name,
            "property": "Padding",
            "value": padding,
        })


def add_vbox(wb, name, parent):
    params = {
        "widget_blueprint": wb,
        "widget_type": "VerticalBox",
        "widget_name": name,
    }
    if parent:
        params["parent_widget"] = parent
    send("add_widget_child", params)


# Colors
AMBER = "(R=0.83,G=0.66,B=0.26,A=1.0)"
TEXT_BRIGHT = "(R=0.8,G=0.87,B=0.93,A=1.0)"
TEXT_MID = "(R=0.67,G=0.73,B=0.8,A=1.0)"
TEXT_DIM = "(R=0.4,G=0.47,B=0.53,A=1.0)"
TEXT_FAINT = "(R=0.33,G=0.4,B=0.47,A=1.0)"
GREEN = "(R=0.3,G=0.85,B=0.4,A=1.0)"
BG_PANEL = "(R=0.04,G=0.05,B=0.08,A=0.95)"
BG_HEADER = "(R=0.0,G=0.0,B=0.0,A=0.25)"
BG_STATUS = "(R=0.0,G=0.0,B=0.0,A=0.35)"


def build_station_widget(widget_name, title, subtitle):
    """Build a styled station widget with C++ txt_* TextBlocks."""

    # Delete existing
    send("delete_blueprint", {"name": widget_name})
    time.sleep(0.3)

    # Create at /Game/UI/
    r = send("create_widget_blueprint", {"name": widget_name, "path": "/Game/UI"})
    if r.get("status") != "ok":
        print(f"  CREATE FAILED: {r.get('message', '?')}")
        return False

    wb = widget_name

    # Panel background
    add_border(wb, "Border_Panel", None, BG_PANEL)

    # Main vertical layout
    add_vbox(wb, "VBox_Main", "Border_Panel")

    # === HEADER ===
    add_border(wb, "Border_Header", "VBox_Main", BG_HEADER,
               "(Left=24,Top=16,Right=24,Bottom=16)")
    add_vbox(wb, "VBox_Header", "Border_Header")

    # txt_Title — C++ RefreshStationUI populates this
    add_text(wb, "txt_Title", "VBox_Header", title, 26, AMBER)

    # txt_Desc — station subtitle
    add_text(wb, "txt_Desc", "VBox_Header", subtitle, 16, TEXT_DIM)

    # === CONTENT ===
    add_border(wb, "Border_Content", "VBox_Main", "(R=0,G=0,B=0,A=0)",
               "(Left=24,Top=16,Right=24,Bottom=16)")
    add_vbox(wb, "VBox_Content", "Border_Content")

    # txt_ItemInfo — part/engine info (C++ populates)
    add_text(wb, "txt_ItemInfo", "VBox_Content", "No engine loaded", 18, TEXT_BRIGHT, True)

    # txt_ActionsHeader
    add_text(wb, "txt_ActionsHeader", "VBox_Content", "AVAILABLE ACTIONS", 14, TEXT_DIM)

    # txt_Actions — operation list (C++ populates)
    add_text(wb, "txt_Actions", "VBox_Content",
             "Load an engine to see available operations", 16, TEXT_MID, True)

    # txt_Equipment — equipment/cash display (C++ populates)
    add_text(wb, "txt_Equipment", "VBox_Content", "Equipment: Basic Tools", 14, TEXT_DIM)

    # === STATUS BAR ===
    add_border(wb, "Border_StatusBar", "VBox_Main", BG_STATUS,
               "(Left=16,Top=10,Right=16,Bottom=10)")

    # txt_ExitHint — exit instructions + time (C++ populates)
    add_text(wb, "txt_ExitHint", "Border_StatusBar",
             "Press Q to exit station", 14, TEXT_FAINT)

    # Widget commands auto-compile. Verify by checking widget tree.
    r = send("get_widget_tree", {"widget_blueprint": wb})
    total = r.get("data", {}).get("total_widgets", 0)
    return total >= 7  # expect at least 7 txt_* TextBlocks


# ===== STATION DEFINITIONS (actual enum-matching names) =====
STATIONS = [
    ("WBP_Station_Bore",        "BORE STATION",    "Station 05 · Bore to Oversize"),
    ("WBP_Station_Hone",        "HONE STATION",    "Station 06 · Hone for Cross-Hatch"),
    ("WBP_Station_Deck",        "DECK STATION",    "Station 09 · Surface Grinding"),
    ("WBP_Station_CrankGrind",  "CRANK GRINDER",   "Station 07 · Journals & Grind"),
    ("WBP_Station_HeadWork",    "CYLINDER HEADS",  "Station 08 · Valve Seats & Guides"),
    ("WBP_Station_ValveWork",   "VALVE WORK",      "Station 08b · Valves & Seats"),
    ("WBP_Station_Balancing",   "BALANCING",       "Station 10 · Assembly Balance"),
    ("WBP_Station_Cleaning",    "CLEANING",        "Station 04 · Deep Clean Parts"),
    ("WBP_Station_Disassembly", "DISASSEMBLY",     "Station 02 · Break Down Engine"),
    ("WBP_Station_Assembly",    "ASSEMBLY",        "Station 11 · Torque Specs"),
    ("WBP_Station_Testing",     "TESTING",         "Station 12 · Engine Performance"),
    ("WBP_Station_Office",      "FRONT OFFICE",    "Orders, Finance & Reputation"),
    ("WBP_Station_Inspection",  "INSPECTION",      "Station 03 · Measure & Assess"),
]

if __name__ == "__main__":
    print(f"Building {len(STATIONS)} station widgets...\n")

    results = {}
    for widget_name, title, sub in STATIONS:
        print(f"{widget_name}: ", end="", flush=True)
        ok = build_station_widget(widget_name, title, sub)
        results[widget_name] = ok
        print("OK" if ok else "FAIL")

    succeeded = sum(results.values())
    print(f"\n=== Results: {succeeded}/{len(results)} succeeded ===")

    if succeeded == len(results):
        r = send("save_all", {})
        print(f"save_all: {r.get('status')}")
