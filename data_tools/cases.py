"""Run one action in one "case" (working, or failing in some way).

Actions use Playwright's mouse and keyboard by POSITION, so a click can miss
or land on a pop-up, as a real one would. Your real mouse is not used.
The label always comes from what is actually on the page afterwards.
"""

import copy
import dataclasses

from evaluation.step_rules import step_succeeded
from evaluation.tasks import VARIANTS, task_url

# The label we EXPECT for each case. It is never used as the label; a
# difference is reported so that the collector or page can be investigated.
EXPECTED = {
    "normal": True, "slow_late": True, "slow_early": False, "broken": False,
    "distractor1": False, "distractor2": False, "popup1": False,
    "popup2": False, "miss": False, "wrong_target": False,
    "wrong_text": False, "wrong_option": False,
}
PAGE_FAULTS = {"broken", "slow", "distractor"}  # only affect button clicks
SETTLE_MS = 300
SLOW_EXTRA_MS = 3300

TEXT_BOXES = ("input:not([type=checkbox]):not([type=radio]):not([type=hidden]), "
              "textarea")
# Free text that can be changed to add variety without changing the task.
FREE_TEXT = {
    "Buy milk": ["Buy milk", "Call the bank", "Return library books"],
    "Sam Tester": ["Sam Tester", "Alex Sample", "Jo"],
    "Too slow": ["Too slow", "The buttons are hard to find", "Fine"],
    "Test Person": ["Test Person", "Pat Example", "Lee"],
    "test@example.com": ["test@example.com", "pat@example.org", "lee@example.net"],
}


def vary_text(task, number: int):
    """A copy of the task with different free text, changed consistently."""
    def swap(value):
        options = FREE_TEXT.get(value) if isinstance(value, str) else None
        return options[number % len(options)] if options else value

    success = copy.deepcopy(task.success)
    answer = copy.deepcopy(task.answer_key)
    for rule in success:
        rule["expected"] = swap(rule["expected"])
    for step in answer:
        if "value" in step:
            step["value"] = swap(step["value"])
        for rule in step.get("expect", []):
            rule["expected"] = swap(rule["expected"])
    return dataclasses.replace(task, success=success, answer_key=answer)


def cases_for(step) -> list[str]:
    cases = ["normal", "popup1", "popup2", "miss"]
    if step["action"] == "click":
        cases += ["broken", "distractor1", "distractor2", "slow"]
    if step["action"] == "fill":
        cases += ["wrong_target", "wrong_text"]
    if step["action"] == "select":
        cases += ["wrong_option"]
    if step["action"] == "check" and step["selector"].startswith("#rating-"):
        cases += ["wrong_target"]
    return cases


def centre(page, locator):
    box = locator.bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, box


def other_target(page, step):
    """Another element of the same kind, or None."""
    if step["action"] == "check":
        candidates = page.locator("input[type=radio]")
    else:
        candidates = page.locator(TEXT_BOXES)
    target = page.locator(step["selector"]).element_handle()
    for i in range(candidates.count()):
        item = candidates.nth(i)
        if item.is_visible() and not item.evaluate("(a, b) => a === b", target):
            return item
    return None


def do_step(page, step) -> None:
    """The normal, working version of a step (used to reach later steps)."""
    target = page.locator(step["selector"])
    if step["action"] == "select":
        target.select_option(step["value"])
        return
    x, y, _ = centre(page, target)
    page.mouse.click(x, y)
    if step["action"] == "fill":
        page.keyboard.type(step["value"])


def perform(page, step, case: str) -> dict | None:
    """Do the action for a case. Returns what was done, or None if impossible."""
    target = page.locator(step["selector"])
    x, y, box = centre(page, target)
    done = {"action": step["action"], "intended_point": [round(x), round(y)]}

    if case == "wrong_target":
        other = other_target(page, step)
        if other is None:
            return None
        x, y, _ = centre(page, other)
    elif case == "miss":
        size = page.viewport_size or page.evaluate(
            "({width: innerWidth, height: innerHeight})")
        y = min(y + box["height"] / 2 + 45, size["height"] - 2)

    if step["action"] == "select":
        if case == "wrong_option":
            options = target.locator("option").all_inner_texts()
            current = target.input_value()
            wrong = [o for o in options if o not in (step["value"], current)]
            if not wrong:
                return None
            target.select_option(wrong[0])
        elif case in ("miss", "popup1", "popup2"):
            page.mouse.click(x, y)  # the list is never opened or changed
        else:
            target.select_option(step["value"])
    else:
        page.mouse.click(x, y)
        if step["action"] == "fill":
            text = step["value"]
            if case == "wrong_text":
                text = "qwerty" if text != "qwerty" else "asdfgh"
            # Just type, like agent/executor.py. (No Ctrl+A: after a miss it
            # highlighted the whole page, which a verifier could learn.)
            page.keyboard.type(text)

    done["actual_point"] = [round(x), round(y)]
    return done


def run_case(page, task, index: int, case: str, shoot, style=None):
    """Load the page, reach step `index`, then run it as `case`.

    shoot() takes a picture. style(page) can change the page's look.
    Returns a list of examples (two for "slow": too early and after waiting).
    """
    step = task.answer_key[index]
    fault, variant = case, 1
    if case[-1] in "12":
        fault, variant = case[:-1], int(case[-1])
    assert variant in VARIANTS

    url = task_url(task, fault if fault in PAGE_FAULTS else None, variant=variant)
    if fault == "popup":  # load normally, but remember which design to show
        url = task_url(task) + f"?variant={variant}"
    page.goto(url)
    page.wait_for_timeout(SETTLE_MS)
    if style:
        style(page)
    for earlier in task.answer_key[:index]:
        do_step(page, earlier)
    page.locator(step["selector"]).scroll_into_view_if_needed()
    if fault == "popup":
        page.evaluate("window.showFaultPopup()")
    page.wait_for_timeout(SETTLE_MS)

    if step_succeeded(page, task, index):
        return []  # already true before the action: the label would be unclear
    before = shoot()
    done = perform(page, step, case)
    if done is None:
        return []
    page.wait_for_timeout(SETTLE_MS)

    def example(name):
        after = shoot()
        return {"case": name, "before": before, "after": after,
                "success": step_succeeded(page, task, index), **done}

    if case != "slow":
        return [example(case)]
    early = example("slow_early")
    page.wait_for_timeout(SLOW_EXTRA_MS)
    return [early, example("slow_late")]
