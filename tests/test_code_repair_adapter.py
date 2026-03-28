from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.autoresearch_plus.code_repair_demo_adapter import CodeRepairDemoAdapter
from src.autoresearch_plus.models import AcceptedState


SOURCE = """from __future__ import annotations


def total_with_tax(subtotal: float, tax_rate: float) -> float:
    return subtotal * tax_rate


def parse_quantity(raw: str) -> int:
    return int(raw)


def apply_discount(total: float, pct: float) -> float:
    return total + total * pct
"""


TESTS = """from __future__ import annotations

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


class CodeRepairAdapterTests(unittest.TestCase):
    def test_chunked_repair_improves_test_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo = root / "demo_code_repair"
            demo.mkdir()
            target = demo / "calculator.py"
            tests = demo / "test_calculator.py"
            target.write_text(SOURCE, encoding="utf-8")
            tests.write_text(TESTS, encoding="utf-8")

            adapter = CodeRepairDemoAdapter(root, target_path=target, proposer_name="chunked_prior")
            baseline = adapter.evaluate()
            accepted = AcceptedState(files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")}, label=adapter.scope_label)
            proposal = adapter.propose(accepted, history=[], revision=1)
            adapter.materialize(accepted, proposal)
            improved = adapter.evaluate()

            self.assertLess(baseline.score, improved.score)


if __name__ == "__main__":
    unittest.main()
