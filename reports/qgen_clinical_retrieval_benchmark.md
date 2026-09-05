# Frozen-G2 clinical retrieval benchmark

`BENCHMARK = RUN`. `LLM_API_CALLS = 0`. `QUESTIONS_GENERATED = 0`.
Full results: `reports/qgen_clinical_retrieval_benchmark.json`.
Pre-registration: `research/qgen/safe_yield/retrieval_benchmark_reference.json`, committed at
`20db2a6` before any arm ran.

Population: the same 30 frozen G2 opportunities, with their realized stems, keys, archetypes and
feature maps held constant. The reference set (83 admitted competitors across 29 opportunities) and
the negative controls (67 anchorless, 8 second-key) are read off records frozen before this task.

## Results

| Metric | A current library | B BM25 | C graph | D hybrid |
|---|---|---|---|---|
| Opportunities with ≥3 viable competitors | **10 / 30** | 0 / 30 | **10 / 30** | **10 / 30** |
| Candidate recall (mean) | 0.4935 | 0.0 | 0.4935 | 0.4935 |
| Same-decision precision | 0.9123 | — | 0.9123 | 0.9123 |
| Same-archetype precision | 1.0 | — | 1.0 | 1.0 |
| Granularity precision | 1.0 | — | 1.0 | 1.0 |
| Stem-anchor survival | 0.4253 | — | **1.0** | 0.4253 |
| Second-key refusals | 8 | 0 | 8 | 8 |
| Anchor-floor refusals | 67 | 0 | **0** | 67 |
| Known-bad returned | **0** | **0** | **0** | **0** |
| Discovered but untyped | 0 | 341 | 0 | 341 |
| Source traceability | 1.0 | — | 1.0 | 1.0 |
| Context size, median characters | 1,737 | 961 | 1,770 | 1,770 |
| Latency p50 / p95 (ms) | 5.4 / 6.6 | 9.0 / 42.0 | 5.5 / 6.6 | 8.4 / 11.3 |

`HYBRID_BENCHMARK_PASS = False`. Six of the seven pre-committed checks pass; the one that fails is
the one the rule was built around — hybrid does not raise the number of opportunities reaching three
viable competitors. 10 against 10.

## What the numbers mean

**The apparent recall figure is not a recall figure.** Mean candidate recall of 0.4935 looks like a
retrieval shortfall and is not one. Every frozen reference positive absent from arm A's ranked set was
traced to the filter that removed it: **41 refused by the stem-anchor floor (SAF-1), 2 by response
class (ADM-1), and `NOT_RETRIEVED_AT_ALL = 0`.** Nothing is missed by retrieval in any arm. The gap
is the validated floor refusing competitors that a reviewer had marked ADMITTED *before the floor
existed* — which is the floor working, not retrieval failing.

**BM25 discovers topics, not competitors.** Arm B returns 341 concepts that carry no typed anchor or
condition rows and so cannot be scored against the floor at all. Sampling them shows what they are:
`Growth`, `Failure to Thrive`, `Hematuria` — chapter and topic headings. That is what a lexical index
over a structured textbook should be expected to return, and it is why arm B reaches 0 opportunities.

**The graph is not useless, but its win is not supply.** Arm C reaches the same 10 opportunities with
**zero** anchor-floor refusals against arm A's 67, because traversal starts from the stem's PRESENT
anchors and therefore never presents an anchorless candidate to the floor at all. That is an
efficiency and provenance result. It is not more competitors.

**Arm C independently corroborates the anchor layer.** It reaches arm A's competitor sets by a
different path — inverted `PLAUSIBILITY_ANCHOR` edges rather than an archetype index lookup — and
arrives at the same answer.

## Decision

`RETRIEVAL_ARCHITECTURE_DECISION = RETRIEVAL_NOT_MAIN_PROBLEM`.

Applying the design's own pre-committed rule: D does not beat A, and no arm closes the gap, so the
bottleneck is not retrieval and the graph must not be built out across the corpus.

`BINDING_CONSTRAINT = TYPED_ANCHOR_AND_CONDITION_POPULATION`. The Phase-0 measurement predicted this
and the benchmark confirms it: the 102 canonical stem features partition across exactly 6 study units
with zero cross-unit collisions, so anchor-bearing competitor supply is structurally confined to
0.4 % of the 1,487 study units. Every typed competitor concept in the repository is already in the
curated index, which is why three of four arms return the identical set.

`LOCAL_EMBEDDING_TRIGGER_MET = NO`. The trigger requires a known-good candidate that lexical retrieval
misses. Nothing is missed by any arm, so a denser retriever would hand the same competitors to the
same floor and change nothing. `LOCAL_EMBEDDINGS = NOT_NEEDED_YET`.

## What this does not say

It does not say the graph was a mistake. It says the graph should not be *expanded* on a retrieval
argument, because retrieval is not what is short. The typed layers built here — 153
`PLAUSIBILITY_ANCHOR`, 100 `DEFEATED_BY`, 81 `ANSWERS` edges with full provenance — are the layers
whose *population* is the actual constraint, and they now have a deterministic home, a provenance
contract and a measured baseline.

It also does not measure question quality. No item was generated, no stem or key was rewritten, and
no terminal state moved.
