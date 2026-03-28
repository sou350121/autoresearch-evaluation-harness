from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import src.autoresearch_plus.llm_proposer as llm_proposer
from src.autoresearch_plus.dl_demo_adapters import (
    BreastCancerClassificationDemoAdapter,
    CapacityBudgetProxyDemoAdapter,
    CirclesClassificationDemoAdapter,
    DiabetesRegressionDemoAdapter,
    DigitsImageClassificationDemoAdapter,
    Friedman1RegressionDemoAdapter,
    OptimizerScheduleProxyDemoAdapter,
    VeGateProxyDemoAdapter,
    WineClassificationDemoAdapter,
)
from src.autoresearch_plus.models import AcceptedState


class DlDemoAdapterTests(unittest.TestCase):
    def _copy_demo(self, demo_name: str) -> tuple[Path, Path]:
        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / demo_name
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        demo = root / demo_name
        shutil.copytree(fixture_root, demo)
        return root, demo

    def _assert_adapter_improves(self, adapter_cls, demo_name: str, target_file: str) -> None:
        root, demo = self._copy_demo(demo_name)
        target = demo / target_file
        adapter = adapter_cls(root, target_path=target, proposer_name="chunked_prior")
        baseline = adapter.evaluate()
        accepted = AcceptedState(
            files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
            label=adapter.scope_label,
        )
        proposal = adapter.propose(accepted, history=[], revision=1)
        adapter.materialize(accepted, proposal)
        improved = adapter.evaluate()
        self.assertGreater(improved.score, baseline.score)

    def test_circles_demo_improves(self) -> None:
        self._assert_adapter_improves(CirclesClassificationDemoAdapter, "demo_circles_classification", "task.py")

    def test_digits_demo_improves(self) -> None:
        self._assert_adapter_improves(
            DigitsImageClassificationDemoAdapter, "demo_digits_image_classification", "task.py"
        )

    def test_diabetes_demo_improves(self) -> None:
        self._assert_adapter_improves(DiabetesRegressionDemoAdapter, "demo_diabetes_regression", "task.py")

    def test_breast_cancer_demo_improves(self) -> None:
        self._assert_adapter_improves(
            BreastCancerClassificationDemoAdapter, "demo_breast_cancer_classification", "task.py"
        )

    def test_wine_demo_improves(self) -> None:
        self._assert_adapter_improves(WineClassificationDemoAdapter, "demo_wine_classification", "task.py")

    def test_friedman1_demo_improves(self) -> None:
        self._assert_adapter_improves(
            Friedman1RegressionDemoAdapter, "demo_friedman1_regression", "task.py"
        )

    def test_ve_gate_proxy_demo_improves(self) -> None:
        self._assert_adapter_improves(VeGateProxyDemoAdapter, "demo_ve_gate_proxy", "task.py")

    def test_optimizer_schedule_proxy_demo_improves(self) -> None:
        self._assert_adapter_improves(
            OptimizerScheduleProxyDemoAdapter, "demo_optimizer_schedule_proxy", "task.py"
        )

    def test_capacity_budget_proxy_demo_improves(self) -> None:
        self._assert_adapter_improves(
            CapacityBudgetProxyDemoAdapter, "demo_capacity_budget_proxy", "task.py"
        )

    def test_llm_proposer_can_select_digits_fix(self) -> None:
        root, demo = self._copy_demo("demo_digits_image_classification")
        target = demo / "task.py"
        adapter = DigitsImageClassificationDemoAdapter(root, target_path=target, proposer_name="llm_codex")

        original_select_fix_ids = llm_proposer.select_fix_ids

        def fake_select_fix_ids(**kwargs):
            return (
                ["increase_hidden_width", "train_longer", "lower_learning_rate"],
                {"provider": "llm_codex", "fallback_used": False, "raw_response": "{}"},
            )

        llm_proposer.select_fix_ids = fake_select_fix_ids
        try:
            baseline = adapter.evaluate()
            accepted = AcceptedState(
                files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
                label=adapter.scope_label,
            )
            proposal = adapter.propose(accepted, history=[], revision=1)
            adapter.materialize(accepted, proposal)
            improved = adapter.evaluate()
        finally:
            llm_proposer.select_fix_ids = original_select_fix_ids

        self.assertEqual("llm_codex", proposal.metadata["proposal_kind"])
        self.assertEqual(
            ["increase_hidden_width", "train_longer", "lower_learning_rate"],
            proposal.metadata["fix_ids"],
        )
        self.assertGreater(improved.score, baseline.score)

    def test_llm_retry_excludes_first_attempt_fix_ids(self) -> None:
        root, demo = self._copy_demo("demo_digits_image_classification")
        target = demo / "task.py"
        adapter = DigitsImageClassificationDemoAdapter(root, target_path=target, proposer_name="llm_codex")

        original_select_fix_ids = llm_proposer.select_fix_ids
        calls: list[list[str]] = []

        def fake_select_fix_ids(**kwargs):
            allowed = list(kwargs["fix_catalog"].keys())
            calls.append(allowed)
            if len(calls) == 1:
                return (
                    ["train_longer"],
                    {"provider": "llm_codex", "fallback_used": False, "raw_response": "{}"},
                )
            return (
                ["increase_hidden_width", "lower_learning_rate"],
                {"provider": "llm_codex", "fallback_used": False, "raw_response": "{}"},
            )

        llm_proposer.select_fix_ids = fake_select_fix_ids
        try:
            accepted = AcceptedState(
                files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
                label=adapter.scope_label,
            )
            first = adapter.propose(accepted, history=[], revision=1)
            retry = adapter.retry_after_reject(
                accepted,
                history=[],
                revision=1,
                rejected_proposal=first,
                rejected_result=adapter.evaluate(),
            )
        finally:
            llm_proposer.select_fix_ids = original_select_fix_ids

        self.assertEqual(
            [
                ["increase_hidden_width", "train_longer", "lower_learning_rate"],
                ["increase_hidden_width", "lower_learning_rate"],
            ],
            calls,
        )
        self.assertIsNotNone(retry)
        assert retry is not None
        self.assertEqual(["increase_hidden_width", "lower_learning_rate"], retry.metadata["fix_ids"])

    def test_ve_gate_retry_can_promote_two_fix_combo(self) -> None:
        root, demo = self._copy_demo("demo_ve_gate_proxy")
        target = demo / "task.py"
        adapter = VeGateProxyDemoAdapter(root, target_path=target, proposer_name="llm_codex")

        original_select_fix_ids = llm_proposer.select_fix_ids
        calls: list[list[str]] = []

        def fake_select_fix_ids(**kwargs):
            allowed = list(kwargs["fix_catalog"].keys())
            calls.append(allowed)
            if len(calls) == 1:
                return (
                    ["enable_alternating_ve"],
                    {"provider": "llm_codex", "fallback_used": False, "raw_response": "{}"},
                )
            return (
                ["neutralize_gate_init"],
                {"provider": "llm_codex", "fallback_used": False, "raw_response": "{}"},
            )

        llm_proposer.select_fix_ids = fake_select_fix_ids
        try:
            accepted = AcceptedState(
                files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
                label=adapter.scope_label,
            )
            first = adapter.propose(accepted, history=[], revision=1)
            retry = adapter.retry_after_reject(
                accepted,
                history=[],
                revision=1,
                rejected_proposal=first,
                rejected_result=adapter.evaluate(),
            )
        finally:
            llm_proposer.select_fix_ids = original_select_fix_ids

        self.assertEqual(
            [
                ["enable_alternating_ve", "neutralize_gate_init"],
                ["neutralize_gate_init", "widen_gate_channels"],
            ],
            calls,
        )
        self.assertIsNotNone(retry)
        assert retry is not None
        self.assertEqual(["enable_alternating_ve", "neutralize_gate_init"], retry.metadata["fix_ids"])

    def test_ve_gate_hypotheses_skip_single_path_after_memory_reject(self) -> None:
        root, demo = self._copy_demo("demo_ve_gate_proxy")
        target = demo / "task.py"
        runs = root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "experiment_memory.jsonl").write_text(
            '{"hypothesis_id":"ve_single_path_restore","outcome":"reject_candidate","retained":false}\n',
            encoding="utf-8",
        )
        adapter = VeGateProxyDemoAdapter(root, target_path=target, proposer_name="chunked_prior")
        accepted = AcceptedState(
            files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
            label=adapter.scope_label,
        )

        hypotheses = adapter.propose_hypotheses(accepted, history=[], revision=2)

        self.assertEqual(1, len(hypotheses))
        self.assertEqual("ve_combo_stabilization", hypotheses[0].hypothesis_id)

    def test_ve_gate_hypotheses_prioritize_retained_combo_method(self) -> None:
        root, demo = self._copy_demo("demo_ve_gate_proxy")
        target = demo / "task.py"
        runs = root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "experiment_memory.jsonl").write_text(
            '{"hypothesis_id":"ve_combo_stabilization","outcome":"accept_candidate","retained":true}\n',
            encoding="utf-8",
        )
        adapter = VeGateProxyDemoAdapter(root, target_path=target, proposer_name="chunked_prior")
        accepted = AcceptedState(
            files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
            label=adapter.scope_label,
        )

        hypotheses = adapter.propose_hypotheses(accepted, history=[], revision=2)

        self.assertEqual(
            ["ve_combo_stabilization", "ve_single_path_restore"],
            [item.hypothesis_id for item in hypotheses],
        )

    def test_optimizer_schedule_hypotheses_prioritize_retained_combo_method(self) -> None:
        root, demo = self._copy_demo("demo_optimizer_schedule_proxy")
        target = demo / "task.py"
        runs = root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "experiment_memory.jsonl").write_text(
            '{"hypothesis_id":"schedule_decay_only","outcome":"accept_candidate","retained":false}\n'
            '{"hypothesis_id":"optimizer_schedule_coupling","outcome":"accept_candidate","retained":true}\n',
            encoding="utf-8",
        )
        adapter = OptimizerScheduleProxyDemoAdapter(root, target_path=target, proposer_name="chunked_prior")
        accepted = AcceptedState(
            files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
            label=adapter.scope_label,
        )

        hypotheses = adapter.propose_hypotheses(accepted, history=[], revision=2)

        self.assertEqual(
            ["optimizer_schedule_coupling", "lower_base_lr_only"],
            [item.hypothesis_id for item in hypotheses],
        )
        self.assertEqual(["exploitation", "exploration"], [item.metadata["beam_role"] for item in hypotheses])

    def test_optimizer_schedule_exploitation_hypothesis_anchors_retained_combo_fix_ids(self) -> None:
        root, demo = self._copy_demo("demo_optimizer_schedule_proxy")
        target = demo / "task.py"
        runs = root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "experiment_memory.jsonl").write_text(
            '{"hypothesis_id":"optimizer_schedule_coupling","outcome":"accept_candidate","retained":true}\n',
            encoding="utf-8",
        )
        adapter = OptimizerScheduleProxyDemoAdapter(root, target_path=target, proposer_name="llm_codex")

        original_select_fix_ids = llm_proposer.select_fix_ids

        def fake_select_fix_ids(**kwargs):
            return (
                ["lower_base_lr"],
                {"provider": "llm_codex", "fallback_used": False, "raw_response": "{}"},
            )

        llm_proposer.select_fix_ids = fake_select_fix_ids
        try:
            accepted = AcceptedState(
                files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
                label=adapter.scope_label,
            )
            hypotheses = adapter.propose_hypotheses(accepted, history=[], revision=2)
        finally:
            llm_proposer.select_fix_ids = original_select_fix_ids

        self.assertEqual("optimizer_schedule_coupling", hypotheses[0].hypothesis_id)
        self.assertEqual("exploitation", hypotheses[0].metadata["beam_role"])
        self.assertEqual(["enable_lr_decay", "enable_lr_warmup"], hypotheses[0].fix_ids)


if __name__ == "__main__":
    unittest.main()
