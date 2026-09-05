# MCCQE clinical contrast graph, hybrid retrieval and question-difficulty design

Status: **DESIGN AND RESEARCH ONLY. NOTHING BUILT.**

- `PRODUCTION_CODE_CHANGED = NO`
- `QUESTIONS_GENERATED = 0`
- `GRAPH_BUILT = NO`
- `RAG_BUILT = NO`
- `GRAPH_CONSTRUCTION_AUTHORIZED = NO`
- `FROZEN_G2_RETRIEVAL_BENCHMARK = DESIGNED_NOT_RUN`
- Baseline commit: `7d829ac`. The validated stem-anchor floor is untouched and this design keeps it.

Two claim boundaries govern the whole document and are checked in §16:

- `OFFICIAL_MCC_DIFFICULTY_DISTRIBUTION_CLAIMED = NO` — the MCC publishes no Easy/Medium/Hard bands or
  percentages. Ours are `STUDY_BANK_DESIGN_POLICY` (§1.3, §3, §3.3).
- `FREE_55_DIFFICULTY_LABEL = MODEL_STRUCTURAL_DIFFICULTY_ESTIMATE` — the difficulty classification of
  the 55 official free questions is this research's own structural estimate, not MCC data (§2.3).

This document answers two questions that were asked together because they turn out to be the same
question. First, whether a local clinical contrast graph plus hybrid retrieval should become the next
grounding and distractor-retrieval architecture. Second, how an explicit EASY / MEDIUM / HARD system
should work. They are the same question because, on this research's reading of the official MCC
material, authored difficulty is largely a property of the competitor set, and the competitor set is
what retrieval produces.

Companion artifacts:

- `reports/mcc_official_item_style_analysis.json` — structural analysis of all 55 official free questions (difficulty labels are a `MODEL_STRUCTURAL_DIFFICULTY_ESTIMATE`), plus the MCC's own published distractor standard and its empirical difficulty *methodology*.
- `reports/qgen_retrieval_architecture_comparison.json` — measured corpus inventory, four-architecture comparison, GraphRAG cost analysis, storage evaluation, frozen-G2 benchmark design.

---

## 1. What the official MCC material actually says

### 1.1 The current exam

The MCCQE is 230 single-best-answer MCQs in two sections of 115, up to 2 h 40 min per section. The
2025 modernization removed the clinical decision-making component entirely, so the exam is now MCQ-only.
Content is governed by the blueprint, with published tolerances:

| Physician activity | Target | Dimension of care | Target |
|---|---|---|---|
| Assessment / Diagnosis | 45 ±5 | Health promotion & illness prevention | 20 ±5 |
| Management | 35 ±5 | Acute | 35 ±5 |
| Communication | 10 ±5 | Chronic | 30 ±5 |
| Professional behaviours | 10 ±5 | Psychosocial aspects | 15 ±5 |

Unscored pilot items sit in the form, unidentified, and are promoted to scored status only if they
perform psychometrically well. The count is recorded locally as 20 but is only partially confirmed
against a current post-2025 source (see §15). `research/mcc/blueprint.json` and
`current_exam_profile.json` already hold this and are unchanged by this work.

### 1.2 The official distractor standard

`MCC_DISTRACTOR_STANDARD_SUMMARY`, from the MCC's own MCQ development guidelines:

- All options are **homogeneous**: same category as the key — all diagnoses, or all tests, or all
  treatments, or all dispositions. Inhomogeneity lets a test-wise candidate eliminate by pattern
  rather than by medicine, and makes the item easier than intended.
- Every distractor is **plausible**, drawn from **common misconceptions and faulty reasoning**, and
  from the mistakes a minimally competent candidate actually makes.
- **The load-bearing rule.** The author must be able to state *the line of reasoning a candidate would
  use to select each distractor*. If the author cannot, the distractor is not plausible.
- Distractors are **incorrect or definitely inferior** to the key; the key must be **defensibly best**.
  If a competent candidate can make a case for another option, that option is reformulated.
- Distractors must **not be mutually exclusive** with each other or with the stem, must not hint at the
  key, and must match it in construction and length.
- Never `All of the above` / `None of the above`; never `EXCEPT`; never negative lead-ins.
- The stem must let a competent candidate answer **with the options covered**.
- **Avoid tricky and overly complex items.** The guideline names a specific category, *irrelevant
  difficulty*: long or double options, inconsistent numerals, vague terms, non-parallel language,
  non-logical ordering.

Two of these deserve emphasis because they independently confirm work the repository has already done.
The requirement that the author be able to state the line of reasoning leading a candidate to each
distractor is, in substance, **the stem-anchor floor**. The requirement that an option a competent
candidate could argue for be reformulated is, in substance, **the ADM-3 second-key ceiling**.

`LIVE_BUT_INFERIOR_MCC_ALIGNMENT = RETAINED`, with one precision about wording:
**`LIVE_BUT_INFERIOR` is this repository's own local term. The MCC does not use that phrase, and no
claim is made that it does.** What the official guidance does establish is every property the term
names — distractors must be plausible, consistent with the stem, drawn from common misconceptions and
real candidate errors, homogeneous with the key in response class, and *incorrect or definitely
inferior* to a key that is defensibly best, with irrelevant difficulty avoided. Our local concept is
therefore not a local invention in substance; it is our name for a standard the MCC publishes in its
own words.

### 1.3 The official difficulty model

`MCC_EMPIRICAL_DIFFICULTY_METHOD_SUMMARY`:

- **Difficulty** is the p-value: the proportion of candidates selecting the key. The item-writing
  guideline gives a rule-of-thumb usable range of **0.20–0.90**, and states that a **wide range of
  difficulties is desirable, with many items near the passing level**.
- **Discrimination** is an item-total correlation (point-biserial); effective items are positive and
  above about **0.2**, typically 0.1–0.4.
- **Distractor functioning** is judged by the correlation between each distractor and total score,
  which should be **negative**. A distractor selected by almost nobody is *non-functioning* and gets
  replaced. A distractor that attracts strong candidates suggests a wrong key or a flawed item.
- Operationally the MCC runs a classical item analysis after every session and calibrates with a
  **Rasch model** (dichotomous and partial-credit, Winsteps, since spring 2015), maintaining the 2018
  scale. Items are flagged for content review when p < 0.10, p > 0.95, omits > 5 %, key correlation
  < 0.05, a distractor correlation > 0.05 with N > 10, the top 20 % of performers choose a distractor
  more often than the key, or outfit mean-square falls outside 0.5–2.0.
- **Standard setting** (July 2025, 23 physicians) used the **Bookmark** method complemented by Hofstee.
  The Bookmark method requires an **ordered item booklet running from easiest to most difficult**;
  panellists place a bookmark where a minimally competent candidate's chance of a correct answer falls
  below 67 %. The recommended cut was θ = 0.74, reported as **439** on the 300–600 scale (mean 450, SD 30).

#### What this establishes, and what it does not

`OFFICIAL_MCC_DIFFICULTY_DISTRIBUTION_CLAIMED = NO`. `MCC_PUBLISHED_EASY_MEDIUM_HARD_BANDS = NONE`.

**Established by official evidence.** MCC operational items span a range of empirically measured
difficulties. The MCC estimates item difficulty empirically, performs classical item analysis and
Rasch calibration after every administration, treats roughly 0.20–0.90 as the usable p-value range,
states that a wide range of difficulties is desirable, and standard-set the 2025 exam with the
Bookmark method, which requires an item booklet ordered from easiest to hardest.

**Not established.** None of that yields a published MCC Easy/Medium/Hard percentage distribution.
The MCC publishes no categorical difficulty bands; its difficulty measure is a continuous p-value, it
is not released per item, and no official target proportion of easy, medium or hard items exists in
any source consulted here. An ordered booklet demonstrates that a range exists — it does not describe
the shape of that range, and it must not be used to imply one.

**Therefore.** Our `EASY` / `MEDIUM` / `HARD` categories, and every target percentage attached to them
anywhere in this document, are `STUDY_BANK_DESIGN_POLICY`. They are explicitly **not** a
`RECONSTRUCTED_MCC_DIFFICULTY_DISTRIBUTION`, and no statement in this design or in its companion
reports may present them as one. Where this document argues that a mixed bank is appropriate, the
argument rests on learning-design grounds (§3.4) and on the general fact that operational MCC
difficulty varies — never on a published MCC distribution, because there is none.

Design difficulty and empirical difficulty must therefore be kept apart in our schema:

- `DIFFICULTY_INTENT` — authored, falsifiable, available at generation time.
- `EMPIRICAL_DIFFICULTY`, `EMPIRICAL_DISCRIMINATION`, `DISTRACTOR_ENDORSEMENT`,
  `DISTRACTOR_DISCRIMINATION` — measured, available only once learners answer.

---

## 2. Structural analysis of the 55 official free questions

All 55 were retrieved from the MCC free-resources PDF, parsed deterministically, and classified.
`OFFICIAL_FREE_QUESTIONS_ANALYZED = 55/55`.

**Copyright handling.** The set is published for personal, non-commercial study. No stem, option,
rationale or reference text is stored in this repository, and no derivative paraphrase of any individual
question exists in any artifact. `reports/mcc_official_item_style_analysis.json` holds abstract
structural metadata only, and each `rationale_for_classification` is written so the underlying scenario
cannot be reconstructed from it.

### 2.1 Deterministic findings

- **Option counts vary: 5 options ×33, 4 options ×21, 3 options ×1.** This resolves an open question in
  `research/mcc/item_style_profile.json`, which records five as the construction default and flags the
  live count as unconfirmed. The current published practice set is not fixed at five. Generation should
  accept 4 or 5 and must never manufacture an extra option to hit a quota — a padded option is a
  non-functioning distractor by construction.
- **Every lead-in is a closed "Which one of the following …?" question.** The most common is *best next
  step* (18 of 55); *most likely diagnosis* is second (4). Four lead-ins fix a prior action and then ask
  for the next, which is an explicit sequencing contract.
- Stems run 39–150 words, median about 75.
- **Each question has one rationale that justifies the key and then walks through every distractor.**
  That is the same per-distractor defeat statement the pipeline already produces.
- **References are per-item and external**: primary journals, guidelines and society statements
  (including Canadian sources such as the CMPA and the Canadian Task Force), StatPearls, UpToDate,
  DSM-5-TR. No single textbook is treated as the authority. This directly supports the repository rule
  that Toronto Notes is not automatically the current clinical authority.

### 2.2 Blueprint conformance

Coding one primary physician activity and one primary dimension per question:

| Activity | Observed | Target | In tolerance |
|---|---|---|---|
| Assessment / Diagnosis | 43.6 % | 45 ±5 | yes |
| Management | 34.5 % | 35 ±5 | yes |
| Communication | 10.9 % | 10 ±5 | yes |
| Professional behaviours | 10.9 % | 10 ±5 | yes |

| Dimension | Observed | Target | In tolerance |
|---|---|---|---|
| Health promotion & prevention | 16.4 % | 20 ±5 | yes |
| Acute | 32.7 % | 35 ±5 | yes |
| Chronic | 32.7 % | 30 ±5 | yes |
| Psychosocial | 18.2 % | 15 ±5 | yes |

All eight categories fall inside tolerance. The free set behaves like a blueprint-sampled miniature of
the exam. Confidence is MEDIUM: single rater, primary-category-only coding, no official per-question
classification is published.

The practical consequence is larger than it looks. **Roughly one in five official items is a
communication or professional-behaviours item**, and our contrast library and stem-feature vocabulary
are built almost entirely around diagnosis, investigation and management. Any coverage plan that
ignores the ethical, legal and communication fifth of the blueprint will systematically under-serve
the exam.

### 2.3 Difficulty and distractor structure

`MODEL_STRUCTURAL_DIFFICULTY_ESTIMATE` over the 55: **EASY 12 (21.8 %), MEDIUM 30 (54.5 %),
HARD 13 (23.6 %)**.

**This label is load-bearing and the figures must never appear without it.** The classification was
produced by this research from item structure alone, by a single rater, using the rubric in §3.2. The
MCC does **not** publish Easy/Medium/Hard labels for these 55 questions, and the published set carries
**no candidate-level statistics**, so no p-value, discrimination or option-endorsement figure can be
derived from it. `21.8 / 54.5 / 23.6` is therefore a `MODEL_STRUCTURAL_DIFFICULTY_ESTIMATE` and is
none of the following:

- MCC empirical difficulty;
- an MCC official difficulty classification;
- a real-exam difficulty distribution;
- evidence that any particular study-bank mix matches the MCC.

Its legitimate uses are internal: it calibrates our own rubric against professionally written items,
and it shows that officially published items are not uniformly hard.

The distractor findings are the important ones:

- **Zero of 55 require a trick, a withheld fact, or specialist-board trivia.**
- Mean apparently-live competitors: about 3.
- Hard items carry **more** live competitors, not fewer and weaker ones.
- In the hard items, competitors are defeated by **positively stated data requiring an inference** —
  most often the decisive move is that the *most salient* datum does not meet its own threshold, or a
  remote history item reframes the whole presentation. They are not defeated by written-in denials.

That last point is the same `GOOD_DISTRACTOR = LIVE_BUT_INFERIOR` versus
`BAD_ANCHORLESS_DISTRACTOR = CATEGORICALLY_IMPOSSIBLE` signature the G2 root-cause diagnosis isolated
from our own accepted and rejected controls. Seeing it independently in official material is the
strongest external validation the stem-anchor work has received.

---

## 3. The difficulty system

`DIFFICULTY_INTENT_MODEL = EASY_MEDIUM_HARD`. `DIFFICULTY_IS_NOT_TRICKINESS = YES`.
`DIFFICULTY_SYSTEM_STATUS = STUDY_BANK_DESIGN_POLICY`.

The whole of §3 is our own learning-design policy for our own study bank. It is informed by official
MCC item-writing guidance on distractor quality and by the fact that operational MCC difficulty is
empirically measured and varies (§1.3), but it does not reproduce, reconstruct or approximate any
published MCC difficulty distribution, because none exists.

Four invariants hold at **every** level, and no difficulty target may be met by relaxing them:

- `NO_TRICKINESS`
- `NO_SPECIALIST_TRIVIA`
- `NO_ARTIFICIAL_AMBIGUITY`
- `NO_WEAK_DISTRACTORS`

Every level, including EASY, still requires appropriate MCC-level clinical application, genuinely
plausible distractors, and a defensibly best key.

### 3.1 What HARD may never mean

Prohibited difficulty sources, each of which the MCC guideline independently forbids as *irrelevant
difficulty* or as a "tricky" item:

- obscure trivia, or rarity without MCC relevance;
- trick wording, double negatives, `EXCEPT`;
- omitting information the decision requires;
- specialist or board-level knowledge beyond a graduating Canadian medical student;
- unnatural, non-homogeneous or padded distractors;
- deliberate ambiguity, or a key that is not defensibly best.

An item that is hard for any of these reasons is a defect, not a HARD item, and must fail closed.

### 3.2 Semantic contracts

Every level requires valid MCC-level reasoning and genuinely plausible distractors. The levels differ
only in **cognitive demand** and in **competitor separability**.

**EASY** — `reasoning_depth ∈ {RECOGNITION, ONE_STEP_APPLICATION}`
- Exactly one decisive discriminator, explicitly stated and highly salient in the stem.
- 3–4 live competitors, all in the key's response class; at least one is separable once the decisive
  feature is read, without further integration.
- No sequencing, no threshold arithmetic, no competing-guideline conflict.
- Still required: every distractor has a stated candidate line of reasoning and a stem anchor.

**MEDIUM** — `reasoning_depth ∈ {ONE_STEP_APPLICATION, TWO_STEP_APPLICATION}`
- Two or three stem features must be integrated, or one rule applied to given data.
- 3–4 live competitors, all in the response class, none separable on category or salience alone.
- One decisive discriminator that a prepared candidate finds reliably.
- May involve one of: a severity or timing distinction, an age-band rule, a simple threshold.

**HARD** — `reasoning_depth ∈ {MULTI_FEATURE_INTEGRATION, SEQUENCED_MANAGEMENT}`
- Three or more features integrated, **or** a management sequence, **or** a threshold judgement where
  the most salient datum does not meet its own criterion.
- Every competitor remains strongly plausible; each is anchored on a different real datum in the stem.
- At least two clinically important discriminators, or one discriminator plus a temporal/severity or
  sequencing constraint.
- The key remains **defensibly best** and the rationale states, per distractor, the positively stated
  datum that defeats it.

Falsifiable checks, computable from artifacts the pipeline already produces:

| Check | EASY | MEDIUM | HARD |
|---|---|---|---|
| `key_discriminator_count` | 1 | 1–2 | ≥2 |
| distinct stem features load-bearing for the key | 1–2 | 2–3 | ≥3 |
| live competitors after the stem-anchor floor | ≥3 | ≥3 | ≥3 |
| competitors defeated by an explicit verbal denial | ≤1 | ≤1 | 0 |
| competitors with ≥1 anchor PRESENT | all | all | all |
| mean anchors PRESENT per competitor | ≥1 | ≥1 | ≥2 |
| sequencing or threshold constraint | no | optional | ≥1 required for SEQ form |

A claimed HARD item that fails the "0 competitors defeated by explicit verbal denial" check is not
hard; it is an item whose stem was written to switch its competitors off, which is exactly the defect
the stem-anchor floor was built to catch.

### 3.3 Recommended mixes

`STUDY_BANK_DIFFICULTY_POLICY = EASY_20_MEDIUM_55_HARD_25` for the **library**, with **delivery mixes
that differ by mode**.

`POLICY_STATUS = INITIAL_LEARNING_DESIGN_POLICY`. `DERIVED_FROM_MCC_DISTRIBUTION = NO`.
`SUPERSEDED_BY = EMPIRICAL_LEARNER_RESPONSE_DATA`.

These three numbers are a choice we are making, not a measurement we are reporting. They are an
initial learning-design policy for a study bank, adopted so that composition is explicit and
falsifiable rather than accidental, and they are expected to be **calibrated and superseded** once
empirical learner-response data exists (§13). They are not an MCC distribution, and nothing downstream
may cite them as evidence about the real exam.

The proposed 15/60/25 was evaluated and is close, but 20/55/25 is preferred on three grounds, stated
with their evidential weight:

1. **Rubric-calibration signal, weak.** It sits within a few points of this research's own
   `MODEL_STRUCTURAL_DIFFICULTY_ESTIMATE` of the official free set (21.8 / 54.5 / 23.6, §2.3). That
   estimate is our model's structural reading of published items, **not** MCC difficulty data, so this
   is a consistency check on our rubric and carries no evidential weight about exam composition.
2. **Learning-design, primary.** It preserves a majority at MEDIUM, which keeps most practice near the
   level at which the bank is trying to build competence. The MCC's own guidance that a wide range of
   difficulties is desirable is consistent with a mixed bank, but supplies no proportion.
3. **Learning-design, primary.** The extra 5 points at EASY buy retrieval success early in a topic,
   which the learning evidence in §3.4 says is the precondition for difficulty being desirable at all.

The library is not the delivery schedule. Composition and delivery are separate policies:

| Mode | EASY | MEDIUM | HARD | Rationale |
|---|---|---|---|---|
| **Learning** (first pass on a topic) | 30 | 55 | 15 | Target roughly 70–85 % success. Retrieval must succeed to strengthen memory; a first pass at 40 % success teaches little and costs adherence. Blocked by topic, immediate feedback, full rationale. |
| **Review** (spaced, later passes) | 15 | 55 | 30 | Interleave topics; select by prior performance and time since last correct answer. Desirable difficulty applies here because the background knowledge now exists. |
| **Exam simulation** | 20 | 55 | 25 | Mirror the library policy mix; sample the blueprint's eight categories in their published proportions (the blueprint *is* published, unlike any difficulty mix); no feedback until the end; timed. |

### 3.4 The learning-science basis, and its limits

- **Retrieval practice** reliably outperforms restudy for retention, and question banks are a
  legitimate vehicle for it. This is among the better-replicated findings in the field.
- **Spacing and interleaving** improve durable retention and discrimination between confusable
  categories, which is precisely the skill a LIVE_BUT_INFERIOR competitor set trains. Interleaving is
  the reason review mode must mix topics rather than block them.
- **Desirable difficulty** is real but conditional. Bjork's own condition is that the difficulty must
  be one the learner can **overcome**, and that it must engage the processes the goal requires. A
  retrieval attempt that never succeeds strengthens little. Difficulty far above the learner's current
  level is an *undesirable* difficulty.
- **An optimal-success band exists, approximately.** Wilson et al. (2019, *Nature Communications*)
  derive an optimal training error rate near 15.87 % — about 85 % success — for a broad class of
  gradient-based learners. This is a **modelling result for a class of learning algorithms, not a
  medical-education randomized trial**, and it is cited here as a directional argument only. It should
  never be presented to learners as an established fact about human exam preparation.

Together these support a mixed bank with mode-dependent delivery, and they argue specifically against
making nearly every practice question hard. They do **not** support any precise percentage; the numbers
above are an **initial learning-design policy**, chosen and stated as such. They are not an attempt to
reproduce an MCC difficulty distribution — no such published distribution exists to reproduce (§1.3) —
and they will be revised against our own learner data rather than defended.

The MCC's own operational practice is consistent with a mixed bank without prescribing a mix: usable
p-values span roughly 0.20–0.90, and Bookmark standard setting requires an easiest-to-hardest ordered
pool. That establishes range, not proportions.

---

## 4. What already exists locally

Measured deterministically; nothing was re-OCRed and no page was read by an LLM to produce these.

| Layer | State |
|---|---|
| Toronto Notes OCR | 1595 pages, per-page sha256 in `ocr/page_index.json`, only 2 pages quality-flagged |
| Clean text | 1595 files, 6.76 MB, ≈1.69 M tokens; mean page ≈1060 tokens |
| Headings | extracted on 1025 of 1595 pages |
| Chapter manifests | 32, covering 1575 pages |
| TOC inventory | 2019 nodes — 32 chapters, 468 sections, 1519 topics — with `parent_id`, TN and PDF page ranges, confidence |
| Study units | 1487, of which 1486 carry a PDF page range; 1247 carry MCC evidence |
| Competency statements | 1815 across 1423 study units |
| MCC objectives | 198, with an id crosswalk |
| Contrast seeds | 105 seeds / 105 concepts, touching **46 of 1487** study units (3.1 %) |
| Stem-feature vocabulary | 102 features across **6 of 1487** study units (0.4 %) |
| Typed contrast edges | **12**, across **1** anchor study unit (0.07 %) |

The last three rows are the whole story. `research/qgen/chapter_global_contrast_library.json` already
contains a typed contrast edge with `anchor_concept_id`, `contrast_concept_id`, study units, chapter
ids, source node ids, TN pages, PDF pages, `decision_context`, `applicable_learner_decisions`,
`shared_features`, `plausible_error`, `neighboring_choice`, `decisive_discriminant`,
`excluded_contexts`, `evidence_refs` with claim sha256, `quality_status`, `reviewer_id` and
`content_sha256`.

That is already a clinical contrast graph edge. It models plausibility, the candidate's error path, the
defeat, the second-key guard and page-level provenance. **The schema is proven. It exists for one study
unit out of 1487.** The named bottleneck `CONTRAST_LIBRARY_COVERAGE` is therefore a population problem
against an existing design, and the architecture question is how to populate it without an LLM pass
over the whole book.

### 4.1 Copyright and source boundaries

Toronto Notes is a legally obtained local study source. It may be used internally for topic
organization, concept and differential discovery, clinical vocabulary, page and chapter provenance, and
contrast discovery. It must **not** become a redistributable database of copied prose.

Rules for the graph:

- Store **normalized concepts, typed relations, page and chunk references, and hashes**.
- Store an **evidence span reference** (page, node id, character offsets) rather than the span text
  wherever the reference suffices.
- Where a short fragment is genuinely necessary to adjudicate a claim, cap it, mark it
  `MINIMAL_FRAGMENT`, and record that it exists for adjudication only.
- Never emit Toronto Notes prose into a generated question, a rationale, or any exported artifact.
- Generated questions remain original. They must not reproduce Toronto Notes, recalled or leaked MCC
  questions, or commercial question banks.
- `CURRENT_CLINICAL_AUTHORITY_SEPARATED_FROM_TN = YES`, enforced structurally in §6.

---

## 5. Architecture decision

`RECOMMENDED_RETRIEVAL_ARCHITECTURE = HYBRID_CLINICAL_CONTRAST_GRAPH_PLUS_RAG`.

`ARCHITECTURE_RECOMMENDATION_CONDITIONAL_ON_BENCHMARK = YES`. `GRAPH_CONSTRUCTION_AUTHORIZED = NO`.

The recommendation is a **recommendation to test in the stated order**, not an authorization to build.
It is conditional on the frozen-G2 retrieval benchmark of §10 meeting its pre-committed decision rule,
and that rule is written to be losable: if plain BM25 alone closes the gap, no graph is built; if no
arm closes it, the bottleneck is not retrieval and the graph must not be built at all. Full graph
construction over the corpus remains unauthorized until Phase 3 reports (§14). This document builds
nothing.

The four-way comparison is in `reports/qgen_retrieval_architecture_comparison.json`. In summary:

- **A — current curated library only.** Highest precision, zero recall outside 3.1 % of study units.
  Validated and necessary; the coverage growth rate is the binding constraint. Keep it; it becomes the
  graph's highest-authority edge set.
- **B — plain local RAG.** Cheap and high-recall, but similarity over prose cannot express "plausible
  *here*, defeated by *this* printed datum". Generic medical similarity is exactly what admitted the R4
  defective distractors. Good discovery substrate, wrong decision layer.
- **C — full generic GraphRAG.** Rejected. See §5.1.
- **D — hybrid typed graph + BM25.** Recommended.

### 5.1 Why full GraphRAG is rejected

`TORONTO_NOTES_FULL_LLM_GRAPH_EXTRACTION_RECOMMENDED = NO`.

The standard GraphRAG index requires LLM calls for entity extraction, relationship extraction, entity
summarization, relationship summarization, optional claim extraction and community report generation;
only community detection is deterministic. Graph extraction alone is reported as roughly 75 % of
indexing cost, and Microsoft's own documentation warns the operation is expensive. A commonly cited
figure for a single average textbook is on the order of 4,000 LLM calls per indexing pass.

For this corpus the token count and the text-unit arithmetic are measured/derived from the committed
corpus: 1.69 M tokens is about 3,100 text units at 600 tokens with overlap, or 6,200 at 300. The call
count is not. With gleanings, per-entity and per-relationship summarization and community reports, a
standard index is an **order-of-10⁴ LLM-call operation** — an `ENGINEERING_ESTIMATE`, as is the
commonly cited ~4,000-call figure above, which is a third-party published signal and not a measurement
of this corpus. Both are order-of-magnitude arguments, and neither is claimed as an experimental
result. No dollar figure is estimated here, deliberately. The project's constraint is **no LLM API calls and small context**; a
standard GraphRAG index violates it by construction.

The deeper objection is that it would spend that budget on layers we cannot use:

- **Community detection and community reports are useless to us.** Our retrieval question is strictly
  local — given a learner decision, an item archetype, an option-set archetype and a realized
  stem-feature map, return the competitors. It is never "what are the themes of this corpus". Global
  narrative summarization is the thing GraphRAG is best at and the thing we never ask for.
- **Entity and relationship summaries are prose.** The floor needs typed predicates with polarity and a
  cited claim. A generated summary is strictly worse than the source span for that purpose, and it
  inserts an LLM-authored layer between the source and the claim — which under `AGENTS.md` is model
  agreement, and model agreement is not evidence.
- **Our node vocabulary is not open.** It is bounded by 1487 study units, 198 MCC objectives, a closed
  set of option-set archetypes and a stem-feature vocabulary. Open-vocabulary entity extraction solves
  a problem we do not have.

`GRAPH_YES, GRAPHRAG_NO`.

---

## 6. The clinical contrast graph

Derived to the minimum that improves retrieval. Node and relation types were cut wherever they did not
change a retrieval decision.

### 6.1 Node types (11)

**Structural / already exist as ids:**
`STUDY_UNIT`, `MCC_OBJECTIVE`, `TN_NODE` (TOC node id, e.g. `C.S06.T02`), `SOURCE`, `EVIDENCE_CLAIM`.

**Decision-shaping / already exist in the wave contracts:**
`LEARNER_DECISION`, `OPTION_SET_ARCHETYPE`.

**Clinical:**
`CONDITION` — a named diagnostic entity.
`FINDING` — the merged type for symptom, sign, risk factor, test result, temporal pattern and severity
state. These are the same thing for retrieval: a stem-assertable feature with a polarity. They are
distinguished by a `finding_kind` attribute, not by separate node types.
`ACTION` — the merged type for investigation, management action, treatment and disposition, again
distinguished by an attribute. What matters for retrieval is which option-set archetype an action can
populate, not its ontological family.
`POPULATION` — age band, pregnancy state, care setting, when it gates admissibility.

**Deliberately not separate node types:** `PRESENTATION` (it is a `LEARNER_DECISION` plus its anchor
`FINDING` set), `SYMPTOM`/`SIGN`/`RISK_FACTOR`/`TEMPORAL_PATTERN`/`SEVERITY_STATE` (attributes of
`FINDING`), `INVESTIGATION`/`TREATMENT`/`CONTRAINDICATION`/`COMPLICATION` (attributes of `ACTION` or
edges), `ITEM_ARCHETYPE` (an attribute of the opportunity, not a graph node).

### 6.2 Relation types (8)

The two that do the work, and that no existing structure supplies at scale:

1. `PLAUSIBILITY_ANCHOR(CONDITION|ACTION → FINDING)` — this finding, **PRESENT**, gives a candidate a
   positive reason to *consider* this competitor. This is the graph form of the validated stem-anchor
   invariant.
2. `DEFEATED_BY(CONDITION|ACTION → FINDING, required_polarity)` — the correctness condition. The
   competitor would be right if this finding held with this polarity; the stem says otherwise.

The rest:

3. `PRESENTS_WITH(CONDITION → FINDING)` — discovery and vocabulary; not admissibility.
4. `CONFUSED_WITH(CONDITION ↔ CONDITION)` — the differential edge; the discovery seed for candidates.
5. `INDICATED_WHEN(ACTION → FINDING)` / `CONTRAINDICATED_WHEN(ACTION → FINDING)`.
6. `ANSWERS(CONDITION|ACTION → LEARNER_DECISION, option_set_archetype, decision_granularity)` — the
   same-decision, same-class, same-grain filter, as an edge rather than a post-hoc test.
7. `BELONGS_TO(STUDY_UNIT → MCC_OBJECTIVE)`, `BELONGS_TO(CONDITION|ACTION → STUDY_UNIT)`.
8. `SUPPORTED_BY(any edge → EVIDENCE_CLAIM → SOURCE)`.

`EXCLUDES`, `REQUIRES`, `PRECEDES` and `ESCALATES_TO` were considered and dropped from v1:
`EXCLUDES` is `DEFEATED_BY` with the polarity inverted; `REQUIRES` is `INDICATED_WHEN`; `PRECEDES` and
`ESCALATES_TO` matter only for sequencing items and can be added when the first `SEQUENCED_MANAGEMENT`
opportunity needs them, rather than modelled speculatively now.

### 6.3 Edge provenance contract

`GRAPH_PROVENANCE_CONTRACT = DEFINED`. Every medically meaningful edge carries:

```
edge_id                     stable, content-addressed
source_node, relation, target_node
source_type                 TORONTO_NOTES | MCC | CANADIAN_GUIDELINE | PEER_REVIEWED | OTHER
authority_role              TOPIC_DISCOVERY_SOURCE | CURRENT_CLINICAL_AUTHORITY
source_id, page, tn_node_id, chunk_id
evidence_span_reference     page + node id + offsets; span text only as MINIMAL_FRAGMENT when required
polarity                    PRESENT | ABSENT | NOT_APPLICABLE
population, age_range, pregnancy_context, severity_context, temporal_context, jurisdiction
currentness_date
confidence                  HIGH | MEDIUM | LOW
verification_status         DERIVED | REVIEWED | VALIDATED | REFUTED
derivation_rule             the deterministic rule or the reviewer id that produced it
content_sha256
```

**The authority rule, enforced and not merely documented.**

- Toronto Notes edges are created with `authority_role = TOPIC_DISCOVERY_SOURCE`. They may supply
  vocabulary, differentials, `CONFUSED_WITH` candidates and page provenance.
- An edge may act as a `CURRENT_CLINICAL_AUTHORITY` only with `source_type ∈ {MCC, CANADIAN_GUIDELINE,
  PEER_REVIEWED}` and a `currentness_date`.
- **A `TOPIC_DISCOVERY_SOURCE` edge may never be the sole support for a candidate-facing clinical
  claim, and may never override a `CURRENT_CLINICAL_AUTHORITY` edge on the same relation.** Where they
  disagree, the authority edge wins and the discovery edge is marked `REFUTED` with a pointer, which is
  auditable rather than silent.
- Discovery edges are allowed to *propose* a competitor. Only authority edges may *justify* one.

This is the structural version of the rule the repository already states in prose, and it is what makes
a 2025 textbook safe to index.

---

## 7. Staged, cost-optimized index strategy

`TORONTO_NOTES_FULL_DETERMINISTIC_INDEX_RECOMMENDED = YES`.
`LOCAL_FIRST = YES`. `LLM_API_REQUIRED = NO`.

**Stage 1 — deterministic whole-book index. No LLM.**
Already 90 % done. Join the existing page index, TOC inventory (2019 nodes), chapter manifests and the
1487 study units into one addressable spine: `page → tn_node → study_unit → mcc_objective`, each with
sha256 and page range. Build SQLite FTS5 over clean text at page and study-unit granularity.

**Stage 2 — normalized concept detection. Dictionaries, rules, local NLP. No LLM.**
Seed the concept vocabulary from what already exists: 105 reviewed competitor concepts, 102 stem
features, 1815 competency statements, 198 objective titles, and the TOC's 1519 topic headings. Match
against the corpus with normalized string and morphological matching. Every detection stores its page
and node id. Output: `CONDITION`, `ACTION` and `FINDING` candidate nodes with provenance and a
confidence. Human/LLM review is spent on the *vocabulary*, which is small, not on the *corpus*, which
is not.

**Stage 3 — typed graph construction from high-confidence explicit structure. No LLM.**
Toronto Notes is heavily structured: differential lists, "Etiology", "Investigations", "Treatment",
"Clinical Features", comparison tables. Deterministic parsers over those structures yield
`PRESENTS_WITH`, `CONFUSED_WITH` (co-membership of one differential list), `INDICATED_WHEN` and
`BELONGS_TO` at scale, each with `authority_role = TOPIC_DISCOVERY_SOURCE`. This produces the candidate
universe and nothing that is candidate-facing.

**Stage 4 — targeted semantic enrichment, only where deterministic extraction is insufficient.**
`PLAUSIBILITY_ANCHOR` and `DEFEATED_BY` are the two relations no parser can produce, because they are
judgements about what makes a competitor considerable and what defeats it. These are authored by
Claude/Codex **per study unit that is actually being generated**, over a retrieved neighbourhood of a
few thousand tokens, and passed through the existing independent seed review. Budget scales with
questions actually built, not with 1595 pages.

**Stage 5 — on-demand enrichment for high-priority opportunities.**
Cache the result. A study unit is enriched once and reused across every opportunity on it.

The saving is structural: Stages 1–3 are free and cover the whole book; Stage 4 is the only paid stage
and is proportional to output, not to corpus size.

---

## 8. Storage

`SQLITE_FTS5_RECOMMENDED = YES`. `TYPED_CLINICAL_GRAPH_RECOMMENDED = YES`.
`LOCAL_EMBEDDINGS_REQUIRED = BENCHMARK_FIRST`.

- Projected graph size is low tens of thousands of nodes and low hundreds of thousands of edges — two
  to three orders of magnitude below where Neo4j earns its operational cost.
- **SQLite adjacency tables** (`nodes`, `edges`, `edge_provenance`), one file, rebuildable.
- **JSON artifacts stay canonical** and reviewable, consistent with every existing frozen layer.
  SQLite is a derived index and is regenerated, never hand-edited.
- **SQLite FTS5 + BM25** for text. 6.76 MB indexes in seconds.
- **NetworkX** for offline analysis and export only, never in the retrieval path.
- **No embedding API.** If the benchmark shows BM25 plus graph misses candidates that embeddings
  recover, add a locally runnable sentence-encoder-class model, CPU-only, a few hundred MB; 3–6 k text
  units is a trivial index. No GPU.
- Rejected for now: Neo4j, external vector databases, hosted services.

---

## 9. Hybrid retrieval, stem-conditional by construction

`STEM_CONDITIONAL_RETRIEVAL = DEFINED`. `LIVE_BUT_INFERIOR_RETRIEVAL = DEFINED`.

The G2 finding this must solve: a condition or action can be related to the topic and still be
irrelevant in the realized scenario. Retrieval must therefore condition on **actual stem features**,
not on chapter, diagnosis or study unit.

Recommended order, with the reason each step sits where it does:

```
 1. QUESTION OPPORTUNITY            learner decision, MCC objective, difficulty intent,
                                    item archetype, option-set archetype
 2. STEM AND KEY REALIZED           open-ended, from evidence claims, before any option exists
 3. STRUCTURED STEM FEATURES        stem -> stem_feature_map, each feature with polarity
 4. GRAPH CONSTRAINT FILTER         ANSWERS edges: same learner decision, same option-set
                                    archetype, same decision granularity        [cheap, exact]
 5. GRAPH NEIGHBOURHOOD             CONFUSED_WITH / INDICATED_WHEN expansion from the key
 6. BM25 LEXICAL CANDIDATES         over study-unit spans, for concepts not yet typed
 7. OPTIONAL LOCAL DENSE CANDIDATES only if the benchmark justifies it
 8. MERGE + DETERMINISTIC RANK      union, dedupe by concept id, rank by typed signals only
 9. SAME-DECISION / ARCHETYPE /     re-applied to BM25 and dense arrivals, which have no
    GRANULARITY FILTER              ANSWERS edge yet
10. STEM-ANCHOR FLOOR (SAF-1)       >=1 PLAUSIBILITY_ANCHOR realized PRESENT   [UNCHANGED]
11. SECOND-KEY CEILING (ADM-3)      reject if every DEFEATED_BY condition is satisfied [UNCHANGED]
12. SMALL SEMANTIC RERANK           LLM over <=12 typed rows, never over prose
13. LIVE_BUT_INFERIOR SET           3-6 competitors, each with anchors, defeat and provenance
```

Why this order:

- **Steps 4–5 before 6.** The graph filter is exact and nearly free; running BM25 first would spend
  recall budget on candidates the archetype filter discards anyway.
- **Step 9 after the merge, not before.** Lexical and dense arrivals have no `ANSWERS` edge, so the
  filter must be re-applied to them or the graph's discipline leaks.
- **Floor before ceiling (10 before 11).** The floor is cheaper and removes more. Order does not change
  the result — they are independent — but it changes cost.
- **Rerank last and small (12).** The LLM sees at most a dozen typed rows and never invents the
  candidate universe. This is the single most important property of the design.

For each candidate the retrieval layer derives, and reports:

- `PLAUSIBILITY_ANCHORS` — anchor findings realized PRESENT in this stem.
- `DEFEATING_DISCRIMINATORS` — the stem data that defeat it, each classified as a *positively stated
  datum* or an *explicit verbal denial*. The second class is capped by difficulty level (§3.2).
- `SECOND_KEY_RISK` — fraction of `DEFEATED_BY` conditions satisfied; 1.0 is a hard reject.
- `CATEGORICAL_EXCLUSION` — no anchor PRESENT, or population gate fails.

Target: `LIVE_BUT_INFERIOR`.

### 9.1 Worked structural example

Abstract, to avoid asserting unsourced medical relations. Take a stem whose realized feature map
contains **neck pain (PRESENT)** and **nausea (PRESENT)**, for a `DIAGNOSIS` archetype with a
`DIAGNOSIS_SET` option set.

1. **Normalize.** Both surface strings map to `FINDING` nodes via the Stage-2 vocabulary, each with
   polarity PRESENT and a page-level provenance for the vocabulary entry.
2. **Constrain.** `ANSWERS` edges restrict to `CONDITION` nodes that answer this learner decision at
   `SINGLE_DIAGNOSIS` granularity for a `DIAGNOSIS_SET`. Actions and investigations are gone before any
   clinical reasoning happens.
3. **Neighbourhood.** `PLAUSIBILITY_ANCHOR⁻¹` from both findings returns every condition for which
   *neck pain* or *nausea*, present, is a reason to consider it. `CONFUSED_WITH` from the key adds the
   differential Toronto Notes itself groups together — discovery only, since those edges are
   `TOPIC_DISCOVERY_SOURCE`.
4. **Lexical fill.** BM25 over the study-unit spans catches concepts Stage 2 has not typed yet.
5. **Remove the irrelevant.** A condition retrieved only because it shares the study unit, with no
   anchor PRESENT in *this* map, fails the floor. This is exactly the G2 failure mode, and it is now a
   graph property rather than a post-hoc test.
6. **Preserve the partial.** A condition anchored on *nausea* alone but not *neck pain* **survives** —
   it is live but weaker. Anchors are a floor, not a scoring threshold, and pruning these would rebuild
   the anchorless-versus-live confusion in the opposite direction.
7. **Reject second keys.** Any condition whose every `DEFEATED_BY` condition is satisfied by this map
   is a second key, not a distractor.
8. **Attach provenance.** Each survivor carries its anchor edges, its defeat edges, its cited
   `EVIDENCE_CLAIM`s and their sources. Discovery-only survivors are flagged as needing an authority
   claim before they may be realized.

No medical relation is asserted here that the graph would not have to source.

---

## 10. Frozen-G2 retrieval benchmark

`FROZEN_G2_RETRIEVAL_BENCHMARK = DEFINED`. **Designed, not run.**

- **Population:** the same 30 frozen G2 opportunities, with attention to the 19 that end
  `FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS` and the 2 whose retrieval index is empty.
- **Arms:** A current library · B plain BM25 · C graph only · D hybrid.
- **Held constant:** the frozen stems and their feature maps, the keys, the option-set archetypes, the
  stem-anchor floor, the ADM-3 ceiling, the evidence packets.
- **Metrics:** candidate recall against a frozen reference competitor set; same-learner-decision
  precision; same-archetype precision; decision-granularity precision; stem-anchor survival;
  second-key rejection; count of opportunities reaching ≥3 admissible competitors; retrieved context
  tokens per opportunity; share of candidates carrying a page-level source reference.
- **Not the only metric:** final accepted yield.
- **Reference-set rule:** the reference competitor set is frozen **before** any arm runs and is authored
  without seeing which arm retrieves what.
- **Decision rule, fixed now:** expand graph coverage only if D beats A on opportunities reaching three
  admissible competitors **and** does not lose on stem-anchor survival or second-key rejection. If B
  alone closes the gap, build no graph. If no arm closes it, the bottleneck is not retrieval and the
  graph must not be built.

---

## 11. Anti-hallucination and low-token contracts

### 11.1 Evidence contract

**LLM memory is never sufficient for a candidate-facing clinical claim.** Every such claim resolves to
a graph edge and/or a retrieved source claim with provenance. Retrieval improves grounding; it does not
replace validation. Unchanged and still authoritative: critical-fact adjudication, numeric and unit
checking, evidence entailment, independent verification, fail-closed on unresolved evidence, provenance
or single-best-answer ambiguity.

Three additions the graph makes possible:

- A realized distractor must name the `PLAUSIBILITY_ANCHOR` edge and the `DEFEATED_BY` edge that
  produced it. A freehand distractor already raises; now it is unrepresentable.
- A claim supported only by `TOPIC_DISCOVERY_SOURCE` edges fails closed with a distinct reason
  (`FAIL_CLOSED_NO_CURRENT_AUTHORITY`) instead of silently inheriting textbook currency.
- Edge `content_sha256` lets a verifier prove it read the same edge the generator did.

### 11.2 Context packet

`LOW_TOKEN_CONTEXT_CONTRACT = DEFINED`. `TOKEN_FIGURES_IN_THIS_SECTION = ENGINEERING_ESTIMATE`.

**Every token number below is an ENGINEERING ESTIMATE, not a measurement.** None of them was measured
from repository artifacts; they are budgeting figures derived by hand from the shape of the intended
context packet. They must not be cited as experimentally established, and the frozen-G2 benchmark
(§10) is where actual retrieved-context sizes get measured — `retrieved context tokens per
opportunity` is already one of its metrics. The one exception in this document is §4, whose corpus
figures (1595 pages, 6.76 MB, ≈1.69 M tokens) *were* measured deterministically from the committed
corpus.

One generated question is budgeted to receive:

```
learner decision + MCC objective id + difficulty intent      ~   60 tokens
item archetype + option-set archetype + demanded class       ~   40
key concept + its study unit anchor                          ~   40
small TN anchor context (headings + <=1 minimal fragment)    ~  250
current evidence claims (3-6, verbatim, with source ids)     ~  600
stem-specific graph neighbourhood (typed rows only)          ~  400
3-6 candidate competitors, each with anchors + defeat        ~  500
provenance block (ids and hashes, no prose)                  ~  150
                                                        total ~ 2,000
```

Relative context sizes, tokens, no dollar figures. **All five rows are ENGINEERING ESTIMATES** — the
first row included, since today's evidence-packet size has not been instrumented either:

| Approach | Retrieved context per question (ENGINEERING ESTIMATE) |
|---|---|
| Current (evidence packet + seeds) | ~3,000–6,000 |
| Plain RAG, top-k page passages | ~8,000–15,000 |
| Full GraphRAG local search with community context | ~8,000–20,000 |
| **Hybrid typed neighbourhood** | **~1,500–3,000** |
| Whole chapter, if ever sent | ~100,000 |

`EXPECTED_TOKEN_EFFECT = LOWER` than today, and substantially lower than any prose-retrieval
alternative, because typed rows replace prose and the candidate set is capped. This expectation is a
prediction the benchmark must confirm, not a result.

### 11.3 Caching

Deterministic, content-addressed, reusable caches for: normalized concept detections; graph
neighbourhoods keyed by (learner decision, archetype, stem-feature set hash); retrieval results;
stem feature vectors; candidate rankings; source packets; evidence claims.

The verifier reuses the generator's retrieved evidence by `content_sha256` rather than re-researching,
and re-retrieves only when adjudication is actually required — a disputed numeric, a currentness
trigger, or a claim the generator marked uncertain. Independent *judgement* is preserved; only the
*retrieval* is shared. Same-stem, same-decision regeneration then costs one rerank instead of a full
research pass.

---

## 12. Difficulty-aware retrieval

Difficulty must never be produced by inserting weaker or stronger fake distractors. It is produced by
**which admissible competitors are selected** from a set that has already passed the floor and the
ceiling — and by nothing else.

| | EASY | MEDIUM | HARD |
|---|---|---|---|
| Candidate pool | same | same | same |
| Floor and ceiling | unchanged | unchanged | unchanged |
| Selection rule | ≥1 competitor with exactly one anchor PRESENT and a highly salient defeat | competitors with 1–2 anchors PRESENT; no competitor separable on category | all competitors with ≥2 anchors PRESENT; each anchored on a *different* stem datum |
| Defeat type | at least one defeat is a single salient stated datum | positively stated data requiring an inference | positively stated data only; **zero** explicit verbal denials |
| Extra constraint | none | one severity, timing or threshold element permitted | ≥2 discriminators, or a sequencing/threshold constraint |
| Key status | defensibly best | defensibly best | defensibly best |

Every level draws from the same pool under the same gates. **No level relaxes the second-key ceiling,
and ambiguity is never introduced deliberately.** If a difficulty target cannot be met from admissible
competitors, the opportunity fails closed at that target — it does not degrade the option set to reach
it. A HARD target that cannot be met is a coverage finding, not a licence to weaken the item.

---

## 13. Future psychometric calibration

`FUTURE_BETA_PSYCHOMETRICS = DEFINED`. Inspired by real examination development; **MCC scoring is not
copied**.

Lifecycle: `DRAFT → BETA → ACTIVE → FLAGGED → RETIRED`.

New items enter **BETA**: delivered and scored for the learner, excluded from any reported metric and
from adaptive selection, and clearly not treated as calibrated.

Once learner responses exist, compute per item: `percent_correct`, `EMPIRICAL_DIFFICULTY`,
`EMPIRICAL_DISCRIMINATION` (item-total correlation), per-option `DISTRACTOR_ENDORSEMENT` and
`DISTRACTOR_DISCRIMINATION`, and median `response_time`.

**No mandatory minimum sample size is invented here.** The literature does not support a single
universal N, and asserting one would be fabrication. Instead: report every statistic with a confidence
interval, keep an item in BETA until its difficulty interval is narrower than a stated width, and
record the achieved N alongside every value. The threshold is a policy decision to be made from our own
data once it exists.

Review triggers, adapted from the MCC's published flags but applied to a study bank rather than a
licensing exam: near-floor or near-ceiling percent correct; non-positive key discrimination; a
distractor with positive discrimination; a distractor with near-zero endorsement (a non-functioning
distractor — the classic signal that a competitor was not live after all); response time far from the
bank median.

`DIFFICULTY_INTENT` and `EMPIRICAL_DIFFICULTY` are stored separately and **never overwrite each other**.
Their disagreement is the most valuable signal the system can produce: an item authored HARD that
everyone answers correctly means the authored discriminator was not actually discriminating, and a
systematic pattern of such disagreements is direct feedback on the rubric in §3.2.

Later, empirical data may drive adaptive selection — choose the next item to sit near the learner's
estimated ability in review mode, and toward the ~70–85 % success band in learning mode. That belongs
to a later design and is out of scope here.

---

## 14. Phasing

Nothing below is authorized by this document; each phase is a separate task with its own gate.

- **Phase 1 — deterministic whole-book index.** No LLM. Join page index, TOC, chapters and study units
  into one addressable spine; build SQLite FTS5. Gate: every study unit resolves to pages with sha256,
  and BM25 returns the correct study unit for a sample of known concepts.
- **Phase 2 — small clinical contrast graph prototype.** Only the study units the frozen G2 cohort
  touches. Generalize the existing 12-edge schema; populate Stages 2–3 deterministically; author
  `PLAUSIBILITY_ANCHOR` and `DEFEATED_BY` for that slice only. Gate: the frozen G2 competitor sets are
  reproduced from graph edges alone, with the floor and ceiling unchanged.
- **Phase 3 — run the frozen-G2 benchmark** of §10. **This is the decision point.** If arm D does not
  beat arm A under the pre-committed rule, stop and report; do not expand.
- **Phase 4 — expand coverage**, only if Phase 3 succeeds, prioritized by uncovered CORE MCC objectives
  and by the communication and professional-behaviours fifth of the blueprint that the current library
  neglects.
- **Phase 5 — integrate with generation**: hybrid retrieval feeds the existing wave; the context packet
  of §11.2 replaces the current evidence-packet assembly; caches turn on.

The full semantic graph is never extracted before the benchmark demonstrates that it improves
retrieval. That ordering is the point of the whole design.

---

## 15. Open questions

1. Whether the current (post-2025) exam still carries exactly 20 pilot items is not confirmed from a
   current official source; `research/mcc/current_exam_profile.json` already records this as partially
   confirmed and it stays that way.
2. Whether the live exam permits 3-option items, as the published practice set does, or whether that is
   a practice-set convention only.
3. Whether Stage-3 deterministic parsing of Toronto Notes differential lists yields enough
   `CONFUSED_WITH` edges to matter. Measurable in Phase 1 at no LLM cost, and it should be measured
   before Phase 2 is scoped.
4. Whether local embeddings add recall over BM25 plus graph. Benchmark, do not assume.
5. Whether the 20/55/25 library mix survives contact with real learner data. It is an initial
   learning-design policy, not a finding, and it is expected to be calibrated and superseded once
   empirical difficulty exists.

---

## 16. Design self-review

Each item was checked against the finalized text of this document and its two companion reports.

| # | Check | Result | Where |
|---|---|---|---|
| 1 | No statement presents model-assigned question difficulty as MCC empirical difficulty | PASS | §1.3, §2.3, §3, §13; `analysis_label` and `not_labels` in the item-style report |
| 2 | No claim invents an official MCC Easy/Medium/Hard distribution | PASS | §1.3 states explicitly that none is published |
| 3 | 20/55/25 is never treated as an MCC distribution | PASS | §3.3 labels it `INITIAL_LEARNING_DESIGN_POLICY`, `DERIVED_FROM_MCC_DISTRIBUTION = NO` |
| 4 | The hybrid graph recommendation stays conditional on benchmark success | PASS | §5, §10 decision rule, §14 Phase 3 gate |
| 5 | Generic/full GraphRAG is not selected by default | PASS | §5.1, `GRAPH_YES, GRAPHRAG_NO` |
| 6 | Full-corpus LLM extraction is not recommended | PASS | §5.1, §7 Stages 1–3 are deterministic; Stage 4 scales with output |
| 7 | Toronto Notes is separated from current clinical authority | PASS | §4.1, §6.3 `authority_role` rule enforced structurally |
| 8 | Local-first / no-API architecture retained | PASS | §7, §8; `LOCAL_EMBEDDINGS_REQUIRED = BENCHMARK_FIRST` |
| 9 | No production implementation occurred | PASS | Header status block; only this spec and two reports change |

Two further checks this design imposes on itself:

- **Token figures.** Every token number in §11.2, and the LLM-call figures in §5.1, are labelled
  `ENGINEERING_ESTIMATE`. The only deterministically measured quantities are the corpus inventory in §4
  and the text-unit arithmetic derived from it. The benchmark measures real context sizes.
- **Terminology.** `LIVE_BUT_INFERIOR` is identified as this repository's own term (§1.2); no claim is
  made that the MCC uses it, only that official guidance establishes the properties it names.
