# MCCQE Qbank Foundation Design

## Scope

This design covers the deterministic production foundation for the MCCQE question-bank project. It establishes repository policy, configuration, canonical schemas, source validation, job queues, lifecycle enforcement, blind-packet isolation, reference normalization, progress reporting, and safe production export.

It does not generate medical questions, create the six researched manifests, ingest the complete Toronto Notes text, build the React application, or deploy Firebase. Those are later milestones built on this foundation. The next milestone will privately extract and index Toronto Notes 2025, followed by a complete 40–50-question Cardiology pilot.

## Operating Modes

The committed project configuration supports three research modes:

- `CODEX_NATIVE`: default. An active Codex task reads durable filesystem jobs, dispatches isolated Codex-native agents, performs authorized web research, and writes artifacts for deterministic validation.
- `MANUAL_RESEARCH`: fallback. The system writes complete research packets and accepts externally prepared results through the same import validators.
- `API_AUTOMATED`: reserved and disabled. It may only be implemented after explicit user approval.

Python is the deterministic control layer. It must not call OpenAI or another model provider, require an API key, or incur external model/API charges. `CODEX_NATIVE` is intentionally not represented as an unattended Python service: native-agent execution occurs while Codex is actively working, while the filesystem queue provides durable resumability.

## Permanent Safety Rules

The root `AGENTS.md` records permanent project rules:

- accuracy over quantity;
- source-first generation;
- Toronto Notes is an organization and study-anchor source, not final clinical authority;
- current MCC Objectives define scope;
- current authoritative Canadian guidance determines the clinical answer;
- no real, recalled, leaked, copied, or closely paraphrased protected questions;
- no copied Toronto Notes prose or questions;
- JSON is canonical;
- validation fails closed;
- no substantive medical edits without renewed validation;
- no “physician reviewed” or equivalent label without actual item-specific human review;
- no external LLM/API billing in `CODEX_NATIVE` or `MANUAL_RESEARCH` modes.

## Source Handling

The local Toronto Notes file remains at `/Users/annabeketova/Desktop/code/mccqe/Toronto Notes 2025.pdf`. Machine-specific paths and derived source text are private and Git-ignored.

Committed `config/project.json` contains portable policy and expected source metadata. Git-ignored `config/project.local.json` contains the actual absolute PDF path. Source validation resolves the local override, verifies that the file exists, checks the expected 2025 edition declaration, page count of 1,595, size of 444,206,901 bytes, and SHA-256 `9cafb5f2064335c8e4ee00abf446ab78d12b469802aa134fb84effcef3704288`, and confirms that the PDF is not tracked or located in deployable directories.

The later ingestion milestone writes private extracted data beneath `derived/toronto-notes-2025/`. The entire `derived/` tree is excluded from Git and Firebase assets.

## Repository Layout

The foundation creates:

```text
config/                 committed config plus ignored local override
source/                 source-handling documentation only
schemas/                JSON Schema documents
scripts/qbank/          focused Python orchestration package
manifests/              validated discipline manifests
jobs/{pending,running,completed,failed}/
batches/                batch-local source, generation, and QA artifacts
candidates/             generated but unverified questions
blind/                  answer-key-free verification packets
blind_verification/     independent solve results
verified/               QA-passed or human-reviewed canonical questions
quarantine/             unresolved or failed medical items
rejected/               rejected items
retired/                stable-ID history
references/             canonical deduplicated registry
reports/                machine-readable and human-readable status
tests/                  deterministic pipeline tests
app/public/data/qbank/  production-only export target
```

Empty lifecycle directories contain `.gitkeep` files where needed. No private source-derived content is committed.

## Python Architecture

The package uses Python 3.11 or newer and keeps files focused:

- `config.py`: load and merge committed and local configuration.
- `errors.py`: typed validation and transition errors.
- `jsonio.py`: deterministic UTF-8 JSON reads and atomic writes.
- `schema.py`: load JSON Schemas and validate instances.
- `source.py`: source integrity and leakage checks.
- `states.py`: status constants and legal transitions.
- `manifests.py`: validate cross-manifest totals, batch sizes, mappings, and unique IDs.
- `jobs.py`: create deterministic generation and verification jobs and move them safely between queue states.
- `blind.py`: build answer-key-free packets from candidates.
- `references.py`: merge references by normalized canonical identity while preserving stable IDs and claim-level support.
- `risk.py`: deterministically assign high-risk flags from structured fields and text markers.
- `export.py`: include only `QA_PASS` or documented `HUMAN_REVIEWED` items and generate real counts.
- `progress.py`: compute JSON and Markdown progress from filesystem truth.
- `cli.py`: expose small commands over these modules.

The package uses `jsonschema` for standards-compliant JSON Schema validation and `pytest` for tests. No PDF-processing dependency is introduced until the ingestion milestone.

## Canonical Schemas

Milestone 1 defines schemas for:

- project configuration;
- discipline manifest;
- queue job;
- reference and reference registry;
- canonical question;
- blind packet;
- blind-verification result;
- full-rationale-verification result;
- progress report;
- production manifest.

Question status values use canonical uppercase names:

```text
DRAFT → CANDIDATE → STRUCTURE_PASS → BLIND_PASS → MEDICAL_PASS → QA_PASS → PUBLISHED
                    CANDIDATE → QUARANTINE → REVISED → CANDIDATE
                                             QUARANTINE → REJECTED
```

`HUMAN_REVIEWED` is a publication-eligible review designation reached only from `MEDICAL_PASS` or `QA_PASS` with reviewer metadata. `RETIRED` is terminal and preserves the ID. Direct `DRAFT → PUBLISHED` and all unlisted transitions fail.

## Job and Agent Contract

Jobs are durable structured tasks, not LLM API requests. Each job records:

- stable job and batch IDs;
- job type and status;
- attempt count and configured maximum;
- manifest, Toronto Notes page, MCC-objective, and prompt-template inputs;
- deterministic question IDs;
- requested Codex-native roles;
- artifact paths;
- timestamps and failure classification.

Supported failure classes are `TECHNICAL_FAILURE`, `SOURCE_FAILURE`, `MEDICAL_AMBIGUITY`, `REFERENCE_FAILURE`, `SCHEMA_FAILURE`, `DUPLICATE`, and `COPYRIGHT_SIMILARITY`.

Queue mutations use atomic writes and validated directory moves. A failed job preserves logs and artifacts, increments attempts, and never mutates completed output. Concurrency limits are configuration values with defaults of four generation and four verification tasks. ID allocation happens before dispatch, so parallel agents cannot claim overlapping IDs.

## Blind Verification Boundary

Blind packets contain only:

- question ID;
- stem;
- lead-in;
- options;
- MCC mapping;
- Toronto Notes mapping;
- source/reference candidates.

They explicitly exclude `correct_answer`, explanations, distractor rationales, verification history, and generator notes. Both schema constraints and recursive forbidden-field tests enforce the boundary.

The comparator advances only when the independent answer matches, confidence is at least `0.85`, `single_best_answer` is true, `other_defensible_options` is empty, and no uncertainty concern is reported. A mismatch moves the item to quarantine with `BLIND_KEY_MISMATCH`; it never changes the answer automatically.

## Production Export

Production export reads only canonical files beneath `verified/`. It includes a question only when its final status is `QA_PASS`, or it is `HUMAN_REVIEWED` with actual reviewer metadata. It writes discipline data, a deduplicated public reference file, and a manifest whose counts and timestamps are computed from exported artifacts.

The exporter rejects private QA notes, verifier reasoning, source text, candidates, quarantine, rejected and retired items. A leakage scan fails if any PDF or private lifecycle artifact appears beneath `app/public/`, `public/`, or `dist/`.

## Reporting

`reports/progress.json` and `reports/progress.md` are regenerated from filesystem truth. They include planned, generated, blind-passed, QA-passed, rejected, quarantined, human-reviewed, discipline/chapter breakdowns, queue counts, and coverage gaps. No count is manually entered.

## Testing Strategy

Tests start from isolated temporary repositories and cover:

- source presence, metadata, hash, and deploy/Git exclusion;
- every schema with valid and invalid fixtures;
- duplicate IDs across manifests;
- deterministic 40–60-item queue creation;
- exactly five options, key membership, rationales, references, TN mapping, and MCC mapping;
- unknown reference IDs;
- forbidden blind-packet fields at any depth;
- every permitted and forbidden state transition;
- blind mismatch quarantine and confidence gates;
- candidate, rejected, and retired export exclusion;
- production manifest counts derived from actual output;
- source PDF and private-artifact leakage;
- failure preservation and attempt increments;
- progress reports derived from real files.

Tests contain synthetic, non-medical fixtures only. Medical accuracy remains the responsibility of later source-grounded Codex-native research and independent verification stages.

## Checkpoints and Next Milestones

Milestone 1 is complete only when all foundation tests pass and the source validates against the recorded local metadata. Its design, implementation plan, and implementation are committed separately.

Milestone 2 will add private Toronto Notes ingestion using embedded-text extraction first, page rendering and OCR only when needed, deterministic page/heading indexes, and visual QA of uncertain pages.

Milestone 3 will add project-local Codex role instructions for source research, MCC mapping, writing, blind solving, and rationale auditing. Milestone 4 will prove the entire flow on one 40–50-question Cardiology batch before any broader scale-up.
