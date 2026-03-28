from __future__ import annotations

import argparse
from pathlib import Path

from .benchmark import render_benchmark_summary, run_ab_benchmark, summarize_trials
from .ledger import RunLedger
from .loop import run_baseline, run_search


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_baseline() -> None:
    record = run_baseline(_repo_root())
    print(f"Accepted baseline revision {record.revision} with score {record.score:.6f}")


def cmd_search(iterations: int) -> None:
    records = run_search(_repo_root(), iterations)
    for record in records:
        print(
            f"revision={record.revision} decision={record.decision} "
            f"score={record.score:.6f} chunk={record.chunk_id} "
            f"prior={record.prior_weight} mutation={record.mutation}"
        )


def _render_composite_summary(trace: dict, label: str = "composite_summary") -> str | None:
    adapter_trace = trace.get("adapter_trace", {})
    stage_results = adapter_trace.get("stage_results", [])
    if not stage_results:
        return None
    saturated = adapter_trace.get("saturated_stages", [])
    saturated_text = ",".join(str(item) for item in saturated) if saturated else "-"
    stages = " ".join(
        f"{item['name']}(raw={float(item['raw_score']):.6f} "
        f"normalized={float(item['normalized_score']):.6f} status={item['status']})"
        for item in stage_results
    )
    return (
        f"{label} "
        f"scoring_policy={adapter_trace.get('scoring_policy', '')} "
        f"integration_bonus={float(adapter_trace.get('integration_bonus', 0.0)):.6f} "
        f"saturated_stages={saturated_text} "
        f"stages={stages}"
    )


def _render_method_summary(trace: dict, label: str = "method_summary") -> str | None:
    proposal = trace.get("proposal", {})
    hypothesis = proposal.get("hypothesis", {})
    hypothesis_id = hypothesis.get("hypothesis_id")
    if not hypothesis_id:
        return None
    beam_role = hypothesis.get("beam_role") or proposal.get("beam_role", "")
    operator_family = hypothesis.get("operator_family", "")
    target_locus = hypothesis.get("target_locus", "")
    return (
        f"{label} "
        f"hypothesis={hypothesis_id} "
        f"beam_role={beam_role} "
        f"operator_family={operator_family} "
        f"target_locus={target_locus}"
    )


def _render_branch_beam_summary(trace: dict, label: str = "branch_beam_summary") -> str | None:
    branch_results = trace.get("branch_results", [])
    if not branch_results:
        return None
    parts = []
    for item in branch_results:
        hypothesis = item.get("hypothesis", {})
        hypothesis_id = hypothesis.get("hypothesis_id")
        if not hypothesis_id:
            continue
        beam_role = hypothesis.get("metadata", {}).get("beam_role") or hypothesis.get("beam_role", "")
        score = float(item.get("score", 0.0))
        parts.append(f"{hypothesis_id}:{beam_role}:{score:.6f}")
    if not parts:
        return None
    return f"{label} " + " ".join(parts)


def cmd_report() -> None:
    ledger = RunLedger(_repo_root())
    best = ledger.best_accepted()
    if not best:
        print("No accepted runs yet.")
        return
    print(
        "best_accepted "
        f"revision={best['revision']} "
        f"score={best['score']} "
        f"git_commit={best['git_commit']} "
        f"git_dirty={best['git_dirty']} "
        f"chunk={best['chunk_id']} "
        f"prior={best['prior_weight']} "
        f"summary={best['summary']}"
    )
    trace = ledger.load_trace(int(best["revision"]))
    composite_summary = _render_composite_summary(trace)
    if composite_summary:
        print(composite_summary)
    method_summary = _render_method_summary(trace)
    if method_summary:
        print(method_summary)
    branch_beam_summary = _render_branch_beam_summary(trace)
    if branch_beam_summary:
        print(branch_beam_summary)
    latest_rejected = ledger.latest_rejected()
    if latest_rejected:
        print(
            "latest_rejected "
            f"revision={latest_rejected['revision']} "
            f"score={latest_rejected['score']} "
            f"summary={latest_rejected['summary']}"
        )
        rejected_trace = ledger.load_trace(int(latest_rejected["revision"]))
        rejected_summary = _render_composite_summary(rejected_trace, label="latest_rejected_composite_summary")
        if rejected_summary:
            print(rejected_summary)
        rejected_method_summary = _render_method_summary(rejected_trace, label="latest_rejected_method_summary")
        if rejected_method_summary:
            print(rejected_method_summary)
        rejected_branch_beam_summary = _render_branch_beam_summary(
            rejected_trace, label="latest_rejected_branch_beam_summary"
        )
        if rejected_branch_beam_summary:
            print(rejected_branch_beam_summary)


def cmd_benchmark(iterations: int, trials: int, tasks: list[str] | None = None) -> None:
    trials_data = run_ab_benchmark(_repo_root(), iterations, trials, tasks=tasks)
    summary = summarize_trials(trials_data)
    print(render_benchmark_summary(summary, iterations=iterations, trials=trials))


def main() -> None:
    parser = argparse.ArgumentParser(prog="autoresearch-plus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("baseline")

    search = subparsers.add_parser("search")
    search.add_argument("--iterations", type=int, default=5)

    subparsers.add_parser("report")

    benchmark = subparsers.add_parser("benchmark")
    benchmark.add_argument("--iterations", type=int, default=8)
    benchmark.add_argument("--trials", type=int, default=2)
    benchmark.add_argument("--task", action="append", dest="tasks")

    args = parser.parse_args()
    if args.command == "baseline":
        cmd_baseline()
    elif args.command == "search":
        cmd_search(args.iterations)
    elif args.command == "report":
        cmd_report()
    elif args.command == "benchmark":
        cmd_benchmark(args.iterations, args.trials, args.tasks)


if __name__ == "__main__":
    main()
