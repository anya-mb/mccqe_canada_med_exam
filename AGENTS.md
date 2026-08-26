## Scope-scaling execution

- `AGENTS.md` is the canonical agent instruction file.
- Follow `docs/scope-chapter-workflow.md` for chapter scope mapping.
- Resume from `reports/scope_scaling_progress.json`.
- Process exactly one chapter per task unless the user explicitly says otherwise.
- Use `.venv/bin/python` for all project Python commands and tests.
- Use the compact packet produced by `scripts.qbank prepare-scope-chapter`.
- Do not preload the complete Toronto Notes corpus or MCC registry.
- Use targeted source/registry retrieval only when needed.
- Never infer Toronto Notes structure from medical knowledge.
- Never fabricate MCC objective mappings.
- Deterministic validation belongs in Python; semantic decisions belong to the model.
- Do not generate clinical questions during scope scaling.
- Do not finalize global ownership during chapter mapping.
- Do not call external LLM APIs from project code.
- Do not commit unless the current user task explicitly authorizes a commit.
- When authorized, keep the chapter commit separate from the ledger-hash follow-up commit.
- Stop after the requested chapter.