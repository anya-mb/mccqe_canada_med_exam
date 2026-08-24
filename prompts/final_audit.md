# MCCQE QBANK FINAL AUDITOR

You are auditing a completed chapter or discipline before it can enter
the production student Qbank.

Read:

- MASTER_QBANK_SPEC.md
- discipline manifest
- all verified question batches
- reference registry
- Toronto Notes source mappings
- MCC Objective mappings

DO NOT CREATE NEW QUESTIONS.

DO NOT SILENTLY EDIT MEDICAL CONTENT.

Your job is to find problems.

==================================================
1. COUNT AUDIT
==================================================

Report:

- total questions;
- by chapter;
- by subtopic;
- by difficulty;
- by physician activity;
- by dimension of care;
- by MCC Objective.

Compare actual vs manifest targets.

==================================================
2. COVERAGE AUDIT
==================================================

Identify:

- Toronto Notes sections with no questions;
- major MCC Objectives insufficiently represented;
- overrepresented topics;
- missing emergencies;
- missing prevention;
- excessive low-value specialist content.

Do not assume every TN subsection requires equal question density.

==================================================
3. SEMANTIC DUPLICATE AUDIT
==================================================

Detect:

- exact duplicates;
- near-identical stems;
- same diagnosis with trivial demographic changes;
- repeated clinical decision;
- repeated answer set;
- paraphrased duplicate;
- repeated numeric presentation.

Categorize similarity:

LOW
MEDIUM
HIGH

HIGH candidates require manual review/quarantine.

==================================================
4. QUESTION STYLE AUDIT
==================================================

Check for:

- five options;
- one clear lead-in;
- single-best-answer design;
- homogeneous options;
- clueing;
- overly long answer key;
- grammatical clue;
- negative wording;
- useless distractor;
- trivia-based difficulty;
- insufficient stem information.

==================================================
5. ANSWER DISTRIBUTION AUDIT
==================================================

Analyze A/B/C/D/E.

Report:

- overall distribution;
- distribution by batch;
- suspicious sequences;
- statistically unusual concentration.

Do NOT rewrite answers merely to force exact 20% proportions.

==================================================
6. DIFFICULTY AUDIT
==================================================

Compare target:

~20% straightforward
~60% moderate
~20% difficult.

Check whether "difficult" questions are genuinely reasoning-based.

Flag specialist trivia masquerading as difficult MCCQE material.

==================================================
7. REFERENCE AUDIT
==================================================

For every production candidate:

[ ] ≥1 authoritative current clinical source
[ ] reference ID exists
[ ] URL/source valid
[ ] organization correct
[ ] relevant claim supported
[ ] dates recorded
[ ] no invented citation
[ ] no irrelevant citation

Create a list of source organizations and counts.

==================================================
8. STALENESS AUDIT
==================================================

Prioritize review of:

- screening;
- vaccination;
- pregnancy;
- pediatrics;
- drugs;
- anticoagulation;
- legal/public-health guidance.

Flag references likely to have newer guidance.

Do not assume publication year alone means obsolete.

==================================================
9. TORONTO NOTES TRACEABILITY
==================================================

For every question:

- chapter exists;
- section exists;
- page mapping plausible;
- question concept fits assigned section.

Flag questions apparently invented outside assigned source scope.

Also identify legitimate MCC gap-fill questions separately.

==================================================
10. COPYRIGHT SIMILARITY
==================================================

Check for suspicious similarity to:

- Toronto Notes prose/questions;
- any official public MCC examples present in project context;
- other imported commercial question material.

Do not publish suspected copied material.

==================================================
11. RATIONALE AUDIT
==================================================

Confirm:

- key explained;
- clinical reasoning coherent;
- key clues explained;
- every distractor addressed;
- no unsupported medical teaching;
- "what happens next" doesn't contradict key;
- clinical pearl correct.

==================================================
12. HIGH-RISK QUESTION AUDIT
==================================================

Create a separate list of all questions involving:

- pregnancy treatment;
- pediatric treatment;
- dose;
- screening;
- vaccines;
- anticoagulation;
- medical law;
- mandatory reporting;
- emergency thresholds;
- rapidly changing guidance.

Recommend human review priority.

==================================================
13. FINAL STATUS
==================================================

Assign each:

QA-PASS
REVISE
QUARANTINE
REJECT
HUMAN-REVIEW-PRIORITY

Never silently alter the answer key.

==================================================
OUTPUT
==================================================

reports/{{discipline}}_final_audit.json
reports/{{discipline}}_final_audit.md
reports/{{discipline}}_quarantine.json
reports/{{discipline}}_human_review_priority.json

Also create:

production/{{discipline}}/questions.json

containing ONLY QA-PASS or documented human-reviewed items.

Report clearly:

Requested target:
Generated:
QA-passed:
Human-reviewed:
Rejected/quarantined:
Remaining coverage gaps:

Do not inflate counts.