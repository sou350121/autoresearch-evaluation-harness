from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import AcceptedState, Candidate, EvalResult, Proposal


class TaskAdapter(Protocol):
    name: str

    @property
    def edit_scope(self) -> list[Path]: ...

    @property
    def scope_label(self) -> str: ...

    def load_accepted_state(self) -> AcceptedState: ...

    def restore(self, accepted: AcceptedState) -> None: ...

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal: ...

    def retry_after_reject(
        self,
        accepted: AcceptedState,
        history: list[dict[str, str]],
        revision: int,
        rejected_proposal: Proposal,
        rejected_result: EvalResult,
    ) -> Proposal | None: ...

    def materialize(self, accepted: AcceptedState, proposal: Proposal) -> Candidate: ...

    def evaluate(self) -> EvalResult: ...

    def is_better(self, incumbent: EvalResult, challenger: EvalResult) -> bool: ...

    def promote(self, candidate: Candidate) -> AcceptedState: ...

    def trace_metadata(self, proposal: Proposal, candidate: Candidate) -> dict: ...
