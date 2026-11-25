"""Pixel-difference baseline: did enough of the screen change?"""

import numpy as np
from PIL import Image

# Placeholders, NOT tuned. Choose real values later using validation data only.
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


def looks_successful(share: float, threshold: float = CHANGE_THRESHOLD) -> bool:
    return share >= threshold
