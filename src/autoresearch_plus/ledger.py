from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .models import RunRecord


RESULTS_HEADER = [
    "revision",
    "decision",
    "score",
    "previous_score",
    "metric_delta",
    "status",
    "summary",
    "mutation",
    "target_file",
    "git_branch",
    "git_commit",
]


class RunLedger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.runs_dir = root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.results_path = self.runs_dir / "results.tsv"
        self.traces_dir = self.runs_dir / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        if not self.results_path.exists():
            with self.results_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=RESULTS_HEADER, delimiter="\t")
                writer.writeheader()

    def next_revision(self) -> int:
        rows = self.rows()
        if not rows:
            return 1
        return max(int(row["revision"]) for row in rows) + 1

    def rows(self) -> list[dict[str, str]]:
        if not self.results_path.exists():
            return []
        with self.results_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            return list(reader)

    def append(self, record: RunRecord, trace: dict) -> None:
        with self.results_path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=RESULTS_HEADER, delimiter="\t")
            writer.writerow(asdict(record))
        trace_path = self.traces_dir / f"run_{record.revision:04d}.json"
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")

    def best_accepted(self) -> dict[str, str] | None:
        accepted = [row for row in self.rows() if row["decision"] == "accept"]
        if not accepted:
            return None
        accepted.sort(key=lambda row: int(row["revision"]))
        return accepted[-1]
