from __future__ import annotations

from typing import Any


class TraceAnalyzer:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    def _parse_new_format_tool_name(self, tool_name: str) -> tuple[str, str]:
        if tool_name.startswith("agent-browsing-"):
            server_name = "agent-browsing"
            actual_tool_name = tool_name[len("agent-browsing-") :]
            return server_name, actual_tool_name
        elif tool_name.startswith("tool-"):
            parts = tool_name.split("-", 2)
            if len(parts) >= 3:
                server_name = parts[1]
                actual_tool_name = parts[2]
            else:
                server_name = "unknown"
                actual_tool_name = tool_name
            return server_name, actual_tool_name
        else:
            return "unknown", tool_name

    def get_main_agent_messages(self) -> list[dict[str, Any]]:
        history = self.data.get("main_agent_message_history", {})
        return list(history.get("message_history", []))

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
            flow_steps.append(step)
        return flow_steps

    def get_execution_summary(self) -> dict[str, Any]:
        flow_steps = self.analyze_conversation_flow()
        tool_usage: dict[str, int] = {}
        tool_calls = []

        for step in flow_steps:
            tool_calls.extend(step["tool_calls"])

        for tool in tool_calls:
            if tool.get("server_name") != "unknown":
                key = f"{tool['server_name']}.{tool['tool_name']}"
            else:
                key = tool["tool_name"]
            tool_usage[key] = tool_usage.get(key, 0) + 1

        return {
            "total_tool_calls": len(tool_calls),
            "tool_usage_distribution": tool_usage,
        }
