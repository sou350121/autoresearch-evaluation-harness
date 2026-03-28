from __future__ import annotations

import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from .ledger import RunLedger
from .loop import run_baseline, run_search

TASKS: dict[str, dict[str, object]] = {
    "numeric": {
        "family": "core/code",
        "tag": "toy/demo",
        "supports_llm": False,
        "max_fix_budget": 1,
        "adapter": "numeric_demo",
        "edit_scope": ["demo_target/train.py"],
        "target_file": "demo_target/train.py",
        "evaluation_command": "python demo_target/eval.py",
        "composite_stage_order": [],
    },
    "prompt": {
        "family": "core/code",
        "tag": "toy/demo",
        "supports_llm": True,
        "max_fix_budget": 1,
        "adapter": "prompt_demo",
        "edit_scope": ["demo_prompt/prompt.md"],
        "target_file": "demo_prompt/prompt.md",
        "evaluation_command": "python demo_prompt/eval.py",
        "composite_stage_order": [],
    },
    "bugfix": {
        "family": "core/code",
        "tag": "toy/demo",
        "supports_llm": True,
        "max_fix_budget": 1,
        "adapter": "bugfix_demo",
        "edit_scope": ["demo_bugfix/buggy_math.py"],
        "target_file": "demo_bugfix/buggy_math.py",
        "evaluation_command": "python demo_bugfix/eval.py",
        "composite_stage_order": [],
    },
    "code_repair": {
        "family": "core/code",
        "tag": "toy/demo",
        "supports_llm": True,
        "max_fix_budget": 1,
        "adapter": "code_repair_demo",
        "edit_scope": ["demo_code_repair/calculator.py"],
        "target_file": "demo_code_repair/calculator.py",
        "evaluation_command": "python demo_code_repair/eval.py",
        "composite_stage_order": [],
    },
    "mixed": {
        "family": "mixed",
        "tag": "toy/demo",
        "supports_llm": True,
        "max_fix_budget": 1,
        "adapter": "mixed_prompt_code_repair_demo",
        "edit_scope": ["demo_prompt/prompt.md", "demo_code_repair/calculator.py"],
        "target_file": "demo_prompt/prompt.md",
        "evaluation_command": "python demo_prompt/eval.py",
        "composite_stage_order": ["prompt_stage", "code_repair_stage"],
    },
    "mixed_bugfix": {
        "family": "mixed",
        "tag": "toy/demo",
        "supports_llm": True,
        "max_fix_budget": 1,
        "adapter": "mixed_prompt_bugfix_demo",
        "edit_scope": ["demo_prompt/prompt.md", "demo_bugfix/buggy_math.py"],
        "target_file": "demo_prompt/prompt.md",
        "evaluation_command": "python demo_prompt/eval.py",
        "composite_stage_order": ["prompt_stage", "bugfix_stage"],
    },
    "miro_trace_parser": {
        "family": "real-fixture",
        "tag": "real-fixture",
        "supports_llm": True,
        "max_fix_budget": 3,
        "adapter": "miro_trace_parser_demo",
        "edit_scope": ["demo_miro_trace_parser/trace_analyzer.py"],
        "target_file": "demo_miro_trace_parser/trace_analyzer.py",
        "evaluation_command": "python demo_miro_trace_parser/eval.py",
        "composite_stage_order": [],
    },
    "miro_trace_html_escape": {
        "family": "real-fixture",
        "tag": "real-fixture",
        "supports_llm": True,
        "max_fix_budget": 1,
        "adapter": "miro_trace_html_escape_demo",
        "edit_scope": ["demo_miro_trace_html_escape/renderer.py"],
        "target_file": "demo_miro_trace_html_escape/renderer.py",
        "evaluation_command": "python demo_miro_trace_html_escape/eval.py",
        "composite_stage_order": [],
    },
    "deepscientist_local_ui_url": {
        "family": "real-fixture",
        "tag": "real-fixture",
        "supports_llm": True,
        "max_fix_budget": 1,
        "adapter": "deepscientist_local_ui_url_demo",
        "edit_scope": ["demo_deepscientist_local_ui_url/ui_url.py"],
        "target_file": "demo_deepscientist_local_ui_url/ui_url.py",
        "evaluation_command": "python demo_deepscientist_local_ui_url/eval.py",
        "composite_stage_order": [],
    },
    "circles_classification": {
        "family": "dl/proxy",
        "tag": "proxy",
        "supports_llm": True,
        "max_fix_budget": 3,
        "adapter": "circles_classification_demo",
        "edit_scope": ["demo_circles_classification/task.py"],
        "target_file": "demo_circles_classification/task.py",
        "evaluation_command": "python demo_circles_classification/eval.py",
        "composite_stage_order": [],
    },
    "digits_image_classification": {
        "family": "dl/proxy",
        "tag": "proxy",
        "supports_llm": True,
        "max_fix_budget": 3,
        "adapter": "digits_image_classification_demo",
        "edit_scope": ["demo_digits_image_classification/task.py"],
        "target_file": "demo_digits_image_classification/task.py",
        "evaluation_command": "python demo_digits_image_classification/eval.py",
        "composite_stage_order": [],
    },
    "diabetes_regression": {
        "family": "dl/proxy",
        "tag": "proxy",
        "supports_llm": True,
        "max_fix_budget": 3,
        "adapter": "diabetes_regression_demo",
        "edit_scope": ["demo_diabetes_regression/task.py"],
        "target_file": "demo_diabetes_regression/task.py",
        "evaluation_command": "python demo_diabetes_regression/eval.py",
        "composite_stage_order": [],
    },
    "friedman1_regression": {
        "family": "held-out",
        "tag": "held-out",
        "supports_llm": True,
        "max_fix_budget": 3,
        "adapter": "friedman1_regression_demo",
        "edit_scope": ["demo_friedman1_regression/task.py"],
        "target_file": "demo_friedman1_regression/task.py",
        "evaluation_command": "python demo_friedman1_regression/eval.py",
        "composite_stage_order": [],
    },
    "breast_cancer_classification": {
        "family": "dl/proxy",
        "tag": "proxy",
        "supports_llm": True,
        "max_fix_budget": 3,
        "adapter": "breast_cancer_classification_demo",
        "edit_scope": ["demo_breast_cancer_classification/task.py"],
        "target_file": "demo_breast_cancer_classification/task.py",
        "evaluation_command": "python demo_breast_cancer_classification/eval.py",
        "composite_stage_order": [],
    },
    "wine_classification": {
        "family": "held-out",
        "tag": "held-out",
        "supports_llm": True,
        "max_fix_budget": 3,
        "adapter": "wine_classification_demo",
        "edit_scope": ["demo_wine_classification/task.py"],
        "target_file": "demo_wine_classification/task.py",
        "evaluation_command": "python demo_wine_classification/eval.py",
        "composite_stage_order": [],
    },
    "ve_gate_proxy": {
        "family": "dl/proxy",
        "tag": "proxy",
        "supports_llm": True,
        "max_fix_budget": 2,
        "adapter": "ve_gate_proxy_demo",
        "edit_scope": ["demo_ve_gate_proxy/task.py"],
        "target_file": "demo_ve_gate_proxy/task.py",
        "evaluation_command": "python demo_ve_gate_proxy/eval.py",
        "composite_stage_order": [],
    },
    "optimizer_schedule_proxy": {
        "family": "dl/proxy",
        "tag": "proxy",
        "supports_llm": True,
        "max_fix_budget": 2,
        "adapter": "optimizer_schedule_proxy_demo",
        "edit_scope": ["demo_optimizer_schedule_proxy/task.py"],
        "target_file": "demo_optimizer_schedule_proxy/task.py",
        "evaluation_command": "python demo_optimizer_schedule_proxy/eval.py",
        "composite_stage_order": [],
    },
    "capacity_budget_proxy": {
        "family": "dl/proxy",
        "tag": "proxy",
        "supports_llm": True,
        "max_fix_budget": 2,
        "adapter": "capacity_budget_proxy_demo",
        "edit_scope": ["demo_capacity_budget_proxy/task.py"],
        "target_file": "demo_capacity_budget_proxy/task.py",
        "evaluation_command": "python demo_capacity_budget_proxy/eval.py",
        "composite_stage_order": [],
    },
}


def _task_family(task: str) -> str:
    if not task or task not in TASKS:
        return task or "unknown"
    return str(TASKS[task]["family"])


def _task_tag(task: str) -> str:
    if not task or task not in TASKS:
        return "unknown"
    return str(TASKS[task]["tag"])


def _normalize_selected_tasks(tasks: list[str] | None) -> list[str]:
    if not tasks:
        return [task for task, info in TASKS.items() if str(info.get("tag", "")) != "held-out"]
    unknown = [task for task in tasks if task not in TASKS]
    if unknown:
        unknown_text = ", ".join(sorted(set(unknown)))
        raise ValueError(f"Unknown benchmark task(s): {unknown_text}")
    ordered: list[str] = []
    seen: set[str] = set()
    for task in tasks:
        if task in seen:
            continue
        seen.add(task)
        ordered.append(task)
    return ordered


def _modes_for_task(task: str) -> list[dict[str, object]]:
    task_info = TASKS[task]
    max_fix_budget = int(task_info["max_fix_budget"])
    modes: list[dict[str, object]] = [
        {
            "mode": "single_step_random",
            "proposer": "single_step_random",
            "chunking_enabled": False,
            "chunk_budget": 1,
            "prior_enabled": False,
            "max_fix_budget": max_fix_budget,
            "llm_memory_enabled": False,
            "llm_retry_enabled": False,
        },
        {
            "mode": "chunked_prior",
            "proposer": "chunked_prior",
            "chunking_enabled": True,
            "chunk_budget": 1,
            "prior_enabled": True,
            "max_fix_budget": max_fix_budget,
            "llm_memory_enabled": False,
            "llm_retry_enabled": False,
        },
    ]
    if bool(task_info["supports_llm"]):
        modes.extend(
            [
                {
                    "mode": "llm_codex_no_memory",
                    "proposer": "llm_codex",
                    "chunking_enabled": False,
                    "chunk_budget": 1,
                    "prior_enabled": False,
                    "max_fix_budget": max_fix_budget,
                    "llm_memory_enabled": False,
                    "llm_retry_enabled": False,
                },
                {
                    "mode": "llm_codex_memory_retry",
                    "proposer": "llm_codex",
                    "chunking_enabled": False,
                    "chunk_budget": 1,
                    "prior_enabled": False,
                    "max_fix_budget": max_fix_budget,
                    "llm_memory_enabled": True,
                    "llm_retry_enabled": True,
                },
            ]
        )
    return modes


def summarize_trials(trials: list[dict]) -> dict[str, dict[str, float | int | str | None]]:
    summary: dict[str, dict[str, float | int | str | None]] = {}
    for trial in trials:
        task = str(trial.get("task", "")).strip()
        mode = str(trial["mode"])
        key = f"{task}:{mode}" if task else mode
        bucket = summary.setdefault(
            key,
            {
                "trials": 0,
                "task": task,
                "task_family": str(trial.get("task_family", _task_family(task))),
                "task_tag": str(trial.get("task_tag", _task_tag(task))),
                "mode": mode,
                "best_score": float("-inf"),
                "total_accepts": 0,
                "improved_trials": 0,
                "ok_trials": 0,
                "sum_accepted_count": 0,
                "sum_iterations_completed": 0,
                "score_deltas": [],
                "first_accept_iterations": [],
            },
        )
        bucket["trials"] = int(bucket["trials"]) + 1
        bucket["best_score"] = max(float(bucket["best_score"]), float(trial["best_score"]))
        bucket["total_accepts"] = int(bucket["total_accepts"]) + int(trial["accepted_count"])
        if str(trial.get("trial_status", "ok")) == "ok":
            bucket["ok_trials"] = int(bucket["ok_trials"]) + 1
            score_delta = float(trial.get("score_delta", 0.0))
            if score_delta > 0:
                bucket["improved_trials"] = int(bucket["improved_trials"]) + 1
            bucket["sum_accepted_count"] = int(bucket["sum_accepted_count"]) + int(trial.get("accepted_count", 0))
            bucket["sum_iterations_completed"] = int(bucket["sum_iterations_completed"]) + int(trial.get("iterations_completed", 0))
            bucket["score_deltas"].append(score_delta)
            first_accept = trial.get("first_accept_iteration")
            if first_accept is not None:
                bucket["first_accept_iterations"].append(float(first_accept))

    for bucket in summary.values():
        ok_trials = int(bucket["ok_trials"])
        trials_total = int(bucket["trials"])
        score_deltas = [float(v) for v in bucket.pop("score_deltas")]  # type: ignore[arg-type]
        first_accepts = [float(v) for v in bucket.pop("first_accept_iterations")]  # type: ignore[arg-type]
        bucket["success_rate"] = (int(bucket["improved_trials"]) / ok_trials) if ok_trials else 0.0
        bucket["median_gain"] = statistics.median(score_deltas) if score_deltas else 0.0
        bucket["median_first_accept_iter"] = statistics.median(first_accepts) if first_accepts else None
        total_steps = int(bucket["sum_iterations_completed"])
        bucket["accept_precision"] = (int(bucket["sum_accepted_count"]) / total_steps) if total_steps else 0.0
        bucket["trial_failure_rate"] = ((trials_total - ok_trials) / trials_total) if trials_total else 0.0
    return summary


def render_benchmark_summary(summary: dict[str, dict[str, float | int | str | None]], *, iterations: int, trials: int) -> str:
    tasks = sorted({str(bucket.get("task", "")) for bucket in summary.values() if str(bucket.get("task", ""))})
    families = sorted({str(bucket.get("task_family", _task_family(str(bucket.get("task", ""))))) for bucket in summary.values()})
    lines = [f"benchmark iterations={iterations} trials={trials} tasks={len(tasks)}", ""]
    for family in families:
        lines.append(family)
        family_tasks = sorted(
            {
                str(bucket.get("task", ""))
                for bucket in summary.values()
                if str(bucket.get("task_family", _task_family(str(bucket.get("task", ""))))) == family
            }
        )
        for task in family_tasks:
            task_rows = [bucket for bucket in summary.values() if str(bucket.get("task", "")) == task]
            task_rows.sort(key=lambda row: str(row["mode"]))
            tag = str(task_rows[0].get("task_tag", _task_tag(task)))
            lines.append(f"  {task} [{tag}]")
            for row in task_rows:
                first_accept = row.get("median_first_accept_iter")
                first_accept_text = "-" if first_accept is None else f"{float(first_accept):.1f}"
                lines.append(
                    "    "
                    f"{row['mode']} "
                    f"success={float(row['success_rate']):.3f} "
                    f"median_gain={float(row['median_gain']):.6f} "
                    f"first_accept={first_accept_text} "
                    f"accept_precision={float(row['accept_precision']):.3f} "
                    f"trial_failure_rate={float(row['trial_failure_rate']):.3f}"
                )
            lines.append("")
    return "\n".join(lines).rstrip()


def _copy_repo(src: Path) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="autoresearch-bench-"))
    dest = temp_root / "repo"
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(".git", "runs", "__pycache__", ".pytest_cache", "*.pyc"),
    )
    subprocess.run(["git", "-C", str(dest), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(dest), "config", "user.name", "Codex"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(dest), "config", "user.email", "codex@example.com"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(dest), "add", "."], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(dest), "commit", "-m", "benchmark snapshot"], check=True, capture_output=True, text=True)
    return dest


def _rewrite_config(
    dest: Path,
    *,
    task: str,
    proposer: str,
    chunking_enabled: bool,
    chunk_budget: int,
    prior_enabled: bool,
    max_fix_budget: int | None = None,
    llm_memory_enabled: bool = True,
    llm_retry_enabled: bool = True,
    ) -> None:
    task_info = TASKS[task]
    effective_fix_budget = int(task_info["max_fix_budget"] if max_fix_budget is None else max_fix_budget)
    config_path = dest / "config" / "project.toml"
    edit_scope = list(task_info["edit_scope"])
    stage_order = list(task_info["composite_stage_order"])
    edit_scope_literal = "[" + ", ".join(f'"{path}"' for path in edit_scope) + "]"
    stage_order_literal = "[" + ", ".join(f'"{name}"' for name in stage_order) + "]"
    config_path.write_text(
        "\n".join(
            [
                f'project_name = "{task}-benchmark"',
                f'adapter = "{task_info["adapter"]}"',
                f'proposer = "{proposer}"',
                f"edit_scope = {edit_scope_literal}",
                f'target_file = "{task_info["target_file"]}"',
                f'evaluation_command = "{task_info["evaluation_command"]}"',
                'score_pattern = "SCORE=(?P<score>-?\\\\d+(?:\\\\.\\\\d+)?)"',
                'direction = "maximize"',
                f"composite_stage_order = {stage_order_literal}",
                f"max_fix_budget = {effective_fix_budget}",
                f"llm_memory_enabled = {'true' if llm_memory_enabled else 'false'}",
                f"llm_retry_enabled = {'true' if llm_retry_enabled else 'false'}",
                "",
                "[mutation]",
                'mode = "python_ast_patch"',
                "max_constant_delta = 0.30",
                "random_seed = 7",
                'allowed_math_funcs = ["sin", "cos", "tanh"]',
                'allowed_binary_ops = ["Add", "Sub", "Mult"]',
                "",
                "[chunking]",
                f"enabled = {'true' if chunking_enabled else 'false'}",
                'strategy = "ast_assignments"',
                f"chunk_budget = {chunk_budget}",
                "",
                "[prior]",
                f"enabled = {'true' if prior_enabled else 'false'}",
                "lookback = 6",
                "decay = 0.8",
                "accept_boost = 1.5",
                "reject_penalty = 1.0",
                "min_weight = 0.2",
            ]
        ),
        encoding="utf-8",
    )


def _failed_trial_result(
    task: str,
    task_info: dict[str, object],
    mode: dict[str, object],
    trial_index: int,
    *,
    error: str,
) -> dict[str, object]:
    return {
        "task": task,
        "task_family": str(task_info["family"]),
        "task_tag": str(task_info["tag"]),
        "mode": str(mode["mode"]),
        "trial": trial_index + 1,
        "trial_status": "failed",
        "baseline_score": 0.0,
        "best_score": 0.0,
        "score_delta": 0.0,
        "accepted_count": 0,
        "iterations_completed": 0,
        "first_accept_iteration": None,
        "error": error,
    }


def _run_single_trial(root: Path, task: str, mode: dict[str, object], trial_index: int, iterations: int) -> dict[str, object]:
    task_info = TASKS[task]
    dest = _copy_repo(root)
    try:
        _rewrite_config(
            dest,
            task=task,
            proposer=str(mode["proposer"]),
            chunking_enabled=bool(mode["chunking_enabled"]),
            chunk_budget=int(mode["chunk_budget"]),
            prior_enabled=bool(mode["prior_enabled"]),
            max_fix_budget=int(mode["max_fix_budget"]),
            llm_memory_enabled=bool(mode["llm_memory_enabled"]),
            llm_retry_enabled=bool(mode["llm_retry_enabled"]),
        )
        baseline = run_baseline(dest)
        records = run_search(dest, iterations)
        ledger = RunLedger(dest)
        best = ledger.best_accepted()
        best_score = float(best["score"]) if best else float("-inf")
        accepted_count = sum(1 for record in records if record.decision == "accept")
        first_accept_iteration = next((index + 1 for index, record in enumerate(records) if record.decision == "accept"), None)
        return {
            "task": task,
            "task_family": str(task_info["family"]),
            "task_tag": str(task_info["tag"]),
            "mode": str(mode["mode"]),
            "trial": trial_index + 1,
            "trial_status": "ok",
            "baseline_score": float(baseline.score),
            "best_score": best_score,
            "score_delta": best_score - float(baseline.score),
            "accepted_count": accepted_count,
            "iterations_completed": len(records),
            "first_accept_iteration": first_accept_iteration,
        }
    except Exception as exc:
        return _failed_trial_result(task, task_info, mode, trial_index, error=f"{type(exc).__name__}: {exc}")
    finally:
        shutil.rmtree(dest.parent, ignore_errors=True)


def _run_single_trial_subprocess(root: Path, task: str, mode: dict[str, object], trial_index: int, iterations: int) -> dict[str, object]:
    task_info = TASKS[task]
    payload = json.dumps(
        {
            "root": str(root),
            "task": task,
            "mode": mode,
            "trial_index": trial_index,
            "iterations": iterations,
        }
    )
    script = (
        "import json, sys; "
        "from pathlib import Path; "
        "from src.autoresearch_plus.benchmark import _run_single_trial; "
        "payload=json.loads(sys.argv[1]); "
        "result=_run_single_trial(Path(payload['root']), payload['task'], payload['mode'], int(payload['trial_index']), int(payload['iterations'])); "
        "print(json.dumps(result))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, payload],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or f"subprocess failed with code {completed.returncode}"
        return _failed_trial_result(task, task_info, mode, trial_index, error=error)

    stdout_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not stdout_lines:
        return _failed_trial_result(task, task_info, mode, trial_index, error="subprocess produced no output")

    try:
        result = json.loads(stdout_lines[-1])
    except json.JSONDecodeError:
        snippet = stdout_lines[-1][:200]
        return _failed_trial_result(task, task_info, mode, trial_index, error=f"invalid subprocess JSON: {snippet}")

    if not isinstance(result, dict):
        return _failed_trial_result(task, task_info, mode, trial_index, error="subprocess returned non-dict result")
    return result


def run_ab_benchmark(root: Path, iterations: int, trials: int, *, tasks: list[str] | None = None, trial_runner=None) -> list[dict]:
    runner = _run_single_trial_subprocess if trial_runner is None else trial_runner
    trial_results: list[dict] = []
    selected_tasks = _normalize_selected_tasks(tasks)
    for task in selected_tasks:
        for mode in _modes_for_task(task):
            for trial_index in range(trials):
                trial_results.append(runner(root, task, mode, trial_index, iterations))
    return trial_results
