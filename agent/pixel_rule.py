"""Pixel-difference baseline: did enough of the screen change?"""

import json
from pathlib import Path

import numpy as np
from PIL import Image

# Tuned values are saved here by data_tools/tune_pixel_rule.py.
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "configs" / "pixel_rule.json"

# The original placeholders, NOT tuned. milestone1.py still uses them.
# Use load_settings() for the values chosen on validation data.
PIXEL_TOLERANCE = 25      # brightness difference (0-255) that counts as changed
CHANGE_THRESHOLD = 0.01   # share of changed pixels needed to say "success"


def changed_share(before: Image.Image, after: Image.Image,
                  tolerance: int = PIXEL_TOLERANCE) -> float:
    """Return the share of pixels (0.0 to 1.0) that changed."""
    if before.size != after.size:
        raise ValueError("Screenshots must be the same size")

    # int16 allows negative differences (uint8 would wrap around).
    first = np.asarray(before.convert("L"), dtype=np.int16)
    second = np.asarray(after.convert("L"), dtype=np.int16)
    return float((np.abs(first - second) > tolerance).mean())


def load_settings(path: Path = SETTINGS_FILE) -> tuple[int, float]:
    """(pixel tolerance, change threshold) chosen on validation data."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["pixel_tolerance"], data["change_threshold"]


def looks_successful(share: float, threshold: float = CHANGE_THRESHOLD) -> bool:
    return share >= threshold
