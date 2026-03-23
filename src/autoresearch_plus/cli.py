from __future__ import annotations

import argparse
from pathlib import Path

from .ledger import RunLedger
from .loop import run_baseline, run_search


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_baseline() -> None:
    record = run_baseline(_repo_root())
    print(f"Accepted baseline revision {record.revision} with score {record.score:.6f}")


def cmd_search(iterations: int) -> None:
    records = run_search(_repo_root(), iterations)
    for record in records:
        print(
            f"revision={record.revision} decision={record.decision} "
            f"score={record.score:.6f} mutation={record.mutation}"
        )


def cmd_report() -> None:
    ledger = RunLedger(_repo_root())
    best = ledger.best_accepted()
    if not best:
        print("No accepted runs yet.")
        return
    print(
        "best_accepted "
        f"revision={best['revision']} "
        f"score={best['score']} "
        f"summary={best['summary']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="autoresearch-plus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("baseline")

    search = subparsers.add_parser("search")
    search.add_argument("--iterations", type=int, default=5)

    subparsers.add_parser("report")

    args = parser.parse_args()
    if args.command == "baseline":
        cmd_baseline()
    elif args.command == "search":
        cmd_search(args.iterations)
    elif args.command == "report":
        cmd_report()


if __name__ == "__main__":
    main()
