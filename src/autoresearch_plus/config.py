from __future__ import annotations

import tomllib
from pathlib import Path

from .models import MutationConfig, ProjectConfig


def load_project_config(root: Path) -> ProjectConfig:
    config_path = root / "config" / "project.toml"
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    mutation = MutationConfig(
        constant_names=list(data["mutation"]["constant_names"]),
        step_scale=float(data["mutation"]["step_scale"]),
        random_seed=int(data["mutation"]["random_seed"]),
    )
    return ProjectConfig(
        root=root,
        project_name=str(data["project_name"]),
        target_file=root / str(data["target_file"]),
        evaluation_command=str(data["evaluation_command"]),
        score_pattern=str(data["score_pattern"]),
        direction=str(data["direction"]),
        mutation=mutation,
    )
