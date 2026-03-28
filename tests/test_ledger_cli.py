from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.autoresearch_plus import cli
from src.autoresearch_plus.ledger import RunLedger
from src.autoresearch_plus.models import RunRecord


class LedgerCliCompatibilityTests(unittest.TestCase):
    def test_report_handles_legacy_results_without_git_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            runs.mkdir(parents=True)
            (runs / "results.tsv").write_text(
                "\t".join(
                    [
                        "revision",
                        "base_revision",
                        "decision",
                        "score",
                        "previous_score",
                        "metric_delta",
                        "status",
                        "summary",
                        "mutation",
                        "target_file",
                        "git_branch",
                        "git_commit",
                    ]
                )
                + "\n"
                + "\t".join(
                    [
                        "1",
                        "",
                        "accept",
                        "95.5",
                        "",
                        "",
                        "ok",
                        "Baseline accepted",
                        "baseline",
                        "demo_target/train.py",
                        "main",
                        "abc1234",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with mock.patch.object(cli, "_repo_root", return_value=root):
                with contextlib.redirect_stdout(output):
                    cli.cmd_report()

            rendered = output.getvalue()
            self.assertIn("best_accepted revision=1", rendered)
            self.assertIn("git_dirty=unknown", rendered)

    def test_append_writes_git_dirty_column_for_new_ledgers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = RunLedger(root)
            record = RunRecord(
                revision=1,
                base_revision=None,
                decision="accept",
                score=99.0,
                previous_score=None,
                metric_delta=None,
                status="ok",
                summary="Baseline accepted",
                mutation="baseline",
                target_file="demo_target/train.py",
                git_branch="main",
                git_commit="deadbee",
                git_dirty=True,
            )

            ledger.append(record, {"mode": "baseline"})
            text = ledger.results_path.read_text(encoding="utf-8")

            self.assertIn("git_dirty", text.splitlines()[0])
            self.assertIn("True", text.splitlines()[1])

    def test_append_migrates_legacy_header_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            runs.mkdir(parents=True)
            legacy = runs / "results.tsv"
            legacy.write_text(
                "\t".join(
                    [
                        "revision",
                        "base_revision",
                        "decision",
                        "score",
                        "previous_score",
                        "metric_delta",
                        "status",
                        "summary",
                        "mutation",
                        "target_file",
                        "git_branch",
                        "git_commit",
                    ]
                )
                + "\n"
                + "\t".join(
                    [
                        "1",
                        "",
                        "accept",
                        "95.5",
                        "",
                        "",
                        "ok",
                        "Baseline accepted",
                        "baseline",
                        "demo_target/train.py",
                        "main",
                        "abc1234",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            ledger = RunLedger(root)
            record = RunRecord(
                revision=2,
                base_revision=1,
                decision="reject",
                score=95.4,
                previous_score=95.5,
                metric_delta=-0.1,
                status="ok",
                summary="Rejected: no improvement",
                mutation="constant patch: 1.0 -> 1.1",
                target_file="demo_target/train.py",
                git_branch="main",
                git_commit="abc1234",
                git_dirty=False,
            )

            ledger.append(record, {"mode": "search"})
            rows = ledger.rows()
            text = legacy.read_text(encoding="utf-8").splitlines()

            self.assertIn("git_dirty", text[0].split("\t"))
            self.assertEqual("unknown", rows[0]["git_dirty"])
            self.assertEqual("False", rows[1]["git_dirty"])

    def test_scope_snapshot_round_trip_restores_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = RunLedger(root)
            files = {
                "a.txt": "alpha",
                "nested\\b.txt": "beta",
            }

            ledger.save_scope_snapshot(3, files)
            restored = ledger.load_scope_snapshot(3)

            self.assertEqual(files, restored)

    def test_append_experiment_writes_jsonl_memory_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = RunLedger(root)

            ledger.append_experiment(
                {
                    "revision": 2,
                    "branch_id": "branch-1",
                    "hypothesis_id": "ve_combo",
                    "outcome": "accept_candidate",
                }
            )

            lines = ledger.experiment_memory_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, len(lines))
            self.assertIn('"hypothesis_id": "ve_combo"', lines[0])

    def test_load_experiments_reads_jsonl_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = RunLedger(root)
            ledger.append_experiment({"hypothesis_id": "h1", "outcome": "reject_candidate"})
            ledger.append_experiment({"hypothesis_id": "h2", "outcome": "accept_candidate"})

            rows = ledger.load_experiments()

            self.assertEqual(2, len(rows))
            self.assertEqual("h1", rows[0]["hypothesis_id"])
            self.assertEqual("h2", rows[1]["hypothesis_id"])

    def test_report_prints_composite_trace_summary_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = RunLedger(root)
            accepted = RunRecord(
                revision=2,
                base_revision=1,
                decision="accept",
                score=17.0,
                previous_score=11.0,
                metric_delta=6.0,
                status="ok",
                summary="Accepted: score improved",
                mutation="composite",
                target_file="demo_prompt/prompt.md + demo_code_repair/calculator.py",
                git_branch="main",
                git_commit="feed123",
                git_dirty=False,
            )
            ledger.append(
                accepted,
                {
                    "mode": "search",
                    "score": 17.0,
                    "adapter_trace": {
                        "scoring_policy": "integration_threshold_bonus",
                        "integration_bonus": 2.0,
                        "saturated_stages": ["code_repair_stage"],
                        "stage_sequence": ["prompt_stage", "code_repair_stage"],
                        "stage_results": [
                            {"name": "prompt_stage", "status": "ok", "raw_score": 86.0, "normalized_score": 2.0},
                            {"name": "code_repair_stage", "status": "ok", "raw_score": 3.0, "normalized_score": 3.0},
                        ],
                    },
                },
            )
            rejected = RunRecord(
                revision=3,
                base_revision=2,
                decision="reject",
                score=17.0,
                previous_score=17.0,
                metric_delta=0.0,
                status="ok",
                summary="Rejected: all_stages_saturated",
                mutation="",
                target_file="demo_prompt/prompt.md + demo_code_repair/calculator.py",
                git_branch="main",
                git_commit="feed123",
                git_dirty=False,
            )
            ledger.append(
                rejected,
                {
                    "mode": "search",
                    "score": 17.0,
                    "skip_reason": "all_stages_saturated",
                    "adapter_trace": {
                        "scoring_policy": "integration_threshold_bonus",
                        "integration_bonus": 2.0,
                        "saturated_stages": ["code_repair_stage", "prompt_stage"],
                        "stage_sequence": [],
                        "stage_results": [
                            {"name": "prompt_stage", "status": "ok", "raw_score": 100.0, "normalized_score": 16.0},
                            {"name": "code_repair_stage", "status": "ok", "raw_score": 3.0, "normalized_score": 3.0},
                        ],
                    },
                },
            )

            output = io.StringIO()
            with mock.patch.object(cli, "_repo_root", return_value=root):
                with contextlib.redirect_stdout(output):
                    cli.cmd_report()

            rendered = output.getvalue()
            self.assertIn("best_accepted revision=2", rendered)
            self.assertIn("scoring_policy=integration_threshold_bonus", rendered)
            self.assertIn("integration_bonus=2.000000", rendered)
            self.assertIn("saturated_stages=code_repair_stage", rendered)
            self.assertIn("prompt_stage(raw=86.000000 normalized=2.000000 status=ok)", rendered)
            self.assertIn("code_repair_stage(raw=3.000000 normalized=3.000000 status=ok)", rendered)
            self.assertIn("latest_rejected revision=3 score=17.0 summary=Rejected: all_stages_saturated", rendered)
            self.assertIn("latest_rejected_composite_summary", rendered)
            self.assertIn("saturated_stages=code_repair_stage,prompt_stage", rendered)

    def test_report_prints_method_summary_for_hypothesis_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = RunLedger(root)
            accepted = RunRecord(
                revision=2,
                base_revision=1,
                decision="accept",
                score=0.962963,
                previous_score=0.887037,
                metric_delta=0.075926,
                status="ok",
                summary="Accepted: hypothesis branch improved",
                mutation="enable_lr_decay | enable_lr_warmup",
                target_file="demo_optimizer_schedule_proxy/task.py",
                git_branch="main",
                git_commit="feed123",
                git_dirty=False,
            )
            ledger.append(
                accepted,
                {
                    "mode": "search",
                    "score": 0.962963,
                    "proposal": {
                        "provider": "llm_codex",
                        "beam_role": "exploitation",
                        "hypothesis": {
                            "hypothesis_id": "optimizer_schedule_coupling",
                            "beam_role": "exploitation",
                            "operator_family": "schedule_combo_fix",
                            "target_locus": "optimizer_schedule",
                        },
                    },
                    "branch_results": [
                        {
                            "hypothesis": {
                                "hypothesis_id": "optimizer_schedule_coupling",
                                "beam_role": "exploitation",
                            },
                            "score": 0.962963,
                        },
                        {
                            "hypothesis": {
                                "hypothesis_id": "lower_base_lr_only",
                                "beam_role": "exploration",
                            },
                            "score": 0.937037,
                        },
                    ],
                },
            )

            output = io.StringIO()
            with mock.patch.object(cli, "_repo_root", return_value=root):
                with contextlib.redirect_stdout(output):
                    cli.cmd_report()

            rendered = output.getvalue()
            self.assertIn("method_summary", rendered)
            self.assertIn("hypothesis=optimizer_schedule_coupling", rendered)
            self.assertIn("beam_role=exploitation", rendered)
            self.assertIn("operator_family=schedule_combo_fix", rendered)
            self.assertIn("branch_beam_summary", rendered)
            self.assertIn("optimizer_schedule_coupling:exploitation:0.962963", rendered)
            self.assertIn("lower_base_lr_only:exploration:0.937037", rendered)


if __name__ == "__main__":
    unittest.main()
