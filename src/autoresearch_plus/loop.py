from __future__ import annotations

from pathlib import Path

from .config import load_project_config
from .evaluator import EvaluationError, run_evaluation
from .git_ops import current_branch, current_commit
from .ledger import RunLedger
from .models import RunRecord
from .mutator import mutate_target_file


def _delta(previous_score: float | None, current_score: float) -> float | None:
    if previous_score is None:
        return None
    return current_score - previous_score


def _is_improvement(direction: str, previous_score: float | None, current_score: float) -> bool:
    if previous_score is None:
        return True
    if direction == "maximize":
        return current_score > previous_score
    return current_score < previous_score


def run_baseline(root: Path) -> RunRecord:
    config = load_project_config(root)
    ledger = RunLedger(root)
    revision = ledger.next_revision()
    score, output = run_evaluation(config)
    record = RunRecord(
        revision=revision,
        decision="accept",
        score=score,
        previous_score=None,
        metric_delta=None,
        status="ok",
        summary="Baseline accepted",
        mutation="baseline",
        target_file=str(config.target_file.relative_to(root)),
        git_branch=current_branch(root),
        git_commit=current_commit(root),
    )
    trace = {
        "mode": "baseline",
        "score": score,
        "output": output,
    }
    ledger.append(record, trace)
    return record


def run_search(root: Path, iterations: int) -> list[RunRecord]:
    config = load_project_config(root)
    ledger = RunLedger(root)
    accepted = ledger.best_accepted()
    if accepted is None:
        raise RuntimeError("No accepted baseline found. Run baseline first.")

    accepted_score = float(accepted["score"])
    accepted_snapshot = config.target_file.read_text(encoding="utf-8")
    records: list[RunRecord] = []

    for offset in range(iterations):
        revision = ledger.next_revision()
        original, updated, mutation_summary = mutate_target_file(config.target_file, config.mutation, revision)
        try:
            score, output = run_evaluation(config)
            improved = _is_improvement(config.direction, accepted_score, score)
            if improved:
                decision = "accept"
                summary = "Accepted: score improved"
                accepted_score = score
                accepted_snapshot = updated
            else:
                decision = "reject"
                summary = "Rejected: no improvement"
                config.target_file.write_text(accepted_snapshot, encoding="utf-8")
        except EvaluationError as exc:
            score = accepted_score
            output = str(exc)
            decision = "reject"
            summary = "Rejected: evaluation failed"
            config.target_file.write_text(accepted_snapshot, encoding="utf-8")

        record = RunRecord(
            revision=revision,
            decision=decision,
            score=score,
            previous_score=float(accepted["score"]) if accepted else None,
            metric_delta=_delta(float(accepted["score"]), score) if accepted else None,
            status="ok" if decision != "reject" or "failed" not in summary.lower() else "failed",
            summary=summary,
            mutation=mutation_summary,
            target_file=str(config.target_file.relative_to(root)),
            git_branch=current_branch(root),
            git_commit=current_commit(root),
        )
        trace = {
            "mode": "search",
            "revision": revision,
            "mutation": mutation_summary,
            "decision": decision,
            "score": score,
            "accepted_score_before_run": float(accepted["score"]),
            "output": output,
        }
        ledger.append(record, trace)
        records.append(record)
        if decision == "accept":
            accepted = {
                **accepted,
                "score": str(score),
                "revision": str(revision),
            }
        else:
            config.target_file.write_text(accepted_snapshot, encoding="utf-8")

    return records
