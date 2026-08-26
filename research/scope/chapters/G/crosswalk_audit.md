# Gastroenterology (Chapter G) MCC Crosswalk Audit

**Generated:** 2026-08-25
**Result:** ✅ Deterministic validation target — see `reports/chapter_validation/G.json` after running
`validate-scope-chapter G`.

## Summary counts

- Study units: 62
- Classification: SUPPORTING_KNOWLEDGE 5, COMPONENT 35, DIRECT 15, SPECIALIST_DETAIL 4, REFERENCE_ONLY 3
- Scope depth: CONTEXT_ONLY 6, RECOGNIZE 11, RECOGNIZE_AND_ACT 20, CORE_ACTION 20, OUT_OF_SCOPE_DETAIL 5
- Mapping strength (per MCC-evidence citation, 83 citations across 62 units): STRONG 58, MODERATE 23, WEAK 2
- Units with `requires_scope_review: true`: 2 (Wilson's Disease SU-G-37, Autoimmune Pancreatitis SU-G-56)
- Units with zero planned questions: 13 (background/overview/reference content; see `zero_question_reason` on
  each in `crosswalk.json`)

## MCC registry search note

18 distinct MCC objectives are cited across the chapter. 11 came directly from the scope packet's bounded
candidate set (`derived/scope_packets/G.json`, `candidate_set_truncated: false`): **22-1** (Acute diarrhea),
**22-2** (Chronic diarrhea), **26** (Dysphagia), **49** (Jaundice), **52** (Abnormal liver function tests),
**6-1** (Upper GI bleeding), **6-2** (Lower GI bleeding), **16-1** (Adult constipation), **3-2** (Acute abdominal
pain), **3-3** (Chronic abdominal pain), **3-4** (Anorectal pain). The packet's remaining candidates (SIDS,
personality disorders, hypertension, etc.) were matched only via the broad `STUDY_SMARTER_DISCIPLINE: Medicine`
tag and are not clinically relevant to Gastroenterology — they were not used.

7 further objectives were found via targeted `search-mcc-objectives` full-registry searches beyond the packet's
candidate set, because a first pass of GI-specific term searches (`"gastroesophageal reflux"`, `"peptic ulcer"`,
`"dyspepsia"`, `"inflammatory bowel disease"`, `"irritable bowel"`, `"celiac"`, `"colorectal cancer"`,
`"cancer screening"`, `"hepatitis"`, `"cirrhosis"`, `"pancreatitis"`, `"gallstones"`, `"cholecystitis"`,
`"malabsorption"`, `"ascites"`, `"encephalopathy"`, `"polyp"`, `"diverticul"`, `"reflux"`, `"heartburn"`, and
`"esophag"`) all returned **zero direct-title matches** — confirming a genuine MCC-objectives-registry coverage
gap for these named GI diagnoses, the same pattern chapter E's review flagged and asked to be checked here:

- `"chest pain"` → **14** (Chest pain) — its own `causal_conditions` text explicitly lists "Esophageal spasm or
  esophagitis", "Peptic ulcer disease", "Mallory-Weiss syndrome", and "Biliary disease or pancreatitis" as named
  GI differentials.
- `"abdominal mass"` → **1** (Abdominal distension) and **2** (Abdominal masses and pelvic masses) — objective
  1's `causal_conditions` explicitly enumerates ascites (transudative/exudative, with portal hypertension
  named) and irritable bowel syndrome; objective 2 explicitly names "liver tumour" and "colon tumour".
- `"anemia"` → **42-1** (Anemia) — microcytic/iron-deficiency anemia as an occult GI-bleeding/malabsorption
  presentation.
- `"weight loss"` → **118-2** (Weight loss/eating disorders/anorexia) — explicitly names "esophageal cancer"
  and "malabsorption (e.g., diarrhea)".
- `"preventive"` → **74** (Periodic health encounter) — explicitly names "Cancer screening (e.g., ... colon
  ...)" for the middle-aged/older adult.
- `"substance use"` → **103** (Substance use or addictive disorders) — cited alongside alcohol-related liver
  disease.

Every affected named diagnosis without a dedicated objective (GERD, Barrett's esophagus, dyspepsia, PUD,
gastritis, IBD/Crohn's/UC, IBS, celiac disease, viral hepatitis, autoimmune/drug-induced/genetic liver disease,
cirrhosis and its complications, colorectal neoplasia, cholelithiasis/cholecystitis/cholangitis, pancreatitis)
was instead mapped by locating its **explicit** appearance inside the retrieved `causal_conditions` text of a
nearby presentation-based objective (objectives 3-2, 3-3, 3-4, 6-1, 6-2, 14, 22-1, 22-2, 49, 52, 1, 74) — never
from model memory of what MCC covers, and mapping_strength was capped at what the retrieved objective text
actually supports (STRONG only where the exact diagnosis/etiology is named verbatim in the objective's own
causal-conditions list; MODERATE where it falls under a named generic category, e.g. "chronic hepatocellular"
covering hemochromatosis/MASLD; WEAK where neither applies).

## WEAK / requires_scope_review units

- **SU-G-37 Wilson's Disease** — mapped WEAK to objective 52; not individually enumerated in 52's
  causal-conditions list (only a generic "other, e.g. celiac disease" bucket exists), and per the
  Gastroenterology scope cautions this rare genetic/metabolic disease is kept at RECOGNIZE depth,
  SPECIALIST_DETAIL classification, zero planned questions.
- **SU-G-56 Autoimmune Pancreatitis** — mapped WEAK to objective 3-3; not individually enumerated under
  3-3's "Pancreatic disease" causal category. Same treatment as above.

No other unit fell below MODERATE mapping strength.

## Cross-discipline overlaps flagged (not finalized — deferred to global audit per workflow)

- **Infectious Colitis / Infectious Esophagitis / Traveller's Diarrhea** — overlap with Infectious Diseases.
- **Traveller's Diarrhea** — overlap with Public Health and Preventive Medicine (travel medicine).
- **Familial Colorectal Cancer Syndromes** — overlap with Medical Genetics (Lynch syndrome, FAP).
- **Biliary Colic/Cholecystitis, Ascending Cholangitis, Acute Pancreatitis, Incarcerated Hernia-adjacent acute
  abdomen content** — overlap with General and Thoracic Surgery.
- **Colorectal Cancer Screening** — overlap with Public Health and Preventive Medicine (population screening
  programs) and Family Medicine (periodic health exam).

PRIMARY_OWNER / CROSS_LINK / DISTINCT_CONTEXT designations are intentionally **not** finalized here, per the
project workflow's instruction to defer discipline-ownership decisions to the global cross-chapter audit after
all chapters are mapped.
