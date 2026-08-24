# MCCQE Qbank Pipeline

Deterministic, fail-closed filesystem foundation for a source-grounded MCCQE
question bank. Python owns orchestration, validation, and data management;
medical reasoning and research happen only through actively supervised Codex-native
work or the documented manual fallback.

`CODEX_NATIVE` is the default mode. It does not call the OpenAI API, require
`OPENAI_API_KEY`, run an unattended LLM worker, or incur external model/API
charges. `MANUAL_RESEARCH` uses the same validated artifact boundary.
`API_AUTOMATED` is reserved, disabled, and may be implemented only as a separate
mode after explicit approval.

## Setup

Python 3.11+, Git, and Poppler's `pdfinfo` command are required.

```bash
uv sync --extra dev
cp config/project.local.example.json config/project.local.json
```

Set the absolute local Toronto Notes PDF path only in the ignored
`config/project.local.json`, then verify the foundation:

```bash
uv run qbank validate-project
uv run pytest -q
```

If `uv run` cannot initialize its user cache in a restricted environment, use
the already synchronized repository environment:

```bash
.venv/bin/qbank validate-project
.venv/bin/pytest -q
```

## Create a searchable private PDF

Use the local OCR page records to add an invisible text layer while leaving
the rendered PDF pages unchanged. The command also writes one normalized UTF-8
text file per page under the ignored `derived/` tree:

```bash
.worktrees/qbank-production/.venv/bin/python scripts/qbank/searchable_pdf.py \
  --pdf Toronto_Notes_with_search.pdf \
  --ocr-dir derived/toronto-notes-2025/ocr/pages \
  --output Toronto_Notes_searchable.pdf \
  --clean-ocr-dir derived/toronto-notes-2025/clean-ocr
```

The output PDF is private source material and must not be committed or placed
under a deploy directory.

Portable policy and expected source metadata live in `config/project.json`.
Machine-local paths never belong in committed configuration.

## Commands

Every command accepts `--root PATH` either before or after the command. It
defaults to the current directory. Successful status goes to stdout. Expected
failures go to stderr as one machine-readable `FAILURE_CLASS: message` line and
return a nonzero status.

```bash
qbank validate-project
qbank validate-source
qbank validate-manifests
qbank create-jobs
qbank create-blind candidates/QUESTION-ID.json
qbank evaluate-blind candidates/QUESTION-ID.json blind_verification/QUESTION-ID.json
qbank progress
qbank export --version 2026.1
```

- `validate-project` checks merged configuration against its schema, all
  required nonempty prompts, the complete schema/valid-fixture catalog, private
  deploy exclusion, source integrity and Git exclusion, and the current
  manifest set. A sound foundation exits successfully with `PROJECT_VALID`.
  Until the exact six discipline identities exist once each—Medicine/MED,
  Obstetrics & Gynecology/OBGYN, Pediatrics/PED, PHELO/PHELO,
  Psychiatry/PSY, and Surgery/SURG—it also reports `GENERATION_BLOCKED`; that
  milestone status is explicit but is not a foundation-validation failure.
- `validate-source` verifies source presence, size, SHA-256, page count,
  `pdfinfo` metadata, Git exclusion, and deploy exclusion.
- `validate-manifests` validates every JSON manifest and all cross-manifest
  totals, mappings, allocations, and global IDs. An empty foundation is a valid
  set of zero manifests.
- `create-jobs` fails closed until those exact six identities exist once each,
  then creates deterministic, idempotent pending generation jobs.
- `create-blind` requires a `STRUCTURE_PASS` candidate and writes an
  allowlisted, answer-key-free packet. `--output PATH` overrides its default
  path under `blind/`.
- `evaluate-blind` requires `STRUCTURE_PASS`, validates the candidate and
  independent result, applies the configured confidence floor and shared
  lifecycle transition rules, and reports `BLIND_PASS` or `QUARANTINE` without
  changing the candidate answer.
- `progress` regenerates `reports/progress.json` and `reports/progress.md` from
  filesystem truth.
- `export` validates and atomically replaces `app/public/data/qbank/` for the
  requested uniform content version. Only publication-eligible `QA_PASS`,
  `HUMAN_REVIEWED`, or already-`PUBLISHED` verified questions and their
  referenced public records are included.

All command input/output paths other than the selected `--root` are strictly
root-relative: absolute paths, parent traversal, and symlink ancestors fail
closed.

## Lifecycle and publication boundary

The canonical path is:

```text
DRAFT → CANDIDATE → STRUCTURE_PASS → BLIND_PASS → MEDICAL_PASS → QA_PASS → PUBLISHED
                    CANDIDATE → QUARANTINE → REVISED → CANDIDATE
                                             QUARANTINE → REJECTED
MEDICAL_PASS or QA_PASS → HUMAN_REVIEWED → PUBLISHED → RETIRED
```

`HUMAN_REVIEWED` requires real item-specific reviewer metadata and is reachable
only from `MEDICAL_PASS` or `QA_PASS`. `PUBLISHED` may move only to `RETIRED`;
`REJECTED` and `RETIRED` are terminal, and all unlisted transitions fail.
Production export reads only `verified/` and admits `QA_PASS`, documented
`HUMAN_REVIEWED`, or persisted `PUBLISHED` items. A separate strict public
schema validates an allowlist projection that omits reviewer identity,
verification internals, private physical-PDF mapping, and source-only QA flags.
Candidates, blind results, QA notes, source text, quarantine, rejected, and
retired artifacts are private and never exported.

## Private source rules

Toronto Notes is a private study anchor and organization source, not final
clinical authority. Current MCC Objectives define scope, and current
authoritative Canadian guidance determines clinical answers. Do not commit,
publish, deploy, quote, or closely paraphrase Toronto Notes prose or protected
questions.

The PDF, `config/project.local.json`, and the entire private derived-source tree
are Git-ignored. No PDF or private lifecycle directory may appear beneath
`app/public/`, `public/`, or `dist/`. Keep extracted text, OCR, verifier
reasoning, generation logs, and QA artifacts in their ignored/private locations;
only schema-validated public JSON crosses the export boundary.

## Codex-native active-task queue contract

The filesystem queue is durable state, not an LLM API request mechanism.
Python may create and validate jobs, allocate IDs, enforce transitions, and
atomically store artifacts, but it does not perform medical generation or start
model calls.

While a Codex task is actively working, it may read validated jobs from
`jobs/pending/`, claim no more than the configured generation or verification
concurrency, dispatch isolated Codex-native roles, perform authorized source
research, and write only the job's declared artifact paths. The controller then
validates the returned JSON before moving the job through
`pending → running → completed` or `failed`. Failures retain logs and artifacts,
carry a supported failure class, increment attempts, and may retry only within
the configured limit. Each transition holds an exclusive per-job claim across
read, validation, write, and move; completed jobs are immutable. Stable question
IDs are allocated before dispatch, so concurrent work cannot claim overlapping
IDs.

When no Codex task is active, no agent work runs. Durable queue files make the
workflow resumable at the next active task without an unattended service or
external model billing.

## Milestones

1. Complete this deterministic foundation and keep generation blocked until all
   six researched discipline manifests validate.
2. Privately extract and index Toronto Notes 2025 beneath the ignored derived
   tree.
3. Research, validate, and audit the six discipline manifests against MCC scope
   and current Canadian guidance.
4. Produce and fully verify a 40–50-question Cardiology pilot through the entire
   blind, medical, QA, and export lifecycle.
5. Scale validated production across the remaining disciplines, preserving the
   same source, reference, risk, and lifecycle gates.
6. Build the student application, conduct real item-specific human review where
   claimed, export only eligible content, and deploy only after a final leakage
   and foundation audit.
