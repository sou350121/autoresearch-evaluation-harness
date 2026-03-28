from __future__ import annotations

import math

from train import predict


def hidden_target(x: float, y: float) -> float:
    base = 1.46 * x + 0.52 * y
    wave = math.sin(x * 0.86) + 0.72 * math.cos(y * 1.18)
    shape = 0.20 * x * y - 0.10 * x * x + 0.08 * y * y
    bias = 0.18
    return base + wave + shape + bias


def dataset() -> list[tuple[float, float]]:
    return [(x / 3.0, y / 4.0) for x in range(-6, 7) for y in range(-6, 7)]


def main() -> None:
    points = dataset()
    mse = sum((predict(x, y) - hidden_target(x, y)) ** 2 for x, y in points) / len(points)
    score = 100.0 - mse
    print(f"SCORE={score:.6f}")


if __name__ == "__main__":
    main()
