from __future__ import annotations


def add(a: int, b: int) -> int:
    return a - b


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return min(low, min(value, high))
