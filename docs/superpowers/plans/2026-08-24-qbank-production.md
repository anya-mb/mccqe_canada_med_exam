# MCCQE Qbank Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the private Toronto Notes index, six curriculum manifests, a fully verified Cardiology pilot, approximately 1,000 QA-passed questions per discipline, verified production JSON, and a tested React/Firebase study application.

**Architecture:** Python remains a deterministic filesystem controller while isolated Codex-native agents perform source research, original question writing, blind solving, and rationale auditing. Work advances through five-question generation micro-batches, per-question verification, chapter locks, discipline audits, and a global audit; only verified records cross the transactional public-export boundary.

**Tech Stack:** Python 3.11+, PyMuPDF, Poppler, optional local Tesseract OCR, JSON Schema Draft 2020-12, pytest, Codex-native web research, React, TypeScript, Vite, Vitest, Testing Library, Firebase Hosting.

**Spec:** `docs/superpowers/specs/2026-08-24-qbank-production-design.md`

## Global Constraints

- Toronto Notes 2025, 41st Edition is the primary curriculum/study anchor; current authoritative Canadian guidance determines current clinical answers.
- The PDF, extracted/OCR text, absolute source paths, source packets, and internal verification artifacts remain private and Git-ignored.
- Never copy Toronto Notes prose, questions, tables, diagrams, cases, or mnemonics into question content.
- `CODEX_NATIVE` is the default; Python must not call an external LLM API or require an API key.
- Generate at most five questions per Codex context and blind-verify one question per isolated context.
- The Cardiology pilot counts toward Medicine's approximately 1,000-question target.
- Accuracy overrides numeric targets; every shortfall must be reported.
- Commit after every meaningful code milestone and every completed chapter/discipline checkpoint.
- Do not deploy Firebase Hosting without a separate explicit user instruction.

---

### Task 1: Private ingestion contracts and configuration

**Files:**
- Modify: `pyproject.toml`
- Modify: `config/project.json`
- Modify: `schemas/project.schema.json`
- Create: `schemas/source-page.schema.json`
- Create: `schemas/source-index.schema.json`
- Create: `tests/fixtures/valid/source-page.json`
- Create: `tests/fixtures/valid/source-index.json`
- Create: `tests/test_ingestion.py`
- Modify: `tests/test_schemas.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `validate_source(root: Path, config: dict) -> SourceReport`.
- Produces: `IngestionConfig`, canonical private page/index schemas, and ignored `derived/toronto-notes-2025/` paths.

- [ ] **Step 1: Write failing schema/config tests**

```python
def test_project_config_defines_private_ingestion():
    config = load_config(REPO_ROOT)
    assert config["ingestion"]["derived_root"] == "derived/toronto-notes-2025"
    assert config["ingestion"]["minimum_text_characters"] >= 100
    assert config["ingestion"]["ocr_mode"] == "fallback"

def test_source_page_rejects_missing_source_hash():
    page = read_json(FIXTURES / "source-page.json")
    page.pop("source_sha256")
    with pytest.raises(SchemaValidationError):
        validate_instance(REPO_ROOT, "source-page", page)
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `python -m pytest tests/test_ingestion.py tests/test_schemas.py -q`

Expected: failures for missing ingestion config and source schemas.

- [ ] **Step 3: Add deterministic ingestion configuration and schemas**

Add `pymupdf>=1.26,<2` to project dependencies. Define `derived_root`, `minimum_text_characters`, `minimum_printable_ratio`, `render_dpi`, and `ocr_mode`. Page records require PDF page, printed page, chapter identity, headings, text, extraction method, quality flags, source hash, and text hash. Index records require the validated source identity, page count, generation tool version, and exactly one page locator per physical page.

- [ ] **Step 4: Extend schema catalog validation**

Add `source-page` and `source-index` to the CLI schema catalog and prove both valid fixtures pass while extra fields, missing hashes, invalid methods, and non-finite quality values fail.

- [ ] **Step 5: Run focused and full tests**

Run: `python -m pytest tests/test_ingestion.py tests/test_schemas.py tests/test_cli.py -q`

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock config/project.json schemas tests .gitignore
git commit -m "feat: define private Toronto Notes ingestion contracts"
```

### Task 2: Deterministic PDF extraction and page indexing

**Files:**
- Create: `scripts/qbank/ingestion.py`
- Create: `scripts/qbank/source_pages.py`
- Modify: `scripts/qbank/cli.py`
- Modify: `tests/test_ingestion.py`
- Create: `tests/fixtures/ingestion/sample.pdf`
- Modify: `README.md`

**Interfaces:**
- Produces: `ingest_source(root: Path, *, force: bool = False) -> IngestionReport` and CLI `qbank ingest-source`.
- Writes: private `book.json`, `page_index.json`, `headings.json`, and page JSON records atomically.

- [ ] **Step 1: Write failing extraction tests**

```python
def test_ingest_source_writes_one_hashed_record_per_page(project_with_sample_pdf):
    report = ingest_source(project_with_sample_pdf)
    assert report.pages_written == 3
    index = read_json(report.index_path)
    assert [page["pdf_page"] for page in index["pages"]] == [1, 2, 3]
    assert all(page["text_sha256"] for page in index["pages"])

def test_ingestion_is_idempotent(project_with_sample_pdf):
    first = ingest_source(project_with_sample_pdf)
    second = ingest_source(project_with_sample_pdf)
    assert second.pages_written == 0
    assert first.index_sha256 == second.index_sha256
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `python -m pytest tests/test_ingestion.py -q`

Expected: import or missing-command failures.

- [ ] **Step 3: Implement embedded-text extraction**

Open the already integrity-validated PDF with PyMuPDF, normalize line endings and Unicode deterministically, compute page text hashes, infer printed page labels without changing physical page numbering, and write to a same-parent staging directory before atomic replacement. Never log extracted text.

- [ ] **Step 4: Implement quality flags and heading candidates**

Compute character count, printable ratio, replacement-character count, and heading candidates. Flag `LOW_TEXT`, `LOW_PRINTABLE_RATIO`, `PAGE_LABEL_UNCERTAIN`, and `HEADING_CONTINUITY` without attempting OCR in this task.

- [ ] **Step 5: Add CLI and interruption safety tests**

Prove `qbank ingest-source` refuses a source hash mismatch, leaves a prior complete index intact after a simulated write failure, and does not follow symlink ancestors.

- [ ] **Step 6: Run focused/full verification and ingest the real PDF**

Run: `python -m pytest tests/test_ingestion.py tests/test_cli.py -q`

Run: `python -m pytest -q`

Run: `qbank ingest-source`

Expected: 1,595 indexed physical pages and a schema-valid private index.

- [ ] **Step 7: Commit code and public documentation only**

```bash
git add scripts/qbank tests README.md
git commit -m "feat: index private Toronto Notes source"
```

### Task 3: Chapter boundaries, visual QA, and OCR fallback

**Files:**
- Create: `scripts/qbank/chapter_index.py`
- Create: `scripts/qbank/ocr.py`
- Create: `scripts/qbank/ingestion_audit.py`
- Modify: `scripts/qbank/ingestion.py`
- Modify: `scripts/qbank/cli.py`
- Create: `tests/test_chapter_index.py`
- Create: `tests/test_ingestion_audit.py`
- Create: `reports/ingestion_audit.md`
- Modify: `reports/milestones.md`

**Interfaces:**
- Produces: `build_chapter_index(...)`, `audit_ingestion(...)`, CLI `qbank audit-ingestion`, and private per-chapter manifests.

- [ ] **Step 1: Write failing boundary and OCR-policy tests**

```python
def test_expected_chapter_ranges_cover_declared_pages_without_overlap(index):
    chapters = build_chapter_index(index, EXPECTED_CHAPTERS)
    assert chapters["C"].pdf_pages == (91, 174)
    assert_no_overlapping_ranges(chapters.values())

def test_ocr_runs_only_for_flagged_pages(fake_ocr, index):
    audit_ingestion(index, ocr=fake_ocr)
    assert fake_ocr.page_numbers == index.flagged_page_numbers
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_chapter_index.py tests/test_ingestion_audit.py -q`

- [ ] **Step 3: Implement expected chapter catalog and boundary validation**

Encode the physical/TN page ranges specified by the six manifest prompts, including supplemental chapters. Resolve chapter/printed-page mappings through the physical index and fail on missing, duplicate, reversed, or overlapping declared pages.

- [ ] **Step 4: Implement visual audit queue and local OCR fallback**

Render every TOC, chapter boundary, and quality-flagged page at the configured DPI. Record human/Codex visual decisions separately from extracted text. Invoke local Tesseract only for pages explicitly marked `OCR_REQUIRED`; retain embedded and OCR hashes and select one canonical extraction with a recorded reason.

- [ ] **Step 5: Audit the real index**

Visually inspect all TOC and boundary pages plus every flagged page. Require 1,595 accounted pages, exact declared chapter endpoints, stable printed-page mappings, and zero unresolved critical flags.

- [ ] **Step 6: Write milestone evidence and commit**

Record source hash, extraction tool versions, counts by extraction method, flagged/resolved counts, chapter coverage, and private-output exclusions in `reports/ingestion_audit.md` and `reports/milestones.md`.

```bash
git add scripts/qbank tests reports README.md
git commit -m "feat: validate Toronto Notes chapter index"
```

### Task 4: Current MCC scope and authoritative-source registry

**Files:**
- Create: `scripts/qbank/research_packets.py`
- Create: `schemas/source-packet.schema.json`
- Create: `schemas/mcc-scope.schema.json`
- Create: `references/approved_domains.json`
- Create: `references/mcc_scope.json`
- Create: `tests/test_research_packets.py`
- Modify: `tests/test_schemas.py`
- Modify: `scripts/qbank/cli.py`
- Create: `reports/mcc_scope.md`

**Interfaces:**
- Produces: validated claim packets with source URL, organization, tier, publication/update date, accessed date, locator, supported claim, and archived metadata.

- [ ] **Step 1: Write failing source-packet policy tests**

Test rejection of invented/unknown reference IDs, non-HTTPS URLs, fragments, userinfo, tracking queries, unapproved domains without review metadata, empty claim locators, future access dates, and source packets created after their questions.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_research_packets.py tests/test_schemas.py -q`

- [ ] **Step 3: Implement source-packet validation and registry merge**

Normalize stable references using existing registry rules, preserve claim-level support separately, and require high-risk packets to record corroboration status.

- [ ] **Step 4: Browse and record current MCC scope**

Use current official MCC pages to record public examination format, Objectives, Blueprint/Study Smarter scope, retrieval date, and exact locators. Store paraphrased scope metadata and URLs, not protected item content.

- [ ] **Step 5: Validate, document, and commit**

Run focused and full tests, validate every stored URL/locator, update `reports/mcc_scope.md`, then commit.

```bash
git add scripts/qbank schemas references tests reports
git commit -m "feat: validate Codex-native medical source packets"
```

### Task 5: Six complete discipline manifests

**Files:**
- Modify: `schemas/manifest.schema.json`
- Create: `scripts/qbank/manifest_builder.py`
- Modify: `scripts/qbank/manifests.py`
- Modify: `scripts/qbank/cli.py`
- Modify: `tests/test_manifests.py`
- Create: `manifests/medicine.json`
- Create: `manifests/pediatrics.json`
- Create: `manifests/obgyn.json`
- Create: `manifests/surgery.json`
- Create: `manifests/psychiatry.json`
- Create: `manifests/phelo.json`
- Create: `reports/medicine_manifest.md`
- Create: `reports/pediatrics_manifest.md`
- Create: `reports/obgyn_manifest.md`
- Create: `reports/surgery_manifest.md`
- Create: `reports/psychiatry_manifest.md`
- Create: `reports/phelo_manifest.md`
- Modify: `reports/milestones.md`

**Interfaces:**
- Produces: six exact discipline identities and deterministic 40-50-ID macro-batches whose totals equal their manifest planning targets.

- [ ] **Step 1: Tighten manifest tests before content creation**

Require ordered chapters/sections/subsections, page-range objects, MCC objective IDs, priority, activity/dimension mixes, high-risk research flags, coverage gaps, macro-batches of 40-50 except one documented tail, and globally unique permanent IDs.

- [ ] **Step 2: Run tests and confirm existing schema is insufficient**

Run: `python -m pytest tests/test_manifests.py tests/test_schemas.py -q`

- [ ] **Step 3: Implement deterministic manifest builder**

Build section/page structures only from the validated private chapter index. Allocation and ID expansion are deterministic; no medical content is generated by Python.

- [ ] **Step 4: Research and write the Medicine and Pediatrics manifests**

Follow `manifest_medicine.md` and `manifest_pediatrics.md`, preserve actual Toronto Notes order, map current MCC scope, allocate approximately 1,000 IDs each, and record Canadian source indexes needed per section.

- [ ] **Step 5: Research and write OBGYN and Surgery manifests**

Follow their prompt targets and exact chapter order, preserve GY-before-OB IDs, emphasize high-risk pregnancy guidance and graduate-level surgical decisions.

- [ ] **Step 6: Research and write Psychiatry and PHELO manifests**

Follow their prompt targets, distinguish provincial legal rules, and mark all screening, public-health, legal, and rapidly changing guidance for fresh research.

- [ ] **Step 7: Validate all six together and generate reports**

Run: `qbank validate-manifests`

Run: `qbank validate-project`

Expected: `GENERATION_READY: six valid manifests`, approximately 6,000 planned unique IDs, and zero mapping collisions.

- [ ] **Step 8: Commit**

```bash
git add schemas scripts/qbank tests manifests reports
git commit -m "feat: add six Toronto Notes curriculum manifests"
```

### Task 6: Five-question micro-batch queue and artifact contracts

**Files:**
- Modify: `schemas/job.schema.json`
- Create: `schemas/generation-report.schema.json`
- Modify: `scripts/qbank/jobs.py`
- Create: `scripts/qbank/microbatches.py`
- Modify: `scripts/qbank/cli.py`
- Modify: `tests/test_jobs.py`
- Create: `tests/test_microbatches.py`
- Modify: `config/project.json`
- Modify: `README.md`

**Interfaces:**
- Produces: `split_macro_batch(batch, size=5) -> tuple[MicroBatch, ...]`, queue types `RESEARCH`, `GENERATE`, `BLIND_SOLVE`, `RATIONALE_REVIEW`, `CHAPTER_AUDIT`, and deterministic artifact paths.

- [ ] **Step 1: Write failing micro-batch tests**

```python
def test_fifty_ids_split_into_ten_stable_microbatches():
    parts = split_macro_batch(make_batch(50), size=5)
    assert [len(part.question_ids) for part in parts] == [5] * 10
    assert parts[0].microbatch_id.endswith("-M01")
    assert parts[-1].microbatch_id.endswith("-M10")
```

Also prove no ID overlap, deterministic byte output, attempt limits, and verification job fan-out of exactly one question.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_microbatches.py tests/test_jobs.py -q`

- [ ] **Step 3: Implement queue/artifact expansion**

Research precedes generation, generation precedes candidate validation, and one candidate produces two sequential verification jobs. Queue transitions remain atomic and concurrency-safe.

- [ ] **Step 4: Generate the full durable queue and commit**

Run full tests, create pending jobs from all six manifests, regenerate progress, verify counts, and commit deterministic queue definitions and documentation without committing volatile running state.

```bash
git add config schemas scripts/qbank tests README.md reports
git commit -m "feat: queue five-question Codex production tasks"
```

### Task 7: Cardiology pilot source packets

**Files:**
- Create: `batches/MED-CARD-B01/batch_spec.json`
- Create: `batches/MED-CARD-B01/source_packet.json`
- Create: `batches/MED-CARD-B01/references.json`
- Create: `batches/MED-CARD-B01/research_report.md`
- Modify: `references/registry.json`
- Modify: `reports/progress.json`
- Modify: `reports/progress.md`
- Modify: `reports/milestones.md`

**Interfaces:**
- Consumes: validated Cardiology index mappings, MCC scope, approved research-packet schema, and first Cardiology macro-batch IDs.
- Produces: claim packets for 40-50 requested pilot items, grouped into no more than five claims per Codex research context.

- [ ] **Step 1: Inspect assigned Toronto Notes Cardiology sections**

Read the exact indexed pages for each micro-batch and write paraphrased topic outlines without copying source prose.

- [ ] **Step 2: Research current authoritative sources before questions**

Browse Canadian Cardiovascular Society, Hypertension Canada, Thrombosis Canada, Government of Canada, and other authoritative sources required by the assigned concepts. Record exact claim locators and retrieval dates; drop claims without accessible support.

- [ ] **Step 3: Validate every source packet and registry merge**

Run schema, URL, locator, high-risk corroboration, TN mapping, and MCC scope validation. Confirm packet timestamps precede generation.

- [ ] **Step 4: Commit the pilot research checkpoint**

```bash
git add batches/MED-CARD-B01 references reports
git commit -m "content: ground Cardiology pilot claims"
```

### Task 8: Cardiology pilot candidate generation

**Files:**
- Create: `batches/MED-CARD-B01/questions.candidate.json`
- Create: `batches/MED-CARD-B01/generation_report.json`
- Create: `candidates/MED-CARD-*.json`
- Modify: `reports/progress.json`
- Modify: `reports/progress.md`
- Modify: `reports/milestones.md`

**Interfaces:**
- Produces: original schema-valid `STRUCTURE_PASS` candidates, at most five per isolated generation context.

- [ ] **Step 1: Generate each five-item micro-batch from its source packet**

Use predetermined IDs, five homogeneous options, one clear lead-in, detailed rationales, four distractor explanations, exact TN study anchors, MCC mappings, risk flags, and reference IDs. Do not generate replacements from memory when a claim is dropped.

- [ ] **Step 2: Validate every item before candidate storage**

Require schema validity, five options, key membership, rationale completeness, reference existence, mapping validity, no copied TN phrase, and legal lifecycle transition.

- [ ] **Step 3: Run pilot duplicate/style checks**

Reject exact hashes and quarantine strong lexical/shared-vignette matches. Record requested, generated, discarded, and reason counts.

- [ ] **Step 4: Commit candidate checkpoint**

```bash
git add batches/MED-CARD-B01 candidates reports
git commit -m "content: generate Cardiology pilot candidates"
```

### Task 9: Cardiology blind verification and rationale audit

**Files:**
- Create: `blind/MED-CARD-*.json`
- Create: `blind_verification/MED-CARD-*.json`
- Create: `rationale_verification/MED-CARD-*.json`
- Create: `verified/medicine/cardiology/MED-CARD-*.json`
- Create: `quarantine/MED-CARD-*.json`
- Create: `rejected/MED-CARD-*.json`
- Modify: `reports/progress.json`
- Modify: `reports/progress.md`
- Modify: `reports/milestones.md`

**Interfaces:**
- Consumes: one candidate and its permitted source candidates per isolated verification context.
- Produces: independently solved blind result, claim-level rationale audit, and legal lifecycle status.

- [ ] **Step 1: Build and mechanically inspect blind packets**

Run the automated forbidden-field test across every packet and confirm answer/rationale fields are absent.

- [ ] **Step 2: Blind-solve every candidate independently**

Reopen the mapped TN section and current sources, return one independent answer, confidence, defensible alternatives, sufficiency, support, and concerns. Quarantine every mismatch or uncertainty.

- [ ] **Step 3: Audit full rationales only after key agreement**

Verify every material claim, distractor, locator, Canadian context, currentness, ambiguity, and MCC depth. Route substantive defects to revision/rejection; every revision repeats blind solving.

- [ ] **Step 4: Run deterministic verification tests and commit**

```bash
git add blind blind_verification rationale_verification verified quarantine rejected reports
git commit -m "content: independently verify Cardiology pilot"
```

### Task 10: Cardiology chapter audit and scale gate

**Files:**
- Create: `scripts/qbank/duplicates.py`
- Create: `scripts/qbank/audit.py`
- Create: `schemas/chapter-audit.schema.json`
- Create: `tests/test_duplicates.py`
- Create: `tests/test_audit.py`
- Create: `reports/medicine/cardiology_audit.json`
- Create: `reports/medicine/cardiology_audit.md`
- Create: `reports/medicine/cardiology_human_review_priority.json`
- Modify: `reports/milestones.md`

**Interfaces:**
- Produces: exact/lexical/semantic duplicate candidates, distribution metrics, coverage gaps, audit verdict, and immutable chapter content version.

- [ ] **Step 1: Write failing duplicate/audit tests**

Test normalized duplicates, demographic-only vignette variants, repeated clinical decisions, repeated option sets, answer concentration, missing TN sections, stale references, and fail-closed audit status.

- [ ] **Step 2: Implement deterministic audit layers**

Exact and lexical layers run locally. Semantic similarity emits review candidates with scores and shared features; it never auto-deletes uncertain matches.

- [ ] **Step 3: Run the Cardiology final audit**

Require source traceability, verification evidence, reference validity, rationale quality, distributions, duplicate review, copyright similarity checks, risk list, and explicit shortfall reasons.

- [ ] **Step 4: Resolve audit findings and lock the pilot**

Revise only through the normal source-first and re-verification path. If the pilot does not pass, update prompts/process and rerun it before releasing other chapter jobs.

- [ ] **Step 5: Commit**

```bash
git add scripts/qbank schemas tests reports verified
git commit -m "audit: lock verified Cardiology pilot"
```

### Task 11: Medicine chapter waves to approximately 1,000 items

**Files:**
- Create/Modify: `batches/MED-*/**`
- Create/Modify: `candidates/MED-*.json`
- Create/Modify: `blind/MED-*.json`
- Create/Modify: `blind_verification/MED-*.json`
- Create/Modify: `rationale_verification/MED-*.json`
- Create/Modify: `verified/medicine/**`
- Create: `reports/medicine/*_audit.json`
- Create: `reports/medicine/*_audit.md`
- Create: `reports/medicine_final_audit.json`
- Create: `reports/medicine_final_audit.md`
- Modify: `references/registry.json`
- Modify: `reports/progress.*`
- Modify: `reports/milestones.md`

**Interfaces:**
- Produces: audited Medicine chapters covering the manifest's Cardiology, pharmacology/toxicology, dermatology/allergy, endocrinology, gastroenterology/hepatology, geriatrics/palliative, hematology/oncology, infectious disease, nephrology, neurology, respirology, and rheumatology/MSK allocations.

- [ ] **Step 1: Release at most two independent Medicine generation micro-batches concurrently**

For each chapter, repeat source packet, five-item generation, item-level blind solve, rationale audit, duplicate review, and chapter audit.

- [ ] **Step 2: Commit each passing chapter**

Use `content(medicine): lock <chapter> questions` and include its audit/progress evidence. Never mix an incomplete chapter into the commit.

- [ ] **Step 3: Run and resolve the Medicine discipline audit**

Check all manifest coverage, MCC objectives, high-risk facts, source freshness/concentration, answer/difficulty/activity distributions, cross-chapter duplicates, and rationale quality.

- [ ] **Step 4: Commit the discipline checkpoint**

```bash
git add batches candidates blind blind_verification rationale_verification verified quarantine rejected references reports
git commit -m "audit: complete Medicine discipline review"
```

### Task 12: Pediatrics and OBGYN chapter waves

**Files:**
- Create/Modify: `batches/PED-*/**`, `batches/GY-*/**`, `batches/OB-*/**`
- Create/Modify: private lifecycle artifacts for `PED-*`, `GY-*`, and `OB-*`
- Create/Modify: `verified/pediatrics/**`, `verified/obgyn/**`
- Create: `reports/pediatrics/**`, `reports/obgyn/**`
- Modify: `references/registry.json`, `reports/progress.*`, `reports/milestones.md`

**Interfaces:**
- Produces: up to approximately 1,000 audited Pediatrics items and approximately 1,000 combined GY/OB items.

- [ ] **Step 1: Process Pediatrics chapter waves**

Give enhanced two-source checking to vaccines, developmental thresholds, neonatal care, fever in infants, bilirubin management, doses, dehydration, safeguarding, and adolescent confidentiality. Commit every passing chapter separately.

- [ ] **Step 2: Audit and commit Pediatrics**

Run the full discipline audit, resolve failures through fresh source packets and re-verification, then commit `audit: complete Pediatrics discipline review`.

- [ ] **Step 3: Process Gynecology then Obstetrics chapter waves**

Preserve Toronto Notes order and apply enhanced checking to screening, contraception, STI care, gestational thresholds, medication safety, Rh prophylaxis, diabetes, hypertension, GBS, fetal surveillance, induction, and emergencies. Commit every passing chapter separately.

- [ ] **Step 4: Audit and commit OBGYN**

Run the full discipline audit and commit `audit: complete OBGYN discipline review` only after all unresolved defects are quarantined or rejected.

### Task 13: Surgery, Psychiatry, and PHELO chapter waves

**Files:**
- Create/Modify: `batches/SURG-*/**`, `batches/PSY-*/**`, `batches/PHELO-*/**`
- Create/Modify: corresponding private lifecycle artifacts
- Create/Modify: `verified/surgery/**`, `verified/psychiatry/**`, `verified/phelo/**`
- Create: `reports/surgery/**`, `reports/psychiatry/**`, `reports/phelo/**`
- Modify: `references/registry.json`, `reports/progress.*`, `reports/milestones.md`

**Interfaces:**
- Produces: up to approximately 1,000 audited items for each remaining discipline.

- [ ] **Step 1: Process and audit Surgery**

Emphasize stabilization, emergencies, imaging, initial management, consultation, disposition, and postoperative complications; reject board-level procedural trivia. Commit each chapter and the final discipline audit separately.

- [ ] **Step 2: Process and audit Psychiatry**

Apply enhanced checking to suicide safety, involuntary treatment jurisdiction, capacity, withdrawal, opioid-use treatment, pregnancy psychopharmacology, lithium, serotonin syndrome, NMS, and monitoring. Commit each chapter and discipline audit separately.

- [ ] **Step 3: Process and audit PHELO**

Name jurisdiction when material, distinguish federal/nationwide/provincial/institutional rules, and independently refresh screening, vaccination, reporting, and outbreak sources. Emphasize applied statistics rather than definitions. Commit each chapter and discipline audit separately.

### Task 14: Global audit and production export

**Files:**
- Modify: `scripts/qbank/audit.py`
- Modify: `scripts/qbank/export.py`
- Create: `tests/test_global_audit.py`
- Modify: `tests/test_export.py`
- Create: `reports/global_audit.json`
- Create: `reports/global_audit.md`
- Create: `reports/global_human_review_priority.json`
- Modify: `reports/progress.json`
- Modify: `reports/progress.md`
- Modify: `reports/milestones.md`
- Create/Modify: `app/public/data/qbank/**`

**Interfaces:**
- Produces: verified-only versioned public corpus and computed production manifest.

- [ ] **Step 1: Write failing global-audit/export tests**

Cover cross-discipline duplicates, overrepresented diagnoses, missing MCC objectives, answer-position patterns, repeated vignette templates, source concentration, freshness, uniform content versions, private-field projection, and transactional replacement.

- [ ] **Step 2: Run and resolve the global audit**

Do not silently edit medical content. Route confirmed defects through quarantine/revision/re-verification, then regenerate exact counts and gaps.

- [ ] **Step 3: Build and test production JSON**

Export only durable publication evidence, stable reference IDs, and strict public projections. Scan deploy roots for PDFs, source text, absolute paths, internal reasoning, candidates, quarantine, rejected records, stages, and backups.

- [ ] **Step 4: Commit**

```bash
git add scripts/qbank tests reports app/public/data/qbank
git commit -m "release: build audited qbank production dataset"
```

### Task 15: React/Firebase study application

**Files:**
- Create: `app/package.json`
- Create: `app/tsconfig.json`
- Create: `app/vite.config.ts`
- Create: `app/firebase.json`
- Create: `app/src/main.tsx`
- Create: `app/src/App.tsx`
- Create: `app/src/qbank/data.ts`
- Create: `app/src/qbank/types.ts`
- Create: `app/src/qbank/search.ts`
- Create: `app/src/components/QuestionSession.tsx`
- Create: `app/src/components/RationalePanel.tsx`
- Create: `app/src/components/StudyAnchor.tsx`
- Create: `app/src/components/ReferenceList.tsx`
- Create: `app/src/**/*.test.tsx`
- Create: `app/tests/content.test.ts`
- Create: `app/index.html`
- Modify: `README.md`
- Modify: `reports/milestones.md`

**Interfaces:**
- Consumes: `app/public/data/qbank/manifest.json`, discipline question JSON, and public references.
- Produces: a static Vite build under `app/dist/` ready for Firebase Hosting configuration checks.

- [ ] **Step 1: Write failing data/content tests**

Test manifest loading, total/count consistency, question navigation, five options, answer reveal, complete distractor rationales, study anchors, reference links, search results, and rejection of private fields or non-production statuses.

- [ ] **Step 2: Implement typed data loader and study UI**

Provide discipline/chapter/subtopic selection, configurable question sessions, answer submission, rationale display, study anchors, current references, search, and local progress persistence. Never expose the correct answer before submission.

- [ ] **Step 3: Configure Firebase Hosting locally**

Serve only `dist`, use SPA rewrites, immutable hashed assets, appropriate JSON caching, and no Functions/API dependency.

- [ ] **Step 4: Run application verification**

Run: `npm test`

Run: `npm run build`

Run content/leakage tests against `app/dist/` and locally inspect representative desktop/mobile flows.

- [ ] **Step 5: Update documentation and commit**

```bash
git add app README.md reports/milestones.md
git commit -m "feat: build Firebase-ready MCCQE study app"
```

### Task 16: Final evidence reconciliation

**Files:**
- Modify: `docs/superpowers/plans/2026-08-24-qbank-production.md`
- Modify: `reports/milestones.md`
- Modify: `reports/progress.json`
- Modify: `reports/progress.md`
- Create: `reports/final_handoff.md`

**Interfaces:**
- Produces: a filesystem-derived final status with no unsupported completion claims.

- [ ] **Step 1: Recompute all counts and milestone statuses**

Mark plan checkboxes only when their durable artifacts and tests exist. Record planned, generated, blind-passed, QA-passed, rejected, quarantined, human-reviewed, and published counts by discipline/chapter.

- [ ] **Step 2: Run full project verification**

Run Python tests, manifest validation, source/index audit, all chapter/discipline/global audits, production export tests, application tests/build, Git/deploy leakage scans, duplicate-ID scans, reference integrity checks, and `git diff --check`.

- [ ] **Step 3: Write the final handoff and commit**

Document exact shortfalls, unresolved human-review priorities, source freshness date, application build evidence, and the explicit fact that Firebase was not deployed.

```bash
git add docs/superpowers/plans reports
git commit -m "docs: reconcile completed qbank production milestones"
```
