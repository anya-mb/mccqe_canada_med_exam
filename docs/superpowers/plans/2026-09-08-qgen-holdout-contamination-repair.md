# QGEN Holdout Contamination Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the Fresh Holdout 24 contamination path, centralize generation readiness, replay the same 24 as development regression data, and prepare an unconsumed next-holdout eligibility inventory.

**Architecture:** Add one lifecycle module whose `assert_generation_ready` function is the only gate immediately before a generator callback. Add a deterministic forensic/replay builder that reads the preserved H24 artifacts, emits canonical lifecycle/accounting reports, and exercises the same gate for the historical AOM control. Existing clinical content and the frozen opportunity roster remain byte-identical.

**Tech Stack:** Python 3, pytest, canonical JSON artifacts, SHA-256 content pinning.

**Spec:** `/Users/annabeketova/.codex/attachments/c37feca6-15ab-42af-9fc7-b54453aa6b04/pasted-text.txt`

## Global Constraints

- Do not create commits.
- Do not alter historical frozen artifacts or clinical content.
- Write tests before production changes and observe the required failures.
- Do not consume a new holdout.
- Run focused verification, then one full canonical suite after the final shared-code state.

---

### Task 1: Executable lifecycle precondition

**Files:**
- Create: `scripts/qbank/generation_lifecycle.py`
- Create: `tests/test_generation_lifecycle.py`

**Interfaces:**
- Produces: `assert_generation_ready(context: dict) -> dict` and `execute_generation(context: dict, generator: Callable) -> Any`.
- Rejects every non-approved, unpinned, unsafe, insufficient, or unfrozen upstream state before invoking the callback.

- [ ] Write the eleven required impossible-state tests plus a positive control using literal contexts.
- [ ] Run the tests and verify they fail because the lifecycle module is absent.
- [ ] Implement the minimal centralized validator and callback wrapper.
- [ ] Run the focused tests and verify all pass.

### Task 2: Reporting contract and contaminated-24 replay

**Files:**
- Create: `scripts/qbank/holdout_contamination_repair.py`
- Modify: `tests/test_fresh_holdout_24.py`
- Create: `research/qgen/holdout/fresh_holdout_24_contamination_classification.json`
- Create: `research/qgen/holdout/fresh_holdout_24_lifecycle_trace.json`
- Create: `research/qgen/holdout/fresh_holdout_24_regression_replay.json`
- Create: `reports/qgen_holdout_contamination_diagnosis.json`

**Interfaces:**
- Consumes: preserved H24 roster, feature maps, audit, reviews, retrieval, items, and their hashes.
- Produces: one terminal lifecycle record per opportunity, canonical metric definitions, twelve draft classifications, seed and contract taxonomies, and regression metrics.

- [ ] Add tests for canonical metric semantics, mutual/exhaustive terminal accounting, and the forbidden `contrast_ready=false/generated=true` state.
- [ ] Run the tests and verify the intended failures.
- [ ] Implement deterministic reconstruction and report composition without rewriting source artifacts.
- [ ] Replay all 24 through `execute_generation`; confirm zero callbacks execute.
- [ ] Verify the physical twelve drafts are preserved and classified as premature invalid pipeline output.

### Task 3: Historical controls and next-holdout preparation

**Files:**
- Modify: `scripts/qbank/holdout_contamination_repair.py`
- Modify: `tests/test_fresh_holdout_24.py`
- Create: `research/qgen/holdout/next_fresh_holdout_eligibility_inventory.json`

**Interfaces:**
- Consumes: independently reviewed AOM development artifacts and the existing eligible inventory.
- Produces: AOM lifecycle proof plus an eligibility-only, unselected inventory for a future holdout.

- [ ] Add failing tests that the AOM control passes the centralized gate and the new inventory contains no selected cases or seed inspection.
- [ ] Implement the artifact adapters and deterministic inventory writer.
- [ ] Run focused safety regression tests.

### Task 4: Final verification and resume state

**Files:**
- Modify: `MEMORY.md`
- Create: `reports/qgen_holdout_contamination_test_results.json`

**Interfaces:**
- Produces: verified milestone status and exact next step.

- [ ] Run all focused QGEN lifecycle, retrieval, anchor, and AOM tests.
- [ ] Run the full canonical suite once at final shared-code state and isolate only a known pre-existing failure if present.
- [ ] Run `git diff --check` and the canonical copyright audit over new artifacts.
- [ ] Recompute all report counts from artifacts, update only `QGEN_ARCHITECTURE_RESUME`, and verify hashes/status again.
