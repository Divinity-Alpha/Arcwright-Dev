"""
Build HUD overlay elements for all 12 BoreAndStroke station widget blueprints.

Adds three HUD groups to each WBP_Station_* widget:
  1. Border_HudChips  - top-left info chips (Day/Time/Equipment)
  2. Border_StationLabel - bottom-left station label
  3. Border_Toast - bottom-center notification toast

Uses raw TCP commands to the Arcwright Command Server on port 13377.

Usage:
    python scripts/build_station_hud.py
"""

import socket
import json
import sys
import time


# ---------------------------------------------------------------------------
# TCP helper
# ---------------------------------------------------------------------------

def send_command(cmd, params=None, timeout=10):
    """Send one TCP command, return parsed JSON response."""
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(('127.0.0.1', 13377))
    payload = json.dumps({'command': cmd, 'params': params or {}}) + '\n'
    s.sendall(payload.encode())
    buf = b''
    while b'\n' not in buf:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    s.close()
    line = buf.split(b'\n', 1)[0]
    result = json.loads(line.decode())
    if result.get('status') == 'error':
        raise RuntimeError(f"Command {cmd} failed: {result.get('message', result)}")
    return result


def add_child(wbp, wtype, wname, parent="RootCanvas"):
    """Add a widget child, return result."""
    return send_command('add_widget_child', {
        'widget_blueprint': wbp,
        'widget_type': wtype,
        'widget_name': wname,
        'parent_widget': parent,
    })


def set_prop(wbp, wname, prop, value):
    """Set a widget property, return result."""
    return send_command('set_widget_property', {
        'widget_blueprint': wbp,
        'widget_name': wname,
        'property': prop,
        'value': value,
    })


# ---------------------------------------------------------------------------
# Alpha to hex helper
# ---------------------------------------------------------------------------

def alpha_hex(base_hex, alpha_float):
    """Convert alpha 0.0-1.0 to 2-char hex and append to base color.
    base_hex should be like '#0A0C0F' (no alpha).
    Returns 'hex:#0A0C0FE0' format.
    """
    alpha_byte = int(round(alpha_float * 255))
    alpha_byte = max(0, min(255, alpha_byte))
    return f"hex:{base_hex}{alpha_byte:02X}"


# ---------------------------------------------------------------------------
# Station definitions
# ---------------------------------------------------------------------------

STATIONS = [
    {
        'name': 'WBP_Station_Office',
        'chip_labels': ['Day', 'Budget', 'Reputation'],
        'chip_values': ['1', '$5,000', '50'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'OFFICE',
        'label_info': 'Budget & Scheduling',
    },
    {
        'name': 'WBP_Station_Disassembly',
        'chip_labels': ['Day', 'Time', 'Parts Recovered'],
        'chip_values': ['1', '0:00', '0'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'DISASSEMBLY',
        'label_info': 'Engine Stand & Tools',
    },
    {
        'name': 'WBP_Station_Cleaning',
        'chip_labels': ['Day', 'Time', 'Cleanliness'],
        'chip_values': ['1', '0:00', '0%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'CLEANING',
        'label_info': 'Ultrasonic Tank',
    },
    {
        'name': 'WBP_Station_Inspection',
        'chip_labels': ['Day', 'Time', 'Issues Found'],
        'chip_values': ['1', '0:00', '0'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'INSPECTION',
        'label_info': 'Dial Bore Gauge',
    },
    {
        'name': 'WBP_Station_Hone',
        'chip_labels': ['Day', 'Time', 'Honing Bar'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'HONE',
        'label_info': 'Sunnen CK-10',
    },
    {
        'name': 'WBP_Station_Deck',
        'chip_labels': ['Day', 'Time', 'Grinder'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'DECK',
        'label_info': 'Peterson RA-800',
    },
    {
        'name': 'WBP_Station_CrankGrind',
        'chip_labels': ['Day', 'Time', 'Grinder'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'CRANK GRIND',
        'label_info': 'Storm Vulcan 15C',
    },
    {
        'name': 'WBP_Station_HeadWork',
        'chip_labels': ['Day', 'Time', 'Valve Grinder'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'HEAD WORK',
        'label_info': 'Serdi 100',
    },
    {
        'name': 'WBP_Station_ValveWork',
        'chip_labels': ['Day', 'Time', 'Lapping Compound'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'VALVE WORK',
        'label_info': 'Kwik-Way SVS II',
    },
    {
        'name': 'WBP_Station_Assembly',
        'chip_labels': ['Day', 'Time', 'Torque Wrench'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'ASSEMBLY',
        'label_info': 'Proto Digital Torque',
    },
    {
        'name': 'WBP_Station_Balancing',
        'chip_labels': ['Day', 'Time', 'Balancer'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'BALANCING',
        'label_info': 'CWT CB-1100',
    },
    {
        'name': 'WBP_Station_Testing',
        'chip_labels': ['Day', 'Time', 'Dyno'],
        'chip_values': ['1', '0:00', '100%'],
        'chip_value_colors': ['hex:#E8A624', 'hex:#EEF0F4', 'hex:#3DDC84'],
        'label_name': 'TESTING',
        'label_info': 'SuperFlow SF-902',
    },
]

# Background color base (no alpha): #0A0C0F
BG_BASE = '#0A0C0F'


# ---------------------------------------------------------------------------
# HUD builder
# ---------------------------------------------------------------------------

def build_hud_for_station(station):
    """Add the 3 HUD overlay groups to one station widget blueprint."""
    wbp = station['name']
    print(f"\n{'='*60}")
    print(f"  Building HUD for {wbp}")
    print(f"{'='*60}")

    # ------------------------------------------------------------------
    # 1. Border_HudChips -- top-left info chips
    # ------------------------------------------------------------------
    print("  [1/3] Adding Border_HudChips (top-left info chips)...")

    # Add the border background with alpha baked into hex color
    add_child(wbp, 'Border', 'Border_HudChips', 'RootCanvas')
    set_prop(wbp, 'Border_HudChips', 'position', {'x': 16, 'y': 16})
    set_prop(wbp, 'Border_HudChips', 'size', {'x': 220, 'y': 110})
    set_prop(wbp, 'Border_HudChips', 'BrushColor', alpha_hex(BG_BASE, 0.88))

    # Add 3 rows of label+value text pairs directly on RootCanvas
    # positioned to overlay the border background
    chip_labels = station['chip_labels']
    chip_values = station['chip_values']
    chip_colors = station['chip_value_colors']

    for i in range(3):
        row_y = 16 + 8 + (i * 30)  # 24, 54, 84 inside the border area
        lbl_name = f"txt_Chip{i}L"
        val_name = f"txt_Chip{i}V"

        # Label text (left side)
        add_child(wbp, 'TextBlock', lbl_name, 'RootCanvas')
        set_prop(wbp, lbl_name, 'Text', chip_labels[i])
        set_prop(wbp, lbl_name, 'Font.Size', '12')
        set_prop(wbp, lbl_name, 'ColorAndOpacity', 'hex:#707888')
        set_prop(wbp, lbl_name, 'position', {'x': 28, 'y': row_y})
        set_prop(wbp, lbl_name, 'size', {'x': 90, 'y': 24})

        # Value text (right side)
        add_child(wbp, 'TextBlock', val_name, 'RootCanvas')
        set_prop(wbp, val_name, 'Text', chip_values[i])
        set_prop(wbp, val_name, 'Font.Size', '14')
        set_prop(wbp, val_name, 'ColorAndOpacity', chip_colors[i])
        set_prop(wbp, val_name, 'position', {'x': 124, 'y': row_y})
        set_prop(wbp, val_name, 'size', {'x': 100, 'y': 24})

    print("    Added Border_HudChips + 6 text elements")

    # ------------------------------------------------------------------
    # 2. Border_StationLabel -- bottom-left station label
    # ------------------------------------------------------------------
    print("  [2/3] Adding Border_StationLabel (bottom-left)...")

    add_child(wbp, 'Border', 'Border_StationLabel', 'RootCanvas')
    set_prop(wbp, 'Border_StationLabel', 'position', {'x': 16, 'y': 954})
    set_prop(wbp, 'Border_StationLabel', 'size', {'x': 320, 'y': 70})
    set_prop(wbp, 'Border_StationLabel', 'BrushColor', alpha_hex(BG_BASE, 0.92))

    # Station name text
    add_child(wbp, 'TextBlock', 'Text_SL_Name', 'RootCanvas')
    set_prop(wbp, 'Text_SL_Name', 'Text', station['label_name'])
    set_prop(wbp, 'Text_SL_Name', 'Font.Size', '14')
    set_prop(wbp, 'Text_SL_Name', 'Font.Typeface', 'Bold')
    set_prop(wbp, 'Text_SL_Name', 'ColorAndOpacity', 'hex:#E8A624')
    set_prop(wbp, 'Text_SL_Name', 'position', {'x': 28, 'y': 962})
    set_prop(wbp, 'Text_SL_Name', 'size', {'x': 296, 'y': 28})

    # Equipment info text
    add_child(wbp, 'TextBlock', 'Text_SL_Info', 'RootCanvas')
    set_prop(wbp, 'Text_SL_Info', 'Text', station['label_info'])
    set_prop(wbp, 'Text_SL_Info', 'Font.Size', '11')
    set_prop(wbp, 'Text_SL_Info', 'ColorAndOpacity', 'hex:#707888')
    set_prop(wbp, 'Text_SL_Info', 'position', {'x': 28, 'y': 990})
    set_prop(wbp, 'Text_SL_Info', 'size', {'x': 296, 'y': 24})

    print("    Added Border_StationLabel + 2 text elements")

    # ------------------------------------------------------------------
    # 3. Border_Toast -- bottom-center notification
    # ------------------------------------------------------------------
    print("  [3/3] Adding Border_Toast (bottom-center)...")

    add_child(wbp, 'Border', 'Border_Toast', 'RootCanvas')
    set_prop(wbp, 'Border_Toast', 'position', {'x': 425, 'y': 1020})
    set_prop(wbp, 'Border_Toast', 'size', {'x': 400, 'y': 44})
    set_prop(wbp, 'Border_Toast', 'BrushColor', alpha_hex(BG_BASE, 0.96))

    # Toast text
    add_child(wbp, 'TextBlock', 'Text_Toast', 'RootCanvas')
    set_prop(wbp, 'Text_Toast', 'Text', 'Ready')
    set_prop(wbp, 'Text_Toast', 'Font.Size', '13')
    set_prop(wbp, 'Text_Toast', 'ColorAndOpacity', 'hex:#EEF0F4')
    set_prop(wbp, 'Text_Toast', 'position', {'x': 441, 'y': 1028})
    set_prop(wbp, 'Text_Toast', 'size', {'x': 368, 'y': 28})

    print(f"    Added Border_Toast + 1 text element")
    print(f"  DONE: {wbp} -- 12 new widgets added")


def verify_station(station):
    """Verify HUD elements exist in the widget tree."""
    wbp = station['name']
    result = send_command('get_widget_tree', {'widget_blueprint': wbp})
    data = result['data']
    total = data['total_widgets']

    # Collect all widget names from the tree
    names = set()

    def walk(nodes):
        for node in nodes:
            names.add(node['name'])
            if 'children' in node:
                walk(node['children'])

    walk(data['tree'])

    # Check for our HUD elements
    expected = [
        'Border_HudChips', 'txt_Chip0L', 'txt_Chip0V',
        'txt_Chip1L', 'txt_Chip1V', 'txt_Chip2L', 'txt_Chip2V',
        'Border_StationLabel', 'Text_SL_Name', 'Text_SL_Info',
        'Border_Toast', 'Text_Toast',
    ]

    missing = [n for n in expected if n not in names]
    if missing:
        print(f"  FAIL  {wbp}: missing {missing} (total={total})")
        return False
    else:
        print(f"  OK    {wbp}: all 12 HUD elements present (total={total})")
        return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  BoreAndStroke Station HUD Builder")
    print("  Adding HUD overlays to 12 station widgets")
    print("=" * 60)

    # Verify connectivity
    try:
        r = send_command('health_check')
        print(f"  Connected to Arcwright Command Server v{r['data'].get('version', '?')}")
    except Exception as e:
        print(f"  ERROR: Cannot connect to Command Server: {e}")
        sys.exit(1)

    # Build HUD for each station
    success = 0
    errors = []
    for station in STATIONS:
        try:
            build_hud_for_station(station)
            success += 1
        except Exception as e:
            print(f"  ERROR building {station['name']}: {e}")
            errors.append((station['name'], str(e)))

    # Save all
    print(f"\n{'='*60}")
    print("  Saving all assets...")
    try:
        send_command('save_all', timeout=30)
        print("  Save complete.")
    except Exception as e:
        print(f"  Save warning: {e}")

    # Verify all stations
    print(f"\n{'='*60}")
    print("  Verification -- checking widget trees")
    print(f"{'='*60}")
    verified = 0
    for station in STATIONS:
        try:
            if verify_station(station):
                verified += 1
        except Exception as e:
            print(f"  FAIL  {station['name']}: verification error: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"  Built:    {success}/12 stations")
    print(f"  Verified: {verified}/12 stations")
    if errors:
        print(f"  Errors:")
        for name, err in errors:
            print(f"    {name}: {err}")
    print(f"{'='*60}")

    sys.exit(0 if verified == 12 else 1)


if __name__ == '__main__':
    main()
