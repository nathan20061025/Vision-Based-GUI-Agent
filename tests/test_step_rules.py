import pytest

from evaluation.step_rules import step_effect, step_succeeded
from evaluation.tasks import load_tasks

TASKS = {task.id: task for task in load_tasks()}


def test_every_step_of_every_task_has_a_rule():
    for task in TASKS.values():
        for index in range(len(task.answer_key)):
            assert step_effect(task, index), (task.id, index)


def test_input_actions_are_judged_on_their_own_target():
    task = TASKS["settings_dark_name"]
    assert step_effect(task, 0) == [
        {"selector": "#theme", "check": "value", "expected": "Dark"}]
    assert step_effect(task, 2) == [
        {"selector": "#status", "check": "text", "expected": "Settings saved"}]


def test_checkbox_rule():
    assert step_effect(TASKS["settings_notifications"], 0) == [
        {"selector": "#notify", "check": "checked", "expected": True}]


def test_two_buttons_have_separate_outcomes():
    task = TASKS["shop_order_pens"]
    assert step_effect(task, 0) != step_effect(task, 1)


class FakeElement:
    def __init__(self, ticked=None, text=None):
        self.ticked, self.text = ticked, text

    def count(self):
        return 0 if self.ticked is None and self.text is None else 1

    def is_checked(self):
        return self.ticked

    def inner_text(self):
        return self.text


class FakePage:
    def __init__(self, **elements):
        self.elements = elements

    def locator(self, selector):
        return self.elements.get(selector.lstrip("#"), FakeElement())


def test_earlier_success_is_kept_when_a_later_action_fails():
    """The box is ticked but saving failed."""
    task = TASKS["settings_notifications"]
    page = FakePage(notify=FakeElement(ticked=True), status=FakeElement(text=""))
    assert step_succeeded(page, task, 0)
    assert not step_succeeded(page, task, 1)


@pytest.mark.parametrize("ticked", [False, None])
def test_unticked_or_missing_box_is_a_failure(ticked):
    page = FakePage(notify=FakeElement(ticked=ticked))
    assert not step_succeeded(page, TASKS["settings_notifications"], 0)
