from __future__ import annotations

import unittest

from src.autoresearch_plus.prior import build_prior


class PriorTests(unittest.TestCase):
    def test_build_prior_boosts_recent_accepted_chunk_and_kind(self) -> None:
        rows = [
            {"revision": "4", "decision": "reject", "metric_delta": "-0.2", "chunk_id": "assign:wave", "mutation_kind": "math_func"},
            {"revision": "5", "decision": "accept", "metric_delta": "0.3", "chunk_id": "assign:base", "mutation_kind": "constant"},
            {"revision": "6", "decision": "accept", "metric_delta": "0.1", "chunk_id": "assign:base", "mutation_kind": "constant"},
        ]

        prior = build_prior(
            rows=rows,
            chunk_ids=["assign:base", "assign:wave"],
            mutation_kinds=["constant", "math_func", "binary_op"],
            lookback=4,
            decay=0.8,
            accept_boost=1.5,
            reject_penalty=1.0,
            min_weight=0.2,
        )

        self.assertGreater(prior.chunk_weights["assign:base"], prior.chunk_weights["assign:wave"])
        self.assertGreater(prior.mutation_kind_weights["constant"], prior.mutation_kind_weights["math_func"])

    def test_build_prior_enforces_exploration_floor(self) -> None:
        prior = build_prior(
            rows=[],
            chunk_ids=["assign:base", "assign:wave"],
            mutation_kinds=["constant", "math_func", "binary_op"],
            lookback=5,
            decay=0.8,
            accept_boost=1.5,
            reject_penalty=1.0,
            min_weight=0.25,
        )

        self.assertEqual(0.25, prior.chunk_weights["assign:base"])
        self.assertEqual(0.25, prior.chunk_weights["assign:wave"])
        self.assertEqual(0.25, prior.mutation_kind_weights["binary_op"])

    def test_build_prior_tracks_latest_basis_revision(self) -> None:
        rows = [
            {"revision": "2", "decision": "accept", "metric_delta": "0.1", "chunk_id": "assign:base", "mutation_kind": "constant"},
            {"revision": "7", "decision": "reject", "metric_delta": "-0.1", "chunk_id": "assign:wave", "mutation_kind": "math_func"},
        ]

        prior = build_prior(
            rows=rows,
            chunk_ids=["assign:base", "assign:wave"],
            mutation_kinds=["constant", "math_func"],
            lookback=5,
            decay=0.9,
            accept_boost=1.0,
            reject_penalty=0.5,
            min_weight=0.2,
        )

        self.assertEqual(7, prior.basis_revision)


if __name__ == "__main__":
    unittest.main()
