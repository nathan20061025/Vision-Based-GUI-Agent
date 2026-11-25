"""Convert a position on a web page into a position on the screen.

Assumes: one monitor, browser zoom 100%, no developer tools or side panel,
and equal left, right and bottom window borders.
"""

from dataclasses import dataclass


@dataclass
class WindowInfo:
    """Values read from the browser, in browser (CSS) pixels."""
    screen_x: float      # window's left edge on the screen
    screen_y: float      # window's top edge on the screen
    outer_width: float   # whole window
    outer_height: float
    inner_width: float   # page area only
    inner_height: float
    scale: float         # devicePixelRatio, e.g. 1.25 for 125% scaling


def page_to_screen(x: float, y: float, window: WindowInfo) -> tuple[int, int]:
    """Page position -> real screen pixel position."""
    if not (0 <= x < window.inner_width and 0 <= y < window.inner_height):
        raise ValueError(f"({x}, {y}) is outside the visible page")

    side_border = (window.outer_width - window.inner_width) / 2
    # Everything above the page: title bar, tabs and address bar.
    top_bar = window.outer_height - window.inner_height - side_border

    screen_x = (window.screen_x + side_border + x) * window.scale
    screen_y = (window.screen_y + top_bar + y) * window.scale
    return round(screen_x), round(screen_y)
