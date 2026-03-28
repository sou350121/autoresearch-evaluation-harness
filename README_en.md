# autoresearch-evaluation-harness

An evaluation-first harness for `autoresearch`-style loops.  
It compares proposal strategies under fixed task adapters, explicit scalar evaluation, and hard keep/discard gates.  
The current system is best described as **benchmark-driven, task-dependent, and adapter-shaped**, not a broad autonomous research agent.

**Docs**  
[`中文 README`](README.md) · [`Frozen Evaluation Report`](docs/superpowers/plans/2026-03-27-frozen-evaluation-interim-report.md) · [`GitHub Launch Notes`](docs/launch/2026-03-28-github-launch-notes.md)

### Chinese-first repo · engineering-focused autoresearch evaluation

Many autoresearch-style projects lead with what an agent can do. Far fewer explain **how proposals are compared, retained, or rejected**.  
This repo does one thing: **put proposal strategies inside fixed tasks, fixed budgets, and hard keep/discard evaluation to see whether they actually produce stable value.**

---

## In Three Sentences

1. **This is not a demo of agent tricks**. It is an evaluation harness that compares proposal strategies under the same task adapters and benchmark contracts.
2. **The LLM can propose, but it cannot judge itself**. Success is determined by external evaluators, reports, and keep/discard gates.
3. **Generalization is pushed onto held-out checks**. Default benchmark tasks and held-out tasks are separated on purpose so held-out evidence does not get tuned away.

## Current Status

- the main `baseline -> search -> report -> benchmark` loop is operational
- the repo supports multiple task adapters, including toy, real-fixture, DL/proxy, and opt-in held-out tasks
- the strongest current conclusion is still `task-dependent` behavior
- the most honest current positioning is: **a high-quality evaluation harness**, not a proven general research agent

## What This Repo Does Not Claim

- broad generalization across tasks
- universal superiority of `llm_codex` over non-LLM baselines
- broad independent value from `memory + retry`
- general unknown-method problem solving

## Default Benchmark vs Held-Out

The default benchmark is for day-to-day regression and strategy comparison.  
Held-out tasks are extra validation checks and are **not** part of the default benchmark. They must be selected explicitly with `--task`.

## Project Goals

- keep the autoresearch loop small, local, and auditable
- compare proposal strategies under the same evaluation budget
- make task-dependent wins and failures visible instead of hiding them behind one headline score
- separate default benchmark tasks from opt-in held-out checks
- support LLM-in-the-loop proposal without letting the model judge its own success

## Repo Layout

- `config/project.toml`: project config and experiment settings
- `programs/default.md`: plain-language operating rules for the agent
- `demo_target/train.py`: default editable demo target
- `demo_target/eval.py`: prints `SCORE=<float>` for the current target
- `demo_prompt/`, `demo_bugfix/`, `demo_code_repair/`: text and repair demos
- `demo_circles_classification/`, `demo_digits_image_classification/`, `demo_diabetes_regression/`, `demo_breast_cancer_classification/`: DL demos
- `demo_wine_classification/`, `demo_friedman1_regression/`: opt-in held-out tasks
- `demo_ve_gate_proxy/`, `demo_optimizer_schedule_proxy/`, `demo_capacity_budget_proxy/`: method proxies
- `src/autoresearch_plus/`: core implementation
- `runs/results.tsv`: append-only experiment ledger
- `runs/traces/`: one JSON trace per run
- `runs/accepted_snapshots/`: accepted snapshots for exact baseline restoration

## Core Loop

1. Edit one target file.
2. Derive stable AST chunks.
3. Bias chunk and mutation-family choice using recent accepted and rejected runs.
4. Run one evaluation command.
5. Parse one scalar score.
6. Compare against the previous accepted revision.
7. Keep or discard, and commit only accepted target changes.
8. Log everything.

The ledger records both `git_commit` and `git_dirty` so accepted runs remain interpretable even when the wider repo is still being edited.  
Each search run also records `chunk_id`, `chunk_span`, `mutation_kind`, and prior metadata so search behavior stays explainable.

## Adapter Boundary

The core loop is task-adapter driven:

`accepted_state -> proposal -> candidate -> evaluate -> keep/discard -> ledger`

The same durability layer is reused across numeric demos, text/prompt tasks, bugfix and code-repair tasks, mixed tasks, DL demos, and held-out tasks.

## Why This Exists

`karpathy/autoresearch` is elegant because it is brutally constrained.

The larger systems in this space are stronger in persistence, memory, branching, and evaluation infrastructure, but they are also much heavier.  
This repo is trying to occupy the middle:

- still small
- still metric-driven
- still easy to reason about
- but structured enough to run repeatedly without losing track

## Plans And Reports

- `docs/superpowers/plans/2026-03-27-frozen-evaluation-interim-report.md`
- `docs/superpowers/plans/2026-03-28-held-out-task-plan.md`
- `docs/launch/2026-03-28-github-launch-notes.md`

## Quick Start

From the repo root:

```powershell
python -m src.autoresearch_plus.cli baseline
python -m src.autoresearch_plus.cli search --iterations 8
python -m src.autoresearch_plus.cli report
python -m src.autoresearch_plus.cli benchmark --iterations 8 --trials 2
python -m src.autoresearch_plus.cli benchmark --iterations 1 --trials 3 --task breast_cancer_classification
python -m src.autoresearch_plus.cli benchmark --iterations 1 --trials 3 --task wine_classification
```

Held-out tasks are opt-in and excluded from the default benchmark. Use `--task` to run them explicitly.

## How To Adapt It

Replace these first:

1. `config/project.toml`
2. `demo_target/train.py`
3. `demo_target/eval.py`

Leave the loop logic unchanged until you have a real reason to expand it.
