# Generalized QGEN study-unit onboarding

## Authority and starting state

The user authorizes new versioned evidence mappings, clinical vocabulary, anchors,
profiles, snapshots, source packets and fresh opportunities, followed by one gated
pilot. Starting HEAD is `1262883`; its working tree was clean. Historical artifacts,
upstream allocation, clinical contrast V2 semantics and difficulty budgets remain
immutable. No external LLM API, embeddings, broad graph, or production generation.

## Alternatives and choice

Patching each historical profile and vocabulary would destroy replay provenance.
An entirely separate generator would duplicate safety logic. Use an additive
onboarding adapter: new evidence and profile contracts, an append-only child of the
existing feature/anchor registry, and explicit inputs to existing contrast gates.
Keep independent semantic judgments as source artifacts; Python performs all joins,
normalization candidates, validation, hashing, counting and report construction.

## Evidence contract

Packet technical status and address readiness are independent. Build one record
for every canonical allocation address, including component addresses. Preserve
study-unit identity, MCC IDs, generation policy, clinical target, original planned
packets, relevant claim IDs and provenance. States are NOT_ASSESSED,
ALIGNED_COMPLETE, ALIGNED_PARTIAL, MISALIGNED, EVIDENCE_MISSING, OUT_OF_SCOPE.
Whole-address completeness is judged against all declared competencies. One
supported decision never promotes an entire address.

An opportunity uses a separately reviewed decision support row: address, decision
ID and statement, target, population, jurisdiction, clinical limitations, required
claim IDs, packet IDs, rationale and review. Only ALIGNED_COMPLETE decision support
with APPROVED independent review grants EVIDENCE_READY. Claims must exist in the
named packet version; cited documents, address and MCC scope must resolve. Technical
READY, a shared TN node, shared MCC objective, prose similarity or author approval
alone cannot grant eligibility. Review records bind a content hash of what was
reviewed and distinguish author from reviewer. Unknowns fail closed.

Freeze the independent re-audit of the known 45 before any repairs. Report old/new
verdicts, cause and exact count changes. Classify wrong-topic packet, broad reuse,
insufficient coverage, population, decision and guidance errors separately. Audit
findings may lower historical ALIGNED to partial without editing the old report.
New mappings may reuse correct existing claims with explicit provenance. Research
only missing claims needed for the prospective pilot, prioritizing authoritative
Canadian guidance. Do not change historical packet populations or the frozen plan.

## Compositional profile V2

Create PROFILE_SCHEMA_V2 / QGEN_PROFILE_SNAPSHOT_V2 in a new artifact. Composition:
common safety core + discipline overlay + decision contract + option-set archetype.
The closed decision catalog covers diagnosis, investigation, initial management,
emergency stabilization, screening/prevention, medication, interpretation,
ethical/legal action, communication and professional/organizational action.
Each decision has explicit permissible granularity and response-class/archetype
pairs. Unknown classes and unsupported pairings are errors, not exceptions.

Common core keeps one best answer, positive anchoring, evidence scope, four-state
semantics, pairwise coherence, option parity and independent final review.
Overlays encode clinical context conditions: child age for PED; gestational context
only when pregnancy/postpartum is relevant for OBGYN; operative context when
operative decisions require it; capacity/risk context where relevant in PSY;
jurisdiction for legal duties across every discipline. Palliative legal action
therefore uses the same legal contract as PHELO. Gynecology does not acquire an
irrelevant pregnancy requirement. Unit existence alone is never eligibility:
resolution requires canonical MCC membership and reviewed evidence for that exact
decision. Avoid per-unit exception tables.

Historical callers retain their original profiles and serialization. New callers
must name a profile snapshot and hash. Test historical accepted controls and invalid
classes alongside both palliative units, all three gynecology units and new
PED/SURG/PSY cases. Structural expressibility and evidence readiness are separate
reported results; neither proves medical validity by itself.

## Vocabulary onboarding and snapshots

A manifest identifies study unit, address, learner decisions, evidence refs,
existing canonical features, new proposals and anchor proposals. Normalize using
the existing text normalization protections and typed identity. Classify as
EXISTING_CANONICAL, NORMALIZED_EXISTING, NEW_CANONICAL_FEATURE,
RELATED_BUT_DISTINCT, AMBIGUOUS or REJECTED. Similarity offers candidates only;
symptom/diagnosis, finding/syndrome, severity/disease, test/result, treatment/
indication and risk/presentation distinctions cannot be merged automatically.

Independent review covers medical correctness, identity, allowed states, role,
decision relevance, target, evidence, second keys and categorical exclusions.
Only APPROVED rows bound to the proposal hash enter a snapshot. UNCERTAIN and
REJECTED remain recorded and excluded; missing evidence or ambiguous identity is
refused. Reuse the existing role/state ontology and registry hash/anchor identity
functions. V4 is a separate versioned artifact, parent V3, retaining every parent
row byte-equivalently. Duplicate IDs, identity changes, missing refs and unscoped
anchor relations are rejected. New anchor relations remain scoped to reviewed
learner decisions; no universal anchor. The snapshot is explicitly loaded and
verified, never selected by a `latest` alias.

Two snapshot stages: an onboarding eligibility snapshot before the opportunity
freeze, then at most one pre-generation contrast acquisition/review wave may add
approved relations to a child pilot snapshot. Pin feature and profile IDs and
content hashes for the entire pilot. Any proposal after generation starts waits
for a subsequent batch and is invisible to this batch.

## Fresh universe and pilot

Re-evaluate all existing 26 and preserve their IDs/provenance and exact transitions.
Prioritize new CORE then IMPORTANT PED/SURG/PSY units. Target 24–36 eligible fresh
opportunities across all six disciplines. Exact equality is unnecessary. Review
educational distinctness against all prior pilots: a renamed decision or the same
key relationship and contrast structure is not fresh. Topic overlap is permitted.
Assign difficulty only after understanding the decision and contrast neighborhood;
intent is never empirical psychometrics.

The fresh-universe gate checks every row's canonical identity, independent
address/decision evidence, compositional profile, vocabulary eligibility, explicit
snapshot pins and independent freshness review. Require at least 24 and all six
disciplines. Failure stops the pilot and records actual remaining bottlenecks;
no attempt or NO_SAFE_ITEM is counted for an unfrozen opportunity.

Freeze opportunities before contrast preflight, then one bounded acquisition wave,
independent feature/anchor review, child snapshot freeze, final contrast sets.
Use existing COUNTERFACTUAL_CORRECT and PLAUSIBLE_BUT_NEVER_BEST contracts unchanged.
One attempt per opportunity: contrast → blueprint → stem freeze → blind solve →
post-stem gates → options/rationale → independent review. No substitutions or
retry for yield. Count earliest failure only. An accepted item must score zero on
all eleven user-specified safety dimensions. Review absent because no item exists
is NO_ACCEPTED_ITEMS, never PASS.

## Measurement and decision

Reports derive counts from artifacts, including all address transitions, original
26 transitions, six-discipline and difficulty distributions, feature/anchor reuse,
profile exceptions, proposal outcomes, context characters by stage and earliest
failure taxonomy. A stage not run is null/NOT_RUN, not measured zero. Ratios with
zero denominators are null. Distinguish audit address counts from pilot counts.
Report difficulty denial-budget confirmation only on the user's fresh thresholds:
20 percent, three disciplines, or multiple otherwise-safe CORE opportunities.
No difficulty changes during this milestone's pilot.

READY requires eligible fresh N >=24, all disciplines, at least one accepted item
with perfect safety, functioning evidence gates, no systematic defect >=20%,
non-overfit profiles and manageable vocabulary growth. Otherwise choose the exact
blocked/promising/unsafe reason supported by the earliest measured failure. Write
production scaleout design only if READY; never implement broad generation.

## Verification and checkpoints

TDD for contract boundaries and adversarial cross-address/claim/profile/snapshot
mismatches; deterministic rebuild tests; historical replay and hash invariance.
Focused tests during work, one full canonical suite at final executable state,
rerun only if executable inputs change afterward. Run the canonical copyright
scanner over new artifacts and git diff --check. Durable commits for design,
contracts, frozen audit, reviewed data/snapshots, freeze, pilot and analysis as
applicable. Update only QGEN_ARCHITECTURE_RESUME after verified canonical progress.
CLAUDE.md unchanged. Never report authored counters as measured results.

## Internal self-review

Reviewed for placeholders, contradictions, scope and ambiguity before implementation.
Resolved: ALIGNED_COMPLETE is separately scoped to entire-address competencies or
to an explicitly named narrow decision; a decision cannot promote its address.
Resolved: preflight contrast sufficiency follows universe freeze, so it is not an
extra universe selection filter. Snapshot eligibility before the gate refers to
approved feature expressibility, not successful blueprints. Resolved: failure at
the explicit universe gate ends later phases without treating them as completed.
Implementation is authorized by the user's complete gated workflow request.

## Independent design review resolutions

A separate fresh reviewer inspected this spec and the existing consumers before
implementation. Independent approval requires a distinct reviewer execution with
recorded agent provenance and frozen input hashes; differing identity strings are
only a consistency check, not proof of independence. Blind solve gets stem/options
without the intended key, author rationale or earlier verdicts. Parent V3 rows may
have legacy unscoped anchors or empty evidence refs: inherit them unchanged with
legacy provenance; strict new-row rules apply to extensions only. Preserve legacy
registry_hash while additionally hashing the entire behavior-bearing V4 payload,
including anchor_scope, unit bindings and review references.

Bind whole-address coverage to canonical competency artifact hashes. Bind profile
context flags (including pregnancy applicability) and decision/domain/class tuple
to the independently reviewed decision payload; callers cannot override them.
New downstream adapters receive the resolved V2 contract object and explicit pins,
and must not reopen historical profile files under a discipline-only lookup.
