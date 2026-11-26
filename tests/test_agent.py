import pytest
from PIL import Image

from agent import loop
from agent.matching import candidates, text_score
from agent.ocr import Word, merge_lines
from agent.planner import Step, UnsupportedInstruction, plan
from agent.safety import SafetyGuard
from evaluation.tasks import load_tasks
from run_agent import allowed_tasks, same_plan, summarise

DEV_TASKS = [t for s in ("train", "validation") for t in load_tasks(split=s)]


def word(text, x=100, y=100, width=80, height=16):
    return Word(text, x, y, x + width, y + height)


# --- planner ---------------------------------------------------------------

@pytest.mark.parametrize("task", DEV_TASKS, ids=lambda t: t.id)
def test_every_development_instruction_gives_the_right_kinds_of_step(task):
    assert same_plan(task.instruction, task)


def test_planner_keeps_typed_values_exactly():
    steps = plan('Add a task called "Salt, and pepper".')
    assert steps[0].value == "Salt, and pepper"


def test_comma_and_and_split_clauses_but_not_quoted_text():
    steps = plan('Choose the Dark theme, set the display name to "A and B" '
                 "and save the changes.")
    assert [s.action for s in steps] == ["select", "fill", "click"]
    assert steps[1].value == "A and B"


@pytest.mark.parametrize("text", ["", "Delete my account.", "Order a pizza",
                                  "Save the changes and delete everything"])
def test_unsupported_instructions_are_rejected(text):
    with pytest.raises(UnsupportedInstruction):
        plan(text)


# --- reading and matching ---------------------------------------------------

def test_pieces_on_one_line_are_joined_but_not_distant_ones():
    joined = merge_lines([word("Full", 59, 100, 30), word("name", 93, 100, 40),
                          word("Search", 400, 100, 50)])
    assert sorted(w.text for w in joined) == ["Full name", "Search"]


def test_text_score():
    assert text_score("log in", "Login") == 1.0
    assert 0 < text_score("search", "Search books") < 1
    assert text_score("login", "Weather") == 0
    assert text_score("full name", "Full I name") > 0.55  # a small OCR error


def test_button_prefers_the_exact_lower_text():
    words = [word("Practice Login", 400, 150, 160), word("Login", 480, 320, 40)]
    first = candidates(Step("click", ("log in", "login")), words, (1000, 700))[0]
    assert (first.x, first.y) == (500, 328)


def test_box_guesses_start_on_the_text_then_below():
    found = candidates(Step("fill", ("email",), "x"), [word("Email")], (1000, 700))
    assert (found[0].x, found[0].y) == (140, 108)
    assert found[1].y > 116


def test_missing_text_gives_no_places():
    assert candidates(Step("click", ("save",)), [word("Hello")], (1000, 700)) == []


def test_places_outside_the_picture_are_dropped():
    found = candidates(Step("check", ("terms",)), [word("terms", 2, 100)], (1000, 700))
    assert all(0 <= c.x < 1000 for c in found)


# --- loop, with fakes --------------------------------------------------------

class FakeEnv:
    def __init__(self):
        self.calls = []

    def capture(self):
        return Image.new("RGB", (1000, 700), "white")

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def type_text(self, text):
        self.calls.append(("type", text))

    def press(self, key):
        self.calls.append(("press", key))

    def wait(self, seconds):
        pass


class FakeReader:
    def __init__(self, *words):
        self.words = list(words)

    def read(self, image):
        return self.words


SEARCH = FakeReader(word("Search books", 100, 100, 100), word("Search", 500, 100, 60))


def test_loop_acts_in_order_when_checks_pass():
    env = FakeEnv()
    result = loop.run('Search for "git".', env, SEARCH, lambda b, a: True,
                      SafetyGuard())
    assert result.status == "claimed_success"
    assert env.calls == [("click", 150, 108), ("type", "git"), ("click", 530, 108)]


def test_list_choice_is_confirmed_with_enter():
    env = FakeEnv()
    reader = FakeReader(word("Theme", 200, 170, 50), word("Save changes", 500, 300, 100))
    loop.run("Choose the Dark theme and save the changes.", env, reader,
             lambda b, a: True, SafetyGuard())
    assert env.calls[1:3] == [("type", "Dark"), ("press", "enter")]


def test_button_is_retried_once_in_place_then_gives_up():
    env = FakeEnv()
    reader = FakeReader(word("Save changes", 500, 300, 100))
    result = loop.run("Save the changes.", env, reader, lambda b, a: False,
                      SafetyGuard())
    assert result.status == "gave_up"
    assert env.calls == [("click", 550, 308), ("click", 550, 308)]


def test_checkbox_is_never_clicked_twice_in_the_same_place():
    env = FakeEnv()
    reader = FakeReader(word("Email notifications", 300, 300, 150))
    loop.run("Turn on email notifications.", env, reader, lambda b, a: False,
             SafetyGuard())
    assert len(env.calls) == 3 == len(set(env.calls))


def test_slow_page_is_checked_again_before_acting_again():
    answers = iter([False, True])
    env = FakeEnv()
    reader = FakeReader(word("Save changes", 500, 300, 100))
    result = loop.run("Save the changes.", env, reader,
                      lambda b, a: next(answers), SafetyGuard())
    assert result.status == "claimed_success"
    assert len(env.calls) == 1 and result.attempts[0]["after_waiting"]


def test_without_a_verifier_there_are_no_retries():
    env = FakeEnv()
    reader = FakeReader(word("Save changes", 500, 300, 100))
    loop.run("Save the changes.", env, reader, None, SafetyGuard())
    assert len(env.calls) == 1


def test_stop_prevents_any_action():
    guard = SafetyGuard()
    guard.stop("Esc key pressed")
    env = FakeEnv()
    result = loop.run('Search for "git".', env, SEARCH, None, guard)
    assert result.status == "stopped" and env.calls == []


def test_action_limit():
    env = FakeEnv()
    result = loop.run('Search for "git".', env, SEARCH, None, SafetyGuard(),
                      max_actions=1)
    assert result.status == "gave_up" and "limit" in result.reason


def test_observer_cannot_change_what_the_agent_does():
    runs = []
    for truth in (True, False):
        env = FakeEnv()
        loop.run('Search for "git".', env, SEARCH, lambda b, a: True,
                 SafetyGuard(), observer=lambda i, c: truth)
        runs.append(env.calls)
    assert runs[0] == runs[1]


def test_unsupported_instruction_does_nothing():
    env = FakeEnv()
    result = loop.run("Order a pizza", env, SEARCH, None, SafetyGuard())
    assert result.status == "unsupported" and env.calls == []


# --- examiner ----------------------------------------------------------------

def test_test_split_is_refused():
    assert {t.split for t in allowed_tasks()} == {"train", "validation"}
    with pytest.raises(SystemExit):
        allowed_tasks(task_id="shop_add_notebook")


def test_summary_counts_false_claims():
    row = {"split": "train", "really_succeeded": False,
           "agent_claimed_success": True, "false_claim": True, "ocr_seconds": [1.0],
           "attempts": [{"claimed": True, "truly": False}]}
    result = summarise([row])
    assert result["false_task_claims"] == 1
    assert result["attempts_wrongly_called_success"] == 1
