# MCCQE Qbank Project Rules

## Medical and source rules

- Accuracy over quantity.
- Source-first generation.
- Generate only from source-grounded, current Canadian clinical guidance.
- Toronto Notes is an organizational and study-anchor source, not the final clinical authority.
- Current MCC Objectives define scope.
- Current authoritative Canadian guidance determines the clinical answer.
- Do not make substantive medical edits without renewed validation.

## Copyright and privacy rules

- Do not use real, recalled, leaked, copied, or closely paraphrased protected questions.
- Do not copy Toronto Notes prose or questions into project artifacts.
- Keep Toronto Notes PDFs, absolute local paths, and derived source text private and Git-ignored.

## Validation and lifecycle rules

- JSON is canonical.
- Validation fails closed.
- Maintain only validated artifacts in their legal lifecycle states.
- Preserve stable IDs for retired items.
- Export only `QA_PASS` items or `HUMAN_REVIEWED` items with actual reviewer metadata.

## Human review and operating modes

- Never label an item “physician reviewed” or equivalent without actual item-specific human review.
- `CODEX_NATIVE` is the default mode and `MANUAL_RESEARCH` is the fallback mode.
- `API_AUTOMATED` is disabled unless explicitly approved.
- Python provides deterministic orchestration, validation, and data management only.

## No external LLM/API billing

This project operates in `CODEX_NATIVE` mode by default.

Do not call the OpenAI API, require `OPENAI_API_KEY`, call Anthropic, Gemini, or OpenRouter, create an LLM API worker, or incur external model/API charges in `CODEX_NATIVE` or `MANUAL_RESEARCH` modes. Any unattended API-based generation must be a separate, explicitly approved `API_AUTOMATED` mode.
