# Frozen Evaluation Period Plan

> **For agentic workers:** This plan freezes mechanism development and evaluates the current `autoresearch-plus` skeleton under fixed budgets. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether the current system shows stable, cross-task gains over simple baselines, and whether any claimed `LLM + memory + retry` benefit is real rather than proxy- or adapter-driven.

**Architecture:** Treat the current repository as a frozen experimental artifact. Do not add new search primitives, adapters, or policies. Run a fixed comparison matrix over a frozen task set, report results by task family, and reject any conclusion that depends on single-run best scores, unfair budgets, or proxy-heavy leakage.

**Tech Stack:** Python, `unittest`, existing `autoresearch-plus` benchmark/loop code, current task adapters and fixtures.

---

## Scope

This is an evaluation-period plan, not an implementation-expansion plan.

During this period:
- Freeze mechanism development in the current skeleton:
  - [engine.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/engine.py)
  - [llm_proposer.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/llm_proposer.py)
  - [hypothesis_memory.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/hypothesis_memory.py)
  - [benchmark.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/benchmark.py)
- Do not add new demo tasks, new adapters, new proxy mechanisms, or new beam/memory policies.
- Only make changes required to:
  - equalize comparison budgets
  - expose missing evaluation toggles
  - produce fair benchmark output

This plan is based on adversarial drafting: 3 agents proposed the evaluation protocol, 3 agents attacked leakage, fairness, and overclaiming.

## Questions This Period Must Answer

Only answer these three questions:

1. Does `LLM` provide independent value over simple non-LLM baselines?
2. Do `memory` and `retry` provide independent value beyond plain `llm_codex`?
3. Do any gains transfer across task families, rather than staying trapped inside proxy-heavy or adapter-scripted tasks?

If the period does not answer these cleanly, the correct outcome is not “add more mechanisms.” The correct outcome is “system evidence is still task-shaped.”

## Frozen Task Set

Run the existing task set and report it in families. Do not add tasks during this period.

### Family A: Core Product / Code Tasks
- `numeric_demo`
- `prompt_demo`
- `bugfix_demo`
- `code_repair_demo`
- `mixed_prompt_code_repair_demo`
- `mixed_prompt_bugfix_demo`
- `miro_trace_parser_demo`
- `miro_trace_html_escape_demo`
- `deepscientist_local_ui_url_demo`

### Family B: DL / Proxy Tasks
- `circles_classification_demo`
- `digits_image_classification_demo`
- `diabetes_regression_demo`
- `breast_cancer_classification_demo`
- `ve_gate_proxy_demo`
- `optimizer_schedule_proxy_demo`
- `capacity_budget_proxy_demo`

### Reporting Tags

Every task must also carry one of these interpretation tags in the report:
- `real-fixture`
- `proxy`
- `toy/demo`

Rules:
- `prompt_demo` is not acceptable as headline evidence for “generic autoresearch.”
- The three method proxies are acceptable as method-search evidence, but not as direct evidence of unknown-method discovery in real systems.
- Final conclusions must be broken down by family and by interpretation tag before any aggregate summary.

## Fixed Comparison Matrix

Evaluate these four modes only:

1. `single_step_random`
2. `chunked_prior`
3. `llm_codex_no_memory`
4. `llm_codex_memory_retry`

Definitions:
- `single_step_random`: simplest non-LLM baseline
- `chunked_prior`: current heuristic search baseline
- `llm_codex_no_memory`: `llm_codex` with no memory summary and no memory-driven ranking bias
- `llm_codex_memory_retry`: current strongest LLM path with memory and retry enabled

Do not add more modes during this period.

## Fairness Constraints

These are hard requirements. If any are violated, the run is not valid.

### Budget Equality
- Same `iterations` for all modes on a given task
- Same `trial` count for all modes
- Same maximum atomic edit / fix budget per iteration
- Same branch budget where branching exists
- Retry counts against the same overall iteration/edit budget; it is not free

### Information Equality
- All modes see the same task artifact and evaluation output
- Any memory access must be explicit and mode-scoped
- No mode may inherit accepted memory from another mode’s run

### Start-State Equality
- Every `(task, mode, seed)` run starts from the same baseline snapshot
- Memory stores are isolated per mode unless the experiment explicitly tests memory effects within that mode

### Reporting Equality
- Do not use `best_score` as a headline metric
- Do not summarize all tasks as a single blended score
- Always report by family first, then overall

## Primary Metrics

These are the only headline metrics:
- `success_rate`
- `median_gain`
- `median_first_accept_iter`
- `accept_precision`

Secondary metrics:
- `wasted_iterations`
- `saturation_stop_rate`

Appendix-only metric:
- `best_score`

For method-proxy tasks, include these appendix metrics if already available without changing core mechanisms:
- `retained_method_reuse_rate`
- `exploration_to_exploitation_conversion`

## Pass / Fail Gates

### Gate 1: Independent LLM Value

`LLM` only counts as providing real value if either `llm_codex_no_memory` or `llm_codex_memory_retry` beats `single_step_random` on held-out results with:
- higher `success_rate`
- non-worse `accept_precision`
- non-worse `median_first_accept_iter`

### Gate 2: Independent Memory / Retry Value

`memory` and `retry` only count as adding value if `llm_codex_memory_retry` beats `llm_codex_no_memory` on held-out results with stable gains, not one-off best scores.

If this does not hold, the system must not be described as:
- `LLM self-optimization`
- `LLM self-review`

At most, it may be described as:
- `LLM-guided proposal selection under hard evaluation`
- `memory-aware retry under constrained action space`

### Gate 3: Cross-Family Transfer

No claim of “closer to generic autoresearch” is allowed unless gains appear outside a single proxy-heavy family.

Minimum bar:
- non-negative median gain advantage in more than one task family
- no catastrophic regression in `real-fixture` tasks
- evidence not limited to `prompt/mixed` budget-sensitive tasks

### Fail Conditions

The period fails if any of these dominates the results:
- gains appear only in proxy tasks
- gains collapse on real fixtures
- `accept_precision` drops materially as stronger modes are enabled
- conclusions depend on `best_score` rather than medians and success rates
- stronger modes win only because they implicitly get larger edit/fix budgets

## Held-Out Protocol

At minimum, split the frozen task set into:
- `development/tuned set`
- `held-out set`

Rules:
- Mechanism decisions must not change after the split
- Final headline conclusions come from the held-out set
- Development-set results can be shown, but only as supporting evidence

If the current repository cannot support a meaningful split without changing mechanisms, state that limitation explicitly in the report. Do not hide it.

## Execution Order

### Task 1: Freeze The Evaluation Surface

**Files:**
- Review: [engine.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/engine.py)
- Review: [llm_proposer.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/llm_proposer.py)
- Review: [hypothesis_memory.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/hypothesis_memory.py)
- Review: [benchmark.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/benchmark.py)

- [ ] Record the exact commit or working-tree snapshot that defines the frozen evaluation build.
- [ ] List any already-known fairness violations that must be corrected before benchmark runs count.
- [ ] Refuse all new mechanism work until this evaluation period is complete.

### Task 2: Normalize Comparison Budgets

**Files:**
- Review and likely modify: [benchmark.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/benchmark.py)
- Review task adapters under [src/autoresearch_plus](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus)

- [ ] Audit each compared mode for per-iteration fix/edit budget mismatches.
- [ ] Normalize `max_fixes_per_iteration` or equivalent knobs so mode comparisons are fair.
- [ ] Verify retry does not silently exceed the comparison budget.
- [ ] Add explicit assertions or benchmark metadata that make budget equality inspectable.

### Task 3: Expose The Four Required Modes

**Files:**
- Modify: [benchmark.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/benchmark.py)
- Review: [llm_proposer.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/llm_proposer.py)

- [ ] Ensure the benchmark can run:
  - `single_step_random`
  - `chunked_prior`
  - `llm_codex_no_memory`
  - `llm_codex_memory_retry`
- [ ] Make `llm_codex_no_memory` explicit rather than inferred.
- [ ] Make `llm_codex_memory_retry` explicit rather than relying on current defaults.

### Task 4: Add Family-First Reporting

**Files:**
- Modify: [benchmark.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/benchmark.py)
- Optionally modify: [README.md](C:/Users/sou35/Documents/repo-research/autoresearch-plus/README.md)

- [ ] Group all benchmark output by task family and interpretation tag.
- [ ] Promote only the headline metrics into the main report.
- [ ] Demote `best_score` to appendix output.
- [ ] Include a short warning when a conclusion is supported only by proxy-heavy tasks.

### Task 5: Run The Frozen Matrix

**Files:**
- Use current benchmark entrypoint in [benchmark.py](C:/Users/sou35/Documents/repo-research/autoresearch-plus/src/autoresearch_plus/benchmark.py)

- [ ] Pre-register a fixed seed list for `5` trials.
- [ ] Run the full matrix: `16 tasks × 4 modes × 5 trials` if all tasks remain in scope.
- [ ] If runtime is too high, produce a documented reduced matrix that still preserves all task families.
- [ ] Store raw outputs and a summarized table in the evaluation report directory.

### Task 6: Write The Evaluation Report

**Files:**
- Create: `docs/superpowers/plans/2026-03-25-frozen-evaluation-report.md` or adjacent report file

- [ ] Write family-by-family results first.
- [ ] State whether `LLM` shows independent value.
- [ ] State whether `memory/retry` shows independent value.
- [ ] State whether evidence transfers beyond proxy-heavy tasks.
- [ ] End with exactly one of:
  - `continue evaluation on same frozen system`
  - `simplify system`
  - `resume mechanism development`

## Expected Outcome Language

Do not overclaim. Use these labels:

- If evidence is weak:
  - `generic skeleton exists`
  - `evidence still task-shaped`

- If evidence is moderate:
  - `LLM-guided proposal under hard evaluation shows cross-family promise`

- Only if all gates pass:
  - `current frozen system shows stable cross-task gains beyond simple baselines`

## Recommendation

Run this frozen evaluation period before any more mechanism work.

If the results do not clear the gates above, the next action should be simplification, not expansion.
