from __future__ import annotations

import importlib.util
from pathlib import Path

from . import llm_proposer
from .adapter import TaskAdapter
from .models import AcceptedState, Candidate, EvalResult, Proposal


FIXES = {
    "fix_add": ("return a - b", "return a + b"),
    "fix_safe_div": ("return 0.0", "raise ZeroDivisionError('division by zero')"),
    "fix_clamp": ("return min(low, min(value, high))", "return max(low, min(value, high))"),
}


class BugfixDemoAdapter(TaskAdapter):
    name = "bugfix_demo"

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
        self.target_path = target_path or (root / "demo_bugfix" / "buggy_math.py")
        self.proposer_name = proposer_name
        self.max_fix_budget = max_fix_budget
        self.llm_memory_enabled = llm_memory_enabled
        self.llm_retry_enabled = llm_retry_enabled

    def _fix_budget(self) -> int:
        if self.max_fix_budget is not None:
            return self.max_fix_budget
        return 2 if self.proposer_name == "chunked_prior" else 1

    @property
    def edit_scope(self) -> list[Path]:
        return [self.target_path]

    @property
    def scope_label(self) -> str:
        return str(self.target_path.relative_to(self.root))

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(files={self.scope_label.replace("/", "\\"): self.target_path.read_text(encoding="utf-8")}, label=self.scope_label)

    def restore(self, accepted: AcceptedState) -> None:
        content = next(iter(accepted.files.values()))
        self.target_path.write_text(content, encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        current_text = self.target_path.read_text(encoding="utf-8")
        missing_fixes = [fix_id for fix_id, (before, _) in FIXES.items() if before in current_text]
        if self.proposer_name == "llm_codex":
            eval_result = self.evaluate()
            catalog = {fix_id: f"Apply {fix_id}" for fix_id in (missing_fixes or ["fix_add"])}
            selected_fixes, llm_metadata = llm_proposer.select_fix_ids(
                root=self.root,
                scope_label=self.scope_label,
                source_text=current_text,
                eval_output=eval_result.output,
                fix_catalog=catalog,
                budget=self._fix_budget(),
                memory_summary="Bugfix demo has no reusable method memory." if self.llm_memory_enabled else None,
            )
        else:
            llm_metadata = {}
            selected_fixes = missing_fixes[: self._fix_budget()] if missing_fixes else ["fix_add"]
        return Proposal(
            summary=f"{self.proposer_name} bugfix proposal",
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "fix_ids": selected_fixes,
                **llm_metadata,
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
        if self.proposer_name != "llm_codex" or not self.llm_retry_enabled:
            return None
        if bool(rejected_proposal.metadata.get("fallback_used")):
            return None
        current_text = self.target_path.read_text(encoding="utf-8")
        tried = {str(fix_id) for fix_id in rejected_proposal.metadata.get("fix_ids", [])}
        missing_fixes = [fix_id for fix_id, (before, _) in FIXES.items() if before in current_text and fix_id not in tried]
        if not missing_fixes:
            return None
        return Proposal(
            summary=f"{self.proposer_name} bugfix retry proposal",
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "fix_ids": missing_fixes[: self._fix_budget()],
                "retry_attempt": 2,
            },
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        text = self.target_path.read_text(encoding="utf-8")
        applied: list[str] = []
        for fix_id in proposal.metadata.get("fix_ids", []):
            before, after = FIXES[fix_id]
            if before in text:
                text = text.replace(before, after, 1)
                applied.append(fix_id)
        self.target_path.write_text(text, encoding="utf-8")
        return Candidate(summary=proposal.summary, metadata={**proposal.metadata, "applied_fixes": applied, "mutation_summary": " | ".join(applied), "mutation_kind": ",".join(applied)})

    def evaluate(self) -> EvalResult:
        spec = importlib.util.spec_from_file_location("buggy_math_eval", self.target_path)
        if spec is None or spec.loader is None:
            return EvalResult(status="failed", score=float("-inf"), output="could not load target")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        passed = 0
        total = 6
        try:
            if module.add(2, 3) == 5:
                passed += 1
            if module.add(-2, 1) == -1:
                passed += 1
            if module.safe_div(8, 2) == 4:
                passed += 1
            try:
                module.safe_div(1, 0)
            except ZeroDivisionError:
                passed += 1
            if module.clamp(15, 0, 10) == 10:
                passed += 1
            if module.clamp(-3, 0, 10) == 0:
                passed += 1
        except Exception as exc:  # noqa: BLE001
            return EvalResult(status="failed", score=float(passed), output=str(exc))

        return EvalResult(status="ok", score=float(passed), output=f"SCORE={float(passed):.6f}")

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.status == "ok" and challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {"fix_ids": proposal.metadata.get("fix_ids", []), "applied_fixes": candidate.metadata.get("applied_fixes", [])}
