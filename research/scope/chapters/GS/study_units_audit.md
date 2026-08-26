# Study Units Audit - GS (General and Thoracic Surgery)

**Generated:** 2026-08-25  
**Total study units:** 80  
**Total source nodes:** 101

## Source accounting

PASS - every canonical source node is represented in at least one study unit's `source_node_ids` or in `organizational_header_nodes`, verified by `validate-scope-chapter GS` (`source_accounting: PASS`).

## Structural corruption summary

Chapter GS's Toronto Notes TOC is heavily corrupted by a two-column OCR bleed pattern (rows from two physically adjacent TOC columns concatenated into one string). This is confirmed - not merely suspected - by `raw_ocr_line` on each affected node, and by the deterministic `prepare-scope-chapter` tool's own 2 flagged `unresolved_headings` ('Abdominal Hernia', 'Inflammatory Bowel Disease' - see `unrecoverable_coverage_gaps` in `study_units_audit.json`). No independent raw-OCR/body-heading corpus beyond `toc_inventory.json` exists for this project (same limitation as chapter G), so every case below was resolved using only canonical TOC data and `raw_ocr_line`, per `docs/scope-chapter-workflow.md`'s resolution order, steps 1-2 and 5.

## Consolidations (multiple source nodes -> one study unit)

- **SU-GS-10**: GS.S04.T04, GS.S04.T05  
  GS.S04.T04 (Postoperative Dyspnea) and T05 (Respiratory Complications) are consolidated as one clinical continuum: dyspnea is the presenting symptom of the postoperative respiratory complications T05 enumerates (atelectasis, pneumonia, PE).

- **SU-GS-13**: GS.S04.T08, GS.S07.T02  
  Paralytic ileus is listed twice in the extracted structure - once as a postoperative complication (GS.S04.T08) and once under Small Intestine (GS.S07.T02, immediately after Mechanical Small Bowel Obstruction). Both source nodes describe the identical clinical entity and are consolidated into one study unit rather than duplicated.

- **SU-GS-18**: GS.S05.T04, GS.S05.T05  
  GS.S05.T04 (Complicated Parapneumonic Effusion) and T05 (Empyema) are consolidated: MCC objective 76 names both together as a single causal category, and empyema is the natural progression of a complicated parapneumonic effusion.

- **SU-GS-58**: GS.S13.T01, GS.S13.T02  
  GS.S13.T01 (Cholelithiasis) and T02 (Biliary Colic) are consolidated: biliary colic is the symptomatic presentation of cholelithiasis, one disease entity sharing the same evidence base.

- **SU-GS-59**: GS.S13.T03, GS.S13.T04  
  GS.S13.T03 (Acute Cholecystitis) and T04 (Acalculous Cholecystitis) are consolidated as one disease with a named etiologic subtype, sharing the same evidence base.

- **SU-GS-80**: GS.S21.T01, GS.S21.T02, GS.S21.T03  
  GS.S21.T01-T03 are extracted as children of a section titled 'Landmark General and Thoracic Surgery Trials', but their actual content (Mechanical Large Bowel Obstruction; Functional Large Bowel Obstruction/Colonic Pseudo-Obstruction; '(Ogilvie's Syndrome)') is unrelated clinical disease content, not trial names - the same documented title/content mismatch pattern as chapter G's SU-G-44 through SU-G-46 (raw_ocr_line for GS.S21 confirms the printed title itself, so this is not treated as an extraction artifact to silently correct). T02's raw title embeds the word 'References', consistent with genuine landmark-trial reference-list content existing somewhere on these pages but not surviving extraction as its own topic; no landmark-trial-specific content could be recovered and none is fabricated here. All three T-nodes are consolidated into one study unit since T02 and T03 are a single split concept (Functional Large Bowel Obstruction = Ogilvie's Syndrome).

## Title/content mismatches (documented, not silently corrected)

- **SU-GS-54, SU-GS-55, SU-GS-56, SU-GS-57**: GS.S12 is titled 'Anorectum' (raw OCR 'AmorectuM') but T08-T11 (Liver Cysts, Liver Abscesses, Neoplasms, Liver Transplantation) are unrelated hepatobiliary/liver content, consistent with the same two-column TOC-OCR bleed pattern documented for chapter G's SU-G-44 through SU-G-46 ('Liver Transplantation' section containing cirrhosis-complication T-children). Not corrected without body-page evidence; each unit's own title reflects its true content.

- **SU-GS-71, SU-GS-72**: GS.S16 is titled 'Breast' but its single T-child merges two unrelated topics ('Short Gut Syndrome' and 'Benign Breast Lesions') in one raw OCR string. Split into two study units sharing the same source_node_id.

- **SU-GS-79**: GS.S17 raw_ocr_line ('Groin Hernias Surgical Endocrinology...') confirms two section titles were merged; 'Groin Hernias' has no surviving T-child and is sourced from the parent GS.S17 node directly.

- **SU-GS-77, SU-GS-78**: Same GS.S17 merge: T02 ('Appendix ee en eee ee ee teens GS35 Advent Gland y') and T03 ('Appendicitis Pancreas') are heavily OCR-corrupted; T02 is treated as UNCERTAIN (SU-GS-75) and the 'Appendicitis' content of T03 is retained as its own study unit (SU-GS-77) with UNRESOLVED page precision.

- **SU-GS-79 (Crohn's Disease)**: GS.S18 raw_ocr_line ('Crohn's Disease Pediatric Surgery... GS73') confirms a merged title. No content survived for an independent Pediatric Surgery topic (see review_items.json).

- **SU-GS-80 (Ulcerative Colitis)**: GS.S19 raw_ocr_line ('Ulcerative Colitis Skin Lesions... GS75') confirms a merged title. No content survived for an independent Skin Lesions topic (see review_items.json).

- **SU-GS-80**: GS.S21 is titled 'Landmark General and Thoracic Surgery Trials' (raw_ocr_line HIGH confidence, confirmed genuine printed title) but its three T-children are Large Bowel Obstruction disease content, not trial names - same documented mismatch pattern as chapter G's SU-G-44 through SU-G-46.

## Unrecoverable coverage gaps

- **Abdominal Hernia**: UNRESOLVED - no toc_inventory.json node_id exists for this heading; its trailing page-number digits did not parse to a page consistent with reading order, and no body-page line matched within the searched window (pdf pages 557-563). Not represented as a study unit because it cannot be traced to a canonical source node. Abdominal-wall hernia content beyond groin hernias (SU-GS-79, MCC objective 2-4) may be under-covered in this chapter pending future source re-extraction.

- **Inflammatory Bowel Disease**: UNRESOLVED - no toc_inventory.json node_id exists for this heading (page window searched: pdf pages 563-565). Surgical IBD content is nonetheless covered via SU-GS-79 (Crohn's Disease) and SU-GS-80 (Ulcerative Colitis), which map to MCC objective 3-3's explicit 'Inflammatory bowel disease' causal-conditions entry.

- **Pediatric Surgery**: No toc_inventory.json node or T-children captured any Pediatric Surgery content; nothing to build a study unit from without fabricating content. Logged as a coverage gap only.

- **Skin Lesions**: No toc_inventory.json node or T-children captured any Skin Lesions content; nothing to build a study unit from without fabricating content. Logged as a coverage gap only.

- **Landmark General and Thoracic Surgery Trials (actual trial names/content)**: No landmark-trial names or content were recoverable from the extracted structure; GS.S21's T-children were repurposed as SU-GS-80 (Large Bowel Obstruction) per their actual textual content. Logged as a coverage gap only.

- **Additional Breast section content (e.g., Breast Cancer, Breast Cancer Screening)**: Only 'Benign Breast Lesions' (SU-GS-71) was textually recoverable from the single corrupted T-child; a 6-page Breast section plausibly contains additional topics (e.g., breast cancer) that did not survive extraction as separate nodes. Logged as a coverage gap only.
