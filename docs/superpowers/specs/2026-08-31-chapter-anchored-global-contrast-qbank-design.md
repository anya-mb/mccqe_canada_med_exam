# Chapter-Anchored Global-Contrast QBank Design

**Status:** Approved architecture checkpoint; amended for staged item construction
**Date:** 2026-08-31
**Scope:** Research and architecture only; no production implementation, question generation, canonical-data migration, or allocation change.

## 1. Decision

Adopt **CHAPTER_ANCHORED_GLOBAL_CONTRASTS**.

The product is for a medically trained learner using Toronto Notes 2025 chapter by chapter as a review sequence, not for a novice encountering medicine for the first time. In `CHAPTER_REVIEW`, the current Toronto Notes study unit determines the primary tested objective and why the item belongs in that review. The complete Toronto Notes study-unit inventory remains eligible for distractor discovery. A distractor may therefore require knowledge from a later or otherwise unreviewed chapter to eliminate.

The boundary is educational target fidelity, not chapter isolation:

- the keyed answer and primary learner decision must be meaningfully anchored to the assigned study unit;
- global alternatives may be difficult, realistic, and cross-disciplinary;
- learner reading progress never controls distractor eligibility;
- a cross-chapter distractor never reassigns the question by itself;
- a non-`PASS` `ANCHOR_FIDELITY` verdict fails closed;
- Toronto Notes supplies organization and contrast discovery, while current authoritative evidence determines medically current claims;
- the frozen 6,086-question allocation is unchanged.

This design replaces the proposed `CHAPTER_SUFFICIENCY` concept with `ANCHOR_FIDELITY_GATE`. “Sufficient from the current chapter alone” is not the construct being measured. The intended construct is a coherent, chapter-anchored clinical or professional decision made in the presence of realistic medical alternatives.

## 2. Research basis

Only derived principles are recorded. No MCC question or Toronto Notes prose is reproduced.

| Source | Derived design principle |
|---|---|
| [Current MCCQE overview](https://mcc.ca/examinations-assessments/mccqe/) and [2025 standard-setting report](https://mcc.ca/wp-content/uploads/MCCQE-Part-I-Standard-setting-report-2025.pdf) | The current MCCQE is a one-day examination of 230 MCQs in two 115-item sections and assesses critical medical knowledge and clinical decision-making. Simulation mode should therefore assemble across the whole eligible curriculum, independent of Toronto Notes chapter boundaries. |
| [MCC Examination Objectives](https://mcc.ca/objectives/) and [MCC blueprint](https://mcc.ca/wp-content/uploads/MCC-Test-Specifications-Blueprint.pdf) | Item targets must trace to an MCC objective and the applicable physician activity/dimension of care, not merely to a textbook heading. |
| [MCC multiple-choice question guidelines](https://mcc.ca/wp-content/uploads/Multiple-choice-question-guidelines.pdf) | Select an important clinical decision, make the stem answerable with the options covered, keep options homogeneous, and source plausible distractors from misconceptions or faulty reasoning that a minimally competent candidate might use. These rules support the open-ended key stage and explicit misconception/discriminator records. |
| [MCC free practice resource](https://mcc.ca/free-resources/free-practice-questions/) and [2025 printable practice set](https://mcc.ca/wp-content/uploads/MCCQE-Part-I-practice-questions-and-answers-2025.pdf) | Public MCC-style material uses applied single-best-answer decisions with rationales and references. It is an external format/quality reference only and must never be copied or transformed into project questions. |
| [MCC 2024 technical report](https://mcc.ca/wp-content/uploads/MCCQE-Part-I-Annual-Technical-Report-2024.pdf) | MCC items have used three to five response options, so a four- or five-option product contract is compatible with MCC-style construction. Strict simulation may still default to five for consistency with current public practice material and the repository’s existing schema. |
| [Gierl, Lai, and Turner: medical automatic item generation](https://mcc.ca/wp-content/uploads/AIG-Gierl-Lai-Turner-Medical-Education-Journal.pdf) | Scalable generation should be staged through a cognitive model, an item model, and constrained assembly. A single monolithic prompt is not the preferred architecture. |
| [Gierl et al.: improving AIG distractor quality](https://pubmed.ncbi.nlm.nih.gov/26849247/) | Plausibility improves when distractors are adapted to the unique features in the stem and key. Global candidates therefore require scenario-context features and evidence-backed discriminants before they become options. |
| [Shin, Guo, and Gierl: misconception-based distractors](https://pubmed.ncbi.nlm.nih.gov/31133911/) | Systematic misconception capture is a defensible source of reusable distractors. A contrast edge should record the partial reasoning or misconception it represents. |
| [Rogausch et al.: nonfunctioning distractors](https://pubmed.ncbi.nlm.nih.gov/21106066/) and [Vyas and Supe option-count review](https://pubmed.ncbi.nlm.nih.gov/19004145/) | Extra weak options do not improve an item merely by increasing option count. Use one key plus at least three strong distractors; add a fourth distractor only when it passes the same quality gates. |
| [Larsen, Butler, and Roediger randomized trial](https://pubmed.ncbi.nlm.nih.gov/19930508/) | Retrieval with feedback can improve long-term retention relative to repeated study, supporting the read → answer → rationale workflow. |
| [Rozenshtein et al. randomized radiology study](https://pubmed.ncbi.nlm.nih.gov/27236286/) | Interleaved exposure improved recognition of chest-radiograph patterns relative to massed exposure in that study, including transfer to new examples for more advanced students. |
| [Systematic review of interleaving and discriminative contrast](https://link.springer.com/article/10.1007/s10648-021-09613-w) | Interleaving is most defensible when alternatives are genuinely confusable and learners must notice decisive differences; mixing unrelated material is not inherently beneficial. Global retrieval must rank medical confusability, not chapter distance or lexical similarity. |
| [Self-explanation plus diagnostic feedback trial](https://pubmed.ncbi.nlm.nih.gov/31185971/) | Asking learners to consider plausible alternative diagnoses and then giving feedback can support near-transfer diagnostic accuracy. Per-option rationales should explain both plausibility and the decisive difference. |
| [MCC study preparation guidance](https://mcc.ca/examinations-assessments/resources-to-help-with-exam-prep/) | MCC itself recommends building differentials, identifying key distinguishing features, and asking what other diagnoses should be considered. Cross-chapter contrasts align with the intended exam-preparation activity. |

The evidence supports global contrasts for medically trained reviewers when the alternatives are clinically or professionally confusable. It does not support indiscriminate topic mixing, nor does it show that every item benefits from a cross-chapter distractor. The architecture therefore makes global retrieval available and quality-gated, not mandatory by quota.

## 3. Fit with the existing repository

### 3.1 Existing canonical support

Targeted inspection found that the required anchor lineage already exists upstream:

| Need | Existing authoritative artifact | Finding |
|---|---|---|
| Toronto Notes chapter order and boundaries | `research/tn2025/toc_inventory.json` | 32 chapter roots and 2,019 total deterministic nodes carry printed TN and physical PDF boundaries. Physical book order is deterministically recoverable by `start_pdf_page`; array order itself must not be treated as book order. |
| Topic identity and source nodes | `research/scope/chapters/*/study_units.json` and `schemas/study-unit.schema.json` | Every canonical study unit has `study_unit_id`, chapter code/title, `source_node_ids`, `tn_page_range`, and `pdf_page_range`. Some valid provenance uses deterministic `UNCATALOGUED:*` identifiers, which must remain distinguishable from TOC node IDs. |
| Allocation address and question count | `research/scope/final_question_allocation.json` | 1,507 allocation addresses sum to the frozen 6,086-question target. Allocation address and study-unit identity are available without reopening allocation. |
| MCC mapping, depth, and item forms | `research/scope/master_scope_crosswalk.json`, `research/scope/mcc_objective_coverage.json`, and final allocation | MCC objective evidence, testable competencies, scope depth, preferred item forms, and coverage weights already exist upstream. |
| Generation grouping | `research/qgen/question_generation_manifest.json` | 220 generation jobs preserve assignment-level study-unit IDs, source nodes, MCC objective IDs, depth, item forms, and fixed question slots. |
| Foundational evidence | `research/qgen/foundational_evidence_claim_cards.json` | Stable claim cards have explicit study-unit scope references and citation lineage. |
| Current guidance | `research/qgen/source_packet_plan.json`, source population artifacts, and source-document registry | Current-evidence requirements and packet/document identities exist. Packet readiness remains a prerequisite for claims that require current guidance. |
| Existing staged item model | `QGEN-PHELO-011.retry-10.concept-plan.json`, `QGEN-PHELO-011.retry-v2-10.item-spec.json`, semantic preflight, and V2.1 micro-review | The V2 model already separates learner decision, evidence discriminants, competing concepts, distractor blueprints, vignette requirements, shortcut controls, rationale requirements, lineage, preflight, and independent semantic review. |

### 3.2 Answer to the OCR/indexing question

**Yes: every future generated question can carry `anchor_chapter`, `anchor_topic`, `anchor_study_unit`, `anchor_source_nodes`, and `anchor_TN_pages` without new OCR or indexing work.** The upstream join is:

`generation job assignment → allocation_address_id/study_unit_id → canonical study unit → source_node_ids + tn_page_range + pdf_page_range → TOC nodes/chapter root`.

Later implementation will require additive contracts and validators, because the current canonical question schema stores chapter/section/subsection and TN/PDF pages but not the complete anchor study-unit/source-node lineage. It also hard-codes five A–E options. That is a schema/validator migration, not an OCR, TN-index, scope, MCC-map, or allocation migration.

No existing canonical question, evidence, allocation, manifest, or study-unit artifact is changed by this design.

## 4. Architecture comparison

| Criterion | A. Chapter-isolated questions | B. Chapter-anchored target + global contrasts | C. Full cross-chapter targets from the start |
|---|---|---|---|
| MCCQE realism | Low–moderate; artificial boundaries weaken differentials | High; one decision remains traceable while alternatives resemble real clinical/professional competition | High for simulation, but poorly matched to chapter review |
| Distractor strength | Limited by same-chapter inventory; encourages filler | Highest practical ceiling because the complete TN inventory is searchable | High, but target and distractor roles can blur |
| Retrieval/interleaving value | Retrieval without much discrimination | Retrieval plus discriminative contrast among plausible competitors | Strong integration but may overwhelm the immediate review target |
| Chapter-review usefulness | High localization, low realism | High localization with realistic breadth | Low–moderate; the learner cannot tell what the chapter review is reinforcing |
| Medical accuracy | Easier provenance, but may omit the best competitor | Strong if every discriminant has evidence and ambiguity fails closed | Strong only with substantially broader evidence closure per item |
| Scalability | Simple but quality-limited | High with indexed retrieval and cached contrast edges | Lower because each target itself requires multi-unit evidence synthesis |
| Evidence burden | Lowest | Targeted and reusable | Broadest per item |
| Token/research cost | Low but produces weaker items | Moderate cold start, lower amortized cost through reuse | Highest and least predictable |

Architecture B provides the best balance. Architecture A remains a useful negative baseline for evaluation. Architecture C is appropriate later for selected cumulative items and for simulation assembly, not as the default target model for chapter review.

## 5. Core concepts

### 5.1 Anchor / target concept

The anchor is the canonical reason an item belongs to a chapter review. It consists of a study unit, its TN provenance, a primary MCC objective/competency, and one primary learner decision. The anchor is not established merely because its diagnosis or term appears in the stem or options.

### 5.2 Contrast concept

A contrast concept is a medically or professionally plausible alternative relevant to the same decision context. It may be a diagnosis, investigation, management step, medication, adverse effect, laboratory or imaging pattern, epidemiologic concept, ethical/legal alternative, or public-health action. It can come from any Toronto Notes chapter, regardless of reading order.

### 5.3 Target drift

Target drift occurs when the assigned anchor ceases to explain the keyed answer and critical reasoning. Operationally, drift is present when any of the following is true:

- authoritative support for the key comes primarily from a different study unit and the anchor contributes only incidental context;
- the critical reasoning step is about a contrast concept rather than the anchor competency;
- removing the anchor-specific knowledge leaves essentially the same item and answer;
- changing the anchor diagnosis/idea to a neutral placeholder does not materially change what competence is assessed;
- the item is assigned to the chapter only because an anchor term appears somewhere in the stem or options.

## 6. Learning modes

### 6.1 `CHAPTER_REVIEW`

- Exactly one primary anchor study unit and one primary learner decision are required.
- The primary objective is anchored to the current chapter/topic.
- Distractors may come from any TN chapter and may require broader prior medical knowledge to eliminate.
- Reading progress is neither an eligibility filter nor a ranking penalty.
- `ANCHOR_FIDELITY = PASS` is mandatory.
- Page/topic references foreground the anchor; contrast references are optional contextual links in rationales.

### 6.2 `CUMULATIVE_REVIEW`

- The primary target may intentionally integrate the current chapter, previously reviewed chapters, or cross-disciplinary competencies.
- Each participating target concept must have explicit provenance and an assigned role in the learner decision; one concept remains the item’s primary target for allocation accounting.
- Interleaving is stronger and may influence both the target and the options.
- Global distractors remain allowed.
- A generalized `TARGET_FIDELITY` check prevents an item from claiming an integration it does not actually require.

### 6.3 `MCCQE_SIMULATION`

- Toronto Notes chapter boundaries do not constrain item selection or ordering.
- Selection uses the full eligible curriculum and MCC blueprint/scope.
- The separate 230-question simulation remains outside the frozen 6,086 study bank.
- Five options are the default presentation for strict public-practice-format familiarity; four may be allowed only if the future simulation policy explicitly adopts the current MCC three-to-five specification and psychometric validation supports the item.
- TN provenance remains available internally and in post-answer review, but it does not drive assembly.

## 7. Required contracts

### 7.1 Per-question anchor record

Every item must record:

| Field | Contract |
|---|---|
| `learning_mode` | `CHAPTER_REVIEW`, `CUMULATIVE_REVIEW`, or `MCCQE_SIMULATION` |
| `anchor_chapter_id` | Canonical TN chapter code |
| `anchor_chapter_title` | Canonical chapter title, joined rather than invented |
| `anchor_topic` | Canonical study-unit title or explicitly versioned derived label tied to that unit |
| `anchor_allocation_address_id` | Frozen allocation identity; preserves allocation accounting |
| `anchor_study_unit_id` | Canonical study unit |
| `anchor_source_node_ids` | Ordered canonical node or deterministic `UNCATALOGUED:*` identifiers |
| `anchor_tn_pages` | Canonical printed page range |
| `anchor_pdf_pages` | Canonical physical PDF page range |
| `primary_mcc_objective` | One primary existing MCC ID; secondary mappings may be separate |
| `primary_physician_activity` | One canonical MCC physician activity applicable to the allocated objective and learner decision |
| `primary_competency` | Existing testable competency/component and depth |
| `primary_learner_decision` | One observable diagnosis, investigation, management, interpretation, communication, professional, ethical/legal, or population-health decision |
| `anchor_fidelity` | Verdict, assessor identity, exact input fingerprints, criteria results, and explanation |
| `tn_alignment` | `CURRENT`, `INCOMPLETE`, or `OUTDATED_CONFLICT` |

### 7.2 Per-distractor record

Every proposed distractor must record:

| Field | Contract |
|---|---|
| `distractor_concept_id` | Stable concept identity |
| `distractor_study_unit_id` | Canonical TN study unit representing the contrast |
| `distractor_tn_chapter` | Joined chapter code/title |
| `distractor_source_node_ids` | Canonical TN provenance |
| `distractor_tn_pages` / `distractor_pdf_pages` | Printed and physical page references |
| `why_plausible` | Scenario-specific reason a partially knowledgeable graduate could select it |
| `misconception_or_partial_reasoning` | The erroneous or incomplete reasoning path, not merely “wrong diagnosis” |
| `context_features_supporting_plausibility` | Stem facts that make the option competitive |
| `decisive_discriminator` | The specific feature, rule, threshold, or priority that makes it inferior |
| `discriminator_evidence_refs` | Assertion-level authoritative references |
| `relationship_to_anchor` | Differential, look-alike, neighboring test/management, medication confusion, jurisdictional alternative, epidemiologic confusion, etc. |
| `quality_status` | `CANDIDATE`, `EVIDENCE_PENDING`, `VALIDATED`, `REJECTED_AMBIGUOUS`, `REJECTED_IRRELEVANT`, `REJECTED_WEAK`, or `RETIRED` |

`CURRENT`, `PREVIOUSLY_READ`, and `FUTURE_UNREAD` are not eligibility states. If later retained for analytics or optional display, they must be derived metadata and must never enter generation filters, candidate scores, or validation outcomes.

### 7.3 Validated contrast edge

A reusable contrast edge is directional and context-bound:

`anchor_concept → contrast_concept + confusion_context`.

It records both concepts’ TN provenance, shared features, decisive discriminants, authoritative evidence, contrast type, applicable learner decisions, excluded contexts, quality status, reviewer, timestamps, and content/evidence fingerprints. Direction matters: a competitor useful when diagnosing anchor A may not be appropriate when anchor B is tested for management.

Validated edges are reusable; raw model suggestions are not. An evidence update invalidates or reopens only edges whose referenced evidence fingerprint changed.

## 8. `ANCHOR_FIDELITY_GATE`

### 8.1 Required criteria for `CHAPTER_REVIEW`

All criteria must pass:

1. **Decision ownership:** The primary learner decision belongs to the anchor study unit’s competency and depth.
2. **Key ownership:** The keyed answer directly demonstrates that competency; it is not chiefly supported by another unit.
3. **Positive anchor evidence:** At least one decisive positive reason for the key is meaningfully tied to the anchor topic and evidence lineage.
4. **Immediate review fit:** The item is educationally appropriate immediately after reviewing the anchor pages for a medically trained learner.
5. **Counterfactual necessity:** Removing anchor-specific knowledge, or substituting a neutral non-anchor label, materially damages the reasoning path or changes the answer.
6. **Contrast-role integrity:** Cross-chapter knowledge may be necessary to reject alternatives, but no contrast concept becomes the primary assessed competency.
7. **Allocation integrity:** The item consumes only its frozen anchor allocation slot; distractor provenance never creates additional allocation or ownership.

### 8.2 Verdicts

- `PASS`: all criteria pass with evidence and explicit reasoning.
- `FAIL_TARGET_DRIFT`: another concept owns the critical decision/key or the counterfactual test fails.
- `FAIL_ANCHOR_TOO_WEAK`: the anchor is relevant but insufficiently central or insufficiently evidenced.
- `UNCERTAIN`: evidence, provenance, or semantic ownership is unresolved.

Only `PASS` proceeds. `UNCERTAIN` is not a soft pass.

### 8.3 Two checkpoints

The gate runs first on the anchor plus open-ended item model, before distractor retrieval. It runs again after MCQ assembly because option construction can introduce target drift that was absent from the open-ended version. The second verdict is bound to exact item and contrast-matrix fingerprints.

## 9. Open-ended key and cover-the-options rule

Before distractors exist, the stage must contain an original stem, a direct lead-in, the intended key, primary learner decision, anchor evidence, and a reasoning chain. A blind solver who cannot see any proposed options must be able to derive the key at the level expected of a competent medical graduate.

This proves coherence of the anchor problem. It does not imply that every later option can be eliminated using only the anchor chapter. Once realistic options are added, broader medical knowledge may legitimately be required.

Failure outcomes are `REVISE_STEM`, `REVISE_KEY`, `FAIL_ANCHOR_FIDELITY`, or `EVIDENCE_GAP`; distractor generation does not repair an incoherent open-ended item.

## 10. Hybrid global contrast library

### 10.1 Build strategy

Use a **HYBRID, ON-DEMAND-FIRST** strategy:

- precompute a lightweight local concept index for every canonical study unit;
- create no exhaustive all-pairs graph;
- discover candidate contrasts only when an anchor/decision context needs them;
- validate the strongest candidates and persist directional, context-bound edges;
- retrieve validated cached edges first on later items;
- research only missing high-value discriminants or stale evidence.

### 10.2 Candidate retrieval

For an anchor study unit:

1. Resolve the complete anchor/MCC/competency/evidence context deterministically.
2. Search the complete study-unit inventory, not the current chapter subset.
3. Combine cached edges with candidates from titles/hierarchy, MCC overlap, competency/item-form compatibility, foundational claims, current-guidance topics, and bounded semantic retrieval.
4. Exclude zero-scope, ownership-suppressed, provenance-missing, and structurally irrelevant candidates as independent targets, while allowing their concepts only if policy explicitly permits them as contrast provenance and they are medically testable.
5. Rank candidates by contextual confusability, shared features, decision-stage match, evidence readiness, novelty/diversity, and prior psychometric performance.
6. Inspect a small top set, normally 8–20 candidates, rather than sending the whole book to an LLM.
7. Validate the decisive discriminants of the best candidates with authoritative evidence.
8. Persist only validated edges and their rejected-context boundaries.

Chapter distance and learner progress have zero eligibility weight. Lexical similarity is a discovery feature at most and can never establish medical plausibility.

### 10.3 Ranking requirements

A strong candidate must:

- answer the same lead-in category as the key;
- be plausible under facts actually present in the stem;
- correspond to a recognizable misconception, differential, or partial reasoning path;
- be decisively inferior under the stated context;
- have evidence sufficient to explain that inferiority;
- not make the item primarily about itself;
- not duplicate another option’s reasoning.

## 11. `CONTRASTIVE_EVIDENCE_MATRIX`

No distractor proceeds to prose construction without a complete matrix.

### 11.1 Key row

- anchor concept and full TN provenance;
- primary learner decision;
- positive evidence;
- decisive features;
- authoritative evidence references;
- `TN_ALIGNMENT`.

### 11.2 Distractor rows

For each proposed distractor:

- global contrast concept and full TN provenance;
- why it is medically plausible in this exact context;
- the misconception or partial reasoning represented;
- features shared with the anchor;
- decisive difference;
- assertion-level evidence for that difference;
- target-drift check;
- ambiguity/also-correct verdict.

At least three rows must be `VALIDATED`. A fourth distractor is optional. A strong competitor from a later TN chapter is neither downgraded nor rejected for that reason.

## 12. Staged construction model

The final architecture is **CHAPTER_ANCHORED_GLOBAL_CONTRASTS with staged item construction**. Chapter-global contrast retrieval is not a standalone generation feature and cannot emit options directly. The normative sequence is:

`TORONTO NOTES ANCHOR`
→ `MCC OBJECTIVE / PHYSICIAN ACTIVITY`
→ `PRIMARY LEARNER DECISION`
→ `ANCHOR FIDELITY`
→ `OPEN-ENDED STEM + KEY`
→ `BLIND COVER-THE-OPTIONS SOLVER`
→ `GLOBAL CONTRAST RETRIEVAL`
→ `CONTRASTIVE EVIDENCE MATRIX`
→ `SEPARATE DISTRACTOR CONSTRUCTION`
→ `DISTRACTOR ADVERSARIAL RANKING`
→ `MCQ ASSEMBLY`
→ `PLAN-FIDELITY / SHORTCUT / CUE CHECK`
→ `RATIONALES`
→ `FRESH INDEPENDENT VERIFICATION`

The executable stages are:

1. **Anchor topic resolution** — join the frozen assignment to canonical TN/MCC/competency provenance.
2. **MCC objective and physician activity resolution** — bind one canonical objective and physician activity without inventing identifiers or labels.
3. **Primary learner decision** — define one observable decision at the allocated depth.
4. **Anchor-fidelity preflight** — fail closed before prose generation.
5. **Open-ended stem/key model** — construct the original problem without options and record the intended answer and reasoning chain.
6. **Blind cover-the-options solver** — a fresh solver independently derives the answer and reasoning without seeing the intended answer, contrast candidates, options, or author self-evaluation. A mismatch revises the stem/decision model; options cannot rescue it.
7. **Global contrast retrieval** — retrieve across the complete TN inventory plus cached validated edges.
8. **Contrastive evidence matrix** — validate the key row and at least three plausible competitor rows for provenance, shared features, partial reasoning, decisive discriminants, authoritative evidence, ambiguity, and drift before option wording exists.
9. **Separate distractor construction** — realize only validated matrix rows in the same option dimension as the key. The constructor is not asked for generic “wrong answers.”
10. **Distractor adversarial ranking** — a fresh reviewer tests plausibility, MCC relevance, medical/professional confusability, uniqueness, scenario binding, evidence-grounded discrimination, and single-best-answer status.
11. **MCQ assembly** — select one key plus three or four strong distractors without materially rewriting approved components.
12. **Plan-fidelity, shortcut, and cue review** — repeat cover-the-options and anchor-fidelity checks; verify item-spec/learner-decision fidelity, context necessity, option-only cues, clang/keyword overlap, option homogeneity, answer-length/specificity cues, and target drift.
13. **Rationale construction** — only after the assembled item is accepted, explain the key and every option from the approved matrix without adding teaching claims.
14. **Fresh independent verification** — a verifier fresh relative to authorship, blind solving, distractor construction, and adversarial ranking binds verdicts to exact anchor, evidence, matrix, plan, and item bytes.

The generator cannot create the item monolithically. Each stage consumes an approved, fingerprinted predecessor and emits a separately reviewable artifact. Model agreement is not evidence.

### 12.1 Context necessity

Context form follows the competency. Clinical decisions may require a patient presentation; public-health, ethical/legal, communication, or professional decisions may instead require study results, a policy, a population, a program, or a professional scenario. Application items fail closed when removing the context leaves the same decision answerable, except for facts deliberately retained as realistic but non-decisive texture and identified as such. No artificial patient vignette is required.

### 12.2 Matrix insufficiency fallback

If fewer than three genuinely plausible evidence-grounded competitors validate, the ordered fallback is: inspect other whole-book candidates; select another learner decision within the same anchor unit; then perform targeted research for one specifically identified missing discriminator. Broad evidence enrichment is forbidden, and a weak distractor is never manufactured to satisfy option count.

## 13. Option-count policy

- Minimum: one key plus three strong distractors (four total options).
- Maximum: one key plus four strong distractors (five total options).
- A fifth option is added only if it independently passes all plausibility, evidence, ambiguity, and cue gates.
- No weak fifth option is manufactured for visual consistency.
- `CHAPTER_REVIEW` and `CUMULATIVE_REVIEW` may use four or five.
- `MCCQE_SIMULATION` defaults to five unless a later, explicit simulation-format policy adopts variable counts.
- Post-use psychometrics should track selection frequency, option discrimination, and retirement/revision decisions without treating low selection alone as proof that an option is medically invalid.

The existing five-option canonical question schema will require a future additive/migration design before four-option production is possible. This document does not authorize that change.

## 14. Toronto Notes and current guidance

### 14.1 Two TN roles

**Anchor role:** chapter order, study unit, review target, and page/topic references.

**Global contrast-discovery role:** candidate diagnoses, tests, treatments, patterns, professional alternatives, and other confusable concepts across the whole book.

TN wording is never copied. TN alone is not current clinical authority. Public artifacts contain mappings and references, not TN text or private source content.

### 14.2 `TN_ALIGNMENT`

- `CURRENT`: TN anchor and current authoritative guidance are materially aligned for the tested decision.
- `INCOMPLETE`: TN provides the anchor but not enough current detail to support the decision or discriminant.
- `OUTDATED_CONFLICT`: current authoritative guidance materially conflicts with TN for the tested decision.

For `INCOMPLETE`, the item may proceed only when authoritative evidence fills the gap and the rationale distinguishes TN’s organizational role from the added current support.

For `OUTDATED_CONFLICT`:

- the medically current keyed answer always wins;
- the item displays a conspicuous **CURRENT CANADIAN GUIDANCE UPDATE** before or at rationale review, not as a hidden footnote;
- the update states the affected decision, the current rule in concise paraphrase, source organization/date, and whether the TN page is outdated for that point;
- the review page keeps the anchor chapter/topic/pages so the learner understands why the item is in the chapter;
- no option is made “correct according to TN but wrong today”; if that ambiguity cannot be cleanly resolved, reject the item;
- conflicts are versioned and revalidated when evidence changes.

This avoids silently teaching outdated medicine while preserving the chapter-review experience.

## 15. Rationale UX

For the key, show:

- why it is correct in this scenario;
- the primary learner decision and decisive positive evidence;
- the anchor Toronto Notes chapter/topic/printed pages;
- authoritative evidence where applicable;
- the current-guidance update banner when required.

For every distractor, show:

- why it was plausible;
- the decisive discriminator in this scenario;
- evidence for the discriminator;
- optional “Related Toronto Notes topic” with chapter/topic/pages.

Do not label another chapter as unfair, unavailable, or unread. Cross-chapter explanations are deliberate interleaving. The rationale must not introduce unsupported facts that were absent from both the matrix and evidence lineage.

## 16. Learning progression

1. **End-of-topic review:** one study-unit anchor; global distractors allowed.
2. **End-of-chapter review:** anchors sampled across that chapter; global distractors allowed and contrast-pair repetition controlled.
3. **Cumulative review:** target concepts may integrate current and prior chapters; explicit multi-target lineage required.
4. **Discipline mix:** primary targets sampled across a discipline with cross-disciplinary contrasts where medically appropriate.
5. **Full MCCQE simulation:** chapter boundaries removed from selection; full eligible curriculum and MCC blueprint govern assembly.

The progression changes what may be the primary target, not whether distractors may be global. Global distractors are available from the first chapter review.

## 17. Scaling and token-cost design

### 17.1 Deterministic work

Use deterministic code for:

- all canonical joins and page resolution;
- physical chapter ordering by PDF start page;
- eligibility, ownership, zero-scope, component-parent, and allocation checks;
- exact/lexical title and hierarchy retrieval;
- MCC/competency/item-form filtering;
- cached-edge lookup and evidence-fingerprint invalidation;
- candidate deduplication, diversity caps, repeated-pair quotas, and sorting;
- schema validation, counts, provenance closure, and reproducibility;
- post-use distractor statistics and stale-edge detection.

### 17.2 Bounded semantic work

Use semantic reasoning only to:

- discover clinically meaningful competitors missed by deterministic retrieval;
- characterize misconception/partial reasoning and contextual plausibility;
- judge target drift and overintegration;
- synthesize a concise evidence-backed discriminator;
- perform adversarial semantic review.

### 17.3 Cost profile

A naive design would search the whole book and research all options for every question. This design instead performs one lightweight whole-inventory index build, then retrieves small candidate sets. A cached validated edge can serve many later items and requires only context-fit revalidation; a new edge triggers targeted evidence work once.

Cold-start cost is higher than same-chapter generation because good cross-chapter discriminants must be validated. Amortized cost becomes lower than repeated monolithic generation as the edge library grows. The expected steady-state path is:

`anchor → cached edges/local top candidates → validate context → research only missing discriminants → persist/reuse`.

## 18. Safeguards and risks

| Risk | Safeguard |
|---|---|
| Target drift into another chapter | Two-stage `ANCHOR_FIDELITY_GATE`, counterfactual anchor-removal test, and exact primary-decision ownership |
| Clinically irrelevant global retrieval | Same-lead-in requirement, contextual confusability ranking, top-set review, and `REJECTED_IRRELEVANT` status |
| Lexical rather than medical similarity | Lexical retrieval is discovery-only; validation requires shared clinical/professional features and evidence-backed discriminants |
| More than one defensible answer | Independent solver, explicit single-best-answer comparison for every pair, and fail-closed `REJECTED_AMBIGUOUS` |
| Weak discrimination evidence | Assertion-level evidence closure; no matrix completion and no option without a supported decisive difference |
| Repeated differential pairs | Per-anchor, per-chapter, and bank-wide edge-use counters; diversity penalties and caps |
| Overuse of famous “classic” distractors | Candidate novelty scoring, context-fit requirement, and rejection when the option is included by fame rather than vignette plausibility |
| Outdated TN recommendations | `TN_ALIGNMENT`, current-source readiness, evidence versioning, and visible guidance-update UX |
| Option cueing | Homogeneity checks, length/form analysis, convergence/overlap checks, option-position balancing, and blind cue review |
| Unsupported distractor rationales | Rationale statements must resolve to matrix assertions and evidence references; no post-hoc factual expansion |
| Excessive global-retrieval cost | Local index, small top-k retrieval, cached validated edges, fingerprinted reuse, and research-only-on-miss |
| Copying TN wording | Provenance-only public use, paraphrase/similarity checks, and no TN text in contrast edges or questions |
| Overintegrated chapter-review items | One primary decision, one allocation owner, immediate-review-fit test, and `FAIL_TARGET_DRIFT` when contrasts become co-targets |
| Drift caused during option assembly | Repeat anchor-fidelity after assembly, not only at item-spec preflight |
| Evidence update silently invalidates reused contrasts | Edge-to-evidence fingerprints and deterministic stale-edge invalidation |

## 19. Representative abstract traces

These are architecture traces, not canonical questions. They contain no final stem, option wording, key position, or production rationale.

### 19.1 Clinical trace: acute coronary syndromes with global chest-pain contrasts

**Anchor**

- Chapter: Cardiology and Cardiac Surgery (`C`)
- Study unit: `SU-C-21`, Acute Coronary Syndromes
- Source nodes: `C.S06.T02`, `C.S06.T03`
- TN pages: `C30-C39`; PDF pages: `120-129`
- Primary learner decision: recognize or manage an acute coronary syndrome at the allocated MCC/competency depth.

**Global candidates discovered from the complete inventory**

| Candidate | TN provenance | Why it can be plausible | Evidence-backed discriminator required before use |
|---|---|---|---|
| Pulmonary embolism | `SU-R-19`, Respirology, `R.S05`, TN `R20-R22`; alternatively the canonical ED routing at `SU-ER-22` | Acute chest symptoms, dyspnea, tachycardia, hypoxemia, or thrombosis context can overlap | Scenario must supply the applicable PE probability/features and the discriminator must follow a current diagnostic approach such as [Thrombosis Canada’s PE guide](https://thrombosiscanada.ca/hcp/practice/clinical_guides?guideID=PULMONARYEMBOLISMDIAGNOSISANDM&language=en-ca). |
| Aortic dissection | `SU-VS-03`, Vascular Surgery, `VS.S02.T01`, TN `VS6-VS8` | Severe acute chest pain and possible ischemic consequences can mimic ACS | Use only when the scenario contains discriminating aortic features supported by an authoritative acute-aortic source such as the [2022 ACC/AHA aortic disease guideline](https://www.jacc.org/doi/10.1016/j.jacc.2022.08.004). |
| Acute pericarditis | `SU-C-33`, Cardiology, `C.S12.T01`, TN `C61-C67` | Chest pain and ST-segment abnormalities can overlap | The scenario must contain positional/pleuritic, examination, ECG, or effusion evidence sufficient for a single best answer under the [ESC pericardial guideline](https://academic.oup.com/eurheartj/article/36/42/2921/2293375). |
| Gastroesophageal reflux disease | `SU-G-04`, Gastroenterology, `G.S02.T01`, TN `G6-G9` | Substernal symptoms may resemble cardiac pain | Use only when symptom context supports reflux and urgent cardiac disease has not been dismissed by a weak stereotype; current guidance notes the overlap in [ACG’s GERD guideline](https://pmc.ncbi.nlm.nih.gov/articles/PMC8754510/). |
| Panic disorder | `SU-PS-15`, Psychiatry, `PS.S05`/`PS.S05.T01`, TN `PS16` | Autonomic symptoms and chest discomfort can overlap | A psychiatric label cannot be used to shortcut exclusion of dangerous medical causes; its discriminator needs scenario-specific psychiatric evidence and authoritative support. |

**Contrastive evidence outcome**

The matrix would select at least three candidates only after the actual stem context makes them plausible and their decisive differences are evidenced. Cross-chapter provenance does not count against them. If PE or dissection becomes the condition whose work-up supplies the critical decision, the item fails `FAIL_TARGET_DRIFT`; if ACS-positive evidence remains decisive and the other concepts are alternatives to eliminate, it remains a Cardiology/ACS review item.

**Anchor-fidelity verdict:** `PASS` at the architecture level. The key and learner decision remain owned by `SU-C-21`; the cross-chapter concepts serve contrastive discrimination. A concrete future item must independently re-earn `PASS`.

### 19.2 Existing `QGEN-PHELO-011` context

**Anchor**

- Job: `QGEN-PHELO-011`
- Chapter: Public Health and Preventive Medicine (`PH`)
- Representative allocation: `SU-PH-01`
- Source node: `PH.S01.T01`
- TN pages: `PH2-3`; PDF pages: `1420-1421`
- Primary MCC objective/competency: `78-4` / structure
- Primary learner decision from the existing V2 model: classify an organized population-facing action by what it does and at what level, rather than by shared health-related vocabulary.

**Candidate contrasts**

| Candidate concept | TN relationship | Plausibility and decisive distinction |
|---|---|---|
| Population-health explanatory framework | `SU-PH-01`, same anchor pages | Plausible because both concern group health; decisive distinction is explanation of group differences versus implementation of an organized action. Existing foundational claim lineage: `FNDCLM-PHELO-011-01A/01B`. |
| Epidemiologic description/causal inquiry | `SU-PH-01` foundational context and later analytic units such as `SU-PH-09`/`SU-PH-16` where applicable | Plausible because data collection and population causes may precede action; decisive distinction is analytic description/investigation versus delivery of a program, service, or policy. Existing lineage includes `FNDCLM-PHELO-011-01C`. |
| Individual preventive/clinical service | global TN examples include `SU-FM-02` (Family Medicine, TN `FM3`) and `SU-P-002` (Pediatrics, TN `P4-P5`) | Plausible when clinicians deliver part of a broader response; decisive distinction is care initiated for an individual problem/risk versus an organized population-facing mechanism. Existing lineage includes `FNDCLM-PHELO-011-02A`; future contrast validation must bind the selected concrete service to its actual TN unit. |
| Quality-improvement intervention | `SU-PH-24`, TN `PH22-23` | Plausible when a system changes a process; decisive distinction depends on whether the decision concerns improving a care process or protecting/promoting population health through a public-health action. It is used only when the scenario supports both interpretations and evidence makes one inferior. |

**Connection to the V2.1 micro-pilot failure**

The existing V2.1 review already proves why scenario binding belongs in the contract: one rejected item omitted the scenario feature that made a clinical-assessment distractor plausible, and another used a raw-count alternative whose rationale did not decisively make it inferior for the stated operational decision. The new matrix would fail those rows before assembly because `context_features_supporting_plausibility` and `decisive_discriminator` must both be true in the exact scenario.

**Anchor-fidelity verdict:** `PASS` at the architecture level. Several alternatives may point to other TN units, but the primary decision remains classification of the `SU-PH-01` public-health structure. If a future item instead asks the learner to choose a Family Medicine preventive service or perform an epidemiologic calculation, it must move to that target or fail `FAIL_TARGET_DRIFT`.

## 20. Acceptance criteria for the future implementation design

A later implementation plan may be written only after user approval of this specification. That future design must preserve these acceptance criteria:

- the 6,086 allocation and frozen upstream layers remain byte-for-byte unchanged unless separately authorized;
- no new OCR/indexing is required for anchor lineage;
- all chapter-review items have `ANCHOR_FIDELITY = PASS` at preflight and postflight;
- learner progress never filters or penalizes distractor eligibility;
- every option has canonical TN contrast provenance and evidence-backed scenario-specific discrimination;
- at least three strong distractors exist, with a fourth optional;
- current guidance overrides conflicting TN recommendations and is visibly disclosed;
- deterministic validation proves provenance, allocation, evidence closure, option count, and reproducibility;
- independent semantic review proves target fidelity, plausibility, single-best-answer status, and rationale support;
- no canonical question generation begins under this design document.

## 21. Self-review

- **Target-drift loopholes:** closed through decision/key ownership, counterfactual necessity, allocation ownership, and post-assembly recheck.
- **Meaning of chapter-anchored:** explicit: one canonical study unit owns the primary decision, positive key evidence, and allocation slot.
- **Evidence/provenance gaps:** fail closed; TN provenance is required for both anchor and contrasts, and authoritative evidence is required for discriminants.
- **Same-chapter restriction:** absent; complete inventory retrieval is explicit and reading progress has no control role.
- **Learner-progress dependency:** limited to optional analytics/display and explicitly excluded from generation/ranking.
- **Scale/token cost:** bounded top-k retrieval, deterministic filtering, cached directional edges, and evidence-on-miss avoid whole-book prompting per item.
- **Scope:** one architecture spec; no implementation plan, production code, generated question, canonical migration, or allocation change.
