# Claude Code Repository Instructions

Before substantive work:

1. Read `AGENTS.md` and follow it as the canonical repository operating policy.
2. Read `MEMORY.md` for the current project checkpoint and resume state.
3. Canonical repository artifacts, validators, tests, and Git history override `MEMORY.md` if they disagree.
4. Do not duplicate changing project state in this file.
5. Use `.venv/bin/python` and `.venv/bin/python -m pytest` as the canonical Python/test runtime unless `AGENTS.md` explicitly says otherwise.
6. Preserve historical/frozen question-bank artifacts unless the task explicitly authorizes changing them.
7. After a successful canonical checkpoint, reconcile/update the changing resume-state section of `MEMORY.md` according to `AGENTS.md`.
8. Fail closed on unresolved medical evidence, provenance, or single-best-answer ambiguity.