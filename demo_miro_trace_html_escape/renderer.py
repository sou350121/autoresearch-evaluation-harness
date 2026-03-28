from __future__ import annotations

import json
import re


def format_mcp_tool_call_with_placeholders(text: str, placeholders: dict[str, str]) -> str:
    if not text or not isinstance(text, str):
        return text

    pattern = r"<use_mcp_tool>\s*<server_name>(.*?)</server_name>\s*<tool_name>(.*?)</tool_name>\s*<arguments>\s*(.*?)\s*</arguments>\s*</use_mcp_tool>"
    placeholder_counter = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal placeholder_counter
        server_name = match.group(1).strip()
        tool_name = match.group(2).strip()
        raw_args = match.group(3).strip()
        try:
            formatted_args = json.dumps(json.loads(raw_args), indent=2)
        except json.JSONDecodeError:
            formatted_args = raw_args

        mcp_html = f"""<div class="mcp-tool-call">
    <div class="mcp-tool-header">
        <span class="mcp-tool-name">{server_name}.{tool_name}</span>
    </div>
    <div class="mcp-tool-content">
        <div class="xml-arguments">{formatted_args}</div>
    </div>
</div>"""
        placeholder_id = f"MCP_PLACEHOLDER_{placeholder_counter}"
        placeholder_counter += 1
        placeholders[placeholder_id] = mcp_html
        return f"[{placeholder_id}]"

    return re.sub(pattern, replace, text, flags=re.DOTALL)


def create_new_format_tool_call_html(tool: dict[str, object]) -> str:
    formatted_args = tool.get("arguments")
    if not isinstance(formatted_args, str):
        formatted_args = json.dumps(formatted_args, indent=2)
    return f"""<div class="mcp-tool-call">
    <div class="mcp-tool-header">
        <span class="mcp-tool-name">{tool['server_name']}.{tool['tool_name']}</span>
    </div>
    <div class="mcp-tool-content">
        <div class="xml-arguments">{formatted_args}</div>
    </div>
</div>"""


def render_markdown(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    html = text
    placeholders: dict[str, str] = {}
    html = format_mcp_tool_call_with_placeholders(html, placeholders)
    html = (
        html.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
    html = html.replace("\n", "<br>")
    for placeholder_id, html_content in placeholders.items():
        html = html.replace(f"[{placeholder_id}]", html_content)
    return html
