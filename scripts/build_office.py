"""Build WBP_Office widget blueprint via TCP on port 13377.

Tabbed layout with JOBS / FINANCES / REPUTATION panels.
BoreAndStroke color palette. Design size 1920x1080.

Usage:
    python scripts/build_office.py
"""

import socket
import json
import sys
import time


# ---------------------------------------------------------------------------
# TCP helper (one connection per command, matching project pattern)
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


def add_child(wtype, wname, parent='RootCanvas'):
    """Add a widget child to WBP_Office.
    Pass parent='' to create the root widget (first call only).
    """
    params = {
        'widget_blueprint': WBP,
        'widget_type': wtype,
        'widget_name': wname,
    }
    if parent:
        params['parent_widget'] = parent
    return send_command('add_widget_child', params)


def sp(wname, prop, value):
    """Set a widget property on WBP_Office."""
    return send_command('set_widget_property', {
        'widget_blueprint': WBP,
        'widget_name': wname,
        'property': prop,
        'value': value,
    })


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WBP = 'WBP_Office'
WBP_PATH = '/Game/UI'

# BoreAndStroke hex palette (rule 17: always use hex: prefix)
BG_DEEP    = 'hex:#0A0C0F'
BG_PANEL   = 'hex:#12161C'
BG_CARD    = 'hex:#181D26'
ACCENT     = 'hex:#E8A624'
GREEN      = 'hex:#3DDC84'
YELLOW     = 'hex:#F0C040'
RED        = 'hex:#E04050'
TEXT       = 'hex:#D0D4DC'
DIM        = 'hex:#707888'
BRIGHT     = 'hex:#EEF0F4'
TAB_BAR_BG = '(R=0.0,G=0.0,B=0.0,A=0.35)'  # semi-transparent black


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------

def build_tab_bar():
    """Tab bar across the top: 1920x60 at (0,0)."""
    print('  [1/4] Building tab bar...')

    # Tab bar background
    add_child('Border', 'Border_TabBar')
    sp('Border_TabBar', 'position', {'x': 0, 'y': 0})
    sp('Border_TabBar', 'size', {'x': 1920, 'y': 60})
    sp('Border_TabBar', 'BrushColor', TAB_BAR_BG)

    # --- Tab: JOBS (active) ---
    add_child('Border', 'Border_TabJobs')
    sp('Border_TabJobs', 'position', {'x': 20, 'y': 8})
    sp('Border_TabJobs', 'size', {'x': 180, 'y': 44})
    sp('Border_TabJobs', 'BrushColor', BG_CARD)

    add_child('TextBlock', 'Text_TabJobs')
    sp('Text_TabJobs', 'position', {'x': 70, 'y': 18})
    sp('Text_TabJobs', 'Text', 'JOBS')
    sp('Text_TabJobs', 'Font.Size', '16')
    sp('Text_TabJobs', 'Font.Typeface', 'Bold')
    sp('Text_TabJobs', 'ColorAndOpacity', ACCENT)

    # --- Tab: FINANCES (inactive) ---
    add_child('Border', 'Border_TabFinance')
    sp('Border_TabFinance', 'position', {'x': 220, 'y': 8})
    sp('Border_TabFinance', 'size', {'x': 180, 'y': 44})
    sp('Border_TabFinance', 'BrushColor', BG_PANEL)

    add_child('TextBlock', 'Text_TabFinance')
    sp('Text_TabFinance', 'position', {'x': 260, 'y': 18})
    sp('Text_TabFinance', 'Text', 'FINANCES')
    sp('Text_TabFinance', 'Font.Size', '16')
    sp('Text_TabFinance', 'ColorAndOpacity', DIM)

    # --- Tab: REPUTATION (inactive) ---
    add_child('Border', 'Border_TabRep')
    sp('Border_TabRep', 'position', {'x': 420, 'y': 8})
    sp('Border_TabRep', 'size', {'x': 180, 'y': 44})
    sp('Border_TabRep', 'BrushColor', BG_PANEL)

    add_child('TextBlock', 'Text_TabRep')
    sp('Text_TabRep', 'position', {'x': 450, 'y': 18})
    sp('Text_TabRep', 'Text', 'REPUTATION')
    sp('Text_TabRep', 'Font.Size', '16')
    sp('Text_TabRep', 'ColorAndOpacity', DIM)

    print('    Tab bar complete (3 tabs)')


def build_jobs_panel():
    """JOBS panel: visible by default."""
    print('  [2/4] Building JOBS panel...')

    add_child('Border', 'Border_PanelJobs')
    sp('Border_PanelJobs', 'position', {'x': 0, 'y': 60})
    sp('Border_PanelJobs', 'size', {'x': 1920, 'y': 1020})
    sp('Border_PanelJobs', 'BrushColor', BG_DEEP)

    add_child('TextBlock', 'Text_JobsTitle')
    sp('Text_JobsTitle', 'position', {'x': 40, 'y': 80})
    sp('Text_JobsTitle', 'Text', 'ACTIVE ORDERS')
    sp('Text_JobsTitle', 'Font.Size', '18')
    sp('Text_JobsTitle', 'ColorAndOpacity', ACCENT)

    add_child('TextBlock', 'Text_Job1')
    sp('Text_Job1', 'position', {'x': 40, 'y': 120})
    sp('Text_Job1', 'Text', 'No active orders')
    sp('Text_Job1', 'Font.Size', '14')
    sp('Text_Job1', 'ColorAndOpacity', TEXT)

    add_child('TextBlock', 'Text_JobDeadline')
    sp('Text_JobDeadline', 'position', {'x': 40, 'y': 150})
    sp('Text_JobDeadline', 'Text', 'Deadline: --')
    sp('Text_JobDeadline', 'Font.Size', '13')
    sp('Text_JobDeadline', 'ColorAndOpacity', YELLOW)

    add_child('TextBlock', 'Text_JobValue')
    sp('Text_JobValue', 'position', {'x': 40, 'y': 180})
    sp('Text_JobValue', 'Text', 'Value: --')
    sp('Text_JobValue', 'Font.Size', '13')
    sp('Text_JobValue', 'ColorAndOpacity', GREEN)

    print('    JOBS panel complete (4 text elements)')


def build_finance_panel():
    """FINANCES panel: initially hidden (Collapsed)."""
    print('  [3/4] Building FINANCES panel...')

    add_child('Border', 'Border_PanelFinance')
    sp('Border_PanelFinance', 'position', {'x': 0, 'y': 60})
    sp('Border_PanelFinance', 'size', {'x': 1920, 'y': 1020})
    sp('Border_PanelFinance', 'BrushColor', BG_DEEP)
    sp('Border_PanelFinance', 'Visibility', 'Collapsed')

    add_child('TextBlock', 'Text_FinTitle')
    sp('Text_FinTitle', 'position', {'x': 40, 'y': 80})
    sp('Text_FinTitle', 'Text', 'FINANCIAL OVERVIEW')
    sp('Text_FinTitle', 'Font.Size', '18')
    sp('Text_FinTitle', 'ColorAndOpacity', ACCENT)

    add_child('TextBlock', 'Text_Cash')
    sp('Text_Cash', 'position', {'x': 40, 'y': 120})
    sp('Text_Cash', 'Text', 'Cash: $5,000')
    sp('Text_Cash', 'Font.Size', '16')
    sp('Text_Cash', 'ColorAndOpacity', GREEN)

    add_child('TextBlock', 'Text_Revenue')
    sp('Text_Revenue', 'position', {'x': 40, 'y': 160})
    sp('Text_Revenue', 'Text', 'Revenue (MTD): $0')
    sp('Text_Revenue', 'Font.Size', '14')
    sp('Text_Revenue', 'ColorAndOpacity', TEXT)

    add_child('TextBlock', 'Text_Expenses')
    sp('Text_Expenses', 'position', {'x': 40, 'y': 190})
    sp('Text_Expenses', 'Text', 'Expenses (MTD): $0')
    sp('Text_Expenses', 'Font.Size', '14')
    sp('Text_Expenses', 'ColorAndOpacity', TEXT)

    add_child('TextBlock', 'Text_Loans')
    sp('Text_Loans', 'position', {'x': 40, 'y': 230})
    sp('Text_Loans', 'Text', 'Loans: $0')
    sp('Text_Loans', 'Font.Size', '14')
    sp('Text_Loans', 'ColorAndOpacity', RED)

    print('    FINANCES panel complete (5 text elements, initially Collapsed)')


def build_rep_panel():
    """REPUTATION panel: initially hidden (Collapsed)."""
    print('  [4/4] Building REPUTATION panel...')

    add_child('Border', 'Border_PanelRep')
    sp('Border_PanelRep', 'position', {'x': 0, 'y': 60})
    sp('Border_PanelRep', 'size', {'x': 1920, 'y': 1020})
    sp('Border_PanelRep', 'BrushColor', BG_DEEP)
    sp('Border_PanelRep', 'Visibility', 'Collapsed')

    add_child('TextBlock', 'Text_RepTitle')
    sp('Text_RepTitle', 'position', {'x': 40, 'y': 80})
    sp('Text_RepTitle', 'Text', 'SHOP REPUTATION')
    sp('Text_RepTitle', 'Font.Size', '18')
    sp('Text_RepTitle', 'ColorAndOpacity', ACCENT)

    add_child('TextBlock', 'Text_Rating')
    sp('Text_Rating', 'position', {'x': 40, 'y': 120})
    sp('Text_Rating', 'Text', 'Rating: 3.0 / 5.0')
    sp('Text_Rating', 'Font.Size', '16')
    sp('Text_Rating', 'ColorAndOpacity', YELLOW)

    add_child('TextBlock', 'Text_Level')
    sp('Text_Level', 'position', {'x': 40, 'y': 160})
    sp('Text_Level', 'Text', 'Shop Level: Novice')
    sp('Text_Level', 'Font.Size', '14')
    sp('Text_Level', 'ColorAndOpacity', TEXT)

    add_child('TextBlock', 'Text_Reviews')
    sp('Text_Reviews', 'position', {'x': 40, 'y': 200})
    sp('Text_Reviews', 'Text', 'Customer Reviews: 0')
    sp('Text_Reviews', 'Font.Size', '14')
    sp('Text_Reviews', 'ColorAndOpacity', DIM)

    print('    REPUTATION panel complete (4 text elements, initially Collapsed)')


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify():
    """Verify all expected widgets exist in the tree."""
    print('\n  Verifying widget tree...')
    result = send_command('get_widget_tree', {'widget_blueprint': WBP})
    data = result['data']
    total = data['total_widgets']

    # Collect all widget names
    names = set()

    def walk(nodes):
        for node in nodes:
            names.add(node['name'])
            if 'children' in node:
                walk(node['children'])

    walk(data['tree'])

    expected = [
        # Tab bar
        'Border_TabBar', 'Border_TabJobs', 'Text_TabJobs',
        'Border_TabFinance', 'Text_TabFinance',
        'Border_TabRep', 'Text_TabRep',
        # Jobs panel
        'Border_PanelJobs', 'Text_JobsTitle', 'Text_Job1',
        'Text_JobDeadline', 'Text_JobValue',
        # Finance panel
        'Border_PanelFinance', 'Text_FinTitle', 'Text_Cash',
        'Text_Revenue', 'Text_Expenses', 'Text_Loans',
        # Rep panel
        'Border_PanelRep', 'Text_RepTitle', 'Text_Rating',
        'Text_Level', 'Text_Reviews',
    ]

    missing = [n for n in expected if n not in names]
    if missing:
        print(f'  FAIL: missing {len(missing)} widgets: {missing}')
        return False
    else:
        print(f'  OK: all {len(expected)} expected widgets present (total in tree: {total})')
        return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('=' * 60)
    print('  WBP_Office Builder')
    print('  Tabbed layout: JOBS / FINANCES / REPUTATION')
    print('=' * 60)

    # Health check
    try:
        r = send_command('health_check')
        print(f"  Connected to Arcwright v{r['data'].get('version', '?')}")
    except Exception as e:
        print(f'  ERROR: Cannot connect to Command Server: {e}')
        sys.exit(1)

    # Delete if exists, then create
    print('\n  Deleting old WBP_Office (if any)...')
    try:
        send_command('delete_blueprint', {'name': WBP})
        time.sleep(0.3)
    except Exception:
        pass  # doesn't exist yet, fine

    print('  Creating widget blueprint...')
    r = send_command('create_widget_blueprint', {
        'name': WBP,
        'path': WBP_PATH,
        'design_width': 1920,
        'design_height': 1080,
    })
    if r.get('status') != 'ok':
        print(f"  CREATE FAILED: {r.get('message', '?')}")
        sys.exit(1)
    print(f"  Created {WBP} at {WBP_PATH}")

    # Set design size explicitly (rule 16)
    send_command('set_widget_design_size', {'name': WBP, 'width': 1920, 'height': 1080})
    print('  Design size set to 1920x1080')

    # Create root CanvasPanel (no parent = becomes root widget)
    print('  Creating root CanvasPanel...')
    add_child('CanvasPanel', 'RootCanvas', parent='')
    print('  RootCanvas created.')

    # Build all sections (children of RootCanvas)
    build_tab_bar()
    build_jobs_panel()
    build_finance_panel()
    build_rep_panel()

    # Protect layout (rule 18)
    print('\n  Protecting widget layout...')
    try:
        send_command('protect_widget_layout', {'name': WBP})
        print('  Layout protected.')
    except Exception as e:
        print(f'  protect_widget_layout warning: {e}')

    # Verify
    ok = verify()

    # Save all
    print('\n  Saving all assets...')
    try:
        send_command('save_all', timeout=30)
        print('  Save complete.')
    except Exception as e:
        print(f'  Save warning: {e}')

    # Summary
    print('\n' + '=' * 60)
    if ok:
        print('  SUCCESS: WBP_Office built and verified.')
    else:
        print('  PARTIAL: WBP_Office built but verification found issues.')
    print('=' * 60)

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
