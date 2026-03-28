from __future__ import annotations

from pathlib import Path

from .adapter import TaskAdapter
from .chunking import Chunk, derive_chunks
from .config import load_project_config
from .evaluator import EvaluationError, run_evaluation
from .models import AcceptedState, Candidate, EvalResult, ProjectConfig, Proposal
from .mutator import mutate_target_file
from .proposers import build_numeric_proposer


def _full_scope_chunk(source_text: str) -> Chunk:
    line_count = max(1, len(source_text.splitlines()))
    return Chunk(chunk_id="scope:full", focus_region="scope:full", start_line=1, end_line=line_count)


def _resolve_chunk_by_id(source_text: str, chunk_id: str) -> Chunk | None:
    for chunk in derive_chunks(source_text):
        if chunk.chunk_id == chunk_id:
            return chunk
    if chunk_id == "scope:full":
        return _full_scope_chunk(source_text)
    return None


class NumericDemoAdapter(TaskAdapter):
    name = "numeric_demo"

    def __init__(self, root: Path, config: ProjectConfig | None = None) -> None:
        self.root = root
        self.config = config or load_project_config(root)
        self.target = self.config.target_file
        self.proposer = build_numeric_proposer(self.config)

    @property
    def edit_scope(self) -> list[Path]:
        return list(self.config.edit_scope)

    @property
    def scope_label(self) -> str:
        return ",".join(str(path.relative_to(self.root)) for path in self.edit_scope)

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(
            files={str(path.relative_to(self.root)): path.read_text(encoding="utf-8") for path in self.edit_scope},
            label=self.scope_label,
        )

    def restore(self, accepted: AcceptedState) -> None:
        for rel_path, content in accepted.files.items():
            (self.root / rel_path).write_text(content, encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        return self.proposer.propose(self, accepted, history, revision)

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        mutation_steps = []
        mutation_summaries: list[str] = []
        mutation_kinds: list[str] = []
        chunk_id = str(proposal.metadata.get("chunk_id", "scope:full"))
        mutation_kind_weights = proposal.metadata.get("mutation_kind_weights")

        for step_iteration in proposal.metadata.get("step_iterations", []):
            active_chunk = _resolve_chunk_by_id(self.target.read_text(encoding="utf-8"), chunk_id) if self.config.chunking.enabled else None
            mutation_result = mutate_target_file(
                self.target,
                self.config.mutation,
                int(step_iteration),
                chunk=active_chunk,
                mutation_kind_weights=mutation_kind_weights if self.config.prior.enabled else None,
            )
            mutation_steps.append(mutation_result.details)
            mutation_summaries.append(mutation_result.summary)
            step_kind = str(mutation_result.details.get("kind", ""))
            mutation_kinds.append(step_kind)
            if step_kind != "constant":
                break

        summary = " | ".join(mutation_summaries)
        return Candidate(
            summary=summary,
            metadata={
                **proposal.metadata,
                "mutation_steps": mutation_steps,
                "mutation_summary": summary,
                "mutation_kind": ",".join(mutation_kinds),
                "final_diff": mutation_steps[-1].get("diff", "") if mutation_steps else "",
            },
        )

    def evaluate(self) -> EvalResult:
        try:
            score, output = run_evaluation(self.config)
            return EvalResult(status="ok", score=score, output=output)
        except EvaluationError as exc:
            return EvalResult(status="failed", score=float("-inf"), output=str(exc))

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        if challenger.status != "ok":
            return False
        if self.config.direction == "maximize":
            return challenger.score > incumbent.score
        return challenger.score < incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {
            "selected_chunk": {
                "chunk_id": proposal.metadata.get("chunk_id", ""),
                "span": proposal.metadata.get("chunk_span", ""),
            },
            "prior_snapshot": {
                "basis_revision": proposal.metadata.get("prior_basis_revision"),
                "prior_weight": proposal.metadata.get("prior_weight"),
            },
            "mutation_steps": candidate.metadata.get("mutation_steps", []),
        }
