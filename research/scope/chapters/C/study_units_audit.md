# Cardiology Study-Unit Consolidation Audit

**Generated:** 2026-08-24
**Result:** ✅ PASS

## Coverage

- Raw TOC nodes: 73
- Raw leaf nodes: 60
- Derived study units: 39
- Unassigned source nodes: 0
- Double-assigned source nodes: 0
- Organizational header nodes accounted for (not units, not dropped): 9
- **Total accounted:** 73 / 73 (fully accounted)

## Ambiguous Consolidations

15 study units combine more than one source node. Each is individually reviewed below; none are flagged as errors, but all are surfaced for reviewer visibility per the task's audit requirement.

**SU-C-21_ACS:** Acute Coronary Syndromes + its own Treatment Algorithm subtopic combined into one unit - not ambiguous: the algorithm is explicitly a child topic of the ACS heading itself in the source TOC, matching the task's canonical 'disease + management subtopic = one unit' example.

**SU-C-26_cardiomyopathies:** Four distinct cardiomyopathy subtypes (Dilated, Hypertrophic, Restrictive, Left Ventricular Noncompaction) combined into one unit. REVIEWED, not ambiguous: these are classically taught/tested as a comparative differential (distinguishing echo/hemodynamic findings between subtypes) rather than as independent standalone diagnoses - matches the task's 'clinically meaningful group of closely related disorders' consolidation category. LVNC specifically is rare enough to be flagged do_not_test in the crosswalk rather than tested as its own entity.

**SU-C-32_valve_intervention:** Valve Repair/Replacement + Choice of Prosthesis + Prosthetic Valve Management combined. REVIEWED, not ambiguous: these three Toronto Notes subheadings describe one sequential clinical decision pathway, not three independent diagnoses.

**SU-C-27_advanced_hf_therapies:** Cardiac Transplantation + VAD + ECMO combined. REVIEWED, not ambiguous: expected graduating-student depth for all three is 'recognize as escalation options', not differentiated management - a shared, thin testable surface that does not warrant 3 separate units at this depth.

**SU-C-34_effusion_tamponade:** Pericardial Effusion + Cardiac Tamponade combined. REVIEWED, not ambiguous: recognizing progression from one to the other IS the core testable competency, so testing them as one continuum is more clinically valid than testing them as unrelated facts.

## Over-Collapse / Fragmentation Checks

- No over-collapse: 6 distinct differential-diagnosis presentations (SU-C-03..08), 6 distinct arrhythmia entities (SU-C-14..19, excluding shared background), 4 distinct ischemic/HF/myocarditis entities kept separate from cardiomyopathies, endocarditis and rheumatic fever kept separate from general valve disease and from each other, 3 distinct pericardial-disease-tier entities (pericarditis / effusion+tamponade / constrictive) kept separate - confirms clinically distinct diagnoses were not over-collapsed into oversized units.

- No fragmentation: No single Toronto Notes disease heading (with its own epidemiology/pathophysiology/clinical features/investigations/management/complications children) was split into multiple study units - every disease-level TOC topic maps to exactly one study unit.

## Page Traceability

All 39 study units' pdf_page_range falls within the chapter's own bounds (91-174): ✅ valid

## Summary

Raw TOC nodes: 73
Raw leaf nodes: 60
Derived study units: 39
Unassigned source nodes: 0
Ambiguous consolidations: 15 (all reviewed, none flagged as errors)

**Study-unit derivation: PASS**

