from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.autoresearch_plus.chunking import derive_chunks
from src.autoresearch_plus.models import AcceptedState, ChunkingConfig, MutationConfig, PriorConfig, ProjectConfig, Proposal
from src.autoresearch_plus.mutator import MutationResult
from src.autoresearch_plus.mutator import mutate_target_file
from src.autoresearch_plus.numeric_demo_adapter import NumericDemoAdapter


SAMPLE = """from __future__ import annotations

import math


def predict(x: float, y: float) -> float:
    base = 1.10 * x + 0.35 * y
    wave = math.sin(x * 0.70) + 0.60 * math.cos(y * 1.40)
    shape = 0.12 * x * y - 0.15 * x * x + 0.05 * y * y
    bias = 0.40
    return base + wave + shape + bias
"""


class ChunkingTests(unittest.TestCase):
    def test_derive_chunks_returns_stable_assignment_chunks(self) -> None:
        chunks = derive_chunks(SAMPLE)

        self.assertEqual(["assign:base", "assign:wave", "assign:shape", "assign:bias"], [chunk.chunk_id for chunk in chunks])
        self.assertEqual([(7, 7), (8, 8), (9, 9), (10, 10)], [(chunk.start_line, chunk.end_line) for chunk in chunks])

    def test_derive_chunks_is_stable_across_calls(self) -> None:
        first = derive_chunks(SAMPLE)
        second = derive_chunks(SAMPLE)

        self.assertEqual(
            [(chunk.chunk_id, chunk.start_line, chunk.end_line) for chunk in first],
            [(chunk.chunk_id, chunk.start_line, chunk.end_line) for chunk in second],
        )

    def test_mutate_target_file_stays_within_selected_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "train.py"
            target.write_text(SAMPLE, encoding="utf-8")
            chunk = derive_chunks(SAMPLE)[1]
            mutation = MutationConfig(
                mode="python_ast_patch",
                max_constant_delta=0.30,
                random_seed=7,
                allowed_math_funcs=["sin", "cos", "tanh"],
                allowed_binary_ops=["Add", "Sub", "Mult"],
            )

            result = mutate_target_file(target, mutation, iteration=3, chunk=chunk)
            self.assertEqual(chunk.chunk_id, result.details["chunk_id"])
            self.assertEqual(f"{chunk.start_line}-{chunk.end_line}", result.details["chunk_span"])
            self.assertIn("-    wave =", result.details["diff"])
            self.assertIn("+    wave =", result.details["diff"])

    def test_numeric_demo_materialize_with_chunk_budget_two_records_multiple_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "train.py"
            target.write_text(SAMPLE, encoding="utf-8")

            config = ProjectConfig(
                root=root,
                project_name="test",
                adapter_name="numeric_demo",
                proposer_name="chunked_prior",
                edit_scope=[target],
                target_file=target,
                evaluation_command="python -c \"print('SCORE=1.0')\"",
                score_pattern=r"SCORE=(?P<score>-?\d+(?:\.\d+)?)",
                direction="maximize",
                mutation=MutationConfig(
                    mode="python_ast_patch",
                    max_constant_delta=0.30,
                    random_seed=7,
                    allowed_math_funcs=["sin", "cos", "tanh"],
                    allowed_binary_ops=["Add", "Sub", "Mult"],
                ),
                chunking=ChunkingConfig(enabled=True, strategy="ast_assignments", chunk_budget=2),
                prior=PriorConfig(enabled=False, lookback=0, decay=1.0, accept_boost=1.0, reject_penalty=1.0, min_weight=1.0),
            )

            accepted_snapshot = target.read_text(encoding="utf-8")
            step_results = [
                MutationResult(
                    original_text=accepted_snapshot,
                    updated_text=accepted_snapshot,
                    summary="constant patch: 1.0 -> 1.1",
                    details={"kind": "constant"},
                ),
                MutationResult(
                    original_text=accepted_snapshot,
                    updated_text=accepted_snapshot,
                    summary="constant patch: 1.1 -> 1.2",
                    details={"kind": "constant"},
                ),
            ]
            adapter = NumericDemoAdapter(root, config)
            accepted = AcceptedState(files={"train.py": accepted_snapshot}, label="train.py")
            proposal = Proposal(
                summary="test",
                scope_label="train.py",
                metadata={
                    "chunk_id": "assign:wave",
                    "chunk_span": "8-8",
                    "prior_weight": 1.0,
                    "prior_basis_revision": 0,
                    "mutation_kind_weights": {"constant": 1.0},
                    "step_iterations": [200, 201],
                },
            )

            with mock.patch("src.autoresearch_plus.numeric_demo_adapter.mutate_target_file", side_effect=step_results):
                candidate = adapter.materialize(accepted, proposal)

            self.assertIn(" | ", candidate.summary)
            self.assertEqual("constant,constant", candidate.metadata["mutation_kind"])


if __name__ == "__main__":
    unittest.main()
