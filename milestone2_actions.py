"""Milestone 2, step 3: log in and scroll using the REAL mouse and keyboard.

    python milestone2_actions.py
    python milestone2_actions.py --capture   also take FULL-SCREEN pictures
                                             before and after each action;
                                             deleted when the run ends
    python milestone2_actions.py --capture --keep   keep the pictures

THIS CONTROLS YOUR MOUSE AND KEYBOARD. Do not touch them while it runs,
except to stop it: press Esc or move the mouse into a screen corner.

Playwright still finds the elements and checks the results.
"""

import argparse
import ctypes
from contextlib import nullcontext
from pathlib import Path

import pyautogui
from playwright.sync_api import sync_playwright

from agent.capture import ActionCapture, run_folder
from agent.coordinates import page_to_screen
from agent.executor import Executor
from agent.logger import RunLogger
from agent.pixel_rule import changed_share
from agent.safety import SafetyGuard, StopRequested, start_stop_key
from milestone2_positions import (centre, read_window, require_practice_window,
                                  wait_for_practice_window)

ROOT = Path(__file__).parent


def report(name: str, passed: bool, logger: RunLogger) -> None:
    logger.log("check", name=name, passed=passed)
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        # Do not carry on after a failed step.
        raise StopRequested(f"check failed: {name}")


def run(page, executor: Executor, capture: ActionCapture | None) -> None:
    def act(label, action):
        if capture is None:
            action()
            return
        before, after = capture.around(label, action)
        share = changed_share(before, after)
        executor.logger.log("screen_change", step=label,
                            changed_share=round(share, 6))
        print(f"  {capture.count:02d} {label:14} changed "
              f"{share:.2%} of the full screen")

    def screen_point(x, y):
        return page_to_screen(x, y, read_window(page))

    def pause():
        page.wait_for_timeout(500)

    point = screen_point(*centre(page, "#username"))
    act("click_username", lambda: executor.click(*point))
    page.wait_for_timeout(200)
    focused_before = page.evaluate("document.activeElement.id")
    act("type_username", lambda: executor.type_text("testuser"))
    pause()
    typed = page.input_value("#username")
    if typed != "testuser":
        # Details to find the cause. These are fake login details only.
        caps_lock = bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
        print(f"  focused after click : {focused_before!r}")
        print(f"  username box holds  : {typed!r}")
        print(f"  password box holds  : {len(page.input_value('#password'))} characters")
        print(f"  Caps Lock on        : {caps_lock}")
    report("type username", typed == "testuser", executor.logger)

    act("press_tab", lambda: executor.press("tab"))
    pause()
    focused = page.evaluate("document.activeElement.id")
    report("tab to password box", focused == "password", executor.logger)

    act("type_password", lambda: executor.type_text("test123"))
    pause()
    report("type password", page.input_value("#password") == "test123", executor.logger)

    point = screen_point(*centre(page, "#login-button"))
    act("click_login", lambda: executor.click(*point))
    pause()
    report("log in", page.locator("#welcome").count() == 1, executor.logger)

    # Make the page taller so there is something to scroll.
    page.evaluate("document.body.style.height = '3000px'")
    window = read_window(page)
    middle = page_to_screen(window.inner_width / 2, window.inner_height / 2, window)
    act("scroll_down", lambda: executor.scroll(*middle, -500))
    page.wait_for_timeout(1000)
    report("scroll down", page.evaluate("window.scrollY") > 0, executor.logger)


def main(use_capture: bool, keep: bool) -> None:
    url = (ROOT / "practice_sites" / "login" / "index.html").as_uri()
    guard = SafetyGuard(max_actions=6, mouse_position=pyautogui.position,
                        screen_size=pyautogui.size())
    listener = start_stop_key(guard)
    logger = RunLogger(ROOT / "runs" / "logs")
    logger.log("run_start", demo="milestone2_actions", capture=use_capture,
               keep_pictures=keep, screen=list(pyautogui.size()))
    result = {"status": "finished", "reason": None}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, args=["--window-position=0,0",
                                      "--window-size=1000,700"])
            page = browser.new_context(no_viewport=True).new_page()
            page.goto(url)
            page.bring_to_front()
            page.wait_for_timeout(2000)
            wait_for_practice_window(page, guard)
            pictures = (run_folder(ROOT / "runs" / "capture", keep)
                        if use_capture else nullcontext())
            # The folder is cleaned up when this block ends, even on a stop.
            with pictures as folder:
                capture = None
                if folder:
                    capture = ActionCapture(folder, require_practice_window,
                                            lambda: page.wait_for_timeout(500))
                    print(f"Pictures in {folder}" if keep else
                          "Taking temporary pictures (deleted when the run ends)")
                executor = Executor(guard, require_practice_window, logger=logger)
                run(page, executor, capture)
            print("All checks passed.")
            page.wait_for_timeout(2000)  # time to see the result
            browser.close()
    except (StopRequested, pyautogui.FailSafeException) as stop:
        result = {"status": "stopped",
                  "reason": str(stop) or "mouse moved to a screen corner"}
        print(f"STOPPED: {stop}")
    except BaseException as error:
        result = {"status": "error", "reason": type(error).__name__}
        raise
    finally:
        listener.stop()
        logger.log("run_end", **result)
        print(f"Log: {logger.path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", action="store_true",
                        help="take full-screen pictures (close private windows)")
    parser.add_argument("--keep", action="store_true",
                        help="with --capture: do not delete the pictures")
    args = parser.parse_args()
    if args.keep and not args.capture:
        parser.error("--keep only works with --capture")
    main(args.capture, args.keep)
