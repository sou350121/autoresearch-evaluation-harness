from __future__ import annotations

import unittest
from pathlib import Path

from src.autoresearch_plus.llm_proposer import _build_codex_command, select_fix_ids


class LlmProposerTests(unittest.TestCase):
    def test_build_codex_command_skips_git_repo_check(self) -> None:
        command = _build_codex_command(
            codex_binary="codex",
            cwd=Path("repo"),
            schema_path=Path("schema.json"),
            output_path=Path("output.json"),
        )

        self.assertIn("--skip-git-repo-check", command)

    def test_select_fix_ids_filters_unknown_ids_and_respects_budget(self) -> None:
        def fake_runner(*, prompt: str, cwd: Path) -> str:
            self.assertIn("fix_alpha", prompt)
            self.assertIn("fix_beta", prompt)
            return '{"selected_fix_ids":["fix_beta","unknown_fix","fix_alpha"],"summary":"pick beta then alpha"}'

        selected, metadata = select_fix_ids(
            root=Path("."),
            scope_label="demo.py",
            source_text="print('demo')",
            eval_output="FAIL",
            fix_catalog={
                "fix_alpha": "alpha summary",
                "fix_beta": "beta summary",
            },
            budget=1,
            runner=fake_runner,
        )

        self.assertEqual(["fix_beta"], selected)
        self.assertEqual("llm_codex", metadata["provider"])
        self.assertFalse(metadata["fallback_used"])

    def test_select_fix_ids_includes_memory_summary_when_provided(self) -> None:
        def fake_runner(*, prompt: str, cwd: Path) -> str:
            self.assertIn("Recent method memory:", prompt)
            self.assertIn("optimizer_schedule_coupling", prompt)
            return '{"selected_fix_ids":["fix_alpha"],"summary":"use retained method"}'

        selected, metadata = select_fix_ids(
            root=Path("."),
            scope_label="demo.py",
            source_text="print('demo')",
            eval_output="FAIL",
            fix_catalog={
                "fix_alpha": "alpha summary",
                "fix_beta": "beta summary",
            },
            budget=1,
            memory_summary="optimizer_schedule_coupling retained_accepts=1 rejects=0",
            runner=fake_runner,
        )

        self.assertEqual(["fix_alpha"], selected)
        self.assertFalse(metadata["fallback_used"])

    def test_select_fix_ids_falls_back_to_catalog_order_on_invalid_response(self) -> None:
        def fake_runner(*, prompt: str, cwd: Path) -> str:
            return "not-json"

        selected, metadata = select_fix_ids(
            root=Path("."),
            scope_label="demo.py",
            source_text="print('demo')",
            eval_output="FAIL",
            fix_catalog={
                "fix_alpha": "alpha summary",
                "fix_beta": "beta summary",
            },
            budget=2,
            runner=fake_runner,
        )

        self.assertEqual(["fix_alpha", "fix_beta"], selected)
        self.assertTrue(metadata["fallback_used"])
        self.assertIn("not-json", metadata["raw_response"])


if __name__ == "__main__":
    unittest.main()
