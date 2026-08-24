You are preparing the Medicine curriculum manifest for an MCCQE question bank.

READ FIRST:

1. MASTER_QBANK_SPEC.md
2. the attached Toronto Notes 2025 PDF
3. current MCC Examination Objectives
4. current MCC Study Smarter discipline mapping
5. current MCCQE Blueprint

DO NOT GENERATE QUESTIONS YET.

Your task is to construct the complete Medicine manifest that later
generation agents will follow.

==================================================
TORONTO NOTES 2025 PRIMARY CHAPTERS
==================================================

Use these chapters IN THIS ORDER:

1. Cardiology and Cardiac Surgery
   chapter code: C
   PDF pages: 91–174
   TN pages: C1–C84

2. Clinical Pharmacology
   code: CP
   PDF: 175–188
   TN: CP1–CP14

3. Dermatology
   code: D
   PDF: 189–246
   TN: D1–D58

4. Endocrinology
   code: E
   PDF: 309–376
   TN: E1–E68

5. Gastroenterology
   code: G
   PDF: 435–492
   TN: G1–G58

6. Geriatric Medicine
   code: GM
   PDF: 573–594
   TN: GM1–GM22

7. Hematology
   code: H
   PDF: 655–718
   TN: H1–H64

8. Infectious Diseases
   code: ID
   PDF: 719–778
   TN: ID1–ID60

9. Nephrology
   code: NP
   PDF: 821–870
   TN: NP1–NP50

10. Neurology
    code: N
    PDF: 871–932
    TN: N1–N62

11. Palliative Medicine
    code: PM
    PDF: 1299–1310
    TN: PM1–PM12

12. Respirology
    code: R
    PDF: 1455–1494
    TN: R1–R40

13. Rheumatology
    code: RH
    PDF: 1495–1530
    TN: RH1–RH36

SUPPLEMENTAL when MCC-relevant:

Emergency Medicine
PDF 247–308 / ER1–ER62

Family Medicine
PDF 377–434 / FM1–FM58

Medical Genetics
PDF 779–790 / MG1–MG12

Medical Imaging
PDF 791–820 / MI1–MI30

==================================================
TARGET
==================================================

Approximately 1,000 questions.

Planning targets:

Cardiovascular — 120
Clinical pharmacology/toxicology — 50
Dermatology/allergy — 50
Endocrinology — 90
Gastroenterology/hepatology — 100
Geriatrics + palliative — 60
Hematology/oncology — 80
Infectious disease — 90
Nephrology/fluid/electrolyte/acid-base — 90
Neurology — 100
Respirology — 100
Rheumatology/MSK — 70

These targets may move modestly after MCC Objective mapping.

==================================================
REQUIRED WORK
==================================================

For EVERY chapter:

1. Open its Toronto Notes table-of-contents page.

2. Extract every major section and subsection in the actual Toronto Notes order.

3. Determine the TN page range for each meaningful study section.

4. Map it to relevant MCC Examination Objectives.

5. Classify MCC importance:
   - Core
   - Important
   - Supporting
   - Low MCC priority

6. Decide approximately how many questions the section deserves.

Do NOT allocate based simply on number of Toronto Notes pages.

Base allocation on:

- MCC objective importance;
- clinical frequency;
- emergency importance;
- decision-making value;
- likelihood of testing assessment/management;
- need for Canadian-specific knowledge.

7. Identify questions that should test:
   - diagnosis
   - investigations
   - management
   - acute stabilization
   - prevention
   - communication/professional behaviour

8. Identify potential Toronto Notes vs current-guideline areas requiring
fresh verification.

9. Divide the discipline into generation batches of 40–60 questions.

==================================================
CARDIOLOGY SPECIAL RULE
==================================================

Toronto Notes contains Cardiac Surgery.

Do not allow specialist operative content to dominate.

For surgery-related cardiovascular content include only graduate-level:

- indications;
- clinical recognition;
- complications;
- need for referral/procedure;
- emergencies.

==================================================
OUTPUT
==================================================

Create:

manifests/medicine.json

Schema:

{
  "discipline": "Medicine",
  "target_questions": 1000,
  "chapters": [
    {
      "chapter": "...",
      "code": "...",
      "pdf_pages": "...",
      "tn_pages": "...",

      "sections": [
        {
          "section": "...",
          "subsections": [],
          "tn_pages": "...",
          "pdf_pages": "...",

          "mcc_objectives": [],

          "priority": "Core",

          "target_questions": 25,

          "target_question_mix": {
            "assessment_diagnosis": 12,
            "management": 9,
            "communication": 2,
            "professional": 2
          },

          "dimensions": [],

          "high_risk_facts": [],

          "current_sources_to_research": []
        }
      ]
    }
  ],

  "batches": [
    {
      "batch_id": "MED-CARD-B01",
      "question_ids": "MED-CARD-001..050",
      "target": 50,
      "sections": [],
      "tn_pages": [],
      "mcc_objectives": []
    }
  ],

  "coverage_gaps": []
}

Also create:

reports/medicine_manifest.md

The report should explain:

- topic distribution;
- MCC Objective coverage;
- any important MCC gaps not adequately represented by Toronto Notes;
- planned gap-fill questions;
- total number of batches.

STOP after manifest generation.
Do not generate actual questions.