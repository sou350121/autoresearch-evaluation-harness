from __future__ import annotations

import random
from dataclasses import dataclass

from .chunking import Chunk, choose_chunk, derive_chunks
from .models import AcceptedState, ProjectConfig, Proposal
from .prior import build_prior

MUTATION_KINDS = ["constant", "math_func", "binary_op"]


def _full_scope_chunk(source_text: str) -> Chunk:
    line_count = max(1, len(source_text.splitlines()))
    return Chunk(chunk_id="scope:full", focus_region="scope:full", start_line=1, end_line=line_count)


@dataclass(frozen=True)
class NumericProposer:
    name: str
    config: ProjectConfig

    def _chunks(self, source_text: str) -> list[Chunk]:
        chunks = derive_chunks(source_text) if self.config.chunking.enabled else [_full_scope_chunk(source_text)]
        return chunks or [_full_scope_chunk(source_text)]


@dataclass(frozen=True)
class SingleStepRandomNumericProposer(NumericProposer):
    def propose(self, adapter, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        source_text = adapter.target.read_text(encoding="utf-8")
        chunks = self._chunks(source_text)
        rng = random.Random(self.config.mutation.random_seed + revision * 17)
        selected_chunk, _ = choose_chunk(chunks, {chunk.chunk_id: 1.0 for chunk in chunks}, rng)
        return Proposal(
            summary=f"single-step proposal for {selected_chunk.chunk_id}",
            scope_label=adapter.scope_label,
            metadata={
                "proposal_kind": self.name,
                "chunk_id": selected_chunk.chunk_id,
                "chunk_span": f"{selected_chunk.start_line}-{selected_chunk.end_line}",
                "prior_weight": 1.0,
                "prior_basis_revision": 0,
                "mutation_kind_weights": None,
                "step_iterations": [revision * 100],
            },
        )


@dataclass(frozen=True)
class ChunkedPriorNumericProposer(NumericProposer):
    def propose(self, adapter, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        source_text = adapter.target.read_text(encoding="utf-8")
        chunks = self._chunks(source_text)
        if self.config.prior.enabled:
            prior = build_prior(
                rows=history,
                chunk_ids=[chunk.chunk_id for chunk in chunks],
                mutation_kinds=MUTATION_KINDS,
                lookback=self.config.prior.lookback,
                decay=self.config.prior.decay,
                accept_boost=self.config.prior.accept_boost,
                reject_penalty=self.config.prior.reject_penalty,
                min_weight=self.config.prior.min_weight,
            )
        else:
            prior = build_prior(
                rows=[],
                chunk_ids=[chunk.chunk_id for chunk in chunks],
                mutation_kinds=MUTATION_KINDS,
                lookback=0,
                decay=1.0,
                accept_boost=1.0,
                reject_penalty=1.0,
                min_weight=1.0,
            )
        rng = random.Random(self.config.mutation.random_seed + revision * 17)
        selected_chunk, prior_weight = choose_chunk(chunks, prior.chunk_weights, rng)
        chunk_budget = max(1, self.config.chunking.chunk_budget if self.config.chunking.enabled else 1)
        return Proposal(
            summary=f"chunked-prior proposal for {selected_chunk.chunk_id}",
            scope_label=adapter.scope_label,
            metadata={
                "proposal_kind": self.name,
                "chunk_id": selected_chunk.chunk_id,
                "chunk_span": f"{selected_chunk.start_line}-{selected_chunk.end_line}",
                "prior_weight": prior_weight,
                "prior_basis_revision": prior.basis_revision,
                "mutation_kind_weights": prior.mutation_kind_weights,
                "step_iterations": [revision * 100 + step for step in range(chunk_budget)],
            },
        )


def build_numeric_proposer(config: ProjectConfig) -> NumericProposer:
    if config.proposer_name == "single_step_random":
        return SingleStepRandomNumericProposer(name="single_step_random", config=config)
    if config.proposer_name == "chunked_prior":
        return ChunkedPriorNumericProposer(name="chunked_prior", config=config)
    raise RuntimeError(f"Unsupported numeric proposer: {config.proposer_name}")
