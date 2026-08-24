# Toronto Notes 2025 — TOC Inventory Extraction Report

**Date:** 2026-08-24
**Output:** `research/tn2025/toc_inventory.json`
**Scope:** Mechanical structural extraction only — **no MCC mapping performed in this pass.**

---

## What this is

A deterministic, mechanical extraction of the Toronto Notes 2025 chapter → section → topic
hierarchy, built entirely from the book's own printed material (chapter page-range boundaries
and each chapter's own internal table-of-contents page). No clinical judgment, MCC objective
mapping, priority assignment, or content classification was performed — that is Phase 4
follow-on work, out of scope for this pass by design (per explicit instruction to stop here for
review).

## What this is not

- Not the master scope crosswalk
- Not an MCC-mapped dataset
- Not a subtopic-level (4th hierarchy level) extraction — see Known Limitations
- Not validated page-by-page against the source PDF for every chapter

---

## Inputs

1. **Chapter-level boundaries** (`derived/toronto-notes-2025/chapters/*/manifest.json`, 32
   files): chapter code, chapter title, and the list of PDF pages belonging to each chapter.
   These were originally computed on a sibling git branch (`codex/qbank-production`, in
   `.worktrees/qbank-production`) with its own validated ingestion pipeline, and copied into
   `main`'s gitignored `derived/` tree for reuse — no code or git history was merged, only the
   already-computed page-boundary output.
2. **Section/topic structure** (new in this pass): extracted by parsing each chapter's own
   printed internal table of contents, located on the first 1–2 physical pages of that chapter.

## Method

For each of the 32 chapters:
1. Scan the first 4 pages of the chapter for lines ending in that chapter's own page-numbering
   code (e.g. `C19`, `P70`) — these pages are the chapter's internal TOC.
2. Parse each TOC line: a **section** line ends in `<chapter_code><number>` (the chapter's own
   printed page label); its heading text is recovered by walking left from that trailing code and
   keeping only tokens that are purely alphabetic once trailing punctuation is stripped, since
   dot-leader OCR garbage (e.g. `"0.0.6.0 ee eee ee es"`) reliably fails that test and stops the
   walk. Lines without a trailing page code, following a already-found section, are recorded as
   **topics** nested under that section.
3. Convert each section's chapter-relative page label (e.g. `C19`) to an absolute PDF page using
   the chapter's own start-page offset, and set each section's page range from its own start to
   the next section's start minus one (or the chapter's last page, for the final section).

Full detail and code: `scripts/qbank/build_tn_toc_inventory.py`.

---

## Results

| Metric | Value |
|---|---|
| Chapters processed | 32 |
| Total pages covered by chapters | 1,575 of 1,595 (remaining 20 are front matter, pages 1–20, before the first chapter) |
| Sections extracted | 479 |
| Topics extracted | 1,472 |
| Chapters fully parsed, no coverage concerns | 24 |
| Chapters parsed but flagged **suspected incomplete coverage** | 7 (D, ER, FM, GY, NS, OR, P) |
| Chapters with **no TOC detected at all** | 1 (NP — Nephrology) |

---

## Data Quality — Read Before Using

### 24 chapters: fully parsed, no flags
A, C, CP, E, ELOM, G, GM, GS, H, ID, MG, MI, N, OB, OP, OT, PH, PL, PM, PS, R, RH, U, VS

These have their first detected section starting within a normal 1–5 page credits/acronyms
preamble of the chapter's first page, which is the expected pattern (verified directly against
raw OCR text for Cardiology as a worked example — see below).

### 7 chapters: suspected incomplete coverage
**D, ER, FM, GY, NS, OR, P** (Dermatology, Emergency Medicine, Family Medicine, Gynecology,
Neurosurgery, Orthopedic Surgery, Pediatrics)

**Root cause, confirmed by direct inspection (not guessed):** for these chapters, the earliest
entries in the printed TOC have long dot-leader runs that OCR mangled badly enough that the
trailing page-number token itself is missing from the extracted text entirely — not just the
leader dots. Example, Family Medicine's actual OCR text for its first several TOC entries:

```
Acromyms. 2... ee ee ee ee
Four Principles of Family Medicine.............
Periodic Health Examination.................
```

No page number appears at all — compare to a working entry lower on the same page where the
number did survive OCR. Because parsing requires a trailing page-code token to identify a
section line, these early entries are silently absent from the output rather than assigned a
wrong page number. This is a real gap in the underlying OCR text, not a bug in the parsing logic.

**Practical effect:** for these 7 chapters, `toc_inventory.json` sections start partway through
the chapter's actual content (e.g. Pediatrics' first captured section is "Genetics Dysmorphisms
and Metabolism" at P50 — everything from P1 through P49 is missing) and the topic/subtopic
material before that point is not represented at all yet.

### 1 chapter: no TOC detected
**NP (Nephrology)** — the page-number token for this chapter's TOC entries landed on a separate
OCR line from its heading text (`"NP2"` appears alone on the line after the heading, rather than
at the end of the heading's own line), which the current line-based parser cannot associate back
to its heading. Zero sections extracted; flagged for manual review rather than guessed at.

---

## Known Limitations (by design, not oversights)

1. **Only 3 of the required 4 hierarchy levels are populated.** Chapter and section are
   page-range anchored; topic is listed in TOC order under its section but has **no independent
   page range** — the printed TOC itself doesn't give sub-items their own page numbers. True
   subtopic-level extraction (in-page heading detection within actual chapter content, beyond
   what a chapter's own TOC lists) was not attempted: the existing OCR pipeline's per-page
   `headings` field is empty for every page checked, meaning no in-page heading detector exists
   yet in this codebase. Building one is separate, larger follow-on work.
2. **Heading text is preserved as OCR'd, not spell-corrected.** E.g. `"ACrOMYMS"` is kept as
   printed by OCR rather than silently "corrected" to "Acronyms" — every section also carries its
   `raw_ocr_line` for manual audit against the source PDF.
3. **Occasional flat-hierarchy artifacts.** A few chapters print an all-caps category header with
   its own page number immediately followed by its first subsection sharing that same page number
   (e.g. Cardiology's `"CARDIAC DISEASE"` at C19, immediately followed by `"Arrhythmias"` also at
   C19) — both surface as adjacent sections at the same page rather than nested category/section,
   since this pass models exactly 3 levels, not the source's occasional 4th.
4. **Topic-to-section attribution is TOC-reading-order-based**, not independently verified line by
   line against the source PDF for all 32 chapters — a small number of OCR line-break artifacts
   may misattribute an individual topic bullet to the wrong section.
5. **Coverage-quality flags are a heuristic** (first section far from chapter start ⇒ suspected
   gap), not a proof of correctness for the 24 "fully parsed" chapters either — they are simply
   the chapters where no gap signal was detected, not chapters independently verified page-by-page.

None of the above were silently smoothed over: every one of these is either an explicit field in
`toc_inventory.json` (`toc_extraction_status`, `coverage_quality_note`) or a documented limitation
in the file's own `known_limitations` array.

---

## Worked Example — Cardiology (fully parsed, spot-checked)

```
C2    pdf 92-92   "ACrOMYMS"                                        0 topics
C2    pdf 92-94   "Basic Anatomy Review"                            2 topics
C5    pdf 95-96   "Differential Diagnoses of Common Presentations"  6 topics
C7    pdf 97-97   "Cardiac Diagnostic Tests"                        1 topic
C7    pdf 97-108  "ApproachtoECGs"                                  9 topics
C19   pdf 109-109 "CARDIAC DISEASE"                                 0 topics
C19   pdf 109-119 "Arrhythmias"                                    10 topics
C30   pdf 120-129 "Ischemic Heart Disease"                          4 topics
...
C81   pdf 171-174 "References"                                      2 topics
```

Cross-checked directly against the chapter's raw OCR text (page 91) and against the corrected
broad-scope memo's independently-stated Cardiology range (C1–C84) — this pass's derived range
(chapter pages 92–174, i.e. C2–C84 relative to a C1 title page) is consistent with that prior
finding.

---

## Files

- **Output:** `research/tn2025/toc_inventory.json`
- **Script:** `scripts/qbank/build_tn_toc_inventory.py`
- **Inputs copied from sibling branch:** `derived/toronto-notes-2025/chapters/*/manifest.json`
  (32 files, gitignored — not committed as code, only as filesystem reuse of already-computed
  page boundaries)

---

## Recommended Next Steps (not performed in this pass)

1. Manually review the 7 "suspected incomplete coverage" chapters and 1 "no TOC detected"
   chapter against the source PDF, and either hand-correct their missing early sections or
   extend the parser with a fallback that searches the following page's running header for a
   printed page label when the TOC line itself is missing one.
2. Decide whether subtopic-level (4th hierarchy level) extraction is needed before crosswalk
   mapping begins, or whether topic-level granularity (3 levels) is sufficient for Phase 4.
3. Only once the TOC inventory is judged sufficient should Phase 4 (MCC objective mapping per
   study unit, using `research/mcc/objectives_registry.json` and
   `research/mcc/study_smarter_discipline_mapping.json`) begin.

**This pass does not claim readiness for master_scope_crosswalk.json generation.** It is a
structural extraction checkpoint for review, as requested.
