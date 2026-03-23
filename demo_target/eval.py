from __future__ import annotations

import math

from train import current_params


def hidden_objective(alpha: float, beta: float, gamma: float, delta: float) -> float:
    # This is intentionally smooth and noisy enough to make the loop interesting,
    # but still deterministic and cheap.
    penalty = 0.0
    penalty += 4.5 * (alpha - 1.75) ** 2
    penalty += 3.8 * (beta + 0.65) ** 2
    penalty += 2.2 * (gamma - 3.20) ** 2
    penalty += 5.0 * (delta - 0.85) ** 2
    interaction = math.sin(alpha * 2.3) + math.cos(gamma - beta) + 0.4 * math.sin(delta * 5.0)
    return 100.0 - penalty + interaction


def main() -> None:
    params = current_params()
    score = hidden_objective(
        params["ALPHA"],
        params["BETA"],
        params["GAMMA"],
        params["DELTA"],
    )
    print("PARAMS", params)
    print(f"SCORE={score:.6f}")


if __name__ == "__main__":
    main()
