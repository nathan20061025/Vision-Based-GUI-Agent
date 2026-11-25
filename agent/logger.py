"""A text log of one run, saved as JSON Lines (one record per line).

Never pass typed text to the logger. Only record how long it was.
"""

import json
from datetime import datetime
from pathlib import Path


class RunLogger:
    def __init__(self, folder: Path):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.path = folder / f"{name}.jsonl"

    def log(self, event: str, **details) -> None:
        record = {"time": datetime.now().isoformat(timespec="milliseconds"),
                  "event": event, **details}
        # Written straight away, so earlier records survive a later crash.
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")
