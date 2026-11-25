import pytest

from agent.executor import Executor
from agent.safety import SafetyGuard, StopRequested


class FakeBackend:
    """Records calls instead of touching the real mouse and keyboard."""

    def __init__(self):
        self.calls = []

    def moveTo(self, x, y, duration=0):
        self.calls.append(("move", x, y))

    def click(self):
        self.calls.append(("click",))

    def write(self, text):
        self.calls.append(("write", text))

    def press(self, key):
        self.calls.append(("press", key))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))


def make(guard=None, require_window=lambda: None):
    backend = FakeBackend()
    executor = Executor(guard or SafetyGuard(), require_window, backend,
                        type_delay=0, caps_lock_on=lambda: False)
    return executor, backend


def test_actions_reach_the_backend_in_order():
    executor, backend = make()
    executor.click(10, 20)
    executor.type_text("ab")
    executor.press("tab")
    executor.scroll(5, 6, -300)
    assert backend.calls == [
        ("move", 10, 20), ("click",), ("write", "a"), ("write", "b"),
        ("press", "tab"), ("move", 5, 6), ("scroll", -300)]
    assert executor.guard.actions == 4


def test_nothing_happens_after_stop():
    executor, backend = make()
    executor.guard.stop("test")
    for action in (lambda: executor.click(1, 1),
                   lambda: executor.type_text("a"),
                   lambda: executor.press("tab"),
                   lambda: executor.scroll(1, 1, -1)):
        with pytest.raises(StopRequested):
            action()
    assert backend.calls == []


def test_stop_during_typing_stops_the_next_character():
    executor, backend = make()

    def write_then_stop(char):
        backend.calls.append(("write", char))
        executor.guard.stop("during typing")

    backend.write = write_then_stop
    with pytest.raises(StopRequested):
        executor.type_text("abc")
    assert backend.calls == [("write", "a")]


def test_wrong_window_after_moving_blocks_the_click():
    def require_window():
        if backend.calls:  # window changes while the mouse is moving
            raise StopRequested("wrong window")

    executor, backend = make(require_window=require_window)
    with pytest.raises(StopRequested):
        executor.click(1, 1)
    assert backend.calls == [("move", 1, 1)]


@pytest.mark.parametrize("key", ["esc", "escape", "win", "alt", "f4"])
def test_unlisted_keys_are_rejected(key):
    executor, backend = make()
    with pytest.raises(ValueError):
        executor.press(key)
    assert backend.calls == []


@pytest.mark.parametrize("text", ["café", "line\nbreak"])
def test_unsupported_text_types_nothing(text):
    executor, backend = make()
    with pytest.raises(ValueError):
        executor.type_text(text)
    assert backend.calls == []


def test_action_limit_applies():
    executor, backend = make(SafetyGuard(max_actions=1))
    executor.press("tab")
    with pytest.raises(StopRequested):
        executor.press("tab")
    assert backend.calls == [("press", "tab")]


def test_caps_lock_blocks_typing():
    executor, backend = make()
    executor.caps_lock_on = lambda: True
    with pytest.raises(StopRequested, match="Caps Lock"):
        executor.type_text("abc")
    assert backend.calls == []
