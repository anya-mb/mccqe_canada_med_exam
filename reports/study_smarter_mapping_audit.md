# Study Smarter Discipline Mapping Audit

**Audit Date:** 2026-08-24
**Overall Status:** ✅ PASS

## Source

- **Title:** Study Smarter: A Study Guide for the MCCQE
- **Published (as printed):** April 1, 2026
- **URL:** https://mcc.ca/wp-content/uploads/Study-smarter-A-study-guide-for-the-MCCQE.pdf
- **SHA-256:** 7c8d8a61f0465b56fae00c35a9968c337c69d86620511f7e71dadff1e624f4f4

## Listing Counts

| Discipline | Rows Listed |
|------------|-------------|
| Medicine | 66 |
| OBGYN | 26 |
| Psychiatry | 31 |
| Pediatrics | 82 |
| Surgery | 63 |
| PHELO | 23 |
| **Total** | **291** |

**Unique Legacy IDs across all disciplines:** 111
**Legacy IDs appearing in >1 discipline (explicit multi-listing, not inferred):** 67

## Reconciliation Against Objectives Registry

| Status | Count |
|--------|-------|
| CONFIRMED | 291 |

**Matched registry records (CONFIRMED):** 291 / 291

## Known Source Anomaly

**Location:** Surgery discipline list, last entry (page 10)

**Printed text:** `Weakness (not caused by cerebrovascular accident), 117 118`

Two Legacy ID numbers ('117' and '118') are printed after this single title, unlike every other entry in the guide which has exactly one Legacy ID. Confirmed by direct visual inspection of the PDF page (not a text-extraction artifact) — the anomaly exists in the official source document itself.

**Resolution:** Recorded as-is (both IDs preserved) in the raw list below. Treated as UNRESOLVED for the '118' portion in reconciliation — not silently dropped, not silently assigned to a guessed title.

## Duplicate Extraction Errors

Count: 0 ✅

## Malformed IDs

Count: 0 ✅

## Important Caveat

Absence of a Medical Expert objective from all six Study Smarter discipline lists does NOT mean it is missing from MCC scope. Study Smarter is explicitly non-exhaustive per its own printed caveats (see study_smarter_discipline_mapping.json.limitations). Absence means only 'not explicitly represented in this non-exhaustive study aid.'

