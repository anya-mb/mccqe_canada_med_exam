# Chapter Option-Realization Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every production behavior and superpowers:verification-before-completion before commit. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the remaining option-cue failures without changing chapter ownership, learner decisions, contrast concepts, or evidence.

**Architecture:** Preserve schema 1.0 failed artifacts byte-for-byte. Add a schema 1.1 option-realization stage between validated semantic options and assembly, followed by deterministic surface checks and a fresh semantic parallel-set review. Generate a derivative ACS retry using the existing matrices, contrast edges, and evidence; validate it with a new independent verifier.

**Tech Stack:** Python 3.11, JSON, pytest.

**Spec:** `docs/superpowers/specs/2026-08-31-chapter-anchored-global-contrast-qbank-design.md`

## Global Constraints

- Do not modify prior pilot, V1/V2/V2.1, frozen scope, allocation, Toronto Notes, MCC, evidence, source-packet, or contrast-library artifacts.
- Surface realization may change wording and answer position only; semantic identities, evidence refs, discriminators, and single-best-answer status remain exact.
- Deterministic checks cover duplicate text, gross key-length outliers, structured grammatical-form mismatch, repeated exact phrases, and batch position balance.
- Semantic review covers specificity, odd-one-out, option category, convergence, clang exploitability, natural parallelism, and meaning preservation.
- Run the full suite once from a standalone verification clone with required ignored local dependencies, so linked-worktree environment assumptions cannot create false regressions.

---

### Task 1: Option-realization and cue-review contracts

**Files:**
- Modify: `scripts/qbank/chapter_staged_generation.py`
- Modify: `tests/test_chapter_staged_generation.py`

**Interfaces:**
- Produce `find_option_text_cues(stem, options) -> list[str]` for deterministic surface defects.
- Extend `validate_staged_item(...)` to accept legacy schema 1.0 unchanged and require schema 1.1 `option_realization` plus `parallel_option_set_review` before assembly.

- [ ] **Step 1: Write failing tests for each required behavior**

```python
def test_option_text_checks_reject_duplicate_nonparallel_and_key_only_phrase():
    assert "DUPLICATE_OPTION_TEXT" in find_option_text_cues("...", duplicate_options)
    assert "NONPARALLEL_GRAMMATICAL_FORM" in find_option_text_cues("...", nonparallel_options)
    assert "KEY_ONLY_STEM_PHRASE" in find_option_text_cues(stem_with_unique_key_phrase, options)

def test_schema_1_1_semantic_review_rejects_category_or_convergence_failure():
    item = valid_schema_1_1_item()
    item["parallel_option_set_review"]["semantic_checks"]["convergence"] = "FAIL"
    with pytest.raises(ChapterStagedGenerationError, match="semantic cue review"):
        validate_staged_item(REPO, item, library(), evidence())
```

- [ ] **Step 2: Run RED**

Run: `PYTHONPATH=scripts /Users/annabeketova/Desktop/code/mccqe/.venv/bin/pytest -q tests/test_chapter_staged_generation.py`

Expected: import or validation failures because schema 1.1 realization behavior does not exist.

- [ ] **Step 3: Implement the minimum schema 1.1 contract**

Keep schema 1.0 validation intact. Bind each realized surface option to its semantic key or contrast ID, exact evidence refs, common option dimension, common grammatical form, and explicit meaning-preservation PASS. Recompute deterministic findings and require a fresh review with all semantic cue dimensions PASS before assembly.

- [ ] **Step 4: Run GREEN**

Run the Task 1 focused file and require zero failures.

### Task 2: Derivative ACS retry and fresh semantic review

**Files:**
- Create: `research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.option-retry-1.staged.json`
- Create: `reports/qgen_med_007_chapter_review_micro_3_option_retry_1_cue_review.json`
- Create: `reports/qgen_med_007_chapter_review_micro_3_option_retry_1_independent_verification.json`
- Modify: `tests/test_chapter_staged_generation.py`

**Interfaces:**
- Consume the existing evidence packet and 12 validated contrast edges unchanged.
- Produce the same three learner decisions and item types with concise natural surface options and distinct key positions.

- [ ] **Step 1: Add a failing derivative-lineage test**

```python
def test_committed_option_retry_passes_three_of_three_zero_defect_gate():
    result = validate_micro_pilot(REPO, retry(), contrasts(), evidence(), verification())
    assert result["micro_items_passed"] == 3
    assert all(count == 0 for count in result["defect_counts"].values())
```

- [ ] **Step 2: Run RED**

Expected: failure because derivative artifacts do not exist.

- [ ] **Step 3: Build the derivative without changing prior artifacts**

Reuse the exact anchors, learner decisions, matrices, evidence refs, and contrast IDs. Remove only item 2's distractor-by-distractor negative checklist, realize all option sets as natural parallel phrases, and assign three distinct answer positions. Rebind every downstream fingerprint.

- [ ] **Step 4: Obtain fresh reviews**

Use one new cue reviewer for the realized option sets and a different new independent verifier for all required medical and assessment dimensions. Record exact-byte lineage and zero defects.

- [ ] **Step 5: Run focused validation**

Run: `PYTHONPATH=scripts /Users/annabeketova/Desktop/code/mccqe/.venv/bin/pytest -q tests/test_chapter_staged_generation.py tests/test_source_ready_generation_pilot.py`

Expected: zero failures.

### Task 3: Verification, resume state, and commit

**Files:**
- Modify: `MEMORY.md`
- Create on 3/3 only: `docs/superpowers/plans/2026-09-01-acs-10-item-chapter-review-pilot.md`

**Interfaces:**
- Produce a clean committed checkpoint and a nonexecuted 10-item pilot plan only after 3/3.

- [ ] **Step 1: Verify frozen and prior artifact bytes**

Compare all protected paths to commit `de247e9735e5f323bcfc3f603be41ebab6db8af3`; require no differences.

- [ ] **Step 2: Prepare a standalone verification clone**

Clone the final branch into a temporary directory, point its `main` branch at the final candidate commit, and provide ignored local `config/project.local.json` plus `derived/toronto-notes-2025` from the saved project checkout. This reproduces the normal repository assumptions without changing production tests.

- [ ] **Step 3: Run the full suite once**

Run: `PYTHONPATH=scripts /Users/annabeketova/Desktop/code/mccqe/.venv/bin/pytest -q`

Expected: zero failures and zero errors.

- [ ] **Step 4: Commit and verify clean state**

Stage only the option-repair code, tests, derivative artifacts, diagnosis, plan, 10-item plan, and resume-state update. Run `git diff --check`, commit with `fix: add cue-safe option realization`, and require `git status --short` to be empty.
