"""Milestone 1: take a screenshot before and after one click, then compare.

Run:
    python milestone1.py              working button
    python milestone1.py --broken     button does nothing
    add --show to watch the browser

Here Playwright finds and clicks the button for us. Later, the parser,
grounding model and mouse control will replace that part.
These are page screenshots; full-screen capture comes later.
"""

import argparse
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from agent.pixel_rule import changed_share, looks_successful

ROOT = Path(__file__).parent


def run(broken: bool, show: bool) -> None:
    out = ROOT / "runs" / ("broken" if broken else "working")
    out.mkdir(parents=True, exist_ok=True)

    url = (ROOT / "practice_sites" / "login" / "index.html").as_uri()
    if broken:
        url += "?broken=1"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show)
        page = browser.new_page(viewport={"width": 1000, "height": 700})
        page.goto(url)
        # Without this pause, the first screenshot often failed with --show.
        page.wait_for_timeout(1000)
        page.fill("#username", "testuser")
        page.fill("#password", "test123")

        page.screenshot(path=out / "before.png")
        page.click("#login-button")
        page.wait_for_timeout(500)  # simple fixed wait for now
        page.screenshot(path=out / "after.png")

        # The "answer sheet": used only to check results, not by the verifier.
        truly_worked = page.locator("#welcome").count() == 1
        browser.close()

    with Image.open(out / "before.png") as before, Image.open(out / "after.png") as after:
        share = changed_share(before, after)

    print(f"Changed pixels : {share:.2%}")
    print(f"Pixel rule says: {'success' if looks_successful(share) else 'failure'}")
    print(f"Real result    : {'success' if truly_worked else 'failure'}")
    print(f"Screenshots    : {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broken", action="store_true", help="button does nothing")
    parser.add_argument("--show", action="store_true", help="show the browser")
    args = parser.parse_args()
    run(args.broken, args.show)
