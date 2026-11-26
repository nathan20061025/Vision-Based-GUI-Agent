# Vision-Based GUI Agent

A final-year project: a desktop agent that completes web tasks from the screen
and verifies each action. **Early development.** A basic rule-based agent
works on some practice tasks (it uses a pretrained text reader). No model
has been trained in this project yet.

## Setup (Windows PowerShell)

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m playwright install chromium
```

## Run

```powershell
.venv\Scripts\python milestone1.py
.venv\Scripts\python milestone1.py --show
.venv\Scripts\python milestone1.py --broken
.venv\Scripts\python milestone1.py --broken --show
.venv\Scripts\python -m pytest
.venv\Scripts\python stop_demo.py
.venv\Scripts\python milestone2_positions.py
.venv\Scripts\python milestone2_positions.py --click
.venv\Scripts\python milestone2_actions.py
.venv\Scripts\python milestone2_actions.py --capture
```

## Practice sites and tasks (Milestone 3)

```powershell
.venv\Scripts\python verify_tasks.py
```

Uses a hidden browser (no mouse control or screen capture) to check every task
in `tasks/` and every failure switch. It tests the sites, not an agent.

- Sites are listed in `practice_sites/sites.json`, each in one split: train,
  validation or test.
- Add `?fault=broken`, `slow`, `popup` or `distractor` to a page address.
  Add `&variant=2` for the second pop-up or banner design. Each split has its
  own designs.
- `evaluation/` reads the page code to score results. `agent/` must not use it.

## Pixel-rule data and tuning (Milestone 4)

```powershell
.venv\Scripts\python -m data_tools.collect          # 10+ minutes, hidden browser
.venv\Scripts\python -m data_tools.tune_pixel_rule  # validation split only
.venv\Scripts\python -m data_tools.label_review     # sheets in runs/label_review/
.venv\Scripts\python -m data_tools.compare_capture  # real screen, page area only
```

- Data goes to `data/` (not in Git). The test split is never collected.
- Chosen settings: `configs/pixel_rule.json` (label sample checked and
  real-screen comparison passed for this data version, one setup). Results are in
  `results/pixel_rule_v1/`. They are validation results, not test results.
- `compare_capture` captures only the practice browser's page area. Keep it in
  front and keep your mouse outside it. `Esc` stops it.
- `milestone1.py` still uses the old placeholder settings.

## Basic agent (Milestone 5)

Plans with fixed rules, reads the screen with pretrained OCR (RapidOCR), chooses
by text and position rules, and checks with the pixel rule. **No model has been
trained in this project.** It understands only the instruction patterns listed
in `agent/planner.py`.

```powershell
.venv\Scripts\python run_agent.py                      # hidden browser, 10 tasks
.venv\Scripts\python run_agent.py --verifier none      # no checking
.venv\Scripts\python run_agent.py --fault distractor   # with a failure on
.venv\Scripts\python run_agent.py --real --task search_git         # REAL mouse
.venv\Scripts\python run_agent.py --real --task search_git --ask   # you type
```

`--real` controls your real mouse and keyboard and captures the practice page
area. Close private windows, turn Caps Lock off, keep the browser in front.
Stop with `Esc` or a screen corner. The test split is refused. Playwright opens
pages, locates the page area and scores results; the agent gets only pictures
and the instruction. Results: `results/agent_m5/`.

## Notes

- `--show` opens a visible browser (it may close quickly). `--broken` makes the
  login button do nothing.
- **`milestone2_positions.py --click` moves your real mouse.** Test the stop
  controls (`Esc`, or mouse into a screen corner) with `stop_demo.py` first.
- **`milestone2_actions.py` controls your real mouse and keyboard.** Turn Caps
  Lock off. Tested only at 100% display scaling on one monitor.
- `--capture` takes **full-screen** pictures: close private windows first. They
  are deleted when the run ends; add `--keep` to keep them. If the program is
  killed (e.g. terminal closed), check `runs/capture/` for leftovers.
- Each actions run writes a text log in `runs/logs/` (typed text is not saved).
- Milestone 1 and the position preview also save pictures in `runs/`.
