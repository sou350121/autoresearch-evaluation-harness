from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.autoresearch_plus.config import load_project_config
from src.autoresearch_plus.numeric_demo_adapter import NumericDemoAdapter
from src.autoresearch_plus.proposers import build_numeric_proposer


class ProposerTests(unittest.TestCase):
    def test_single_step_random_numeric_proposer_uses_one_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "demo_target").mkdir()
            (root / "demo_target" / "train.py").write_text(
                "def predict(x, y):\n    base = 1.0 * x\n    return base\n",
                encoding="utf-8",
            )
            (root / "config" / "project.toml").write_text(
                """
project_name = "test"
adapter = "numeric_demo"
proposer = "single_step_random"
edit_scope = ["demo_target/train.py"]
target_file = "demo_target/train.py"
evaluation_command = "python -c \\"print('SCORE=1.0')\\""
score_pattern = "SCORE=(?P<score>-?\\\\d+(?:\\\\.\\\\d+)?)"
direction = "maximize"

[mutation]
mode = "python_ast_patch"
max_constant_delta = 0.30
random_seed = 7
allowed_math_funcs = ["sin", "cos", "tanh"]
allowed_binary_ops = ["Add", "Sub", "Mult"]

[chunking]
enabled = true
strategy = "ast_assignments"
chunk_budget = 2

[prior]
enabled = true
lookback = 6
decay = 0.8
accept_boost = 1.5
reject_penalty = 1.0
min_weight = 0.2
""".strip(),
                encoding="utf-8",
            )
            config = load_project_config(root)
            adapter = NumericDemoAdapter(root, config)
            proposer = build_numeric_proposer(config)

            proposal = proposer.propose(adapter, adapter.load_accepted_state(), history=[], revision=2)

            self.assertEqual("single_step_random", proposer.name)
            self.assertEqual(1, len(proposal.metadata["step_iterations"]))

    def test_chunked_prior_numeric_proposer_uses_chunk_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "demo_target").mkdir()
            (root / "demo_target" / "train.py").write_text(
                "def predict(x, y):\n    base = 1.0 * x\n    bias = 0.4\n    return base + bias\n",
                encoding="utf-8",
            )
            (root / "config" / "project.toml").write_text(
                """
project_name = "test"
adapter = "numeric_demo"
proposer = "chunked_prior"
edit_scope = ["demo_target/train.py"]
target_file = "demo_target/train.py"
evaluation_command = "python -c \\"print('SCORE=1.0')\\""
score_pattern = "SCORE=(?P<score>-?\\\\d+(?:\\\\.\\\\d+)?)"
direction = "maximize"

[mutation]
mode = "python_ast_patch"
max_constant_delta = 0.30
random_seed = 7
allowed_math_funcs = ["sin", "cos", "tanh"]
allowed_binary_ops = ["Add", "Sub", "Mult"]

[chunking]
enabled = true
strategy = "ast_assignments"
chunk_budget = 2

[prior]
enabled = true
lookback = 6
decay = 0.8
accept_boost = 1.5
reject_penalty = 1.0
min_weight = 0.2
""".strip(),
                encoding="utf-8",
            )
            config = load_project_config(root)
            adapter = NumericDemoAdapter(root, config)
            proposer = build_numeric_proposer(config)

            proposal = proposer.propose(adapter, adapter.load_accepted_state(), history=[], revision=2)

            self.assertEqual("chunked_prior", proposer.name)
            self.assertEqual(2, len(proposal.metadata["step_iterations"]))


if __name__ == "__main__":
    unittest.main()
