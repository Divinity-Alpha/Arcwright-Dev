#!/usr/bin/env python3
"""WBP_EngineProcurement — BoreAndStroke engine procurement UI.

Two-column layout on a CanvasPanel root:
  Left  (60%): Engine list with 3 sample cards
  Right (40%): Detail panel with buy/pass buttons

All children placed directly on RootCanvas with absolute positioning.
Uses BoreAndStroke hex color palette via hex: prefix.
"""

import socket
import json
import time
import sys

# ── TCP Helpers ──────────────────────────────────────────────────────────────

def send(cmd, params, retries=3):
    """Send a TCP command to Arcwright on port 13377."""
    for attempt in range(retries):
        try:
            s = socket.socket()
            s.settimeout(30)
            s.connect(('localhost', 13377))
            s.sendall((json.dumps({'command': cmd, 'params': params}) + '\n').encode())
            buf = b''
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if b'\n' in buf:
                    break
            s.close()
            time.sleep(0.12)
            return json.loads(buf.decode().strip())
        except (ConnectionResetError, ConnectionRefusedError, socket.timeout) as e:
            if attempt < retries - 1:
                print(f"  [RETRY {attempt+1}] {cmd} -- {e}")
                time.sleep(3)
            else:
                raise


def add(wbp, wtype, wname, parent=''):
    """Add a widget child to the blueprint.
    Empty parent = add to root (or become root if no root exists).
    """
    params = {
        'widget_blueprint': wbp,
        'widget_type': wtype,
        'widget_name': wname,
    }
    if parent:
        params['parent_widget'] = parent
    r = send('add_widget_child', params)
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X ADD FAILED {wname}: {r.get('error', r.get('message', '?'))[:80]}")
    return ok


def sp(wbp, wname, prop, val):
    """Set a widget property."""
    r = send('set_widget_property', {
        'widget_blueprint': wbp,
        'widget_name': wname,
        'property': prop,
        'value': str(val) if not isinstance(val, dict) else json.dumps(val),
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X SET FAILED {wname}.{prop}: {r.get('error', r.get('message', '?'))[:80]}")
    return ok


def pos(wbp, wname, x, y):
    """Set position on canvas."""
    sp(wbp, wname, 'position', {'x': x, 'y': y})


def size(wbp, wname, w, h):
    """Set size on canvas."""
    sp(wbp, wname, 'size', {'x': w, 'y': h})


def place(wbp, wname, x, y, w, h):
    """Set position and size on canvas."""
    pos(wbp, wname, x, y)
    size(wbp, wname, w, h)


def add_border(wbp, name, x, y, w, h, color, parent=''):
    """Add a border with position, size, and BrushColor."""
    add(wbp, 'Border', name, parent)
    place(wbp, name, x, y, w, h)
    sp(wbp, name, 'BrushColor', color)


def add_text(wbp, name, text, x, y, font_size, color, parent='',
             typeface=None, w=None, h=None):
    """Add a TextBlock with position, text, font size, and ColorAndOpacity."""
    add(wbp, 'TextBlock', name, parent)
    sp(wbp, name, 'Text', text)
    sp(wbp, name, 'Font.Size', str(font_size))
    sp(wbp, name, 'ColorAndOpacity', color)
    if typeface:
        sp(wbp, name, 'Font.Typeface', typeface)
    # Position
    pos(wbp, name, x, y)
    # Optionally set explicit size
    if w and h:
        size(wbp, name, w, h)


# ── Color Palette (BoreAndStroke) ────────────────────────────────────────────

BG_DEEP    = 'hex:#0A0C0F'
BG_PANEL   = 'hex:#12161C'
BG_CARD    = 'hex:#181D26'
BORDER_C   = 'hex:#2A3040'
BORDER_ACT = 'hex:#3A4560'
ACCENT     = 'hex:#E8A624'
GREEN      = 'hex:#3DDC84'
YELLOW     = 'hex:#F0C040'
RED        = 'hex:#E04050'
TEXT_CLR   = 'hex:#D0D4DC'
DIM        = 'hex:#707888'
BRIGHT     = 'hex:#EEF0F4'
APPROVE_BG = '(R=0.008,G=0.052,B=0.022,A=0.9)'
CANCEL_BG  = '(R=0.073,G=0.006,B=0.009,A=0.8)'

# ── Constants ────────────────────────────────────────────────────────────────

WBP = 'WBP_EngineProcurement'

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("WBP_EngineProcurement -- BoreAndStroke Engine Procurement UI")
print("=" * 60)

# ── STEP 1: Health check ─────────────────────────────────────────────────────
print("\n[STEP 1] Health check")
r = send('health_check', {})
print(f"  Server: {r.get('data', {}).get('server', '?')} v{r.get('data', {}).get('version', '?')}")

# ── STEP 2: Delete old + create widget blueprint ─────────────────────────────
print("\n[STEP 2] Delete old + create WBP_EngineProcurement at /Game/UI/")
send('delete_blueprint', {'name': WBP})
time.sleep(0.5)
r = send('create_widget_blueprint', {
    'name': WBP,
    'path': '/Game/UI',
    'design_width': 1920,
    'design_height': 1080,
})
assert r.get('status') == 'ok', f"CREATE FAILED: {r}"
print(f"  OK Created {WBP}")

# Set design size explicitly to be sure
send('set_widget_design_size', {'name': WBP, 'width': 1920, 'height': 1080})
print("  OK Design size 1920x1080")

# ── STEP 2b: Create root CanvasPanel ──────────────────────────────────────────
print("\n[STEP 2b] Create root CanvasPanel")
add(WBP, 'CanvasPanel', 'RootCanvas')  # empty parent = becomes root
print("  OK RootCanvas created as root widget")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — Engine List (60%, 1152px wide)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[STEP 3] Left column -- engine list panel")

# Background border for list panel
add_border(WBP, 'Border_ListPanel', 0, 0, 1152, 1080, BG_DEEP)
print("  OK Border_ListPanel (0,0 1152x1080) BG_DEEP")

# Title text
add_text(WBP, 'Text_ListTitle', 'AVAILABLE ENGINES', 30, 15, 18, ACCENT)
print("  OK Text_ListTitle")

# Subtitle text
add_text(WBP, 'Text_ListSub', 'Auction & Swap Meet', 30, 45, 13, DIM)
print("  OK Text_ListSub")

# ── Engine Card 1 ─────────────────────────────────────────────────────────────
print("\n[STEP 4] Engine Card 1 -- 1969 Chevy 350 SBC")

add_border(WBP, 'Border_Card1', 20, 80, 1112, 90, BG_PANEL)
print("  OK Border_Card1")

add_text(WBP, 'Text_C1Name', '1969 Chevy 350 SBC', 40, 90, 15, TEXT_CLR)
print("  OK Text_C1Name")

add_text(WBP, 'Text_C1Cond', 'Fair Condition', 40, 115, 12, YELLOW)
print("  OK Text_C1Cond")

add_text(WBP, 'Text_C1Price', '$850', 950, 95, 18, GREEN)
print("  OK Text_C1Price")

# ── Engine Card 2 ─────────────────────────────────────────────────────────────
print("\n[STEP 5] Engine Card 2 -- 1970 Ford 351 Cleveland")

add_border(WBP, 'Border_Card2', 20, 180, 1112, 90, BG_PANEL)
print("  OK Border_Card2")

add_text(WBP, 'Text_C2Name', '1970 Ford 351 Cleveland', 40, 190, 15, TEXT_CLR)
print("  OK Text_C2Name")

add_text(WBP, 'Text_C2Cond', 'Poor Condition', 40, 215, 12, RED)
print("  OK Text_C2Cond")

add_text(WBP, 'Text_C2Price', '$450', 950, 195, 18, GREEN)
print("  OK Text_C2Price")

# ── Engine Card 3 ─────────────────────────────────────────────────────────────
print("\n[STEP 6] Engine Card 3 -- 1972 Pontiac 455")

add_border(WBP, 'Border_Card3', 20, 280, 1112, 90, BG_PANEL)
print("  OK Border_Card3")

add_text(WBP, 'Text_C3Name', '1972 Pontiac 455', 40, 290, 15, TEXT_CLR)
print("  OK Text_C3Name")

add_text(WBP, 'Text_C3Cond', 'Good Condition', 40, 315, 12, GREEN)
print("  OK Text_C3Cond")

add_text(WBP, 'Text_C3Price', '$1,400', 950, 295, 18, GREEN)
print("  OK Text_C3Price")

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Detail Panel (40%, 768px wide, starts at x=1152)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[STEP 7] Right column -- detail panel")

add_border(WBP, 'Border_Detail', 1152, 0, 768, 1080, BG_CARD)
print("  OK Border_Detail (1152,0 768x1080) BG_CARD")

# Detail header
add_text(WBP, 'Text_DetTitle', 'ENGINE DETAILS', 1172, 15, 16, DIM)
print("  OK Text_DetTitle")

# Engine name placeholder
add_text(WBP, 'Text_DetName', 'Select an engine', 1172, 55, 20, ACCENT)
print("  OK Text_DetName")

# Detail fields
add_text(WBP, 'Text_DetYear', 'Year: --', 1172, 100, 14, TEXT_CLR)
print("  OK Text_DetYear")

add_text(WBP, 'Text_DetDisp', 'Displacement: --', 1172, 130, 14, TEXT_CLR)
print("  OK Text_DetDisp")

add_text(WBP, 'Text_DetCond', 'Condition: --', 1172, 160, 14, TEXT_CLR)
print("  OK Text_DetCond")

add_text(WBP, 'Text_DetHist', 'History: --', 1172, 190, 14, DIM)
print("  OK Text_DetHist")

# Price
add_text(WBP, 'Text_DetPrice', 'Asking: --', 1172, 240, 22, YELLOW)
print("  OK Text_DetPrice")

# ── Buttons ───────────────────────────────────────────────────────────────────
print("\n[STEP 8] Buy / Pass buttons")

# BUY button border
add_border(WBP, 'Border_BtnBuy', 1172, 900, 340, 55, APPROVE_BG)
print("  OK Border_BtnBuy")

# BUY text
add_text(WBP, 'Text_BtnBuy', 'BUY', 1300, 912, 20, GREEN, typeface='Bold')
print("  OK Text_BtnBuy")

# PASS button border
add_border(WBP, 'Border_BtnPass', 1532, 900, 340, 55, CANCEL_BG)
print("  OK Border_BtnPass")

# PASS text
add_text(WBP, 'Text_BtnPass', 'PASS', 1660, 912, 20, RED, typeface='Bold')
print("  OK Text_BtnPass")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 9: Protect widget layout
# ══════════════════════════════════════════════════════════════════════════════
print("\n[STEP 9] Protect widget layout")
r = send('protect_widget_layout', {'name': WBP})
print(f"  {r.get('status', '?')}: {r.get('data', {}).get('message', r.get('message', ''))[:80]}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 10: Verify with get_widget_tree
# ══════════════════════════════════════════════════════════════════════════════
print("\n[STEP 10] Verify widget tree")
r = send('get_widget_tree', {'widget_blueprint': WBP})
data = r.get('data', {})
tree = data.get('tree', [])
total = data.get('total_widgets', 0)

# Walk tree and collect names
all_names = set()
def walk(nodes):
    for node in nodes:
        all_names.add(node.get('name', ''))
        if 'children' in node:
            walk(node['children'])

walk(tree)

expected = [
    'Border_ListPanel', 'Text_ListTitle', 'Text_ListSub',
    'Border_Card1', 'Text_C1Name', 'Text_C1Cond', 'Text_C1Price',
    'Border_Card2', 'Text_C2Name', 'Text_C2Cond', 'Text_C2Price',
    'Border_Card3', 'Text_C3Name', 'Text_C3Cond', 'Text_C3Price',
    'Border_Detail', 'Text_DetTitle', 'Text_DetName',
    'Text_DetYear', 'Text_DetDisp', 'Text_DetCond', 'Text_DetHist', 'Text_DetPrice',
    'Border_BtnBuy', 'Text_BtnBuy', 'Border_BtnPass', 'Text_BtnPass',
]

missing = [n for n in expected if n not in all_names]
found = [n for n in expected if n in all_names]

print(f"  Total widgets: {total}")
print(f"  Expected: {len(expected)}  Found: {len(found)}  Missing: {len(missing)}")
if missing:
    print(f"  MISSING: {missing}")
else:
    print("  ALL WIDGETS PRESENT")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 11: Save all
# ══════════════════════════════════════════════════════════════════════════════
print("\n[STEP 11] Save all")
r = send('save_all', {})
print(f"  {r.get('status', '?')}: saved")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if not missing:
    print("SUCCESS: WBP_EngineProcurement built at /Game/UI/")
    print(f"  {len(found)} widgets created, layout protected, saved.")
else:
    print(f"PARTIAL: {len(missing)} widgets missing: {missing}")
print("=" * 60)
