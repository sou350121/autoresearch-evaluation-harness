from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.autoresearch_plus.prompt_demo_adapter import PromptDemoAdapter
from src.autoresearch_plus.models import AcceptedState, Candidate, Proposal


class PromptAdapterTests(unittest.TestCase):
    def test_evaluate_scores_improved_prompt_higher(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            prompt_dir.mkdir()
            prompt_path = prompt_dir / "prompt.md"
            prompt_path.write_text(
                "# Ticket Triage\n\n## Instructions\n- Classify the ticket.\n",
                encoding="utf-8",
            )
            adapter = PromptDemoAdapter(root, prompt_path=prompt_path)

            baseline = adapter.evaluate()
            adapter.materialize(
                AcceptedState(files={"demo_prompt\\prompt.md": prompt_path.read_text(encoding="utf-8")}, label="demo_prompt/prompt.md"),
                Proposal(
                    summary="improve prompt",
                    scope_label="demo_prompt/prompt.md",
                    metadata={
                        "section_id": "instructions",
                        "candidate_lines": [
                            "- Return valid JSON only.",
                            "- Use one label from: billing, technical, refund, other.",
                        ],
                    },
                ),
            )
            improved = adapter.evaluate()

            self.assertGreater(improved.score, baseline.score)

    def test_simple_rule_insertion_does_not_saturate_prompt_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "demo_prompt"
            prompt_dir.mkdir()
            prompt_path = prompt_dir / "prompt.md"
            prompt_path.write_text(
                "# Ticket Triage\n\n## Instructions\n- Classify the ticket.\n\n## Output\n- Return a structured result.\n",
                encoding="utf-8",
            )
            adapter = PromptDemoAdapter(root, prompt_path=prompt_path)

            baseline = adapter.evaluate()
            adapter.materialize(
                AcceptedState(files={"demo_prompt\\prompt.md": prompt_path.read_text(encoding="utf-8")}, label="demo_prompt/prompt.md"),
                Proposal(
                    summary="add two rules",
                    scope_label="demo_prompt/prompt.md",
                    metadata={
                        "section_id": "instructions",
                        "candidate_lines": [
                            "- Return valid JSON only.",
                            "- Use one label from: billing, technical, refund, other.",
                        ],
                    },
                ),
            )
            improved = adapter.evaluate()

            self.assertGreater(improved.score, baseline.score)
            self.assertLess(improved.score, 100.0)


if __name__ == "__main__":
    unittest.main()
