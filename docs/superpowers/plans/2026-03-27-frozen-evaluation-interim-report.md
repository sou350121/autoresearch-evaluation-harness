# Frozen Evaluation Interim Report

Date: 2026-03-27
Repo: `C:\Users\sou35\Documents\repo-research\autoresearch-plus`
Status: mechanism-frozen, evidence-gathering only

## Scope

This report summarizes the current frozen evaluation evidence after:

- budget normalization
- explicit benchmark mode separation
- family-first reporting
- per-trial benchmark subprocess isolation
- reduced benchmark runs on `mixed`, `real-fixture`, and `dl/proxy`
- targeted `3-trial` stability checks on the most informative DL tasks

The intent is to answer three questions:

1. Does `llm_codex` show independent value?
2. Does `memory + retry` show independent value beyond plain `llm_codex`?
3. Is the system showing general gains, or only task-specific wins?

## Modes Under Comparison

- `single_step_random`
- `chunked_prior`
- `llm_codex_no_memory`
- `llm_codex_memory_retry`

## What Is Already Clear

### 1. `llm_codex` is not uniformly better

Current evidence does not support any claim that LLM-driven proposal is globally stronger.

Observed pattern:

- some tasks favor `llm_codex`
- some tasks favor non-LLM baselines
- many tasks show no separation at all

This means the current system is task-sensitive, not universally improved by adding LLM proposal.

### 2. `memory + retry` has not yet shown stable independent value

Across the reduced frozen runs completed so far, `llm_codex_memory_retry` has repeatedly tied `llm_codex_no_memory`.

That does not prove the mechanism is useless. It does mean:

- there is not yet cross-task evidence that it earns separate credit
- current gains appear to come primarily from base LLM proposal quality, not from memory/retry

### 3. Many current tasks have low discriminative power

The weakest task families for mode separation so far are:

- `mixed` toy tasks
- `real-fixture` tasks
- method proxies under current low-budget settings

These tasks are still useful for correctness and regression coverage, but not currently strong evidence for ranking search strategies.

## Evidence By Family

### Mixed Family

Budget:

- `iterations=4`
- `trials=1`

Results:

- `mixed`
  - all 4 modes tied
  - `median_gain=8.0`
- `mixed_bugfix`
  - `chunked_prior`, `llm_codex_no_memory`, and `llm_codex_memory_retry` tied
  - `median_gain=11.0`
  - `single_step_random` lower at `median_gain=9.0`

Interpretation:

- these toy mixed tasks currently do not separate LLM from non-LLM methods
- they do show that `single_step_random` can be weaker than guided approaches
- they do not show independent `memory + retry` benefit

### Real-Fixture Family

Budget:

- `iterations=1`
- `trials=1`

Tasks:

- `miro_trace_parser`
- `miro_trace_html_escape`
- `deepscientist_local_ui_url`

Results:

- all 4 modes tied on all 3 tasks

Interpretation:

- these fixtures currently behave more like constrained single-answer repair tasks
- they validate execution and correctness
- they do not currently provide evidence that LLM proposal or memory/retry improves search quality

### DL / Proxy Family

#### Directional `1x1` result across all 7 tasks

Budget:

- `iterations=1`
- `trials=1`

Findings:

- `circles_classification`
  - non-LLM modes better than LLM modes
- `digits_image_classification`
  - non-LLM modes better than LLM modes
- `diabetes_regression`
  - LLM modes better than non-LLM modes
- `breast_cancer_classification`
  - LLM modes better than non-LLM modes
- `ve_gate_proxy`
  - all 4 modes tied
- `optimizer_schedule_proxy`
  - all 4 modes tied
- `capacity_budget_proxy`
  - all 4 modes tied

Interpretation:

- the strongest mode separation currently appears in the four traditional DL tasks
- the three method proxies are not yet separating modes under the current low-budget evaluation setting

#### Stability check: `iterations=1`, `trials=3`

Completed tasks:

- `circles_classification`
- `digits_image_classification`
- `breast_cancer_classification`

Results:

- `circles_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.520000`
  - `llm_codex_*`: `median_gain=0.420000`
- `digits_image_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.011111`
  - `llm_codex_*`: `median_gain=0.005556`
- `breast_cancer_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.008772`
  - `llm_codex_*`: `median_gain=0.017544`

Shared properties across these runs:

- `success_rate=1.000`
- `first_accept=1.0`
- `accept_precision=1.000`
- `trial_failure_rate=0.000`

Interpretation:

- the earlier `1x1` directional signal is stable for these three tasks
- `llm_codex` is better on `breast_cancer_classification`
- `llm_codex` is worse on `circles_classification` and `digits_image_classification`
- `llm_codex_memory_retry` remains tied with `llm_codex_no_memory`

#### Focused follow-up after subprocess isolation: `diabetes_regression`

Budget:

- `iterations=1`
- `trials=3`
- modes:
  - `llm_codex_no_memory`
  - `llm_codex_memory_retry`

Results:

- `llm_codex_memory_retry`
  - `success_rate=1.000`
  - `median_gain=0.094834`
  - `first_accept=1.0`
  - `accept_precision=1.000`
  - `trial_failure_rate=0.000`
- `llm_codex_no_memory`
  - `success_rate=0.667`
  - `median_gain=0.094834`
  - `first_accept=1.0`
  - `accept_precision=0.667`
  - `trial_failure_rate=0.000`

Interpretation:

- trial subprocess isolation was sufficient to complete this previously unstable check
- this is the first frozen-evaluation result where `memory + retry` shows a measurable advantage
- the advantage is reliability and completion quality, not a larger median gain

#### Formal focused matrix rerun: `4 tasks`, `iterations=1`, `trials=3`

Tasks:

- `circles_classification`
- `digits_image_classification`
- `diabetes_regression`
- `breast_cancer_classification`

Results:

- `breast_cancer_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.008772`
  - `llm_codex_no_memory` / `llm_codex_memory_retry`: `median_gain=0.017544`
- `circles_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.520000`
  - `llm_codex_no_memory` / `llm_codex_memory_retry`: `median_gain=0.420000`
- `diabetes_regression`
  - `single_step_random` / `chunked_prior`: `median_gain=0.006460`
  - `llm_codex_no_memory`: `median_gain=0.094834`
  - `llm_codex_memory_retry`: `median_gain=0.102070`
- `digits_image_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.011111`
  - `llm_codex_no_memory` / `llm_codex_memory_retry`: `median_gain=0.005556`

Shared properties across this rerun:

- `success_rate=1.000`
- `first_accept=1.0`
- `accept_precision=1.000`
- `trial_failure_rate=0.000`

Interpretation:

- `breast_cancer_classification`: LLM remains stably stronger than non-LLM baselines
- `circles_classification`: non-LLM baselines remain stably stronger than LLM
- `diabetes_regression`: LLM remains stably stronger than non-LLM baselines; in this rerun `memory + retry` showed a small positive gain advantage over plain `llm_codex`, but later repeated matrix evidence did not keep that margin
- `digits_image_classification`: the earlier one-run `memory + retry` lead did not reproduce; the more conservative interpretation is that it was a single-run fluctuation

#### Narrow focused rerun: `diabetes_regression` only

Budget:

- `iterations=1`
- `trials=3`

Results:

- `single_step_random`
  - `median_gain=0.006460`
- `chunked_prior`
  - `median_gain=0.006460`
- `llm_codex_no_memory`
  - `median_gain=0.094834`
- `llm_codex_memory_retry`
  - `median_gain=0.102070`

Shared properties:

- all modes `success_rate=1.000`
- all modes `first_accept=1.0`
- all modes `accept_precision=1.000`
- all modes `trial_failure_rate=0.000`

Interpretation:

- the earlier `diabetes_regression` result reproduced under a narrower focused rerun
- `memory + retry` again outperformed plain `llm_codex`
- this is now the clearest local evidence that `memory + retry` can add value
- this remains a task-local result, not a broad cross-task conclusion

#### Repeated focused matrix rerun: `4 tasks`, `iterations=1`, `trials=3`

Tasks:

- `circles_classification`
- `digits_image_classification`
- `diabetes_regression`
- `breast_cancer_classification`

Results:

- `breast_cancer_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.008772`
  - `llm_codex_no_memory` / `llm_codex_memory_retry`: `median_gain=0.017544`
- `circles_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.520000`
  - `llm_codex_no_memory` / `llm_codex_memory_retry`: `median_gain=0.420000`
- `diabetes_regression`
  - `single_step_random` / `chunked_prior`: `median_gain=0.006460`
  - `llm_codex_no_memory` / `llm_codex_memory_retry`: `median_gain=0.094834`
- `digits_image_classification`
  - `single_step_random` / `chunked_prior`: `median_gain=0.011111`
  - `llm_codex_no_memory` / `llm_codex_memory_retry`: `median_gain=0.005556`

Shared properties across this rerun:

- `success_rate=1.000`
- `first_accept=1.0`
- `accept_precision=1.000`
- `trial_failure_rate=0.000`

Interpretation:

- the broad 4-task directional pattern remained stable
- `breast_cancer_classification`: LLM remained stronger than non-LLM baselines
- `circles_classification` and `digits_image_classification`: non-LLM baselines remained stronger than LLM
- `diabetes_regression`: LLM remained much stronger than non-LLM baselines, but `llm_codex_memory_retry` no longer beat plain `llm_codex`; they tied at `median_gain=0.094834`
- the current strongest fair reading is that `memory + retry` has a meaningful local positive signal on `diabetes_regression`, but not yet a stable replicated advantage under the broader focused matrix

### Held-Out Task

Budget:

- `iterations=1`
- `trials=3`

Task:

- `wine_classification`

Results:

- `single_step_random` / `chunked_prior`
  - `median_gain=0.583333`
- `llm_codex_no_memory`
  - `median_gain=0.500000`
- `llm_codex_memory_retry`
  - `median_gain=0.250000`

Shared properties:

- all modes `success_rate=1.000`
- all modes `first_accept=1.0`
- all modes `accept_precision=1.000`
- all modes `trial_failure_rate=0.000`

Interpretation:

- this held-out task extends the current pattern rather than reversing it
- non-LLM guided baselines remained stronger than both LLM modes
- `memory + retry` underperformed plain `llm_codex` on this held-out task
- the held-out result strengthens the claim that current LLM gains are task-dependent and do not yet establish broad generalization

#### Second held-out task: `friedman1_regression`

Budget:

- `iterations=1`
- `trials=3`

Results:

- `single_step_random` / `chunked_prior`
  - `median_gain=0.011101`
- `llm_codex_no_memory` / `llm_codex_memory_retry`
  - `median_gain=0.081095`

Shared properties:

- all modes `success_rate=1.000`
- all modes `first_accept=1.0`
- all modes `accept_precision=1.000`
- all modes `trial_failure_rate=0.000`

Interpretation:

- the second held-out task did not match the first
- on `friedman1_regression`, both LLM modes clearly outperformed the non-LLM guided baselines
- `memory + retry` did not add an extra gain over plain `llm_codex`; they tied
- taken together, the first two held-out tasks strengthen the same top-line conclusion: the current system remains task-dependent, and held-out evidence does not yet support a broad generalization claim in either direction

## Stability and Operational Risks

The evaluation surfaced a non-trivial operational finding:

- `diabetes_regression + llm_codex` `3-trial` stability runs exited abnormally around the second or third attempt without a useful Python traceback
- longer `method proxy` `3-trial` batches also showed hanging behavior and left temporary benchmark subprocesses behind

Interpretation:

- LLM-path runtime stability is currently part of the evaluation surface
- it should be counted as a negative in the frozen report, not treated as external noise and ignored

After enabling per-trial subprocess isolation in the benchmark runner:

- the focused `diabetes_regression` LLM-only rerun completed cleanly
- the earlier abnormal exit did not reproduce in that isolated check

This does not fully clear the stability concern. It does narrow the problem:

- part of the earlier instability came from benchmark orchestration, not only from search logic
- longer proxy batches should still be treated as operationally sensitive until repeated cleanly

## Current Best-Supported Claims

The strongest claims supportable now are:

1. `llm_codex` can provide better proposal quality on some tasks.
2. `llm_codex` can also underperform simple guided baselines on other tasks.
3. The current benefit of LLM proposal is task-dependent, not general.
4. `memory + retry` has not yet shown broad, cross-task independent value.
5. Several benchmark tasks are still useful for correctness coverage but weak for discriminating among search strategies.
6. LLM-path runtime stability is itself an unresolved evaluation issue.
7. Per-trial subprocess isolation is now required for trustworthy LLM benchmark numbers.
8. The strongest current positive signal for `memory + retry` is concentrated in `diabetes_regression`, not spread broadly across the frozen task set.
9. `diabetes_regression` has repeated focused evidence that `memory + retry` can add value, but the advantage over plain `llm_codex` is not yet stable across repeated `4-task` focused matrix reruns.
10. The held-out slice is now mixed: `wine_classification` favored non-LLM guided baselines, while `friedman1_regression` favored LLM proposal; this reinforces task-dependence rather than broad generalization.

## What Should Not Be Claimed Yet

The current evidence does **not** justify claiming:

- `llm_codex` is generally better than non-LLM methods
- method-memory has already proven broad value
- the system has already demonstrated robust self-improvement on unknown-method problems across the frozen task set
- two held-out tasks are enough to claim stable held-out generalization in either direction

## Recommended Next Step

Do not add mechanisms.

Do exactly two things:

1. continue frozen evaluation only on the most informative tasks:
   - `circles_classification`
   - `digits_image_classification`
   - `diabetes_regression`
   - `breast_cancer_classification`
2. keep subprocess trial isolation enabled and treat non-isolated benchmark numbers as lower-trust
3. treat the current two-task held-out slice as evidence that the system is still task-dependent and adapter-shaped, not yet broadly generalizing

Keep the evaluation budget fixed:

- `iterations=1`
- `trials=3`

The objective is no longer breadth. It is to establish whether the observed LLM advantage/disadvantage pattern is stable and reproducible, and whether a larger held-out slice continues to reinforce task-dependence or begins to show a more coherent generalization trend.
