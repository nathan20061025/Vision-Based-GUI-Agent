"""What does success mean for ONE action? (Examiner side only.)

Label rule: is the intended effect of this action there afterwards?
A whole task can fail while earlier actions succeeded, so each action is
judged on its own.

  fill    the intended text is in the intended box
  check   the intended checkbox or radio button is ticked
  select  the intended option is selected
  click   (a button) the outcome it should cause has appeared
"""

from evaluation.checker import check_one


def step_effect(task, index: int) -> list:
    """The rules that must ALL hold for step `index` to count as success."""
    step = task.answer_key[index]
    selector = step["selector"]
    if step["action"] in ("fill", "select"):
        return [{"selector": selector, "check": "value", "expected": step["value"]}]
    if step["action"] == "check":
        return [{"selector": selector, "check": "checked", "expected": True}]
    if "expect" in step:
        return step["expect"]

    # One button only: its outcome is every task rule not caused by an input.
    buttons = [s for s in task.answer_key if s["action"] == "click"]
    if len(buttons) != 1:
        raise ValueError(f"task {task.id}: each button click needs 'expect'")
    inputs = {s["selector"] for s in task.answer_key if s["action"] != "click"}
    rules = [rule for rule in task.success if rule["selector"] not in inputs]
    if not rules:
        raise ValueError(f"task {task.id}: no outcome rule for the button")
    return rules


def step_succeeded(page, task, index: int) -> bool:
    return all(check_one(page, rule) for rule in step_effect(task, index))
