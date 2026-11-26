"""Run the basic agent on practice tasks and score it.

HIDDEN browser (your mouse is not used):
    python run_agent.py                         all train + validation tasks
    python run_agent.py --split train
    python run_agent.py --task search_git
    python run_agent.py --verifier none         no checking, no retries

REAL screen and REAL mouse and keyboard (Esc or a screen corner stops it):
    python run_agent.py --real --task search_git
    python run_agent.py --real --task search_git --ask   you type the task

The test split is refused: it is kept for the final experiments.
The AGENT only gets pictures and the instruction. This script (the
examiner) reads the page code afterwards to score what really happened.
Playwright opens the pages and, in real mode, says where the page area is.
"""

import argparse
import json
import statistics
import sys
from datetime import datetime

from playwright.sync_api import sync_playwright

from agent import loop
from agent.environments import HiddenEnv, ScreenEnv
from agent.logger import RunLogger
from agent.ocr import OcrReader
from agent.pixel_rule import changed_share, load_settings
from agent.planner import UnsupportedInstruction, plan
from agent.safety import SafetyGuard, StopRequested
from evaluation.checker import task_succeeded
from evaluation.step_rules import step_succeeded
from evaluation.tasks import FAULTS, ROOT, load_tasks, task_url

RESULTS = ROOT / "results" / "agent_m5"
ALLOWED_SPLITS = ("train", "validation")


def allowed_tasks(split=None, task_id=None) -> list:
    tasks = [t for s in ALLOWED_SPLITS for t in load_tasks(split=s)
             if split in (None, s)]
    if task_id:
        tasks = [t for t in tasks if t.id == task_id]
        if not tasks:
            raise SystemExit(f"{task_id!r} is not a train or validation task "
                             "(the test split is not allowed)")
    return tasks


def make_verifier(name: str):
    if name == "none":
        return None
    tolerance, threshold = load_settings()
    return lambda before, after: changed_share(before, after, tolerance) >= threshold


def same_plan(instruction: str, task) -> bool:
    """Can plan step N be scored with the task's step N?"""
    try:
        steps = plan(instruction)
    except UnsupportedInstruction:
        return False
    return [s.action for s in steps] == [a["action"] for a in task.answer_key]


def score(task, result, truly: bool) -> dict:
    return {"task": task.id, "split": task.split, "really_succeeded": truly,
            "agent_claimed_success": result.status == "claimed_success",
            "false_claim": result.status == "claimed_success" and not truly,
            **result.as_dict()}


def summarise(rows: list) -> dict:
    times = [s for r in rows for s in r["ocr_seconds"]]
    attempts = [a for r in rows for a in r["attempts"] if "truly" in a]
    return {
        "tasks": len(rows),
        "really_succeeded": sum(r["really_succeeded"] for r in rows),
        "claimed_success": sum(r["agent_claimed_success"] for r in rows),
        "false_task_claims": sum(r["false_claim"] for r in rows),
        "attempts_scored": len(attempts),
        "attempts_wrongly_called_success": sum(
            a["claimed"] and not a["truly"] for a in attempts),
        "attempts_wrongly_called_failure": sum(
            a["truly"] and not a["claimed"] for a in attempts),
        "median_ocr_seconds": round(statistics.median(times), 2) if times else None,
        "by_split": {s: f"{sum(r['really_succeeded'] for r in rows if r['split'] == s)}"
                        f"/{sum(r['split'] == s for r in rows)}"
                     for s in sorted({r["split"] for r in rows})},
    }


def run_hidden(tasks, reader, verifier_name, fault) -> list:
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for task in tasks:
            page = browser.new_page(viewport={"width": 1000, "height": 700})
            page.goto(task_url(task, fault))
            page.wait_for_timeout(800)
            scorable = same_plan(task.instruction, task)

            def observer(index, claimed, page=page, task=task):
                return step_succeeded(page, task, index)

            result = loop.run(task.instruction, HiddenEnv(page), reader,
                              make_verifier(verifier_name), SafetyGuard(),
                              max_actions=task.step_limit,
                              logger=RunLogger(ROOT / "runs" / "logs"),
                              observer=observer if scorable else None)
            row = score(task, result, task_succeeded(page, task))
            rows.append(row)
            print(f"{task.split:10} {task.id:24} "
                  f"really: {'YES' if row['really_succeeded'] else 'no ':3}  "
                  f"agent: {result.status:15} {result.reason}", flush=True)
            page.close()
        browser.close()
    return rows


def run_real(task, reader, verifier_name, ask: bool) -> dict | None:
    import pyautogui

    from agent.executor import Executor
    from agent.safety import start_stop_key
    from milestone2_positions import (active_window_title, read_window,
                                      wait_for_practice_window)

    instruction = task.instruction
    if ask:
        print(f"Example for this page: {task.instruction}")
        instruction = input("Type your instruction: ").strip()
    try:
        plan(instruction)  # reject before opening or touching anything
    except UnsupportedInstruction as error:
        print(error)
        return None

    guard = SafetyGuard(max_actions=40, mouse_position=pyautogui.position,
                        screen_size=pyautogui.size())
    listener = start_stop_key(guard)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, args=["--window-position=0,0",
                                      "--window-size=1000,700"])
            page = browser.new_context(no_viewport=True).new_page()
            page.goto(task_url(task))
            page.bring_to_front()
            page.wait_for_timeout(2000)
            title = page.title()  # used only to check the right window is active

            def require_window():
                if title not in active_window_title():
                    raise StopRequested("the practice browser is not active")

            # wait_for_practice_window() expects the login title, so wait here.
            print("If needed, click a blank part of the practice browser.")
            for _ in range(100):
                guard.check()
                if title in active_window_title():
                    break
                page.wait_for_timeout(100)
            require_window()

            executor = Executor(guard, require_window,
                                logger=(logger := RunLogger(ROOT / "runs" / "logs")))
            env = ScreenEnv(lambda: read_window(page), executor, guard,
                            require_window,
                            wait=lambda s: page.wait_for_timeout(s * 1000))
            scorable = instruction == task.instruction

            def observer(index, claimed):
                return step_succeeded(page, task, index)

            result = loop.run(instruction, env, reader,
                              make_verifier(verifier_name), guard,
                              max_actions=task.step_limit, logger=logger,
                              observer=observer if scorable else None)
            row = None
            print(f"Agent says: {result.status} {result.reason}")
            if scorable:
                row = score(task, result, task_succeeded(page, task))
                print(f"Examiner says the task really succeeded: "
                      f"{'YES' if row['really_succeeded'] else 'NO'}")
            else:
                print("Your own instruction: check the result on screen yourself.")
            page.wait_for_timeout(3000)
            browser.close()
            return row
    except (StopRequested, pyautogui.FailSafeException) as stop:
        print(f"STOPPED: {stop}")
        return None
    finally:
        listener.stop()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=ALLOWED_SPLITS)
    parser.add_argument("--task")
    parser.add_argument("--verifier", choices=["pixel", "none"], default="pixel")
    parser.add_argument("--fault", choices=sorted(FAULTS), help="hidden runs only")
    parser.add_argument("--real", action="store_true",
                        help="REAL mouse and keyboard; needs --task")
    parser.add_argument("--ask", action="store_true",
                        help="with --real: type the instruction yourself")
    args = parser.parse_args()
    if args.real and not args.task:
        parser.error("--real needs --task (one task at a time)")
    if args.ask and not args.real:
        parser.error("--ask only works with --real")
    if args.fault and args.real:
        parser.error("--fault is for hidden runs only")

    tasks = allowed_tasks(args.split, args.task)
    print("Loading the text reader...")
    reader = OcrReader()
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")

    if args.real:
        row = run_real(tasks[0], reader, args.verifier, args.ask)
        if row:
            with (RESULTS / "real_runs.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"time": stamp, "verifier": args.verifier,
                                    **row}) + "\n")
        return 0 if row and row["really_succeeded"] else 1

    rows = run_hidden(tasks, reader, args.verifier, args.fault)
    summary = summarise(rows)
    print(json.dumps(summary, indent=2))
    if not args.task:  # only full runs are saved as results
        name = "_".join(filter(None, ["hidden", args.verifier, args.split,
                                      args.fault]))
        (RESULTS / f"{name}.json").write_text(json.dumps(
            {"time": stamp, "NOTE": "development results, not test results",
             "summary": summary, "tasks": rows}, indent=2) + "\n", encoding="utf-8")
        print(f"Saved results/agent_m5/{name}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
