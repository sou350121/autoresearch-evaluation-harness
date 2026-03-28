from __future__ import annotations

import random
from pathlib import Path

from . import llm_proposer
from .adapter import TaskAdapter
from .models import AcceptedState, Candidate, EvalResult, Proposal

PROMPT_FRAGMENTS = [
    "- Return valid JSON only.",
    "- Use one label from: billing, technical, refund, other.",
    "- If confidence is below 0.6, use other.",
    "- Do not explain your reasoning.",
    "- Include fields: label, confidence, rationale.",
    "- Confidence must be between 0.0 and 1.0.",
    "- Prefer refund when the user explicitly asks for money back.",
    "- Prefer technical when the user cannot complete a workflow.",
    "- Prefer billing when the issue is about charges or invoices.",
    "- If the ticket mixes categories, pick the user-blocking issue first.",
    "- Never invent labels outside the allowed set.",
    "- Keep rationale under 12 words.",
    "- Example: {\"label\":\"refund\",\"confidence\":0.92,\"rationale\":\"Explicit refund request\"}",
    "- Example: {\"label\":\"technical\",\"confidence\":0.88,\"rationale\":\"Checkout flow blocked\"}",
    "- Reject answers that are not valid JSON.",
    "- When evidence is weak, lower confidence rather than guessing.",
]


class PromptDemoAdapter(TaskAdapter):
    name = "prompt_demo"

    def __init__(
        self,
        root: Path,
        prompt_path: Path | None = None,
        proposer_name: str = "chunked_prior",
        *,
        max_fix_budget: int | None = None,
        llm_memory_enabled: bool = True,
        llm_retry_enabled: bool = True,
    ) -> None:
        self.root = root
        self.prompt_path = prompt_path or (root / "demo_prompt" / "prompt.md")
        self.proposer_name = proposer_name
        self.max_fix_budget = max_fix_budget
        self.llm_memory_enabled = llm_memory_enabled
        self.llm_retry_enabled = llm_retry_enabled

    def _fragment_budget(self) -> int:
        if self.max_fix_budget is not None:
            return self.max_fix_budget
        return 2 if self.proposer_name == "chunked_prior" else 1

    def _fragment_catalog(self, current_text: str) -> tuple[dict[str, str], dict[str, str]]:
        fix_to_fragment: dict[str, str] = {}
        catalog: dict[str, str] = {}
        for index, fragment in enumerate(PROMPT_FRAGMENTS, start=1):
            if fragment in current_text:
                continue
            fix_id = f"fragment_{index:02d}"
            fix_to_fragment[fix_id] = fragment
            catalog[fix_id] = fragment
        return fix_to_fragment, catalog

    @property
    def edit_scope(self) -> list[Path]:
        return [self.prompt_path]

    @property
    def scope_label(self) -> str:
        return str(self.prompt_path.relative_to(self.root))

    def load_accepted_state(self) -> AcceptedState:
        return AcceptedState(files={self.scope_label.replace("/", "\\"): self.prompt_path.read_text(encoding="utf-8")}, label=self.scope_label)

    def restore(self, accepted: AcceptedState) -> None:
        content = next(iter(accepted.files.values()))
        self.prompt_path.write_text(content, encoding="utf-8")

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        rng = random.Random(revision * 31)
        current_text = self.prompt_path.read_text(encoding="utf-8")
        fix_to_fragment, catalog = self._fragment_catalog(current_text)
        fragment_budget = self._fragment_budget()
        if self.proposer_name == "llm_codex":
            eval_result = self.evaluate()
            selected_fix_ids, llm_metadata = llm_proposer.select_fix_ids(
                root=self.root,
                scope_label=self.scope_label,
                source_text=current_text,
                eval_output=eval_result.output,
                fix_catalog=catalog or {"fragment_01": PROMPT_FRAGMENTS[0]},
                budget=fragment_budget,
                memory_summary="Prompt task has no reusable method memory." if self.llm_memory_enabled else None,
            )
            candidate_lines = [fix_to_fragment[fix_id] for fix_id in selected_fix_ids if fix_id in fix_to_fragment]
        else:
            llm_metadata = {}
            missing = [fragment for fragment in PROMPT_FRAGMENTS if fragment not in current_text]
            candidate_lines = missing[:fragment_budget]
        if not candidate_lines:
            candidate_lines = [rng.choice(PROMPT_FRAGMENTS)]
        return Proposal(
            summary=f"{self.proposer_name} prompt proposal",
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "section_id": "instructions",
                "candidate_lines": candidate_lines,
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
        current_text = self.prompt_path.read_text(encoding="utf-8")
        tried = {str(item) for item in rejected_proposal.metadata.get("candidate_lines", [])}
        remaining = [fragment for fragment in PROMPT_FRAGMENTS if fragment not in current_text and fragment not in tried]
        if not remaining:
            return None
        return Proposal(
            summary=f"{self.proposer_name} prompt retry proposal",
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "section_id": "instructions",
                "candidate_lines": remaining[: self._fragment_budget()],
                "retry_attempt": 2,
            },
        )

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate:
        text = self.prompt_path.read_text(encoding="utf-8")
        insertion = "\n".join(str(line) for line in proposal.metadata.get("candidate_lines", []))
        if "## Instructions" in text:
            text = text.replace("## Instructions", f"## Instructions\n{insertion}", 1)
        else:
            text = text + f"\n## Instructions\n{insertion}\n"
        self.prompt_path.write_text(text, encoding="utf-8")
        return Candidate(summary=proposal.summary, metadata=proposal.metadata)

    def evaluate(self) -> EvalResult:
        text = self.prompt_path.read_text(encoding="utf-8")
        score = 84.0 + float(sum(1 for fragment in PROMPT_FRAGMENTS if fragment in text))
        return EvalResult(status="ok", score=score, output=f"SCORE={score:.6f}")

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool:
        return challenger.score > incumbent.score

    def promote(self, candidate: Candidate) -> AcceptedState:
        return self.load_accepted_state()

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict:
        return {"section_id": proposal.metadata.get("section_id", ""), "candidate_lines": proposal.metadata.get("candidate_lines", [])}
