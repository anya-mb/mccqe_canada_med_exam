# MCC Canonical Evidence Layer

**Last Updated:** 2026-08-24
**Status:** Phase 1 Complete | Phase 2 Complete | Ready for Master Scope Crosswalk

This directory contains the official, verified MCC evidence layer for the MCCQE (Medical Council of Canada Qualifying Examination). Every claim is sourced from official MCC documentation at mcc.ca.

---

## Files in This Directory

### ✅ Complete & Verified

**current_exam_profile.json**
- Exam name, purpose, delivery format
- Total items (230), section structure (115 + 115)
- Timing (2h40 per section, 45-minute optional break)
- Pilot items (20 total, 210 operational/scored)
- Assessment framework (MCC Examination Objectives)
- Blueprint categories overview

**blueprint.json**
- Physician Activities: Assessment/Diagnosis (45±5%), Management (35±5%), Communication (10±5%), Professional Behaviours (10±5%)
- Dimensions of Care: Health Promotion & Illness Prevention (20±5%), Acute (35±5%), Chronic (30±5%), Psychosocial Aspects (15±5%)
- CanMEDS roles framework and Medical Expert sub-organization
- Percentages cross-confirmed against two independent official sources: the mcc.ca MCCQE page and the Study Smarter 2026 guide's printed blueprint table
- **Important:** Blueprint percentages are distinct from CanMEDS role weights—do not conflate them

**item_style_profile.json**
- Official MCQ guidelines: single-best-answer format
- 5-option construction (default for generation)
- Stem requirements: clinical context, explicit lead-in
- Distractor requirements: plausible, homogeneous, based on misconceptions
- Prohibitions: no "all of the above," no "none of the above"
- 55 free MCC-style practice questions available (calibration only)
- Unresolved: whether ALL current live items use exactly 5 options

**objectives_registry.json** — 198 records
- 192 Medical Expert objectives retrieved from the official web service (`https://mcc.ca/wp-json/mcc/medical-expert/en/?type=json&content=true`), each with mcc_id, legacy_id (confirmed identical), title, version, group, official URL, and full parsed content (rationale, causal conditions, key objectives, enabling objectives)
- 6 non-Medical-Expert role records (Collaborator, Communicator, Health Advocate, Leader/Manager, Professional, Scholar), each captured as a single role-level competency statement — MCC publishes no per-objective IDs for these roles, and no web-service endpoint exists for them (confirmed via HTTP 404)
- Audit: `reports/objectives_registry_audit.md` — PASS, 16/16 manual verification samples PASS

**objective_id_crosswalk.json**
- Documents the finding that the web-service `id` field is identical to the official page's "Legacy ID" field for every Medical Expert objective (4/4 direct page spot-checks, no counter-example across 192 records)
- Non-Medical-Expert roles marked NOT_APPLICABLE (no Legacy ID system exists for them)

**study_smarter_discipline_mapping.json**
- 291 discipline-listing rows extracted verbatim from the official 2026 Study Smarter guide (pages 7–10), across all six disciplines
- 111 unique Legacy IDs, 67 listed under more than one discipline
- Official non-exhaustiveness caveats preserved verbatim as metadata
- One known source anomaly documented (Surgery's "Weakness... 117 118" dual-ID line) rather than silently resolved

**study_smarter_registry_reconciliation.json**
- Every one of the 291 rows reconciled against `objectives_registry.json`: 291/291 CONFIRMED (0 unresolved, 0 needing review)
- Audit: `reports/study_smarter_mapping_audit.md` — PASS

**unresolved_mcc_evidence.json**
- Distinguishes between items confirmed from official sources and items that remain genuinely unresolved
- All formerly CRITICAL blockers (objectives registry, Study Smarter mapping) now resolved
- Remaining unresolved items are explicitly tagged as non-blocking for the scope crosswalk

---

## Quality Assurance

### Objectives Registry Audit
See: `reports/objectives_registry_audit.md`
- Overall status: **PASS**
- 198 total records (192 Medical Expert + 6 non-expert roles), zero duplicate IDs/titles/URLs
- 16-item manual verification sample (Headache/39, cardiovascular, respiratory, pediatric, OBGYN, surgery, psychiatry presentations, plus all 6 non-expert roles): **16/16 PASS**

### Study Smarter Mapping Audit
See: `reports/study_smarter_mapping_audit.md`
- Overall status: **PASS**
- 291/291 listing rows reconciled to a specific registry record
- 1 known, explicitly-flagged source anomaly (dual Legacy ID on one Surgery line) — preserved, not silently resolved

### Deep Research Memo Audit
See: `reports/mcc_deep_research_claim_audit.md` and its provenance addendum `reports/mcc_deep_research_claim_audit_provenance_note.md`
- 15+ claims OFFICIAL_CONFIRMED from mcc.ca, 0 incorrect claims found
- The provenance note documents that the audited memo was already a corrected version (not the original uncorrected Deep Research output) — this does not invalidate the audit's findings, since every fact in this evidence layer was independently re-verified against live official sources regardless of what the memo claimed

### Phase 2 Completion Gate
See: `reports/mcc_evidence_phase2_completion.md` for the full gate checklist and PASS/FAIL determination.

---

## What This IS

✅ Official, verified MCC specifications
✅ Every fact sourced from mcc.ca (or an official MCC-hosted PDF) with access dates
✅ Comprehensive audit trail documenting verification process
✅ Canonical reference for MCCQE format, structure, and assessment framework
✅ Complete Medical Expert objectives registry with official content
✅ Complete Study Smarter discipline mapping, reconciled to the registry
✅ Foundation for the Toronto Notes → MCC curriculum crosswalk

## What This IS NOT

❌ Practice questions or sample content
❌ Clinical guidance or treatment recommendations
❌ Prepared for question generation (see downstream phases)

---

## Data Integrity Standards

Every artifact in this directory follows these standards:

1. **Provenance Required:** Every field documents source URL, title, and access date
2. **No Invention:** Unknown or unconfirmed values explicitly marked as such
3. **Distinction Maintained:** Difference between OFFICIAL_RULE, OBSERVED_PATTERN, and UNRESOLVED
4. **Cautions Documented:** Important clarifications (e.g., blueprint ≠ CanMEDS roles) flagged
5. **Anomalies preserved, not resolved away:** e.g. the Surgery dual-Legacy-ID line is recorded verbatim with an explicit anomaly note rather than guessed at
6. **Audit Trail:** All corrections and verifications documented in reports

---

## Next Steps (Phase 3)

With both former blockers resolved, work can proceed to:

1. Validate the Toronto Notes 2025 structural inventory (`research/tn2025/toc_inventory.json`)
2. Build `research/scope/master_scope_crosswalk.json` combining Toronto Notes structure with this MCC evidence layer
3. Derive the six discipline manifests from the validated crosswalk
4. Only then may question generation begin

---

## File Structure

```
research/mcc/
├── README.md (this file)
├── current_exam_profile.json                  [✅ Complete]
├── blueprint.json                              [✅ Complete]
├── item_style_profile.json                     [✅ Complete]
├── objectives_registry.json                    [✅ Complete - 198 records]
├── objective_id_crosswalk.json                 [✅ Complete]
├── study_smarter_discipline_mapping.json       [✅ Complete - 291 rows]
├── study_smarter_registry_reconciliation.json  [✅ Complete - 291/291 CONFIRMED]
├── unresolved_mcc_evidence.json                [✅ Complete]
└── raw_retrieval/                              [Raw API/PDF responses, for provenance]
    ├── medical-expert_web_service_response.json
    ├── medical-expert_titles_only_response.json
    ├── medical-expert_page_links.json
    ├── objectives_web_service_technical_documentation.pdf
    ├── study_smarter_guide_2026.pdf
    └── study_smarter_discipline_lists_raw.json

reports/
├── mcc_deep_research_claim_audit.md                    [Phase 1 audit]
├── mcc_deep_research_claim_audit_provenance_note.md     [Provenance addendum]
├── mcc_evidence_layer_construction_status.md           [Phase 1 status]
├── objectives_registry_audit.md / .json                [Phase 2 audit]
├── study_smarter_mapping_audit.md / .json              [Phase 2 audit]
└── mcc_evidence_phase2_completion.md                    [Phase 2 gate]
```

---

## Relationships to Other Documentation

- **Audit Source:** research/raw/MCC_ONLY_DEEP_RESEARCH_MEMO.md (unchanged, preserved)
- **Methodology Source:** research/raw/broad_scope_memo_corrected_2026-08-24.md (unchanged, preserved)
- **Toronto Notes:** derived/toronto-notes-2025/ (OCR and index already extracted)
- **Downstream:** research/scope/ (master_scope_crosswalk.json — Phase 3)

---

## Contact & Questions

For questions about:
- **MCC facts & specifications:** Consult this evidence layer with its provenance trails
- **Corrections to claims:** See mcc_deep_research_claim_audit.md and its provenance note
- **Registry/mapping data quality:** See objectives_registry_audit.md and study_smarter_mapping_audit.md
- **Current construction status:** See mcc_evidence_phase2_completion.md
- **Raw research material:** See research/raw/ and research/mcc/raw_retrieval/ directories

---

*Canonical Evidence Layer v2.0 — Phase 2 completed 2026-08-24*
*Audited & verified. Ready for Phase 3 master scope crosswalk.*
