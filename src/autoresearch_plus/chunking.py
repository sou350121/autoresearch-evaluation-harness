from __future__ import annotations

import ast
import random
from typing import Iterable

from .models import Chunk


def derive_chunks(source: str) -> list[Chunk]:
    tree = ast.parse(source)
    function = next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)
    if function is None:
        return []

    chunks: list[Chunk] = []
    for node in function.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        start_line = getattr(node, "lineno", 0)
        end_line = getattr(node, "end_lineno", start_line)
        chunk_id = f"assign:{target.id}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                focus_region=chunk_id,
                start_line=start_line,
                end_line=end_line,
            )
        )
    return chunks


def choose_chunk(chunks: Iterable[Chunk], chunk_weights: dict[str, float], rng: random.Random) -> tuple[Chunk, float]:
    available = list(chunks)
    if not available:
        raise RuntimeError("No chunks available for selection.")

    weights = [max(chunk_weights.get(chunk.chunk_id, 1.0), 1e-6) for chunk in available]
    selected = rng.choices(available, weights=weights, k=1)[0]
    return selected, chunk_weights.get(selected.chunk_id, 1.0)
