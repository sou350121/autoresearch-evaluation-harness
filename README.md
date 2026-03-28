# autoresearch-plus

`autoresearch-plus` 是一个以评估为先的 `autoresearch` 风格实验框架。  
它用固定 task adapter、明确的标量评估信号，以及硬性的 keep/discard gate 来比较不同 proposal strategy。  
当前系统的可信定位是：**benchmark-driven、task-dependent、adapter-shaped**，而不是通用 autonomous research agent。

`autoresearch-plus` is an evaluation-first harness for `autoresearch`-style loops.  
It compares proposal strategies under fixed task adapters, explicit scalar evaluation, and hard keep/discard gates.  
The current system is benchmark-driven and task-dependent, not a broad autonomous research agent.

## 这个仓库是什么 / What This Repo Is

- 一个用于比较 search 和 proposal strategy 的本地实验框架
- 一个围绕 `baseline -> search -> report -> benchmark` 构建的小型、可审计闭环
- 一个带有明确 evaluation contract 的 task-adapter 系统
- 一个把 held-out 检查视为 opt-in 证据、而不是默认回归项的仓库

它保留了 `karpathy/autoresearch` 最有价值的核心约束：

- one main target file
- one scalar evaluation signal
- a hard keep/discard loop

它只从更重的系统里借了少数高价值结构：

- explicit run ledger and notes
- accepted baseline gate
- per-run JSON traces
- ACT-style chunked mutation regions
- a heuristic flow-inspired prior over chunk and mutation choice
- a task-adapter boundary so the core loop is not tied to one demo artifact

它**不**试图把自己包装成 general research platform。  
这个仓库的重点是把 loop 保持在足够小、足够清楚、仍然能一口气讲明白的范围内。

## 项目目标 / Project Goals

- 保持 autoresearch loop 足够小、足够本地化、足够可审计
- 在相同预算下比较不同 proposal strategy，而不是只看单次最好分
- 让 task-dependent 的强弱和失败都可见，而不是被一个 headline score 掩盖
- 将默认 benchmark task 与 opt-in held-out 检查分开
- 允许 LLM 参与 proposal，但不让模型自己判定是否成功

## 当前不主张的内容 / What It Does Not Claim

- 不主张 broad generalization across tasks
- 不主张 `llm_codex` 已普遍强于 non-LLM baseline
- 不主张 `memory + retry` 已经具备 broad independent value
- 不主张当前系统已经以一般形式解决 unknown-method problem

## 当前证据 / Current Evidence

- harness 本身已经能工作：task filtering、per-trial isolation、reporting 和 benchmark summaries 都已接通
- 当前增益是明显 task-dependent 的：有些任务偏向 LLM mode，有些任务偏向更简单的 guided baseline
- held-out 证据目前是混合的：
  - `wine_classification` 更偏向 non-LLM guided baseline
  - `friedman1_regression` 更偏向 LLM proposal
- `memory + retry` 目前最强的局部正信号仍然是 `diabetes_regression`，而不是整个 task set

## 仓库结构 / Repo Layout

- `config/project.toml`：项目配置与实验设置
- `programs/default.md`：面向 agent 的自然语言运行规则
- `demo_target/train.py`：默认可编辑 demo target
- `demo_target/eval.py`：为当前 target 输出 `SCORE=<float>`
- `demo_prompt/prompt.md`：prompt 优化 demo artifact
- `demo_prompt/eval.py`：prompt demo scorer
- `demo_bugfix/buggy_math.py`：bugfix demo artifact
- `demo_bugfix/eval.py`：bugfix demo scorer
- `demo_code_repair/calculator.py`：code repair demo artifact
- `demo_code_repair/eval.py`：code repair demo scorer
- `demo_circles_classification/task.py`：非线性二分类 demo artifact
- `demo_circles_classification/eval.py`：circles scorer
- `demo_digits_image_classification/task.py`：图像分类 demo artifact
- `demo_digits_image_classification/eval.py`：digits scorer
- `demo_diabetes_regression/task.py`：回归 demo artifact
- `demo_diabetes_regression/eval.py`：diabetes scorer
- `demo_breast_cancer_classification/task.py`：表格分类 demo artifact
- `demo_breast_cancer_classification/eval.py`：breast cancer scorer
- `demo_wine_classification/task.py`：held-out 表格分类 demo artifact
- `demo_wine_classification/eval.py`：held-out wine scorer
- `demo_friedman1_regression/task.py`：held-out 非线性回归 demo artifact
- `demo_friedman1_regression/eval.py`：held-out Friedman1 scorer
- `demo_ve_gate_proxy/task.py`：从 `autoresearch/train.py` 抽出的 value embedding / gate proxy artifact
- `demo_ve_gate_proxy/eval.py`：alternating VE、neutral gate init、gate channel 变更的 CPU proxy scorer
- `demo_optimizer_schedule_proxy/task.py`：optimizer/schedule coupling proxy artifact
- `demo_optimizer_schedule_proxy/eval.py`：warmup/decay coupling 的 CPU proxy scorer
- `demo_capacity_budget_proxy/task.py`：capacity/training-budget coupling proxy artifact
- `demo_capacity_budget_proxy/eval.py`：width+budget coupling 的 CPU proxy scorer
- `src/autoresearch_plus/`：核心 loop 实现
- `src/autoresearch_plus/adapter.py`：通用 task-adapter 协议
- `src/autoresearch_plus/composite_adapter.py`：多阶段 composite adapter
- `src/autoresearch_plus/engine.py`：task-agnostic baseline/search engine
- `src/autoresearch_plus/numeric_demo_adapter.py`：numeric demo adapter
- `src/autoresearch_plus/prompt_demo_adapter.py`：prompt demo adapter
- `src/autoresearch_plus/bugfix_demo_adapter.py`：bugfix demo adapter
- `src/autoresearch_plus/code_repair_demo_adapter.py`：test-driven code-repair demo adapter
- `src/autoresearch_plus/mixed_prompt_code_repair_adapter.py`：mixed prompt+code-repair demo adapter
- `src/autoresearch_plus/mixed_prompt_bugfix_adapter.py`：mixed prompt+bugfix demo adapter
- `src/autoresearch_plus/dl_demo_adapters.py`：CPU 友好的 deep learning demo adapter
- `src/autoresearch_plus/proposers.py`：可插拔的 numeric search strategy
- `runs/results.tsv`：append-only 实验账本
- `runs/traces/`：每次运行一份 JSON trace
- `runs/accepted_snapshots/`：accepted target 的快照，用于精确恢复 baseline

## 核心循环 / Core Loop

1. 编辑一个 target file。
2. 从 target file 派生稳定的 AST chunks。
3. 用最近的 accepted / rejected run 去偏置 chunk 与 mutation-family 选择。
4. 跑一次 evaluation command。
5. 解析一个标量分数。
6. 与前一个 accepted revision 比较。
7. 决定 keep 或 discard，只提交 accepted target change。
8. 记录全部运行痕迹。

ledger 同时记录 `git_commit` 与 `git_dirty`，这样即使 wider repo 仍在变化，accepted run 仍然可解释。  
每次 search run 也会记录 `chunk_id`、`chunk_span`、`mutation_kind` 和 prior metadata，让搜索行为保持可解释。

## 适配器边界 / Adapter Boundary

当前 core loop 已经由 task-adapter 驱动：

`accepted_state -> proposal -> candidate -> evaluate -> keep/discard -> ledger`

numeric demo 是第一类 adapter，prompt demo、bugfix demo、code-repair demo、mixed demo 和 CPU-friendly DL demo 都复用了同一条主循环。  
这意味着 durability layer 和 search loop 在 artifact 不再只是单个 Python 文件时仍可复用。

Composite adapter 目前支持：

- configurable `composite_stage_order`
- an `integration_stage` bonus layered on top of per-stage scores
- a named composite scoring policy
- stage-level trace summaries with raw and normalized scores
- stage saturation detection and stage skipping
- fail-fast rejection when all composite stages are saturated
- 整个 mixed revision 只做一次 keep/discard decision

当 composite trace 存在时，`python -m src.autoresearch_plus.cli report` 会输出 accepted `composite_summary` 和最新 rejected composite summary，包括 `saturated_stages`。

当前 strategy layer 也已经可插拔：

- `single_step_random`
- `chunked_prior`

目前它们最先接在 numeric demo 上，但整体架构已经不再假设只有一种内建 search policy。

## 为什么存在 / Why This Exists

`karpathy/autoresearch` 的优雅之处在于它的约束非常强。

我研究过的其他系统在 persistence、memory、branching 和 evaluation infrastructure 上更强，但它们也明显更重：

- `theam/autonomous-researcher`: durable research OS
- `ResearAI/DeepScientist`: quest and artifact platform
- `MiroMindAI/MiroThinker`: benchmark-heavy research agent system

这个仓库想占据的是中间位置：

- 仍然小
- 仍然 metric-driven
- 仍然容易解释
- 但已经有足够的结构去重复运行，而不至于失去上下文

## 计划与报告 / Plans And Reports

- `docs/superpowers/plans/2026-03-27-frozen-evaluation-interim-report.md`：当前 frozen-evaluation 证据与 claim
- `docs/superpowers/plans/2026-03-28-held-out-task-plan.md`：`wine_classification` 的 held-out task 计划与实现记录
- `docs/launch/2026-03-28-github-launch-notes.md`：公开发布文案、repo 描述与当前 non-claims

## 快速开始 / Quick Start

在仓库根目录下运行：

```powershell
python -m src.autoresearch_plus.cli baseline
python -m src.autoresearch_plus.cli search --iterations 8
python -m src.autoresearch_plus.cli report
python -m src.autoresearch_plus.cli benchmark --iterations 8 --trials 2
python -m src.autoresearch_plus.cli benchmark --iterations 1 --trials 3 --task breast_cancer_classification
python -m src.autoresearch_plus.cli benchmark --iterations 1 --trials 3 --task wine_classification
```

默认 demo target 是故意保持简单的。  
loop 会对 `demo_target/train.py` 应用小的 Python AST patch，运行 `demo_target/eval.py`，并且只保留改进。  
当前 search 以 chunk-first 方式工作：它先挑一个 assignment region，例如 `assign:wave`，再在该 region 内应用 patch，并用最近 ledger history 偏置选择。  
benchmark 命令支持按 focused task slice 过滤，包括 numeric fitting、prompt revision、direct bugfix、test-driven code repair、mixed multi-stage task、real-fixture repair、DL/proxy task 和 held-out task。  
held-out task 是 opt-in 的：默认 benchmark 不会跑，必须显式传 `--task`。

## 如何适配 / How To Adapt It

一开始只替换这三样：

1. `config/project.toml`
2. `demo_target/train.py`
3. `demo_target/eval.py`

在你真正需要扩展之前，先不要改 loop logic。
