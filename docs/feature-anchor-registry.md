# The feature and anchor-relation registry

One versioned source of truth for clinical feature identity and for
plausibility-anchor relations, consumed by Clinical Contrast Model V2, `SAF_1`,
`retrieve_profile_aware_contrasts` and the on-demand supply layer.

Design:
`docs/superpowers/specs/2026-09-06-versioned-clinical-feature-anchor-registry-design.md`

## Why it exists

The supply wave approved four evidence-cited plausibility anchors, and `SAF_1`
could not see any of them, because it reads the frozen `*.stem_anchors.json`
packs that supply rule S-2 forbids supply to edit. `G2-PED-01` was scored zero on
all eleven independent-review dimensions and refused by the anchor contract
alone.

## The two tables

A **feature** is something the vocabulary can say. An **anchor relation** is a
claim that this feature, PRESENT, for this learner decision, gives a candidate a
reason to consider that competitor. Registration is not entitlement:
`SF-GS76-IMAGING-AVAILABLE-NOW` is a registered feature and anchors nothing
except where a relation says so.

## Commands

```bash
.venv/bin/python -m scripts.qbank build-feature-anchor-reconciliation
```

```bash
.venv/bin/python -m scripts.qbank build-feature-anchor-snapshots
```

```bash
.venv/bin/python -m scripts.qbank run-feature-anchor-gate-replay
```

```bash
.venv/bin/python -m scripts.qbank run-feature-anchor-registry-milestone
```

```bash
.venv/bin/python -m scripts.qbank run-snapshot-bootstrap
```

## Snapshots

| snapshot | features | anchor relations | content |
| --- | --- | --- | --- |
| `FEATURE_ANCHOR_SNAPSHOT_V1` | 102 | 153 | the frozen vocabulary and the three frozen anchor packs, imported unchanged |
| `FEATURE_ANCHOR_SNAPSHOT_V2` | 102 | 157 | V1 plus the four independently approved frozen-five anchor relations |
| `FEATURE_ANCHOR_SNAPSHOT_V3` | 102 | 162 | V2 plus the five independently approved medium-pilot anchor relations |

The store is **append-only**. A snapshot that has run a batch is history: a later
cycle adds a new id and never rewrites an earlier one, and `build_snapshot_store`
regenerates every earlier entry byte for byte. Each snapshot is built from the
baseline plus the whole accumulated approved delta rather than by editing its
parent, so `V3.extension_diff` reports both `ANCHOR_RELATIONS_ADDED` (9, against
the baseline) and `ANCHOR_RELATIONS_ADDED_SINCE_PARENT` (5), and names the five
`UNCERTAIN` proposals it excluded.

`registry_hash` is SHA-256 over the sorted feature and relation rows and nothing
else, so a rebuild reproduces it. There is no `latest`, and `load_snapshot`
refuses one.

## Consuming a snapshot

Three index builders take an optional pin. **Unpinned, each is bit-for-bit what
it was** and reads the frozen packs, which is what keeps retrieval benchmark arm
A and every historical replay unchanged.

```python
load_curated_candidates(
    root,
    feature_anchor_snapshot=load_snapshot(root, EXTENDED_SNAPSHOT_ID),
    feature_anchor_scope="G2-PED-01",
)
```

`feature_anchor_scope` is not optional in effect: an extension relation applies
only in the decision contexts its review named, and with no scope it applies
nowhere. That guard exists because the strict historical regression caught the
alternative — `SEED-PSY-T03-COMBINED`'s anchor, approved for `G2-PSY-03`, also
made it admissible in `G2-PSY-04`, a different learner decision no reviewer had
considered. Retrieval indexes on discipline, item archetype and option-set
archetype and not on the decision, so an unscoped approved anchor becomes a
universal one.

`SAF_1`'s rule is untouched by either path. What the pin changes is where its
anchors come from.

## Adding an extension

```
propose -> evidence validation -> independent review -> approved set
  -> deterministic new snapshot -> replay
```

`UNCERTAIN` fails closed exactly as `REJECTED` does. An approved extension must
be `ANCHOR_RELATION_ONLY`, carry evidence, name its reviewed scope, and satisfy
every minimality criterion; **question yield is not evidence**. Growing the
frozen 102-feature vocabulary is refused here and needs its own authorization.

## Production lifecycle

Run *N* pins `SNAPSHOT_N` for every opportunity in the batch and records its id
and hash. Extensions proposed during the batch are collected, reviewed and built
into `SNAPSHOT_N+1` for the next batch — never made visible to a later question
in the same batch, which is what prevents adaptive contamination.
