"""Read the words in a picture, with their positions (OCR).

Uses RapidOCR. Its models are PRETRAINED and bundled with the package; this
is not a model trained in this project. It runs on this computer.
"""

import logging
from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    """A piece of text and the rectangle around it, in picture pixels."""
    text: str
    left: float
    top: float
    right: float
    bottom: float

    @property
    def centre(self) -> tuple[float, float]:
        return (self.left + self.right) / 2, (self.top + self.bottom) / 2

    @property
    def height(self) -> float:
        return self.bottom - self.top


def merge_lines(words: list[Word]) -> list[Word]:
    """Join pieces that sit close together on one line ("Full" + "name")."""
    merged: list[Word] = []
    for word in sorted(words, key=lambda w: (w.centre[1], w.left)):
        for i, other in enumerate(merged):
            height = min(word.height, other.height)
            same_row = abs(word.centre[1] - other.centre[1]) < height * 0.5
            gap = word.left - other.right
            if same_row and -height * 0.5 <= gap <= height * 0.7:
                merged[i] = Word(f"{other.text} {word.text}",
                                 min(other.left, word.left), min(other.top, word.top),
                                 max(other.right, word.right),
                                 max(other.bottom, word.bottom))
                break
        else:
            merged.append(word)
    return merged


class OcrReader:
    def __init__(self):
        from rapidocr import RapidOCR

        logging.getLogger("RapidOCR").setLevel(logging.WARNING)
        self._engine = RapidOCR()
        logging.getLogger("RapidOCR").setLevel(logging.WARNING)

    def read(self, image) -> list[Word]:
        """image: a PIL picture."""
        import numpy as np

        result = self._engine(np.asarray(image.convert("RGB"))[:, :, ::-1])
        if result.boxes is None:
            return []
        words = []
        for box, text in zip(result.boxes, result.txts):
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            words.append(Word(text, min(xs), min(ys), max(xs), max(ys)))
        return merge_lines(words)
