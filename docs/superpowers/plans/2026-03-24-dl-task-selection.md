# Deep Learning Task Selection

**Goal:** Pick the first deep-learning-style task worth connecting to `autoresearch-plus` without pretending this machine can run full `autoresearch/train.py` experiments.

**Constraint:** This machine has `torch` installed but `torch.cuda.is_available() == False`. That means:

- we can inspect and reason about `autoresearch/train.py`
- we cannot honestly validate 5-minute GPU training loops here
- we should not represent static proxy tasks as full training experiments

## What counts as a good first DL task

The first DL task should satisfy all of these:

- live in the real [`train.py`](C:\Users\sou35\Documents\repo-research\autoresearch\train.py) path
- expose multiple plausible research directions, not a single obvious bugfix
- let an LLM read code and logs, summarize tradeoffs, and choose a repair or experiment direction
- stay local enough that a future adapter can keep the edit scope small

## Top 3 candidate tasks

### 1. Value Embedding / Gate design

**Target area:**

- `has_ve`
- `ve_gate_channels`
- `ve_gate`
- `v = v + gate.unsqueeze(-1) * ve`
- `value_embeds`

**Why it is strong:**

- This is the most "research-like" part of the model.
- There are multiple credible directions:
  - change which layers get VE
  - change gate input width
  - change gate parameterization
  - change VE initialization or learning rate treatment
- It is more structural than plain hyperparameter tuning.

**Why it is the recommended first task:**

- It is small enough to bound.
- It is rich enough that `llm_codex` has to read and choose, not just match one keyword to one fix.

### 2. Optimizer and schedule coupling

**Target area:**

- `setup_optimizer`
- `WARMUP_RATIO`
- `WARMDOWN_RATIO`
- `FINAL_LR_FRAC`
- `get_lr_multiplier`
- `get_muon_momentum`
- `get_weight_decay`

**Why it is strong:**

- This is a real experiment surface with interacting knobs.
- It reflects the fixed-budget nature of `autoresearch`.

**Why it is second, not first:**

- It is easier to bloat into many tiny scalar tweaks.
- It is slightly less distinctive than the VE/gate path.

### 3. Initialization + depth/width/time-budget coupling

**Target area:**

- `build_model_config`
- `init_weights`
- `DEPTH`
- `ASPECT_RATIO`
- `HEAD_DIM`
- `WINDOW_PATTERN`
- `resid_lambdas`
- `x0_lambdas`

**Why it is strong:**

- This is the closest to real small-budget architecture search.
- It naturally forces tradeoffs between capacity, stability, and token throughput.

**Why it is third:**

- It is the broadest of the three.
- It is the most likely to require real GPU evidence before the loop becomes trustworthy.

## Recommendation

Start with **Value Embedding / Gate design**.

That is the best first DL task because it has:

- real architectural meaning
- multiple plausible fixes or experiment ideas
- a compact code surface
- a stronger need for code reading and synthesis than pure LR tuning

## Honest next step options

### Option A: CUDA-first

Use a CUDA machine and connect a real adapter against the actual `autoresearch` repo:

- edit scope: `autoresearch/train.py`
- evaluator: `uv run train.py`
- score: parsed `val_bpb`

This is the only path that should be called a true deep-learning experiment loop.

### Option B: CPU-only proxy

Build a **DL-derived fixture** from the VE/gate section of `train.py`:

- keep the source grounded in the real code
- let `llm_codex` choose among several VE/gate experiment hypotheses
- evaluate with targeted contract tests or proxy scoring

This is still useful, but it should be described as a **proxy task**, not full training.

## Decision

For this machine, the correct next implementation is:

1. keep the chosen first task as **VE/gate**
2. do **not** claim full DL loop validation
3. only build a CPU proxy if we explicitly decide that a proxy is worth the complexity
