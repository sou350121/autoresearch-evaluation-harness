from __future__ import annotations

from pathlib import Path

from .config import load_project_config
from .dl_demo_adapters import (
    BreastCancerClassificationDemoAdapter,
    CapacityBudgetProxyDemoAdapter,
    CirclesClassificationDemoAdapter,
    DiabetesRegressionDemoAdapter,
    DigitsImageClassificationDemoAdapter,
    Friedman1RegressionDemoAdapter,
    OptimizerScheduleProxyDemoAdapter,
    VeGateProxyDemoAdapter,
    WineClassificationDemoAdapter,
)
from .bugfix_demo_adapter import BugfixDemoAdapter
from .code_repair_demo_adapter import CodeRepairDemoAdapter
from .deepscientist_local_ui_url_adapter import DeepScientistLocalUiUrlAdapter
from .engine import run_baseline_with_adapter, run_search_with_adapter
from .ledger import RunLedger
from .miro_trace_html_escape_adapter import MiroTraceHtmlEscapeAdapter
from .mixed_prompt_bugfix_adapter import MixedPromptBugfixDemoAdapter
from .mixed_prompt_code_repair_adapter import MixedPromptCodeRepairDemoAdapter
from .miro_trace_parser_adapter import MiroTraceParserAdapter
from .numeric_demo_adapter import NumericDemoAdapter
from .prompt_demo_adapter import PromptDemoAdapter


def _build_adapter(root: Path):
    config = load_project_config(root)
    adapter_kwargs = {
        "proposer_name": config.proposer_name,
        "max_fix_budget": config.max_fix_budget,
        "llm_memory_enabled": config.llm_memory_enabled,
        "llm_retry_enabled": config.llm_retry_enabled,
    }
    if config.adapter_name == "numeric_demo":
        return NumericDemoAdapter(root, config)
    if config.adapter_name == "prompt_demo":
        return PromptDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "bugfix_demo":
        return BugfixDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "circles_classification_demo":
        return CirclesClassificationDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "digits_image_classification_demo":
        return DigitsImageClassificationDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "diabetes_regression_demo":
        return DiabetesRegressionDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "friedman1_regression_demo":
        return Friedman1RegressionDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "breast_cancer_classification_demo":
        return BreastCancerClassificationDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "wine_classification_demo":
        return WineClassificationDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "ve_gate_proxy_demo":
        return VeGateProxyDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "optimizer_schedule_proxy_demo":
        return OptimizerScheduleProxyDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "capacity_budget_proxy_demo":
        return CapacityBudgetProxyDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "code_repair_demo":
        return CodeRepairDemoAdapter(root, **adapter_kwargs)
    if config.adapter_name == "deepscientist_local_ui_url_demo":
        return DeepScientistLocalUiUrlAdapter(root, **adapter_kwargs)
    if config.adapter_name == "miro_trace_html_escape_demo":
        return MiroTraceHtmlEscapeAdapter(root, **adapter_kwargs)
    if config.adapter_name == "miro_trace_parser_demo":
        return MiroTraceParserAdapter(root, **adapter_kwargs)
    if config.adapter_name == "mixed_prompt_code_repair_demo":
        return MixedPromptCodeRepairDemoAdapter(root, stage_order=config.composite_stage_order or None, **adapter_kwargs)
    if config.adapter_name == "mixed_prompt_bugfix_demo":
        return MixedPromptBugfixDemoAdapter(root, stage_order=config.composite_stage_order or None, **adapter_kwargs)
    raise RuntimeError(f"Unsupported adapter: {config.adapter_name}")


def run_baseline(root: Path):
    ledger = RunLedger(root)
    adapter = _build_adapter(root)
    return run_baseline_with_adapter(root, adapter, ledger)


def run_search(root: Path, iterations: int):
    ledger = RunLedger(root)
    adapter = _build_adapter(root)
    return run_search_with_adapter(root, adapter, ledger, iterations=iterations)
