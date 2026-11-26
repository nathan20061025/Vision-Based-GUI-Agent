"""Where the agent looks and acts. Both give it pictures only.

HiddenEnv: a hidden browser. For development; your mouse is not used.
ScreenEnv: real screen pictures of the page area, your real mouse and
           keyboard (through agent/executor.py).
"""

import io
import time

from PIL import Image

from agent.coordinates import page_to_screen


class HiddenEnv:
    """The page must have device scale 1, so picture and mouse units match."""

    def __init__(self, page):
        self.page = page

    def capture(self) -> Image.Image:
        return Image.open(io.BytesIO(self.page.screenshot())).convert("RGB")

    def click(self, x: int, y: int) -> None:
        self.page.mouse.click(x, y)

    def type_text(self, text: str) -> None:
        self.page.keyboard.type(text)

    def press(self, key: str) -> None:
        self.page.keyboard.press({"enter": "Enter", "tab": "Tab"}[key])

    def wait(self, seconds: float) -> None:
        self.page.wait_for_timeout(seconds * 1000)


class ScreenEnv:
    """Captures only the browser's page area.

    TEMPORARY HELP: the position of that area comes from the browser's window
    values (via window_info), not from looking at the screen.
    """

    def __init__(self, window_info, executor, guard, require_window, wait=None):
        self.window_info = window_info    # function returning WindowInfo
        self.executor = executor
        self.guard = guard
        self.require_window = require_window
        self._wait = wait or time.sleep

    def _region(self):
        window = self.window_info()
        left, top = page_to_screen(0, 0, window)
        return {"left": left, "top": top,
                "width": int(window.inner_width * window.scale),
                "height": int(window.inner_height * window.scale)}

    def capture(self) -> Image.Image:
        import mss

        self.guard.check()
        self.require_window()  # never photograph some other window
        with mss.MSS() as screen:
            shot = screen.grab(self._region())
        return Image.frombytes("RGB", shot.size, shot.rgb)

    def click(self, x: int, y: int) -> None:
        region = self._region()
        if not (0 <= x < region["width"] and 0 <= y < region["height"]):
            raise ValueError("click outside the page area")
        self.executor.click(region["left"] + x, region["top"] + y)

    def type_text(self, text: str) -> None:
        self.executor.type_text(text)

    def press(self, key: str) -> None:
        self.executor.press(key)

    def wait(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.guard.check()  # Esc also works while waiting
            self._wait(0.1)
