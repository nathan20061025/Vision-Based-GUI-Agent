"""Perform actions: click, type, press a key and scroll.

Every action checks the safety guard and the active window first.
"""

import ctypes
import time
from contextlib import contextmanager

from agent.safety import StopRequested

# Only these keys may be pressed. Esc is left out: it is the stop key.
ALLOWED_KEYS = {"enter", "tab", "backspace", "delete", "up", "down", "left",
                "right", "pageup", "pagedown", "home", "end"}


def windows_caps_lock_on() -> bool:
    return bool(ctypes.windll.user32.GetKeyState(0x14) & 1)


class Executor:
    def __init__(self, guard, require_window, backend=None,
                 move_seconds=0.5, type_delay=0.08,
                 caps_lock_on=windows_caps_lock_on, logger=None):
        """require_window: function that raises if the wrong window is active.
        backend: pyautogui by default; tests pass in a fake one.
        """
        if backend is None:
            import pyautogui
            backend = pyautogui
        self.guard = guard
        self.require_window = require_window
        self.backend = backend
        self.move_seconds = move_seconds
        self.type_delay = type_delay
        self.caps_lock_on = caps_lock_on
        self.logger = logger

    @contextmanager
    def _logged(self, action: str, **details):
        """Record the action, its result and how long it took."""
        start = time.perf_counter()
        status = "done"
        try:
            yield
        except StopRequested:
            status = "stopped"
            raise
        except BaseException as error:
            status = f"error: {type(error).__name__}"  # no message: may hold text
            raise
        finally:
            if self.logger:
                self.logger.log("action", action=action, status=status,
                                seconds=round(time.perf_counter() - start, 3),
                                **details)

    def _check(self) -> None:
        self.guard.check()
        self.require_window()

    def _start_action(self) -> None:
        self.guard.before_action()  # also counts towards the action limit
        self.require_window()

    def _move(self, x: int, y: int) -> None:
        self._check()
        self.backend.moveTo(x, y, duration=self.move_seconds)

    def click(self, x: int, y: int) -> None:
        with self._logged("click", x=x, y=y):
            self._move(x, y)
            self._start_action()  # check again after moving
            self.backend.click()

    def type_text(self, text: str) -> None:
        # pyautogui cannot type every character, so reject others up front.
        if not all(" " <= char <= "~" for char in text):
            raise ValueError("only plain English keyboard characters are supported")
        # Log only the length, never the text itself.
        with self._logged("type", characters=len(text)):
            self._start_action()
            for char in text:
                self._check()  # before every character
                if self.caps_lock_on():  # it would swap upper and lower case
                    raise StopRequested("Caps Lock is on: turn it off and run again")
                self.backend.write(char)
                time.sleep(self.type_delay)

    def press(self, key: str) -> None:
        if key not in ALLOWED_KEYS:
            raise ValueError(f"key not allowed: {key!r}")
        with self._logged("press", key=key):
            self._start_action()
            self.backend.press(key)

    def scroll(self, x: int, y: int, amount: int) -> None:
        """Scroll with the mouse at (x, y). Negative amount scrolls down."""
        with self._logged("scroll", x=x, y=y, amount=amount):
            self._move(x, y)
            self._start_action()
            self.backend.scroll(amount)
