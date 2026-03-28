from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

from . import llm_proposer
from .adapter import TaskAdapter
from .models import AcceptedState, Candidate, EvalResult, Proposal


FIXES = {
    "escape_user_fields_in_html_renderers": (
        """import json
import re
""",
        """import html
import json
import re
""",
    ),
}

FIX_SUMMARIES = {
    "escape_user_fields_in_html_renderers": "Escape user-controlled server names, tool names, and arguments before interpolating them into MCP and new-format tool-call HTML.",
}


class MiroTraceHtmlEscapeAdapter(TaskAdapter):
    name = "miro_trace_html_escape_demo"

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
        self.demo_root = root / "demo_miro_trace_html_escape"
        self.target_path = target_path or (self.demo_root / "renderer.py")
        self.proposer_name = proposer_name
        self.max_fix_budget = max_fix_budget
        self.llm_memory_enabled = llm_memory_enabled
        self.llm_retry_enabled = llm_retry_enabled

    def _fix_budget(self) -> int:
        return self.max_fix_budget if self.max_fix_budget is not None else 1

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

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        current_text = self.target_path.read_text(encoding="utf-8")
        missing = [fix_id for fix_id, (before, _) in FIXES.items() if before in current_text]
        if self.proposer_name == "llm_codex":
            eval_result = self.evaluate()
            catalog = {fix_id: FIX_SUMMARIES[fix_id] for fix_id in missing or ["escape_user_fields_in_html_renderers"]}
            selected, llm_metadata = llm_proposer.select_fix_ids(
                root=self.root,
                scope_label=self.scope_label,
                source_text=current_text,
                eval_output=eval_result.output,
                fix_catalog=catalog,
                budget=self._fix_budget(),
                memory_summary="HTML escape demo has no reusable method memory." if self.llm_memory_enabled else None,
            )
        else:
            llm_metadata = {}
            selected = missing[: self._fix_budget()] if missing else ["escape_user_fields_in_html_renderers"]
        return Proposal(
            summary=f"{self.proposer_name} miro trace html escape proposal",
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
        if bool(rejected_proposal.metadata.get("fallback_used")):
            return None
        current_text = self.target_path.read_text(encoding="utf-8")
        tried = {str(fix_id) for fix_id in rejected_proposal.metadata.get("fix_ids", [])}
        missing = [fix_id for fix_id, (before, _) in FIXES.items() if before in current_text and fix_id not in tried]
        if not missing:
            return None
        return Proposal(
            summary=f"{self.proposer_name} miro trace html escape retry proposal",
            scope_label=self.scope_label,
            metadata={"proposal_kind": self.proposer_name, "fix_ids": missing[: self._fix_budget()], "retry_attempt": 2},
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        text = self.target_path.read_text(encoding="utf-8")
        applied: list[str] = []
        for fix_id in proposal.metadata.get("fix_ids", []):
            before, after = FIXES[fix_id]
            if before in text:
                text = text.replace(before, after, 1)
                text = text.replace("{server_name}.{tool_name}", "{html.escape(server_name)}.{html.escape(tool_name)}")
                text = text.replace("{formatted_args}</div>", "{html.escape(formatted_args)}</div>")
                text = text.replace("{tool['server_name']}.{tool['tool_name']}", "{html.escape(str(tool['server_name']))}.{html.escape(str(tool['tool_name']))}")
                text = text.replace("{formatted_args}</div>", "{html.escape(formatted_args)}</div>")
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
        sys.modules.pop("renderer", None)
        sys.modules.pop("test_renderer", None)
        sys.path.insert(0, str(self.demo_root))
        try:
            suite = unittest.defaultTestLoader.discover(str(self.demo_root), pattern="test_*.py")
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
            passed = result.testsRun - len(result.failures) - len(result.errors)
            status = "ok" if not result.errors else "failed"
            return EvalResult(status=status, score=float(passed), output=stream.getvalue())
        finally:
            if str(self.demo_root) in sys.path:
                sys.path.remove(str(self.demo_root))

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.status == "ok" and challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {
            "fix_ids": proposal.metadata.get("fix_ids", []),
            "applied_fixes": candidate.metadata.get("applied_fixes", []),
        }
