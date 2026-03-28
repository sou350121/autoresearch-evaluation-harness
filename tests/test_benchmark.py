from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.autoresearch_plus import cli
from src.autoresearch_plus import benchmark
from src.autoresearch_plus.benchmark import (
    _modes_for_task,
    _normalize_selected_tasks,
    _rewrite_config,
    render_benchmark_summary,
    run_ab_benchmark,
    summarize_trials,
)


class BenchmarkTests(unittest.TestCase):
    def test_summarize_trials_aggregates_best_score_and_accepts(self) -> None:
        summary = summarize_trials(
            [
                {"mode": "single_step_random", "best_score": 99.6, "accepted_count": 1},
                {"mode": "single_step_random", "best_score": 99.8, "accepted_count": 0},
                {"mode": "chunked_prior", "best_score": 99.9, "accepted_count": 2},
                {"mode": "chunked_prior", "best_score": 99.7, "accepted_count": 1},
            ]
        )

        self.assertEqual(2, summary["single_step_random"]["trials"])
        self.assertEqual(99.8, summary["single_step_random"]["best_score"])
        self.assertEqual(1, summary["single_step_random"]["total_accepts"])
        self.assertEqual(99.9, summary["chunked_prior"]["best_score"])
        self.assertEqual(3, summary["chunked_prior"]["total_accepts"])

    def test_summarize_trials_keeps_task_and_mode_separate(self) -> None:
        summary = summarize_trials(
            [
                {"task": "numeric", "mode": "single_step_random", "best_score": 99.6, "accepted_count": 1},
                {"task": "prompt", "mode": "single_step_random", "best_score": 97.0, "accepted_count": 2},
            ]
        )

        self.assertIn("numeric:single_step_random", summary)
        self.assertIn("prompt:single_step_random", summary)

    def test_rewrite_config_supports_mixed_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            _rewrite_config(
                root,
                task="mixed",
                proposer="chunked_prior",
                chunking_enabled=True,
                chunk_budget=2,
                prior_enabled=True,
            )

            text = (root / "config" / "project.toml").read_text(encoding="utf-8")
            self.assertIn('adapter = "mixed_prompt_code_repair_demo"', text)
            self.assertIn('edit_scope = ["demo_prompt/prompt.md", "demo_code_repair/calculator.py"]', text)
            self.assertIn('composite_stage_order = ["prompt_stage", "code_repair_stage"]', text)

    def test_rewrite_config_supports_dl_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            _rewrite_config(
                root,
                task="digits_image_classification",
                proposer="chunked_prior",
                chunking_enabled=True,
                chunk_budget=2,
                prior_enabled=True,
            )

            text = (root / "config" / "project.toml").read_text(encoding="utf-8")
            self.assertIn('adapter = "digits_image_classification_demo"', text)
            self.assertIn('edit_scope = ["demo_digits_image_classification/task.py"]', text)
            self.assertIn('evaluation_command = "python demo_digits_image_classification/eval.py"', text)

    def test_rewrite_config_supports_ve_gate_proxy_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            _rewrite_config(
                root,
                task="ve_gate_proxy",
                proposer="llm_codex",
                chunking_enabled=False,
                chunk_budget=1,
                prior_enabled=False,
            )

            text = (root / "config" / "project.toml").read_text(encoding="utf-8")
            self.assertIn('adapter = "ve_gate_proxy_demo"', text)
            self.assertIn('edit_scope = ["demo_ve_gate_proxy/task.py"]', text)
            self.assertIn('evaluation_command = "python demo_ve_gate_proxy/eval.py"', text)

    def test_rewrite_config_supports_optimizer_schedule_proxy_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            _rewrite_config(
                root,
                task="optimizer_schedule_proxy",
                proposer="llm_codex",
                chunking_enabled=False,
                chunk_budget=1,
                prior_enabled=False,
            )

            text = (root / "config" / "project.toml").read_text(encoding="utf-8")
            self.assertIn('adapter = "optimizer_schedule_proxy_demo"', text)
            self.assertIn('edit_scope = ["demo_optimizer_schedule_proxy/task.py"]', text)
            self.assertIn('evaluation_command = "python demo_optimizer_schedule_proxy/eval.py"', text)

    def test_rewrite_config_supports_capacity_budget_proxy_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            _rewrite_config(
                root,
                task="capacity_budget_proxy",
                proposer="llm_codex",
                chunking_enabled=False,
                chunk_budget=1,
                prior_enabled=False,
            )

            text = (root / "config" / "project.toml").read_text(encoding="utf-8")
            self.assertIn('adapter = "capacity_budget_proxy_demo"', text)
            self.assertIn('edit_scope = ["demo_capacity_budget_proxy/task.py"]', text)
            self.assertIn('evaluation_command = "python demo_capacity_budget_proxy/eval.py"', text)

    def test_rewrite_config_supports_wine_held_out_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            _rewrite_config(
                root,
                task="wine_classification",
                proposer="llm_codex",
                chunking_enabled=False,
                chunk_budget=1,
                prior_enabled=False,
            )

            text = (root / "config" / "project.toml").read_text(encoding="utf-8")
            self.assertIn('adapter = "wine_classification_demo"', text)
            self.assertIn('edit_scope = ["demo_wine_classification/task.py"]', text)
            self.assertIn('evaluation_command = "python demo_wine_classification/eval.py"', text)

    def test_rewrite_config_supports_friedman1_held_out_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            _rewrite_config(
                root,
                task="friedman1_regression",
                proposer="llm_codex",
                chunking_enabled=False,
                chunk_budget=1,
                prior_enabled=False,
            )

            text = (root / "config" / "project.toml").read_text(encoding="utf-8")
            self.assertIn('adapter = "friedman1_regression_demo"', text)
            self.assertIn('edit_scope = ["demo_friedman1_regression/task.py"]', text)
            self.assertIn('evaluation_command = "python demo_friedman1_regression/eval.py"', text)

    def test_modes_for_task_adds_llm_only_for_dl_tasks(self) -> None:
        digits_modes = _modes_for_task("digits_image_classification")
        prompt_modes = _modes_for_task("prompt")

        self.assertEqual(
            ["single_step_random", "chunked_prior", "llm_codex_no_memory", "llm_codex_memory_retry"],
            [str(mode["mode"]) for mode in digits_modes],
        )
        self.assertEqual(
            ["single_step_random", "chunked_prior", "llm_codex_no_memory", "llm_codex_memory_retry"],
            [str(mode["mode"]) for mode in _modes_for_task("ve_gate_proxy")],
        )
        self.assertEqual(
            ["single_step_random", "chunked_prior", "llm_codex_no_memory", "llm_codex_memory_retry"],
            [str(mode["mode"]) for mode in _modes_for_task("optimizer_schedule_proxy")],
        )
        self.assertEqual(
            ["single_step_random", "chunked_prior", "llm_codex_no_memory", "llm_codex_memory_retry"],
            [str(mode["mode"]) for mode in _modes_for_task("capacity_budget_proxy")],
        )
        self.assertEqual(
            ["single_step_random", "chunked_prior", "llm_codex_no_memory", "llm_codex_memory_retry"],
            [str(mode["mode"]) for mode in prompt_modes],
        )

    def test_summarize_trials_computes_multi_task_metrics(self) -> None:
        summary = summarize_trials(
            [
                {
                    "task": "mixed",
                    "task_family": "mixed",
                    "mode": "chunked_prior",
                    "trial": 1,
                    "trial_status": "ok",
                    "baseline_score": 1.0,
                    "best_score": 7.0,
                    "score_delta": 6.0,
                    "accepted_count": 1,
                    "iterations_completed": 1,
                    "first_accept_iteration": 1,
                },
                {
                    "task": "mixed",
                    "task_family": "mixed",
                    "mode": "chunked_prior",
                    "trial": 2,
                    "trial_status": "ok",
                    "baseline_score": 1.0,
                    "best_score": 1.0,
                    "score_delta": 0.0,
                    "accepted_count": 0,
                    "iterations_completed": 1,
                    "first_accept_iteration": None,
                },
            ]
        )

        bucket = summary["mixed:chunked_prior"]
        self.assertEqual(2, bucket["trials"])
        self.assertEqual(1, bucket["improved_trials"])
        self.assertEqual(0.5, bucket["success_rate"])
        self.assertEqual(3.0, bucket["median_gain"])
        self.assertEqual(1.0, bucket["median_first_accept_iter"])
        self.assertEqual(0.5, bucket["accept_precision"])

    def test_render_benchmark_summary_groups_rows_by_task(self) -> None:
        summary = {
            "numeric:single_step_random": {
                "task": "numeric",
                "task_family": "core/code",
                "task_tag": "toy/demo",
                "mode": "single_step_random",
                "trials": 2,
                "best_score": 99.8,
                "success_rate": 0.5,
                "median_gain": 0.2,
                "median_first_accept_iter": 3.0,
                "accept_precision": 0.25,
                "trial_failure_rate": 0.0,
            },
            "numeric:chunked_prior": {
                "task": "numeric",
                "task_family": "core/code",
                "task_tag": "toy/demo",
                "mode": "chunked_prior",
                "trials": 2,
                "best_score": 99.9,
                "success_rate": 1.0,
                "median_gain": 0.4,
                "median_first_accept_iter": 1.0,
                "accept_precision": 0.5,
                "trial_failure_rate": 0.0,
            },
        }

        rendered = render_benchmark_summary(summary, iterations=8, trials=2)

        self.assertIn("benchmark iterations=8 trials=2 tasks=1", rendered)
        self.assertIn("core/code", rendered)
        self.assertIn("numeric [toy/demo]", rendered)
        self.assertIn("single_step_random", rendered)
        self.assertIn("success=0.500", rendered)
        self.assertIn("median_gain=0.200000", rendered)
        self.assertIn("first_accept=3.0", rendered)
        self.assertIn("accept_precision=0.250", rendered)
        self.assertIn("trial_failure_rate=0.000", rendered)

    def test_cmd_benchmark_uses_grouped_rendered_summary(self) -> None:
        trials_data = [
            {
                "task": "mixed",
                "task_family": "mixed",
                "mode": "chunked_prior",
                "trial": 1,
                "trial_status": "ok",
                "baseline_score": 1.0,
                "best_score": 7.0,
                "score_delta": 6.0,
                "accepted_count": 1,
                "iterations_completed": 1,
                "first_accept_iteration": 1,
            }
        ]

        output = io.StringIO()
        with mock.patch.object(cli, "run_ab_benchmark", return_value=trials_data):
            with contextlib.redirect_stdout(output):
                cli.cmd_benchmark(iterations=8, trials=1)

        rendered = output.getvalue()
        self.assertIn("benchmark iterations=8 trials=1 tasks=1", rendered)
        self.assertIn("mixed", rendered)
        self.assertIn("chunked_prior", rendered)

    def test_cmd_benchmark_passes_selected_tasks(self) -> None:
        with mock.patch.object(cli, "run_ab_benchmark", return_value=[]) as run_mock:
            with mock.patch.object(cli, "render_benchmark_summary", return_value="ok"):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    cli.cmd_benchmark(iterations=4, trials=3, tasks=["circles_classification", "diabetes_regression"])

        run_mock.assert_called_once_with(
            cli._repo_root(),
            4,
            3,
            tasks=["circles_classification", "diabetes_regression"],
        )
        self.assertIn("ok", output.getvalue())

    def test_normalize_selected_tasks_keeps_order_and_deduplicates(self) -> None:
        self.assertEqual(
            ["prompt", "bugfix"],
            _normalize_selected_tasks(["prompt", "prompt", "bugfix"]),
        )

    def test_normalize_selected_tasks_excludes_held_out_by_default(self) -> None:
        selected = _normalize_selected_tasks(None)

        self.assertIn("prompt", selected)
        self.assertNotIn("wine_classification", selected)

    def test_normalize_selected_tasks_allows_explicit_held_out_selection(self) -> None:
        self.assertEqual(
            ["wine_classification"],
            _normalize_selected_tasks(["wine_classification"]),
        )

    def test_normalize_selected_tasks_rejects_unknown_task(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown benchmark task"):
            _normalize_selected_tasks(["prompt", "not_a_task"])

    def test_run_ab_benchmark_uses_trial_runner_once_per_trial(self) -> None:
        task_info = {
            "family": "core/code",
            "tag": "toy/demo",
            "supports_llm": False,
            "max_fix_budget": 1,
            "adapter": "prompt_demo",
            "edit_scope": ["demo_prompt/prompt.md"],
            "target_file": "demo_prompt/prompt.md",
            "evaluation_command": "python demo_prompt/eval.py",
            "composite_stage_order": [],
        }

        calls: list[tuple[str, str, int, int]] = []

        def fake_runner(root: Path, task: str, mode: dict[str, object], trial_index: int, iterations: int) -> dict[str, object]:
            calls.append((str(root), str(mode["mode"]), trial_index, iterations))
            return {
                "task": task,
                "task_family": task_info["family"],
                "task_tag": task_info["tag"],
                "mode": str(mode["mode"]),
                "trial": trial_index + 1,
                "trial_status": "ok",
                "baseline_score": 1.0,
                "best_score": 2.0,
                "score_delta": 1.0,
                "accepted_count": 1,
                "iterations_completed": 1,
                "first_accept_iteration": 1,
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.dict(benchmark.TASKS, {"prompt": task_info}, clear=True):
                results = run_ab_benchmark(root, iterations=4, trials=3, trial_runner=fake_runner)

        self.assertEqual(6, len(results))
        self.assertEqual(6, len(calls))
        self.assertEqual(["single_step_random", "single_step_random", "single_step_random", "chunked_prior", "chunked_prior", "chunked_prior"], [mode for _, mode, _, _ in calls])
        self.assertTrue(all(iterations == 4 for _, _, _, iterations in calls))

    def test_run_ab_benchmark_filters_to_selected_tasks(self) -> None:
        prompt_info = {
            "family": "core/code",
            "tag": "toy/demo",
            "supports_llm": False,
            "max_fix_budget": 1,
            "adapter": "prompt_demo",
            "edit_scope": ["demo_prompt/prompt.md"],
            "target_file": "demo_prompt/prompt.md",
            "evaluation_command": "python demo_prompt/eval.py",
            "composite_stage_order": [],
        }
        bugfix_info = {
            "family": "core/code",
            "tag": "toy/demo",
            "supports_llm": False,
            "max_fix_budget": 1,
            "adapter": "bugfix_demo",
            "edit_scope": ["demo_bugfix/buggy_math.py"],
            "target_file": "demo_bugfix/buggy_math.py",
            "evaluation_command": "python demo_bugfix/eval.py",
            "composite_stage_order": [],
        }
        calls: list[str] = []

        def fake_runner(root: Path, task: str, mode: dict[str, object], trial_index: int, iterations: int) -> dict[str, object]:
            calls.append(task)
            return {
                "task": task,
                "task_family": "core/code",
                "task_tag": "toy/demo",
                "mode": str(mode["mode"]),
                "trial": trial_index + 1,
                "trial_status": "ok",
                "baseline_score": 1.0,
                "best_score": 2.0,
                "score_delta": 1.0,
                "accepted_count": 1,
                "iterations_completed": 1,
                "first_accept_iteration": 1,
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.dict(benchmark.TASKS, {"prompt": prompt_info, "bugfix": bugfix_info}, clear=True):
                results = run_ab_benchmark(
                    root,
                    iterations=4,
                    trials=1,
                    tasks=["bugfix"],
                    trial_runner=fake_runner,
                )

        self.assertEqual(2, len(results))
        self.assertEqual(["bugfix", "bugfix"], calls)

    def test_run_single_trial_subprocess_returns_failed_trial_on_nonzero_exit(self) -> None:
        mode = {
            "mode": "llm_codex_no_memory",
            "proposer": "llm_codex",
            "chunking_enabled": False,
            "chunk_budget": 1,
            "prior_enabled": False,
            "max_fix_budget": 1,
            "llm_memory_enabled": False,
            "llm_retry_enabled": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(
                benchmark.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(args=["python"], returncode=1, stdout="", stderr="boom"),
            ):
                result = benchmark._run_single_trial_subprocess(root, "prompt", mode, 0, 4)

        self.assertEqual("failed", result["trial_status"])
        self.assertEqual("llm_codex_no_memory", result["mode"])
        self.assertIn("boom", str(result["error"]))


if __name__ == "__main__":
    unittest.main()
