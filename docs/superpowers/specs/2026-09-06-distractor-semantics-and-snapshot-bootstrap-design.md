# Distractor semantics and snapshot bootstrap

Status: implemented. Starting commit `2e90375`.

The cross-discipline medium pilot ended on one number, `MEDIUM_GENERATED = 0`,
and two claims about why. This design tests both against the same six frozen
opportunities, moving one variable at a time, and repairs one of them.

## The two claims

1. **Snapshot bootstrap.** Four of six opportunities failed with
   `NEW_EXTENSION_NOT_IN_PINNED_SNAPSHOT`: the wave could cite the anchor
   relations their competitors needed, and the pinned-snapshot rule correctly
   withheld every one of them from the batch that found them. The claim is that
   building the next snapshot *before* generation, from the already-reviewed
   approved delta, converts some of those failures.
2. **Never-correct distractors.** `V2_CANNOT_CARRY_A_NEVER_CORRECT_DISTRACTOR`,
   at 33.3% of opportunities. The claim is that this is a real architectural
   defect rather than a data problem.

## Arms

| arm | snapshot | acquisition | what moved |
| --- | --- | --- | --- |
| A | `FEATURE_ANCHOR_SNAPSHOT_V2` | frozen wave | nothing; reproduces the committed pilot |
| B | `FEATURE_ANCHOR_SNAPSHOT_V3` | frozen wave | the pinned snapshot |
| C | `FEATURE_ANCHOR_SNAPSHOT_V3` | arm-C overlay | how six already-discovered candidates are typed |

Opportunities, keys, evidence, difficulty intents, contrast relations and option
texts are the committed frozen artifacts in all three arms and are read from the
same files. One generation attempt per opportunity, no retries, no replacements.

## `FEATURE_ANCHOR_SNAPSHOT_V3`

V2 plus the **five** anchor relations the medium pilot's own extension review
independently approved, and none of the five it left `UNCERTAIN`. 102 features,
162 anchor relations. `UNCERTAIN` fails closed exactly as `REJECTED` does; the
five exclusions are recorded in `research/qgen/feature_anchor_extensions_v3.json`
with why each stayed uncertain, whether a reviewer inconsistency or evidence bug
was found (none was), and what would warrant revisiting it.

Three of the five uncertain rows are the surgical `SF-GS76-MIGRATORY-RLQ-PAIN`
anchors, which fail design rule S-4 limb B on a strict reading — the cited claims
name appendicitis, the disease, and not the migratory pain, the feature — and
whose downstream signature is the post-stem gate firing CS2-7
`SET_LIVES_ON_ONE_FEATURE` on exactly the set they built. The other two would
grow the frozen 102-feature stem-feature vocabulary, which `validate_extension`
refuses on its own account.

## The distractor semantic model

### What V2 required, and where the requirement came from

V2 required every competitor to carry a satisfiable correctness tree. This is not
a policy that could be waived, it is structural: `validate_predicate` refuses a
branch operator with no conditions — "an empty branch has no truth value" — so
"no state of the world makes this correct" was **unrepresentable**.
`classify_competitor` read the tree unconditionally, `validate_contrast_relation`
required one on both sides of every pair, and CS2-6 and CS2-8 are defined over
the correctness signature.

The requirement is **not necessary for one-best-answer safety**. Safety needs the
key correct and every competitor not correct under the realized stem; a
competitor with no state in which it is right satisfies the second condition
under every stem, unconditionally. It is the safest possible option against a
second key, and the strict model refused it for the property that makes it safer.

The frozen record already contained the counterexample. `G2-MED-04` is an
accepted item, scored zero on all eleven dimensions, **two of whose three
competitors carry zero condition predicates**. The G2 root-cause diagnosis
recorded that, drew the distinction that matters — never *optimal* against never
*appropriate* — observed that "the library does not distinguish the two", and
deliberately proposed no rule. This is that rule.

The requirement was inherited from the contrast architecture, where the
correctness condition was made the single machine-readable link between a
competitor and a stem. Making the link universal made it compulsory.

### The second class

`PLAUSIBLE_BUT_NEVER_BEST`, declared per member. Absence of a declaration means
`COUNTERFACTUAL_CORRECT`, so nothing historical moves and no verdict serializes a
new field.

A never-best competitor carries **no** correctness tree. That is the whole of its
semantics and also its structural guarantee: its correctness is `NOT_SATISFIED`
under every stem, its `second_key_risk` is zero by construction, and the blueprint
solver settles it by cited evidence rather than by spending denial budget.

It is held to a **stricter** contract than a counterfactual-correct competitor,
not a looser one — seven limbs, every one a positive cited statement:

| limb | what it requires |
| --- | --- |
| `POSITIVE_PLAUSIBILITY_SUPPORT` | at least one anchor the member carries and the stem states, with evidence |
| `EXPLICIT_INFERIORITY_REASON` | a basis from the closed set, with evidence and a stated reason |
| `COMMON_CLINICAL_CONFUSION_OR_ERROR` | the named error that makes it a recognisable temptation |
| `SAME_DECISION_CLASS` | the demanded response class is among the member's own tokens |
| `NO_SECOND_KEY` | structural: no correctness tree exists |
| `NO_CATEGORY_MISMATCH` | no satisfied categorical exclusion |
| `NO_GRANULARITY_MISMATCH` | the member's granularity is the set's |

The inferiority bases are `EVIDENCE_STATES_NO_BENEFIT`, `EVIDENCE_STATES_HARM`,
`EVIDENCE_PREFERS_ANOTHER_ACTION` and
`ADDRESSES_A_DIFFERENT_PROBLEM_THAN_THE_ONE_ASKED`. There is deliberately **no
basis meaning "the stem does not say so"**, so silence cannot supply inferiority
— the shape cannot be encoded, and therefore cannot be argued. A structural limb
that fails raises; a stem-dependent one yields `INSUFFICIENT_SUPPORT`; a
set-dependent one is left to the unmodified coherence contract.

Being wrong is not a qualification. Of nine diagnosed cases, the contract refused
`SEED-PED-T03-HYPERTONIC` for having no plausibility anchor the frozen vocabulary
can state, and CS2-3 — not the case file — threw out `SEED-OB-T02-CRP` and
`SEED-PED-T03-SALBUTAMOL` on response class.

`OPTION_2` was chosen over a general distractor scoring model because no measured
failure needs a graded score, and a score would replace a fail-closed contract
with a threshold.

## Two-stage lifecycle

```
STAGE 1  freeze opportunities -> check contrast readiness -> bounded supply
         -> collect extensions -> independent review -> build SNAPSHOT_N
STAGE 2  pin SNAPSHOT_N -> freeze contrast sets -> generate and review
         -> collect proposals for SNAPSHOT_N+1 only
```

No snapshot mutation during Stage 2.

### Why preflight is not outcome-adaptive contamination

Adaptive contamination is choosing what the vocabulary may say **after** seeing
which questions failed. Preflight runs before any question exists, so what it
conditions on is the decision the item is about — the opportunity, the learner
decision, the key concept, the required contrast neighbourhood — and not the
item. It may not inspect a generation outcome, a review verdict, a stem, an
option set or a blind solve, because none of those exists yet.

Two consequences are checkable rather than argued: the extension review's inputs
are the opportunity freeze and the frozen evidence packets, and the snapshot it
produces is content-addressed and frozen before the batch's first item is
written, so no later item can move it.

Arm B is deliberately **not** an instance of this lifecycle. Its five extensions
were proposed inside a batch and reviewed with that batch's downstream evidence
available, which is how three of the wave's own approvals were overturned. That
is why arm B is reported as a controlled replay and the lifecycle verdict is
`PROMISING` rather than `VALIDATED`.

## Result

Contrast-ready 1/6 → 2/6 → 3/6 across arms A, B and C. Generated 0 in all three.
`SNAPSHOT_BOOTSTRAP_VALIDATED` on all four precommitted limbs.

The binding constraint moved twice and now sits somewhere new: both opportunities
that arms B and C carried downstream stop at
`FAIL_CLOSED_COMPETITOR_CANNOT_BE_SETTLED` with the difficulty contract's denial
budget spent — `MAXIMUM_ABSENT_REQUIRED_FEATURES` is 1 at MEDIUM and **0** at
HARD. That is 2 of 6, above the 20% threshold, and per Part Q it is measured and
left alone.

## Commands

```bash
.venv/bin/python -m scripts.qbank build-feature-anchor-snapshots
```

```bash
.venv/bin/python -m scripts.qbank run-snapshot-bootstrap
```

## Artifacts

| artifact | what it holds |
| --- | --- |
| `research/qgen/feature_anchor_extensions_v3.json` | the five approved and five excluded proposals |
| `research/qgen/pilot/medium-pilot-6-armc-acquisition.json` | the frozen wave with six candidates retyped |
| `reports/qgen_medium6_failure_root_cause.json` | the per-opportunity matrix and its counterfactual |
| `reports/qgen_snapshot_v3_visibility_replay.json` | V2 against V3, and the precommitted criteria |
| `reports/qgen_never_correct_distractor_diagnosis.json` | the nine cases, the necessity argument, the options |
| `reports/qgen_snapshot_bootstrap_three_arm.json` | the three arms and the difficulty finding |
| `reports/qgen_fresh_validation_universe_feasibility.json` | why no fresh pilot could be built |
| `reports/qgen_snapshot_bootstrap_milestone.json` | the decision and what is not claimed |

## Not done

No item was generated in any arm, so no independent review ran and no
accepted-item safety counter was exercised. No fresh validation universe was
built — the canonical universe declares 32 learner decisions across six study
units and 29 are already opportunities, so at most three remain against a floor
of 24. No difficulty parameter was changed. No production scale-out spec was
written, because three of its four preconditions fail. No frozen seed row, frozen
snapshot or historical artifact was edited.
