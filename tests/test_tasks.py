import ast
import json

import pytest

from evaluation.tasks import (ROOT, check_task, load_sites, load_tasks,
                              task_url)


def sample() -> dict:
    path = ROOT / "tasks" / "login_valid.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_task_files_load():
    assert len(load_tasks()) >= 10


def test_every_site_has_a_task_and_every_split_is_used():
    tasks = load_tasks()
    assert {t.site for t in tasks} == set(load_sites())
    assert {t.split for t in tasks} == {"train", "validation", "test"}


def test_split_filter():
    assert {t.split for t in load_tasks(split="test")} == {"test"}


def test_task_cannot_move_its_site_to_another_split():
    data = sample() | {"split": "test"}
    with pytest.raises(ValueError, match="split"):
        check_task(data, load_sites())


@pytest.mark.parametrize("change", [
    {"site": "nowhere"}, {"success": []}, {"step_limit": 1}, {"extra": 1}])
def test_invalid_tasks_are_rejected(change):
    with pytest.raises(ValueError):
        check_task(sample() | change, load_sites())


def test_unknown_fault_is_rejected():
    with pytest.raises(ValueError):
        task_url(load_tasks()[0], "typo")


def test_instructions_do_not_contain_page_selectors():
    for task in load_tasks():
        for step in task.answer_key:
            assert step["selector"] not in task.instruction


def test_agent_never_imports_the_examiner_code():
    for path in (ROOT / "agent").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(n.split(".")[0] == "evaluation" for n in names), path
