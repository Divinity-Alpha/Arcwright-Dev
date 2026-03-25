import time
import shutil
import hashlib
import pyperclip
from pathlib import Path

from playwright.sync_api import sync_playwright

WATCH_FILE = Path(r"C:\Arcwright\GRADE_ME.txt")
WATCH_DIR = WATCH_FILE.parent
PROCESSED_DIR = WATCH_DIR / "_processed"
FAILED_DIR = WATCH_DIR / "_failed"

CLAUDE_URL = "https://claude.ai/chat/763112a1-4c1c-418a-b2da-6057a10650db"

POLL_SECONDS = 1.0

# If Enter creates a newline instead of sending, set to True
SEND_WITH_CTRL_ENTER = False

CDP_ENDPOINT = "http://127.0.0.1:9222"  # Chrome remote debugging port

def ensure_dirs():
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    if not WATCH_FILE.exists():
        WATCH_FILE.write_text("", encoding="utf-8")

def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252", errors="replace")

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

def wait_for_file_ready(path: Path, timeout_sec: float = 10.0) -> bool:
    start = time.time()
    last_size = -1
    stable = 0
    while time.time() - start < timeout_sec:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False

        if size == last_size:
            stable += 1
            if stable >= 3:
                return True
        else:
            stable = 0
            last_size = size
        time.sleep(0.25)
    return False

def move_file(src: Path, dest_dir: Path) -> Path:
    dest = dest_dir / src.name
    if dest.exists():
        dest = dest_dir / f"{src.stem}_{int(time.time())}{src.suffix}"
    shutil.move(str(src), str(dest))
    return dest

def focus_claude_input(page):
    # Try common textbox patterns (Claude uses contenteditable)
    selectors = [
        "div[contenteditable='true']",
        "[role='textbox']",
        "div[contenteditable='true'][role='textbox']",
    ]
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            try:
                loc.first.wait_for(state="visible", timeout=3000)
                loc.first.click()
                return True
            except Exception:
                pass

    # Fallback click near bottom center
    vp = page.viewport_size or {"width": 1200, "height": 800}
    page.mouse.click(vp["width"] // 2, int(vp["height"] * 0.85))
    page.wait_for_timeout(200)

    loc = page.locator("div[contenteditable='true'], [role='textbox']")
    loc.first.wait_for(state="visible", timeout=5000)
    loc.first.click()
    return True

def get_or_open_claude_page(context):
    # Look for an existing tab that matches your Claude chat
    for p in context.pages:
        try:
            if p.url.startswith(CLAUDE_URL):
                return p
        except Exception:
            pass

    # If not found, open a new tab to that URL
    page = context.new_page()
    page.goto(CLAUDE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    return page

def send_to_existing_chrome(message: str):
    with sync_playwright() as p:
        # Connect to the already-running Chrome
        browser = p.chromium.connect_over_cdp(CDP_ENDPOINT)

        # Use the first available context (it represents the logged-in profile)
        contexts = browser.contexts
        if not contexts:
            raise RuntimeError("No browser contexts found. Is Chrome running with --remote-debugging-port=9222?")
        context = contexts[0]

        page = get_or_open_claude_page(context)
        page.bring_to_front()

        # Ensure it’s loaded
        if not page.url.startswith("https://claude.ai"):
            page.goto(CLAUDE_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(800)

        # Focus composer + type + send
        focus_claude_input(page)

        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")

        # Normalize line endings (important)
        message = message.replace("\r\n", "\n").replace("\r", "\n")

        # Copy to clipboard
        pyperclip.copy(message)

        # Paste
        page.keyboard.press("Control+V")

        # Send
        if SEND_WITH_CTRL_ENTER:
            page.keyboard.press("Control+Enter")
        else:
            page.keyboard.press("Enter")


def main():
    ensure_dirs()

    print(f"Watching file: {WATCH_FILE}")
    print(f"Processed folder: {PROCESSED_DIR}")
    print(f"Failed folder: {FAILED_DIR}")
    print(f"Claude URL: {CLAUDE_URL}")
    print(f"CDP endpoint: {CDP_ENDPOINT}")
    print("Make sure Chrome was launched with --remote-debugging-port=9222 and you are logged in.")
    print("Press Ctrl+C to stop.\n")

    last_hash = None
    last_mtime = 0.0

    while True:
        try:
            mtime = WATCH_FILE.stat().st_mtime
            if mtime != last_mtime:
                last_mtime = mtime

                if not wait_for_file_ready(WATCH_FILE):
                    time.sleep(POLL_SECONDS)
                    continue

                text = read_text_file(WATCH_FILE).strip()
                if not text:
                    print("[i] File changed but empty; ignoring.")
                    time.sleep(POLL_SECONDS)
                    continue

                h = sha256_text(text)
                if h == last_hash:
                    print("[i] Content unchanged; not resending.")
                    time.sleep(POLL_SECONDS)
                    continue

                print("[+] New content detected. Sending to existing Chrome tab...")
                send_to_existing_chrome(text)
                last_hash = h
                print("[✓] Sent.")

                moved = move_file(WATCH_FILE, PROCESSED_DIR)
                print(f"[✓] Moved file to: {moved}\n")

                WATCH_FILE.write_text("", encoding="utf-8")
                last_mtime = WATCH_FILE.stat().st_mtime

        except KeyboardInterrupt:
            print("\nStopping.")
            return
        except Exception as e:
            print(f"[x] Error: {e}")
            try:
                if WATCH_FILE.exists() and WATCH_FILE.stat().st_size > 0:
                    moved = move_file(WATCH_FILE, FAILED_DIR)
                    print(f"[!] Moved file to failed: {moved}\n")
                    WATCH_FILE.write_text("", encoding="utf-8")
                    last_mtime = WATCH_FILE.stat().st_mtime
            except Exception:
                pass

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()