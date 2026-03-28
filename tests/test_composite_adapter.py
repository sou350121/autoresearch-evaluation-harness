from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.autoresearch_plus.mixed_prompt_bugfix_adapter import MixedPromptBugfixDemoAdapter
from src.autoresearch_plus.mixed_prompt_code_repair_adapter import MixedPromptCodeRepairDemoAdapter
from src.autoresearch_plus.prompt_demo_adapter import PROMPT_FRAGMENTS


PROMPT_SOURCE = """# Ticket Triage

## Role
You classify support tickets.

## Instructions
- Read the ticket.
- Choose the best label.

## Output
- Return a structured result.
"""

FULL_PROMPT_SOURCE = PROMPT_SOURCE + "\n## Instructions\n" + "\n".join(PROMPT_FRAGMENTS) + "\n"

REPAIRED_CODE_SOURCE = """from __future__ import annotations


def total_with_tax(subtotal: float, tax_rate: float) -> float:
    return subtotal * (1.0 + tax_rate)


def parse_quantity(raw: str) -> int:
    return int(raw.strip())


def apply_discount(total: float, pct: float) -> float:
    return total - total * pct
"""


CODE_SOURCE = """from __future__ import annotations


def total_with_tax(subtotal: float, tax_rate: float) -> float:
    return subtotal * tax_rate


def parse_quantity(raw: str) -> int:
    return int(raw)


def apply_discount(total: float, pct: float) -> float:
    return total + total * pct
"""


CODE_TESTS = """from __future__ import annotations

import unittest

from calculator import apply_discount, parse_quantity, total_with_tax


class CalculatorTests(unittest.TestCase):
    def test_total_with_tax(self) -> None:
        self.assertAlmostEqual(12.0, total_with_tax(10.0, 0.2))

    def test_parse_quantity_strips_whitespace(self) -> None:
        self.assertEqual(3, parse_quantity(" 3 "))

    def test_apply_discount_reduces_total(self) -> None:
        self.assertAlmostEqual(90.0, apply_discount(100.0, 0.1))


if __name__ == "__main__":
    unittest.main()
"""


BUGFIX_SOURCE = """from __future__ import annotations


def add(a: float, b: float) -> float:
    return a - b


def safe_div(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b


def clamp(value: float, low: float, high: float) -> float:
    return min(low, min(value, high))
"""


class CompositeAdapterTests(unittest.TestCase):
    def test_mixed_adapter_improves_combined_score_across_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            repair_dir = root / "demo_code_repair"
            prompt_dir.mkdir()
            repair_dir.mkdir()
            (prompt_dir / "prompt.md").write_text(PROMPT_SOURCE, encoding="utf-8")
            (repair_dir / "calculator.py").write_text(CODE_SOURCE, encoding="utf-8")
            (repair_dir / "test_calculator.py").write_text(CODE_TESTS, encoding="utf-8")

            adapter = MixedPromptCodeRepairDemoAdapter(root, proposer_name="chunked_prior")
            baseline = adapter.evaluate()
            accepted = adapter.load_accepted_state()
            proposal = adapter.propose(accepted, history=[], revision=1)
            candidate = adapter.materialize(accepted, proposal)
            improved = adapter.evaluate()

            self.assertLess(baseline.score, improved.score)
            self.assertEqual(["prompt_stage", "code_repair_stage"], proposal.metadata["stage_sequence"])
            self.assertEqual(["prompt_stage", "code_repair_stage"], candidate.metadata["applied_stage_names"])
            self.assertIn("integration_stage", improved.output)
            self.assertEqual(7.0, improved.score)
            trace = adapter.trace_metadata(proposal, candidate)
            self.assertEqual("integration_threshold_bonus", trace["scoring_policy"])
            self.assertEqual(2.0, trace["integration_bonus"])
            self.assertEqual(2, len(trace["stage_results"]))
            self.assertEqual(2.0, trace["stage_results"][0]["normalized_score"])
            self.assertEqual(3.0, trace["stage_results"][1]["normalized_score"])

    def test_mixed_adapter_honors_configured_stage_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            repair_dir = root / "demo_code_repair"
            prompt_dir.mkdir()
            repair_dir.mkdir()
            (prompt_dir / "prompt.md").write_text(PROMPT_SOURCE, encoding="utf-8")
            (repair_dir / "calculator.py").write_text(CODE_SOURCE, encoding="utf-8")
            (repair_dir / "test_calculator.py").write_text(CODE_TESTS, encoding="utf-8")

            adapter = MixedPromptCodeRepairDemoAdapter(
                root,
                proposer_name="chunked_prior",
                stage_order=["code_repair_stage", "prompt_stage"],
            )
            accepted = adapter.load_accepted_state()
            proposal = adapter.propose(accepted, history=[], revision=1)

            self.assertEqual(["code_repair_stage", "prompt_stage"], proposal.metadata["stage_sequence"])

    def test_second_mixed_adapter_improves_combined_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            bugfix_dir = root / "demo_bugfix"
            prompt_dir.mkdir()
            bugfix_dir.mkdir()
            (prompt_dir / "prompt.md").write_text(PROMPT_SOURCE, encoding="utf-8")
            (bugfix_dir / "buggy_math.py").write_text(BUGFIX_SOURCE, encoding="utf-8")

            adapter = MixedPromptBugfixDemoAdapter(root, proposer_name="chunked_prior")
            baseline = adapter.evaluate()
            accepted = adapter.load_accepted_state()
            proposal = adapter.propose(accepted, history=[], revision=1)
            candidate = adapter.materialize(accepted, proposal)
            improved = adapter.evaluate()

            self.assertLess(baseline.score, improved.score)
            self.assertIn("integration_stage", improved.output)
            self.assertEqual(["prompt_stage", "bugfix_stage"], proposal.metadata["stage_sequence"])
            trace = adapter.trace_metadata(proposal, candidate)
            self.assertEqual("integration_threshold_bonus", trace["scoring_policy"])
            self.assertEqual(2.0, trace["integration_bonus"])

    def test_mixed_adapter_skips_saturated_stage_when_other_stage_can_still_improve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            repair_dir = root / "demo_code_repair"
            prompt_dir.mkdir()
            repair_dir.mkdir()
            (prompt_dir / "prompt.md").write_text(PROMPT_SOURCE, encoding="utf-8")
            (repair_dir / "calculator.py").write_text(REPAIRED_CODE_SOURCE, encoding="utf-8")
            (repair_dir / "test_calculator.py").write_text(CODE_TESTS, encoding="utf-8")

            adapter = MixedPromptCodeRepairDemoAdapter(root, proposer_name="chunked_prior")
            accepted = adapter.load_accepted_state()
            proposal = adapter.propose(accepted, history=[], revision=1)

            self.assertEqual(["prompt_stage"], proposal.metadata["stage_sequence"])
            self.assertEqual(["code_repair_stage"], proposal.metadata["saturated_stages"])
            self.assertNotIn("skip_evaluation", proposal.metadata)

    def test_mixed_adapter_marks_all_saturated_for_fail_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            repair_dir = root / "demo_code_repair"
            prompt_dir.mkdir()
            repair_dir.mkdir()
            (prompt_dir / "prompt.md").write_text(FULL_PROMPT_SOURCE, encoding="utf-8")
            (repair_dir / "calculator.py").write_text(REPAIRED_CODE_SOURCE, encoding="utf-8")
            (repair_dir / "test_calculator.py").write_text(CODE_TESTS, encoding="utf-8")

            adapter = MixedPromptCodeRepairDemoAdapter(root, proposer_name="chunked_prior")
            accepted = adapter.load_accepted_state()
            proposal = adapter.propose(accepted, history=[], revision=1)

            self.assertEqual([], proposal.metadata["stage_sequence"])
            self.assertEqual(["code_repair_stage", "prompt_stage"], sorted(proposal.metadata["saturated_stages"]))
            self.assertTrue(proposal.metadata["skip_evaluation"])
            self.assertEqual("all_stages_saturated", proposal.metadata["skip_reason"])


if __name__ == "__main__":
    unittest.main()
