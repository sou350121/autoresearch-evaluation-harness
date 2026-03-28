from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path


def main() -> None:
    demo_root = Path(__file__).resolve().parent
    sys.modules.pop("trace_analyzer", None)
    sys.modules.pop("test_trace_analyzer", None)
    sys.path.insert(0, str(demo_root))
    suite = unittest.defaultTestLoader.discover(str(demo_root), pattern="test_*.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"SCORE={float(passed):.6f}")


if __name__ == "__main__":
    main()
