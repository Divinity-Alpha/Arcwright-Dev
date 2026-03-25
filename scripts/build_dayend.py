"""
Build WBP_DayEnd widget blueprint in the running UE5 editor via TCP.
BoreAndStroke End-of-Day summary screen.
"""

import socket
import json
import time
import sys

# ── TCP helper ────────────────────────────────────────────────
def send_command(cmd, params=None, timeout=30):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(('127.0.0.1', 13377))
    s.sendall((json.dumps({'command': cmd, 'params': params or {}}) + '\n').encode())
    data = b''
    while True:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
            # Newline-delimited JSON: response ends with \n
            if b'\n' in data:
                break
            # Also try to parse — if valid JSON, we're done
            try:
                json.loads(data.decode())
                break
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        except socket.timeout:
            break
        except Exception:
            break
    s.close()
    return json.loads(data.decode().strip())


def check(result, label):
    """Check a TCP result and abort on error."""
    if result.get('status') != 'ok':
        print(f"  FAILED: {label}")
        print(f"  Error: {result.get('error', result)}")
        sys.exit(1)
    print(f"  OK: {label}")
    return result


WBP = "WBP_DayEnd"

# ── 1. Create the widget blueprint ───────────────────────────
print("=== Building WBP_DayEnd ===\n")

print("[1] Create widget blueprint")
check(send_command("create_widget_blueprint", {
    "name": WBP,
    "design_width": 1920,
    "design_height": 1080
}), "create_widget_blueprint")

# ── 2. Add RootCanvas as the root CanvasPanel ────────────────
print("\n[2] Add RootCanvas")
check(send_command("add_widget_child", {
    "widget_blueprint": WBP,
    "widget_type": "CanvasPanel",
    "widget_name": "RootCanvas"
}), "RootCanvas")


# ── Helper: add a child widget to RootCanvas ─────────────────
def add_child(widget_type, widget_name):
    return check(send_command("add_widget_child", {
        "widget_blueprint": WBP,
        "widget_type": widget_type,
        "widget_name": widget_name,
        "parent_widget": "RootCanvas"
    }), f"add {widget_name}")


def set_prop(widget_name, prop, value):
    return check(send_command("set_widget_property", {
        "widget_blueprint": WBP,
        "widget_name": widget_name,
        "property": prop,
        "value": value
    }), f"set {widget_name}.{prop}")


def set_pos(widget_name, x, y):
    set_prop(widget_name, "position", {"x": x, "y": y})


def set_size(widget_name, w, h):
    set_prop(widget_name, "size", {"x": w, "y": h})


def setup_border(name, x, y, w, h, color):
    """Add a Border to RootCanvas, position and size it, set BrushColor."""
    add_child("Border", name)
    set_pos(name, x, y)
    set_size(name, w, h)
    set_prop(name, "BrushColor", color)


def setup_text(name, x, y, text, font_size, color):
    """Add a TextBlock to RootCanvas, position it, set text/font/color."""
    add_child("TextBlock", name)
    set_pos(name, x, y)
    set_prop(name, "Text", text)
    set_prop(name, "Font.Size", str(font_size))
    set_prop(name, "ColorAndOpacity", color)


# ── 3. Build all UI elements ─────────────────────────────────

# --- Border_BG: full screen background ---
print("\n[3] Border_BG (full screen background)")
setup_border("Border_BG", 0, 0, 1920, 1080, "hex:#0A0C0F")

# --- Border_Header: top section ---
print("\n[4] Border_Header")
setup_border("Border_Header", 0, 0, 1920, 120, "(R=0.0,G=0.0,B=0.0,A=0.35)")

print("\n[5] Text_Title")
setup_text("Text_Title", 40, 20, "END OF DAY", 36, "hex:#E8A624")

print("\n[6] Text_DayNum")
setup_text("Text_DayNum", 40, 70, "Day 1", 18, "hex:#707888")

# --- Border_Revenue: revenue section ---
print("\n[7] Border_Revenue")
setup_border("Border_Revenue", 200, 160, 720, 300, "hex:#12161C")

print("\n[8] Text_RevTitle")
setup_text("Text_RevTitle", 220, 170, "REVENUE", 16, "hex:#707888")

print("\n[9] Text_JobCount")
setup_text("Text_JobCount", 220, 210, "Jobs Completed: 0", 14, "hex:#D0D4DC")

print("\n[10] Text_GrossRev")
setup_text("Text_GrossRev", 220, 260, "$0.00", 28, "hex:#3DDC84")

# --- Border_Expenses: expenses section ---
print("\n[11] Border_Expenses")
setup_border("Border_Expenses", 1000, 160, 720, 300, "hex:#12161C")

print("\n[12] Text_ExpTitle")
setup_text("Text_ExpTitle", 1020, 170, "EXPENSES", 16, "hex:#707888")

print("\n[13] Text_Parts")
setup_text("Text_Parts", 1020, 210, "Parts: $0", 14, "hex:#D0D4DC")

print("\n[14] Text_Consumables")
setup_text("Text_Consumables", 1020, 240, "Consumables: $0", 14, "hex:#D0D4DC")

print("\n[15] Text_Overhead")
setup_text("Text_Overhead", 1020, 270, "Overhead: $0", 14, "hex:#D0D4DC")

# --- Border_NetProfit: net profit section ---
print("\n[16] Border_NetProfit")
setup_border("Border_NetProfit", 200, 500, 1520, 180, "hex:#181D26")

print("\n[17] Text_NetLabel")
setup_text("Text_NetLabel", 220, 510, "NET PROFIT", 16, "hex:#707888")

print("\n[18] Text_NetAmount")
setup_text("Text_NetAmount", 220, 550, "+$0.00", 48, "hex:#3DDC84")

# --- Border_Quality: quality section ---
print("\n[19] Border_Quality")
setup_border("Border_Quality", 200, 720, 1520, 120, "hex:#12161C")

print("\n[20] Text_QualLabel")
setup_text("Text_QualLabel", 220, 730, "QUALITY SUMMARY", 16, "hex:#707888")

print("\n[21] Text_AvgQuality")
setup_text("Text_AvgQuality", 220, 770, "Average Quality: --", 18, "hex:#F0C040")

# --- Border_BtnContinue: continue button ---
print("\n[22] Border_BtnContinue")
setup_border("Border_BtnContinue", 760, 900, 400, 60, "(R=0.008,G=0.052,B=0.022,A=0.9)")

print("\n[23] Text_Continue")
setup_text("Text_Continue", 860, 915, "CONTINUE", 22, "hex:#3DDC84")

# ── 4. Verify with get_widget_tree ────────────────────────────
print("\n[24] Verifying widget tree...")
tree_result = send_command("get_widget_tree", {"widget_blueprint": WBP})
if tree_result.get('status') == 'ok':
    tree_data = tree_result.get('data', {})
    print(f"  Widget tree for {WBP}:")
    print(json.dumps(tree_data, indent=2))
else:
    print(f"  WARNING: Could not get widget tree: {tree_result.get('error', tree_result)}")

# ── 5. Protect widget layout ─────────────────────────────────
print("\n[25] Protecting widget layout...")
protect_result = send_command("protect_widget_layout", {"name": WBP})
if protect_result.get('status') == 'ok':
    print("  OK: protect_widget_layout")
else:
    print(f"  WARNING: protect_widget_layout: {protect_result.get('error', protect_result)}")

# ── 6. Save all ──────────────────────────────────────────────
print("\n[26] Saving all...")
save_result = send_command("save_all", {})
if save_result.get('status') == 'ok':
    print("  OK: save_all")
else:
    print(f"  WARNING: save_all: {save_result.get('error', save_result)}")

print("\n=== WBP_DayEnd build complete ===")
