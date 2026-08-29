# Accelerated Source Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the minimum deterministic substrate for parallel source-packet research, coordinator integration, generation readiness, and repository-only resume.

**Architecture:** Extend the existing packet validator, then add focused registry, readiness, coordinator, and checkpoint modules. Every builder reads the frozen plan plus integrated packet populations and fails closed before atomically writing derived artifacts.

**Tech Stack:** Python 3.11, existing `qbank` JSON/path utilities, Git CLI via argument-list subprocess calls, pytest.

**Spec:** `docs/superpowers/specs/2026-08-29-accelerated-source-research-design.md`

## Global Constraints

- Preserve every frozen planning layer and existing source-packet schema.
- Implement no MCQ generator or independent-verification executor.
- Use deterministic Python for parsing, reconciliation, ordering, hashing, and rendering.
- Source-research worker branches remain `codex/source-research/SRB-XXX`; normal concurrency is two.
- A successful worker commit contains only its population and audit pair.
- Later implementation reasoning defaults to MEDIUM; escalate to HIGH only for an architecture conflict or difficult semantic decision.
- Every task ends with focused verification, a full suite when production Python changes, `git diff --check`, and one checkpoint commit.
- Tasks 1–5 update only the marked `MEMORY.md` resume block with `Task N of 6 complete` and the exact next task; Task 6 replaces this implementation marker with the derived operational resume state.

---

### Task 1: Batch-local validator and disjoint ownership

**Files:**
- Modify: `scripts/qbank/source_packet_population.py`
- Create: `scripts/qbank/source_research_coordinator.py`
- Modify: `scripts/qbank/cli.py`
- Modify: `tests/test_source_packet_population.py`
- Create: `tests/test_source_research_coordinator.py`
- Modify: `MEMORY.md`

**Interfaces:**
- Produces: `load_integrated_source_packet_populations(root) -> list[dict[str, Any]]`.
- Produces: `validate_source_packet_research_batch(root, population, integrated_populations, audit) -> SourcePacketPopulationValidation`.
- Produces: `validate_disjoint_worker_ownership(root, batch_ids, integrated_populations) -> SourceResearchCoordinatorValidation`.
- CLI: `validate-source-packet-wave SRB-XXX` validates against all integrated populations except the selected artifact, independent of batch order.

- [ ] **Step 1: Add failing tests for batch isolation and state handling**

Add these exact cases: `test_batch_validator_accepts_ready_blocked_and_incomplete_packets`, `test_batch_validator_rejects_changed_planning_field_and_wrong_packet_order`, `test_batch_validator_rejects_packet_already_present_in_any_integrated_population`, `test_disjoint_ownership_rejects_duplicate_pending_packet_or_integrated_batch`, and `test_cli_wave_validation_does_not_require_every_earlier_batch_file`.

Assert exact canonical packet order, plan SHA-256, unchanged `_PLANNING_FIELDS`, the four terminal research statuses, claim/source rules, audit rebuild equality, and pairwise-disjoint selected packet IDs.

- [ ] **Step 2: Confirm the new tests fail**

Run: `.venv/bin/python -m pytest tests/test_source_packet_population.py tests/test_source_research_coordinator.py -q`

Expected: FAIL because the new public interfaces and order-independent loading do not exist.

- [ ] **Step 3: Implement the minimal contracts**

Reuse existing source, citation, family, disagreement, jurisdiction, and rollup checks. Do not weaken pilot validation. Sort file discovery by canonical plan order, not filename order.

- [ ] **Step 4: Run focused and full verification**

Run: `.venv/bin/python -m pytest tests/test_source_packet_population.py tests/test_source_research_coordinator.py -q`

Run: `.venv/bin/python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 5: Verify scope and commit checkpoint**

Insert `<!-- SOURCE_RESEARCH_RESUME:START -->` and `<!-- SOURCE_RESEARCH_RESUME:END -->` around the current-phase resume content. Preserve the canonical counts, add `Acceleration implementation: Task 1 of 6 complete`, and set `NEXT_STEP = IMPLEMENT_ACCELERATED_SOURCE_RESEARCH_TASK_2`.

Run: `git diff --check && git diff -- research/qgen/source_packet_plan.json research/qgen/question_generation_manifest.json research/scope`

Expected: no frozen-artifact diff.

```bash
git add scripts/qbank/source_packet_population.py scripts/qbank/source_research_coordinator.py scripts/qbank/cli.py tests/test_source_packet_population.py tests/test_source_research_coordinator.py MEMORY.md
git commit -m "qgen: validate isolated source research batches"
```

---

### Task 2: Metadata-only source-document registry

**Files:**
- Create: `scripts/qbank/source_document_registry.py`
- Create: `tests/test_source_document_registry.py`
- Modify: `MEMORY.md`

**Interfaces:**
- Produces: `build_source_document_registry(root, populations) -> dict[str, Any]`.
- Produces: `validate_source_document_registry(root, populations, registry) -> SourceDocumentRegistryValidation`.
- Produces: `write_source_document_registry(root, populations) -> dict[str, Any]`.

- [ ] **Step 1: Add failing registry tests**

Add these exact cases: `test_registry_deduplicates_by_canonical_https_url_and_contains_metadata_only`, `test_registry_preserves_source_and_packet_provenance_in_canonical_order`, `test_registry_rejects_one_source_id_with_incompatible_metadata`, `test_registry_rejects_one_url_with_incompatible_document_identity`, and `test_registry_rebuild_is_byte_deterministic`.

Require `document_id = "SRDOC-" + sha256(canonical_url.encode()).hexdigest()[:16].upper()`. Each record contains document identity/currentness fields, sorted source IDs and packet IDs, first/last packet ID, and latest retrieval date; it excludes recommendations, evidence boundaries, exceptions, and claim text.

- [ ] **Step 2: Confirm the tests fail**

Run: `.venv/bin/python -m pytest tests/test_source_document_registry.py -q`

Expected: FAIL because `qbank.source_document_registry` does not exist.

- [ ] **Step 3: Implement deterministic build, validation, and atomic write**

```python
_IDENTITY_FIELDS = (
    "title", "issuing_organization", "source_family", "source_type",
    "jurisdiction", "is_canadian", "international_fallback",
    "publication_date", "update_date", "guideline_version",
    "date_status", "version_status", "currentness_status",
)
```

Normalize only surrounding whitespace in URLs; require HTTPS and exact identity-field agreement for repeated URLs. Repeated source IDs may name several locator URLs only when `_IDENTITY_FIELDS` agree; contextual `currentness_notes` are not copied into the registry. Include input population paths and SHA-256 fingerprints at registry level.

- [ ] **Step 4: Run focused and full verification**

Run: `.venv/bin/python -m pytest tests/test_source_document_registry.py tests/test_source_packet_population.py -q`

Run: `.venv/bin/python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit checkpoint**

Run: `git diff --check`

Update the marked resume block to `Task 2 of 6 complete` and `NEXT_STEP = IMPLEMENT_ACCELERATED_SOURCE_RESEARCH_TASK_3`; retain artifact-derived research counts.

```bash
git add scripts/qbank/source_document_registry.py tests/test_source_document_registry.py MEMORY.md
git commit -m "qgen: build source document registry"
```

---

### Task 3: Generation readiness and queue

**Files:**
- Create: `scripts/qbank/generation_source_state.py`
- Modify: `scripts/qbank/cli.py`
- Create: `tests/test_generation_source_state.py`
- Modify: `MEMORY.md`

**Interfaces:**
- Produces: `build_generation_source_readiness(root, populations) -> dict[str, Any]`.
- Produces: `build_generation_queue(root, readiness) -> dict[str, Any]`.
- Produces: `validate_generation_source_readiness(root, populations, artifact) -> GenerationSourceStateValidation`.
- Produces: `validate_generation_queue(root, readiness, artifact) -> GenerationSourceStateValidation`.
- Produces: `write_generation_source_state(root, populations) -> tuple[dict[str, Any], dict[str, Any]]`.
- CLI: `build-generation-source-state` and `validate-generation-source-state`.

- [ ] **Step 1: Add failing readiness and queue tests**

Add these exact cases: `test_readiness_has_exactly_one_record_for_each_of_220_manifest_jobs`, `test_job_is_source_ready_only_when_every_required_packet_is_ready`, `test_blocked_precedes_pending_and_records_packet_ids_and_reason_categories`, `test_queue_contains_only_source_ready_jobs_in_manifest_order_then_job_id`, and `test_readiness_and_queue_validators_reject_missing_extra_or_reordered_jobs`.

Each readiness record contains `job_id`, `required_source_packet_ids`, ordered `packet_statuses`, `state`, `blocking_source_packet_ids`, and sorted `blocking_reason_categories`. `BLOCKED` wins over `PENDING`; otherwise any pending/incomplete packet yields `PENDING`; all ready yields `SOURCE_READY`.

- [ ] **Step 2: Confirm the tests fail**

Run: `.venv/bin/python -m pytest tests/test_generation_source_state.py -q`

Expected: FAIL because the state module and CLI commands do not exist.

- [ ] **Step 3: Implement exact derivation and validation**

```python
BLOCKED_STATUSES = {"BLOCKED_EVIDENCE_CONFLICT", "BLOCKED_JURISDICTION"}
```

Read job order and job metadata from `question_generation_manifest.json`; read packet requirements only from `source_packet_plan.json`. Reject duplicate integrated packet IDs and unknown statuses.

- [ ] **Step 4: Run focused and full verification**

Run: `.venv/bin/python -m pytest tests/test_generation_source_state.py tests/test_source_packet_plan.py -q`

Run: `.venv/bin/python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit checkpoint**

Run: `git diff --check`

Update the marked resume block to `Task 3 of 6 complete` and `NEXT_STEP = IMPLEMENT_ACCELERATED_SOURCE_RESEARCH_TASK_4`; retain artifact-derived research counts.

```bash
git add scripts/qbank/generation_source_state.py scripts/qbank/cli.py tests/test_generation_source_state.py MEMORY.md
git commit -m "qgen: derive generation source readiness"
```

---

### Task 4: Coordinator reconciliation and worker-commit inspection

**Files:**
- Modify: `scripts/qbank/source_research_coordinator.py`
- Modify: `scripts/qbank/cli.py`
- Modify: `tests/test_source_research_coordinator.py`
- Modify: `MEMORY.md`

**Interfaces:**
- Produces: `discover_source_research_workers(root, canonical_commit) -> list[dict[str, Any]]`.
- Produces: `resolve_git_commit(root, revision) -> str`.
- Produces: `validate_worker_commit(root, worker, canonical_commit) -> SourceResearchCoordinatorValidation`.
- Produces: `build_source_research_integration_audit(root, canonical_commit, populations, registry, readiness, queue, workers) -> dict[str, Any]`.
- Produces: `validate_source_research_integration_audit(root, audit, populations, registry, readiness, queue, workers) -> SourceResearchCoordinatorValidation`.
- CLI: `status-source-research-workers` and `validate-source-research-worker-set COMMIT [additional commits]`; neither mutates Git.

- [ ] **Step 1: Add failing Git/reconciliation tests**

Add these exact cases: `test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration`, `test_worker_commit_requires_codex_batch_branch_matching_parent_checkpoint`, `test_worker_commit_rejects_any_file_outside_expected_population_audit_pair`, `test_worker_set_rejects_overlapping_or_already_integrated_batches`, and `test_integration_audit_rebuild_detects_changed_prior_ready_packet_and_queue_mismatch`.

Use temporary Git repositories and subprocess argument lists. Do not invoke a shell. Worker JSON is read with `git show COMMIT:path`; validation uses the canonical checkout's frozen plan.

- [ ] **Step 2: Confirm the tests fail**

Run: `.venv/bin/python -m pytest tests/test_source_research_coordinator.py -q`

Expected: FAIL because worker discovery and integration audit interfaces do not exist.

- [ ] **Step 3: Implement read-only Git inspection and reconciliation**

```python
def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout
```

Require branch `codex/source-research/SRB-XXX`, one parent equal to `canonical_commit`, and exactly `research/qgen/source_packet_population_srb_XXX.json` plus `reports/source_packet_wave_srb_XXX_audit.json`. Audit plan/population hashes, packet/batch counts, prior-ready immutability, registry reconciliation, readiness/queue equality, and worker states.

- [ ] **Step 4: Run focused and full verification**

Run: `.venv/bin/python -m pytest tests/test_source_research_coordinator.py tests/test_source_packet_population.py tests/test_source_document_registry.py tests/test_generation_source_state.py -q`

Run: `.venv/bin/python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit checkpoint**

Run: `git diff --check`

Update the marked resume block to `Task 4 of 6 complete` and `NEXT_STEP = IMPLEMENT_ACCELERATED_SOURCE_RESEARCH_TASK_5`; retain artifact-derived research counts.

```bash
git add scripts/qbank/source_research_coordinator.py scripts/qbank/cli.py tests/test_source_research_coordinator.py MEMORY.md
git commit -m "qgen: reconcile source research workers"
```

---

### Task 5: Migrate the existing validated research state

**Files:**
- Modify: `scripts/qbank/source_research_coordinator.py`
- Modify: `scripts/qbank/cli.py`
- Create: `tests/test_source_research_migration.py`
- Create: `research/qgen/source_document_registry.json`
- Create: `research/qgen/generation_source_readiness.json`
- Create: `research/qgen/generation_queue.json`
- Modify: `reports/source_packet_research_progress.json`
- Create: `reports/source_research_integration_audit.json`
- Modify: `MEMORY.md`

**Interfaces:**
- Produces: `build_source_research_state(root, coordinator_input_commit) -> SourceResearchState`.
- Produces: `write_source_research_state(root, coordinator_input_commit) -> SourceResearchState`.
- CLI: `rebuild-source-research-state --input-commit SHA` validates all inputs before atomically writing each derived JSON artifact.

- [ ] **Step 1: Add failing current-state reconstruction test**

```python
def test_current_repository_reconstructs_valid_source_research_state():
    state = build_source_research_state(
        REPO,
        coordinator_input_commit=resolve_git_commit(REPO, "HEAD"),
    )
    assert state.progress["SOURCE_PACKETS_READY"] == 70
    assert state.progress["RESEARCH_BATCHES_COMPLETE"] == 8
    assert len(state.registry["documents"]) == 67
    assert len(state.readiness["jobs"]) == 220
    assert state.queue["jobs"] == []
    assert state.audit["status"] == "PASS"
```

Also assert 1,454 pending packets, 95 source links, zero duplicate ownership, exact integrated input hashes, and byte-identical repeated builds.

- [ ] **Step 2: Confirm the test fails**

Run: `.venv/bin/python -m pytest tests/test_source_research_migration.py -q`

Expected: FAIL because the aggregate builder does not exist.

- [ ] **Step 3: Implement aggregate validation-before-write**

```python
@dataclass(frozen=True)
class SourceResearchState:
    progress: dict[str, Any]
    registry: dict[str, Any]
    readiness: dict[str, Any]
    queue: dict[str, Any]
    audit: dict[str, Any]
```

Validate every canonical population and all five derived artifacts in memory before the first write. Resolve CLI revision input with `resolve_git_commit`; record the resulting SHA as `coordinator_input_commit`, not a self-referential future commit SHA.

- [ ] **Step 4: Materialize and verify the migration**

Run: `.venv/bin/python -m qbank.cli rebuild-source-research-state --input-commit HEAD`

Run: `.venv/bin/python -m qbank.cli validate-generation-source-state && .venv/bin/python -m pytest tests/test_source_research_migration.py -q`

Run: `.venv/bin/python -m pytest -q`

Expected: registry has 67 documents/95 source links; readiness has 220 jobs; queue has zero jobs; integration audit and full suite PASS.

- [ ] **Step 5: Verify data-only scope and commit checkpoint**

Run: `git diff --check && git diff -- research/qgen/source_packet_population_srb_*.json research/qgen/source_packet_plan.json research/qgen/question_generation_manifest.json research/scope`

Expected: no source populations or frozen inputs changed.

Update the marked resume block from the rebuilt artifacts to `Task 5 of 6 complete` and `NEXT_STEP = IMPLEMENT_ACCELERATED_SOURCE_RESEARCH_TASK_6`.

```bash
git add scripts/qbank/source_research_coordinator.py scripts/qbank/cli.py tests/test_source_research_migration.py research/qgen/source_document_registry.json research/qgen/generation_source_readiness.json research/qgen/generation_queue.json reports/source_packet_research_progress.json reports/source_research_integration_audit.json MEMORY.md
git commit -m "qgen: migrate source research coordinator state"
```

---

### Task 6: Checkpoint validation and deterministic resume state

**Files:**
- Create: `scripts/qbank/source_research_checkpoint.py`
- Modify: `scripts/qbank/source_research_coordinator.py`
- Modify: `scripts/qbank/cli.py`
- Create: `tests/test_source_research_checkpoint.py`
- Modify: `MEMORY.md`
- Modify: `reports/source_research_integration_audit.json`

**Interfaces:**
- Produces: `derive_next_source_research_action(progress, queue, workers) -> str`.
- Produces: `render_memory_source_research_resume(existing, state, workers) -> str`.
- CLI: `checkpoint-source-research --input-commit SHA` rebuilds/validates JSON state, renders `MEMORY.md`, then revalidates the written checkpoint.

- [ ] **Step 1: Add failing checkpoint/resume tests**

Add these exact cases: `test_next_action_priority_is_awaiting_then_retry_then_source_ready_then_pending_then_blocked`, `test_memory_renderer_changes_only_marked_resume_sections`, `test_memory_renderer_uses_artifact_counts_and_current_head_checkpoint_marker`, `test_checkpoint_command_is_idempotent_and_fails_before_write_on_invalid_state`, and `test_fresh_session_contract_is_reconstructible_from_repo_and_git_state`.

Use this exact action order: `INTEGRATE_SOURCE_RESEARCH_WORKERS`, `RESUME_SOURCE_RESEARCH_BATCH`, `PLAN_SOURCE_READY_GENERATION`, `CONTINUE_SOURCE_PACKET_RESEARCH`, `RESOLVE_SOURCE_PACKET_BLOCKERS`, `SOURCE_RESEARCH_COMPLETE`.

- [ ] **Step 2: Confirm the tests fail**

Run: `.venv/bin/python -m pytest tests/test_source_research_checkpoint.py -q`

Expected: FAIL because deterministic resume rendering does not exist.

- [ ] **Step 3: Implement fail-closed checkpoint rendering**

```python
RESUME_START = "<!-- SOURCE_RESEARCH_RESUME:START -->"
RESUME_END = "<!-- SOURCE_RESEARCH_RESUME:END -->"
```

Insert the markers once around the changing `Current phase` content. Preserve all stable methodology/history byte-for-byte outside the markers. Write `Canonical checkpoint: current Git HEAD` and the audited coordinator input SHA; the actual checkpoint SHA is obtained from `git log`, avoiding impossible self-reference.

- [ ] **Step 4: Build the canonical checkpoint and run final verification**

Run: `.venv/bin/python -m qbank.cli checkpoint-source-research --input-commit HEAD`

Run: `.venv/bin/python -m pytest tests/test_source_packet_population.py tests/test_source_document_registry.py tests/test_generation_source_state.py tests/test_source_research_coordinator.py tests/test_source_research_migration.py tests/test_source_research_checkpoint.py -q`

Run: `.venv/bin/python -m pytest -q`

Run: `git diff --check`

Expected: all tests PASS; repeated checkpoint command produces no diff.

- [ ] **Step 5: Verify frozen layers and commit final implementation checkpoint**

Run: `git diff -- research/qgen/source_packet_population_srb_*.json research/qgen/source_packet_plan.json research/qgen/question_generation_manifest.json research/scope`

Expected: no source populations or frozen inputs changed.

```bash
git add scripts/qbank/source_research_checkpoint.py scripts/qbank/source_research_coordinator.py scripts/qbank/cli.py tests/test_source_research_checkpoint.py MEMORY.md reports/source_research_integration_audit.json
git commit -m "qgen: checkpoint accelerated source research"
```

Final resume check: `git status --short`, `git log -7 --oneline`, and the canonical JSON validators must identify Task 6 as complete and source research as the next authorized stage.
