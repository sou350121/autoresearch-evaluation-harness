from __future__ import annotations

import ast
import difflib
import random
from dataclasses import dataclass
from pathlib import Path

from .models import Chunk, MutationConfig


@dataclass
class MutationResult:
    original_text: str
    updated_text: str
    summary: str
    details: dict


def _binary_op_name(op: ast.operator) -> str:
    return type(op).__name__


def _binary_op_from_name(name: str) -> ast.operator:
    mapping = {
        "Add": ast.Add,
        "Sub": ast.Sub,
        "Mult": ast.Mult,
    }
    return mapping[name]()


def _weighted_count(kind: str, mutation_kind_weights: dict[str, float] | None) -> int:
    base = {
        "constant": 6,
        "math_func": 2,
        "binary_op": 1,
    }[kind]
    factor = 1.0
    if mutation_kind_weights is not None:
        factor = max(mutation_kind_weights.get(kind, 1.0), 0.1)
    return max(1, int(base * factor * 10))


def _in_chunk(node: ast.AST, chunk: Chunk | None) -> bool:
    if chunk is None:
        return True
    start_line = getattr(node, "lineno", None)
    end_line = getattr(node, "end_lineno", start_line)
    if start_line is None:
        return False
    if end_line is None:
        end_line = start_line
    return chunk.start_line <= start_line and end_line <= chunk.end_line


def mutate_target_file(
    target_file: Path,
    mutation: MutationConfig,
    iteration: int,
    chunk: Chunk | None = None,
    mutation_kind_weights: dict[str, float] | None = None,
) -> MutationResult:
    if mutation.mode != "python_ast_patch":
        raise RuntimeError(f"Unsupported mutation mode: {mutation.mode}")

    original = target_file.read_text(encoding="utf-8")
    tree = ast.parse(original)
    rng = random.Random(mutation.random_seed + iteration)

    constant_candidates: list[ast.Constant] = []
    call_candidates: list[ast.Call] = []
    op_candidates: list[ast.BinOp] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool) and _in_chunk(node, chunk):
            constant_candidates.append(node)
        elif isinstance(node, ast.Call) and _in_chunk(node, chunk):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "math":
                if func.attr in mutation.allowed_math_funcs:
                    call_candidates.append(node)
        elif isinstance(node, ast.BinOp) and _in_chunk(node, chunk):
            if _binary_op_name(node.op) in mutation.allowed_binary_ops:
                op_candidates.append(node)

    choices: list[tuple[str, int]] = []
    if constant_candidates:
        choices.append(("constant", len(constant_candidates)))
    if call_candidates:
        choices.append(("math_func", len(call_candidates)))
    if op_candidates:
        choices.append(("binary_op", len(op_candidates)))
    if not choices:
        raise RuntimeError("No AST mutation candidates found in target file.")

    weighted_kinds: list[str] = []
    if constant_candidates:
        weighted_kinds.extend(["constant"] * _weighted_count("constant", mutation_kind_weights))
    if call_candidates:
        weighted_kinds.extend(["math_func"] * _weighted_count("math_func", mutation_kind_weights))
    if op_candidates:
        weighted_kinds.extend(["binary_op"] * _weighted_count("binary_op", mutation_kind_weights))
    mutation_kind = rng.choice(weighted_kinds)

    if mutation_kind == "constant":
        node = constant_candidates[rng.randrange(len(constant_candidates))]
        before = float(node.value)
        delta = rng.uniform(-mutation.max_constant_delta, mutation.max_constant_delta)
        after = round(before + delta, 6)
        node.value = after
        summary = f"constant patch: {before:.6f} -> {after:.6f}"
        details = {"kind": mutation_kind, "before": before, "after": after, "delta": delta}
    elif mutation_kind == "math_func":
        node = call_candidates[rng.randrange(len(call_candidates))]
        func = node.func
        assert isinstance(func, ast.Attribute)
        before = func.attr
        alternatives = [name for name in mutation.allowed_math_funcs if name != before]
        after = rng.choice(alternatives)
        func.attr = after
        summary = f"math func patch: {before} -> {after}"
        details = {"kind": mutation_kind, "before": before, "after": after}
    else:
        node = op_candidates[rng.randrange(len(op_candidates))]
        before = _binary_op_name(node.op)
        alternatives = [name for name in mutation.allowed_binary_ops if name != before]
        after = rng.choice(alternatives)
        node.op = _binary_op_from_name(after)
        summary = f"binary op patch: {before} -> {after}"
        details = {"kind": mutation_kind, "before": before, "after": after}

    ast.fix_missing_locations(tree)
    updated = ast.unparse(tree) + "\n"
    target_file.write_text(updated, encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile="before",
            tofile="after",
        )
    )
    details["diff"] = diff
    if chunk is not None:
        details["chunk_id"] = chunk.chunk_id
        details["chunk_span"] = f"{chunk.start_line}-{chunk.end_line}"
    return MutationResult(
        original_text=original,
        updated_text=updated,
        summary=summary,
        details=details,
    )
