import json

import pytest

from agent.pixel_rule import load_settings
from data_tools.cases import EXPECTED, cases_for, vary_text
from data_tools.collect import check_split
from data_tools.compare_capture import summarise
from data_tools.label_review import pick
from data_tools.tune_pixel_rule import choose, score, validation_only
from evaluation.step_rules import step_effect
from evaluation.tasks import load_tasks


def test_test_split_is_refused():
    with pytest.raises(ValueError):
        check_split("test")


def test_tuning_uses_validation_records_only():
    records = [{"split": s} for s in ("train", "validation", "test")]
    assert validation_only(records) == [{"split": "validation"}]
    with pytest.raises(ValueError):
        validation_only([{"split": "train"}])


def test_scores_are_calculated_correctly():
    result = score([True, True, False, False], [True, False, True, False])
    assert (result["tp"], result["fn"], result["fp"], result["tn"]) == (1, 1, 1, 1)
    assert result["balanced_accuracy"] == 0.5
    assert result["false_success_rate"] == 0.5


def test_scoring_needs_both_kinds_of_label():
    with pytest.raises(ValueError):
        score([True, True], [True, False])


def row(exact, false_rate, tolerance=5, threshold=0.01):
    return {"exact": exact, "false_success_rate": false_rate,
            "tolerance": tolerance, "threshold": threshold}


def test_tie_goes_to_fewer_false_successes_then_fixed_order():
    assert choose([row(1, 0.4), row(1, 0.2)])["false_success_rate"] == 0.2
    assert choose([row(0, 0.0), row(1, 0.9)])["exact"] == 1
    assert choose([row(1, 0.2, tolerance=25), row(1, 0.2, tolerance=5)])["tolerance"] == 5
    assert choose([row(1, 0.2, threshold=0.01),
                   row(1, 0.2, threshold=0.02)])["threshold"] == 0.02


def test_every_case_has_an_expected_label():
    for task in load_tasks():
        for step in task.answer_key:
            for case in cases_for(step):
                names = ["slow_early", "slow_late"] if case == "slow" else [case]
                assert all(name in EXPECTED for name in names)


def test_page_faults_are_only_used_on_button_clicks():
    for action in ("fill", "select", "check"):
        cases = cases_for({"action": action, "selector": "#x"})
        assert not {"broken", "slow", "distractor1"} & set(cases)


def test_changed_text_stays_consistent_with_the_success_rule():
    task = next(t for t in load_tasks() if t.id == "todo_add")
    varied = vary_text(task, 1)
    typed = varied.answer_key[0]["value"]
    assert typed != "Buy milk"
    assert step_effect(varied, 0)[0]["expected"] == typed
    assert step_effect(varied, 1)[0]["expected"] == typed
    assert task.answer_key[0]["value"] == "Buy milk"  # original unchanged


def test_label_sample_is_repeatable_and_balanced():
    records = [{"id": i, "success": i % 3 == 0} for i in range(90)]
    first = pick(records, 20, seed=1)
    assert first == pick(records, 20, seed=1)
    assert sum(r["success"] for r in first) == 10


def test_comparison_pass_rule():
    same = {"label": True, "page_says": True, "screen_says": True,
            "page_share": 0.01, "screen_share": 0.0101}
    different = same | {"screen_says": False}
    assert summarise([same] * 20)["passed"]
    assert not summarise([same] * 18 + [different] * 2)["passed"]
    assert not summarise([same | {"screen_share": 0.02}] * 20)["passed"]


def test_settings_are_loaded_from_file(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"pixel_tolerance": 5, "change_threshold": 0.002}))
    assert load_settings(path) == (5, 0.002)
