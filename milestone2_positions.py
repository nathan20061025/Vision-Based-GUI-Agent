"""Milestone 2, step 2: are the calculated screen positions correct?

    python milestone2_positions.py           PREVIEW: moves nothing.
        Draws red dots on a picture of the browser's page area.
    python milestone2_positions.py --click   MOVES YOUR REAL MOUSE.
        Clicks each point and measures how far off each click is.

Keep the browser in front. Stop with Esc or a screen corner.
"""

import argparse
import ctypes
import time
from pathlib import Path

import mss
import pyautogui  # also makes this program use real screen pixels on Windows
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

from agent.coordinates import WindowInfo, page_to_screen
from agent.safety import SafetyGuard, StopRequested, start_stop_key

ROOT = Path(__file__).parent
TITLE = "Practice Login"
TARGETS = ["#username", "#password", "#login-button"]


def active_window_title() -> str:
    handle = ctypes.windll.user32.GetForegroundWindow()
    text = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetWindowTextW(handle, text, 256)
    return text.value


def require_practice_window() -> None:
    if TITLE not in active_window_title():
        raise StopRequested("the practice browser is not the active window")


def wait_for_practice_window(page, guard: SafetyGuard, seconds: int = 10) -> None:
    """Give the user time to click the practice browser if it is behind."""
    if TITLE not in active_window_title():
        print(f"Click the practice browser window (waiting {seconds} s)...")
    for _ in range(seconds * 10):
        guard.check()
        if TITLE in active_window_title():
            page.wait_for_timeout(500)
            return
        page.wait_for_timeout(100)
    require_practice_window()


def read_window(page) -> WindowInfo:
    return WindowInfo(**page.evaluate("""() => ({
        screen_x: window.screenX, screen_y: window.screenY,
        outer_width: window.outerWidth, outer_height: window.outerHeight,
        inner_width: window.innerWidth, inner_height: window.innerHeight,
        scale: window.devicePixelRatio})"""))


def centre(page, selector):
    box = page.locator(selector).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def preview(page, out: Path) -> None:
    window = read_window(page)
    left, top = page_to_screen(0, 0, window)
    region = {"left": left, "top": top,
              "width": int(window.inner_width * window.scale),
              "height": int(window.inner_height * window.scale)}

    require_practice_window()
    # Only the page area is captured, not the rest of your screen.
    with mss.MSS() as screen:
        shot = screen.grab(region)
    image = Image.frombytes("RGB", shot.size, shot.rgb)

    draw = ImageDraw.Draw(image)
    for selector in TARGETS:
        x, y = page_to_screen(*centre(page, selector), window)
        x, y = x - left, y - top
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="red")
        print(f"{selector:14} dot at ({x}, {y}) in the picture")

    image.save(out / "preview.png")
    print(f"Window values: {window}")
    print(f"Saved {out / 'preview.png'}")


def click_test(page, guard: SafetyGuard) -> None:
    # The page records where each click actually arrived.
    page.evaluate("""() => document.addEventListener('mousedown',
        e => { window.lastClick = [e.clientX, e.clientY]; }, true)""")

    for selector in TARGETS:
        page.evaluate("window.lastClick = null")
        wanted_x, wanted_y = centre(page, selector)
        x, y = page_to_screen(wanted_x, wanted_y, read_window(page))

        guard.check()
        require_practice_window()
        pyautogui.moveTo(x, y, duration=0.8)
        time.sleep(0.5)  # time to press Esc

        guard.before_action()  # check again immediately before clicking
        require_practice_window()
        pyautogui.click()
        page.wait_for_timeout(300)

        got = page.evaluate("window.lastClick")
        if got is None:
            raise StopRequested(f"click on {selector} did not reach the page")
        print(f"{selector:14} off by x={got[0] - wanted_x:+.1f}, "
              f"y={got[1] - wanted_y:+.1f} page pixels")


def main(click: bool) -> None:
    out = ROOT / "runs" / "positions"
    out.mkdir(parents=True, exist_ok=True)
    url = (ROOT / "practice_sites" / "login" / "index.html").as_uri()

    guard = SafetyGuard(max_actions=len(TARGETS),
                        mouse_position=pyautogui.position if click else None,
                        screen_size=pyautogui.size() if click else None)
    listener = start_stop_key(guard)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, args=["--window-position=0,0",
                                      "--window-size=1000,700"])
            # no_viewport: report the real window size and display scaling.
            page = browser.new_context(no_viewport=True).new_page()
            page.goto(url)
            page.bring_to_front()
            page.wait_for_timeout(2000)
            wait_for_practice_window(page, guard)
            if click:
                click_test(page, guard)
            else:
                preview(page, out)
            browser.close()
    except (StopRequested, pyautogui.FailSafeException) as stop:
        print(f"STOPPED: {stop}")
    finally:
        listener.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--click", action="store_true",
                        help="moves your real mouse")
    main(parser.parse_args().click)
