from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .models import RunRecord


RESULTS_HEADER = [
    "revision",
    "base_revision",
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
    "git_dirty",
    "chunk_id",
    "chunk_span",
    "mutation_kind",
    "prior_weight",
    "prior_basis_revision",
]


class RunLedger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.runs_dir = root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.results_path = self.runs_dir / "results.tsv"
        self.experiment_memory_path = self.runs_dir / "experiment_memory.jsonl"
        self.traces_dir = self.runs_dir / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir = self.runs_dir / "accepted_snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        if not self.results_path.exists():
            with self.results_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=RESULTS_HEADER, delimiter="\t")
                writer.writeheader()
        else:
            self._migrate_results_if_needed()

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
            rows = list(reader)
        normalized: list[dict[str, str]] = []
        for row in rows:
            merged = {header: "" for header in RESULTS_HEADER}
            merged.update(row)
            if not merged["git_dirty"]:
                merged["git_dirty"] = "unknown"
            normalized.append(merged)
        return normalized

    def append(self, record: RunRecord, trace: dict) -> None:
        with self.results_path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=RESULTS_HEADER, delimiter="\t")
            writer.writerow(asdict(record))
        trace_path = self.traces_dir / f"run_{record.revision:04d}.json"
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")

    def append_experiment(self, entry: dict) -> None:
        with self.experiment_memory_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def load_experiments(self) -> list[dict]:
        if not self.experiment_memory_path.exists():
            return []
        rows: list[dict] = []
        for line in self.experiment_memory_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
        return rows

    def save_snapshot(self, revision: int, target_file: str, content: str) -> Path:
        target_name = Path(target_file).name
        snapshot_path = self.snapshots_dir / f"run_{revision:04d}_{target_name}"
        snapshot_path.write_text(content, encoding="utf-8")
        return snapshot_path

    def save_scope_snapshot(self, revision: int, files: dict[str, str]) -> Path:
        snapshot_root = self.snapshots_dir / f"run_{revision:04d}"
        snapshot_root.mkdir(parents=True, exist_ok=True)
        for rel_path, content in files.items():
            target = snapshot_root / Path(rel_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return snapshot_root

    def load_snapshot(self, revision: int, target_file: str) -> str:
        target_name = Path(target_file).name
        snapshot_path = self.snapshots_dir / f"run_{revision:04d}_{target_name}"
        return snapshot_path.read_text(encoding="utf-8")

    def load_scope_snapshot(self, revision: int) -> dict[str, str]:
        snapshot_root = self.snapshots_dir / f"run_{revision:04d}"
        files: dict[str, str] = {}
        if not snapshot_root.exists():
            return files
        for path in snapshot_root.rglob("*"):
            if path.is_file():
                files[str(path.relative_to(snapshot_root))] = path.read_text(encoding="utf-8")
        return files

    def load_trace(self, revision: int) -> dict:
        trace_path = self.traces_dir / f"run_{revision:04d}.json"
        if not trace_path.exists():
            return {}
        return json.loads(trace_path.read_text(encoding="utf-8"))

    def best_accepted(self) -> dict[str, str] | None:
        accepted = [row for row in self.rows() if row["decision"] == "accept"]
        if not accepted:
            return None
        accepted.sort(key=lambda row: int(row["revision"]))
        return accepted[-1]

    def latest_rejected(self) -> dict[str, str] | None:
        rejected = [row for row in self.rows() if row["decision"] == "reject"]
        if not rejected:
            return None
        rejected.sort(key=lambda row: int(row["revision"]))
        return rejected[-1]

    def _migrate_results_if_needed(self) -> None:
        with self.results_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            fieldnames = reader.fieldnames or []
            rows = list(reader)
        if fieldnames == RESULTS_HEADER:
            return

        normalized: list[dict[str, str]] = []
        for row in rows:
            merged = {header: "" for header in RESULTS_HEADER}
            merged.update({key: value for key, value in row.items() if key})
            if not merged["git_dirty"]:
                merged["git_dirty"] = "unknown"
            normalized.append(merged)

        with self.results_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=RESULTS_HEADER, delimiter="\t")
            writer.writeheader()
            writer.writerows(normalized)
