# Chapter-Staged Global-Contrast Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement deterministic fail-closed contracts for chapter-anchored, globally contrastive, staged MCQ construction and prove them with a three-item clinical micro-pilot.

**Architecture:** A focused Python module resolves immutable anchor lineage, builds the whole-book study-unit index, validates reusable evidence-bound contrast edges, and validates every fingerprinted generation stage. A separate micro-pilot gate binds exact generated items to a fresh independent review and accepts only 3/3 with all defect counters at zero.

**Tech Stack:** Python 3.11, JSON, pytest.

**Spec:** `docs/superpowers/specs/2026-08-31-chapter-anchored-global-contrast-qbank-design.md`

## Global Constraints

- Preserve V1, V2, and V2.1 artifacts and frozen upstream scope/allocation artifacts byte-for-byte.
- Use deterministic code for IDs, joins, fingerprints, stage order, provenance, option-shape checks, and duplicate checks.
- Use semantic judgment only for confusability, medical discriminants, item design, and independent review.
- Use one clinical anchor chapter and exactly diagnosis, investigation/interpretation, and management/next-best-step items.
- Do targeted evidence research only for exact pilot claims; do not mark pending canonical source packets READY.
- Stop after root-cause attribution if any micro item fails; do not regenerate repeatedly.

---

### Task 1: Generic staged-generation contracts

**Files:**
- Create: `scripts/qbank/chapter_staged_generation.py`
- Create: `tests/test_chapter_staged_generation.py`

**Interfaces:**
- Produces `build_global_study_unit_index(root) -> list[dict]` and `resolve_chapter_anchor(root, allocation_address_id, primary_mcc_objective, primary_physician_activity, primary_learner_decision) -> dict`.
- Produces `validate_contrast_library(root, artifact, evidence_packet) -> dict` and `retrieve_global_contrasts(root, anchor_study_unit_id, decision_context, semantic_candidate_ids, library, evidence_packet) -> dict`.
- Produces `validate_staged_item(root, item, library, evidence_packet) -> dict` and `validate_micro_pilot(root, artifact, library, evidence_packet, verification) -> dict`.

- [ ] **Step 1: Write failing behavior tests**

```python
def test_anchor_resolution_joins_frozen_allocation_tn_and_mcc_lineage():
    anchor = resolve_chapter_anchor(REPO, "SU-C-21", "14", "Assessment/Diagnosis", "Differentiate ACS from other dangerous chest-pain causes.")
    assert anchor["anchor_source_node_ids"] == ["C.S06.T02", "C.S06.T03"]
    assert anchor["anchor_tn_pages"] == "C30-C39"

def test_matrix_fails_before_options_when_three_validated_competitors_do_not_exist():
    item = valid_staged_item()
    item["contrastive_evidence_matrix"]["competitors"] = item["contrastive_evidence_matrix"]["competitors"][:2]
    with pytest.raises(ChapterStagedGenerationError, match="three validated competitors"):
        validate_staged_item(REPO, item, library(), evidence())
```

Cover canonical anchor mismatch, noncanonical MCC ID/activity, non-global index ordering, unvalidated/stale edge reuse, lexical-only retrieval, stage-fingerprint breakage, nonfresh blind solver/reviewer/verifier, options existing before matrix approval, unplanned distractor, weak fifth option, assembly rewrite, failed context/cover/cue/plan/anchor checks, rationale claim expansion, and duplicate micro items.

- [ ] **Step 2: Run RED**

Run: `PYTHONPATH=scripts /Users/annabeketova/Desktop/code/mccqe/.venv/bin/pytest -q tests/test_chapter_staged_generation.py`

Expected: collection failure because `qbank.chapter_staged_generation` does not exist.

- [ ] **Step 3: Implement the minimum generic validators**

Use canonical JSON joins, exact set/sequence checks, SHA-256 fingerprints, and explicit `PASS`/`VALIDATED` gates. Require at least three matrix competitors; each constructed distractor must instantiate one validated edge; the optional fourth distractor must pass the same gate.

- [ ] **Step 4: Run GREEN and regression focus**

Run: `PYTHONPATH=scripts /Users/annabeketova/Desktop/code/mccqe/.venv/bin/pytest -q tests/test_chapter_staged_generation.py tests/test_source_ready_generation_pilot.py`

Expected: PASS.

### Task 2: ACS clinical three-item micro-pilot

**Files:**
- Create: `research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.evidence.json`
- Create: `research/qgen/chapter_global_contrast_library.json`
- Create: `research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.staged.json`
- Create: `reports/qgen_med_007_chapter_review_micro_3_independent_verification.json`
- Test: `tests/test_chapter_staged_generation.py`

**Interfaces:**
- Consumes immutable `SU-C-21`, MCC objective `14`, the whole-book study-unit index, and exact targeted source claims.
- Produces three accepted Chapter Review items and reusable directional contrast edges.

- [ ] **Step 1: Add a failing canonical-artifact test**

```python
def test_committed_acs_micro_pilot_reaches_zero_defect_three_of_three_gate():
    result = validate_micro_pilot(REPO, staged(), contrasts(), evidence(), verification())
    assert result["micro_items_passed"] == 3
    assert all(value == 0 for value in result["defect_counts"].values())
```

- [ ] **Step 2: Run RED**

Expected: failure because the micro artifacts do not exist.

- [ ] **Step 3: Create targeted evidence and staged items**

Anchor all three to Cardiology/`SU-C-21`; use one diagnosis/differential, one investigation/interpretation, and one management/next-best-step decision. Record why each new claim was required, exact source locators, `TN_ALIGNMENT`, blind-solver output, matrix rows, separate distractor construction, adversarial review, assembly checks, and rationales.

- [ ] **Step 4: Obtain fresh independent review and bind it to exact bytes**

Require all listed quality dimensions to pass and every defect counter to be zero. If a reviewer rejects an item, record the root cause and stop without another generation cycle.

- [ ] **Step 5: Run focused validation**

Run: `PYTHONPATH=scripts /Users/annabeketova/Desktop/code/mccqe/.venv/bin/pytest -q tests/test_chapter_staged_generation.py`

Expected: PASS.

### Task 3: Successful-pilot handoff and final verification

**Files:**
- Create only on 3/3: `docs/superpowers/plans/2026-09-01-acs-10-item-chapter-review-pilot.md`
- Modify only if resume state materially changes: `MEMORY.md`

**Interfaces:**
- Consumes the validated micro-pilot result.
- Produces a nonexecuted 10-item pilot plan; it does not scale generation.

- [ ] **Step 1: Write the 10-item pilot plan only after 3/3**

Specify a balanced diagnosis, investigation, management, and applicable communication/professional mix, with the same staged gates and a stop condition before scale.

- [ ] **Step 2: Verify immutable artifacts and repository formatting**

Run byte comparisons against commit `1cbfca5` for all V1/V2/V2.1 and frozen scope/allocation paths, then run `git diff --check`.

- [ ] **Step 3: Run the full suite exactly once after production changes**

Run: `PYTHONPATH=scripts /Users/annabeketova/Desktop/code/mccqe/.venv/bin/pytest -q`

Expected: PASS.

- [ ] **Step 4: Commit implementation and pilot artifacts**

```bash
git add scripts/qbank/chapter_staged_generation.py tests/test_chapter_staged_generation.py research/qgen/chapter_global_contrast_library.json research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.evidence.json research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.staged.json reports/qgen_med_007_chapter_review_micro_3_independent_verification.json docs/superpowers/plans/2026-09-01-chapter-staged-global-contrast-implementation.md docs/superpowers/plans/2026-09-01-acs-10-item-chapter-review-pilot.md MEMORY.md
git commit -m "feat: validate staged chapter global-contrast generation"
```
