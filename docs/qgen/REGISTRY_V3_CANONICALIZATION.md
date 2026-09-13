# Registry V3 canonicalization

Status: **frozen for production-question use**.

Registry V3 is the first curriculum registry built under the architecture the
relation-matcher closeout left behind:

    DETERMINISTIC_CANDIDATE_PROPOSAL + SEMANTIC_ADJUDICATION

No automatic relation matcher has authority anywhere in this build. Deterministic
code mines candidates, proves exact-invariant duplicates, builds the relation
graph, derives canonical components, computes every metric and serializes every
artifact. Relation *labels* come only from frozen offline semantic adjudication.

Code: `scripts/qbank/registry_v3_canonicalization.py`
Tests: `tests/test_registry_v3_canonicalization.py`
Artifacts: `research/qgen/opportunity_registry_v3_canonical/`

## Frozen inputs

| input | rows | content sha256 |
| --- | --- | --- |
| `curriculum_question_opportunity_registry_v1.json` | 1,541 | `aa465f77…` |
| `curriculum_question_opportunity_registry_v2.json` | 2,001 | `d1625711…` |
| `normalized_atomic_opportunity_benchmark_v2.json` | 145 | `dba01681…` |
| `atomic_opportunity_contract_v1.json` | — | `c250e20c…` |

Registry V2 is treated as immutable. V3 is a new versioned artifact in a new
directory; no historical file is rewritten.

## What one V3 row is

One independently scoreable learner decision for a graduating Canadian medical
student entering supervised practice — the frozen Atomic Opportunity Contract V1,
unchanged. A V3 row is explicitly *not* a topic heading, a bare disease name, a
chapter heading, an umbrella category, a wording variant, a presentation wrapper,
or a specialist subdetail without independent MCCQE value.

## Deterministic candidate discovery

All-pairs semantic comparison was never run. Blocking on study unit, discipline +
topic, discipline + study-unit title, shared MCC objective, and a rare-token
lexical index proposes **21,770** candidate pairs out of 2,001,000 possible —
roughly 1%. Pairs are then tiered by shared scope, family, response class and
lexical overlap; only tiers T1–T3 (**427** pairs) reach semantic review.

### Retrieval recall audit

Measured against the 167 already-adjudicated Registry-V2-to-Registry-V2 pairs in
the frozen relation gold, used purely as a retrieval diagnostic and never to tune
a label:

- every collapsing relation retrieved **and queued**: 14/14
- directional containment retrieved: 15/15
- known-unrelated pairs correctly excluded: 40/40
- one `RELATED_BUT_DISTINCT` pair missed (non-destructive)

High recall with low precision is the intended shape.

## Relation effect on canonicalization

| relation | effect |
| --- | --- |
| `DUPLICATE`, `EQUIVALENT` | collapse to one canonical decision; both source ids kept as lineage |
| `VARIANT_OF_SAME_DECISION` | attach as a variant descriptor, never a second coverage unit |
| `NEAR_DUPLICATE` | retain separately with a review flag; never merged automatically |
| `REGISTRY_BROADER_CONTAINS_BENCHMARK` / `REGISTRY_NARROWER_THAN_BENCHMARK` | preserve the directional link; both endpoints stay independent |
| `RELATED_BUT_DISTINCT`, `UNRELATED` | keep separate |
| `UNCERTAIN` | fail closed: never merge, never remove, always queue |

## Exact-duplicate fast path

Deterministic collapse is allowed only on full invariant identity — fingerprint,
atomic signature, and projected-record hash all matching. Registry V2 is already
exactly deduplicated on every one of those, so **0** pairs resolved this way.
Fuzzy similarity was never accepted as identity.

## Semantic adjudication

| stage | pairs |
| --- | --- |
| queued high-impact candidates | 427 |
| already resolved by frozen double-reviewed gold | 99 |
| primary adjudications performed | 328 |
| destructive proposals sent to a second independent reviewer | 52 |
| reviewer agreement | 28 (0.538) |
| disagreements sent to a third fresh adjudicator | 24 |
| benchmark-mapping adjudications | 264 (+37 reused) |
| missing-benchmark dispositions | 64 |

A destructive relation never binds on one reviewer: either two independent
reviewers agreed, or a third adjudicator concurred that the pair is one decision.
`resolve_registry_relations` raises if that invariant is ever violated.

## Deterministic atomicity screen

Registry V2 inherited all 1,541 V1 rows in the generated wrapper form
`Apply <phrase> reasoning for <study unit>.` The wrapper is a presentation shell,
so the question is what `<phrase>` denotes:

| form | rows | can be a canonical decision |
| --- | --- | --- |
| `CONCRETE_DECISION_STATEMENT` | 458 | yes |
| `NAMED_PHRASE_WRAPPER` | 685 | not yet proven |
| `GENERIC_CATEGORY_WRAPPER` | 821 | no — the phrase is entirely curriculum-category vocabulary, so it names a heading |

This is a structural screen only. It never asserts that a concrete statement *is*
atomic; it asserts that a bare category heading cannot be.

## Registry V3

- canonical rows: **1,964** (from 2,001 V2 rows)
- source rows collapsed by adjudicated equivalence: 33
- source rows demoted to variant descriptors: 4
- every V2 row traced to exactly one canonical row: yes

Lifecycle states: `PRODUCTION_ELIGIBLE` 445, `NEEDS_SEMANTIC_REVIEW` 1,510,
`REFERENCE_ONLY` 9. Production-eligible rows span all six disciplines
(MED 248, SURG 108, OBGYN 36, PED 29, PSY 14, PHELO 10).

Canonical ids are `QOP-V3C-<sha256(sorted source ids)[:12]>` — content-derived,
order-independent, never positional, and stable when unrelated rows are added.

## Coverage

Metrics are deliberately kept separate rather than collapsed into one recall
number:

| metric | value |
| --- | --- |
| atomic-equivalent benchmark recall | 0.0207 |
| atomic-equivalent precision | 0.0256 |
| curriculum-decision coverage (any granularity) | 0.5586 |
| missing benchmark decisions | 64 |
| registry-only decisions | 1,847 |
| atomization deficit | 77 |
| variant capture | 3 |
| duplicate rate | 0.0165 |
| over-split rate | 0.0 |
| uncertain rate | 0.0 |

The dominant finding: of 145 benchmark decisions, 81 are represented somewhere in
the registry but only **3** are held at the same granularity. **77** exist solely
inside a broader registry heading. The registry's problem is not scope — it is
that most of it is headings rather than decisions, which is exactly what the
atomicity screen independently measures.

Benchmark mapping is many-to-many by construction: 95 benchmark rows match more
than one registry row and 69 registry rows match more than one benchmark row.

## Missing benchmark decisions

All 64 sit in study units the registry already contains, so none is a scope gap.
Dispositions: retrieval miss 16, out-of-scope detail 15, granularity mismatch 14,
true omission 12, cross-discipline mapping 5, benchmark artifact 2, uncertain 0.
Of the 12 true omissions, **10** also satisfy the atomic contract and were
admitted as `QOP-V3G-*` rows in `NEEDS_SOURCE_RESEARCH` — they carry benchmark
provenance but no Canadian source packet of their own yet.

The 16 retrieval misses are a real limitation of study-unit-scoped blocking and
are recorded, not hidden.

## Capacity

No fixed questions-per-opportunity ratio is asserted anywhere. Curriculum decision
count (1,964), variant count (4) and production-eligible count (445) are reported
separately. The historical 6,086 / 1,000-per-discipline allocation targets are not
treated as a registry truth.

## Acceptance gate

All twelve checks pass: historical preservation, reproducible canonical ids,
independently confirmed destructive merges, variants excluded from coverage,
fail-closed unresolved cases, many-to-many adjudicated benchmark mapping,
internally coherent metrics, reported residual duplicate review set,
atomic-contract-satisfying production rows, copyright, full lineage, and
deterministic rebuild.

A non-empty review queue does not fail the gate. The queue holds 1,583 rows:
1,490 ambiguous atomicity, 64 unresolved benchmark gaps, 29 unresolved relations.

## Rebuild

`verify_deterministic_rebuild` recomputes all 26 canonical artifacts from the
frozen inputs plus the frozen adjudication files and reproduces every content
hash. Semantic review outputs are frozen inputs; they are never rerun.

## Pilot manifest

36 production-eligible opportunities selected by stratified round-robin over
(discipline, family), covering all 6 disciplines, 18 opportunity families, 10
response classes, 4 dimensions of care and 4 physician activities. It carries ids
and structural metadata only — **no questions were generated in this milestone**.

Each authored item must flow through: author session → frozen item package →
separate verification session → Stage 1 blind solve → freeze verdict → Stage 2
rationale/claim/source/TN/current-Canadian-guidance audit → verified accept or
reject. Independent Verification V1 is unchanged.
