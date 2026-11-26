"""Turn a written instruction into steps, using fixed rules.

This is NOT a machine-learning model and understands only these patterns:

  Log in with username "U" and password "P".   (also "Try to log in ...")
  Search for "TEXT".
  Sign up with the name "N" and email "E", and accept the terms.
  Add a task called "TEXT".
  Choose the X theme / X rating
  set the display name to "TEXT" / write the comment "TEXT"
  turn on email notifications
  ... save the changes / send the feedback

Target words come from the instruction and a few general synonyms.
Anything else is rejected, so the agent never guesses what you meant.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    action: str               # click, fill, check or select
    targets: tuple[str, ...]  # words that may name the target, best first
    value: str | None = None  # text to type, or option to choose

    @property
    def kind(self) -> str:
        return {"click": "button", "fill": "textbox",
                "check": "checkbox", "select": "dropdown"}[self.action]


class UnsupportedInstruction(ValueError):
    pass


def click(*targets):
    return Step("click", targets)


def fill(value, *targets):
    return Step("fill", targets, value)


QUOTED = r'"([^"]+)"'

# Each clause of a longer instruction must match one of these completely.
CLAUSES = [
    (rf"turn on email notifications",
     lambda m: [Step("check", ("email notifications",))]),
    (r"choose the (\w+) theme",
     lambda m: [Step("select", ("theme",), m[1])]),
    (r"choose the (\w+) rating",
     lambda m: [Step("check", (m[1],))]),
    (rf"set the display name to {QUOTED}",
     lambda m: [fill(m[1], "display name")]),
    (rf"write the comment {QUOTED}",
     lambda m: [fill(m[1], "your comment", "comment")]),
    (r"save the changes",
     lambda m: [click("save changes", "save")]),
    (r"send the feedback",
     lambda m: [click("send feedback", "send", "submit")]),
]

WHOLE = [
    (rf"(?:try to )?log in with username {QUOTED} and password {QUOTED}",
     lambda m: [fill(m[1], "username"), fill(m[2], "password"),
                click("log in", "login", "sign in")]),
    (rf"search for {QUOTED}",
     lambda m: [fill(m[1], "search"), click("search")]),
    (rf"sign up with the name {QUOTED} and email {QUOTED}, and accept the terms",
     lambda m: [fill(m[1], "full name", "name"), fill(m[2], "email"),
                Step("check", ("accept the terms", "terms")),
                click("sign up", "register", "create account")]),
    (rf"add a task called {QUOTED}",
     lambda m: [fill(m[1], "new task", "task", "what needs to be done"),
                click("add task", "add")]),
]


def plan(instruction: str) -> list[Step]:
    text = instruction.strip().rstrip(".").strip()
    for pattern, build in WHOLE:
        match = re.fullmatch(pattern, text, re.IGNORECASE)
        if match:
            return build(match)

    steps = []
    # Split "A, B and C" but never inside quotation marks.
    parts = re.split(r'(?:,\s*(?:and\s+)?|\s+and\s+)(?=(?:[^"]*"[^"]*")*[^"]*$)', text)
    for part in parts:
        for pattern, build in CLAUSES:
            match = re.fullmatch(pattern, part.strip(), re.IGNORECASE)
            if match:
                steps += build(match)
                break
        else:
            raise UnsupportedInstruction(
                f"I only understand a few kinds of instruction. Not: {part!r}")
    return steps
