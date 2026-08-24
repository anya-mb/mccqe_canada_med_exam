# Objectives Registry Audit

**Audit Date:** 2026-08-24
**Registry Retrieved At:** 2026-08-24
**Overall Status:** ✅ PASS

## Record Counts

**Total records:** 198

| Role | Count |
|------|-------|
| Medical Expert | 192 |
| Collaborator | 1 |
| Communicator | 1 |
| Health Advocate | 1 |
| Leader/Manager | 1 |
| Professional | 1 |
| Scholar | 1 |

## Integrity Checks

- Duplicate MCC IDs: 0 ✅
- Duplicate titles: 0 ✅
- Duplicate normalized title candidates: 0 ✅
- Missing title: 0 ✅
- Missing role: 0 ✅
- Missing source URL: 0 ✅
- Invalid source URLs: 0 ✅
- Unknown roles: 0 ✅
- Unresolved Legacy IDs (Medical Expert): 0 ✅
- Unresolved current IDs (Medical Expert): 0 ✅
- Retrieval failures: 0 ✅
- Malformed content records: 0 ✅

## Manual Verification Sample (Representative Cross-Check)

Each sample was independently loaded from the live official MCC page and compared against the registry record.

| Title | Category | Result | Registry ID | Registry Version |
|-------|----------|--------|-------------|-------------------|
| Headache | Legacy ID 39 (task-specified anchor) | ✅ PASS | 39 | March 2025 |
| Limp in children | pediatric-relevant presentation (secondary sample) | ✅ PASS | 20 | March 2025 |
| Abnormal lipids | medicine presentation (secondary sample) | ✅ PASS | 51 | March 2022 |
| Vascular injury | surgery-relevant presentation (secondary sample) | ✅ PASS | 109-15 | January 2017 |
| Chest pain | cardiovascular presentation | ✅ PASS | 14 | March 2022 |
| Dyspnea | respiratory presentation | ✅ PASS | 27 | March 2023 |
| Neonatal jaundice | pediatric-relevant presentation (primary sample) | ✅ PASS | 49-1 | March 2026 |
| Preterm labour | OBGYN presentation | ✅ PASS | 82 | January 2017 |
| Abdominal injuries | surgery-relevant presentation (primary sample) | ✅ PASS | 109-1 | March 2022 |
| Suicidal behaviour | psychiatry-relevant presentation | ✅ PASS | 105 | February 2017 |
| Collaborator | PHELO/non-Medical-Expert role | ✅ PASS | None | None |
| Communicator | PHELO/non-Medical-Expert role | ✅ PASS | None | None |
| Health Advocate | PHELO/non-Medical-Expert role | ✅ PASS | None | None |
| Leader/Manager | PHELO/non-Medical-Expert role | ✅ PASS | None | None |
| Professional | PHELO/non-Medical-Expert role | ✅ PASS | None | None |
| Scholar | PHELO/non-Medical-Expert role | ✅ PASS | None | None |

**Sample overall result:** ✅ PASS (16/16 checked)

## Notes on Expected Non-Issues

21 Medical Expert objectives legitimately have no `causal_conditions` section (e.g., Consent, Immunization, Prenatal care) because they are not differential-diagnosis presentations. This is expected structural variation in official MCC content, not a data quality defect.

The six non-Medical-Expert roles (Collaborator, Communicator, Health Advocate, Leader/Manager, Professional, Scholar) have no Legacy ID, version, or per-objective URL because MCC publishes them as single role-level competency statements, not discrete presentation objectives. This is preserved as the actual official structure, not treated as missing data.

