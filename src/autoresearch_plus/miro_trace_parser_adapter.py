from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

from . import llm_proposer
from .adapter import TaskAdapter
from .models import AcceptedState, Candidate, EvalResult, Proposal


FIXES = {
    "fix_hyphenated_tool_server_name": (
        '            parts = tool_name.split("-", 2)\n'
        "            if len(parts) >= 3:\n"
        "                server_name = parts[1]\n"
        "                actual_tool_name = parts[2]\n",
        '            if "-" in tool_name:\n'
        '                server_name, actual_tool_name = tool_name.rsplit("-", maxsplit=1)\n',
    ),
    "fix_multiple_mcp_tool_calls": (
        """    def analyze_conversation_flow(self) -> list[dict[str, Any]]:
        flow_steps: list[dict[str, Any]] = []
        for index, message in enumerate(self.get_main_agent_messages()):
            step = {
                "step_id": index,
                "tool_calls": [],
            }
            for tool_call in message.get("tool_calls", []):
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                server_name, actual_tool_name = self._parse_new_format_tool_name(tool_name)
                step["tool_calls"].append(
                    {
                        "server_name": server_name,
                        "tool_name": actual_tool_name,
                        "format": "new",
                    }
                )
            flow_steps.append(step)
        return flow_steps
""",
        """    def extract_text_content(self, content: Any) -> str:
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
        return str(content)

    def parse_mcp_tool_calls(self, text: str) -> list[dict[str, Any]]:
        import json
        import re

        pattern = r"<use_mcp_tool>\\s*<server_name>(.*?)</server_name>\\s*<tool_name>(.*?)</tool_name>\\s*<arguments>\\s*(.*?)\\s*</arguments>\\s*</use_mcp_tool>"
        tool_calls: list[dict[str, Any]] = []
        for match in re.finditer(pattern, text, re.DOTALL):
            arguments_text = match.group(3).strip()
            try:
                arguments = json.loads(arguments_text)
            except json.JSONDecodeError:
                arguments = arguments_text
            tool_calls.append(
                {
                    "server_name": match.group(1).strip(),
                    "tool_name": match.group(2).strip(),
                    "arguments": arguments,
                }
            )
        return tool_calls

    def analyze_conversation_flow(self) -> list[dict[str, Any]]:
        flow_steps: list[dict[str, Any]] = []
        for index, message in enumerate(self.get_main_agent_messages()):
            step = {
                "step_id": index,
                "tool_calls": [],
            }
            for tool_call in message.get("tool_calls", []):
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                server_name, actual_tool_name = self._parse_new_format_tool_name(tool_name)
                step["tool_calls"].append(
                    {
                        "server_name": server_name,
                        "tool_name": actual_tool_name,
                        "format": "new",
                    }
                )
            text_content = self.extract_text_content(message.get("content", []))
            for tool_call in self.parse_mcp_tool_calls(text_content):
                step["tool_calls"].append({**tool_call, "format": "mcp"})
            flow_steps.append(step)
        return flow_steps
""",
    ),
    "fix_multiple_browser_sessions": (
        """    def analyze_conversation_flow(self) -> list[dict[str, Any]]:
        flow_steps: list[dict[str, Any]] = []
        for index, message in enumerate(self.get_main_agent_messages()):
            step = {
                "step_id": index,
                "tool_calls": [],
            }
            for tool_call in message.get("tool_calls", []):
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                server_name, actual_tool_name = self._parse_new_format_tool_name(tool_name)
                step["tool_calls"].append(
                    {
                        "server_name": server_name,
                        "tool_name": actual_tool_name,
                        "format": "new",
                    }
                )
            text_content = self.extract_text_content(message.get("content", []))
            for tool_call in self.parse_mcp_tool_calls(text_content):
                step["tool_calls"].append({**tool_call, "format": "mcp"})
            flow_steps.append(step)
        return flow_steps
""",
        """    def get_browser_agent_sessions(self) -> dict[str, Any]:
        sessions = self.data.get("browser_agent_message_history_sessions", {})
        if not sessions:
            sessions = self.data.get("sub_agent_message_history_sessions", {})
        return sessions

    def get_browser_agent_session_messages(self, session_id: str) -> list[dict[str, Any]]:
        session = self.get_browser_agent_sessions().get(session_id, {})
        return list(session.get("message_history", []))

    def analyze_browser_session_flow(self, session_id: str) -> list[dict[str, Any]]:
        browser_flow: list[dict[str, Any]] = []
        for index, message in enumerate(self.get_browser_agent_session_messages(session_id)):
            step = {
                "step_id": index,
                "tool_calls": [],
            }
            for tool_call in message.get("tool_calls", []):
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                server_name, actual_tool_name = self._parse_new_format_tool_name(tool_name)
                step["tool_calls"].append(
                    {
                        "server_name": server_name,
                        "tool_name": actual_tool_name,
                        "format": "new",
                    }
                )
            text_content = self.extract_text_content(message.get("content", []))
            for tool_call in self.parse_mcp_tool_calls(text_content):
                step["tool_calls"].append({**tool_call, "format": "mcp"})
            browser_flow.append(step)
        return browser_flow

    def analyze_conversation_flow(self) -> list[dict[str, Any]]:
        flow_steps: list[dict[str, Any]] = []
        browser_sessions = self.get_browser_agent_sessions()
        browser_call_count = 0
        for index, message in enumerate(self.get_main_agent_messages()):
            step = {
                "step_id": index,
                "tool_calls": [],
                "browser_sessions": [],
                "browser_flows": [],
            }
            for tool_call in message.get("tool_calls", []):
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                server_name, actual_tool_name = self._parse_new_format_tool_name(tool_name)
                parsed = {
                    "server_name": server_name,
                    "tool_name": actual_tool_name,
                    "format": "new",
                }
                step["tool_calls"].append(parsed)
                if server_name.startswith("agent-"):
                    browser_call_count += 1
                    session_id = f"{server_name}_{browser_call_count}"
                    step["browser_sessions"].append(session_id)
                    step["browser_flows"].append(
                        self.analyze_browser_session_flow(session_id) if session_id in browser_sessions else []
                    )
            text_content = self.extract_text_content(message.get("content", []))
            for tool_call in self.parse_mcp_tool_calls(text_content):
                parsed = {**tool_call, "format": "mcp"}
                step["tool_calls"].append(parsed)
                if tool_call["server_name"].startswith("agent-"):
                    browser_call_count += 1
                    session_id = f"{tool_call['server_name']}_{browser_call_count}"
                    step["browser_sessions"].append(session_id)
                    step["browser_flows"].append(
                        self.analyze_browser_session_flow(session_id) if session_id in browser_sessions else []
                    )
            flow_steps.append(step)
        return flow_steps
""",
    ),
}

FIX_SUMMARIES = {
    "fix_hyphenated_tool_server_name": "Normalize hyphenated tool server names so tool-google-search-google_search becomes tool-google-search + google_search.",
    "fix_multiple_mcp_tool_calls": "Preserve every MCP tool call from one assistant message instead of only the first parsed block.",
    "fix_multiple_browser_sessions": "Preserve every browser or sub-agent session linked from one assistant step instead of only the first session.",
}


class MiroTraceParserAdapter(TaskAdapter):
    name = "miro_trace_parser_demo"

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
        self.demo_root = root / "demo_miro_trace_parser"
        self.target_path = target_path or (self.demo_root / "trace_analyzer.py")
        self.proposer_name = proposer_name
        self.max_fix_budget = max_fix_budget
        self.llm_memory_enabled = llm_memory_enabled
        self.llm_retry_enabled = llm_retry_enabled

    def _fix_budget(self) -> int:
        if self.max_fix_budget is not None:
            return self.max_fix_budget
        return 3 if self.proposer_name == "chunked_prior" else 1

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
        missing: list[str] = []
        projected_text = current_text
        for fix_id, (before, after) in FIXES.items():
            if before in projected_text:
                missing.append(fix_id)
                projected_text = projected_text.replace(before, after, 1)
        return missing

    def propose(self, accepted: AcceptedState, history: list[dict[str, str]], revision: int) -> Proposal:
        current_text = self.target_path.read_text(encoding="utf-8")
        missing = self._available_fix_ids(current_text)
        if self.proposer_name == "llm_codex":
            eval_result = self.evaluate()
            catalog = {fix_id: FIX_SUMMARIES[fix_id] for fix_id in missing or ["fix_hyphenated_tool_server_name"]}
            selected, llm_metadata = llm_proposer.select_fix_ids(
                root=self.root,
                scope_label=self.scope_label,
                source_text=current_text,
                eval_output=eval_result.output,
                fix_catalog=catalog,
                budget=self._fix_budget(),
                memory_summary="Trace parser demo has no reusable method memory." if self.llm_memory_enabled else None,
            )
        else:
            llm_metadata = {}
            selected = missing[: self._fix_budget()] if missing else ["fix_hyphenated_tool_server_name"]
        return Proposal(
            summary=f"{self.proposer_name} miro trace parser proposal",
            scope_label=self.scope_label,
            metadata={
                "proposal_kind": self.proposer_name,
                "fix_ids": selected,
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
        remaining = [fix_id for fix_id in self._available_fix_ids(current_text) if fix_id not in tried]
        if not remaining:
            return None
        return Proposal(
            summary=f"{self.proposer_name} miro trace parser retry proposal",
            scope_label=self.scope_label,
            metadata={"proposal_kind": self.proposer_name, "fix_ids": remaining[: self._fix_budget()], "retry_attempt": 2},
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
        sys.modules.pop("trace_analyzer", None)
        sys.modules.pop("test_trace_analyzer", None)
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
