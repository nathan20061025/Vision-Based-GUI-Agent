import json

import pytest

from agent.logger import RunLogger
from agent.safety import StopRequested
from tests.test_executor import make


def records(logger):
    return [json.loads(line)
            for line in logger.path.read_text(encoding="utf-8").splitlines()]


def logged_executor(tmp_path):
    executor, backend = make()
    executor.logger = RunLogger(tmp_path)
    return executor, backend


def test_each_record_has_time_event_and_details(tmp_path):
    logger = RunLogger(tmp_path)
    logger.log("check", name="log in", passed=True)
    [record] = records(logger)
    assert record["event"] == "check"
    assert record["passed"] is True
    assert "time" in record


def test_actions_are_logged_with_position_and_duration(tmp_path):
    executor, _ = logged_executor(tmp_path)
    executor.click(10, 20)
    [record] = records(executor.logger)
    assert (record["action"], record["x"], record["y"]) == ("click", 10, 20)
    assert record["status"] == "done"
    assert record["seconds"] >= 0


def test_typed_text_is_never_saved(tmp_path):
    executor, _ = logged_executor(tmp_path)
    executor.type_text("Secret-9x!")
    saved = executor.logger.path.read_text(encoding="utf-8")
    assert "Secret-9x!" not in saved
    assert records(executor.logger)[0]["characters"] == 10


def test_stopped_action_is_logged_as_stopped(tmp_path):
    executor, _ = logged_executor(tmp_path)
    executor.guard.stop("Esc key pressed")
    with pytest.raises(StopRequested):
        executor.press("tab")
    assert records(executor.logger)[0]["status"] == "stopped"


def test_error_message_is_not_saved(tmp_path):
    executor, backend = logged_executor(tmp_path)

    def broken(text):
        raise RuntimeError(f"could not type {text}")

    backend.write = broken
    with pytest.raises(RuntimeError):
        executor.type_text("Z")
    [record] = records(executor.logger)
    assert record["status"] == "error: RuntimeError"
    assert "could not type" not in json.dumps(record)
