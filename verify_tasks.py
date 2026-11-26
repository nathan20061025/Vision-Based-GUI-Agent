"""Check that every task and failure switch behaves as intended.

Uses a HIDDEN browser and Playwright. It does not control your mouse or
capture your screen. It tests the practice sites and checks, NOT an agent.

For each task:
  start       the success check must be False before doing anything
  normal      following the answer key must make it True
  broken      the same steps must leave it False
  distractor  the same steps must leave it False, and show the banner
              (distractor and popup are checked for both design variants)
  slow        False straight after the steps, True after waiting
  popup       the pop-up blocks the page; after closing it, the task works

    python verify_tasks.py
"""

import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from evaluation.checker import task_succeeded
from evaluation.tasks import VARIANTS, load_tasks, task_url


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


def designs_are_separate(designs) -> list[str]:
    """No pop-up or banner text or style may appear in two designs."""
    problems = []
    for column, what in ((3, "text"), (4, "style")):
        owners = {}
        for item in designs:
            owners.setdefault((item[1], item[column]), set()).add((item[0], item[2]))
        problems += [f"{kind} {what} shared by {sorted(who)}"
                     for (kind, _), who in owners.items() if len(who) > 1]
    # 3 splits x 2 kinds x 2 variants
    if len({item[:3] for item in designs}) != 12:
        problems.append("not all 12 pop-up and banner designs were seen")
    return problems


def verify(page, task, designs: set) -> dict:
    results = {}

    page.goto(task_url(task))
    results["start"] = not task_succeeded(page, task)
    do_steps(page, task.answer_key)
    results["normal"] = task_succeeded(page, task)

    page.goto(task_url(task, "broken"))
    do_steps(page, task.answer_key)
    page.wait_for_timeout(300)
    results["broken"] = not task_succeeded(page, task)

    page.goto(task_url(task, "slow"))
    do_steps(page, task.answer_key)
    early = task_succeeded(page, task)
    page.wait_for_timeout(3600)
    results["slow"] = not early and task_succeeded(page, task)

    for variant in VARIANTS:
        page.goto(task_url(task, "distractor", variant=variant))
        do_steps(page, task.answer_key)
        page.wait_for_timeout(300)
        banner = page.locator("#distractor")
        results[f"distractor{variant}"] = (not task_succeeded(page, task)
                                           and banner.is_visible())
        if banner.count():
            designs.add((task.split, "banner", variant, banner.inner_text(),
                         banner.get_attribute("style")))

        url = task_url(task, "popup", variant=variant)
        page.goto(url)
        designs.add((task.split, "popup", variant,
                     page.locator("#fault-popup").inner_text(),
                     page.locator("#fault-popup > div").get_attribute("style")))
        try:
            do_steps(page, task.answer_key[:1], timeout=700)
            # select_option does not click, so confirm with a real click test.
            page.locator(task.answer_key[0]["selector"]).click(timeout=700, trial=True)
            blocked = False
        except PlaywrightTimeout:
            blocked = True
        page.goto(url)
        page.click("#fault-popup-close")
        do_steps(page, task.answer_key)
        results[f"popup{variant}"] = blocked and task_succeeded(page, task)

    return results


def main() -> int:
    tasks = load_tasks()
    failures = 0
    designs = set()  # (split, kind, variant, text, style) seen
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for task in tasks:
            # A fresh page per task, with the same size every time.
            page = browser.new_page(viewport={"width": 1000, "height": 700})
            try:
                results = verify(page, task, designs)
                bad = [name for name, ok in results.items() if not ok]
            except Exception as error:  # report it and check the other tasks
                bad = [f"{type(error).__name__}: {str(error).splitlines()[0]}"]
            page.close()
            failures += bool(bad)
            status = "PASS" if not bad else "FAIL " + ", ".join(bad)
            print(f"{task.split:10} {task.id:24} {status}")
        browser.close()
    print(f"\n{len(tasks) - failures} of {len(tasks)} tasks passed")

    problems = designs_are_separate(designs)
    print("Failure designs differ between splits and variants: "
          + ("FAIL" if problems else "PASS"))
    for problem in problems:
        print("  " + problem)
    return 1 if failures or problems else 0


if __name__ == "__main__":
    sys.exit(main())
