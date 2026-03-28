from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.autoresearch_plus.bugfix_demo_adapter import BugfixDemoAdapter
from src.autoresearch_plus.models import AcceptedState


BUGGY_SOURCE = """from __future__ import annotations


def add(a: int, b: int) -> int:
    return a - b


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return min(low, min(value, high))
"""


class BugfixAdapterTests(unittest.TestCase):
    def test_correct_patch_improves_bugfix_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo_dir = root / "demo_bugfix"
            demo_dir.mkdir()
            target = demo_dir / "buggy_math.py"
            target.write_text(BUGGY_SOURCE, encoding="utf-8")

            adapter = BugfixDemoAdapter(root, target_path=target, proposer_name="chunked_prior")
            baseline = adapter.evaluate()
            accepted = AcceptedState(files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")}, label=adapter.scope_label)
            proposal = adapter.propose(accepted, history=[], revision=1)
            adapter.materialize(accepted, proposal)
            improved = adapter.evaluate()

            self.assertLess(baseline.score, improved.score)
            self.assertEqual("ok", improved.status)
            self.assertLess(baseline.score, 6.0)


if __name__ == "__main__":
    unittest.main()
