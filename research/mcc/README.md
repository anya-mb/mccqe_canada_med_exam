# MCC Canonical Evidence Layer

**Last Updated:** 2026-08-24  
**Status:** Phase 1 Complete | Phase 2 Blocking (Web Service Retrieval Required)

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
- **Important:** Blueprint percentages are distinct from CanMEDS role weights—do not conflate them

**item_style_profile.json**
- Official MCQ guidelines: single-best-answer format
- 5-option construction (default for generation)
- Stem requirements: clinical context, explicit lead-in
- Distractor requirements: plausible, homogeneous, based on misconceptions
- Prohibitions: no "all of the above," no "none of the above"
- 55 free MCC-style practice questions available (calibration only)
- Unresolved: whether ALL current live items use exactly 5 options

**unresolved_mcc_evidence.json**
- Distinguishes between items that HAVE been confirmed from official sources
- Documents genuinely unresolved items: pilot distribution, all-items-5-options, complete objectives registry, Study Smarter mappings

---

### ⚠️ Placeholders (Require Web Service Retrieval & Extraction)

**objectives_registry.json**
- **Status:** Framework created, awaiting data population
- **How to complete:** 
  1. Access technical documentation at https://mcc.ca/objectives/ → "Read the technical documentation"
  2. Use documented JSON/XML endpoints to retrieve objectives
  3. For each objective, capture: mcc_id, legacy_id, title, canmeds_role, version, group_id, official_url, content, retrieval_date
  4. Do NOT invent missing IDs
- **Expected scope:** 100+ objectives
- **Criticality:** BLOCKS master scope crosswalk generation

**study_smarter_discipline_mapping.json**
- **Status:** Framework created, awaiting data extraction
- **How to complete:**
  1. Access current 2026 MCC Study Smarter guide (launched April 2, 2026)
  2. For every objective, record which Study Smarter discipline list(s) contain it
  3. Document overlaps
  4. Do NOT infer mappings beyond explicit Study Smarter listings
- **Six disciplines:** Medicine, Pediatrics, Obstetrics & Gynecology, Surgery, Psychiatry, PHELO
- **Important:** Study Smarter is explicitly non-exhaustive; objectives overlap disciplines; not all objectives are represented
- **Criticality:** BLOCKS master scope crosswalk generation

---

## Quality Assurance

### Audit Report
See: `reports/mcc_deep_research_claim_audit.md`

**Audit Results:**
- 15+ claims OFFICIAL_CONFIRMED from mcc.ca
- 2 claims PARTIALLY_SUPPORTED (correct but need detailed source links)
- 0 incorrect claims found

**Key Findings:**
- The Deep Research memo is substantially accurate
- All major claims verified or appropriately flagged
- Study Smarter launch date corrected: April 2, 2026 (2026 version, not 2025)
- Pilot item distribution correctly flagged as unresolved (not one-third)

### Construction Status Report
See: `reports/mcc_evidence_layer_construction_status.md`

**Completeness Assessment:**
| Component | Status | Blocking Crosswalk? |
|-----------|--------|-------------------|
| Exam profile | 100% Complete ✅ | No |
| Blueprint | 100% Complete ✅ | No |
| Item style | 95% Complete ⚠️ | No |
| Objectives registry | 5% (Placeholder) | **YES** |
| Study Smarter mapping | 5% (Placeholder) | **YES** |
| Unresolved evidence | 100% Complete ✅ | No |

---

## What This IS

✅ Official, verified MCC specifications  
✅ Every fact sourced from mcc.ca with access dates  
✅ Comprehensive audit trail documenting verification process  
✅ Canonical reference for MCCQE format, structure, and assessment framework  
✅ Foundation for Toronto Notes → MCC curriculum crosswalk  

## What This IS NOT

❌ The complete MCC Objectives registry (requires web service retrieval)  
❌ Study Smarter discipline mapping (requires guide extraction)  
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
5. **Audit Trail:** All corrections and verifications documented in reports

---

## Next Steps (Phase 2)

**BLOCKER: Complete Objectives Registry & Study Smarter Mappings**

1. Retrieve complete objectives from MCC web service
2. Extract Study Smarter discipline assignments from current guide
3. Once both are complete, build master scope crosswalk
4. Then derive six discipline manifests
5. Finally, question generation can begin

**Do NOT proceed to master_scope_crosswalk.json generation until both web service retrieval and Study Smarter extraction are complete.**

---

## File Structure

```
research/mcc/
├── README.md (this file)
├── current_exam_profile.json        [✅ Complete]
├── blueprint.json                   [✅ Complete]
├── item_style_profile.json          [✅ Complete]
├── objectives_registry.json         [⚠️ Placeholder]
├── study_smarter_discipline_mapping.json [⚠️ Placeholder]
└── unresolved_mcc_evidence.json     [✅ Complete]

reports/
├── mcc_deep_research_claim_audit.md              [Audit verification]
└── mcc_evidence_layer_construction_status.md     [Phase status]
```

---

## Relationships to Other Documentation

- **Audit Source:** research/raw/MCC_ONLY_DEEP_RESEARCH_MEMO.md (unchanged, preserved)
- **Methodology Source:** research/raw/broad_scope_memo_corrected_2026-08-24.md (unchanged, preserved)
- **Toronto Notes:** derived/toronto-notes-2025/ (OCR and index already extracted)
- **Downstream:** research/scope/ (master_scope_crosswalk.json to be created in Phase 2)

---

## Contact & Questions

For questions about:
- **MCC facts & specifications:** Consult this evidence layer with its provenance trails
- **Corrections to claims:** See mcc_deep_research_claim_audit.md
- **Current construction status:** See mcc_evidence_layer_construction_status.md
- **Raw research material:** See research/raw/ directory

---

*Canonical Evidence Layer v1.0 — Established 2026-08-24*  
*Audited & verified. Ready for Phase 2 web service retrieval.*
