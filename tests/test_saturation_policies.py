from __future__ import annotations

import unittest

from src.autoresearch_plus.saturation_policies import make_threshold_saturation_policy


class SaturationPolicyTests(unittest.TestCase):
    def test_threshold_policy_marks_only_stages_at_or_above_threshold(self) -> None:
        policy = make_threshold_saturation_policy(
            {
                "prompt_stage": 100.0,
                "code_repair_stage": 3.0,
            }
        )

        saturated = policy(
            [
                {"name": "prompt_stage", "raw_score": 100.0, "normalized_score": 16.0, "status": "ok"},
                {"name": "code_repair_stage", "raw_score": 2.0, "normalized_score": 2.0, "status": "ok"},
            ]
        )

        self.assertEqual({"prompt_stage"}, saturated)


if __name__ == "__main__":
    unittest.main()
