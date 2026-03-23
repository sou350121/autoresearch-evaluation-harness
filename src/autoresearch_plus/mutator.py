from __future__ import annotations

import random
import re
from pathlib import Path

from .models import MutationConfig


ASSIGNMENT_RE = re.compile(r"^(?P<name>[A-Z_]+)\s*=\s*(?P<value>-?\d+(?:\.\d+)?)\s*$", re.MULTILINE)


def mutate_target_file(target_file: Path, mutation: MutationConfig, iteration: int) -> tuple[str, str, str]:
    rng = random.Random(mutation.random_seed + iteration)
    original = target_file.read_text(encoding="utf-8")
    values: dict[str, float] = {}

    for match in ASSIGNMENT_RE.finditer(original):
        name = match.group("name")
        if name in mutation.constant_names:
            values[name] = float(match.group("value"))

    if not values:
        raise RuntimeError("No mutable constants found in target file.")

    name = mutation.constant_names[iteration % len(mutation.constant_names)]
    if name not in values:
        name = sorted(values)[0]

    delta = rng.uniform(-mutation.step_scale, mutation.step_scale)
    new_value = values[name] + delta
    replacement = f"{name} = {new_value:.6f}"
    updated = re.sub(rf"^{name}\s*=\s*-?\d+(?:\.\d+)?\s*$", replacement, original, flags=re.MULTILINE)
    target_file.write_text(updated, encoding="utf-8")
    mutation_summary = f"{name} += {delta:.6f}"
    return original, updated, mutation_summary
