from __future__ import annotations

import unittest

from trace_analyzer import TraceAnalyzer


class TraceAnalyzerTests(unittest.TestCase):
    def test_parse_new_format_tool_name_handles_hyphenated_server_names(self) -> None:
        analyzer = TraceAnalyzer({})

        self.assertEqual(
            analyzer._parse_new_format_tool_name("tool-google-search-google_search"),
            ("tool-google-search", "google_search"),
        )
        self.assertEqual(
            analyzer._parse_new_format_tool_name("agent-browsing-search_and_browse"),
            ("agent-browsing", "search_and_browse"),
        )

    def test_execution_summary_keeps_hyphenated_tool_usage_key(self) -> None:
        payload = {
            "main_agent_message_history": {
                "message_history": [
                    {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "tool-google-search-google_search",
                                }
                            },
                            {
                                "function": {
                                    "name": "agent-browsing-search_and_browse",
                                }
                            },
                        ]
                    }
                ]
            }
        }

        summary = TraceAnalyzer(payload).get_execution_summary()

        self.assertEqual(2, summary["total_tool_calls"])
        self.assertEqual(1, summary["tool_usage_distribution"]["tool-google-search.google_search"])
        self.assertEqual(1, summary["tool_usage_distribution"]["agent-browsing.search_and_browse"])

    def test_analyze_conversation_flow_keeps_multiple_mcp_tool_calls(self) -> None:
        payload = {
            "main_agent_message_history": {
                "message_history": [
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": """
<use_mcp_tool>
  <server_name>tool-google-search</server_name>
  <tool_name>google_search</tool_name>
  <arguments>{"query": "alpha"}</arguments>
</use_mcp_tool>
<use_mcp_tool>
  <server_name>tool-vqa-os</server_name>
  <tool_name>answer_question</tool_name>
  <arguments>{"question": "beta"}</arguments>
</use_mcp_tool>
""",
                            }
                        ]
                    }
                ]
            }
        }

        flow = TraceAnalyzer(payload).analyze_conversation_flow()

        self.assertEqual(2, len(flow[0]["tool_calls"]))
        self.assertEqual(
            [
                (tool["server_name"], tool["tool_name"])
                for tool in flow[0]["tool_calls"]
            ],
            [
                ("tool-google-search", "google_search"),
                ("tool-vqa-os", "answer_question"),
            ],
        )

    def test_analyze_conversation_flow_keeps_multiple_browser_sessions(self) -> None:
        payload = {
            "main_agent_message_history": {
                "message_history": [
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": """
<use_mcp_tool>
  <server_name>agent-browsing</server_name>
  <tool_name>search_and_browse</tool_name>
  <arguments>{"query": "alpha"}</arguments>
</use_mcp_tool>
<use_mcp_tool>
  <server_name>agent-browsing</server_name>
  <tool_name>search_and_browse</tool_name>
  <arguments>{"query": "beta"}</arguments>
</use_mcp_tool>
""",
                            }
                        ]
                    }
                ]
            },
            "sub_agent_message_history_sessions": {
                "agent-browsing_1": {
                    "message_history": [
                        {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "tool-google-search-google_search",
                                    }
                                }
                            ]
                        }
                    ]
                },
                "agent-browsing_2": {
                    "message_history": [
                        {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "tool-vqa-os-answer_question",
                                    }
                                }
                            ]
                        }
                    ]
                },
            },
        }

        flow = TraceAnalyzer(payload).analyze_conversation_flow()

        self.assertEqual(["agent-browsing_1", "agent-browsing_2"], flow[0]["browser_sessions"])
        self.assertEqual(2, len(flow[0]["browser_flows"]))
        self.assertEqual(
            [item["server_name"] for item in flow[0]["browser_flows"][0][0]["tool_calls"]],
            ["tool-google-search"],
        )
        self.assertEqual(
            [item["server_name"] for item in flow[0]["browser_flows"][1][0]["tool_calls"]],
            ["tool-vqa-os"],
        )


if __name__ == "__main__":
    unittest.main()
