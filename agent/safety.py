"""Safety controls: a stop key, a screen-corner stop and an action limit."""

import threading

CORNER_MARGIN = 5  # pixels from a corner that still count as "in the corner"


class StopRequested(Exception):
    """Raised when the agent must stop."""


def in_corner(x, y, width, height, margin=CORNER_MARGIN) -> bool:
    """True if the point is in any corner of the (primary) screen."""
    near_left_or_right = x <= margin or x >= width - 1 - margin
    near_top_or_bottom = y <= margin or y >= height - 1 - margin
    return near_left_or_right and near_top_or_bottom


class SafetyGuard:
    """Call check() while waiting and before_action() before every action.

    This does not interrupt code by itself: the program only stops at the
    next check, so call it often. Once stopped, it stays stopped.
    """

    def __init__(self, max_actions=20, mouse_position=None, screen_size=None):
        self.max_actions = max_actions
        self.actions = 0
        self.reason = None
        self._mouse_position = mouse_position  # function returning (x, y)
        self._screen_size = screen_size        # (width, height)
        self._stopped = threading.Event()      # safe to set from another thread

    def stop(self, reason: str) -> None:
        if not self._stopped.is_set():
            self.reason = reason  # keep the first reason
            self._stopped.set()

    def check(self) -> None:
        if self._mouse_position and self._screen_size:
            if in_corner(*self._mouse_position(), *self._screen_size):
                self.stop("mouse moved to a screen corner")
        if self._stopped.is_set():
            raise StopRequested(self.reason)

    def before_action(self) -> None:
        self.check()
        if self.actions >= self.max_actions:
            self.stop(f"action limit of {self.max_actions} reached")
            self.check()
        self.actions += 1


def start_stop_key(guard: SafetyGuard):
    """Listen for Esc, even when another window is active.

    Returns the listener; call .stop() on it when finished.
    It only reacts to Esc and does not record any keys.
    Note: if the agent itself presses Esc later, this will also stop it.
    """
    from pynput import keyboard

    def on_press(key):
        if key == keyboard.Key.esc:
            guard.stop("Esc key pressed")

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    listener.wait()  # make sure it is ready
    return listener
