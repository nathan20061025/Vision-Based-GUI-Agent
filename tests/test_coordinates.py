import pytest

from agent.coordinates import WindowInfo, page_to_screen


def window(scale=1.0):
    # Borders are 8 px, so the top bar is 700 - 612 - 8 = 80 px.
    return WindowInfo(screen_x=100, screen_y=50, outer_width=816,
                      outer_height=700, inner_width=800, inner_height=612,
                      scale=scale)


def test_adds_window_position_border_and_top_bar():
    assert page_to_screen(0, 0, window()) == (108, 130)
    assert page_to_screen(200, 100, window()) == (308, 230)


def test_applies_display_scaling():
    assert page_to_screen(200, 100, window(scale=1.25)) == (385, 288)


@pytest.mark.parametrize("point", [(-1, 0), (0, -1), (800, 0), (0, 612)])
def test_rejects_points_outside_the_page(point):
    with pytest.raises(ValueError):
        page_to_screen(*point, window())
