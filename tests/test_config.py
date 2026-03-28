from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.autoresearch_plus.config import load_project_config


class ConfigTests(unittest.TestCase):
    def test_load_project_config_reads_composite_stage_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "project.toml").write_text(
                """
project_name = "mixed-demo"
adapter = "mixed_prompt_code_repair_demo"
proposer = "chunked_prior"
edit_scope = ["demo_prompt/prompt.md", "demo_code_repair/calculator.py"]
target_file = "demo_prompt/prompt.md"
evaluation_command = "python demo_prompt/eval.py"
score_pattern = "SCORE=(?P<score>-?\\\\d+(?:\\\\.\\\\d+)?)"
direction = "maximize"
composite_stage_order = ["code_repair_stage", "prompt_stage"]

[mutation]
mode = "python_ast_patch"
max_constant_delta = 0.30
random_seed = 7
allowed_math_funcs = ["sin", "cos", "tanh"]
allowed_binary_ops = ["Add", "Sub", "Mult"]
""".strip(),
                encoding="utf-8",
            )

            config = load_project_config(root)

            self.assertEqual(["code_repair_stage", "prompt_stage"], config.composite_stage_order)


if __name__ == "__main__":
    unittest.main()
