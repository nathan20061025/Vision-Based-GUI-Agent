import pytest

from agent.safety import SafetyGuard, StopRequested, in_corner


@pytest.mark.parametrize("point", [(0, 0), (1919, 0), (0, 1079), (1919, 1079)])
def test_all_four_corners(point):
    assert in_corner(*point, 1920, 1080)


@pytest.mark.parametrize("point", [(960, 540), (0, 540), (960, 0)])
def test_centre_and_edges_are_not_corners(point):
    assert not in_corner(*point, 1920, 1080)


def test_stop_is_kept_with_first_reason():
    guard = SafetyGuard()
    guard.check()
    guard.stop("first")
    guard.stop("second")
    for _ in range(2):
        with pytest.raises(StopRequested, match="first"):
            guard.check()


def test_action_limit():
    guard = SafetyGuard(max_actions=2)
    guard.before_action()
    guard.before_action()
    with pytest.raises(StopRequested, match="limit"):
        guard.before_action()
    assert guard.actions == 2


def test_stopped_guard_blocks_actions():
    guard = SafetyGuard()
    guard.stop("test")
    with pytest.raises(StopRequested):
        guard.before_action()
    assert guard.actions == 0


def test_corner_stays_stopped_after_mouse_leaves():
    position = [(0, 0)]
    guard = SafetyGuard(mouse_position=lambda: position[0], screen_size=(100, 100))
    with pytest.raises(StopRequested, match="corner"):
        guard.check()
    position[0] = (50, 50)
    with pytest.raises(StopRequested):
        guard.check()
