from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .models import ProjectConfig


class EvaluationError(RuntimeError):
    pass


def run_evaluation(config: ProjectConfig) -> tuple[float, str]:
    result = subprocess.run(
        config.evaluation_command,
        cwd=config.root,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode != 0:
        raise EvaluationError(combined.strip())

    match = re.search(config.score_pattern, combined)
    if not match:
        raise EvaluationError(f"Could not parse score from output:\n{combined}")
    return float(match.group("score")), combined.strip()
