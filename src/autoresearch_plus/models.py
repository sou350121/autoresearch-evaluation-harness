from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MutationConfig:
    mode: str
    max_constant_delta: float
    random_seed: int
    allowed_math_funcs: list[str]
    allowed_binary_ops: list[str]


@dataclass(frozen=True)
class ChunkingConfig:
    enabled: bool
    strategy: str
    chunk_budget: int


@dataclass(frozen=True)
class PriorConfig:
    enabled: bool
    lookback: int
    decay: float
    accept_boost: float
    reject_penalty: float
    min_weight: float


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    project_name: str
    adapter_name: str
    proposer_name: str
    edit_scope: list[Path]
    target_file: Path
    evaluation_command: str
    score_pattern: str
    direction: str
    mutation: MutationConfig
    chunking: ChunkingConfig
    prior: PriorConfig
    composite_stage_order: list[str] = field(default_factory=list)
    max_fix_budget: int | None = None
    llm_memory_enabled: bool = True
    llm_retry_enabled: bool = True


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    focus_region: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class PriorState:
    chunk_weights: dict[str, float]
    mutation_kind_weights: dict[str, float]
    basis_revision: int


@dataclass(frozen=True)
class AcceptedState:
    files: dict[str, str]
    label: str


@dataclass(frozen=True)
class Proposal:
    summary: str
    scope_label: str
    metadata: dict


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    problem_frame: str
    target_locus: str
    mechanism_guess: str
    operator_family: str
    expected_signal: str
    risk: str
    patch_budget: int
    fix_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Candidate:
    summary: str
    metadata: dict


@dataclass(frozen=True)
class EvalResult:
    status: str
    score: float
    output: str


@dataclass
class RunRecord:
    revision: int
    base_revision: int | None
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
    git_dirty: bool
    chunk_id: str = ""
    chunk_span: str = ""
    mutation_kind: str = ""
    prior_weight: float | None = None
    prior_basis_revision: int | None = None
