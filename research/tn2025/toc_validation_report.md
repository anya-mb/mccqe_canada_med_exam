# Toronto Notes TOC Inventory — Validation Report

**Generated:** 2026-08-24
**TOC_VALIDATION:** ✅ PASS

## Chapter Coverage

- Chapters expected: 32
- Chapters parsed (TOC detected): 32
- Clean chapters (no unresolved headings): 22 — ['C', 'CP', 'E', 'ELOM', 'ER', 'G', 'GM', 'GY', 'H', 'ID', 'MG', 'MI', 'N', 'OB', 'PH', 'PL', 'PM', 'PS', 'R', 'RH', 'U', 'VS']
- Incomplete chapters (>=1 unresolved heading): 10 — ['A', 'D', 'FM', 'GS', 'NP', 'NS', 'OP', 'OR', 'OT', 'P']
- Missing TOCs (no internal TOC page detected at all): 0 — []

## Node Counts

- Total TOC nodes: 2019
- Sections: 468
- Topics/subtopics: 1519
- Leaf nodes: 1660

## Extraction Method Breakdown (sections)

- TOC_OCR: 414
- BODY_HEADING_CONFIRMATION: 54

## Integrity Checks

- Unresolved headings: 27
- Duplicate IDs: 0 ✅
- Orphan nodes: 0 ✅
- Invalid page ranges: 0 ✅

## Test Results

- TOC-specific tests: 27 passed / 0 failed
- Full project tests: 487 passed / 0 failed

## Gate Criteria

- zero_duplicate_ids: ✅
- zero_orphan_nodes: ✅
- zero_invalid_page_ranges: ✅
- toc_tests_all_pass: ✅
- full_suite_all_pass: ✅
- at_most_1_chapter_with_no_toc: ✅
- unresolved_count_small_and_documented: ✅

## Notes

27 unresolved headings remain across the 32 chapters (see research/tn2025/unresolved_headings.json for each one's exact source page and reason). These are catastrophically OCR-corrupted individual TOC lines (dot-leader runs that swallowed the page number entirely, or two-column layout merges with no recoverable second anchor) where neither the TOC digit nor a body-page search could confirm a page. None are silently dropped - every one is individually recorded with its raw OCR source line.

