# GitHub Launch Notes

日期 / Date: 2026-03-28  
仓库 / Repo: `https://github.com/sou350121/autoresearch-evaluation-harness`

## 项目定位 / Positioning

`autoresearch-plus` 是一个以评估为先的 `autoresearch` 风格实验框架。  
它用固定任务适配器、明确的标量评估信号，以及硬性的 keep/discard gate 来比较不同提案策略。  
当前系统的可信定位是：**benchmark-driven、task-dependent、adapter-shaped**，而不是通用 research agent。

`autoresearch-plus` is an evaluation-first experimental harness for autoresearch-style loops.  
It compares proposal strategies under fixed task adapters, explicit scalar evaluation, and hard keep/discard gates.  
The current system is best described as **benchmark-driven, task-dependent, and adapter-shaped**, not a general research agent.

## 项目目标 / Project Goals

- 保持 autoresearch loop 足够小、足够本地化、足够可审计  
  Keep the loop small, local, and auditable.
- 在相同预算下比较不同 proposal strategy，而不是只看单次最好分  
  Compare proposal strategies under the same evaluation budget instead of chasing a single best run.
- 让 task-dependent 的强弱和失败都可见，而不是被一个总分掩盖  
  Make task-dependent wins and failures visible instead of hiding them behind one aggregate score.
- 将默认 benchmark 与 opt-in held-out 检查分开  
  Separate default benchmark tasks from opt-in held-out checks.
- 允许 LLM 参与 proposal，但不让模型自己判定是否成功  
  Let the LLM participate in proposal while keeping success judgment outside the model.

## GitHub About 文案 / GitHub About Copy

### About Description

简中：  
`一个以评估为先的 autoresearch 风格本地实验框架，包含 LLM proposal、硬性 keep/discard 与可基准化的 task adapter。`

English:  
`Local evaluation-first harness for autoresearch-style loops with LLM proposal, hard keep/discard, and benchmarkable task adapters.`

### Subtitle

简中：  
`一个小型、本地、可审计的 autoresearch 实验框架，用固定评估、明确 task adapter 与硬性 keep/discard gate 比较不同提案策略。`

English:  
`A small local experimental harness for comparing autoresearch-style proposal strategies under fixed evaluation, explicit task adapters, and hard keep/discard gates.`

### Topics

- `autoresearch`
- `evaluation-harness`
- `llm-in-the-loop`
- `benchmarking`
- `task-adapters`
- `keep-discard`
- `experiment-tracking`
- `research-tooling`

## README 简介文案 / README Intro Copy

简中：

`autoresearch-evaluation-harness` 是一个用于比较 autoresearch 风格 proposal strategy 的本地实验框架。  
它强调固定评估、明确 task adapter 与硬性 keep/discard gate。  
当前版本是一个 task-dependent 的 benchmark harness，而不是通用 autonomous research agent。

English:

`autoresearch-evaluation-harness` is a local experimental harness for comparing autoresearch-style proposal strategies.  
It emphasizes fixed evaluation, explicit task adapters, and hard keep/discard gates.  
The current system is a task-dependent benchmark harness, not a broad autonomous research agent.

## 发布重点 / Release Highlights

- 已具备可运行的 `baseline -> search -> report -> benchmark` 主流程  
  Working `baseline -> search -> report -> benchmark` loop.
- benchmark 支持通过 `benchmark --task ...` 做 focused task slice  
  Benchmark supports focused task slices through `benchmark --task ...`.
- LLM benchmark trial 采用 subprocess isolation，结果更可信  
  LLM benchmark trials now use subprocess isolation for more reliable evaluation.
- benchmark mode 已明确分离：
  - `single_step_random`
  - `chunked_prior`
  - `llm_codex_no_memory`
  - `llm_codex_memory_retry`
- held-out task 现为 opt-in，不再混入默认 benchmark  
  Held-out tasks are opt-in and excluded from default benchmark runs.
- family-first reporting 与 focused task slices 已成型  
  Family-first reporting and focused task slices are now part of the workflow.
- 冻结评估结论已写入仓库文档，而不是只停留在临时实验  
  Frozen evaluation evidence is now documented in-repo instead of living only in ad hoc runs.

## 当前证据 / Current Evidence

- 作为 evaluation harness，这个系统已经能稳定运行：task filtering、subprocess-isolated trials、report 与 benchmark summary 都已接通  
  As an evaluation harness, the system is operational: task filtering, subprocess-isolated trials, reporting, and benchmark summaries all work together.
- 当前最稳定的结论不是“LLM 全面更强”，而是“表现高度 task-dependent”  
  The strongest current conclusion is not broad LLM superiority, but strong task dependence.
- `memory + retry` 有局部正信号，最明显在 `diabetes_regression`，但还没有跨任务的广泛证据  
  `memory + retry` shows local positive signal, especially on `diabetes_regression`, but not broad cross-task proof.
- 当前两个 held-out task 呈混合结果：
  - `wine_classification` 更偏向非 LLM guided baseline
  - `friedman1_regression` 更偏向 LLM proposal  
  The current two held-out tasks are mixed:
  - `wine_classification` favored non-LLM guided baselines
  - `friedman1_regression` favored LLM proposal

## 当前不主张的内容 / Non-Claims

- 不主张 `autoresearch-plus` 已经是通用 autoresearch system  
  This launch does not claim that `autoresearch-plus` is already a general-purpose autoresearch system.
- 不主张 `llm_codex` 已经在整个 benchmark 集合上普遍优于非 LLM baseline  
  This launch does not claim that `llm_codex` is broadly better than non-LLM baselines across the benchmark set.
- 不主张 held-out 结果已经足够支撑稳定泛化结论  
  This launch does not claim that held-out evidence is already conclusive.
- 不主张当前系统已经能广泛解决 unknown-method problems  
  This launch does not claim robust unknown-method solving across tasks.

## 建议避免的词 / Terms To Avoid

- `general`
- `autonomous`
- `fully self-improving`
- `general research agent`
- `unknown-method solver`
- `AGI`
- `self-evolving`
- `fully automatic research system`

## GitHub Release 正文草案 / GitHub Release Body Draft

### 简中

`autoresearch-evaluation-harness` 当前版本重点不是扩展更多机制，而是把 autoresearch 风格 loop 的评估面做扎实。  
现在仓库已经包含固定 task adapter、硬性 keep/discard、可重复 benchmark、LLM proposal 路径，以及 opt-in held-out 检查。  
当前证据支持的结论是：这个系统作为 evaluation harness 已成立，但它的表现仍然明显 task-dependent，尚不支持 broad generalization claim。

### English

This release focuses on making the evaluation surface of an autoresearch-style loop more trustworthy, not on adding more mechanism layers.  
The repo now includes fixed task adapters, hard keep/discard gates, repeatable benchmarking, an LLM proposal path, and opt-in held-out checks.  
The current evidence supports the system as an evaluation harness, while still showing clearly task-dependent behavior rather than broad generalization.
