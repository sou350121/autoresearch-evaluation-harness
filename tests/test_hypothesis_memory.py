from __future__ import annotations

import unittest

from src.autoresearch_plus.hypothesis_memory import (
    drop_pure_reject_hypotheses,
    label_hypothesis_beam_roles,
    prioritize_retained_hypotheses,
    select_hypothesis_beam,
    summarize_hypothesis_memory,
)
from src.autoresearch_plus.models import Hypothesis


class HypothesisMemoryTests(unittest.TestCase):
    def test_summarize_hypothesis_memory_counts_accepts_rejects_and_retained(self) -> None:
        stats = summarize_hypothesis_memory(
            [
                {"hypothesis_id": "h1", "outcome": "reject_candidate", "retained": False},
                {"hypothesis_id": "h1", "outcome": "accept_candidate", "retained": True},
                {"hypothesis_id": "h2", "outcome": "reject_candidate", "retained": False},
            ]
        )

        self.assertEqual(1, stats["h1"].accepts)
        self.assertEqual(1, stats["h1"].rejects)
        self.assertEqual(1, stats["h1"].retained_accepts)
        self.assertEqual(0, stats["h2"].accepts)
        self.assertEqual(1, stats["h2"].rejects)

    def test_drop_pure_reject_hypotheses_removes_only_unproven_failures(self) -> None:
        hypotheses = [
            Hypothesis(
                hypothesis_id="h_reject",
                problem_frame="toy",
                target_locus="a",
                mechanism_guess="reject",
                operator_family="single",
                expected_signal="up",
                risk="medium",
                patch_budget=1,
            ),
            Hypothesis(
                hypothesis_id="h_accept",
                problem_frame="toy",
                target_locus="b",
                mechanism_guess="accept",
                operator_family="combo",
                expected_signal="up",
                risk="low",
                patch_budget=1,
            ),
        ]
        stats = summarize_hypothesis_memory(
            [
                {"hypothesis_id": "h_reject", "outcome": "reject_candidate", "retained": False},
                {"hypothesis_id": "h_accept", "outcome": "accept_candidate", "retained": True},
            ]
        )

        filtered = drop_pure_reject_hypotheses(hypotheses, stats)

        self.assertEqual(["h_accept"], [item.hypothesis_id for item in filtered])

    def test_prioritize_retained_hypotheses_moves_retained_evidence_to_front(self) -> None:
        hypotheses = [
            Hypothesis(
                hypothesis_id="h_neutral",
                problem_frame="toy",
                target_locus="a",
                mechanism_guess="neutral",
                operator_family="single",
                expected_signal="up",
                risk="medium",
                patch_budget=1,
            ),
            Hypothesis(
                hypothesis_id="h_retained",
                problem_frame="toy",
                target_locus="b",
                mechanism_guess="retained",
                operator_family="combo",
                expected_signal="up",
                risk="low",
                patch_budget=1,
            ),
        ]
        stats = summarize_hypothesis_memory(
            [
                {"hypothesis_id": "h_retained", "outcome": "accept_candidate", "retained": True},
            ]
        )

        ranked = prioritize_retained_hypotheses(hypotheses, stats)

        self.assertEqual(["h_retained", "h_neutral"], [item.hypothesis_id for item in ranked])

    def test_select_hypothesis_beam_prefers_retained_then_untried(self) -> None:
        hypotheses = [
            Hypothesis(
                hypothesis_id="h_explored_not_retained",
                problem_frame="toy",
                target_locus="a",
                mechanism_guess="explored",
                operator_family="single",
                expected_signal="up",
                risk="medium",
                patch_budget=1,
            ),
            Hypothesis(
                hypothesis_id="h_retained",
                problem_frame="toy",
                target_locus="b",
                mechanism_guess="retained",
                operator_family="combo",
                expected_signal="up",
                risk="low",
                patch_budget=1,
            ),
            Hypothesis(
                hypothesis_id="h_untried",
                problem_frame="toy",
                target_locus="c",
                mechanism_guess="untried",
                operator_family="single",
                expected_signal="up",
                risk="medium",
                patch_budget=1,
            ),
        ]
        stats = summarize_hypothesis_memory(
            [
                {"hypothesis_id": "h_explored_not_retained", "outcome": "accept_candidate", "retained": False},
                {"hypothesis_id": "h_retained", "outcome": "accept_candidate", "retained": True},
            ]
        )

        selected = select_hypothesis_beam(hypotheses, stats, width=2)

        self.assertEqual(["h_retained", "h_untried"], [item.hypothesis_id for item in selected])

    def test_label_hypothesis_beam_roles_marks_exploitation_and_exploration(self) -> None:
        hypotheses = [
            Hypothesis(
                hypothesis_id="h_retained",
                problem_frame="toy",
                target_locus="a",
                mechanism_guess="retained",
                operator_family="combo",
                expected_signal="up",
                risk="low",
                patch_budget=1,
            ),
            Hypothesis(
                hypothesis_id="h_untried",
                problem_frame="toy",
                target_locus="b",
                mechanism_guess="untried",
                operator_family="single",
                expected_signal="up",
                risk="medium",
                patch_budget=1,
            ),
        ]
        stats = summarize_hypothesis_memory(
            [
                {"hypothesis_id": "h_retained", "outcome": "accept_candidate", "retained": True},
            ]
        )

        labeled = label_hypothesis_beam_roles(hypotheses, stats)

        self.assertEqual("exploitation", labeled[0].metadata["beam_role"])
        self.assertEqual("exploration", labeled[1].metadata["beam_role"])


if __name__ == "__main__":
    unittest.main()
