1. Current MCCQE format and examination framework

As of August 24, 2026, the current official examination name is the Medical Council of Canada Qualifying Examination (MCCQE), formerly called MCCQE Part I.

The MCCQE is a one-day computer-based examination consisting of 230 single-best-answer multiple-choice questions, divided into two sections of 115 questions. Candidates have 2 hours and 40 minutes for each section, with an optional 45-minute break between them. The former Clinical Decision-Making written-response component was removed beginning with the April 2025 examination format.

The MCC describes the examination as assessing critical medical knowledge and clinical decision-making at the level expected of a medical student completing a Canadian medical degree and entering supervised practice.

The examination is based on two central official resources:

MCC Examination Objectives, which define the attributes and competencies expected of graduates entering residency in Canada; and
the MCCQE Blueprint, which determines how examination content is distributed.

The MCC explicitly states that the Examination Objectives provide the foundation of MCCQE content and guide question development.

Blueprint

Current physician-activity weightings are:

Assessment / Diagnosis — 45% ±5
Management — 35% ±5
Communication — 10% ±5
Professional Behaviours — 10% ±5

Current dimensions-of-care weightings are:

Health Promotion & Illness Prevention — 20% ±5
Acute — 35% ±5
Chronic — 30% ±5
Psychosocial Aspects — 15% ±5.

The MCC Examination Objectives are organized using seven adapted CanMEDS roles:

Medical Expert
Collaborator
Communicator
Health Advocate
Leader/Manager
Professional
Scholar.

The 2026 MCC Study Smarter guide states that the six broad disciplines are represented more or less equally on the MCCQE—approximately one-sixth of the examination each. It also specifically cautions that its discipline categorization is not exhaustive, objectives may overlap several disciplines, and non-Medical Expert roles apply across disciplines.

Therefore, Toronto Notes content should not be weighted solely by chapter length or number of associated MCC Objectives.

2. Role of Toronto Notes in the curriculum crosswalk

The supplied source is Toronto Notes 2025, 41st Edition.

Toronto Notes should be used as the project's:

study-organization framework;
chapter/topic/subtopic hierarchy;
reading sequence;
study-page anchor;
source for identifying the concepts a learner has just reviewed.

It must not be treated as the sole authority for:

current MCC scope;
current diagnostic criteria;
treatment recommendations;
medication selection or dosing;
vaccination schedules;
screening recommendations;
Canadian law;
rapidly changing clinical guidance.

Toronto Notes itself explains that its chapters commonly contain basic review, common differential diagnoses, diagnoses with clinical features/investigations/management/complications/prognosis, and common medications.

It also states that a Toronto Notes “Key Objective” icon may represent an objective or condition associated with either the Medical Council of Canada or the National Board of Medical Examiners. Therefore a Toronto Notes icon is useful as a study signal but is not sufficient evidence for a DIRECT MCC mapping.

The required hierarchy is therefore:

Toronto Notes 2025 → study organization
Current MCC Objectives → examination scope
MCC Blueprint → type/distribution of competency testing
Current authoritative Canadian guidelines → clinical answer

3. Toronto Notes 2025 structural inventory

The project should use the already extracted local Toronto Notes OCR/index as the canonical source for the book's structure.

The searchable Toronto Notes file contains the top-level chapter structure and chapter codes used throughout the book.

The local pipeline should create and validate a complete hierarchy:

chapter → section → meaningful topic → meaningful subtopic

For every node, preserve:

exact heading;
chapter code;
parent/child relationship;
Toronto Notes printed page;
Toronto Notes page range where determinable;
physical PDF page range;
structural type.

Do not infer these from the broad Deep Research memo when they can be determined from the locally indexed Toronto Notes pages.

Corrected Cardiology example

The previous memo used C1–C90. This is incorrect.

The searchable Toronto Notes 2025 file shows the final Cardiology and Cardiac Surgery page as C84.

Therefore a chapter-level record should use the locally verified range, approximately:

{
  "chapter": "Cardiology and Cardiac Surgery",
  "chapter_code": "C",
  "tn_pages": "C1-C84"
}

All other page ranges should likewise be determined from the local index rather than copied from the original Deep Research narrative.

Important operational correction

The broad research memo referred to files such as:

toc_inventory.json
objectives_registry.json
gap_analysis.json
medicine.scope.json

The memo itself does not prove these files were actually created.

Only artifacts physically present in the repository should be considered real.

The local Claude/Python pipeline must create and schema-validate the canonical versions.

4. Distribution across the six question-bank disciplines

For study organization, the Toronto Notes chapters can be assigned primarily as follows.

Medicine

Primary chapters:

Cardiology and Cardiac Surgery — C
Clinical Pharmacology — CP
Dermatology — D
Endocrinology — E
Family Medicine — FM
Gastroenterology — G
Geriatric Medicine — GM
Hematology — H
Infectious Diseases — ID
Medical Genetics — MG
Medical Imaging — MI
Nephrology — NP
Neurology — N
Palliative Medicine — PM
Respirology — R
Rheumatology — RH

Family Medicine, Genetics and Imaging should be inventoried rather than silently omitted. Where their material belongs more naturally to another discipline, it can be cross-linked instead of duplicated.

Pediatrics

Primary chapter:

Pediatrics — P

Relevant material from Genetics, Imaging, Public Health, ELOM and other chapters may be cross-linked when a pediatric context materially changes the decision.

Obstetrics & Gynecology

Use the actual Toronto Notes study order:

Gynecology — GY
Obstetrics — OB

Relevant Genetics, Pharmacology, Imaging and PHELO material may be linked without disrupting this sequence.

Surgery

Primary chapters:

Anesthesia — A
Emergency Medicine — ER
General and Thoracic Surgery — GS
Neurosurgery — NS
Ophthalmology — OP
Orthopedic Surgery — OR
Otolaryngology — OT
Plastic Surgery — PL
Urology — U
Vascular Surgery — VS

Questions should remain at graduating-medical-student level rather than becoming specialty-board questions.

Psychiatry

Primary:

Psychiatry — PS

Relevant Pediatrics, Geriatrics, Clinical Pharmacology and ELOM topics can be linked when the clinical context differs meaningfully.

PHELO

Primary:

Ethical, Legal and Organizational Medicine — ELOM
Public Health and Preventive Medicine — PH

Communication, professionalism, prevention and health-advocacy objectives should nevertheless also occur naturally within clinical disciplines because MCC non-Medical Expert roles apply across disciplines.

5. MCC mapping methodology

Every meaningful Toronto Notes study unit should be independently compared against the current official MCC Examination Objectives.

Do not equate every microscopic Toronto Notes heading with a separate examination topic.

For example, a diagnosis may contain headings for:

epidemiology;
pathophysiology;
clinical features;
investigations;
management;
complications.

Those are generally dimensions of understanding the same clinical study unit, not six independent question-bank topics. This corresponds to Toronto Notes' own chapter design.

Use these mapping classes:

DIRECT

A current MCC Objective clearly addresses the presentation, diagnosis, problem or competency.

COMPONENT

The Toronto Notes item represents an important component of a broader MCC Objective.

For example, a diagnostic method may be required to satisfy an objective even though it is not a separately named MCC Objective.

CROSS_DISCIPLINE

The item is MCC-relevant but primarily belongs to another discipline or requires meaningful cross-disciplinary context.

SUPPORTING_KNOWLEDGE

Knowledge contributes to clinical reasoning but should generally not be tested as a standalone fact.

SPECIALIST_DETAIL

The material exceeds the expected MCCQE level for a graduating medical student.

REFERENCE_ONLY

Reference lists, glossaries, drug tables, bibliographies and similar material that do not independently define a clinical competency.

UNCERTAIN

A defensible relationship to current MCC Objectives cannot yet be established.

For DIRECT mappings, the canonical dataset should contain:

official MCC Objective title;
current or Legacy ID where provided by MCC;
CanMEDS role;
official MCC URL;
mapping strength;
verification date.

Never fabricate an objective ID.

The MCC's 2026 Study Smarter guide can be used as an additional discipline-mapping signal, but the MCC explicitly says those discipline lists are not exhaustive.

6. Appropriate depth of knowledge

The scope dataset should describe what the candidate must be capable of doing, rather than prematurely hard-code treatment recommendations.

Use:

CORE_ACTION

Candidate should be capable of recognizing the problem and performing appropriate initial assessment and management expected at the end of Canadian medical school.

RECOGNIZE_AND_ACT

Candidate should recognize an important or dangerous condition, initiate appropriate assessment/stabilization, and know when escalation/referral is required.

RECOGNIZE

Candidate should recognize the presentation, formulate an appropriate differential and identify broad next steps.

CONTEXT_ONLY

Background information that helps clinical reasoning but is rarely suitable for a standalone MCCQE question.

OUT_OF_SCOPE_DETAIL

Subspecialist knowledge beyond the expected examination depth.

Examples of appropriately worded competencies

Instead of:

“Stroke: give urgent thrombolysis.”

use:

Recognize suspected acute stroke, initiate rapid assessment and neuroimaging, and determine eligibility for reperfusion treatment including IV thrombolysis and/or endovascular thrombectomy.

Current Canadian Stroke Best Practices make treatment eligibility and imaging central; thrombolysis is not an automatic treatment for every patient with stroke.

Instead of:

“Pulmonary embolism: spiral CT and heparin.”

use:

Assess hemodynamic stability and clinical probability in suspected PE, select the appropriate diagnostic pathway, and recognize when anticoagulation or escalation of therapy is required.

Current Thrombosis Canada guidance uses stability, pretest probability, D-dimer and CTPA/V/Q testing in context; anticoagulation strategy depends on probability, timing, bleeding risk and confirmed/risk-stratified disease.

Instead of:

“Hypertension: detect with CBC.”

use:

Accurately identify and confirm hypertension using appropriate standardized blood-pressure assessment and determine appropriate initial evaluation and management.

The current Hypertension Canada primary-care guideline bases diagnosis on standardized BP measurement and confirmation—not CBC.

The scope crosswalk should generally stop at this competency level. Exact changing thresholds and drug regimens should be verified during question-batch generation.

7. Priority assignment

Priority should be based on official MCC relevance plus clinical importance, not model impressions of what is “high yield.”

Use:

MCC_PRIORITY_1 — core/common/critical
MCC_PRIORITY_2 — important
MCC_PRIORITY_3 — supporting but testable
MCC_PRIORITY_4 — contextual
OUT_OF_SCOPE_SPECIALIST

Useful priority evidence includes:

direct MCC Objective;
current Study Smarter discipline mapping;
common or critical presentation;
emergency consequences;
management relevance;
prevention relevance;
communication/professionalism relevance.

The MCC itself advises candidates to focus on common or critical patient presentations, construct differential diagnoses, identify key findings, and determine investigations and management plans.

The scope dataset should therefore identify major clinical competencies rather than encode unverified treatments.

Examples of reasonable Priority-1 domains

Depending on final objective mapping, likely Priority-1 areas include clinically important presentations such as:

chest pain / acute coronary syndromes;
cardiac arrest and important arrhythmias;
stroke/TIA;
seizures and altered consciousness;
dyspnea and acute respiratory compromise;
sepsis;
meningitis;
diabetic emergencies;
important electrolyte emergencies;
obstetric hemorrhage;
hypertensive disorders of pregnancy;
sick/febrile young infant;
dehydration/shock;
suicidality;
acute psychosis/safety;
consent/capacity/confidentiality;
epidemiologic interpretation;
screening/prevention.

But the canonical Priority-1 designation should be confirmed against actual current MCC objective mappings rather than simply copied from this illustrative list.

8. Corrected examples of previously erroneous clinical scope

Several examples in the original memo must not enter the manifests.

Febrile young infant

Original:

“recognize required investigations/BCG.”

Correct:

Recognize fever in a young infant as a potentially serious presentation, assess stability and age-specific risk, and select appropriate investigation, disposition and empiric management based on current pediatric guidance.

Canadian Paediatric Society guidance for febrile young infants uses age, clinical appearance, urinalysis, inflammatory markers and microbiologic evaluation/risk stratification. BCG is not part of this acute evaluation.

PHAC's Canadian Immunization Guide states that BCG vaccination is not recommended for routine use in any Canadian population, although it may be considered in selected exceptional high-TB-risk circumstances.

Therefore the BCG statement must be deleted.

Hypertension

Original:

“detect hypertension by CBC.”

Delete.

Correct competency:

Measure and confirm elevated blood pressure appropriately, assess cardiovascular risk/target-organ consequences where appropriate, and initiate evidence-based management.

Current Hypertension Canada guidance establishes standardized BP measurement and confirmation as the diagnostic basis.

Acute stroke

Original:

“FAST signs, urgent thrombolysis.”

Correct competency:

Recognize acute stroke, establish time/last-known-well information, obtain urgent appropriate imaging, and identify candidates for evidence-based reperfusion and acute stroke management.

Current Canadian Stroke Best Practices include both IV thrombolysis and endovascular thrombectomy according to eligibility and imaging.

Pulmonary embolism

Original:

“spiral CT/angiography and APTT/heparin.”

Correct competency:

Assess PE probability and stability, choose an appropriate diagnostic pathway, and initiate/escalate treatment according to risk and current Canadian thrombosis guidance.

Current Canadian guidance uses a probability-based algorithm rather than automatic CTPA for every patient.

Suicidality

Original:

“sedating medication and hospitalization.”

Correct competency:

Assess and quantify suicide risk, identify contributing conditions, ensure immediate patient safety, and determine the appropriate level of observation/disposition and treatment.

The MCC's own suicidal-behaviour objective specifically requires determination of risk and appropriate management, including urgent hospitalization and continuous observation when imminent risk is present. Sedation is not described as the general core response to suicidality.

These corrected formulations illustrate how scope statements should be written: action-oriented but not unnecessarily tied to potentially changing therapeutic specifics.

9. Specialist and low-value Toronto Notes content

Toronto Notes includes information extending beyond what should routinely become MCCQE practice questions.

Potential OUT_OF_SCOPE_DETAIL or SUPPORTING_KNOWLEDGE categories include:

detailed operative technique;
specialist procedural parameters;
highly specific chemotherapy regimens;
rare molecular variants without clinical decision relevance;
exhaustive genetic tables;
brand-name medication memorization;
detailed imaging acquisition technique;
anatomy/pathophysiology minutiae that do not affect clinical decisions.

However, these classifications must be made node by node.

Do not automatically declare a rare disease out of scope simply because it is uncommon. Some uncommon conditions may still be MCC-relevant because they are dangerous or linked to a specific official presentation/objective.

Similarly, basic science should not automatically receive zero coverage when it is necessary to interpret a clinically meaningful presentation.

10. MCC gaps not adequately represented in Toronto Notes

The original memo speculated about possible future MCC topics such as CRISPR, personalized medicine and emerging genetic technologies.

Those speculative gap statements should be removed.

A legitimate MCC_GAP_FILL unit should be created only when an actual comparison against the current official MCC Objectives demonstrates that an MCC competency is absent or inadequately represented in Toronto Notes.

The gap-analysis process should therefore be:

current MCC objective registry
        ↓
compare with all Toronto Notes study units
        ↓
unmapped relevant objective?
        ↓
yes → MCC_GAP_FILL candidate

Gap-fill topics may include areas of:

communication;
professionalism;
health advocacy;
patient safety;
health equity;
Indigenous health/cultural safety;
population health;
current ethical/legal competencies;

but only where current official MCC evidence supports the gap.

The 2026 Study Smarter guide explicitly notes that non-Medical Expert roles apply to all disciplines.

11. Cross-disciplinary ownership

Cross-disciplinary topics should use:

PRIMARY_OWNER
CROSS_LINK
DISTINCT_CONTEXT

The primary owner should be determined from:

the Toronto Notes study location;
the strongest MCC discipline/context mapping;
the intended learner workflow.

Avoid arbitrary rules such as:

“all vaccination questions belong to PHELO”

or

“all childhood depression belongs to Pediatrics.”

A vaccination question in pregnancy may be naturally OBGYN-specific; immunization principles may primarily belong to PHELO; pediatric vaccine counselling may appropriately live within Pediatrics.

Similarly, psychiatric disorders in children may support both Psychiatry and Pediatrics where the decisions being tested differ.

Separate questions are justified when the context changes the clinical reasoning, for example:

VTE treatment during pregnancy versus non-pregnant treatment;
depression in an adolescent versus older adult;
capacity assessment in psychiatric illness versus general medical care.

Otherwise use cross-links rather than near-duplicate questions.

12. Question-bank volume

The original memo proposed:

Medicine ~1,100
Pediatrics ~980
OBGYN ~1,010
Surgery ~1,020
Psychiatry ~950
PHELO ~940

These values should be treated as provisional project planning estimates only.

They are not MCC-recommended numbers.

The MCC's current Study Smarter guide says the six disciplines are represented more or less equally on the actual examination, with roughly one-sixth of the exam allocated to each discipline despite substantial differences in the number of objectives assigned to individual disciplines.

For the learning bank, it may still be reasonable for Medicine to contain more questions because its Toronto Notes/MCC scope is broader. But that should be calculated after the canonical study units are mapped.

The manifest process should therefore produce:

evidence_based_recommended_count
normalized_target_count
Recommended rule

Approximately 1,000 ±10% per discipline is a reasonable product target, not an MCC fact.

Question density should depend on:

number of meaningful MCC-relevant study units;
clinical importance;
number of distinct decisions that can be tested;
risk of missing the condition;
breadth of assessment/management/prevention reasoning.

For full 230-question mock examinations, discipline representation should instead approximate the MCC's “more or less equally” distributed six-discipline structure.

13. Current-source plan for rapidly changing material

The scope phase should identify the correct authoritative source family but should generally avoid freezing detailed recommendations.

Actual recommendations should be researched again during each 40–60-question generation batch.

Immunization

Use:

PHAC Canadian Immunization Guide;
current NACI statements;
current provincial/territorial schedules when program differences matter.

The Canadian Immunization Guide is actively updated as evidence and NACI guidance change; multiple sections received updates during 2026 alone.

Preventive health and screening

The original memo's source hierarchy needs an important 2026 update.

The National Advisory Committee on Preventive Health Services (NACPHS) was launched in June 2026 and replaced the Canadian Task Force on Preventive Health Care. Therefore new national preventive-health source planning should point to PHAC/NACPHS, while older CTFPHC guidance may remain relevant only where it is still the applicable published recommendation.

Do not encode generic claims such as:

“colonoscopy is the standard colorectal screening test”

or

“mammography begins at age X”

into the scope manifest.

Exact modality, age, interval and risk criteria should be verified when the question is generated.

Infectious diseases / antibiotics

Use:

AMMI Canada / Canadian Antibiotic Treatment Guidance where applicable;
PHAC for public-health and nationally relevant infectious-disease guidance;
relevant Canadian specialty/public-health sources.

AMMI Canada is leading development of Canadian national antimicrobial empiric guidance under the Pan-Canadian Action Plan on Antimicrobial Resistance.

Do not use Thrombosis Canada as an antibiotic-treatment authority.

Thrombosis

Use Thrombosis Canada for:

VTE;
PE/DVT;
anticoagulation;
thromboprophylaxis;
antithrombotic treatment.

Its current clinical guides explicitly cover PE diagnosis/treatment and pregnancy-associated thrombosis.

Hypertension

Use Hypertension Canada for current Canadian hypertension guidance. Its 2025 primary-care guideline includes standardized BP diagnosis/confirmation and current treatment recommendations.

Diabetes

Use Diabetes Canada and current chapter updates/clinical tools. Diabetes Canada currently exposes a 2025 clinical-practice-guideline quick reference and updated guideline chapters.

Obstetrics and Gynecology

Prefer:

SOGC;
PHAC/NACI where vaccination/infection issues apply;
current Canadian contraception/sexual-health sources;
current jurisdictional screening guidance where appropriate.

For example, SOGC publishes Canadian guidance on hypertensive disorders of pregnancy, but exact thresholds and timing should be retrieved again when a question is created.

Stroke

Use Canadian Stroke Best Practice Recommendations for acute stroke assessment, imaging and treatment.

Diagnostic imaging

Use the Canadian Association of Radiologists (CAR) as the primary national specialty source for imaging-referral appropriateness.

CAR states that its updated national referral recommendations cover 13 clinical sections and are intended to help clinicians select the appropriate diagnostic imaging modality.

The Canadian Medical Association helped support the project, but the guidelines are CAR Diagnostic Imaging Referral Guidelines, so CAR should be listed as the principal source organization.

Medico-legal and patient safety

Use:

current legislation;
provincial/territorial Colleges/regulators;
Health Canada/Justice Canada where federal law applies;
CMPA for high-quality medico-legal/patient-safety guidance where appropriate.

CMPA should be correctly described as a mutual medical defence organization, not a medical insurance company. It provides medico-legal assistance and patient-safety education/advice.

Its current consent guide, revised in 2024, is a useful Canadian secondary medico-legal resource, but jurisdiction-specific statutory rules should still be verified against the governing legislation/regulator.

MAID

Use the Canadian term medical assistance in dying (MAID).

Source hierarchy should include:

Criminal Code / Department of Justice;
Health Canada;
applicable provincial/territorial law and regulator standards.

As of August 2026, a person whose sole underlying medical condition is a mental illness is not eligible for MAID until March 17, 2027.

Do not use the generic term “euthanasia” as though it were synonymous with the current Canadian legal framework.

14. Uncertainty, validation, and next-stage requirements

The original broad research memo must be treated as a research memo, not proof that an exhaustive crosswalk has already been created.

Statements such as:

“every leaf-level topic has been mapped”

“no topic is missing”

“all page numbers were validated”

“gap_analysis.json has been created”

should not appear as completed facts unless the local deterministic pipeline has actually demonstrated them.

The canonical process should now:

build/verify the exact Toronto Notes TOC from the already-indexed local OCR;
independently retrieve/validate the official MCC Objective registry;
map each meaningful study unit;
identify low-confidence mappings;
run deterministic completeness tests;
create the master scope crosswalk;
derive the six manifests only after the crosswalk passes.

Use:

HIGH
MODERATE
LOW

for research confidence.

Any low-confidence mapping should have:

{
  "needs_review": true,
  "review_reason": "..."
}

No uncertain mapping should silently become DIRECT.

Practice-coverage principle

The target learner experience remains:

Read Toronto Notes topic/subtopic → immediately practise MCCQE-style application of that material.

However, this does not require a separate question for every tiny internal heading.

Every meaningful MCC-relevant study unit should have appropriate practice coverage.

For example:

Acute Coronary Syndrome
    epidemiology
    pathophysiology
    clinical features
    investigations
    management
    complications

can form one study unit with a set of questions collectively assessing:

recognition;
differential diagnosis;
interpretation;
investigation;
next-step management;
emergency priorities;
complications.

This is preferable to manufacturing a separate question solely because “Pathophysiology” happens to appear as a heading.

15. Corrected final conclusion

The purpose of the scope crosswalk is to make the following workflow possible:

Toronto Notes 2025 reading section
↓
Current verified MCC competency
↓
appropriate MCCQE-level question plan
↓
current Canadian source research
↓
original MCCQE-style questions and detailed rationales

Toronto Notes supplies the study structure.

MCC Examination Objectives supply the examination scope.

The MCCQE Blueprint supplies the assessment framework.

Current authoritative Canadian sources supply the clinical answer.

The broad research memo should therefore not itself determine detailed clinical management.

Detailed clinical recommendations—especially for:

medication;
doses;
screening;
immunization;
pregnancy;
pediatrics;
anticoagulation;
infectious disease;
emergency treatment;
diagnostic thresholds;
medical law;

must be researched source-first at question-generation time.

The MCC's own preparation advice reinforces this clinical reasoning approach: candidates should focus on common or critical presentations, differential diagnosis, key findings, investigations and management rather than attempting to memorize an undifferentiated collection of facts.

The current 2026 Study Smarter guide should be used for discipline mapping and blueprint planning, remembering its explicit cautions that discipline mappings overlap and are not exhaustive.

The next canonical outputs should be produced locally and deterministically, not assumed to exist because this memo mentions them:

research/tn2025/toc_inventory.json
research/mcc/current_exam_profile.json
research/mcc/objectives_registry.json
research/mcc/item_style_profile.json

research/scope/master_scope_crosswalk.json
research/scope/gap_analysis.json
research/scope/cross_discipline_map.json
research/scope/unresolved_scope_items.json

manifests/medicine.json
manifests/pediatrics.json
manifests/obgyn.json
manifests/surgery.json
manifests/psychiatry.json
manifests/phelo.json

Only after those files pass validation should question generation begin.