from __future__ import annotations

import tomllib
from pathlib import Path

from .models import ChunkingConfig, MutationConfig, PriorConfig, ProjectConfig


def load_project_config(root: Path) -> ProjectConfig:
    config_path = root / "config" / "project.toml"
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    mutation = MutationConfig(
        mode=str(data["mutation"]["mode"]),
        max_constant_delta=float(data["mutation"]["max_constant_delta"]),
        random_seed=int(data["mutation"]["random_seed"]),
        allowed_math_funcs=list(data["mutation"]["allowed_math_funcs"]),
        allowed_binary_ops=list(data["mutation"]["allowed_binary_ops"]),
    )
    chunking_data = data.get("chunking", {})
    prior_data = data.get("prior", {})
    return ProjectConfig(
        root=root,
        project_name=str(data["project_name"]),
        adapter_name=str(data.get("adapter", "numeric_demo")),
        proposer_name=str(data.get("proposer", "chunked_prior")),
        composite_stage_order=[str(name) for name in data.get("composite_stage_order", [])],
        edit_scope=[root / str(path) for path in data.get("edit_scope", [str(data["target_file"])])],
        target_file=root / str(data["target_file"]),
        evaluation_command=str(data["evaluation_command"]),
        score_pattern=str(data["score_pattern"]),
        direction=str(data["direction"]),
        mutation=mutation,
        chunking=ChunkingConfig(
            enabled=bool(chunking_data.get("enabled", True)),
            strategy=str(chunking_data.get("strategy", "ast_assignments")),
            chunk_budget=int(chunking_data.get("chunk_budget", 1)),
        ),
        prior=PriorConfig(
            enabled=bool(prior_data.get("enabled", True)),
            lookback=int(prior_data.get("lookback", 6)),
            decay=float(prior_data.get("decay", 0.8)),
            accept_boost=float(prior_data.get("accept_boost", 1.5)),
            reject_penalty=float(prior_data.get("reject_penalty", 1.0)),
            min_weight=float(prior_data.get("min_weight", 0.2)),
        ),
        max_fix_budget=(int(data["max_fix_budget"]) if "max_fix_budget" in data else None),
        llm_memory_enabled=bool(data.get("llm_memory_enabled", True)),
        llm_retry_enabled=bool(data.get("llm_retry_enabled", True)),
    )
