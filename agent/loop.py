"""The agent: plan, then for each step look, choose, act, check, recover.

It sees ONLY pictures from the environment. It never reads page code.

Recovery when a check says "failed":
  1. wait longer and check again (the page may be slow), before acting again
  2. for a button only: try the same place once more
  3. try the next-best place
  4. give up and say so
Typing and ticking are not repeated in the same place: that could double
the text or untick the box.
"""

import time
from dataclasses import asdict, dataclass, field

from agent.matching import candidates
from agent.planner import UnsupportedInstruction, plan
from agent.safety import StopRequested

MAX_ATTEMPTS = 3       # per step
SAME_PLACE = 8         # pixels: places this close count as the same place
SLOW_WAIT = 3.5        # seconds to wait before judging a step as failed


@dataclass
class Result:
    status: str                    # claimed_success / gave_up / unsupported / stopped
    reason: str = ""
    actions: int = 0
    attempts: list = field(default_factory=list)
    ocr_seconds: list = field(default_factory=list)
    seconds: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


def near(a, b) -> bool:
    return abs(a.x - b.x) <= SAME_PLACE and abs(a.y - b.y) <= SAME_PLACE


def choose(options: list, tried: list, action: str):
    """The next place to try, or None."""
    if action == "click" and len(tried) == 1:
        return tried[0]  # one repeat of a button click
    for option in options:
        if not any(near(option, old) for old in tried):
            return option
    return None


def settle(env, pause: float = 0.4, limit: float = 2.5):
    """Wait until two pictures in a row are the same (or the time limit)."""
    env.wait(pause)
    picture = env.capture()
    waited = pause
    while waited < limit:
        env.wait(pause)
        waited += pause
        again = env.capture()
        if again.tobytes() == picture.tobytes():
            return again
        picture = again
    return picture


def run(instruction: str, env, reader, verify, guard, max_actions: int = 12,
        logger=None, observer=None) -> Result:
    """verify(before, after) -> bool, or None for NO checking and no retries.

    observer(step_index, claimed) is for the experimenter's scoring only.
    It is not allowed to influence the agent: its result is only recorded.
    """
    started = time.perf_counter()
    result = Result("claimed_success")

    def log(event, **details):
        if logger:
            logger.log(event, **details)

    def finish(status, reason=""):
        result.status, result.reason = status, reason
        result.seconds = round(time.perf_counter() - started, 1)
        log("agent_end", status=status, reason=reason, actions=result.actions)
        return result

    try:
        steps = plan(instruction)
    except UnsupportedInstruction as error:
        return finish("unsupported", str(error))

    try:
        for index, step in enumerate(steps):
            tried = []
            while True:
                guard.check()
                before = settle(env)
                start = time.perf_counter()
                words = reader.read(before)
                result.ocr_seconds.append(round(time.perf_counter() - start, 2))
                guard.check()

                options = candidates(step, words, before.size)
                target = choose(options, tried, step.action)
                if target is None:
                    return finish("gave_up", f"step {index + 1} ({step.action}): "
                                  + ("no more places to try" if tried
                                     else "target text not found"))
                if result.actions >= max_actions:
                    return finish("gave_up", "action limit reached")

                result.actions += 1
                env.click(target.x, target.y)
                if step.action in ("fill", "select"):
                    env.type_text(step.value)
                if step.action == "select":
                    # Without this, an open list keeps the old value until
                    # something else is clicked.
                    env.press("enter")
                after = settle(env)

                claimed, waited = True, False
                if verify is not None:
                    claimed = verify(before, after)
                    if not claimed:  # maybe just slow: wait, look again
                        env.wait(SLOW_WAIT)
                        claimed, waited = verify(before, env.capture()), True

                record = {"step": index, "action": step.action,
                          "x": target.x, "y": target.y, "why": target.why,
                          "claimed": claimed, "after_waiting": waited}
                if observer:
                    record["truly"] = observer(index, claimed)
                result.attempts.append(record)
                log("agent_attempt", **record)

                if claimed:
                    break
                tried.append(target)
                if len(tried) >= MAX_ATTEMPTS:
                    return finish("gave_up", f"step {index + 1} ({step.action}): "
                                  "still failing after retries")
    except StopRequested as stop:
        return finish("stopped", str(stop))

    return finish("claimed_success")
