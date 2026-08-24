# MCCQE BATCH QUESTION GENERATOR

MODE: GENERATE

Read and obey:

1. MASTER_QBANK_SPEC.md
2. the supplied discipline manifest
3. the supplied batch specification
4. the attached Toronto Notes 2025 PDF
5. current MCC Examination Objectives
6. current authoritative medical sources

==================================================
INPUT VARIABLES
==================================================

DISCIPLINE = {{discipline}}

BATCH_ID = {{batch_id}}

QUESTION_IDS = {{question_ids}}

TARGET_QUESTION_COUNT = {{target_count}}

TORONTO_NOTES_CHAPTER = {{tn_chapter}}

TORONTO_NOTES_SECTIONS = {{tn_sections}}

TORONTO_NOTES_PAGE_RANGES = {{tn_page_ranges}}

PDF_PAGE_RANGES = {{pdf_page_ranges}}

MCC_OBJECTIVES = {{mcc_objectives}}

TARGET_DIFFICULTY =
20% straightforward
60% moderate
20% difficult

TARGET_PHYSICIAN_ACTIVITIES = {{activity_mix}}

TARGET_DIMENSIONS = {{dimension_mix}}

==================================================
PHASE 1 — READ THE ASSIGNED TORONTO NOTES SOURCE
==================================================

BEFORE WRITING A SINGLE QUESTION:

Open and inspect the assigned Toronto Notes pages.

Create an internal/source-grounding outline containing:

- section titles;
- subsection titles;
- presentations;
- diagnostic approaches;
- investigations;
- management concepts;
- emergencies;
- complications;
- prevention;
- important distinctions.

Do not quote/copy the prose.

Do not generate a topic merely because you remember it from pretraining.

Every question must map to:

A. a concept present in these assigned TN pages;

OR

B. an explicitly authorized MCC coverage-gap item in the batch spec.

If neither applies:
do not write it.

==================================================
PHASE 2 — MCC OBJECTIVE CONFIRMATION
==================================================

Confirm that the proposed clinical reasoning task is appropriate for
a Canadian medical graduate entering supervised practice.

Map each item to at least one MCC Objective whenever possible.

Discard specialist-level proposed questions.

==================================================
PHASE 3 — BUILD SOURCE PACKET BEFORE WRITING
==================================================

Research current authoritative clinical guidance.

For each intended clinical decision establish BEFORE question generation:

- proposed concept;
- clinical claim;
- authoritative source;
- current recommendation;
- publication/update date;
- exact source section/table/recommendation that supports it.

Create:

source_packet.json

No question may be generated around a clinical decision until its
supporting claim has been source-verified.

Do not search for citations after writing the answer.

==================================================
PHASE 4 — HIGH-RISK FACT CHECK
==================================================

Extra-check any proposed item involving:

- numerical cutoff;
- age threshold;
- dose;
- medication;
- pregnancy;
- pediatrics;
- screening;
- vaccine;
- timing interval;
- diagnostic criterion;
- anticoagulation;
- public health;
- law.

Prefer two corroborating authoritative sources when practical.

If reliable support is not found:
DROP that proposed question.

==================================================
PHASE 5 — WRITE ORIGINAL MCCQE-STYLE QUESTIONS
==================================================

Generate only ORIGINAL questions.

Default construction:

- clinical stem;
- clear lead-in;
- five options;
- one best answer;
- four plausible distractors.

Aim for authentic MCC-style clinical reasoning.

Do not copy:

- Toronto Notes cases/questions;
- MCC sample cases;
- commercial Qbanks.

Question forms should include an appropriate mix of:

MOST LIKELY DIAGNOSIS

BEST NEXT STEP

INITIAL INVESTIGATION

BEST/CONFIRMATORY INVESTIGATION

IMMEDIATE STABILIZATION

FIRST-LINE MANAGEMENT

COMPLICATION

PREVENTION / SCREENING

COMMUNICATION / PROFESSIONAL ACTION

Do not make every question "most likely diagnosis."

==================================================
CLINICAL VIGNETTES
==================================================

Use realistic patient scenarios.

Include only clinically relevant information.

When useful include:

- age;
- clinical history;
- vitals;
- physical examination;
- medications;
- laboratory data;
- imaging description.

Do not make every vignette identical in structure.

Use SI units.

When a normal range is needed to answer fairly, include it.

==================================================
DISTRACTORS
==================================================

Every distractor must be clinically plausible.

Prefer distractors based on:

- common diagnostic confusion;
- action that happens later but not yet;
- test that is reasonable but not first;
- therapy appropriate in another patient;
- contraindicated treatment;
- alternative diagnosis missing a key criterion.

Do not use absurd distractors merely to fill five options.

If a competent graduate could reasonably defend two choices:
rewrite the question.

==================================================
DIFFICULTY
==================================================

Straightforward:
recognize common presentation or standard first-line decision.

Moderate:
requires integration of multiple findings or correct sequencing.

Difficult:
requires discrimination between plausible alternatives,
interpretation, comorbidity, contraindications, or management priority.

Never use rare trivia as the main source of difficulty.

==================================================
PHASE 6 — WRITE DETAILED EXPLANATION
==================================================

For EACH question include:

1. Correct answer.

2. Answer summary.

3. Detailed clinical reasoning.

4. Key clues:
   explain why each important clue matters.

5. Why the keyed option is the BEST answer.

6. Why EACH of the four distractors is less appropriate.

For each distractor, when useful explain:
"When would this answer have been appropriate?"

7. What happens next:
for sequential management questions.

8. Clinical pearl.

9. MCC Objective.

10. Physician activity.

11. Dimension of care.

12. Difficulty.

13. Toronto Notes study anchor.

14. Current clinical references.

Do not make rationales artificially brief.

==================================================
PHASE 7 — REFERENCE ATTRIBUTION
==================================================

For every question record reference IDs.

Every important clinical recommendation in the rationale must be supportable
by the cited references.

Store references separately.

For each reference include:

- organization;
- title;
- URL;
- date/version;
- accessed date;
- exact claim(s) supported;
- locator.

Do not cite Toronto Notes as the only evidence for a current management decision.

==================================================
PHASE 8 — SELF-CHECK
==================================================

Before accepting a question ask:

[ ] Is one answer clearly better?
[ ] Does the stem provide enough information?
[ ] Are all five answers the same logical type?
[ ] Is the key current?
[ ] Does the cited source actually support the key?
[ ] Are numerical facts verified?
[ ] Is the Toronto Notes mapping accurate?
[ ] Is it appropriate for MCCQE level?
[ ] Is it original?
[ ] Is it meaningfully different from other questions in this batch?
[ ] Is the difficulty caused by reasoning rather than trick wording?
[ ] Are all distractors explained?

If not:
rewrite or discard.

==================================================
OUTPUT FILES
==================================================

Write:

batches/{{BATCH_ID}}/batch_spec.json
batches/{{BATCH_ID}}/source_packet.json
batches/{{BATCH_ID}}/questions.candidate.json
batches/{{BATCH_ID}}/references.json
batches/{{BATCH_ID}}/generation_report.json

Do NOT call questions "verified" yet.

Set:

verification.final_status = "pending"

The next step is blind independent verification.

==================================================
GENERATION REPORT
==================================================

Report:

- requested questions;
- generated questions;
- discarded proposed questions;
- reasons for discarding;
- topic counts;
- difficulty counts;
- physician-activity counts;
- reference organizations;
- questions containing high-risk facts;
- questions where current guidance differs from TN2025.

Accuracy beats hitting the exact requested count.