# Competency-component ownership design

## Decision

**MINIMAL_COMPONENT_DESIGN_SUFFICIENT.**  Add one exceptional, ownership-only
abstraction: `COMPETENCY_COMPONENT`.  It is an allocation address beneath one
existing study unit; it neither creates a Toronto Notes unit nor changes a
scope/crosswalk record.  The abstraction is sufficient for all 13 canonical
deferrals.  It is not a new general ownership graph.

This document is design-only.  It preserves the input decisions verbatim:

- `reports/global_ownership_aggregate_audit.json` SHA-256
  `5c61dc7563662bab56c0b63bd08aeb313ca289578abd5aeb409be7be0b9d748a`
- `research/scope/global_ownership_decisions.json` SHA-256
  `4ad97ae2c447dcc40ee3c46e6a82957f429f9eecb7ce965c381e32b8e4a222f4`

No clinical or ownership conclusion is re-adjudicated here.

## Why one feature is enough

The five required capabilities are different outcomes of the same missing
addressability: a whole unit can currently have one ownership outcome, while
some canonical relationships apply only to a named competency inside it.  A
component can be independently allocated, directly cross-linked, or retained
as distinct context.  Therefore competency-level ownership, partial
cross-link, multiple owners, interaction with an older ownership decision, and
mixed relationships need no separate mechanisms.

The existing `PRIMARY_OWNER`, `CROSS_LINK`, and `DISTINCT_CONTEXT` meanings do
not change.  A component relationship uses the same role vocabulary and the
same direct-owner invariant.

## Data model

Keep `research/scope/global_ownership_decisions.json` as immutable historical
whole-unit decision evidence (schema `1.0`).  Introduce a separate ownership
extension artifact, proposed name
`research/scope/competency_component_ownership.json`, with schema version
`1.1` and two arrays:

1. `components` -- exceptional allocation addresses.
2. `relationships` -- only the component-level relationships needed to resolve
   a deferred group.  Group outcome is derived from these rows plus unchanged
   whole-unit decisions; it is never stored as a group-wide role.

### Minimum component record

```json
{
  "component_id": "SU-OP-41::C01",
  "study_unit_id": "SU-OP-41",
  "label": "optic_or_retinal_RAPD_interpretation",
  "component_scope": "The canonical competency subset named by this label.",
  "source_basis": {
    "source_node_ids": ["OP.S14.T05"],
    "crosswalk_competency_keys": ["exam_interpretation"],
    "canonical_decision_ref": "GOC-6e7de6e1004d"
  }
}
```

All shown fields are required.  `source_basis` is deliberately small but must
include the canonical deferred-group ID and at least one existing source-node
ID or crosswalk competency key that bounds the component.  `mcc_objective_ids`
are derived from the existing parent crosswalk, not copied; component creation
cannot fabricate or remap MCC evidence.  Allocation status, rationale, and
ownership role are also not component fields: each is either derived or
belongs to a relationship row, preventing two sources of truth.

### Minimum relationship record

```json
{
  "candidate_group_id": "GOC-6e7de6e1004d",
  "subject_component_id": "SU-OP-41::C02",
  "ownership_role": "CROSS_LINK",
  "primary_owner_ref": {"kind": "COMPONENT", "id": "SU-NS-XX::C01"},
  "rationale": "Canonical deferred adjudication rationale."
}
```

`primary_owner_ref` is required only for `CROSS_LINK`; its target is either a
`STUDY_UNIT` that is a direct primary owner or a `COMPONENT` that is a direct
primary owner.  No target may itself be a cross-link.  `PRIMARY_OWNER` rows
identify a directly allocatable canonical target; `DISTINCT_CONTEXT` rows have
no target and never suppress coverage.  `rationale` references, rather than
replaces, the original deferred rationale.

## Identity and modes

Component IDs use `SU-<CHAPTER>-<NN or NNN>::C<NN>`, for example
`SU-PH-41::C03`, validated by
`^SU-[A-Z]+-\d{2,3}::C\d{2}$`.  This cannot collide with a study-unit ID.

At migration, components are assigned in stable order by the parent unit's
ordered `source_basis.source_node_ids`, then canonical competency label, then
the deferred group ID.  The assigned IDs are persisted; later rebuilds read
them rather than recomputing or renumbering them.  UUIDs and model-generated
IDs are prohibited.

Resolver rule:

```
no components for study unit       -> WHOLE_UNIT_MODE; use existing decisions
one or more components for unit    -> COMPONENT_MODE; use component decisions
```

A parent in `COMPONENT_MODE` has no active whole-unit ownership assignment.
This prevents a whole-unit link from suppressing an independent component.
There is one deliberate non-conflict: a unit can participate in a *candidate
group* whose derived summary is mixed while retaining an existing relationship
from another group.  That is the osteoporosis/Paget case below; it needs no
components and no migration.

## Allocation semantics

Allocation first resolves an allocation address (the whole unit in
`WHOLE_UNIT_MODE`, otherwise every component), then applies the existing
classification/depth/coverage rules to that address.

| Resolved relationship | Allocation result |
| --- | --- |
| whole-unit `CROSS_LINK` | suppress the entire unit's independent allocation |
| component `CROSS_LINK` | suppress only that component; its siblings remain eligible |
| `PRIMARY_OWNER` or no ownership row | eligible under normal coverage rules |
| `DISTINCT_CONTEXT` | no suppression; the address remains independently eligible |
| `REFERENCE_ONLY`, `CONTEXT_ONLY`, or existing zero-question material | remains zero allocation; a component cannot promote it |

Thus `SU-X::C01` may cross-link to owner A while `SU-X::C02` receives normal
independent coverage.  Multiple owners are safe because each cross-link names
one direct primary target, never another cross-link.

## Creation and provenance rules

A component is permitted only when all are true:

1. Its parent is in one of the 13 canonical deferred groups (or is a directly
   necessary counterpart in that same migration).
2. The deferral is classified as an ownership-model limitation, with no
   outstanding semantic review.
3. The canonical deferred rationale identifies the competency boundary and
   ownership relationship that whole-unit roles cannot express.
4. The boundary has a concrete existing source-node, crosswalk-competency, or
   explicit source cross-reference basis.
5. The component is necessary to preserve independent coverage or prevent
   duplicate coverage; ordinary units must not be proactively fragmented.

## Deterministic validator design

The component validator must check all of the following before the ownership
resolver or question allocator reads the extension:

1. extension schema/version, deterministic array ordering, unique component
   and relationship keys;
2. ID pattern, no collision with `study_unit_id`, exactly one existing parent,
   and source-basis references that exist on that parent's canonical records;
3. every component references exactly one canonical deferred group and every
   deferred group has a complete, nonempty representational plan;
4. component scopes within a parent are non-overlapping, unless their source
   basis explicitly records a shared boundary and their relationship outcomes
   are identical;
5. every owner target exists, is a direct `PRIMARY_OWNER`, is not the subject,
   and has no outgoing cross-link; graph traversal must find no self-link,
   cycle, or cross-link chain;
6. a component has at most one effective ownership outcome for the same
   competency scope; conflicting primary targets are invalid;
7. no parent has both active whole-unit ownership and component ownership;
   except that unrelated historical whole-unit decisions may coexist when the
   parent remains in `WHOLE_UNIT_MODE`;
8. `DISTINCT_CONTEXT` never supplies an owner target or suppresses allocation;
   zero-question/status inheritance is preserved for every component;
9. derived group summaries reconcile to their component and pre-existing
   whole-unit rows, allowing `SHARED`, `DISTINCT_CONTEXT`, and `INDEPENDENT`
   facets in one group; and
10. the canonical decision artifact and its 93 resolved groups are bytewise
    unchanged, while the extension accounts for all 13 deferred group IDs.

Existing decision/audit validators continue unchanged for whole-unit data.
The master scope builder, ownership resolver, ownership validator/audit
builder, and later question-allocation reader gain a component-aware branch.
Study-unit and crosswalk schemas remain `1.0`; only the ownership-extension
contract requires version `1.1`.

## Dry-run requirement matrix and representability

`direct target` below means the canonical target already named by the deferred
rationale/source cross-reference.  It is intentionally not a new clinical
selection.  `independent` means normal allocation is preserved, subject to the
existing zero-allocation rule.

| Candidate group | Study-unit component plan | Structural requirement and direct relationship | Coverage / prior relationship | Representable |
| --- | --- | --- | --- | --- |
| GOC-02fc2bef8021 | `SU-PS-55::C01` ASD; `::C02` ADHD | A: each cross-links directly to canonical `SU-P-046` / `SU-P-047` | source is zero coverage; no new allocation | yes |
| GOC-3b1fba49ba4f | `SU-OP-28::C01` Kayser-Fleischer/Wilson; `::C02` young arcus/dyslipidemia | A: direct cross-link for each external canonical owner | existing zero allocation retained | yes |
| GOC-6e7de6e1004d | `SU-OP-41::C01` RAPD; `::C02` compressive CN III; `::C03` pharmacologic pupils | A: three direct targets/independent outcomes as canonically adjudicated | unaffected siblings preserve coverage | yes |
| GOC-d2b95ab5e96b | `SU-PH-41::C01` child protection; `::C02` police; `::C03` coroner/registrar; `::C04` long-term care; `::C05` driving; `::C06` flying | A: six separately addressable reporting competencies | each keeps its canonical eligibility | yes |
| GOC-da256e74edb3 | `SU-R-11::C01` pulmonary CF; `::C02` multisystem complications | A: different direct external owners | independent nonduplicated subset retained | yes |
| GOC-47bcd6aa3fd2 | `SU-E-56::C01` PCOS; `::C02` menstrual disorders; `::C03` menopause | A: direct Gynecology counterpart per component | cross-reference remains zero coverage | yes |
| GOC-4cc6ee4a976b | `SU-D-44::C01` wounds/ulcers; `::C02` pediatric exanthems | A: two direct source-designated owners | cross-reference remains zero coverage | yes |
| GOC-affe28b0a599 | `SU-N-46::C01` NF1; `::C02` NF2 | A: separate Pediatric canonical targets | cross-reference remains zero coverage | yes |
| GOC-bc2393b18440 | `SU-N-20::C01` endocrine paraneoplastic; `::C02` CNS tumours | A: two direct source-designated owners | cross-reference remains zero coverage | yes |
| GOC-35d3276ee022 | `SU-G-20::C01` celiac diagnosis; `::C02` gluten-free management; `SU-P-067::C01` pediatric presentation/FTT | A/C: separately owned shared and age-context competencies | independent pediatric presentation preserved | yes |
| GOC-01b92489a96f | no components | C: derived group summary combines existing `SU-E-48` primary / `SU-FM-46` cross-link with whole-unit `SU-E-51` distinct Paget context | existing osteoporosis pair remains unchanged | yes |
| GOC-298783746993 | `SU-OT-33::C01` shared epistaxis bleeding management; `::C02` facial trauma; `::C03` specialist recognition | B: only `C01` cross-links to direct epistaxis owner; C02/C03 independent | independent OT coverage preserved | yes |
| GOC-ab4868457a6c | `SU-C-30::C01` shared IE recognition/prophylaxis; `::C02` cardiac diagnostic framing; `SU-ID-08::C01` shared IE recognition/prophylaxis; `::C02` infectious diagnostic framing | D: shared components cross-link directly; framing components and whole `SU-P-040` remain independent/distinct | pediatric congenital-risk/prophylaxis coverage preserved | yes |

This dry run requires components in **14 study units** and **36 components**.
The one prior-ownership group needs none.  All 93 resolved groups remain as
they are; **0** resolved groups require a change.

## Migration boundary

Migration will add only the extension artifact and records for the dry-run
components/relationships.  It will not alter study units, MCC mappings,
source scope, original deferred decisions, or question counts.  The original
deferred records remain the canonical decision history; the extension supplies
the previously unavailable representational projection.  Candidate generation
remains unchanged and group-level outcomes become deterministic summaries.

## Design-only acceptance check

- deferred groups analyzed: 13
- deferred groups structurally representable: 13
- ownership decisions changed: 0
- full suite: not run (design-only; no executable schema or code changed)
