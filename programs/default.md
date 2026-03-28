# Default Program

Operate like a tight experiment loop.

- Edit only the configured target file through small, reviewable code patches.
- Change as little as possible per run.
- Use the scalar score as the primary decision signal.
- Compare only against the previous accepted revision.
- Keep a failed run if it teaches something, but never keep its file changes.
- Prefer improvements that are simple and repeatable over clever changes that are hard to explain.
- If a run crashes, restore the accepted target file and log the failure.
