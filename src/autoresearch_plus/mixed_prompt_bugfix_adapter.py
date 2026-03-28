from __future__ import annotations

from pathlib import Path

from .bugfix_demo_adapter import BugfixDemoAdapter
from .composite_adapter import CompositeStage, CompositeTaskAdapter
from .models import EvalResult
from .prompt_demo_adapter import PromptDemoAdapter
from .saturation_policies import make_threshold_saturation_policy


class MixedPromptBugfixDemoAdapter(CompositeTaskAdapter):
    name = "mixed_prompt_bugfix_demo"

    def __init__(
        self,
        root: Path,
        proposer_name: str = "chunked_prior",
        stage_order: list[str] | None = None,
        *,
        max_fix_budget: int | None = None,
        llm_memory_enabled: bool = True,
        llm_retry_enabled: bool = True,
    ) -> None:
        prompt_adapter = PromptDemoAdapter(
            root,
            proposer_name=proposer_name,
            max_fix_budget=max_fix_budget,
            llm_memory_enabled=llm_memory_enabled,
            llm_retry_enabled=llm_retry_enabled,
        )
        bugfix_adapter = BugfixDemoAdapter(
            root,
            proposer_name=proposer_name,
            max_fix_budget=max_fix_budget,
            llm_memory_enabled=llm_memory_enabled,
            llm_retry_enabled=llm_retry_enabled,
        )

        def integration_bonus(stage_results: dict[str, EvalResult]) -> float:
            prompt_gain = stage_results["prompt_stage"].score - 84.0
            bugfix_score = stage_results["bugfix_stage"].score
            return 2.0 if prompt_gain >= 2.0 and bugfix_score >= 4.0 else 0.0

        super().__init__(
            root,
            [
                CompositeStage(name="prompt_stage", adapter=prompt_adapter, score_offset=84.0),
                CompositeStage(name="bugfix_stage", adapter=bugfix_adapter),
            ],
            adapter_name=self.name,
            scope_label="demo_prompt/prompt.md + demo_bugfix/buggy_math.py",
            stage_order=stage_order,
            integration_fn=integration_bonus,
            saturation_fn=make_threshold_saturation_policy({"prompt_stage": 100.0, "bugfix_stage": 6.0}),
        )
