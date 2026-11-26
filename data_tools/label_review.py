"""Make picture sheets so YOU can check a random sample of labels.

    python -m data_tools.label_review

Open the sheets in runs/label_review/. For each number, ask: "Is the intended
effect there in the AFTER picture?" Write down any label you disagree with.
"""

import json
import random

from PIL import Image, ImageDraw

from data_tools.collect import OUT
from evaluation.tasks import ROOT

SAMPLE, PER_SHEET, SEED = 24, 4, 7
WIDTH, HEIGHT = 700, 480


def pick(records: list, size: int, seed: int) -> list:
    """A repeatable random sample, half success and half failure."""
    rng = random.Random(seed)
    chosen = []
    for label in (True, False):
        group = [r for r in records if r["success"] is label]
        chosen += rng.sample(group, min(size // 2, len(group)))
    rng.shuffle(chosen)
    return chosen


def describe(record: dict) -> str:
    wanted = "; ".join(f"{r['selector']} {r['check']} = {r['expected']}"
                       for r in record["effect"])
    return f"{record['action']}  |  wanted: {wanted}"


def main() -> None:
    lines = (OUT / "records.jsonl").read_text(encoding="utf-8").splitlines()
    sample = pick([json.loads(line) for line in lines], SAMPLE, SEED)
    folder = ROOT / "runs" / "label_review"
    folder.mkdir(parents=True, exist_ok=True)

    row = HEIGHT + 60
    for start in range(0, len(sample), PER_SHEET):
        group = sample[start:start + PER_SHEET]
        sheet = Image.new("RGB", (WIDTH * 2 + 10, row * len(group)), "black")
        draw = ImageDraw.Draw(sheet)
        for position, record in enumerate(group):
            top = position * row
            label = "SUCCESS" if record["success"] else "FAILURE"
            draw.text((8, top + 6), f"#{start + position + 1}   LABEL: {label}",
                      fill="yellow")
            draw.text((8, top + 22), describe(record)[:200], fill="white")
            for column, key in enumerate(("before", "after")):
                with Image.open(OUT / record[key]) as image:
                    image.thumbnail((WIDTH, HEIGHT))
                    sheet.paste(image, (column * (WIDTH + 10), top + 56))
        path = folder / f"sheet_{start // PER_SHEET + 1}.png"
        sheet.save(path)
        print(path)
    print(f"{len(sample)} examples. Left = before, right = after.")


if __name__ == "__main__":
    main()
