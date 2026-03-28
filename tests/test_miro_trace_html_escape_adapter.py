from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import src.autoresearch_plus.llm_proposer as llm_proposer
from src.autoresearch_plus.miro_trace_html_escape_adapter import MiroTraceHtmlEscapeAdapter
from src.autoresearch_plus.models import AcceptedState


class MiroTraceHtmlEscapeAdapterTests(unittest.TestCase):
    def test_real_fixture_adapter_improves_test_score(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "demo_miro_trace_html_escape"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo = root / "demo_miro_trace_html_escape"
            shutil.copytree(fixture_root, demo)

            target = demo / "renderer.py"
            adapter = MiroTraceHtmlEscapeAdapter(root, target_path=target, proposer_name="chunked_prior")
            baseline = adapter.evaluate()
            accepted = AcceptedState(
                files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
                label=adapter.scope_label,
            )
            proposal = adapter.propose(accepted, history=[], revision=1)
            adapter.materialize(accepted, proposal)
            improved = adapter.evaluate()

            self.assertLess(baseline.score, improved.score)
            self.assertEqual(3.0, improved.score)

    def test_llm_proposer_can_select_html_escape_fix(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "demo_miro_trace_html_escape"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo = root / "demo_miro_trace_html_escape"
            shutil.copytree(fixture_root, demo)

            target = demo / "renderer.py"
            adapter = MiroTraceHtmlEscapeAdapter(root, target_path=target, proposer_name="llm_codex")

            original_select_fix_ids = llm_proposer.select_fix_ids

            def fake_select_fix_ids(**kwargs):
                return (
                    ["escape_user_fields_in_html_renderers"],
                    {"provider": "llm_codex", "fallback_used": False, "raw_response": "{}"},
                )

            llm_proposer.select_fix_ids = fake_select_fix_ids
            try:
                baseline = adapter.evaluate()
                accepted = AcceptedState(
                    files={adapter.scope_label.replace("/", "\\"): target.read_text(encoding="utf-8")},
                    label=adapter.scope_label,
                )
                proposal = adapter.propose(accepted, history=[], revision=1)
                adapter.materialize(accepted, proposal)
                improved = adapter.evaluate()
            finally:
                llm_proposer.select_fix_ids = original_select_fix_ids

            self.assertEqual("llm_codex", proposal.metadata["proposal_kind"])
            self.assertEqual(["escape_user_fields_in_html_renderers"], proposal.metadata["fix_ids"])
            self.assertLess(baseline.score, improved.score)
            self.assertEqual(3.0, improved.score)


if __name__ == "__main__":
    unittest.main()
