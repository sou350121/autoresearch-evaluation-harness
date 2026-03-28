from __future__ import annotations

from dataclasses import dataclass, replace

from .models import Hypothesis


@dataclass(frozen=True)
class HypothesisMemoryStat:
    accepts: int = 0
    rejects: int = 0
    retained_accepts: int = 0


def summarize_hypothesis_memory(experiments: list[dict]) -> dict[str, HypothesisMemoryStat]:
    stats: dict[str, HypothesisMemoryStat] = {}
    for row in experiments:
        hypothesis_id = str(row.get("hypothesis_id", "")).strip()
        if not hypothesis_id:
            continue
        current = stats.get(hypothesis_id, HypothesisMemoryStat())
        outcome = str(row.get("outcome", ""))
        retained = bool(row.get("retained", False))
        accepts = current.accepts
        rejects = current.rejects
        retained_accepts = current.retained_accepts
        if outcome == "accept_candidate":
            accepts += 1
        elif outcome == "reject_candidate":
            rejects += 1
        if retained:
            retained_accepts += 1
        stats[hypothesis_id] = HypothesisMemoryStat(
            accepts=accepts,
            rejects=rejects,
            retained_accepts=retained_accepts,
        )
    return stats


def drop_pure_reject_hypotheses(
    hypotheses: list[Hypothesis],
    stats: dict[str, HypothesisMemoryStat],
) -> list[Hypothesis]:
    filtered: list[Hypothesis] = []
    for hypothesis in hypotheses:
        stat = stats.get(hypothesis.hypothesis_id)
        if stat and stat.rejects > 0 and stat.accepts == 0 and stat.retained_accepts == 0:
            continue
        filtered.append(hypothesis)
    return filtered


def prioritize_retained_hypotheses(
    hypotheses: list[Hypothesis],
    stats: dict[str, HypothesisMemoryStat],
) -> list[Hypothesis]:
    indexed = list(enumerate(hypotheses))
    indexed.sort(
        key=lambda item: (
            -(stats.get(item[1].hypothesis_id, HypothesisMemoryStat()).retained_accepts),
            item[0],
        )
    )
    return [hypothesis for _, hypothesis in indexed]


def select_hypothesis_beam(
    hypotheses: list[Hypothesis],
    stats: dict[str, HypothesisMemoryStat],
    *,
    width: int,
) -> list[Hypothesis]:
    if width <= 0:
        return []
    retained = prioritize_retained_hypotheses(
        [hypothesis for hypothesis in hypotheses if stats.get(hypothesis.hypothesis_id, HypothesisMemoryStat()).retained_accepts > 0],
        stats,
    )
    untried = [hypothesis for hypothesis in hypotheses if hypothesis.hypothesis_id not in stats]
    explored_non_retained = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.hypothesis_id in stats
        and stats.get(hypothesis.hypothesis_id, HypothesisMemoryStat()).retained_accepts == 0
    ]

    selected: list[Hypothesis] = []
    seen: set[str] = set()
    for group in (retained, untried, explored_non_retained):
        for hypothesis in group:
            if hypothesis.hypothesis_id in seen:
                continue
            selected.append(hypothesis)
            seen.add(hypothesis.hypothesis_id)
            if len(selected) >= width:
                return selected
    return selected


def label_hypothesis_beam_roles(
    hypotheses: list[Hypothesis],
    stats: dict[str, HypothesisMemoryStat],
) -> list[Hypothesis]:
    labeled: list[Hypothesis] = []
    for hypothesis in hypotheses:
        stat = stats.get(hypothesis.hypothesis_id, HypothesisMemoryStat())
        if stat.retained_accepts > 0:
            beam_role = "exploitation"
        elif hypothesis.hypothesis_id not in stats:
            beam_role = "exploration"
        else:
            beam_role = "followup"
        labeled.append(replace(hypothesis, metadata={**hypothesis.metadata, "beam_role": beam_role}))
    return labeled


def render_hypothesis_memory_summary(stats: dict[str, HypothesisMemoryStat]) -> str:
    if not stats:
        return "No prior hypothesis memory. Prefer exploration unless a retained method appears."
    ordered = sorted(
        stats.items(),
        key=lambda item: (-item[1].retained_accepts, -item[1].accepts, item[1].rejects, item[0]),
    )
    parts = [
        f"{hypothesis_id} retained_accepts={stat.retained_accepts} accepts={stat.accepts} rejects={stat.rejects}"
        for hypothesis_id, stat in ordered
    ]
    return (
        "Beam policy: use retained methods for exploitation and untried methods for exploration.\n"
        + "\n".join(parts)
    )
