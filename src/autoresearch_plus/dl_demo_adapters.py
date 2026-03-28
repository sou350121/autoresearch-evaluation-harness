from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from . import llm_proposer
from .adapter import TaskAdapter
from .hypothesis_memory import (
    drop_pure_reject_hypotheses,
    label_hypothesis_beam_roles,
    prioritize_retained_hypotheses,
    render_hypothesis_memory_summary,
    select_hypothesis_beam,
    summarize_hypothesis_memory,
)
from .ledger import RunLedger
from .models import AcceptedState, Candidate, EvalResult, Hypothesis, Proposal


class BaseDlDemoAdapter(TaskAdapter):
    name = ""
    demo_dir = ""
    target_name = "task.py"
    fixes: dict[str, tuple[str, str]] = {}
    fix_summaries: dict[str, str] = {}
    fix_budget = 3

    def __init__(
        self,
        root: Path,
        target_path: Path | None = None,
        proposer_name: str = "chunked_prior",
        *,
        max_fix_budget: int | None = None,
        llm_memory_enabled: bool = True,
        llm_retry_enabled: bool = True,
    ) -> None:
        self.root = root
        self.demo_root = root / self.demo_dir
        self.target_path = target_path or (self.demo_root / self.target_name)
        self.proposer_name = proposer_name
        self.max_fix_budget = max_fix_budget
        self.llm_memory_enabled = llm_memory_enabled
        self.llm_retry_enabled = llm_retry_enabled

    def _fix_budget(self) -> int:
        return self.max_fix_budget if self.max_fix_budget is not None else self.fix_budget

    @property
    def edit_scope(self) -> list[Path]:
        return [self.target_path]

    @property
    def scope_label(self) -> str:
        return str(self.target_path.relative_to(self.root))

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(
            files={self.scope_label.replace("/", "\\"): self.target_path.read_text(encoding="utf-8")},
            label=self.scope_label,
        )

    def restore(self, accepted: AcceptedState) -> None:
        self.target_path.write_text(next(iter(accepted.files.values())), encoding="utf-8")

    def _available_fix_ids(self, current_text: str) -> list[str]:
        return [fix_id for fix_id, (before, _) in self.fixes.items() if before in current_text]

    def _llm_select_fix_ids(
        self,
        *,
        current_text: str,
        eval_output: str,
        exclude_fix_ids: list[str] | None = None,
        memory_summary: str | None = None,
    ) -> tuple[list[str], dict]:
        exclude = set(exclude_fix_ids or [])
        catalog_ids = [fix_id for fix_id in self._available_fix_ids(current_text) if fix_id not in exclude]
        budget = self._fix_budget()
        catalog = {fix_id: self.fix_summaries[fix_id] for fix_id in catalog_ids[:budget]}
        if not catalog:
            return [], {"provider": "llm_codex", "fallback_used": True, "raw_response": ""}
        return llm_proposer.select_fix_ids(
            root=self.root,
            scope_label=self.scope_label,
            source_text=current_text,
            eval_output=eval_output,
            fix_catalog=catalog,
            budget=budget,
            memory_summary=(memory_summary if self.llm_memory_enabled else None),
        )

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        current_text = self.target_path.read_text(encoding="utf-8")
        missing = self._available_fix_ids(current_text)
        if self.proposer_name == "llm_codex":
            eval_result = self.evaluate()
            selected, llm_metadata = self._llm_select_fix_ids(current_text=current_text, eval_output=eval_result.output)
        else:
            llm_metadata = {}
            selected = missing[: self._fix_budget()]
        return Proposal(
            summary=f"{self.proposer_name} {self.name} proposal",
            scope_label=self.scope_label,
            metadata={"proposal_kind": self.proposer_name, "fix_ids": selected, **llm_metadata},
        )

    def retry_after_reject(
        self,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        rejected_proposal: Proposal,
        rejected_result: EvalResult,
    ) -> Proposal | None:
        if self.proposer_name != "llm_codex" or not self.llm_retry_enabled:
            return None
        if rejected_proposal.metadata.get("provider") != "llm_codex":
            return None
        if bool(rejected_proposal.metadata.get("fallback_used")):
            return None
        current_text = self.target_path.read_text(encoding="utf-8")
        tried_fix_ids = [str(fix_id) for fix_id in rejected_proposal.metadata.get("fix_ids", [])]
        selected, llm_metadata = self._llm_select_fix_ids(
            current_text=current_text,
            eval_output=rejected_result.output,
            exclude_fix_ids=tried_fix_ids,
        )
        if not selected:
            return None
        return Proposal(
            summary=f"{self.proposer_name} {self.name} retry proposal",
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "fix_ids": selected,
                "retry_attempt": 2,
                "retry_of_fix_ids": tried_fix_ids,
                **llm_metadata,
            },
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        text = self.target_path.read_text(encoding="utf-8")
        applied: list[str] = []
        for fix_id in proposal.metadata.get("fix_ids", []):
            before, after = self.fixes[fix_id]
            if before in text:
                text = text.replace(before, after, 1)
                applied.append(fix_id)
        self.target_path.write_text(text, encoding="utf-8")
        return Candidate(
            summary=proposal.summary,
            metadata={
                **proposal.metadata,
                "applied_fixes": applied,
                "mutation_summary": " | ".join(applied),
                "mutation_kind": ",".join(applied),
            },
        )

    def evaluate(self) -> EvalResult:
        result = subprocess.run(
            [sys.executable, str(self.demo_root / "eval.py")],
            cwd=self.demo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        if result.returncode != 0:
            return EvalResult(status="failed", score=float("-inf"), output=output)
        match = re.search(r"SCORE=(?P<score>-?\d+(?:\.\d+)?)", output)
        if not match:
            return EvalResult(status="failed", score=float("-inf"), output=output)
        return EvalResult(status="ok", score=float(match.group("score")), output=output)

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.status == "ok" and challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {
            "fix_ids": proposal.metadata.get("fix_ids", []),
            "applied_fixes": candidate.metadata.get("applied_fixes", []),
        }


class CirclesClassificationDemoAdapter(BaseDlDemoAdapter):
    name = "circles_classification_demo"
    demo_dir = "demo_circles_classification"
    fixes = {
        "increase_hidden_width": (
            "HIDDEN_DIM = 4\nSECOND_HIDDEN_DIM = 4\n",
            "HIDDEN_DIM = 32\nSECOND_HIDDEN_DIM = 32\n",
        ),
        "train_longer": (
            "EPOCHS = 5\n",
            "EPOCHS = 120\n",
        ),
        "lower_learning_rate": (
            "LEARNING_RATE = 0.05\n",
            "LEARNING_RATE = 0.01\n",
        ),
    }
    fix_summaries = {
        "increase_hidden_width": "Use a wider MLP so the classifier can model the nonlinear ring boundary.",
        "train_longer": "Train for more epochs so the small CPU demo can converge.",
        "lower_learning_rate": "Reduce the learning rate to stabilize training on the circles task.",
    }


class DigitsImageClassificationDemoAdapter(BaseDlDemoAdapter):
    name = "digits_image_classification_demo"
    demo_dir = "demo_digits_image_classification"
    fixes = {
        "increase_hidden_width": (
            "HIDDEN_DIM = 16\nSECOND_HIDDEN_DIM = 16\n",
            "HIDDEN_DIM = 64\nSECOND_HIDDEN_DIM = 64\n",
        ),
        "train_longer": (
            "EPOCHS = 15\n",
            "EPOCHS = 60\n",
        ),
        "lower_learning_rate": (
            "LEARNING_RATE = 0.01\n",
            "LEARNING_RATE = 0.001\n",
        ),
    }
    fix_summaries = {
        "increase_hidden_width": "Use a larger hidden representation for the 8x8 digits classifier.",
        "train_longer": "Run more optimization steps so the digits classifier reaches a higher accuracy plateau.",
        "lower_learning_rate": "Lower the learning rate to reduce overshooting on the digits task.",
    }


class DiabetesRegressionDemoAdapter(BaseDlDemoAdapter):
    name = "diabetes_regression_demo"
    demo_dir = "demo_diabetes_regression"
    fixes = {
        "increase_hidden_width": (
            "HIDDEN_DIM = 16\nSECOND_HIDDEN_DIM = 16\n",
            "HIDDEN_DIM = 64\nSECOND_HIDDEN_DIM = 64\n",
        ),
        "train_longer": (
            "EPOCHS = 40\n",
            "EPOCHS = 140\n",
        ),
        "lower_learning_rate": (
            "LEARNING_RATE = 0.01\n",
            "LEARNING_RATE = 0.001\n",
        ),
    }
    fix_summaries = {
        "increase_hidden_width": "Use a wider regression MLP to fit the diabetes target better.",
        "train_longer": "Train longer so the regressor reaches a stronger R2 score.",
        "lower_learning_rate": "Reduce the learning rate to improve regression stability.",
    }


class Friedman1RegressionDemoAdapter(BaseDlDemoAdapter):
    name = "friedman1_regression_demo"
    demo_dir = "demo_friedman1_regression"
    fixes = {
        "increase_hidden_width": (
            "HIDDEN_DIM = 16\nSECOND_HIDDEN_DIM = 16\n",
            "HIDDEN_DIM = 64\nSECOND_HIDDEN_DIM = 64\n",
        ),
        "train_longer": (
            "EPOCHS = 40\n",
            "EPOCHS = 140\n",
        ),
        "lower_learning_rate": (
            "LEARNING_RATE = 0.01\n",
            "LEARNING_RATE = 0.001\n",
        ),
    }
    fix_summaries = {
        "increase_hidden_width": "Use a wider regression MLP for the held-out Friedman1 task.",
        "train_longer": "Train longer so the held-out regressor can fit the nonlinear target better.",
        "lower_learning_rate": "Reduce the learning rate to improve held-out regression stability.",
    }


class BreastCancerClassificationDemoAdapter(BaseDlDemoAdapter):
    name = "breast_cancer_classification_demo"
    demo_dir = "demo_breast_cancer_classification"
    fixes = {
        "increase_hidden_width": (
            "HIDDEN_DIM = 4\nSECOND_HIDDEN_DIM = 4\n",
            "HIDDEN_DIM = 32\nSECOND_HIDDEN_DIM = 32\n",
        ),
        "train_longer": (
            "EPOCHS = 5\n",
            "EPOCHS = 100\n",
        ),
        "lower_learning_rate": (
            "LEARNING_RATE = 0.01\n",
            "LEARNING_RATE = 0.001\n",
        ),
    }
    fix_summaries = {
        "increase_hidden_width": "Use a larger hidden representation for the tabular cancer classifier.",
        "train_longer": "Run more epochs to improve validation accuracy on the breast cancer dataset.",
        "lower_learning_rate": "Lower the learning rate to improve convergence on the tabular classifier.",
    }


class WineClassificationDemoAdapter(BaseDlDemoAdapter):
    name = "wine_classification_demo"
    demo_dir = "demo_wine_classification"
    fixes = {
        "increase_hidden_width": (
            "HIDDEN_DIM = 4\nSECOND_HIDDEN_DIM = 4\n",
            "HIDDEN_DIM = 32\nSECOND_HIDDEN_DIM = 32\n",
        ),
        "train_longer": (
            "EPOCHS = 5\n",
            "EPOCHS = 60\n",
        ),
        "lower_learning_rate": (
            "LEARNING_RATE = 0.01\n",
            "LEARNING_RATE = 0.001\n",
        ),
    }
    fix_summaries = {
        "increase_hidden_width": "Use a wider hidden representation for the held-out wine classifier.",
        "train_longer": "Run more optimization steps so the wine classifier can converge past the weak baseline.",
        "lower_learning_rate": "Lower the learning rate to reduce overshooting on the held-out wine task.",
    }


class VeGateProxyDemoAdapter(BaseDlDemoAdapter):
    name = "ve_gate_proxy_demo"
    demo_dir = "demo_ve_gate_proxy"
    fix_budget = 2
    fixes = {
        "enable_alternating_ve": (
            'VE_PATTERN = "none"\n',
            'VE_PATTERN = "alternating"\n',
        ),
        "neutralize_gate_init": (
            'GATE_INIT = "normal"\n',
            'GATE_INIT = "zero"\n',
        ),
        "widen_gate_channels": (
            "GATE_CHANNELS = 4\n",
            "GATE_CHANNELS = 16\n",
        ),
    }
    fix_summaries = {
        "enable_alternating_ve": "Enable alternating value-embedding layers so the model can inject the auxiliary value stream through the stack.",
        "neutralize_gate_init": "Initialize the VE gate at a neutral point so the value path starts stable instead of saturating early.",
        "widen_gate_channels": "Expose more hidden channels to the gate so the value residual can react to a richer input slice.",
    }

    def propose_hypotheses(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> list[Hypothesis]:
        current_text = self.target_path.read_text(encoding="utf-8")
        eval_result = self.evaluate()
        stats = summarize_hypothesis_memory(RunLedger(self.root).load_experiments()) if self.llm_memory_enabled else {}
        memory_summary = render_hypothesis_memory_summary(stats) if self.llm_memory_enabled else None
        if self.proposer_name == "llm_codex":
            selected, llm_metadata = self._llm_select_fix_ids(
                current_text=current_text,
                eval_output=eval_result.output,
                memory_summary=memory_summary,
            )
        else:
            llm_metadata = {}
            selected = ["enable_alternating_ve"]
        primary_fix_ids = selected[:1] or ["enable_alternating_ve"]
        combo_fix_ids: list[str] = []
        for fix_id in [*primary_fix_ids, "enable_alternating_ve", "neutralize_gate_init"]:
            if fix_id in self.fixes and fix_id not in combo_fix_ids:
                combo_fix_ids.append(fix_id)
            if len(combo_fix_ids) >= self._fix_budget():
                break
        hypotheses = [
            Hypothesis(
                hypothesis_id="ve_single_path_restore",
                problem_frame="Restore the VE path with the smallest possible intervention before adding coupled stabilization.",
                target_locus="value_embedding_path",
                mechanism_guess=f"Start with a single intervention: {primary_fix_ids[0]}",
                operator_family="ve_single_fix",
                expected_signal="local proxy score should rise if one missing VE ingredient is dominant",
                risk="medium",
                patch_budget=1,
                fix_ids=primary_fix_ids,
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
            Hypothesis(
                hypothesis_id="ve_combo_stabilization",
                problem_frame="Treat VE restoration as a coupled method requiring path enablement and stable gate behavior together.",
                target_locus="value_embedding_path+gate_init",
                mechanism_guess="Test the smallest paired VE method rather than another isolated single fix.",
                operator_family="ve_combo_fix",
                expected_signal="integration score should rise only when the VE path and gate init are corrected together",
                risk="low",
                patch_budget=self._fix_budget(),
                fix_ids=combo_fix_ids,
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
        ]
        if self.llm_memory_enabled:
            hypotheses = drop_pure_reject_hypotheses(hypotheses, stats)
        return label_hypothesis_beam_roles(select_hypothesis_beam(hypotheses, stats, width=2), stats)

    def proposal_from_hypothesis(
        self,
        hypothesis: Hypothesis,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        branch_id: str,
    ) -> Proposal:
        return Proposal(
            summary=hypothesis.mechanism_guess,
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "branch_id": branch_id,
                "fix_ids": list(hypothesis.fix_ids),
                "provider": hypothesis.metadata.get("provider", self.proposer_name),
                "fallback_used": bool(hypothesis.metadata.get("fallback_used", False)),
                "raw_response": hypothesis.metadata.get("raw_response", ""),
                "beam_role": hypothesis.metadata.get("beam_role", ""),
                "hypothesis": {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "problem_frame": hypothesis.problem_frame,
                    "target_locus": hypothesis.target_locus,
                    "mechanism_guess": hypothesis.mechanism_guess,
                    "operator_family": hypothesis.operator_family,
                    "expected_signal": hypothesis.expected_signal,
                    "risk": hypothesis.risk,
                    "patch_budget": hypothesis.patch_budget,
                    "beam_role": hypothesis.metadata.get("beam_role", ""),
                },
            },
        )

    def retry_after_reject(
        self,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        rejected_proposal: Proposal,
        rejected_result: EvalResult,
    ) -> Proposal | None:
        retry = super().retry_after_reject(accepted, history, revision, rejected_proposal, rejected_result)
        if retry is None:
            return None
        first_fix_ids = [str(fix_id) for fix_id in rejected_proposal.metadata.get("fix_ids", [])]
        combined: list[str] = []
        for fix_id in [*first_fix_ids, *[str(fix_id) for fix_id in retry.metadata.get("fix_ids", [])]]:
            if fix_id not in combined:
                combined.append(fix_id)
            if len(combined) >= self._fix_budget():
                break
        return Proposal(
            summary=retry.summary,
            scope_label=retry.scope_label,
            metadata={**retry.metadata, "fix_ids": combined, "combo_retry": True},
        )


class OptimizerScheduleProxyDemoAdapter(BaseDlDemoAdapter):
    name = "optimizer_schedule_proxy_demo"
    demo_dir = "demo_optimizer_schedule_proxy"
    fix_budget = 2
    fixes = {
        "enable_lr_decay": (
            "FINAL_LR_FRAC = 1.0\n",
            "FINAL_LR_FRAC = 0.1\n",
        ),
        "enable_lr_warmup": (
            "WARMUP_RATIO = 0.0\n",
            "WARMUP_RATIO = 0.2\n",
        ),
        "lower_base_lr": (
            "BASE_LR = 0.3\n",
            "BASE_LR = 0.1\n",
        ),
    }
    fix_summaries = {
        "enable_lr_decay": "Decay the learning rate instead of holding it flat for the whole run.",
        "enable_lr_warmup": "Warm up the learning rate so the high base LR does not destabilize early steps.",
        "lower_base_lr": "Reduce the base LR if the schedule itself is not enough to stabilize training.",
    }

    @staticmethod
    def _canonical_combo_fix_ids() -> list[str]:
        return ["enable_lr_decay", "enable_lr_warmup"]

    def propose_hypotheses(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> list[Hypothesis]:
        current_text = self.target_path.read_text(encoding="utf-8")
        eval_result = self.evaluate()
        stats = summarize_hypothesis_memory(RunLedger(self.root).load_experiments()) if self.llm_memory_enabled else {}
        memory_summary = render_hypothesis_memory_summary(stats) if self.llm_memory_enabled else None
        if self.proposer_name == "llm_codex":
            selected, llm_metadata = self._llm_select_fix_ids(
                current_text=current_text,
                eval_output=eval_result.output,
                memory_summary=memory_summary,
            )
        else:
            llm_metadata = {}
            selected = ["enable_lr_decay"]
        decay_fix_ids = selected[:1] or ["enable_lr_decay"]
        if stats.get("optimizer_schedule_coupling", None) and stats["optimizer_schedule_coupling"].retained_accepts > 0:
            combo_fix_ids = self._canonical_combo_fix_ids()
        else:
            combo_fix_ids: list[str] = []
            for fix_id in [*decay_fix_ids, *self._canonical_combo_fix_ids()]:
                if fix_id in self.fixes and fix_id not in combo_fix_ids:
                    combo_fix_ids.append(fix_id)
                if len(combo_fix_ids) >= self._fix_budget():
                    break
        hypotheses = [
            Hypothesis(
                hypothesis_id="schedule_decay_only",
                problem_frame="Treat the high-LR baseline as mostly a schedule-tail issue and test decay before coupling more knobs.",
                target_locus="optimizer_schedule",
                mechanism_guess=f"Start with the smallest schedule change: {decay_fix_ids[0]}",
                operator_family="schedule_single_fix",
                expected_signal="validation accuracy should rise if the main issue is a missing tail decay",
                risk="medium",
                patch_budget=1,
                fix_ids=decay_fix_ids,
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
            Hypothesis(
                hypothesis_id="optimizer_schedule_coupling",
                problem_frame="Treat the optimizer instability as a coupled warmup-plus-decay problem rather than a single missing knob.",
                target_locus="optimizer_schedule",
                mechanism_guess="Test the smallest coupled schedule method: warmup together with decay.",
                operator_family="schedule_combo_fix",
                expected_signal="accuracy should improve only when both early-step stabilization and end-of-run decay are present",
                risk="low",
                patch_budget=self._fix_budget(),
                fix_ids=combo_fix_ids,
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
            Hypothesis(
                hypothesis_id="lower_base_lr_only",
                problem_frame="Treat the instability as mostly an optimizer scale issue and test a smaller base LR before schedule coupling.",
                target_locus="optimizer_schedule",
                mechanism_guess="Try lowering the base LR without adding schedule structure yet.",
                operator_family="optimizer_single_fix",
                expected_signal="accuracy should rise if the run is mainly unstable because the base LR is too high",
                risk="medium",
                patch_budget=1,
                fix_ids=["lower_base_lr"],
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
        ]
        if self.llm_memory_enabled:
            hypotheses = drop_pure_reject_hypotheses(hypotheses, stats)
        return label_hypothesis_beam_roles(select_hypothesis_beam(hypotheses, stats, width=2), stats)

    def proposal_from_hypothesis(
        self,
        hypothesis: Hypothesis,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        branch_id: str,
    ) -> Proposal:
        return Proposal(
            summary=hypothesis.mechanism_guess,
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "branch_id": branch_id,
                "fix_ids": list(hypothesis.fix_ids),
                "provider": hypothesis.metadata.get("provider", self.proposer_name),
                "fallback_used": bool(hypothesis.metadata.get("fallback_used", False)),
                "raw_response": hypothesis.metadata.get("raw_response", ""),
                "beam_role": hypothesis.metadata.get("beam_role", ""),
                "hypothesis": {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "problem_frame": hypothesis.problem_frame,
                    "target_locus": hypothesis.target_locus,
                    "mechanism_guess": hypothesis.mechanism_guess,
                    "operator_family": hypothesis.operator_family,
                    "expected_signal": hypothesis.expected_signal,
                    "risk": hypothesis.risk,
                    "patch_budget": hypothesis.patch_budget,
                    "beam_role": hypothesis.metadata.get("beam_role", ""),
                },
            },
        )


class CapacityBudgetProxyDemoAdapter(BaseDlDemoAdapter):
    name = "capacity_budget_proxy_demo"
    demo_dir = "demo_capacity_budget_proxy"
    fix_budget = 2
    fixes = {
        "increase_hidden_width": (
            "HIDDEN_DIM = 2\nSECOND_HIDDEN_DIM = 2\n",
            "HIDDEN_DIM = 8\nSECOND_HIDDEN_DIM = 8\n",
        ),
        "train_longer": (
            "EPOCHS = 3\n",
            "EPOCHS = 18\n",
        ),
    }
    fix_summaries = {
        "increase_hidden_width": "Use a wider MLP so the model has enough capacity for the noisy moons boundary.",
        "train_longer": "Train for more epochs so the tiny network gets enough optimization budget.",
    }

    def propose_hypotheses(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> list[Hypothesis]:
        current_text = self.target_path.read_text(encoding="utf-8")
        eval_result = self.evaluate()
        stats = summarize_hypothesis_memory(RunLedger(self.root).load_experiments()) if self.llm_memory_enabled else {}
        memory_summary = render_hypothesis_memory_summary(stats) if self.llm_memory_enabled else None
        if self.proposer_name == "llm_codex":
            selected, llm_metadata = self._llm_select_fix_ids(
                current_text=current_text,
                eval_output=eval_result.output,
                memory_summary=memory_summary,
            )
        else:
            llm_metadata = {}
            selected = ["increase_hidden_width"]
        primary_fix_ids = selected[:1] or ["increase_hidden_width"]
        hypotheses = [
            Hypothesis(
                hypothesis_id="capacity_budget_coupling",
                problem_frame="Treat the baseline as a coupled underfitting problem that needs both more width and more training budget together.",
                target_locus="model_capacity+training_budget",
                mechanism_guess="Test the smallest coupled method: widen the network and train longer in the same revision.",
                operator_family="capacity_budget_combo_fix",
                expected_signal="accuracy should rise only when the model has enough width and enough steps to use it",
                risk="low",
                patch_budget=self._fix_budget(),
                fix_ids=["increase_hidden_width", "train_longer"],
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
            Hypothesis(
                hypothesis_id="capacity_only",
                problem_frame="Treat the weak baseline as mainly a representational bottleneck and test width before spending more steps.",
                target_locus="model_capacity",
                mechanism_guess=f"Start with the smallest capacity change: {primary_fix_ids[0]}",
                operator_family="capacity_single_fix",
                expected_signal="validation accuracy should rise if underfitting is mostly caused by too little width",
                risk="medium",
                patch_budget=1,
                fix_ids=primary_fix_ids,
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
            Hypothesis(
                hypothesis_id="budget_only",
                problem_frame="Treat the weak baseline as mostly an optimization-budget issue and spend more epochs before widening the network.",
                target_locus="training_budget",
                mechanism_guess="Try a longer run without changing capacity first.",
                operator_family="budget_single_fix",
                expected_signal="validation accuracy should rise if the current small model just needs more optimization steps",
                risk="medium",
                patch_budget=1,
                fix_ids=["train_longer"],
                metadata={"provider": self.proposer_name, **llm_metadata},
            ),
        ]
        if self.llm_memory_enabled:
            hypotheses = drop_pure_reject_hypotheses(hypotheses, stats)
        return label_hypothesis_beam_roles(select_hypothesis_beam(hypotheses, stats, width=2), stats)

    def proposal_from_hypothesis(
        self,
        hypothesis: Hypothesis,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        branch_id: str,
    ) -> Proposal:
        return Proposal(
            summary=hypothesis.mechanism_guess,
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "branch_id": branch_id,
                "fix_ids": list(hypothesis.fix_ids),
                "provider": hypothesis.metadata.get("provider", self.proposer_name),
                "fallback_used": bool(hypothesis.metadata.get("fallback_used", False)),
                "raw_response": hypothesis.metadata.get("raw_response", ""),
                "beam_role": hypothesis.metadata.get("beam_role", ""),
                "hypothesis": {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "problem_frame": hypothesis.problem_frame,
                    "target_locus": hypothesis.target_locus,
                    "mechanism_guess": hypothesis.mechanism_guess,
                    "operator_family": hypothesis.operator_family,
                    "expected_signal": hypothesis.expected_signal,
                    "risk": hypothesis.risk,
                    "patch_budget": hypothesis.patch_budget,
                    "beam_role": hypothesis.metadata.get("beam_role", ""),
                },
            },
        )
