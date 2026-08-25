# MCCQE Qbank Project Rules

## Medical and source rules

- Accuracy over quantity.
- Toronto Notes 2025 is the organizational/study-anchor source, not the final clinical authority.
- Current MCC Examination Objectives and the current MCCQE Blueprint define examination scope.
- Study Smarter is an official but non-exhaustive discipline-mapping aid.
- Scope mappings must be supported by canonical MCC evidence; do not use model memory as evidence.
- Any clinical claim used in future question generation must be source-grounded in current authoritative Canadian guidance.
- Current authoritative Canadian guidance determines the clinical answer.
- Do not make substantive medical or scope edits without renewed validation.
- When evidence is insufficient, preserve WEAK/UNCERTAIN status rather than guessing.

## Copyright and privacy rules

- Do not use real, recalled, leaked, copied, or closely paraphrased protected questions.
- Do not copy Toronto Notes prose or questions into project artifacts.
- Keep Toronto Notes PDFs, absolute local paths, OCR/source text, and other copyrighted derived source material private and Git-ignored.

## Validation and lifecycle rules

- JSON is canonical.
- Validation fails closed.
- Preserve stable IDs.
- Preserve provenance and source-node traceability.
- Do not silently promote unresolved or weak evidence.
- Export only `QA_PASS` or genuinely `HUMAN_REVIEWED` questions.
- Never label an item “physician reviewed” or equivalent without actual item-specific human review.

## Current scope-scaling workflow

- Current phase: Toronto Notes → MCC scope crosswalk.
- Do not generate practice questions yet.
- Process one chapter at a time.
- Resume from `reports/scope_scaling_progress.json`.
- Use the frozen scope schema.
- Use deterministic validation for structural checks.
- Use compact per-chapter packets (`python -m scripts.qbank prepare-scope-chapter <CODE>`)
  and the deterministic validator (`python -m scripts.qbank validate-scope-chapter <CODE>`)
  instead of loading the full TOC inventory/objectives registry or manually
  rechecking machine-verifiable facts. See `docs/scope-chapter-workflow.md`.
- Give risk-based second review only to what the validator flags
  (WEAK/UNCERTAIN/warnings).
- Use LLM review only for judgment-heavy mappings and flagged risks.
- Commit every completed chapter before starting another chapter.
- Stop after the requested chapter unless explicitly instructed to continue.

## Operating modes

- `CODEX_NATIVE` is the default Codex mode.
- `MANUAL_RESEARCH` is the fallback.
- `API_AUTOMATED` is disabled unless explicitly approved.
- Python provides deterministic orchestration, validation, retrieval, and data management.

## No external model/API billing

Do not add, configure, or invoke paid external model APIs from project code unless explicitly approved.

In particular, do not:
- require `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, Gemini, or OpenRouter credentials;
- create an LLM API worker;
- call paid model APIs from Python/Node scripts;
- silently introduce usage-billed model dependencies.

Using the currently authorized Codex or Claude Code interactive environment itself is allowed.

Any unattended API-based generation must be implemented only as a separate, explicitly approved `API_AUTOMATED` mode.