"""
Single editable target file for the local demo.

The search loop mutates real Python code in this file through AST patches.
"""

from __future__ import annotations

import math


def predict(x: float, y: float) -> float:
    base = 1.10 * x + 0.35 * y
    wave = math.sin(x * 0.70) + 0.60 * math.cos(y * 1.40)
    shape = 0.12 * x * y - 0.15 * x * x + 0.05 * y * y
    bias = 0.40
    return base + wave + shape + bias
