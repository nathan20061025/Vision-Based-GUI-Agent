# Vision-Based GUI Agent

A final-year project: a desktop agent that completes web tasks from the screen
and verifies each action. **Early development.** No ML models are built yet.

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
