from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from src.autoresearch_plus.engine import run_baseline_with_adapter, run_search_with_adapter
from src.autoresearch_plus.adapter import AcceptedState, Candidate, EvalResult, Proposal, TaskAdapter
from src.autoresearch_plus.ledger import RunLedger
from src.autoresearch_plus.mixed_prompt_code_repair_adapter import MixedPromptCodeRepairDemoAdapter
from src.autoresearch_plus.models import Hypothesis


class FakeAdapter(TaskAdapter):
    name = "fake"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.target = root / "artifact.txt"
        self.target.write_text("baseline", encoding="utf-8")
        self._proposal_count = 0

    @property
    def edit_scope(self) -> list[Path]:
        return [self.target]

    @property
    def scope_label(self) -> str:
        return "artifact.txt"

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(files={"artifact.txt": self.target.read_text(encoding="utf-8")}, label=self.scope_label)

    def restore(self, accepted: AcceptedState) -> None:
        self.target.write_text(accepted.files["artifact.txt"], encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        self._proposal_count += 1
        content = "better" if self._proposal_count == 1 else "worse"
        return Proposal(
            summary=f"write {content}",
            scope_label=self.scope_label,
            metadata={"content": content, "proposal_kind": "rewrite"},
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        content = str(proposal.metadata["content"])
        self.target.write_text(content, encoding="utf-8")
        return Candidate(summary=proposal.summary, metadata=proposal.metadata)

    def evaluate(self) -> EvalResult:
        content = self.target.read_text(encoding="utf-8")
        score = 2.0 if content == "better" else 0.5
        return EvalResult(status="ok", score=score, output=f"SCORE={score}")

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return AcceptedState(files={"artifact.txt": self.target.read_text(encoding="utf-8")}, label=self.scope_label)

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {"proposal_kind": proposal.metadata["proposal_kind"]}


class FakeSkipAdapter(TaskAdapter):
    name = "fake_skip"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.target = root / "artifact.txt"
        self.target.write_text("stable", encoding="utf-8")
        self.evaluate_calls = 0

    @property
    def edit_scope(self) -> list[Path]:
        return [self.target]

    @property
    def scope_label(self) -> str:
        return "artifact.txt"

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(files={"artifact.txt": self.target.read_text(encoding="utf-8")}, label=self.scope_label)

    def restore(self, accepted: AcceptedState) -> None:
        self.target.write_text(accepted.files["artifact.txt"], encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        return Proposal(
            summary="all saturated",
            scope_label=self.scope_label,
            metadata={"proposal_kind": "rewrite", "skip_evaluation": True, "skip_reason": "all_stages_saturated"},
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        return Candidate(summary=proposal.summary, metadata={"mutation_summary": "", "mutation_kind": "skip"})

    def evaluate(self) -> EvalResult:
        self.evaluate_calls += 1
        return EvalResult(status="ok", score=1.0, output="SCORE=1.0")

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {"skip_reason": proposal.metadata["skip_reason"]}


class FakeRetryAdapter(TaskAdapter):
    name = "fake_retry"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.target = root / "artifact.txt"
        self.target.write_text("baseline", encoding="utf-8")

    @property
    def edit_scope(self) -> list[Path]:
        return [self.target]

    @property
    def scope_label(self) -> str:
        return "artifact.txt"

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(files={"artifact.txt": self.target.read_text(encoding="utf-8")}, label=self.scope_label)

    def restore(self, accepted: AcceptedState) -> None:
        self.target.write_text(accepted.files["artifact.txt"], encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        return Proposal(
            summary="bad first attempt",
            scope_label=self.scope_label,
            metadata={"content": "bad", "proposal_kind": "llm_codex", "fix_ids": ["bad_fix"], "provider": "llm_codex"},
        )

    def retry_after_reject(
        self,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        rejected_proposal: Proposal,
        rejected_result: EvalResult,
    ) -> Proposal | None:
        return Proposal(
            summary="good retry attempt",
            scope_label=self.scope_label,
            metadata={
                "content": "good",
                "proposal_kind": "llm_codex",
                "fix_ids": ["good_fix"],
                "provider": "llm_codex",
                "retry_attempt": 2,
            },
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        content = str(proposal.metadata["content"])
        self.target.write_text(content, encoding="utf-8")
        return Candidate(summary=proposal.summary, metadata={**proposal.metadata, "mutation_summary": content, "mutation_kind": content})

    def evaluate(self) -> EvalResult:
        content = self.target.read_text(encoding="utf-8")
        score = {"baseline": 1.0, "bad": 0.5, "good": 2.0}[content]
        return EvalResult(status="ok", score=score, output=f"SCORE={score}")

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {"proposal_kind": proposal.metadata["proposal_kind"]}


class FakeBranchAdapter(TaskAdapter):
    name = "fake_branch"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.target = root / "artifact.txt"
        self.target.write_text("baseline", encoding="utf-8")

    @property
    def edit_scope(self) -> list[Path]:
        return [self.target]

    @property
    def scope_label(self) -> str:
        return "artifact.txt"

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(files={"artifact.txt": self.target.read_text(encoding="utf-8")}, label=self.scope_label)

    def restore(self, accepted: AcceptedState) -> None:
        self.target.write_text(accepted.files["artifact.txt"], encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        raise AssertionError("branch adapters should use hypotheses")

    def propose_hypotheses(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> list[Hypothesis]:
        return [
            Hypothesis(
                hypothesis_id="bad_method",
                problem_frame="toy",
                target_locus="artifact.txt",
                mechanism_guess="bad rewrite",
                operator_family="rewrite",
                expected_signal="score up",
                risk="medium",
                patch_budget=1,
                fix_ids=["bad"],
            ),
            Hypothesis(
                hypothesis_id="good_method",
                problem_frame="toy",
                target_locus="artifact.txt",
                mechanism_guess="good rewrite",
                operator_family="rewrite",
                expected_signal="score up",
                risk="low",
                patch_budget=1,
                fix_ids=["good"],
            ),
        ]

    def proposal_from_hypothesis(
        self,
        hypothesis: Hypothesis,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        branch_id: str,
    ) -> Proposal:
        content = "good" if hypothesis.hypothesis_id == "good_method" else "bad"
        return Proposal(
            summary=hypothesis.mechanism_guess,
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": "hypothesis_branch",
                "branch_id": branch_id,
                "content": content,
                "hypothesis": {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "target_locus": hypothesis.target_locus,
                    "operator_family": hypothesis.operator_family,
                    "mechanism_guess": hypothesis.mechanism_guess,
                },
                "fix_ids": hypothesis.fix_ids,
            },
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        content = str(proposal.metadata["content"])
        self.target.write_text(content, encoding="utf-8")
        return Candidate(summary=proposal.summary, metadata={**proposal.metadata, "mutation_summary": content, "mutation_kind": content})

    def evaluate(self) -> EvalResult:
        content = self.target.read_text(encoding="utf-8")
        score = {"baseline": 1.0, "bad": 0.5, "good": 2.0}[content]
        return EvalResult(status="ok", score=score, output=f"SCORE={score}")

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {"proposal_kind": proposal.metadata["proposal_kind"]}


class FakeDualImproveBranchAdapter(FakeBranchAdapter):
    def proposal_from_hypothesis(
        self,
        hypothesis: Hypothesis,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        branch_id: str,
    ) -> Proposal:
        content = "better" if hypothesis.hypothesis_id == "bad_method" else "good"
        return Proposal(
            summary=hypothesis.mechanism_guess,
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": "hypothesis_branch",
                "branch_id": branch_id,
                "content": content,
                "hypothesis": {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "target_locus": hypothesis.target_locus,
                    "operator_family": hypothesis.operator_family,
                    "mechanism_guess": hypothesis.mechanism_guess,
                },
                "fix_ids": hypothesis.fix_ids,
            },
        )

    def evaluate(self) -> EvalResult:
        content = self.target.read_text(encoding="utf-8")
        score = {"baseline": 1.0, "bad": 0.5, "better": 1.5, "good": 2.0}[content]
        return EvalResult(status="ok", score=score, output=f"SCORE={score}")


class EngineTests(unittest.TestCase):
    def test_engine_accepts_improvement_and_restores_on_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FakeAdapter(root)
            ledger = RunLedger(root)

            baseline = run_baseline_with_adapter(root, adapter, ledger)
            records = run_search_with_adapter(root, adapter, ledger, iterations=2)

            self.assertEqual("accept", baseline.decision)
            self.assertEqual(2, len(records))
            self.assertEqual("accept", records[0].decision)
            self.assertEqual("reject", records[1].decision)
            self.assertEqual("better", adapter.target.read_text(encoding="utf-8"))

    def test_engine_trace_includes_stage_level_metadata_for_composite_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            repair_dir = root / "demo_code_repair"
            prompt_dir.mkdir()
            repair_dir.mkdir()
            (prompt_dir / "prompt.md").write_text(
                "# Ticket Triage\n\n## Role\nYou classify support tickets.\n\n## Instructions\n- Read the ticket.\n- Choose the best label.\n\n## Output\n- Return a structured result.\n",
                encoding="utf-8",
            )
            (repair_dir / "calculator.py").write_text(
                "from __future__ import annotations\n\n\ndef total_with_tax(subtotal: float, tax_rate: float) -> float:\n    return subtotal * tax_rate\n\n\ndef parse_quantity(raw: str) -> int:\n    return int(raw)\n\n\ndef apply_discount(total: float, pct: float) -> float:\n    return total + total * pct\n",
                encoding="utf-8",
            )
            (repair_dir / "test_calculator.py").write_text(
                "from __future__ import annotations\n\nimport unittest\n\nfrom calculator import apply_discount, parse_quantity, total_with_tax\n\n\nclass CalculatorTests(unittest.TestCase):\n    def test_total_with_tax(self) -> None:\n        self.assertAlmostEqual(12.0, total_with_tax(10.0, 0.2))\n\n    def test_parse_quantity_strips_whitespace(self) -> None:\n        self.assertEqual(3, parse_quantity(\" 3 \"))\n\n    def test_apply_discount_reduces_total(self) -> None:\n        self.assertAlmostEqual(90.0, apply_discount(100.0, 0.1))\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n",
                encoding="utf-8",
            )
            adapter = MixedPromptCodeRepairDemoAdapter(root, proposer_name="chunked_prior")
            ledger = RunLedger(root)

            run_baseline_with_adapter(root, adapter, ledger)
            records = run_search_with_adapter(root, adapter, ledger, iterations=1)

            self.assertEqual(1, len(records))
            trace = json.loads((root / "runs" / "traces" / "run_0002.json").read_text(encoding="utf-8"))
            self.assertEqual(["prompt_stage", "code_repair_stage"], trace["adapter_trace"]["stage_sequence"])
            self.assertEqual(2, len(trace["adapter_trace"]["stage_results"]))
            self.assertEqual("integration_threshold_bonus", trace["adapter_trace"]["scoring_policy"])
            self.assertEqual(2.0, trace["adapter_trace"]["integration_bonus"])

    def test_engine_fail_fast_skips_evaluation_when_proposal_marks_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FakeSkipAdapter(root)
            ledger = RunLedger(root)

            run_baseline_with_adapter(root, adapter, ledger)
            records = run_search_with_adapter(root, adapter, ledger, iterations=3)

            self.assertEqual(1, adapter.evaluate_calls)
            self.assertEqual(1, len(records))
            self.assertEqual("reject", records[0].decision)
            self.assertEqual("Rejected: all_stages_saturated", records[0].summary)
            self.assertEqual(0.0, records[0].metric_delta)
            trace = json.loads((root / "runs" / "traces" / "run_0002.json").read_text(encoding="utf-8"))
            self.assertEqual("all_stages_saturated", trace["skip_reason"])

    def test_engine_can_accept_retry_after_first_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FakeRetryAdapter(root)
            ledger = RunLedger(root)

            run_baseline_with_adapter(root, adapter, ledger)
            records = run_search_with_adapter(root, adapter, ledger, iterations=1)

            self.assertEqual(1, len(records))
            self.assertEqual("accept", records[0].decision)
            self.assertEqual(2.0, records[0].score)
            self.assertEqual("good", adapter.target.read_text(encoding="utf-8"))
            trace = json.loads((root / "runs" / "traces" / "run_0002.json").read_text(encoding="utf-8"))
            self.assertEqual(["good_fix"], trace["proposal"]["fix_ids"])
            self.assertEqual(["good_fix"], trace["retry_attempt"]["proposal"]["fix_ids"])

    def test_engine_can_select_best_hypothesis_branch_and_write_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FakeBranchAdapter(root)
            ledger = RunLedger(root)

            run_baseline_with_adapter(root, adapter, ledger)
            records = run_search_with_adapter(root, adapter, ledger, iterations=1)

            self.assertEqual(1, len(records))
            self.assertEqual("accept", records[0].decision)
            self.assertEqual(2.0, records[0].score)
            trace = json.loads((root / "runs" / "traces" / "run_0002.json").read_text(encoding="utf-8"))
            self.assertEqual("branch-2", trace["proposal"]["branch_id"])
            self.assertEqual(2, len(trace["branch_results"]))
            memory_rows = [
                json.loads(line)
                for line in (root / "runs" / "experiment_memory.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(2, len(memory_rows))
            self.assertEqual("bad_method", memory_rows[0]["hypothesis_id"])
            self.assertEqual("good_method", memory_rows[1]["hypothesis_id"])
            self.assertFalse(memory_rows[0]["retained"])
            self.assertTrue(memory_rows[1]["retained"])

    def test_engine_marks_only_best_improved_hypothesis_as_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FakeDualImproveBranchAdapter(root)
            ledger = RunLedger(root)

            run_baseline_with_adapter(root, adapter, ledger)
            _ = run_search_with_adapter(root, adapter, ledger, iterations=1)

            memory_rows = [
                json.loads(line)
                for line in (root / "runs" / "experiment_memory.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(2, len(memory_rows))
            self.assertFalse(memory_rows[0]["retained"])
            self.assertTrue(memory_rows[1]["retained"])


if __name__ == "__main__":
    unittest.main()
