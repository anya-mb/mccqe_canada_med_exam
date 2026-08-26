# Study Units Audit - GY (Gynecology)

**Generated:** 2026-08-25
**Total study units:** 39
**Total source nodes:** 55

## Source accounting

PASS - every canonical source node is represented in at least one study unit's `source_node_ids` or in `organizational_header_nodes`, verified by `validate-scope-chapter GY` (`source_accounting: PASS`).

## Structural quality summary

Chapter GY is a large, structurally noisy chapter: 0 `unresolved_headings` per the deterministic tool, but three sections carry title/merged-heading conflicts more serious than the ordinary "OCR-corrupted acronym" case seen in earlier chapters (G, GS, GM). No independent raw-OCR/body-heading corpus beyond `toc_inventory.json` exists for this project (same limitation as prior chapters), so each case below was resolved using only canonical TOC data, per `docs/scope-chapter-workflow.md`'s resolution order.

## Consolidations (multiple source nodes -> one study unit)

- **SU-GY-02** (Menstrual Cycle Physiology): GY.S02, GY.S18.T01
  Main-chapter 'Menstruation' physiology and the appendix-position 'Menstrual Cycle' entry under the mislabeled GY.S18 ('References') cover the same normal-physiology content; consolidated rather than duplicated.

- **SU-GY-03** (Gynecologic Imaging and Endometrial Biopsy): GY.S03, GY.S03.T01, GY.S03.T02
  'Imaging' and 'Endometrial Biopsy' consolidated as the non-surgical investigation pair; 'Hysterectomy' (T03) split out separately as a distinct therapeutic procedure (SU-GY-04).

- **SU-GY-12** (Early Pregnancy Loss and First-Trimester Bleeding): GY.S07, GY.S07.T01, GY.S07.T02
  'First Trimester Bleeding' and 'Spontaneous Abortions' are two facets of one presentation-to-diagnosis pathway sharing MCC objective 81.

- **SU-GY-14** (Infertility): GY.S09, GY.S09.T01, GY.S09.T02
  'Female Factors' and 'Male Factors' are two facets of the single couple-level infertility competency (MCC objective 46).

- **SU-GY-16** (Vaginal Discharge and Vulvovaginitis): GY.S11, GY.S11.T01, GY.S11.T02, GY.S11.T03
  'Physiologic Discharge', 'Non-Physiologic Discharge', and 'Vulvovaginitis' are three facets of the single discharge differential targeted by MCC objective 113. The section's five clinically distinct T-children (STI, Bartholin Gland Abscess, PID, Toxic Shock Syndrome, Surgical Infections) were each kept as independent units instead.

- **SU-GY-39** (Premenstrual Syndrome and Premenstrual Dysphoric Disorder): GY.S18.T03, GY.S18.T04
  Both are named and explicitly differentiated within the single MCC objective 56-3.

## Title/content notes (documented, not silently corrected)

- **SU-GY-01**: GY.S01's printed TOC title 'Acromyms' is a trivial acronym-list heading, not a clinical topic; `merged_duplicate_headings` records the legible alternate 'Basic Anatomy Review', used as the study-unit title.

- **SU-GY-08 / SU-GY-09**: GY.S04 ('Disorders of Menstruation') carries `merged_duplicate_headings` 'Endometriosis' and 'Adenomyosis' in addition to its three T-children. Unlike a same-content alternate label, these are clinically distinct diagnoses with no dedicated child node, so each was broken out as its own study unit cited against the parent section node.

- **SU-GY-10 / SU-GY-40**: GY.S05's printed title 'Fibroids' (BODY_HEADING_CONFIRMATION) conflicts with all three of its own T-children (Hormonal Methods, IUD, Emergency Postcoital Contraception), which match its `merged_duplicate_headings` entry 'Contraception'. RESOLVED (raw-OCR follow-up, 2026-08-25): pdf pages 608-612 confirm GY.S05 merges two genuine adjacent sections - Fibroids content (pdf 608-609, TN GY14-GY15) followed by a body-confirmed 'Contraception' heading mid-page-609. Represented as SU-GY-10 (Contraception, pdf 609-612) and SU-GY-40 (Fibroids, pdf 608-609); see the resolved coverage-gap note below.

- **SU-GY-22 / SU-GY-23**: GY.S12's printed title 'SexualAbuse' with merged heading 'Sexuality and Sexual Dysfunction' names two clinically distinct topics rather than one topic under two labels; split into two units against the shared parent node.

- **SU-GY-02 / SU-GY-38 / SU-GY-39**: GY.S18's printed title 'References' is a structural mislabel - its four T-children are real appendix-style clinical content (Menstrual Cycle, Stages of Puberty, PMS, PMDD), not a bibliography, unlike every other completed chapter's genuine terminal References section.

## Broad-oncology split note

- **GY.S15 ('Gynecological Oncology')**: 8 T-children (Pelvic Mass, Uterus, Ovary, Cervix, Fallopian Tube, Vulva, Vagina, Gestational Trophoblastic Disease/Neoplasia) are each represented as an independent study unit (SU-GY-28 through SU-GY-35), consistent with the GM.S03 broad-syndrome-split precedent - each organ site carries distinct clinical content and, in most cases, its own adjacent MCC evidence.

## GY/OB boundary note

- SU-GY-11 (Termination of Pregnancy), SU-GY-12 (Early Pregnancy Loss/First-Trimester Bleeding), and SU-GY-13 (Ectopic Pregnancy) all genuinely appear as GY-chapter source nodes (GY.S06-GY.S08) and are mapped here rather than deferred to Obstetrics, per the instruction against moving genuine GY content out simply because it is pregnancy-related. Final PRIMARY_OWNER/CROSS_LINK/DISTINCT_CONTEXT decisions against OB are deferred to the global boundary audit once OB is mapped.

## Resolved coverage gaps

- **Fibroids (uterine leiomyoma)** - RESOLVED 2026-08-25 as CONFIRMED_REAL_HEADING_AND_CONTENT: GY.S05's body-confirmed printed title 'Fibroids' names a genuine section, but its inherited page range and T-children were carried over from an adjacent 'Contraception' section during TOC extraction. Targeted raw-OCR verification of pdf pages 608-609 (TN GY14-GY15) confirmed standalone Fibroids Definition/Epidemiology/Pathogenesis/Management content ending where a body-confirmed 'Contraception' heading begins mid-page-609. Added as SU-GY-40 against source node GY.S05, page range corrected to pdf 608-609.
