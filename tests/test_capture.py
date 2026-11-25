import pytest
from PIL import Image

from agent.capture import ActionCapture, run_folder
from agent.safety import StopRequested


def fake_screen(colour="white"):
    return Image.new("RGB", (20, 10), colour)


def test_order_is_before_action_wait_after(tmp_path):
    events = []

    def grab():
        events.append("grab")
        return fake_screen()

    capture = ActionCapture(tmp_path, lambda: None,
                            lambda: events.append("wait"), grab)
    capture.around("click", lambda: events.append("action"))
    assert events == ["grab", "action", "wait", "grab"]


def test_files_are_numbered_and_not_overwritten(tmp_path):
    capture = ActionCapture(tmp_path, lambda: None, lambda: None, fake_screen)
    capture.around("click", lambda: None)
    capture.around("click", lambda: None)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "01_click_after.png", "01_click_before.png",
        "02_click_after.png", "02_click_before.png"]


def test_before_and_after_show_the_change(tmp_path):
    colour = ["white"]
    capture = ActionCapture(tmp_path, lambda: None, lambda: None,
                            lambda: fake_screen(colour[0]))
    before, after = capture.around("click", lambda: colour.__setitem__(0, "black"))
    assert before.getpixel((0, 0)) == (255, 255, 255)
    assert after.getpixel((0, 0)) == (0, 0, 0)


def test_wrong_window_means_no_picture_and_no_action(tmp_path):
    done = []

    def wrong_window():
        raise StopRequested("wrong window")

    capture = ActionCapture(tmp_path, wrong_window, lambda: None, fake_screen)
    with pytest.raises(StopRequested):
        capture.around("click", lambda: done.append(True))
    assert done == []
    assert list(tmp_path.iterdir()) == []


def test_stopped_action_takes_no_after_picture(tmp_path):
    def stopped():
        raise StopRequested("Esc")

    capture = ActionCapture(tmp_path, lambda: None, lambda: None, fake_screen)
    with pytest.raises(StopRequested):
        capture.around("type", stopped)
    assert [p.name for p in tmp_path.iterdir()] == ["01_type_before.png"]


def test_run_folder_is_deleted_by_default(tmp_path):
    with run_folder(tmp_path) as folder:
        (folder / "picture.png").write_bytes(b"x")
    assert not folder.exists()


def test_run_folder_is_deleted_after_a_stop(tmp_path):
    with pytest.raises(StopRequested):
        with run_folder(tmp_path) as folder:
            (folder / "picture.png").write_bytes(b"x")
            raise StopRequested("Esc")
    assert not folder.exists()


def test_run_folder_can_be_kept(tmp_path):
    with run_folder(tmp_path, keep=True) as folder:
        (folder / "picture.png").write_bytes(b"x")
    assert (folder / "picture.png").exists()


def test_older_runs_are_not_deleted(tmp_path):
    (tmp_path / "old_run").mkdir()
    with run_folder(tmp_path):
        pass
    assert [p.name for p in tmp_path.iterdir()] == ["old_run"]
