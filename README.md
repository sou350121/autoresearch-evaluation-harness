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

It does **not** try to be a general research platform. The point is to keep the loop small enough that you can still explain it in one breath.

## Repo layout

- `config/project.toml`: project config and experiment settings
- `programs/default.md`: plain-language operating rules for the agent
- `demo_target/train.py`: the single editable demo target
- `demo_target/eval.py`: prints a scalar `SCORE=<float>` for the current target
- `src/autoresearch_plus/`: loop implementation
- `runs/results.tsv`: append-only experiment ledger
- `runs/traces/`: one JSON trace per run

## Core loop

1. Edit one target file.
2. Run one evaluation command.
3. Parse one scalar score.
4. Compare against the previous accepted revision.
5. Keep or discard.
6. Log everything.

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

## Quick start

From this repo root:

```powershell
python -m src.autoresearch_plus.cli baseline
python -m src.autoresearch_plus.cli search --iterations 8
python -m src.autoresearch_plus.cli report
```

The demo target is intentionally simple. The loop mutates numeric constants in `demo_target/train.py`, runs `demo_target/eval.py`, and keeps only improvements.

## How to adapt it

Replace only these things first:

1. `config/project.toml`
2. `demo_target/train.py`
3. `demo_target/eval.py`

Keep the loop logic unchanged until you have a real need to expand it.
