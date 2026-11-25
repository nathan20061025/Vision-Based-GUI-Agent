"""Harmless test of the stop controls. It only counts; it controls nothing.

Run:  python stop_demo.py
Then press Esc, or move the mouse into a screen corner.
"""

import time

import pyautogui  # used here only to read the mouse position and screen size

from agent.safety import SafetyGuard, StopRequested, start_stop_key

SECONDS = 20


def main() -> None:
    guard = SafetyGuard(mouse_position=pyautogui.position,
                        screen_size=pyautogui.size())
    listener = start_stop_key(guard)
    print("Press Esc or move the mouse into a screen corner to stop.")
    try:
        for tick in range(SECONDS * 10):
            guard.check()
            if tick % 10 == 0:
                print(f"working... {tick // 10 + 1}/{SECONDS}")
            time.sleep(0.1)
        print("Finished without being stopped.")
    except StopRequested as stop:
        print(f"STOPPED: {stop}")
    finally:
        listener.stop()


if __name__ == "__main__":
    main()
