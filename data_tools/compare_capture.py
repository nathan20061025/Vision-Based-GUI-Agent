"""Do hidden-browser page pictures behave like REAL screen pictures?

    python -m data_tools.compare_capture             real screen (YOU run this)
    python -m data_tools.compare_capture --dry-run   tests the code only

For each validation example, in one visible browser, it takes BOTH a page
screenshot and a real screen picture of the same page area, then compares
the pixel rule on each.

It captures ONLY the browser's page area. Playwright does the actions, so
your real mouse is not used. Keep the practice browser in front, and keep
your own mouse OUT of the browser window. Press Esc to stop.
Pictures stay in memory and are not saved; only numbers are saved.

Pass rule, fixed before running: both methods give the same answer for at
least 95% of examples AND the median difference in changed share is no more
than 0.2 percentage points.
"""

import argparse
import io
import json
import statistics
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

from agent.coordinates import page_to_screen
from agent.pixel_rule import changed_share, load_settings
from agent.safety import SafetyGuard, StopRequested, start_stop_key
from data_tools.cases import run_case
from evaluation.tasks import ROOT, load_tasks

MIN_AGREEMENT, MAX_MEDIAN_DIFFERENCE = 0.95, 0.002
CASES = ["normal", "miss", "popup1", "broken", "distractor1", "wrong_text"]
TASK_IDS = ["settings_notifications", "todo_add", "feedback_comment"]
OUTPUT = ROOT / "results" / "pixel_rule_v1" / "capture_comparison.json"


def summarise(rows: list) -> dict:
    agreement = sum(r["page_says"] == r["screen_says"] for r in rows) / len(rows)
    median = statistics.median(
        abs(r["page_share"] - r["screen_share"]) for r in rows)
    return {
        "examples": len(rows), "agreement": agreement,
        "median_difference": median,
        "page_correct": sum(r["page_says"] == r["label"] for r in rows),
        "screen_correct": sum(r["screen_says"] == r["label"] for r in rows),
        "passed": agreement >= MIN_AGREEMENT and median <= MAX_MEDIAN_DIFFERENCE,
    }


def open_png(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def main(dry_run: bool) -> int:
    tolerance, threshold = load_settings()
    tasks = {t.id: t for t in load_tasks(split="validation")}
    rows = []
    guard = SafetyGuard()
    listener = None if dry_run else start_stop_key(guard)

    if not dry_run:
        import mss

        from milestone2_positions import (active_window_title, read_window,
                                          wait_for_practice_window)

    try:
        with sync_playwright() as p:
            if dry_run:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1000, "height": 700})
            else:
                browser = p.chromium.launch(
                    headless=False, args=["--window-position=0,0",
                                          "--window-size=1000,700"])
                page = browser.new_context(no_viewport=True).new_page()
                # The title check expects the login page first.
                page.goto((ROOT / "practice_sites" / "login" / "index.html").as_uri())
                page.bring_to_front()
                page.wait_for_timeout(2000)
                wait_for_practice_window(page, guard)

            def shoot():
                guard.check()
                png = page.screenshot()
                if dry_run:  # stands in for the screen: tests the code only
                    return open_png(png), open_png(png)
                if not active_window_title().startswith("Practice "):
                    raise StopRequested("the practice browser is not active")
                window = read_window(page)
                left, top = page_to_screen(0, 0, window)
                region = {"left": left, "top": top,
                          "width": int(window.inner_width * window.scale),
                          "height": int(window.inner_height * window.scale)}
                with mss.MSS() as screen:
                    shot = screen.grab(region)
                return (open_png(png),
                        Image.frombytes("RGB", shot.size, shot.rgb))

            for task_id in TASK_IDS:
                task = tasks[task_id]
                for index, step in enumerate(task.answer_key):
                    for case in CASES:
                        button_only = case in ("broken", "distractor1")
                        if button_only and step["action"] != "click":
                            continue
                        if case == "wrong_text" and step["action"] != "fill":
                            continue
                        for item in run_case(page, task, index, case, shoot):
                            shares = [changed_share(b, a, tolerance) for b, a in
                                      zip(item["before"], item["after"])]
                            rows.append({
                                "task": task_id, "step": index, "case": case,
                                "label": item["success"],
                                "page_share": shares[0], "screen_share": shares[1],
                                "page_says": shares[0] >= threshold,
                                "screen_says": shares[1] >= threshold})
                            print(f"{task_id:24} step {index} {case:12} "
                                  f"page {shares[0]:7.3%}  screen {shares[1]:7.3%}")
            browser.close()
    except StopRequested as stop:
        print(f"STOPPED: {stop}")
        return 1
    finally:
        if listener:
            listener.stop()

    result = summarise(rows)
    print(json.dumps(result, indent=2))
    if dry_run:
        print("DRY RUN: code check only. This says nothing about real screens.")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(
            {"settings": [tolerance, threshold], "summary": result, "rows": rows},
            indent=2) + "\n", encoding="utf-8")
        print(f"Saved {OUTPUT}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="hidden browser; tests the code only")
    sys.exit(main(parser.parse_args().dry_run))
