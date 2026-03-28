# autoresearch-plus

`autoresearch-plus` is a local skeleton for building an `autoresearch`-style self-improving loop without jumping straight to a full research OS.

It keeps the strongest part of `karpathy/autoresearch`:

- one main target file
- one scalar evaluation signal
- a hard keep/discard loop

It borrows only a few high-value ideas from larger systems:

- explicit run ledger and notes
- accepted baseline gate
- per-run JSON traces
- ACT-style chunked mutation regions
- a heuristic flow-inspired prior over chunk and mutation choice
- a task-adapter boundary so the core loop is not tied to one demo artifact

It does **not** try to be a general research platform. The point is to keep the loop small enough that you can still explain it in one breath.

## Repo layout

- `config/project.toml`: project config and experiment settings
- `programs/default.md`: plain-language operating rules for the agent
- `demo_target/train.py`: the single editable demo target
- `demo_target/eval.py`: prints a scalar `SCORE=<float>` for the current target
- `demo_prompt/prompt.md`: prompt-optimization demo artifact
- `demo_prompt/eval.py`: prompt demo scorer
- `demo_bugfix/buggy_math.py`: bugfix demo artifact
- `demo_bugfix/eval.py`: bugfix demo scorer
- `demo_code_repair/calculator.py`: code-repair demo artifact
- `demo_code_repair/eval.py`: code-repair demo scorer
- `demo_circles_classification/task.py`: nonlinear binary classification demo artifact
- `demo_circles_classification/eval.py`: circles classification scorer
- `demo_digits_image_classification/task.py`: image classification demo artifact
- `demo_digits_image_classification/eval.py`: digits classification scorer
- `demo_diabetes_regression/task.py`: regression demo artifact
- `demo_diabetes_regression/eval.py`: diabetes regression scorer
- `demo_friedman1_regression/task.py`: held-out nonlinear regression demo artifact
- `demo_friedman1_regression/eval.py`: held-out friedman1 regression scorer
- `demo_breast_cancer_classification/task.py`: tabular classification demo artifact
- `demo_breast_cancer_classification/eval.py`: breast cancer classification scorer
- `demo_wine_classification/task.py`: held-out tabular classification demo artifact
- `demo_wine_classification/eval.py`: held-out wine classification scorer
- `demo_friedman1_regression/task.py`: held-out nonlinear regression demo artifact
- `demo_friedman1_regression/eval.py`: held-out Friedman1 regression scorer
- `demo_ve_gate_proxy/task.py`: value-embedding / gate proxy artifact derived from `autoresearch/train.py`
- `demo_ve_gate_proxy/eval.py`: CPU proxy scorer for alternating VE, neutral gate init, and gate-channel changes
- `demo_optimizer_schedule_proxy/task.py`: optimizer/schedule coupling proxy artifact for warmup/decay method search
- `demo_optimizer_schedule_proxy/eval.py`: CPU proxy scorer for warmup and decay coupling on a digits classifier
- `demo_capacity_budget_proxy/task.py`: capacity/training-budget coupling proxy artifact for width+epochs method search
- `demo_capacity_budget_proxy/eval.py`: CPU proxy scorer for coupled width and budget changes on a noisy moons task
- `src/autoresearch_plus/`: loop implementation
- `src/autoresearch_plus/adapter.py`: generic task-adapter protocol
- `src/autoresearch_plus/composite_adapter.py`: multi-stage composite task adapter
- `src/autoresearch_plus/engine.py`: task-agnostic baseline/search engine
- `src/autoresearch_plus/numeric_demo_adapter.py`: current demo adapter
- `src/autoresearch_plus/prompt_demo_adapter.py`: text/prompt demo adapter
- `src/autoresearch_plus/bugfix_demo_adapter.py`: bugfix demo adapter
- `src/autoresearch_plus/code_repair_demo_adapter.py`: test-driven code-repair demo adapter
- `src/autoresearch_plus/mixed_prompt_code_repair_adapter.py`: mixed prompt+code-repair demo adapter
- `src/autoresearch_plus/mixed_prompt_bugfix_adapter.py`: mixed prompt+bugfix demo adapter
- `src/autoresearch_plus/dl_demo_adapters.py`: CPU-friendly deep learning demo adapters
- `src/autoresearch_plus/proposers.py`: pluggable numeric search strategies
- `runs/results.tsv`: append-only experiment ledger
- `runs/traces/`: one JSON trace per run
- `runs/accepted_snapshots/`: accepted target snapshots for exact baseline restoration

## Core loop

1. Edit one target file.
2. Derive stable AST chunks from the target file.
3. Bias chunk and mutation-family choice using recent accepted and rejected runs.
4. Run one evaluation command.
5. Parse one scalar score.
6. Compare against the previous accepted revision.
7. Keep or discard, and commit only accepted target changes.
8. Log everything.

The ledger records both `git_commit` and `git_dirty` so accepted runs remain interpretable even when the wider repo is still being edited.
Each search run also records `chunk_id`, `chunk_span`, `mutation_kind`, and prior metadata so search behavior stays explainable.

## Adapter boundary

The core loop is now task-adapter driven:

`accepted_state -> proposal -> candidate -> evaluate -> keep/discard -> ledger`

The numeric demo remains the first adapter, the prompt demo is the second, the bugfix demo is the third, the code-repair demo is the fourth, the mixed prompt+code-repair demo is the fifth, the mixed prompt+bugfix demo is the sixth, and the CPU-friendly DL demos extend the same loop to nonlinear classification, image classification, regression, tabular classification, held-out wine and Friedman1 tasks, a VE/gate proxy derived from `autoresearch/train.py`, an optimizer/schedule coupling proxy, and a capacity/budget coupling proxy. That means the durability layer and search loop are reusable even when the editable artifact is no longer a single Python file or a simple numeric fit task.

Composite adapters now support:

- configurable `composite_stage_order`
- an `integration_stage` bonus layered on top of per-stage scores
- a named composite scoring policy
- stage-level trace summaries with raw and normalized scores
- stage saturation detection and stage skipping
- fail-fast rejection when all composite stages are saturated
- one keep/discard decision for the whole mixed revision

When composite traces are available, `python -m src.autoresearch_plus.cli report` now prints both the accepted `composite_summary` and the latest rejected composite summary, including `saturated_stages`.

The current strategy layer is also becoming pluggable:

- `single_step_random`
- `chunked_prior`

Today those are wired for the numeric demo first, but the architecture no longer assumes one built-in search policy.

## Why this exists

`karpathy/autoresearch` is elegant because it is brutally constrained.

The other systems I studied are stronger in persistence, memory, branching, and evaluation infrastructure, but they are all much heavier:

- `theam/autonomous-researcher`: durable research OS
- `ResearAI/DeepScientist`: quest and artifact platform
- `MiroMindAI/MiroThinker`: benchmark-heavy research agent system

This repo is meant to sit in the middle:

- still small
- still metric-driven
- still easy to reason about
- but with just enough structure to run repeatedly without losing track

## Plans and reports

- `docs/superpowers/plans/2026-03-27-frozen-evaluation-interim-report.md`: current frozen-evaluation evidence and claims
- `docs/superpowers/plans/2026-03-28-held-out-task-plan.md`: held-out task plan and implementation record for `wine_classification`

## Quick start

From this repo root:

```powershell
python -m src.autoresearch_plus.cli baseline
python -m src.autoresearch_plus.cli search --iterations 8
python -m src.autoresearch_plus.cli report
python -m src.autoresearch_plus.cli benchmark --iterations 8 --trials 2
```

The demo target is intentionally simple. The loop applies small Python AST patches to `demo_target/train.py`, runs `demo_target/eval.py`, and keeps only improvements.
The search is now chunk-first: it picks one assignment region such as `assign:wave`, then applies a patch inside that region with probabilities biased by recent ledger history.
The benchmark command can be filtered to focused task slices, including numeric fitting, prompt revision, direct bugfix, test-driven code repair, mixed multi-stage tasks, real-fixture repairs, DL/proxy tasks, and held-out tasks.
Held-out tasks are opt-in: they are excluded from default benchmark runs and should be invoked explicitly with `--task`.

## How to adapt it

Replace only these things first:

1. `config/project.toml`
2. `demo_target/train.py`
3. `demo_target/eval.py`

Keep the loop logic unchanged until you have a real need to expand it.
