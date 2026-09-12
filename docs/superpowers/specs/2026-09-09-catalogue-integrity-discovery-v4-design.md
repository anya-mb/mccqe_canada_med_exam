# Catalogue Integrity and Discovery V4 Design

## Scope

This milestone repairs the extraction-artifact class that invalidated the frozen
Discovery-V3 Transfer-12 experiment, treats that cohort only as development
diagnostic evidence, diagnoses all 52 prior `WRONG_DECISION` results, and adds a
small reusable decision-compatibility layer. It does not run or select a new
clean transfer cohort unless the final readiness gate passes, and it never
rewrites the frozen V1/V3/cache/Transfer artifacts.

## Immutable baseline

The V1 catalogue, Discovery-V3 code and outputs, Cache V1/V2/V3, Build-12 V3
outputs, Transfer-12 roster and V3 outputs, semantic reviews, and copyright
failure report remain byte-identical. A new diagnostic-classification artifact
binds their hashes and permanently marks the old cohort as
`DISCOVERY_V3_DIAGNOSTIC_TRANSFER_12`.

## Catalogue integrity contract

`contrast_supply_v4.py` owns the V2 catalogue contract. It classifies every V1
row into exactly one required taxonomy value and emits explicit reason codes.
The classifier uses structural signals: caption/furniture prefixes, incomplete
clauses, repeated extraction filler, malformed OCR token runs, embedded page or
chapter codes, abnormal punctuation, and prose-like syntax. Independently
reviewed candidate labels retain a narrow provenance-aware allowance for
imperative option text. `UNCERTAIN` is excluded from V2.

V2 is rebuilt from the canonical SQLite concept graph plus the existing
reviewed identities, not edited from V1. It records the V1 parent content hash,
audit counts, removed IDs and reasons, and its own content hash. Copyright must
pass before V4 replay proceeds.

## Diagnostic reconstruction

A deterministic join binds each of the 52 frozen `WRONG_DECISION` reviews to
its opportunity, learner decision, candidate, response class, granularity,
source metadata, V3 ranking signals, and prior verdict. Each row receives one
earliest semantic mismatch from the required taxonomy. The classification is
based first on frozen review/context evidence; any new semantic review is
limited to representative unresolved groups and counted explicitly.

## Decision signature

The signature has three controlled dimensions:

- `decision_intent`: the act the learner is choosing, such as identifying a
  diagnosis, classifying state/complication, selecting a diagnostic action,
  selecting treatment, escalating/disposition, or making an ethical/legal
  assessment.
- `target_domain`: a reusable clinical or institutional domain, such as
  cardiopulmonary, gastrointestinal, reproductive, psychiatric, hematologic,
  endocrine/metabolic, public-health programme, clinical governance, or law.
- `clinical_stage`: initial recognition, diagnostic workup, acute management,
  longitudinal management, escalation, prevention, or governance/legal review.

Compatibility requires exact intent and target-domain agreement. Clinical stage
requires exact agreement or a small reviewed adjacency explicitly justified by
a known-good contrast relation; there is no unrestricted wildcard. This keeps
HbA1c and TTE-type inferior-but-relevant contrasts eligible while rejecting a
same-response-class candidate from an unrelated decision lane. Values must be
reused across multiple rows; the economy report exposes single-use values and
cross-unit/cross-discipline reuse.

## Discovery V4

Discovery V4 retains V3's global canonical search, response-class and
granularity gates, deterministic ranking, locality bonuses, provenance, and
fixed ten-candidate budget. It adds signature compatibility before ranking and
records each signature rejection. It uses only authored/reviewed signatures;
missing signatures fail closed. It does not generate candidate names, inspect
chapter prose, use embeddings, or adapt after diagnostic replay.

## Replay and gates

Build-12 and the contaminated diagnostic Transfer-12 are replayed once from
fixed inputs. Exact candidate-plus-context hashes reuse frozen clinical verdicts;
only genuinely new survivors may receive bounded review. The report compares V3
and V4 counts, wrong-decision rate, reviews avoided, plausible yield, known-good
controls, lifecycle and historical safety, and copyright results.

Readiness is `YES` only when every user-specified criterion passes. A precision
improvement with zero clinically plausible Transfer candidates is insufficient.
If readiness is `NO`, no new cohort is selected and the next step identifies the
remaining architectural bottleneck.

## Verification

Every production behavior is developed red-green. Focused tests run throughout;
the canonical full suite runs once after the last shared-code change. Frozen
hashes, `git diff --check`, `MEMORY.md`, copyright, and the known unrelated
coordinator failure are reconciled in the final report. No commit is created.
