"""Load and validate sites and task files."""

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPLITS = {"train", "validation", "test"}
FAULTS = {"broken", "slow", "popup", "distractor"}
CHECKS = {"count", "text", "value", "checked"}
ACTIONS = {"fill", "click", "select"}
REQUIRED = {"id", "site", "split", "difficulty", "instruction",
            "step_limit", "success", "answer_key"}


@dataclass(frozen=True)
class Task:
    id: str
    site: str
    split: str
    difficulty: str
    instruction: str     # the ONLY part the agent may be given
    step_limit: int
    success: list        # for the examiner only
    answer_key: list     # for the examiner only: proves the task can be done


def load_sites(root: Path = ROOT) -> dict:
    path = root / "practice_sites" / "sites.json"
    sites = json.loads(path.read_text(encoding="utf-8"))
    for name, site in sites.items():
        if site["split"] not in SPLITS:
            raise ValueError(f"site {name}: unknown split {site['split']!r}")
        if not (root / "practice_sites" / site["path"]).is_file():
            raise ValueError(f"site {name}: page not found")
    return sites


def check_task(data: dict, sites: dict) -> Task:
    name = data.get("id", "?")
    if set(data) != REQUIRED:
        raise ValueError(f"task {name}: fields must be {sorted(REQUIRED)}")
    if data["site"] not in sites:
        raise ValueError(f"task {name}: unknown site {data['site']!r}")
    # A whole site belongs to one split, so its tasks must match it.
    if data["split"] != sites[data["site"]]["split"]:
        raise ValueError(f"task {name}: split differs from its site's split")
    if not data["success"]:
        raise ValueError(f"task {name}: needs at least one success check")
    if any(item["check"] not in CHECKS for item in data["success"]):
        raise ValueError(f"task {name}: unknown success check")
    if any(step["action"] not in ACTIONS for step in data["answer_key"]):
        raise ValueError(f"task {name}: unknown answer-key action")
    if data["step_limit"] < len(data["answer_key"]):
        raise ValueError(f"task {name}: step limit is smaller than the answer")
    return Task(**data)


def load_tasks(root: Path = ROOT, split: str | None = None) -> list[Task]:
    sites = load_sites(root)
    tasks = []
    for path in sorted((root / "tasks").glob("*.json")):
        task = check_task(json.loads(path.read_text(encoding="utf-8")), sites)
        if task.id != path.stem:
            raise ValueError(f"task {task.id}: file name must match the id")
        if split is None or task.split == split:
            tasks.append(task)
    return tasks


def task_url(task: Task, fault: str | None = None, root: Path = ROOT) -> str:
    if fault is not None and fault not in FAULTS:
        raise ValueError(f"unknown fault {fault!r}")
    page = root / "practice_sites" / load_sites(root)[task.site]["path"]
    return page.as_uri() + (f"?fault={fault}" if fault else "")
