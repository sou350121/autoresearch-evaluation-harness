from __future__ import annotations

import unittest

from renderer import create_new_format_tool_call_html, render_markdown


class RendererTests(unittest.TestCase):
    def test_render_markdown_keeps_placeholder_wrapper_but_escapes_user_fields(self) -> None:
        html = render_markdown(
            """
<use_mcp_tool>
  <server_name>tool-<script>alert(1)</script></server_name>
  <tool_name>google_search</tool_name>
  <arguments>{"query":"<img src=x onerror=alert(1)>"}</arguments>
</use_mcp_tool>
"""
        )

        self.assertIn('<div class="mcp-tool-call">', html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn('<img src=x onerror=alert(1)>', html)

    def test_create_new_format_tool_call_html_escapes_server_tool_and_arguments(self) -> None:
        html = create_new_format_tool_call_html(
            {
                "server_name": 'tool-<svg onload=alert(1)>',
                "tool_name": "<b>answer</b>",
                "arguments": '{"question":"<iframe src=x></iframe>"}',
            }
        )

        self.assertIn("&lt;svg onload=alert(1)&gt;", html)
        self.assertIn("&lt;b&gt;answer&lt;/b&gt;", html)
        self.assertIn("&lt;iframe src=x&gt;&lt;/iframe&gt;", html)
        self.assertNotIn("<svg onload=alert(1)>", html)
        self.assertNotIn("<b>answer</b>", html)
        self.assertNotIn("<iframe src=x></iframe>", html)

    def test_render_markdown_escapes_regular_text_outside_placeholders(self) -> None:
        html = render_markdown('hello <strong>world</strong>')
        self.assertEqual("hello &lt;strong&gt;world&lt;/strong&gt;", html)


if __name__ == "__main__":
    unittest.main()
