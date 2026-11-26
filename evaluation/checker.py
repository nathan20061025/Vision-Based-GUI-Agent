"""Automatic success checks. Reads the DOM: for scoring only."""


def check_one(page, rule: dict) -> bool:
    found = page.locator(rule["selector"])
    expected = rule["expected"]
    if rule["check"] == "count":
        return found.count() == expected
    # The other checks need exactly one element.
    if found.count() != 1:
        return False
    if rule["check"] == "text":
        return found.inner_text().strip() == expected
    if rule["check"] == "value":
        return found.input_value() == expected
    if rule["check"] == "checked":
        return found.is_checked() == expected
    raise ValueError(f"unknown check {rule['check']!r}")


def task_succeeded(page, task) -> bool:
    """True only if EVERY success rule holds right now."""
    return all(check_one(page, rule) for rule in task.success)
