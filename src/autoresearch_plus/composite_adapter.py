from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .adapter import TaskAdapter
from .models import AcceptedState, Candidate, EvalResult, Proposal


@dataclass(frozen=True)
class CompositeStage:
    name: str
    adapter: TaskAdapter
    score_offset: float = 0.0
    score_weight: float = 1.0

    def normalized_score(self, result: EvalResult) -> float:
        return (result.score - self.score_offset) * self.score_weight


@dataclass(frozen=True)
class CompositeScoringResult:
    stage_results: list[dict[str, float | str]]
    integration_bonus: float
    total_score: float
    policy_name: str


class CompositeTaskAdapter(TaskAdapter):
    name = "composite"

    def __init__(
        self,
        root: Path,
        stages: list[CompositeStage],
        *,
        adapter_name: str,
        scope_label: str | None = None,
        stage_order: list[str] | None = None,
        integration_fn: Callable[[dict[str, EvalResult]], float] | None = None,
        saturation_fn: Callable[[list[dict[str, float | str]]], set[str]] | None = None,
    ) -> None:
        self.root = root
        stage_map = {stage.name: stage for stage in stages}
        if stage_order:
            unknown = [name for name in stage_order if name not in stage_map]
            if unknown:
                raise ValueError(f"Unknown composite stage(s): {', '.join(unknown)}")
            self.stages = [stage_map[name] for name in stage_order]
        else:
            self.stages = stages
        self.name = adapter_name
        self._scope_label = scope_label or " + ".join(stage.adapter.scope_label for stage in self.stages)
        self._stage_by_name = {stage.name: stage for stage in self.stages}
        self._integration_fn = integration_fn
        self._saturation_fn = saturation_fn
        self._policy_name = "integration_threshold_bonus" if integration_fn is not None else "stage_sum_only"
        self._last_scoring_result: CompositeScoringResult | None = None

    @property
    def edit_scope(self) -> list[Path]:
        seen: set[str] = set()
        paths: list[Path] = []
        for stage in self.stages:
            for path in stage.adapter.edit_scope:
                key = str(path.resolve())
                if key not in seen:
                    seen.add(key)
                    paths.append(path)
        return paths

    @property
    def scope_label(self) -> str:
        return self._scope_label

    def load_accepted_state(self) -> AcceptedState:
        files: dict[str, str] = {}
        for stage in self.stages:
            files.update(stage.adapter.load_accepted_state().files)
        return AcceptedState(files=files, label=self.scope_label)

    def restore(self, accepted: AcceptedState) -> None:
        for rel_path, content in accepted.files.items():
            target = self.root / rel_path.replace("\\", "/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        current_scoring = self._score_stages()
        self._last_scoring_result = current_scoring
        saturated_stages = sorted(self._saturation_fn(current_scoring.stage_results)) if self._saturation_fn is not None else []
        stage_payloads: list[dict] = []
        stage_sequence: list[str] = []
        for index, stage in enumerate(self.stages):
            if stage.name in saturated_stages:
                continue
            stage_proposal = stage.adapter.propose(stage.adapter.load_accepted_state(), history, revision * 100 + index + 1)
            stage_sequence.append(stage.name)
            stage_payloads.append(
                {
                    "name": stage.name,
                    "summary": stage_proposal.summary,
                    "scope_label": stage_proposal.scope_label,
                    "metadata": stage_proposal.metadata,
                }
            )
        metadata = {
            "proposal_kind": "composite",
            "saturated_stages": saturated_stages,
            "stage_sequence": stage_sequence,
            "stages": stage_payloads,
        }
        if not stage_sequence:
            metadata["skip_evaluation"] = True
            metadata["skip_reason"] = "all_stages_saturated"
            return Proposal(summary="all stages saturated", scope_label=self.scope_label, metadata=metadata)
        return Proposal(summary=f"{self.name} composite proposal", scope_label=self.scope_label, metadata=metadata)

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        stage_candidates: list[dict] = []
        mutation_parts: list[str] = []
        applied_stage_names: list[str] = []
        for stage_payload in proposal.metadata.get("stages", []):
            stage_name = str(stage_payload["name"])
            stage = self._stage_by_name[stage_name]
            stage_proposal = Proposal(
                summary=str(stage_payload["summary"]),
                scope_label=str(stage_payload["scope_label"]),
                metadata=dict(stage_payload["metadata"]),
            )
            candidate = stage.adapter.materialize(stage.adapter.load_accepted_state(), stage_proposal)
            applied_stage_names.append(stage_name)
            mutation_parts.append(str(candidate.metadata.get("mutation_summary", candidate.summary)))
            stage_candidates.append(
                {
                    "name": stage_name,
                    "summary": candidate.summary,
                    "metadata": candidate.metadata,
                }
            )
        metadata = {
            **proposal.metadata,
            "applied_stage_names": applied_stage_names,
            "stage_candidates": stage_candidates,
            "mutation_summary": " -> ".join(part for part in mutation_parts if part),
            "mutation_kind": "composite",
        }
        return Candidate(summary=proposal.summary, metadata=metadata)

    def _score_stages(self) -> CompositeScoringResult:
        total = 0.0
        status = "ok"
        stage_results: dict[str, EvalResult] = {}
        stage_summaries: list[dict[str, float | str]] = []
        for stage in self.stages:
            result = stage.adapter.evaluate()
            stage_results[stage.name] = result
            normalized = stage.normalized_score(result)
            total += normalized
            stage_summaries.append(
                {
                    "name": stage.name,
                    "status": result.status,
                    "raw_score": result.score,
                    "normalized_score": normalized,
                }
            )
            if result.status != "ok":
                status = "failed"
        integration_score = 0.0
        if status == "ok" and self._integration_fn is not None:
            integration_score = float(self._integration_fn(stage_results))
            total += integration_score
        return CompositeScoringResult(
            stage_results=stage_summaries,
            integration_bonus=integration_score,
            total_score=total,
            policy_name=self._policy_name,
        )

    def evaluate(self) -> EvalResult:
        scoring = self._score_stages()
        self._last_scoring_result = scoring
        output_lines = [
            f"{item['name']}:{item['status']}:raw={float(item['raw_score']):.6f}:normalized={float(item['normalized_score']):.6f}"
            for item in scoring.stage_results
        ]
        status = "ok" if all(item["status"] == "ok" for item in scoring.stage_results) else "failed"
        output_lines.append(f"integration_stage:{status}:score={scoring.integration_bonus:.6f}")
        return EvalResult(status=status, score=scoring.total_score, output="\n".join(output_lines))

    def _with_scoring(self, metadata: dict) -> dict:
        scoring = self._last_scoring_result or self._score_stages()
        return {
            **metadata,
            "scoring_policy": scoring.policy_name,
            "integration_bonus": scoring.integration_bonus,
            "stage_results": scoring.stage_results,
        }

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.status == "ok" and challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return self._with_scoring(
            {
            "stage_sequence": proposal.metadata.get("stage_sequence", []),
            "saturated_stages": proposal.metadata.get("saturated_stages", []),
            "stage_candidates": candidate.metadata.get("stage_candidates", []),
            }
        )
