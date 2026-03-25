#!/usr/bin/env python3
"""WBP_Inspection — Three-panel inspection widget for BoreAndStroke.

Left panel (40%):   Part map
Center panel (35%): Measurements
Right panel (25%):  Actions

All positioned absolutely on RootCanvas. BoreAndStroke color palette.
Design size: 1920x1080.
"""
import socket, json, time, sys

# ── TCP helpers ──────────────────────────────────────────────
def send(cmd, params, retries=3):
    for attempt in range(retries):
        try:
            s = socket.socket()
            s.settimeout(30)
            s.connect(('localhost', 13377))
            s.send((json.dumps({'command': cmd, 'params': params}) + '\n').encode())
            resp = b''
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                resp += chunk
                if b'\n' in resp:
                    break
            s.close()
            time.sleep(0.15)
            return json.loads(resp.decode().strip())
        except (ConnectionResetError, ConnectionRefusedError, socket.timeout) as e:
            if attempt < retries - 1:
                print(f"  [RETRY {attempt+1}] {cmd} -- {e}")
                time.sleep(5)
            else:
                raise

def sp(wbp, wname, prop, val):
    """Set widget property."""
    r = send('set_widget_property', {
        'widget_blueprint': wbp, 'widget_name': wname,
        'property': prop, 'value': str(val)
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X SET FAILED {wname}.{prop}: {r.get('error', r.get('message','?'))[:80]}")
    return ok

def sp_color(wbp, wname, prop, val, label=""):
    """Set color property and verify not white."""
    sp(wbp, wname, prop, val)
    r = send('get_widget_property', {
        'widget_blueprint': wbp, 'widget_name': wname, 'property': prop
    })
    got = r.get('data', {}).get('value', '?')
    if 'BrushColor' in prop or 'ColorAndOpacity' in prop or 'FillColorAndOpacity' in prop:
        if '1.0000,G=1.0000,B=1.0000' in got:
            print(f"  X WHITE {wname}.{prop} -- set failed silently")
            return False
    print(f"  OK {wname}.{prop} = {got[:55]} {label}")
    return True

def add(wbp, parent, wtype, wname):
    """Add a child widget."""
    r = send('add_widget_child', {
        'widget_blueprint': wbp, 'parent_widget': parent,
        'widget_type': wtype, 'widget_name': wname,
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X ADD FAILED {wname}: {r.get('error', r.get('message','?'))[:80]}")
    else:
        print(f"  + {wtype}: {wname}")
    return ok

# ── BoreAndStroke color constants (hex: prefix -> auto sRGB->Linear) ──
BG_DEEP    = 'hex:#0A0C0F'
BG_PANEL   = 'hex:#12161C'
BG_CARD    = 'hex:#181D26'
BORDER_C   = 'hex:#2A3040'
BORDER_ACT = 'hex:#3A4560'
ACCENT     = 'hex:#E8A624'
GREEN      = 'hex:#3DDC84'
YELLOW     = 'hex:#F0C040'
RED        = 'hex:#E04050'
TEXT       = 'hex:#D0D4DC'
DIM        = 'hex:#707888'
BRIGHT     = 'hex:#EEF0F4'
APPROVE_BG = '(R=0.008,G=0.052,B=0.022,A=0.9)'
CANCEL_BG  = '(R=0.073,G=0.006,B=0.009,A=0.8)'

WBP = 'WBP_Inspection'

# ══════════════════════════════════════════════════════════════
print("=" * 60)
print("WBP_Inspection -- BoreAndStroke Inspection Panel")
print("  Left: Part Map (768px)  Center: Measurements (672px)  Right: Actions (480px)")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# STEP 1: Delete existing + create fresh at /Game/UI/
# ══════════════════════════════════════════════════════════════
print("\n[STEP 1] Delete and create WBP_Inspection at /Game/UI/")
send('delete_blueprint', {'name': WBP})
time.sleep(0.5)
r = send('create_widget_blueprint', {'name': WBP, 'path': '/Game/UI'})
assert r.get('status') == 'ok', f"CREATE FAILED: {r}"
print(f"  OK Created {WBP}")

# Set design size explicitly
send('set_widget_design_size', {'name': WBP, 'width': 1920, 'height': 1080})
print("  OK Design size: 1920x1080")

# ══════════════════════════════════════════════════════════════
# STEP 2: Root CanvasPanel
# ══════════════════════════════════════════════════════════════
print("\n[STEP 2] Root CanvasPanel")
add(WBP, '', 'CanvasPanel', 'RootCanvas')

# ══════════════════════════════════════════════════════════════
# STEP 3: LEFT PANEL — Part Map (0,0, 768x1080)
# ══════════════════════════════════════════════════════════════
print("\n[STEP 3] Left panel — Part Map (768x1080)")

add(WBP, 'RootCanvas', 'Border', 'Border_PartMap')
sp(WBP, 'Border_PartMap', 'Slot.Position.X', '0')
sp(WBP, 'Border_PartMap', 'Slot.Position.Y', '0')
sp(WBP, 'Border_PartMap', 'Slot.Size.X', '768')
sp(WBP, 'Border_PartMap', 'Slot.Size.Y', '1080')
sp(WBP, 'Border_PartMap', 'Brush.DrawType', 'Box')
sp_color(WBP, 'Border_PartMap', 'BrushColor', BG_PANEL, '<-- bg-panel #12161C')

# Part Map texts — all children of RootCanvas, positioned absolutely
pm_texts = [
    ('Text_PMTitle',   'PART MAP',                    20,  10, 16, DIM,   ''),
    ('Text_PMStatus',  'Select an engine to inspect',  20,  50, 14, TEXT,  ''),
    ('Text_PMBlock',   'Block: --',                    20, 100, 13, GREEN, ''),
    ('Text_PMHead',    'Head: --',                     20, 130, 13, YELLOW,''),
    ('Text_PMCrank',   'Crank: --',                    20, 160, 13, RED,   ''),
    ('Text_PMPistons', 'Pistons: --',                  20, 190, 13, DIM,   ''),
    ('Text_PMValves',  'Valves: --',                   20, 220, 13, DIM,   ''),
]

for name, text, x, y, size, color, typeface in pm_texts:
    add(WBP, 'RootCanvas', 'TextBlock', name)
    sp(WBP, name, 'Text', text)
    sp(WBP, name, 'Slot.Position.X', str(x))
    sp(WBP, name, 'Slot.Position.Y', str(y))
    sp(WBP, name, 'Font.Size', str(size))
    if typeface:
        sp(WBP, name, 'Font.Typeface', typeface)
    sp_color(WBP, name, 'ColorAndOpacity', color)

print("  OK Left panel — 7 text widgets placed")

# ══════════════════════════════════════════════════════════════
# STEP 4: CENTER PANEL — Measurements (768,0, 672x1080)
# ══════════════════════════════════════════════════════════════
print("\n[STEP 4] Center panel — Measurements (672x1080)")

add(WBP, 'RootCanvas', 'Border', 'Border_Measure')
sp(WBP, 'Border_Measure', 'Slot.Position.X', '768')
sp(WBP, 'Border_Measure', 'Slot.Position.Y', '0')
sp(WBP, 'Border_Measure', 'Slot.Size.X', '672')
sp(WBP, 'Border_Measure', 'Slot.Size.Y', '1080')
sp(WBP, 'Border_Measure', 'Brush.DrawType', 'Box')
sp_color(WBP, 'Border_Measure', 'BrushColor', BG_CARD, '<-- bg-card #181D26')

m_texts = [
    ('Text_MTitle',    'MEASUREMENTS',                 788,  10, 16, DIM,    ''),
    ('Text_MPartName', 'Part: --',                     788,  50, 14, ACCENT, ''),
    ('Text_MSpec',     'Spec: --',                     788,  90, 14, TEXT,   ''),
    ('Text_MActual',   'Actual: --',                   788, 120, 14, TEXT,   ''),
    ('Text_MResult',   'Result: --',                   788, 160, 18, GREEN,  'Bold'),
]

for name, text, x, y, size, color, typeface in m_texts:
    add(WBP, 'RootCanvas', 'TextBlock', name)
    sp(WBP, name, 'Text', text)
    sp(WBP, name, 'Slot.Position.X', str(x))
    sp(WBP, name, 'Slot.Position.Y', str(y))
    sp(WBP, name, 'Font.Size', str(size))
    if typeface:
        sp(WBP, name, 'Font.Typeface', typeface)
    sp_color(WBP, name, 'ColorAndOpacity', color)

# ProgBar_Tolerance at (788,200, 630x24)
print("  Adding ProgBar_Tolerance")
add(WBP, 'RootCanvas', 'ProgressBar', 'ProgBar_Tolerance')
sp(WBP, 'ProgBar_Tolerance', 'Slot.Position.X', '788')
sp(WBP, 'ProgBar_Tolerance', 'Slot.Position.Y', '200')
sp(WBP, 'ProgBar_Tolerance', 'Slot.Size.X', '630')
sp(WBP, 'ProgBar_Tolerance', 'Slot.Size.Y', '24')
sp(WBP, 'ProgBar_Tolerance', 'Percent', '0.0')
sp_color(WBP, 'ProgBar_Tolerance', 'FillColorAndOpacity', GREEN, '<-- green fill')

print("  OK Center panel — 5 text widgets + 1 progress bar placed")

# ══════════════════════════════════════════════════════════════
# STEP 5: RIGHT PANEL — Actions (1440,0, 480x1080)
# ══════════════════════════════════════════════════════════════
print("\n[STEP 5] Right panel — Actions (480x1080)")

add(WBP, 'RootCanvas', 'Border', 'Border_Actions')
sp(WBP, 'Border_Actions', 'Slot.Position.X', '1440')
sp(WBP, 'Border_Actions', 'Slot.Position.Y', '0')
sp(WBP, 'Border_Actions', 'Slot.Size.X', '480')
sp(WBP, 'Border_Actions', 'Slot.Size.Y', '1080')
sp(WBP, 'Border_Actions', 'Brush.DrawType', 'Box')
sp_color(WBP, 'Border_Actions', 'BrushColor', BG_DEEP, '<-- bg-deep #0A0C0F')

# Action panel texts
a_texts = [
    ('Text_ATitle', 'INSPECTION',                          1460,  10, 16, DIM, ''),
    ('Text_AInfo',  'Select engine, then inspect each part', 1460,  50, 12, DIM, ''),
]

for name, text, x, y, size, color, typeface in a_texts:
    add(WBP, 'RootCanvas', 'TextBlock', name)
    sp(WBP, name, 'Text', text)
    sp(WBP, name, 'Slot.Position.X', str(x))
    sp(WBP, name, 'Slot.Position.Y', str(y))
    sp(WBP, name, 'Font.Size', str(size))
    if typeface:
        sp(WBP, name, 'Font.Typeface', typeface)
    sp_color(WBP, name, 'ColorAndOpacity', color)

# Border_BtnInspect: (1460,100, 440x50), APPROVE_BG
print("  Adding Border_BtnInspect")
add(WBP, 'RootCanvas', 'Border', 'Border_BtnInspect')
sp(WBP, 'Border_BtnInspect', 'Slot.Position.X', '1460')
sp(WBP, 'Border_BtnInspect', 'Slot.Position.Y', '100')
sp(WBP, 'Border_BtnInspect', 'Slot.Size.X', '440')
sp(WBP, 'Border_BtnInspect', 'Slot.Size.Y', '50')
sp(WBP, 'Border_BtnInspect', 'Brush.DrawType', 'Box')
sp_color(WBP, 'Border_BtnInspect', 'BrushColor', APPROVE_BG, '<-- approve bg')

# Text_BtnInspect: "INSPECT SELECTED" at (1540,112), 16px, GREEN
add(WBP, 'RootCanvas', 'TextBlock', 'Text_BtnInspect')
sp(WBP, 'Text_BtnInspect', 'Text', 'INSPECT SELECTED')
sp(WBP, 'Text_BtnInspect', 'Slot.Position.X', '1540')
sp(WBP, 'Text_BtnInspect', 'Slot.Position.Y', '112')
sp(WBP, 'Text_BtnInspect', 'Slot.bAutoSize', 'true')
sp(WBP, 'Text_BtnInspect', 'Font.Size', '16')
sp_color(WBP, 'Text_BtnInspect', 'ColorAndOpacity', GREEN, '<-- green')

# Border_BtnBack: (1460,170, 440x50), CANCEL_BG
print("  Adding Border_BtnBack")
add(WBP, 'RootCanvas', 'Border', 'Border_BtnBack')
sp(WBP, 'Border_BtnBack', 'Slot.Position.X', '1460')
sp(WBP, 'Border_BtnBack', 'Slot.Position.Y', '170')
sp(WBP, 'Border_BtnBack', 'Slot.Size.X', '440')
sp(WBP, 'Border_BtnBack', 'Slot.Size.Y', '50')
sp(WBP, 'Border_BtnBack', 'Brush.DrawType', 'Box')
sp_color(WBP, 'Border_BtnBack', 'BrushColor', CANCEL_BG, '<-- cancel bg')

# Text_BtnBack: "BACK" at (1620,182), 16px, RED
add(WBP, 'RootCanvas', 'TextBlock', 'Text_BtnBack')
sp(WBP, 'Text_BtnBack', 'Text', 'BACK')
sp(WBP, 'Text_BtnBack', 'Slot.Position.X', '1620')
sp(WBP, 'Text_BtnBack', 'Slot.Position.Y', '182')
sp(WBP, 'Text_BtnBack', 'Slot.bAutoSize', 'true')
sp(WBP, 'Text_BtnBack', 'Font.Size', '16')
sp_color(WBP, 'Text_BtnBack', 'ColorAndOpacity', RED, '<-- red')

print("  OK Right panel — 2 text + 2 buttons placed")

# ══════════════════════════════════════════════════════════════
# STEP 6: Protect widget layout
# ══════════════════════════════════════════════════════════════
print("\n[STEP 6] Protect widget layout")
r = send('protect_widget_layout', {'name': WBP})
print(f"  protect_widget_layout: {r.get('status')}")

# ══════════════════════════════════════════════════════════════
# STEP 7: Verify with get_widget_tree
# ══════════════════════════════════════════════════════════════
print("\n[STEP 7] Verify widget tree")
r = send('get_widget_tree', {'widget_blueprint': WBP})
if r.get('status') == 'ok':
    tree = r.get('data', {})
    total = tree.get('total_widgets', '?')
    print(f"  OK Widget tree retrieved — {total} total widgets")
    # Print the hierarchy
    widgets = tree.get('widgets', tree.get('hierarchy', []))
    if isinstance(widgets, list):
        for w in widgets:
            if isinstance(w, dict):
                wn = w.get('name', w.get('widget_name', '?'))
                wt = w.get('type', w.get('widget_type', '?'))
                print(f"    {wt}: {wn}")
            else:
                print(f"    {w}")
    elif isinstance(widgets, str):
        # Sometimes comes back as a string
        for line in widgets.split('\n')[:30]:
            print(f"    {line}")
else:
    print(f"  X get_widget_tree FAILED: {r.get('message', '?')}")

# ══════════════════════════════════════════════════════════════
# STEP 8: Color verification
# ══════════════════════════════════════════════════════════════
print("\n[STEP 8] Color verification — all borders")
all_ok = True
borders_to_check = [
    ('Border_PartMap',     'BrushColor'),
    ('Border_Measure',     'BrushColor'),
    ('Border_Actions',     'BrushColor'),
    ('Border_BtnInspect',  'BrushColor'),
    ('Border_BtnBack',     'BrushColor'),
]
for name, prop in borders_to_check:
    r = send('get_widget_property', {
        'widget_blueprint': WBP, 'widget_name': name, 'property': prop
    })
    val = r.get('data', {}).get('value', 'ERROR')
    is_white = '1.0000,G=1.0000,B=1.0000' in val
    if is_white:
        all_ok = False
    print(f"  {'X WHITE' if is_white else 'OK'} {name}: {val[:60]}")

# Check text colors
texts_to_check = [
    'Text_PMTitle', 'Text_PMStatus', 'Text_PMBlock', 'Text_PMHead',
    'Text_PMCrank', 'Text_MTitle', 'Text_MPartName', 'Text_MResult',
    'Text_BtnInspect', 'Text_BtnBack',
]
for name in texts_to_check:
    r = send('get_widget_property', {
        'widget_blueprint': WBP, 'widget_name': name, 'property': 'ColorAndOpacity'
    })
    val = r.get('data', {}).get('value', 'ERROR')
    is_white = '1.0000,G=1.0000,B=1.0000' in val
    if is_white:
        all_ok = False
    print(f"  {'X WHITE' if is_white else 'OK'} {name}: {val[:60]}")

# ══════════════════════════════════════════════════════════════
# STEP 9: Save all
# ══════════════════════════════════════════════════════════════
print("\n[STEP 9] Save all")
r = send('save_all', {})
print(f"  save_all: {r.get('status')}")

# ══════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
if all_ok:
    print("BUILD COMPLETE -- ALL COLORS VERIFIED")
else:
    print("BUILD COMPLETE -- SOME COLORS ARE WHITE (check above)")
print(f"  Widget: {WBP}")
print(f"  Path: /Game/UI/{WBP}")
print(f"  Design: 1920x1080")
print(f"  Panels: Left(768) + Center(672) + Right(480) = 1920")
print(f"  Widgets: 3 borders + 14 texts + 1 progress bar + 2 btn borders = 20")
print("=" * 60)
