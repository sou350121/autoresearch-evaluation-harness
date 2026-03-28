from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> None:
    target = Path(__file__).resolve().parent / "buggy_math.py"
    spec = importlib.util.spec_from_file_location("buggy_math_eval", target)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load target")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    passed = 0
    if module.add(2, 3) == 5:
        passed += 1
    if module.add(-2, 1) == -1:
        passed += 1
    if module.safe_div(8, 2) == 4:
        passed += 1
    try:
        module.safe_div(1, 0)
    except ZeroDivisionError:
        passed += 1
    if module.clamp(15, 0, 10) == 10:
        passed += 1
    if module.clamp(-3, 0, 10) == 0:
        passed += 1
    print(f"SCORE={float(passed):.6f}")


if __name__ == "__main__":
    main()
