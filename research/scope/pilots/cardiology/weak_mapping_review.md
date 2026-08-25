# Cardiology Weak-Mapping Review (Phase 3B)

**Generated:** 2026-08-24
**Reviewed:** 6 WEAK-strength mcc_evidence entries from the Phase 3A crosswalk

---

## Methodology

Each WEAK mapping's cited MCC objective(s) had their **full** `causal_conditions`
and `enabling_objectives` text re-read (not the truncated excerpts used during
initial Phase 3A drafting), then compared against the study unit's actual
clinical content. One of five dispositions was chosen for each:

`KEEP_COMPONENT_WEAK` · `DOWNGRADE_SUPPORTING` · `DOWNGRADE_SPECIALIST` · `REMAP` · `UNRESOLVED`

**No mapping was upgraded merely to reduce the WEAK count.**

---

## Disposition Summary

| Disposition | Count |
|---|---|
| KEEP_COMPONENT_WEAK | 2 |
| DOWNGRADE_SUPPORTING | 1 |
| DOWNGRADE_SPECIALIST | 3 (2 mappings on one unit, SU-C-19) |
| REMAP | 0 |
| UNRESOLVED | 0 |

**Result: 6 WEAK mappings → 2 remaining WEAK mappings**, both explicitly flagged `requires_scope_review = true`.

---

## Individual Reviews

### SU-C-19 — Cardiac Implantable Electronic Devices (Pacemakers and ICDs)
**Weak mappings reviewed:** id=13 (Cardiac arrest), id=106 (Syncope)
**Finding:** Full enabling text for both objectives reviewed — neither mentions device therapy at all, even indirectly. The original COMPONENT classification overstated the evidence.
**Disposition: DOWNGRADE_SPECIALIST**
**Action:** Reclassified COMPONENT → SPECIALIST_DETAIL. Both WEAK citations removed (mcc_evidence now empty, matching sibling SPECIALIST_DETAIL units). scope_depth RECOGNIZE → CONTEXT_ONLY. target_questions 6 → 2.

### SU-C-27 — Advanced Heart Failure Therapies (Transplant, VAD, ECMO)
**Weak mapping reviewed:** id=29-1 (Generalized edema)
**Finding:** Objective's enabling text does contain genuine escalation-to-specialist-care language ("advanced...cardiac...disease" requiring consultation), but doesn't name transplant/VAD/ECMO specifically.
**Disposition: DOWNGRADE_SPECIALIST** (confirmed — already SPECIALIST_DETAIL)
**Action:** Classification unchanged; WEAK citation removed for consistency with sibling SPECIALIST_DETAIL units that carry no mcc_evidence.

### SU-C-28 — Cardiac Tumours
**Weak mapping reviewed:** id=106 (Syncope)
**Finding:** Full causal_conditions list has no obstructive-mass-lesion category at all.
**Disposition: DOWNGRADE_SUPPORTING** (confirmed — already SUPPORTING_KNOWLEDGE)
**Action:** Classification unchanged; WEAK citation removed for consistency with sibling SUPPORTING_KNOWLEDGE unit (Cardiac Anatomy Review).

### SU-C-31 — Rheumatic Fever
**Weak mapping reviewed:** id=62 (Abnormal heart sounds and murmurs)
**Finding:** Searched the entire Medical Expert registry for any objective naming "rheumatic fever," "Jones criteria," or "streptococc*" — none found. Closest alternative checked (Polyarthralgia, id=50-2) doesn't name it either.
**Disposition: KEEP_COMPONENT_WEAK**
**Action:** Unchanged classification/ID; `requires_scope_review = true` added.
**Why not downgrade/unresolve:** No better anchor exists anywhere in the current registry, and the clinical link (rheumatic fever → chronic valve disease → murmur) is genuine. Discarding it would lose real MCC-relevant content with nothing to replace it.

### SU-C-35 — Constrictive Pericarditis
**Weak mapping reviewed:** id=27 (Dyspnea)
**Finding:** The objective explicitly names "Pericardial disease (e.g., tamponade, pericarditis)" as a category, with the two examples marked non-exhaustive. Constrictive pericarditis is a standard member of that same named category, just not individually named.
**Disposition: KEEP_COMPONENT_WEAK**
**Action:** Unchanged classification/ID; `requires_scope_review = true` added.
**Why not downgrade:** Qualitatively stronger than a zero-evidence mapping — the parent category is explicitly named and explicitly non-exhaustive. Flagged rather than silently treated as equal-confidence to the STRONG pericarditis/tamponade mappings.

---

## What This Confirms for Scaling

- Re-reading full (not truncated) objective text before finalizing a WEAK mapping catches real overstatement (SU-C-19) without requiring new evidence.
- A WEAK mapping is not automatically wrong — some (SU-C-31, SU-C-35) reflect genuine but indirect textual support and are legitimately kept, provided they're flagged for reviewer visibility rather than presented at the same confidence as an explicitly-named STRONG mapping.
- SPECIALIST_DETAIL / SUPPORTING_KNOWLEDGE units should carry **empty** `mcc_evidence`, not a WEAK citation — a citation implies a testable component; these classifications explicitly mean the content isn't meant to be tested at that depth. This convention should be applied consistently going forward.
