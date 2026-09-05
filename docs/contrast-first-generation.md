# Contrast-first item construction

How the pilot works, why the generation order changed, and how to run it again.

Design spec:
`docs/superpowers/specs/2026-09-05-contrast-first-difficulty-aware-item-construction-design.md`

Module: `scripts/qbank/contrast_first_pilot.py`. It is an **isolated pilot**. It
imports production code and edits none of it. The production generator is
unchanged.

---

## 1. Why the order changed

The frozen four-arm retrieval benchmark settled that retrieval is not the binding
constraint: `NOT_RETRIEVED_AT_ALL = 0` in every arm. Of the twenty opportunities
that failed, fifteen failed on `STEM_ANCHOR_FLOOR` — the stem was already frozen,
and it stated nothing that would give a candidate a positive reason to consider
the competitor retrieval had returned. The refusal is correct, and no better
retriever can undo a correct refusal.

The old order authors the stem against the key alone and then hopes the stem
happens to contain the findings that make legitimate competitors live.
`STEM_ANCHOR_SURVIVAL_mean = 0.4253` measures that hope.

```
old:  learner decision -> stem + key -> retrieve competitors -> filter against frozen stem
new:  learner decision -> key -> contrast set -> contrast matrix -> stem blueprint
                       -> author stem -> freeze -> blind solve
                       -> the SAME post-stem gates -> options -> independent review
```

Only the **order** changes. Every gate that decides safety runs afterwards,
unchanged.

## 2. Stages

| stage | function | what it produces |
|---|---|---|
| pre-stem admission | `admit_pre_stem` | P1–P6 verdict per candidate |
| contrast set | `validate_contrast_set` | 3–6 admitted competitors + the key |
| contrast matrix | `build_contrast_matrix`, `validate_contrast_matrix` | the eight blocks per competitor |
| blueprint | `solve_stem_blueprint` | the stem-feature set, forbidden features, competitor status |
| coherence | `evaluate_clinical_coherence` | CO-1..CO-6 |
| difficulty | `difficulty_evidence_from_blueprint`, `structural_difficulty_review` | measured evidence, not asserted |
| freeze | `research/qgen/contrast_first_pilot_stems.json` | the stem, never edited after |
| blind solve | fresh contexts, stem + lead-in only | key supported or not |
| post-stem | `revalidate_against_frozen_stem` | the **production** ADM_1 / ADM_3 / SAF_1 |
| options | `validate_option_realization` | homogeneous options traceable to the matrix |
| review | fresh contexts | the nine accepted-item safety counts |

### The pre-stem admission predicate

P1–P6 are the **stem-independent** conditions the current pipeline already
applies: same learner-decision dimension (read off the frozen independent seed
review), response-class closure under the profile's declared token implications,
item and option-set archetype, granularity parity, a passed independent seed
review, and evidence on both the plausibility and the discrimination side. Moving
them earlier admits nothing new; it only stops work being spent on a candidate
that was never eligible.

The two **stem-dependent** gates cannot be evaluated before a stem exists and are
not moved.

### The blueprint solver

Given a contrast matrix it solves for a stem-feature assignment satisfying three
constraints together:

- `KEY_FULLY_SUPPORTED` — every key correctness condition is satisfied.
- `EVERY_COMPETITOR_LIVE` — every competitor has at least one plausibility anchor
  `PRESENT`. This is `SAF_1` as a constraint instead of a filter.
- `NO_SECOND_KEY` — every competitor has at least one correctness condition
  unsatisfied. This is `ADM_3` as a constraint instead of a filter.

The floor pass visits competitors in seed order and picks, for each still-
anchorless one, the anchor that also serves the most other anchorless competitors,
skipping any anchor that would complete some competitor's correctness signature or
violate a declared contradiction pair. A harder difficulty contract then adds
further anchors under the same rules until the level's anchor-density target is
met or nothing more can be added. Ties break on feature id, so the solve is
deterministic.

If the three constraints cannot hold together the blueprint fails closed and **no
stem is written**. That is the point: the failure moves earlier and costs less.

The blueprint also names the **forbidden features** — those whose statement would
complete a competitor's correctness signature — and hands them to the author as a
prohibition rather than leaving them to be discovered by a gate afterwards.

### Difficulty intent

`EASY`, `MEDIUM`, `HARD`, authored and never empirical. The checks are reused
unmodified from `scripts/qbank/question_difficulty.py`. Difficulty is targeted by
the blueprint — how many correctness conditions the key rests on, and how many
anchors each competitor gets — and it is capped above by `REQUIRED_FEATURE_CAP`,
so a level can never be reached by making the stem longer.

`competitor_similarity` is measured as the mean of
`satisfied_conditions / total_conditions` over admitted competitors: how close
each competitor comes to being correct without being correct.

## 3. When `NO_SAFE_ITEM` occurs

| reason | when |
|---|---|
| `FAIL_CLOSED_CONTRAST_SET_SIZE` | fewer than 3, or more than 6, competitors survive P1–P6 or the author's selection |
| `FAIL_CLOSED_COMPETITOR_NOT_CONSIDERABLE` | a competitor has no answer to "why would a minimally competent candidate seriously consider this?" |
| `FAIL_CLOSED_BLUEPRINT_UNSATISFIABLE` | floor, ceiling and key support cannot hold together |
| `FAIL_CLOSED_CLINICAL_COHERENCE` | CO-1..CO-6 violated |
| `FAIL_CLOSED_DIFFICULTY_TARGET_NOT_MET` | the level's checks cannot be met from admissible competitors |
| `FAIL_CLOSED_BLIND_SOLVE_DISAGREEMENT` | the blind solver converges on another answer |
| `FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS` | fewer than 3 survive the unchanged post-stem gates |

None of these is ever repaired by weakening a gate, by editing a frozen stem, or
by substituting an easier opportunity.

### A recurring structural finding

Several curated competitors carry a single plausibility anchor that is also their
single correctness condition. Such a competitor can be live **only** by being a
second key, so it is unusable in any contrast set. This is a property of the
frozen library, not a retrieval failure, and it is the most common reason a
contrast set falls below three in this pilot.

## 4. How the graph is used

Upstream only, and for two jobs the archetype-tagged library index cannot do
without a stem:

1. **Contrast discovery from the key.** Traversal seeded at the *target node* the
   key answers, over inverted `ANSWERS` and then `CONFUSED_WITH`. Benchmark arm C
   seeds at the realized stem's `PRESENT` features and is unusable here by
   construction — there is no stem yet.
2. **Competitor → stem-feature support.** `PLAUSIBILITY_ANCHOR` edges give, for
   each candidate, the features that would make it live. That is exactly the input
   the blueprint solver needs.

Whether the graph contributed a candidate the library alone would not have
surfaced is measured, not assumed. Toronto Notes edges remain
`TOPIC_DISCOVERY_SOURCE` and may never justify a clinical claim. No embeddings.

## 5. Running it

Everything is deterministic and reads only frozen artifacts.

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0,'scripts')
from pathlib import Path
from qbank import contrast_first_pilot as cf
pre = cf.build_pilot_contrast_sets(Path('.'))
post = cf.run_post_stem_revalidation(Path('.'), pre)
print(len([r for r in pre['results'] if r['stage']=='READY_FOR_STEM']), 'blueprints')
print(sum(1 for r in post['results'] if r['post_stem_3_viable']), 'post-stem viable')
"
```

Focused tests:

```bash
.venv/bin/python -m pytest tests/test_contrast_first_pilot.py -q
```

Inputs, all tracked and frozen:

- `research/qgen/contrast_first_pilot_opportunities.json` — the 18-opportunity
  sample, its selection rule S1 and its frozen metrics.
- `research/qgen/contrast_first_pilot_authoring.json` — key decisions, key
  correctness conditions, contrast-set selection with a reason for every
  exclusion, declared contradiction pairs, context features.
- `research/qgen/contrast_first_pilot_stems.json` — the frozen stems and their
  feature maps.
- `research/qgen/contrast_first_pilot_items.json` — realized options and
  rationales.
- `research/qgen/contrast_first_pilot_blind_solver.json` — blind-solve records.

The blind solve and the independent review are the two stages that need fresh
contexts and are therefore not reproducible by running Python. Their outputs are
recorded verbatim in substance in the artifacts above and in
`reports/qgen_contrast_first_independent_review.json`.

## 6. What this pilot does not establish

Eighteen opportunities over six anchor study units, all inside the frozen thirty
whose stem-first baseline is archived. It is evidence about generation order in
six well-characterised units. It is not evidence about the 1,487-unit curriculum,
and the production generator has not been changed.
