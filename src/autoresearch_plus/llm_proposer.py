from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from shutil import which


def parse_fix_selection(text: str, allowed_fix_ids: set[str], budget: int) -> list[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(text[start : end + 1])

    selected: list[str] = []
    for fix_id in payload.get("selected_fix_ids", []):
        if not isinstance(fix_id, str):
            continue
        if fix_id not in allowed_fix_ids:
            continue
        if fix_id in selected:
            continue
        selected.append(fix_id)
        if len(selected) >= budget:
            break
    return selected


def _build_codex_command(*, codex_binary: str, cwd: Path, schema_path: Path, output_path: Path) -> list[str]:
    return [
        codex_binary,
        "exec",
        "-m",
        "gpt-5.4",
        "--ephemeral",
        "-s",
        "danger-full-access",
        "--skip-git-repo-check",
        "-C",
        str(cwd),
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        "-",
    ]


def _default_runner(*, prompt: str, cwd: Path) -> str:
    codex_binary = which("codex.cmd") or which("codex") or str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as schema_handle:
        schema_path = Path(schema_handle.name)
        schema_handle.write(
            json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "selected_fix_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "summary": {"type": "string"},
                    },
                    "required": ["selected_fix_ids", "summary"],
                    "additionalProperties": False,
                }
            )
        )
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as output_handle:
        output_path = Path(output_handle.name)
    try:
        result = subprocess.run(
            _build_codex_command(
                codex_binary=codex_binary,
                cwd=cwd,
                schema_path=schema_path,
                output_path=output_path,
            ),
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if output_path.exists():
            response = output_path.read_text(encoding="utf-8").strip()
            if response:
                return response
        return (result.stdout or result.stderr or "").strip()
    finally:
        schema_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def select_fix_ids(
    *,
    root: Path,
    scope_label: str,
    source_text: str,
    eval_output: str,
    fix_catalog: dict[str, str],
    budget: int,
    memory_summary: str | None = None,
    runner=None,
) -> tuple[list[str], dict]:
    ordered_fix_ids = list(fix_catalog.keys())
    fallback = ordered_fix_ids[:budget]
    prompt = "\n".join(
        [
            "You are choosing fix ids for a small verified repair loop.",
            "Return JSON only with shape: {\"selected_fix_ids\": [\"fix_id\"], \"summary\": \"...\"}.",
            f"Scope: {scope_label}",
            f"Budget: {budget}",
        ]
        + (
            [
                "Recent method memory:",
                memory_summary,
            ]
            if memory_summary
            else []
        )
        + [
            "Allowed fix ids and summaries:",
            json.dumps(fix_catalog, ensure_ascii=False, indent=2),
            "Current file:",
            source_text,
            "Current failing evaluation output:",
            eval_output,
            "Choose the smallest set of fix ids most likely to improve the score.",
        ]
    )
    run = runner or _default_runner
    raw_response = ""
    try:
        raw_response = run(prompt=prompt, cwd=root)
        selected = parse_fix_selection(raw_response, set(ordered_fix_ids), budget)
        if selected:
            return selected, {
                "provider": "llm_codex",
                "fallback_used": False,
                "raw_response": raw_response,
            }
    except Exception:
        pass
    return fallback, {
        "provider": "llm_codex",
        "fallback_used": True,
        "raw_response": raw_response,
    }
