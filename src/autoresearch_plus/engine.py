from __future__ import annotations

import json
from pathlib import Path

from .adapter import TaskAdapter
from .git_ops import commit_paths, current_branch, current_commit, is_dirty
from .ledger import RunLedger
from .models import EvalResult, RunRecord


def _delta(previous_score: float | None, current_score: float) -> float | None:
    if previous_score is None:
        return None
    return current_score - previous_score


def _scope_snapshot(ledger: RunLedger, revision: int, adapter: TaskAdapter) -> None:
    ledger.save_scope_snapshot(
        revision,
        {str(path.relative_to(ledger.root)): path.read_text(encoding="utf-8") for path in adapter.edit_scope},
    )


def _serialize_hypothesis(hypothesis) -> dict:
    return {
        "hypothesis_id": str(hypothesis.hypothesis_id),
        "problem_frame": str(hypothesis.problem_frame),
        "target_locus": str(hypothesis.target_locus),
        "mechanism_guess": str(hypothesis.mechanism_guess),
        "operator_family": str(hypothesis.operator_family),
        "expected_signal": str(hypothesis.expected_signal),
        "risk": str(hypothesis.risk),
        "patch_budget": int(hypothesis.patch_budget),
        "fix_ids": [str(fix_id) for fix_id in hypothesis.fix_ids],
        "metadata": dict(hypothesis.metadata),
    }


def run_baseline_with_adapter(root: Path, adapter: TaskAdapter, ledger: RunLedger | None = None) -> RunRecord:
    active_ledger = ledger or RunLedger(root)
    accepted = adapter.load_accepted_state()
    revision = active_ledger.next_revision()
    result = adapter.evaluate()
    _scope_snapshot(active_ledger, revision, adapter)
    record = RunRecord(
        revision=revision,
        base_revision=None,
        decision="accept",
        score=result.score,
        previous_score=None,
        metric_delta=None,
        status=result.status,
        summary="Baseline accepted",
        mutation="baseline",
        target_file=accepted.label,
        git_branch=current_branch(root),
        git_commit=current_commit(root),
        git_dirty=is_dirty(root),
    )
    active_ledger.append(record, {"mode": "baseline", "score": result.score, "output": result.output})
    return record


def run_search_with_adapter(root: Path, adapter: TaskAdapter, ledger: RunLedger | None = None, iterations: int = 1) -> list[RunRecord]:
    active_ledger = ledger or RunLedger(root)
    accepted_row = active_ledger.best_accepted()
    if accepted_row is None:
        raise RuntimeError("No accepted baseline found. Run baseline first.")

    accepted_revision = int(accepted_row["revision"])
    accepted_score = float(accepted_row["score"])
    accepted_snapshot = active_ledger.load_scope_snapshot(accepted_revision)
    accepted_state = adapter.load_accepted_state()
    for rel_path, content in accepted_snapshot.items():
        (root / rel_path).write_text(content, encoding="utf-8")
    accepted_eval = EvalResult(status="ok", score=accepted_score, output="")
    records: list[RunRecord] = []
    history = active_ledger.rows()

    for _ in range(iterations):
        revision = active_ledger.next_revision()
        previous_score = accepted_eval.score
        base_revision = int(accepted_row["revision"]) if accepted_row else None
        retry_trace = None
        branch_results = None

        hypotheses_fn = getattr(adapter, "propose_hypotheses", None)
        proposal_from_hypothesis_fn = getattr(adapter, "proposal_from_hypothesis", None)
        if callable(hypotheses_fn) and callable(proposal_from_hypothesis_fn):
            hypotheses = hypotheses_fn(accepted_state, history, revision)
            branch_results = []
            best_branch = None
            first_branch = None
            for branch_index, hypothesis in enumerate(hypotheses[:2], start=1):
                branch_id = f"branch-{branch_index}"
                adapter.restore(accepted_state)
                proposal = proposal_from_hypothesis_fn(hypothesis, accepted_state, history, revision, branch_id)
                candidate = adapter.materialize(accepted_state, proposal)
                result = accepted_eval if proposal.metadata.get("skip_evaluation") else adapter.evaluate()
                improved = result.status == "ok" and adapter.is_better(accepted_eval, result)
                branch_payload = {
                    "branch_id": branch_id,
                    "hypothesis": _serialize_hypothesis(hypothesis),
                    "proposal": proposal.metadata,
                    "candidate": candidate.metadata,
                    "score": result.score,
                    "status": result.status,
                    "improved": improved,
                }
                branch_results.append(branch_payload)
                active_ledger.append_experiment(
                    {
                        "revision": revision,
                        "parent_revision": base_revision,
                        "branch_id": branch_id,
                        "hypothesis_id": str(hypothesis.hypothesis_id),
                        "target_locus": str(hypothesis.target_locus),
                        "operator_family": str(hypothesis.operator_family),
                        "claimed_mechanism": str(hypothesis.mechanism_guess),
                        "expected_signal": str(hypothesis.expected_signal),
                        "risk": str(hypothesis.risk),
                        "candidate_summary": candidate.summary,
                        "mutation_summary": candidate.metadata.get("mutation_summary", ""),
                        "score": result.score,
                        "score_delta": _delta(previous_score, result.score),
                        "outcome": "accept_candidate" if improved else "reject_candidate",
                        "retained": False,
                    }
                )
                if improved and (best_branch is None or result.score > best_branch["result"].score):
                    best_branch = {
                        "hypothesis": hypothesis,
                        "proposal": proposal,
                        "candidate": candidate,
                        "result": result,
                    }
                if first_branch is None:
                    first_branch = {
                        "proposal": proposal,
                        "candidate": candidate,
                        "result": result,
                    }
            if best_branch is not None:
                proposal = best_branch["proposal"]
                candidate = best_branch["candidate"]
                result = best_branch["result"]
                decision = "accept"
                summary = "Accepted: hypothesis branch improved"
                accepted_state = adapter.promote(candidate)
                accepted_eval = result
                _scope_snapshot(active_ledger, revision, adapter)
                git_commit = commit_paths(root, adapter.edit_scope, f"accept revision {revision}: {proposal.summary}")
                accepted_row = {**accepted_row, "revision": str(revision), "score": str(result.score), "git_commit": git_commit}
                experiments = active_ledger.load_experiments()
                if experiments:
                    for index in range(len(experiments) - 1, -1, -1):
                        row = experiments[index]
                        if int(row.get("revision", -1)) != revision:
                            continue
                        if str(row.get("branch_id", "")) != str(best_branch["proposal"].metadata.get("branch_id", "")):
                            continue
                        row["retained"] = True
                        active_ledger.experiment_memory_path.write_text(
                            "\n".join(json.dumps(item, ensure_ascii=False) for item in experiments) + "\n",
                            encoding="utf-8",
                        )
                        break
            else:
                adapter.restore(accepted_state)
                proposal = first_branch["proposal"]
                candidate = first_branch["candidate"]
                result = first_branch["result"]
                decision = "reject"
                summary = "Rejected: no hypothesis branch improved"
                git_commit = current_commit(root)
        else:
            adapter.restore(accepted_state)
            proposal = adapter.propose(accepted_state, history, revision)
            candidate = adapter.materialize(accepted_state, proposal)
            if proposal.metadata.get("skip_evaluation"):
                result = accepted_eval
                decision = "reject"
                summary = f"Rejected: {proposal.metadata.get('skip_reason', 'proposal skipped')}"
                adapter.restore(accepted_state)
                git_commit = current_commit(root)
            else:
                result = adapter.evaluate()
                if result.status == "ok" and adapter.is_better(accepted_eval, result):
                    decision = "accept"
                    summary = "Accepted: score improved"
                    accepted_state = adapter.promote(candidate)
                    accepted_eval = result
                    _scope_snapshot(active_ledger, revision, adapter)
                    git_commit = commit_paths(root, adapter.edit_scope, f"accept revision {revision}: {proposal.summary}")
                    accepted_row = {**accepted_row, "revision": str(revision), "score": str(result.score), "git_commit": git_commit}
                else:
                    adapter.restore(accepted_state)
                    retry_proposal = None
                    retry_fn = getattr(adapter, "retry_after_reject", None)
                    if callable(retry_fn):
                        retry_proposal = retry_fn(accepted_state, history, revision, proposal, result)
                    if retry_proposal is not None:
                        retry_candidate = adapter.materialize(accepted_state, retry_proposal)
                        retry_result = adapter.evaluate()
                        retry_trace = {
                            "proposal": retry_proposal.metadata,
                            "candidate": retry_candidate.metadata,
                            "score": retry_result.score,
                            "status": retry_result.status,
                            "output": retry_result.output,
                        }
                        if retry_result.status == "ok" and adapter.is_better(accepted_eval, retry_result):
                            proposal = retry_proposal
                            candidate = retry_candidate
                            result = retry_result
                            decision = "accept"
                            summary = "Accepted: retry score improved"
                            accepted_state = adapter.promote(candidate)
                            accepted_eval = result
                            _scope_snapshot(active_ledger, revision, adapter)
                            git_commit = commit_paths(root, adapter.edit_scope, f"accept revision {revision}: {proposal.summary}")
                            accepted_row = {**accepted_row, "revision": str(revision), "score": str(result.score), "git_commit": git_commit}
                        else:
                            result = retry_result
                            decision = "reject"
                            summary = "Rejected: no improvement" if result.status == "ok" else "Rejected: evaluation failed"
                            adapter.restore(accepted_state)
                            git_commit = current_commit(root)
                    else:
                        decision = "reject"
                        summary = "Rejected: no improvement" if result.status == "ok" else "Rejected: evaluation failed"
                        git_commit = current_commit(root)

        if proposal.metadata.get("skip_evaluation"):
            result = accepted_eval
            decision = "reject"
            summary = f"Rejected: {proposal.metadata.get('skip_reason', 'proposal skipped')}"
            adapter.restore(accepted_state)
            git_commit = current_commit(root)

        if decision == "accept":
            decision = "accept"
            score_for_record = result.score
        else:
            score_for_record = accepted_eval.score if proposal.metadata.get("skip_evaluation") else (result.score if result.status == "ok" else accepted_eval.score)

        record = RunRecord(
            revision=revision,
            base_revision=base_revision,
            decision=decision,
            score=score_for_record,
            previous_score=previous_score,
            metric_delta=_delta(previous_score, score_for_record),
            status=result.status,
            summary=summary,
            mutation=str(candidate.metadata.get("mutation_summary", proposal.summary)),
            target_file=proposal.scope_label,
            git_branch=current_branch(root),
            git_commit=git_commit,
            git_dirty=is_dirty(root),
            chunk_id=str(proposal.metadata.get("chunk_id", "")),
            chunk_span=str(proposal.metadata.get("chunk_span", "")),
            mutation_kind=str(candidate.metadata.get("mutation_kind", proposal.metadata.get("proposal_kind", ""))),
            prior_weight=proposal.metadata.get("prior_weight"),
            prior_basis_revision=proposal.metadata.get("prior_basis_revision"),
        )
        trace = {
            "mode": "search",
            "revision": revision,
            "base_revision": int(accepted_row["revision"]),
            "proposal": proposal.metadata,
            "candidate": candidate.metadata,
            "decision": decision,
            "score": score_for_record,
            "output": proposal.metadata.get("skip_reason", result.output),
            "skip_reason": proposal.metadata.get("skip_reason", ""),
            "adapter_trace": adapter.trace_metadata(proposal, candidate),
        }
        if branch_results is not None:
            trace["branch_results"] = branch_results
        if retry_trace is not None:
            trace["retry_attempt"] = retry_trace
        active_ledger.append(record, trace)
        history = active_ledger.rows()
        records.append(record)
        if proposal.metadata.get("skip_evaluation"):
            break
    return records
