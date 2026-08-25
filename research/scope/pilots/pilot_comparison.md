# Pilot Comparison: Cardiology vs. ELOM

**Generated:** 2026-08-24
**Purpose:** Validate that the study-unit-derivation + MCC-crosswalk methodology generalizes across a fundamentally clinical, Medical-Expert-driven chapter (Cardiology) and a fundamentally non-clinical, role-based chapter (ELOM), before scaling to the remaining 30 Toronto Notes chapters.

---

## Headline Numbers

| | Cardiology | ELOM |
|---|---|---|
| Raw TOC nodes | 73 | 45 |
| Study units derived | 39 | 25 |
| Unassigned source nodes | 0 | 0 |
| Same-page TOC merges resolved by direct source inspection | 1 | 3 |
| DIRECT | 8 | 14 |
| COMPONENT | 22 → 21 (post-review) | 6 |
| CROSS_DISCIPLINE | 0 | 0 |
| SUPPORTING_KNOWLEDGE | 2 | 1 |
| SPECIALIST_DETAIL | 3 → 4 (post-review) | 0 |
| REFERENCE_ONLY | 4 | 3 |
| UNCERTAIN | 0 | 1 |
| WEAK mappings | 6 → 2 (post-review) | 2 |
| Invalid MCC objective IDs | 0 | 0 |
| Study-unit derivation gate | PASS | PASS |
| Crosswalk gate | PASS | PASS |

---

## Dimension-by-Dimension Assessment

### 1. Clinical Medical Expert content
**Works as designed.** Cardiology's 30 clinically-testable units map almost entirely to Medical Expert presentation objectives (Chest pain, Palpitations, Dyspnea, etc.), each verified against the objective's own `causal_conditions`/`enabling_objectives` text before citing it. No schema change needed here.

### 2. Non-Medical-Expert content
**Works, with one addition needed.** ELOM leans heavily on the six role-level objectives (Collaborator, Leader/Manager, Professional, Scholar) which have no per-objective `mcc_id`/`legacy_id` — confirmed in Phase 2 that MCC represents these as one role-level competency statement, not discrete objectives. The crosswalk schema handled this by adding a `role_ref()` helper (parallel to `obj_ref()`) that explicitly sets `mcc_id`/`legacy_id` to `null` rather than fabricating one, and cites the specific objective *group* (e.g., "Leader/Manager - Allocate health care resources effectively") instead. **This distinction — object-level vs. role-level evidence — should be formalized as a documented schema variant before scaling**, since roughly a quarter of ELOM's DIRECT/COMPONENT mappings are role-level and this pattern will recur in every chapter's PHELO-adjacent content.

### 3. Presentation objectives
Cardiology confirmed MCC Medical Expert objectives are purely presentation-based (no objective titled "Acute Coronary Syndrome"). ELOM confirms the opposite pattern holds for its own domain: several ELOM topics (Consent, Truth-Telling, Negligence, Legal system, Dying patients, Indigenous health, Clinical informatics) **do** have their own dedicated Medical Expert objectives, not merely role-level coverage. **No single "everything is COMPONENT of a presentation" assumption should be hard-coded** — each chapter needs its own registry search, as both pilots demonstrate.

### 4. Legal/ethical content — jurisdiction model
**New requirement, successfully validated.** 15/25 ELOM units required jurisdiction metadata (`FEDERAL`, `PROVINCIAL_TERRITORIAL`, `CANADA_WIDE_PROFESSIONAL_PRINCIPLE`); 14/25 flagged `fresh_legal_verification_required = true`. Cardiology has no equivalent field and didn't need one. **The jurisdiction model is ELOM-specific (and will likely recur for OBGYN/consent-adjacent and Psychiatry/capacity-adjacent content), not universal — it should be an optional field present only where legally relevant, not forced onto every chapter's schema.**

### 5. Specialist exclusions
Both pilots produced legitimate `SPECIALIST_DETAIL`/`REFERENCE_ONLY` zero-coverage units with explicit reasons (Cardiology: cardiopulmonary bypass, landmark trials; ELOM: acronyms, bibliography, resource pointer). **Consistent pattern, no schema change needed**, but see Finding 4 below (mcc_evidence hygiene) which emerged from the Cardiology weak-mapping review and should be applied uniformly.

### 6. Source planning
Both pilots populated `clinical_source_organizations` per unit. Cardiology's source families are stable (CCS, Thrombosis Canada) since cardiac guidelines don't change jurisdiction. ELOM's are broader and jurisdiction-dependent (provincial Colleges, CMPA, Department of Justice, provincial legislation) — **confirms the task's instruction that ELOM verification will need a wider source-family net than clinical chapters.** No schema change; this is expected domain variation, already captured in the existing `clinical_source_organizations` + `fresh_legal_verification_required`/`fresh_guideline_required` fields (note: field name differs slightly between the two scripts — see Finding 1).

### 7. Page mapping
Both chapters show heavy `SECTION_INHERITED` precision (most units sourced from topic-level nodes, which don't get independent page anchors per the TOC schema). Cardiology: 30/39 SECTION_INHERITED. ELOM: also majority SECTION_INHERITED. **Confirms this is a structural property of the TOC extraction, not a per-chapter issue** — worth deciding once, chapter-independently, whether topic-level page refinement is worth doing before final manifest publication (deferred per Phase 3A's own recommendation).

### 8. Cross-disciplinary ownership
**Neither pilot produced a CROSS_DISCIPLINE primary classification**, despite both having genuinely multi-discipline-relevant content (Cardiology's edema/dyspnea units, ELOM's Indigenous-health-jurisdiction unit). Both cases were instead handled as DIRECT/COMPONENT + an optional `cross_discipline_note` field. This reveals a genuine finding: **CROSS_DISCIPLINE as a primary classification may be rare in practice** — Toronto Notes' own chapter placement usually makes primary ownership clear even when content is legitimately relevant elsewhere, and MCC's own "non-Medical-Expert roles apply to all disciplines" design principle means technically *most* professionalism/communication content is cross-disciplinary by default. **Recommend keeping CROSS_DISCIPLINE as a real option but not being alarmed if it's used rarely** — the `cross_discipline_note` field is doing the actual work in both pilots so far.

### 9. Question coverage weighting
Cardiology was built with an absolute `target_questions` model (Phase 3A), later retrofitted with `coverage_weight`/`minimum_question_coverage` in Phase 3B calibration (with the original absolute numbers preserved as `historical_absolute_estimate`, explicitly marked non-canonical). ELOM was built with the relative model from the start (`question_planning.coverage_weight`/`minimum_question_coverage`, no absolute-count field at all). **The direct-from-start approach (ELOM) is cleaner and should be the standard going forward** — no future chapter should introduce an absolute `target_questions` field, per the task's explicit instruction not to compute final absolute counts before a discipline-level budget exists.

---

## Concrete Schema/Rule Findings to Apply Before Scaling

1. **Field naming inconsistency:** Cardiology uses `fresh_guideline_required`; ELOM uses `fresh_legal_verification_required`. Both express the same concept ("this unit's answer depends on external, possibly-changing authority"). **Recommend standardizing on one field name** (e.g., `fresh_verification_required`) with a `verification_domain` sub-field (`"clinical_guideline"` vs. `"legal_regulatory"`) rather than two differently-named booleans, so downstream tooling doesn't need per-discipline special-casing.

2. **Role-level MCC evidence needs a documented schema variant.** `role_ref()` (mcc_id/legacy_id = null, cites a role + objective-group title) should be formalized as part of the canonical crosswalk schema, not an ad-hoc addition — expect PHELO, and likely Psychiatry (Professional/communication-heavy), to need it too.

3. **`mcc_evidence` hygiene for non-testable classifications.** The Cardiology weak-mapping review established the convention that `SPECIALIST_DETAIL`/`SUPPORTING_KNOWLEDGE`/`REFERENCE_ONLY` units should carry **empty** `mcc_evidence`, not a weak citation used to justify their existence — a citation implies a testable component. ELOM followed this convention from the start (`SU-ELOM-07`, `SU-ELOM-01/23/24` all have `mcc_evidence: []`). **This should be stated as an explicit rule in the shared methodology, not left implicit.**

4. **Jurisdiction and coverage-weight fields should be declared optional, not chapter-schema-specific.** Rather than each pilot script defining its own ad-hoc field set, a shared JSON Schema for `crosswalk.json` entries should define `jurisdiction` as present-when-relevant (default `NOT_APPLICABLE`) so a Cardiology-style output validates against the same schema as an ELOM-style output without either being "wrong" for omitting a field the other has.

5. **Same-page TOC merges are common enough to need a standard resolution protocol, not ad-hoc case-by-case handling.** Both pilots hit this (Cardiology: 1 merge; ELOM: 3 merges, plus a genuinely tricky content-misattribution case). The resolution method (search raw OCR pages for the disputed text, confirm true location, document in `structural_rationale`) worked reliably both times and should be written up as a standard step in the study-unit-derivation procedure for all remaining chapters, rather than rediscovered per chapter.

6. **`build_crosswalk()`'s coverage-weight derivation heuristic differs between the two scripts** (Cardiology derives it from the old `target_questions`; ELOM derives it from a `minimum_question_coverage`→weight lookup table). Since Cardiology's `target_questions` is being phased out per Finding 9 above, **the ELOM approach (weight and minimum coverage set directly by the mapper, not derived from a retired field) should become the single standard** for all future chapters.

---

## What Worked Well in Both Pilots (No Change Needed)

- Verifying every DIRECT/COMPONENT MCC evidence citation against the objective's actual registry content (not memory) before writing the rationale — caught real overstatements in the Cardiology weak-mapping review and prevented any in ELOM from the start.
- The three-way node-accounting model (assigned to a unit / organizational header / excluded artifact) cleanly proved full source-node coverage in both chapters with zero silent drops.
- `do_not_test` / low-priority flagging for specialist content, applied consistently.
- Explicit `UNRESOLVED`/`UNCERTAIN` tracking rather than force-mapping thin evidence (ELOM's Conscientious Objection; several Cardiology WEAK links kept honestly WEAK rather than upgraded).

---

## Recommendation

The core methodology (TOC inventory → study units → MCC crosswalk → audit) generalizes correctly across both a clinical and a non-clinical domain. The six findings above are refinements to make explicit and consistent, not fundamental redesigns. See the completion report for the `SCHEMA_READY_TO_SCALE` determination and recommended next steps.
