"""Choose the pixel rule's two settings using VALIDATION examples only.

    python -m data_tools.tune_pixel_rule

Score: highest balanced accuracy (success and failure count equally).
Ties: fewer false successes, then smaller tolerance, then larger threshold.
"""

import csv
import json
import sys
from collections import defaultdict
from fractions import Fraction

from PIL import Image

from agent.pixel_rule import (CHANGE_THRESHOLD, PIXEL_TOLERANCE, SETTINGS_FILE,
                              changed_share)
from data_tools.collect import OUT, data_version
from evaluation.tasks import ROOT

RESULTS = ROOT / "results" / "pixel_rule_v1"
TOLERANCES = [0, 5, 10, 15, 25, 40, 60, 90]
THRESHOLDS = [0.0, 0.0001, 0.0002, 0.0005, 0.001, 0.0015, 0.002, 0.0025,
              0.003, 0.004, 0.005, 0.006, 0.008, 0.01, 0.015, 0.02, 0.03,
              0.05, 0.08, 0.12, 0.2, 0.3]


def validation_only(records: list) -> list:
    chosen = [r for r in records if r["split"] == "validation"]
    if not chosen:
        raise ValueError("no validation examples")
    return chosen


def score(labels: list, predictions: list) -> dict:
    """labels / predictions: lists of True (success) or False (failure)."""
    pairs = list(zip(labels, predictions, strict=True))
    tp = sum(a and b for a, b in pairs)
    tn = sum(not a and not b for a, b in pairs)
    fp = sum(not a and b for a, b in pairs)   # FALSE SUCCESS
    fn = sum(a and not b for a, b in pairs)
    if not (tp + fn) or not (tn + fp):
        raise ValueError("need both successes and failures")
    # Fractions make exact ties compare as equal.
    balanced = (Fraction(tp, tp + fn) + Fraction(tn, tn + fp)) / 2
    return {"balanced_accuracy": float(balanced), "exact": balanced,
            "false_success_rate": fp / (fp + tn),
            "success_found_rate": tp / (tp + fn),
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn}


def choose(rows: list) -> dict:
    return max(rows, key=lambda r: (r["exact"], -r["false_success_rate"],
                                    -r["tolerance"], r["threshold"]))


def sweep(shares: dict, labels: list, which: list) -> list:
    """Score every setting on the examples whose positions are in `which`."""
    rows = []
    for tolerance in TOLERANCES:
        for threshold in THRESHOLDS:
            result = score([labels[i] for i in which],
                           [shares[tolerance][i] >= threshold for i in which])
            rows.append({"tolerance": tolerance, "threshold": threshold, **result})
    return rows


def group_accuracy(records, predictions, field) -> dict:
    groups = defaultdict(list)
    for record, predicted in zip(records, predictions):
        names = record[field] if isinstance(record[field], list) else [record[field]]
        for name in names:
            groups[name].append(predicted == record["success"])
    return {name: {"correct": sum(g), "total": len(g)}
            for name, g in sorted(groups.items())}


def main() -> int:
    lines = (OUT / "records.jsonl").read_text(encoding="utf-8").splitlines()
    records = validation_only([json.loads(line) for line in lines])
    version = data_version(OUT)
    labels = [r["success"] for r in records]

    shares = {t: [] for t in TOLERANCES}
    for record in records:
        with Image.open(OUT / record["before"]) as before, \
                Image.open(OUT / record["after"]) as after:
            for tolerance in TOLERANCES:
                shares[tolerance].append(changed_share(before, after, tolerance))

    everything = list(range(len(records)))
    rows = sweep(shares, labels, everything)
    best = choose(rows)

    def predict(tolerance, threshold):
        return [s >= threshold for s in shares[tolerance]]

    chosen = predict(best["tolerance"], best["threshold"])
    placeholder = score(labels, [
        s >= CHANGE_THRESHOLD for s in shares[PIXEL_TOLERANCE]])

    # How stable is it? Tune on two validation sites, check on the third.
    left_out = {}
    for site in sorted({r["site"] for r in records}):
        keep = [i for i, r in enumerate(records) if r["site"] != site]
        held = [i for i, r in enumerate(records) if r["site"] == site]
        pick = choose(sweep(shares, labels, keep))
        result = score([labels[i] for i in held],
                       [shares[pick["tolerance"]][i] >= pick["threshold"]
                        for i in held])
        left_out[site] = {"tolerance": pick["tolerance"],
                          "threshold": pick["threshold"],
                          "balanced_accuracy": result["balanced_accuracy"],
                          "false_success_rate": result["false_success_rate"]}

    def clean(row):
        return {k: v for k, v in row.items() if k != "exact"}

    report = {
        "WARNING": "Validation results used to CHOOSE settings. Not test results.",
        "data_version": version,
        "examples": len(records),
        "successes": sum(labels),
        "failures": len(labels) - sum(labels),
        "chosen": clean(best),
        "settings_tied_on_balanced_accuracy":
            sum(r["exact"] == best["exact"] for r in rows),
        "old_placeholder": {"tolerance": PIXEL_TOLERANCE,
                            "threshold": CHANGE_THRESHOLD, **clean(placeholder)},
        "accuracy_by_case": group_accuracy(records, chosen, "cases"),
        "accuracy_by_action": group_accuracy(records, chosen, "action"),
        "accuracy_by_site": group_accuracy(records, chosen, "site"),
        "tune_on_two_sites_check_third": left_out,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                         encoding="utf-8")
    with (RESULTS / "all_settings.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(clean(rows[0])),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(clean(r) for r in rows)

    SETTINGS_FILE.parent.mkdir(exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps({
        "status": "provisional: label check and real-screen comparison needed",
        "pixel_tolerance": best["tolerance"],
        "change_threshold": best["threshold"],
        "chosen_on": "validation split only",
        "data_version": version,
        "rule": "highest balanced accuracy; ties: fewer false successes, "
                "smaller tolerance, larger threshold",
    }, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
