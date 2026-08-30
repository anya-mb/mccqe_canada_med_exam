# Foundational Evidence Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the validated, audit-backed foundational-evidence substrate without research content or generator changes.

**Architecture:** A focused model module validates the canonical card artifact against frozen scope and the existing `SRDOC-*` registry. A deterministic audit rebuild fingerprints those inputs and rejects any provenance, identity, ordering, or reuse violation before writing the report.

**Tech Stack:** Python 3.11, existing `qbank` JSON/path utilities, JSON Schema, pytest.

**Spec:** `docs/superpowers/specs/2026-08-30-foundational-evidence-design.md`

## Global Constraints

- Preserve frozen allocation and all existing READY packet populations/audits unchanged.
- Treat Toronto Notes as `TOPIC_CONTEXT_ONLY`; retain both `tn_page_range` and `pdf_page_range` as untouched navigation metadata.
- Permit only atomic `VERIFIED_COMPLETE` cards; no research claims are added in Phase A.
- Reuse `SRDOC-*` by canonical URL; create `FNDOC-*` metadata only for URLs absent from the registry.
- Do not modify the generator, generate questions, browse, OCR, or update `MEMORY.md` in this documentation-only/Phase A implementation scope.
- Use deterministic Python for parsing, validation, IDs, ordering, SHA-256 fingerprints, and audit rendering; fail closed.

---

### Task 1: Canonical schema and model

**Files:**

- Create: `schemas/foundational-evidence-claim-cards.schema.json`
- Create: `scripts/qbank/foundational_evidence.py`
- Modify: `scripts/qbank/cli.py`
- Create: `research/qgen/foundational_evidence_claim_cards.json`
- Create: `tests/test_foundational_evidence.py`

**Interfaces:**

- Produces: `build_foundational_evidence_model(root, artifact) -> FoundationalEvidenceModel`.
- Produces: `validate_foundational_evidence(root, artifact, registry) -> FoundationalEvidenceValidation`.
- CLI: `validate-foundational-evidence` reads the canonical artifact and existing source-document registry without mutation.

- [ ] **Step 1: Write failing schema/model tests**

Add `test_empty_canonical_artifact_is_valid`, `test_card_requires_verified_complete_atomic_claim_and_citation_locator`, and `test_card_references_known_frozen_scope_identifier`. The empty Phase A artifact must have empty `documents` and `claim_cards`; cards must use `FNDCLM-*`, document citations, and recognized study-unit/allocation IDs.

- [ ] **Step 2: Confirm the focused tests fail**

Run: `.venv/bin/python -m pytest tests/test_foundational_evidence.py -q`

Expected: FAIL because the schema, model, validator, CLI command, and artifact do not yet exist.

- [ ] **Step 3: Implement the minimum model**

Define JSON-schema shapes for the root, `FNDOC-*` metadata, atomic cards, and citations. Reuse `validate_instance`, `read_json`, `resolve_root_path`, and the registry’s canonical-URL normalization policy. Validate frozen IDs from `research/scope/master_scope_crosswalk.json` and `research/scope/final_question_allocation.json`; do not rewrite either input. Make the Phase A artifact an empty, valid canonical corpus with fingerprints left to its derived audit.

- [ ] **Step 4: Run focused verification**

Run: `.venv/bin/python -m pytest tests/test_foundational_evidence.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the independently testable model**

Run: `git diff --check`

```bash
git add schemas/foundational-evidence-claim-cards.schema.json scripts/qbank/foundational_evidence.py scripts/qbank/cli.py research/qgen/foundational_evidence_claim_cards.json tests/test_foundational_evidence.py
git commit -m "qgen: add foundational evidence model"
```

### Task 2: SRDOC/FNDOC provenance validation and deterministic audit

**Files:**

- Modify: `scripts/qbank/foundational_evidence.py`
- Modify: `scripts/qbank/cli.py`
- Create: `reports/foundational_evidence_audit.json`
- Modify: `tests/test_foundational_evidence.py`

**Interfaces:**

- Produces: `build_foundational_evidence_audit(root, artifact, registry) -> dict[str, Any]`.
- Produces: `validate_foundational_evidence_audit(root, artifact, registry, audit) -> FoundationalEvidenceValidation`.
- Produces: `write_foundational_evidence_audit(root) -> dict[str, Any]`.
- CLI: `build-foundational-evidence-audit` validates all inputs before atomically writing the audit.

- [ ] **Step 1: Add failing provenance/audit tests**

Add `test_existing_registry_url_must_use_srdoc_not_fndoc`, `test_new_fndoc_id_is_deterministic_and_cited`, `test_unknown_or_duplicate_document_reference_fails_closed`, and `test_audit_rebuild_detects_changed_input_fingerprint`. Assert FNDOC ID equals `FNDOC-` plus the first 16 uppercase hexadecimal SHA-256 characters of the canonical URL and that every cited document is either registry-backed SRDOC or unique FNDOC metadata.

- [ ] **Step 2: Confirm the provenance tests fail**

Run: `.venv/bin/python -m pytest tests/test_foundational_evidence.py -q`

Expected: FAIL because no provenance/audit builder exists.

- [ ] **Step 3: Implement exact audit rebuild and atomic writer**

Fingerprint the canonical card artifact, source-document registry, and frozen scope inputs by repository-relative path and SHA-256. Sort IDs deterministically; derive all count fields; compare the supplied audit object against the rebuilt audit. Reject duplicate URLs, FNDOC/SRDOC URL collisions, document-ID/content mismatches, unresolved citations, and missing or stale fingerprints before the first write.

- [ ] **Step 4: Run focused verification**

Run: `.venv/bin/python -m pytest tests/test_foundational_evidence.py tests/test_source_document_registry.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the audit layer**

Run: `git diff --check`

```bash
git add scripts/qbank/foundational_evidence.py scripts/qbank/cli.py reports/foundational_evidence_audit.json tests/test_foundational_evidence.py
git commit -m "qgen: audit foundational evidence provenance"
```

### Task 3: Regression protection and Phase A checkpoint

**Files:**

- Modify: `tests/test_foundational_evidence.py`
- Modify: `tests/test_source_document_registry.py`

**Interfaces:**

- Verifies: the empty canonical corpus and audit are reproducible; existing `SRDOC-*` registry semantics remain unchanged.

- [ ] **Step 1: Add cross-layer regression tests**

Add `test_empty_corpus_and_audit_are_byte_deterministic` and `test_foundational_validation_does_not_mutate_registry_or_source_packets`. Use deep copies and SHA-256 snapshots of `research/qgen/source_document_registry.json` and every `research/qgen/source_packet_population_srb_*.json` to assert read-only Phase A behavior.

- [ ] **Step 2: Run focused regression verification**

Run: `.venv/bin/python -m pytest tests/test_foundational_evidence.py tests/test_source_document_registry.py tests/test_source_packet_population.py -q`

Expected: PASS.

- [ ] **Step 3: Run the full suite once**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS because Phase A changes production Python, schema, and tests.

- [ ] **Step 4: Verify frozen artifacts and commit checkpoint**

Run: `git diff --check && git diff -- research/scope research/qgen/source_packet_population_srb_*.json reports/source_packet_*`

Expected: no diff in frozen scope, existing source packets, or their audits.

```bash
git add tests/test_foundational_evidence.py tests/test_source_document_registry.py
git commit -m "test: protect foundational evidence boundaries"
```

## Deferred Phase B

Only after Phase A passes: research the stable factual support needed for the 10-question `QGEN-PHELO-011` retry; create its 10-slot concept plan; then make the pilot generator consume frozen scope, Toronto Notes context, foundational claim cards, and READY current source packets. This plan authorizes none of those actions.

