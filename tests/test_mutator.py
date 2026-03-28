from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from src.autoresearch_plus.models import MutationConfig
from src.autoresearch_plus.mutator import mutate_target_file


class AstPatchMutatorTests(unittest.TestCase):
    def test_python_ast_patch_changes_code_and_keeps_it_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "train.py"
            original = """from __future__ import annotations

import math


def predict(x: float, y: float) -> float:
    base = 1.10 * x + 0.35 * y
    wave = math.sin(x * 0.70) + 0.60 * math.cos(y * 1.40)
    return base + wave + 0.40
"""
            target.write_text(original, encoding="utf-8")
            mutation = MutationConfig(
                mode="python_ast_patch",
                max_constant_delta=0.30,
                random_seed=7,
                allowed_math_funcs=["sin", "cos", "tanh"],
                allowed_binary_ops=["Add", "Sub", "Mult"],
            )

            result = mutate_target_file(target, mutation, iteration=3)
            updated = target.read_text(encoding="utf-8")

            self.assertNotEqual(original, updated)
            self.assertEqual(updated, result.updated_text)
            self.assertIn(result.details["kind"], {"constant", "math_func", "binary_op"})
            self.assertTrue(result.details["diff"].startswith("--- before"))
            ast.parse(updated)


if __name__ == "__main__":
    unittest.main()
