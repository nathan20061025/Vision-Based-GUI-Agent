"""Full-screen screenshots before and after each action.

WARNING: a full-screen picture shows everything visible on the main screen.
"""

import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from PIL import Image


def grab_full_screen() -> Image.Image:
    """Picture of the whole main monitor."""
    import mss

    with mss.MSS() as screen:
        shot = screen.grab(screen.monitors[1])  # 1 = first real monitor
    return Image.frombytes("RGB", shot.size, shot.rgb)


class ActionCapture:
    """Saves a picture before and after an action."""

    def __init__(self, folder: Path, require_window, wait, grab=grab_full_screen):
        """require_window: raises if the wrong window is active.
        wait: function that waits for the screen to update after an action.
        grab: tests pass in a fake one.
        """
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.require_window = require_window
        self.wait = wait
        self.grab = grab
        self.count = 0

    def _save(self, name: str):
        self.require_window()  # do not photograph if another window is active
        image = self.grab()
        image.save(self.folder / f"{name}.png")
        return image

    def around(self, label: str, action):
        """Capture, do the action, wait, capture. Returns (before, after).

        If anything raises, no further pictures are taken.
        """
        self.count += 1
        name = f"{self.count:02d}_{label}"
        before = self._save(f"{name}_before")
        action()
        self.wait()
        after = self._save(f"{name}_after")
        return before, after


def new_run_folder(root: Path) -> Path:
    """A new folder for each run, so old pictures are not overwritten."""
    return Path(root) / datetime.now().strftime("%Y%m%d_%H%M%S_%f")


@contextmanager
def run_folder(root: Path, keep: bool = False):
    """A folder for one run's pictures. Deleted afterwards unless keep=True.

    It is also deleted after a stop or an error. It CANNOT be deleted if the
    program is killed, e.g. by closing the terminal or a power cut.
    Only this run's folder is removed; other runs are left alone.
    """
    folder = new_run_folder(root)
    folder.mkdir(parents=True, exist_ok=False)
    try:
        yield folder
    finally:
        if not keep:
            shutil.rmtree(folder)
