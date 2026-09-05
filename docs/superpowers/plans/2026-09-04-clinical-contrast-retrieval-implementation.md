# Clinical contrast retrieval — implementation plan

Approved design: `docs/superpowers/specs/2026-09-04-mccqe-clinical-contrast-graph-rag-and-difficulty-design.md`
`DESIGN_COMMIT = 777653a`. `STARTING_COMMIT = 777653a` (HEAD, clean tree, design commit is HEAD itself).

Scope bound for this milestone, restated so it cannot drift:

- `PRODUCTION_QUESTION_GENERATOR_CHANGED = NO`
- `QUESTIONS_GENERATED = 0`
- `LLM_API_CALLS = 0`
- No historical 6,086 allocation artifact is touched.
- No frozen qgen artifact (seed pack, enrichment, anchors, wave plan, scenarios, items,
  semantic-admissibility, G2 execution reports) is modified.
- The validated stem-anchor floor, the ADM-3 second-key ceiling, semantic admissibility, critical-fact
  adjudication, evidence entailment and fail-closed behaviour are preserved unchanged.

---

## Phase 0 — reuse matrix

Measured deterministically from the working tree at `777653a`. Nothing was re-OCRed and no page was read
by a model to produce this table.

| Existing artifact | Verdict | Why |
|---|---|---|
| `derived/toronto-notes-2025/ocr/page_index.json` (1595 pages, per-page sha256, `source_sha256`) | **REUSABLE_AS_IS** | Canonical page spine with hashes already exists. Re-OCR is forbidden and unnecessary. |
| `derived/toronto-notes-2025/ocr/pages/*.json` (1595, `ocr_text` with line/blank-line structure, `headings`, quality flags) | **REUSABLE_AS_IS** | Retains blank-line block structure and running headers, which is what structure-aware chunking needs. Preferred over `clean-ocr`. |
| `derived/toronto-notes-2025/clean-ocr/*.txt` (1595, flattened, no newlines) | **NEEDS_EXTENSION** (used for hashing/verification only) | Newlines are stripped, so paragraph and heading boundaries are unrecoverable. Unsuitable as the chunker's input; kept as a cross-check. |
| `derived/toronto-notes-2025/chapters/*/manifest.json` (32 chapters, pdf+tn page ranges) | **REUSABLE_AS_IS** | Canonical chapter boundaries; becomes the `chapters` table. |
| `research/tn2025/toc_inventory.json` (2019 nodes: 32 chapters / 468 sections / 1519 topics, `parent_id`, tn+pdf page ranges, confidence) | **REUSABLE_AS_IS** | Becomes the `sections` (TN_NODE) table and supplies the section path for every chunk. |
| `research/scope/master_scope_crosswalk.json` (1487 study units, page ranges, MCC evidence, classification) | **REUSABLE_AS_IS** | Becomes `study_units`; supplies `page → study_unit` resolution and the BELONGS_TO edges. |
| `research/qgen/chapter_global_contrast_library.json` (12 typed contrast edges, full provenance) | **REUSABLE_AS_IS**, projected | Already a typed clinical contrast edge set with page provenance. Projected into the graph as `CONFUSED_WITH` + `SUPPORTED_BY`; the JSON stays canonical and byte-identical. |
| `research/qgen/generalization/*seed_pack*.json` (82 curated + targeted/extension seeds) | **REUSABLE_AS_IS**, projected | Source of `CONDITION`/`ACTION` competitor nodes. Frozen; never rewritten. |
| `research/qgen/generalization/*.enrichment.json` (`condition_predicates`, response-class tokens, applicable disciplines/archetypes) | **REUSABLE_AS_IS**, projected | Projects to `DEFEATED_BY` (correctness conditions) and `ANSWERS` (decision/archetype/granularity) edges. |
| `research/qgen/generalization/*.stem_anchors.json` (frozen anchors over 81 retrievable seeds) | **REUSABLE_AS_IS**, projected | Projects to `PLAUSIBILITY_ANCHOR` edges. This is the only source of the floor relation and it is already independently derived and frozen; deriving new anchors is out of scope. |
| `research/qgen/safe_yield/g2_stem_feature_vocabulary.json` (102 features / 6 study units) | **REUSABLE_AS_IS** | Becomes the `FINDING` node vocabulary. Measured: **0 exact cross-study-unit collisions**; features are cleanly partitioned by study unit (see the note below, which changes the benchmark design). |
| `research/qgen/safe_yield/g2_profile_pilot.{opportunities,wave_plan,semantic_admissibility}.json` | **REUSABLE_AS_IS** | The frozen benchmark population: 30 opportunities, 30 realized stem-feature maps, 29 frozen semantic judgements. Read-only. |
| `reports/qgen_g2_stem_anchor_retest_execution.json` | **REUSABLE_AS_IS** | Arm-A reference results and the frozen negative controls (SAF-1 and ADM-3 refusals). Read-only. |
| `scripts/qbank/profile_contrast_retrieval.py` | **REUSABLE_AS_IS — DO NOT MODIFY** | This *is* benchmark arm A. Modifying it would destroy the reference. New retrieval lives in new modules. |
| `scripts/qbank/option_set_admissibility.py` (`expand_response_tokens`, `normalize_option_text`, closed vocabularies) | **REUSABLE_AS_IS** | The response-class closure and option normalization are reused verbatim by every new arm so precision metrics stay comparable. |
| `scripts/qbank/{paths,jsonio,errors,schema}.py` | **REUSABLE_AS_IS** | Root-contained path resolution, atomic deterministic JSON, error base class, schema validation. |
| `scripts/qbank/safe_yield_wave.py`, `question_opportunity.py` | **REUSABLE_AS_IS — NOT TOUCHED** | Production generation path. Out of scope by explicit instruction (Phase 40). |
| SQLite + FTS5 | **REUSABLE_AS_IS** | Verified locally: sqlite 3.51.2, FTS5 present, `unicode61` and `porter` tokenizers available, `bm25()` available. No new dependency. |
| Neo4j / hosted graph DB / vector DB / embedding API | **REJECTED** | Forbidden by the design and by this task. |
| A separate `item_archetypes` / `option_set_archetypes` table | **REJECTED** | Would duplicate the closed vocabularies already owned by `option_set_admissibility.py` and `qgen_profiles.py`. The archetype triple is carried as validated columns on the `ANSWERS` edge instead. A table that only restates an existing enum has no retrieval or provenance purpose. |

### The Phase-0 measurement that shapes the benchmark

The 102 canonical stem features are partitioned across exactly 6 study units with **zero exact
cross-study-unit normalized-string collisions**. Feature ids are study-unit-namespaced
(`SF-C21-…`, `SF-P147-…`) and their normalized text is study-unit-specific clinical prose.

Consequence, and it is structural rather than incidental: a competitor whose plausibility anchors are
drawn from one study unit's vocabulary **can never clear the stem-anchor floor against a stem realized
from another study unit's vocabulary**. Anchor-bearing competitor supply is therefore confined to the
6 study units that have a stem-feature vocabulary — 0.4 % of 1487.

This does not decide the benchmark, and it is deliberately not treated as one. It does mean the
benchmark must be able to tell two very different failures apart, so the metric set below separates:

- `VIABLE_COMPETITOR` — retrieved **and** same-decision/archetype/granularity **and** clears SAF-1
  **and** clears the ADM-3 ceiling; and
- `DISCOVERED_BUT_UNTYPED` — a clinically relevant concept an arm genuinely retrieved that cannot be
  scored against the floor because no typed anchor row exists for it.

An architecture that scores high on the second and zero on the first has demonstrated that the
bottleneck is graph/anchor **population**, not retrieval. That distinction is the point of the exercise
and it is pre-committed here, before any arm runs.

---

## Phase 1 — storage and the deterministic index

**Artifact location.** `derived/tn_index/tn_index.sqlite3`. `derived/` is already gitignored, so the
corpus-bearing database is never a tracked artifact. Tracked instead: the builder, the schema, the
tests, and a small build manifest of counts and hashes carrying no Toronto Notes prose.

**Tables, each with a stated retrieval or provenance purpose.** Tables that only sounded graph-like
were cut (see the rejected row above).

| Table | Purpose |
|---|---|
| `documents` | corpus identity + `source_sha256`; makes the build reproducible and auditable |
| `chapters` | chapter boundaries; chunk → chapter resolution |
| `sections` | TOC nodes (`node_id`, `parent_id`, level, page range); supplies `section_path` and bounds graph provenance to a TN node |
| `chunks` | retrieval unit with deterministic id, page, tn node, ordinal, text hash, char count |
| `chunk_text` | local-only searchable text; never exported, never tracked |
| `chunks_fts` | FTS5 external-content index over normalized text; the BM25 arm |
| `study_units` | 1487 study units with page ranges; `page → study_unit` join |
| `mcc_objectives`, `study_unit_objectives` | `BELONGS_TO`; coverage joins |
| `concepts`, `concept_aliases` | normalized clinical vocabulary + ambiguity state |
| `concept_mentions` | concept → chunk with page provenance; the evidence for a discovery edge |
| `nodes`, `edges`, `edge_provenance` | the typed clinical contrast graph and its per-edge provenance contract |
| `sources`, `source_claims` | authority-role separation; `SUPPORTED_BY` targets |
| `learner_decisions` | the decision-granularity filter the current index does *not* key on |
| `retrieval_cache` | content-addressed cache keyed by (arm, opportunity, stem-feature-set hash) |

**Chunking.** Structure-aware, not fixed-token. Per page: drop the running header line, split on blank
lines into blocks, classify each block (heading / bullet-list / paragraph / figure-noise), attach blocks
to the nearest preceding heading, and pack into chunks that never cross a page or heading boundary and
respect a deterministic maximum size. Chunk id = a truncated sha256 over
(`document_id`, `pdf_page`, `ordinal`, `text_sha256`) — stable under rebuild, and asserted by test.

**Tokenizer.** `unicode61 remove_diacritics 2` with `porter` stemming, chosen deliberately and recorded
in the build manifest: medical prose needs `-itis`/`-osis` morphology folded for recall, and diacritic
folding matters for OCR noise. `porter` is documented as a known trade-off (it over-stems some drug
names) rather than silently adopted.

**Measured and reported:** index build wall time, DB size, chunk count, median / p95 / max chunk size,
pages per chapter.

---

## Phase 2 — normalization, graph, retrieval, benchmark

Concepts are seeded from what already exists — study-unit titles, TOC topic headings, MCC objective
titles, curated competitor concepts, the 102 stem features, competency statements — never invented.
Alias handling is conservative: ambiguity resolves to `RESOLVED` / `MULTI_MATCH` / `UNRESOLVED` and a
`MULTI_MATCH` is never silently collapsed, because merging medically distinct entities is the one
failure this layer must not have.

The graph is projected **deterministically from already-frozen, already-independently-reviewed
artifacts**. No new medical relation is authored in this task: `PLAUSIBILITY_ANCHOR` comes from the
frozen anchor layer, `DEFEATED_BY` from the frozen enrichment predicates, `ANSWERS` from the frozen
enrichment archetype tags, `CONFUSED_WITH` from the 12 validated contrast-library edges and from
deterministic parsing of Toronto Notes differential structure (`TOPIC_DISCOVERY_SOURCE` only).
Every edge carries the §6.3 provenance contract, and a `TOPIC_DISCOVERY_SOURCE` edge may propose a
competitor but never justify one.

Four arms — A current library (unmodified), B BM25, C graph, D hybrid — run over the same 30 frozen G2
opportunities with the same stems, keys, archetypes, floor and ceiling. Every arm's candidates pass
through the *same* downstream filters so precision is comparable. Metrics are frozen in code before any
arm runs; the pass rule is the design's §10 rule, written to be losable.

---

## Task list (TDD; each task is one red-green cycle)

Storage and index
1. `tn_index_schema` — schema DDL + `open_index`; test: tables/indices exist, FTS5 available, rebuild is idempotent.
2. `chunker` — block classification and packing; test: deterministic ids, no chunk crosses a page or heading, size bounds hold.
3. `index_build` — full corpus build; test: 1595 pages indexed, per-page hash matches `page_index.json`, rebuild is byte-stable.
4. `fts_search` — BM25 query API; test: known concepts return their own study unit's pages.

Normalization and graph
5. `concept_normalization` — vocabulary load, alias table, ambiguity states; test: no medically distinct merge, `MULTI_MATCH` fails closed.
6. `concept_mentions` — deterministic detection with page provenance; test: every mention resolves to a chunk and a page.
7. `graph_schema` + `graph_build` — nodes/edges/provenance projection; test: every edge carries the full provenance contract, authority-role rule enforced, no invented context defaults.
8. `graph_neighbourhood` — bounded traversal API; test: depth bound honoured, path provenance returned for every candidate.

Retrieval
9. `bm25_retriever` — deterministic query construction from opportunity data; test: no per-item hand tuning, same query for same opportunity.
10. `graph_retriever` — typed path retrieval; test: every candidate carries the path that produced it.
11. `hybrid_retriever` — union with preserved component scores; test: components are not averaged away.
12. `floor_and_ceiling_reuse` — all arms routed through the *existing* SAF-1 and ADM-3 semantics; test: the 11 known anchorless and 8 known second-key controls are refused in every arm.
13. `context_packet` — bounded packet builder; test: measured size, no raw chunk dumps.

Benchmark and difficulty
14. `benchmark_metrics` — metric definitions frozen in code; test: definitions are pure functions of frozen inputs.
15. `benchmark_run` — four arms over 30 opportunities; report `reports/qgen_clinical_retrieval_benchmark.json`.
16. `difficulty_schema` — `DIFFICULTY_INTENT` + rationale + seven dimensions; test: classification cannot rest on stem length, option count, rarity or obscure terms alone.
17. `psychometric_schema` — nullable empirical fields; test: no fabricated value can be stored, `BETA` is the only entry state.

Audit and close
18. copyright audit over every new tracked artifact; graph quality audit sampled across the six disciplines.
19. docs; full canonical suite once at final production state; commit; `MEMORY.md` `QGEN_ARCHITECTURE_RESUME` update.
