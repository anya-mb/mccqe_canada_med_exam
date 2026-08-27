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

## MCC scope-scaling workflow

For chapter scope mapping:

1. Resume from `reports/scope_scaling_progress.json`.
2. Process exactly one `NEXT_CHAPTER`; stop afterward.
3. Follow `docs/scope-chapter-workflow.md`.
4. Use `.venv/bin/python`.
5. Start with `prepare-scope-chapter <CODE>` and use its compact packet.
6. Do not preload completed chapters, the full Toronto Notes corpus, or the
   full MCC registry.
7. Toronto Notes structure must be source-grounded. Never reconstruct missing
   headings from medical knowledge.
8. MCC mappings must use canonical registry evidence. Never fabricate an MCC ID.
9. TOC node != study unit.
10. Current clinical recommendations are not frozen at scope stage.
11. Use Python for deterministic validation/accounting; use model reasoning
    only for semantic/source decisions.
12. Review semantically only WEAK, UNCERTAIN, CROSS_DISCIPLINE, recovered
    headings, source ambiguities, and questionable specialist-depth decisions.
13. Do not finalize PRIMARY_OWNER/CROSS_LINK/DISTINCT_CONTEXT during chapter mapping.
14. Run chapter validator and one canonical full pytest run before commit.
15. Do not repeatedly rerun the full test suite unless data changed afterward.
16. Do not launch parallel chapter agents.
17. Commits are authorized when the task explicitly requests them:
    chapter commit first, ledger-hash commit second.
18. Stop after the requested chapter.