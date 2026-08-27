## MCC scope pipeline

`AGENTS.md` is the canonical agent instruction file.

### General rules

- Follow `docs/scope-chapter-workflow.md`.
- Resume state from `reports/scope_scaling_progress.json`.
- Use `.venv/bin/python` for all Python commands and tests.
- Use deterministic Python for validation, accounting, aggregation, and reporting.
- Use model reasoning only for semantic/source decisions that cannot be resolved deterministically.
- Never infer Toronto Notes structure from medical knowledge.
- Never fabricate MCC objective IDs or mappings.
- Do not freeze changing clinical recommendations during scope mapping.
- Do not call external LLM APIs from project code.
- Do not preload the full Toronto Notes corpus, complete MCC registry, or completed chapter artifacts unless specifically necessary.
- Prefer targeted retrieval over broad context loading.
- Do not read completed chapters merely as formatting examples; use schemas and project docs.
- Keep narration concise and avoid rereading files unnecessarily.
- Do not launch parallel chapter agents unless explicitly requested.
- Do not commit unless the current user task explicitly authorizes commits.

### Chapter scope mapping

- Process exactly one `NEXT_CHAPTER` per task and stop afterward.
- Start with `prepare-scope-chapter <CODE>` and use the compact packet.
- TOC node != study unit.
- Source structure must be source-grounded.
- Use targeted registry/source retrieval only when needed.
- Do not finalize `PRIMARY_OWNER`, `CROSS_LINK`, or `DISTINCT_CONTEXT` during chapter mapping.
- Semantically review only genuine risk items:
  - UNCERTAIN
  - weak-only evidence
  - unresolved source ambiguities
  - recovered headings needing confirmation
  - questionable SPECIALIST_DETAIL
  - CROSS_DISCIPLINE only when the classification itself is uncertain
- Run the chapter validator and one canonical full pytest run after final canonical edits.
- Do not rerun the full suite after ledger-hash-only changes.
- When commits are authorized:
  1. chapter/content commit
  2. ledger-hash follow-up commit
- Stop after the requested chapter.

### Global scope phase

After chapter scope scaling is complete:

- Global aggregation must be deterministic Python.
- Do not load all chapter JSON into model context.
- Scripts should read chapter artifacts directly from disk.
- Do not semantically merge or rewrite chapter content during deterministic aggregation.
- Preserve all chapter-local provenance.
- Build candidate sets deterministically before using model reasoning.
- Semantic global review should operate only on compact conflict/risk packets.
- Do not create `MCC_GAP_FILL` units until the dedicated semantic gap-analysis phase.
- Do not generate questions until global ownership, weak/uncertain review, and MCC gap analysis are complete.

### Agent efficiency

For deterministic pipeline work:

- Do not load optional plugin/skill documentation unless the current user task explicitly requires it.
- Do not use planning frameworks for simple read-only or deterministic maintenance tasks unless required by the user.
- Inspect large JSON collections programmatically rather than placing them in model context.
- For failures, identify the root cause before changing code.