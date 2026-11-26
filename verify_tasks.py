"""Check that every task and failure switch behaves as intended.

Uses a HIDDEN browser and Playwright. It does not control your mouse or
capture your screen. It tests the practice sites and checks, NOT an agent.

For each task:
  start       the success check must be False before doing anything
  normal      following the answer key must make it True
  broken      the same steps must leave it False
  distractor  the same steps must leave it False, and show the banner
  slow        False straight after the steps, True after waiting
  popup       the pop-up blocks the page; after closing it, the task works

    python verify_tasks.py
"""

import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from evaluation.checker import task_succeeded
from evaluation.tasks import load_tasks, task_url


def do_steps(page, steps, timeout=2000) -> None:
    for step in steps:
        target = page.locator(step["selector"])
        if step["action"] == "fill":
            target.click(timeout=timeout)  # fails if something covers it
            target.fill(step["value"], timeout=timeout)
        elif step["action"] == "select":
            target.select_option(step["value"], timeout=timeout)
        else:
            target.click(timeout=timeout)


def verify(page, task) -> dict:
    results = {}

    page.goto(task_url(task))
    results["start"] = not task_succeeded(page, task)
    do_steps(page, task.answer_key)
    results["normal"] = task_succeeded(page, task)

    page.goto(task_url(task, "broken"))
    do_steps(page, task.answer_key)
    page.wait_for_timeout(300)
    results["broken"] = not task_succeeded(page, task)

    page.goto(task_url(task, "distractor"))
    do_steps(page, task.answer_key)
    page.wait_for_timeout(300)
    results["distractor"] = (not task_succeeded(page, task)
                             and page.locator("#distractor").is_visible())

    page.goto(task_url(task, "slow"))
    do_steps(page, task.answer_key)
    early = task_succeeded(page, task)
    page.wait_for_timeout(3600)
    results["slow"] = not early and task_succeeded(page, task)

    page.goto(task_url(task, "popup"))
    try:
        do_steps(page, task.answer_key[:1], timeout=700)
        # select_option does not click, so confirm with a real click test.
        page.locator(task.answer_key[0]["selector"]).click(timeout=700, trial=True)
        blocked = False
    except PlaywrightTimeout:
        blocked = True
    page.goto(task_url(task, "popup"))
    page.click("#fault-popup-close")
    do_steps(page, task.answer_key)
    results["popup"] = blocked and task_succeeded(page, task)

    return results


def main() -> int:
    tasks = load_tasks()
    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for task in tasks:
            # A fresh page per task, with the same size every time.
            page = browser.new_page(viewport={"width": 1000, "height": 700})
            try:
                results = verify(page, task)
                bad = [name for name, ok in results.items() if not ok]
            except Exception as error:  # report it and check the other tasks
                bad = [f"{type(error).__name__}: {str(error).splitlines()[0]}"]
            page.close()
            failures += bool(bad)
            status = "PASS" if not bad else "FAIL " + ", ".join(bad)
            print(f"{task.split:10} {task.id:24} {status}")
        browser.close()
    print(f"\n{len(tasks) - failures} of {len(tasks)} tasks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
