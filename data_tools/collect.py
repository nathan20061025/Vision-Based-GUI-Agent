"""Collect before/after pictures with labels (train and validation ONLY).

    python -m data_tools.collect

Uses a hidden browser: page pictures only, no mouse control, no desktop
capture. The test split is refused; it is kept for the final experiments.
"""

import hashlib
import io
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from data_tools.cases import EXPECTED, cases_for, run_case, vary_text
from evaluation.step_rules import step_effect
from evaluation.tasks import ROOT, load_tasks

OUT = ROOT / "data" / "pixel_v1"
ALLOWED_SPLITS = ("train", "validation")

# Each variation changes the window size, zoom, colours and free text.
VARIATIONS = [
    {"name": "v1", "size": (1000, 700), "zoom": 1.0, "hue": 0},
    {"name": "v2", "size": (1280, 720), "zoom": 1.15, "hue": 0},
    {"name": "v3", "size": (800, 600), "zoom": 0.9, "hue": 140},
]


def check_split(split: str) -> None:
    if split not in ALLOWED_SPLITS:
        raise ValueError(f"split {split!r} must not be collected or tuned on")


def make_style(variation):
    def style(page):
        page.evaluate(
            """([zoom, hue]) => {
                document.body.style.zoom = zoom;
                if (hue) document.documentElement.style.filter =
                    `hue-rotate(${hue}deg)`;
            }""", [variation["zoom"], variation["hue"]])
    return style


def data_version(folder: Path) -> str:
    """A fingerprint of the records and pictures."""
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        if path.is_file() and (path.suffix == ".png" or path.name == "records.jsonl"):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)  # this folder is made only by this script
    images = OUT / "images"
    images.mkdir(parents=True)

    tasks = [t for split in ALLOWED_SPLITS for t in load_tasks(split=split)]
    records, seen, mismatches, errors = [], {}, [], []
    duplicates, checked = 0, 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for number, variation in enumerate(VARIATIONS):
            width, height = variation["size"]
            for original in tasks:
                check_split(original.split)
                task = vary_text(original, number)
                for index, step in enumerate(task.answer_key):
                    for case in cases_for(step):
                        where = f"{task.id}_s{index}_{case}_{variation['name']}"
                        page = browser.new_page(
                            viewport={"width": width, "height": height})
                        page.set_default_timeout(5000)
                        try:
                            examples = run_case(page, task, index, case,
                                                page.screenshot, make_style(variation))
                        except Exception as error:
                            errors.append(f"{where}: {type(error).__name__}")
                            examples = []
                        page.close()

                        for item in examples:
                            before, after = item.pop("before"), item.pop("after")
                            name = f"{task.id}_s{index}_{item['case']}_{variation['name']}"
                            # Check EVERY label, including later duplicates.
                            checked += 1
                            if item["success"] != EXPECTED[item["case"]]:
                                mismatches.append(name)
                            key = (task.id, index, hashlib.sha256(before).digest(),
                                   hashlib.sha256(after).digest(), item["success"])
                            if key in seen:  # identical examples add nothing
                                duplicates += 1
                                kept = seen[key]
                                if item["case"] not in kept["cases"]:
                                    kept["cases"].append(item["case"])
                                continue
                            for suffix, data in (("before", before), ("after", after)):
                                Image.open(io.BytesIO(data)).convert("RGB").save(
                                    images / f"{name}_{suffix}.png")
                            records.append({
                                "cases": [item["case"]],
                                "id": name, "site": task.site, "split": task.split,
                                "task": task.id, "step": index,
                                "variation": variation["name"],
                                "effect": step_effect(task, index), **item,
                                "before": f"images/{name}_before.png",
                                "after": f"images/{name}_after.png"})
                            seen[key] = records[-1]
            print(f"variation {variation['name']} done, {len(records)} examples so far")
        browser.close()

    (OUT / "records.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    summary = {
        "data_version": data_version(OUT),
        "examples": len(records),
        "labels_checked": checked,
        "identical_examples_removed": duplicates,
        "by_split": dict(Counter(r["split"] for r in records)),
        "success": sum(r["success"] for r in records),
        "failure": sum(not r["success"] for r in records),
        # One saved example can stand for several cases with identical pictures.
        "examples_covering_each_case": dict(sorted(
            Counter(c for r in records for c in r["cases"]).items())),
        "label_differs_from_expected": mismatches,
        "errors": errors,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if errors or mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
