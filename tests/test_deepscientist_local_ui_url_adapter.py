from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import src.autoresearch_plus.llm_proposer as llm_proposer
from src.autoresearch_plus.deepscientist_local_ui_url_adapter import DeepScientistLocalUiUrlAdapter
from src.autoresearch_plus.models import AcceptedState


class DeepScientistLocalUiUrlAdapterTests(unittest.TestCase):
    def test_real_fixture_adapter_improves_test_score(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "demo_deepscientist_local_ui_url"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo = root / "demo_deepscientist_local_ui_url"
            shutil.copytree(fixture_root, demo)

            target = demo / "ui_url.py"
            adapter = DeepScientistLocalUiUrlAdapter(root, target_path=target, proposer_name="chunked_prior")
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

    def test_llm_proposer_can_select_url_fix(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        fixture_root = repo_root / "demo_deepscientist_local_ui_url"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo = root / "demo_deepscientist_local_ui_url"
            shutil.copytree(fixture_root, demo)

            target = demo / "ui_url.py"
            adapter = DeepScientistLocalUiUrlAdapter(root, target_path=target, proposer_name="llm_codex")

            original_select_fix_ids = llm_proposer.select_fix_ids

            def fake_select_fix_ids(**kwargs):
                return (
                    ["normalize_local_ui_url_to_loopback"],
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
            self.assertEqual(["normalize_local_ui_url_to_loopback"], proposal.metadata["fix_ids"])
            self.assertLess(baseline.score, improved.score)
            self.assertEqual(3.0, improved.score)


if __name__ == "__main__":
    unittest.main()
