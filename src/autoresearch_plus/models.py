from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MutationConfig:
    constant_names: list[str]
    step_scale: float
    random_seed: int


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    project_name: str
    target_file: Path
    evaluation_command: str
    score_pattern: str
    direction: str
    mutation: MutationConfig


@dataclass
class RunRecord:
    revision: int
    decision: str
    score: float
    previous_score: float | None
    metric_delta: float | None
    status: str
    summary: str
    mutation: str
    target_file: str
    git_branch: str
    git_commit: str
