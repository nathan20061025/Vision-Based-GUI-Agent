"""Real-screen environment, tested with fakes (no mouse is moved)."""

import pytest

from agent.coordinates import WindowInfo
from agent.environments import ScreenEnv
from agent.safety import SafetyGuard, StopRequested


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def type_text(self, text):
        self.calls.append(("type", text))

    def press(self, key):
        self.calls.append(("press", key))


def make(guard=None, require_window=lambda: None):
    window = WindowInfo(screen_x=0, screen_y=0, outer_width=1000, outer_height=700,
                        inner_width=984, inner_height=605, scale=1)
    executor = FakeExecutor()
    env = ScreenEnv(lambda: window, executor, guard or SafetyGuard(),
                    require_window, wait=lambda s: None)
    return env, executor


def test_picture_positions_become_screen_positions():
    env, executor = make()
    env.click(100, 50)
    # border 8 px, top bar 700 - 605 - 8 = 87 px
    assert executor.calls == [("click", 108, 137)]


@pytest.mark.parametrize("point", [(-1, 5), (984, 5), (5, 605)])
def test_never_clicks_outside_the_page_area(point):
    env, executor = make()
    with pytest.raises(ValueError):
        env.click(*point)
    assert executor.calls == []


def test_wrong_window_means_no_picture():
    def wrong():
        raise StopRequested("wrong window")

    env, _ = make(require_window=wrong)
    with pytest.raises(StopRequested):
        env.capture()


def test_stop_works_while_waiting():
    guard = SafetyGuard()
    env, _ = make(guard)
    guard.stop("Esc key pressed")
    with pytest.raises(StopRequested):
        env.wait(1)
