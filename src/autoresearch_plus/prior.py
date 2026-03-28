from __future__ import annotations

from .models import PriorState


def _metric_delta(row: dict[str, str]) -> float:
    raw = row.get("metric_delta", "") or "0"
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _revision(row: dict[str, str]) -> int:
    raw = row.get("revision", "") or "0"
    try:
        return int(raw)
    except ValueError:
        return 0


def build_prior(
    rows: list[dict[str, str]],
    chunk_ids: list[str],
    mutation_kinds: list[str],
    lookback: int,
    decay: float,
    accept_boost: float,
    reject_penalty: float,
    min_weight: float,
) -> PriorState:
    chunk_weights = {chunk_id: min_weight for chunk_id in chunk_ids}
    mutation_kind_weights = {kind: min_weight for kind in mutation_kinds}
    ranked = sorted(rows, key=_revision, reverse=True)[:lookback]
    basis_revision = max((_revision(row) for row in ranked), default=0)

    for rank, row in enumerate(ranked):
        magnitude = max(abs(_metric_delta(row)), 0.05)
        scale = decay**rank
        effect = magnitude * scale
        decision = row.get("decision", "")
        signed_effect = effect * accept_boost if decision == "accept" else -effect * reject_penalty

        chunk_id = row.get("chunk_id", "")
        if chunk_id in chunk_weights:
            chunk_weights[chunk_id] = max(min_weight, chunk_weights[chunk_id] + signed_effect)

        mutation_kind = row.get("mutation_kind", "")
        if mutation_kind in mutation_kind_weights:
            mutation_kind_weights[mutation_kind] = max(
                min_weight,
                mutation_kind_weights[mutation_kind] + signed_effect,
            )

    return PriorState(
        chunk_weights=chunk_weights,
        mutation_kind_weights=mutation_kind_weights,
        basis_revision=basis_revision,
    )
