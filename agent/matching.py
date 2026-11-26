"""Choose where to act, from OCR words only (no page code).

A simple baseline, NOT a trained grounding model. It compares text and uses
position rules. It cannot see the outline of a box, checkbox or list, so
for those it makes guesses near the label, best guess first.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from agent.ocr import Word

MIN_SCORE = 0.55


@dataclass(frozen=True)
class Candidate:
    x: int
    y: int
    score: float
    why: str  # for the log


def normalise(text: str) -> str:
    """Lower case, letters and digits only: OCR often loses or adds spaces."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def text_score(target: str, found: str) -> float:
    """How well `found` names `target`, from 0 to 1."""
    want, have = normalise(target), normalise(found)
    if not want or not have:
        return 0.0
    if want == have:
        return 1.0
    if want in have:  # part of a longer line: better if the line is shorter
        return 0.5 + 0.4 * len(want) / len(have)
    ratio = SequenceMatcher(None, want, have).ratio()
    return ratio * 0.85 if ratio >= 0.8 else 0.0  # small OCR mistakes


def ranked_words(targets, words: list[Word]) -> list[tuple[float, Word, str]]:
    """Best matches first. Earlier targets are preferred."""
    scored = []
    for word in words:
        best = max(((text_score(t, word.text) - 0.02 * i, t)
                    for i, t in enumerate(targets)), default=(0, ""))
        if best[0] >= MIN_SCORE:
            scored.append((best[0], word, best[1]))
    # Ties: the lower one first (buttons usually come after headings).
    return sorted(scored, key=lambda item: (-item[0], -item[1].centre[1]))


def candidates(step, words: list[Word], size: tuple[int, int]) -> list[Candidate]:
    """Places to try for this step, best first, all inside the picture."""
    matches = ranked_words(step.targets, words)
    if step.kind == "textbox" and step.targets[0] == "search":
        # "Search books" (inside the box) rather than the "Search" button.
        matches.sort(key=lambda m: normalise(m[1].text) == "search")

    found = []
    for score, word, target in matches[:3]:
        x, y = word.centre
        h = word.height
        # 1. On the text: a button, text inside a box, or a clickable label.
        guesses = [(x, y, "on the text")]
        if step.kind == "textbox":
            guesses += [(word.left + 4 * h, word.bottom + 1.3 * h, "below the label"),
                        (word.right + 8 * h, y, "right of the label")]
        elif step.kind == "checkbox":
            guesses += [(word.left - 1.0 * h, y, "left of the label"),
                        (word.right + 1.0 * h, y, "right of the label")]
        elif step.kind == "dropdown":
            guesses += [(word.right + 8 * h, y, "right of the label"),
                        (word.left + 3 * h, word.bottom + 1.3 * h, "below the label")]
        for rank, (gx, gy, where) in enumerate(guesses):
            if 0 <= gx < size[0] and 0 <= gy < size[1]:
                found.append(Candidate(round(gx), round(gy), score - 0.001 * rank,
                                       f"{where} '{target}'"))
        if step.kind == "button":
            continue
        break  # for other controls, guess around the best label only
    return found
