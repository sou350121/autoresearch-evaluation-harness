from __future__ import annotations


def make_threshold_saturation_policy(thresholds: dict[str, float]):
    def policy(stage_results: list[dict[str, float | str]]) -> set[str]:
        saturated: set[str] = set()
        for item in stage_results:
            name = str(item["name"])
            raw_score = float(item["raw_score"])
            threshold = thresholds.get(name)
            if threshold is not None and raw_score >= threshold:
                saturated.add(name)
        return saturated

    return policy
