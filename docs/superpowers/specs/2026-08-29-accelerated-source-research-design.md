# Accelerated Source Research Design

Date: 2026-08-29

## Scope

Option A accelerates only current-source packet research and discovers generation readiness. It preserves the frozen source-packet plan and existing packet schema. This phase adds no MCQ generator, verifier, or research content.

## Durable artifacts

The coordinator deterministically rebuilds and validates these tracked artifacts from the plan and canonical integrated packet populations:

| Artifact | Purpose |
| --- | --- |
| `research/qgen/source_document_registry.json` | Metadata-only records for verified source discovery: canonical URL, title, issuer, source family/type, jurisdiction, version/date/currentness metadata, retrieval check, and first/last packet reference. It contains no clinical claims. |
| `reports/source_packet_research_progress.json` | Existing plan-bound packet/batch totals and statuses, rebuilt from integrated populations. |
| `research/qgen/generation_source_readiness.json` | One deterministic record per frozen generation job: required packet IDs, their statuses, `PENDING`/`BLOCKED`/`SOURCE_READY`, and blocking IDs/reason categories. |
| `research/qgen/generation_queue.json` | Ordered subset of readiness records whose state is `SOURCE_READY`; order is the frozen manifest job order, then job ID. |
| `reports/source_research_integration_audit.json` | Reconciliation, immutability, worker-branch discovery, registry, readiness, queue, and checkpoint validation results. |

`MEMORY.md` is updated by the coordinator from these artifacts with the canonical checkpoint SHA and one next recommended action. It is a resume summary, never a source of truth.

## States and ownership

Each planned source packet has exactly one integrated state:

`PENDING_RESEARCH` → `SOURCE_PACKET_READY` | `INCOMPLETE_RESEARCH` | `BLOCKED_EVIDENCE_CONFLICT` | `BLOCKED_JURISDICTION`.

Each frozen generation job derives its state without agent judgment:

`PENDING` when any required packet is pending or incomplete; `BLOCKED` when any required packet is blocked; `SOURCE_READY` only when every required packet is ready. A ready job enters the queue immediately; it does not wait for unrelated research.

Future-only generation contract is:

`SOURCE_READY` → `GENERATED` → `PENDING_INDEPENDENT_VERIFICATION` → `VERIFIED`, with `REJECTED_FOR_REVISION` looping back to generation. The generator and independent verifier must run in separate contexts; no generator self-verification. No executor or verifier artifact is implemented in this phase.

## Worker contract

A worker receives a mechanically prepared, batch-local input: stable applicable `AGENTS.md` rules, current `MEMORY.md`, one batch's exact packet objects, source-family/freshness/jurisdiction metadata, a read-only registry snapshot, and the minimal output/validator contract. It does not receive unrelated packet populations, generation jobs, historical reports, or methodology unless a concrete failure requires them.

One worker owns one canonical batch. Its isolated branch is named `codex/source-research/SRB-XXX` and begins at the recorded canonical coordinator checkpoint. On success it runs the batch validator and creates exactly one commit containing only:

- `research/qgen/source_packet_population_srb_XXX.json`
- `reports/source_packet_wave_srb_XXX_audit.json`

The worker neither changes coordinator artifacts nor processes another uncommitted batch. It reuses registry discovery metadata only after independently checking that the document remains current under registry policy; packet-specific claim support, citations, and conflict handling are always independently researched.

The worker reports only:

```text
WORKER_BATCH = SRB-XXX
STATUS = PASS/FAIL
PACKETS = __
READY = __
BLOCKED = __
INCOMPLETE = __
CANADIAN_SOURCES = __
INTERNATIONAL_FALLBACKS = __
UNRESOLVED_CONFLICTS = __
COMMIT = __
WORKING_TREE_CLEAN = true/false
```

Batch-local validation checks exact canonical packet order and ownership, frozen input fingerprints, planning-field immutability, status/claim/source structure, citation locators, and the wave audit. Data-only workers run no full suite.

## Coordinator contract and resume

Parallelism is an execution choice: default two workers, three for routine LOW/MODERATE batches, and four only for straightforward independent batches when usage budget permits. A coordinator selects only disjoint packet IDs and records branch names plus base checkpoint before dispatch. Branches are the durable in-flight ledger: a new session derives `PENDING`, retry-in-progress, and `AWAITING_INTEGRATION` batches from the plan, canonical populations, `git worktree list`, and the required worker-branch naming/commit shape. A committed output pair on an unmerged worker branch is awaiting integration; an uncommitted worktree is its retry point.

The coordinator accepts only worker commits with the two allowed files, the expected batch ID, a matching base checkpoint, and a passing batch validator. It merges a disjoint accepted set, then rebuilds the registry, progress, readiness, queue, and integration audit from canonical packet populations. It validates combined source-round reconciliation, immutable prior ready packets, document-registry metadata consistency, and queue/readiness completeness. It then commits the consolidated artifacts and `MEMORY.md` as one canonical coordinator checkpoint.

Thus, a new session needs only the checkout and local git references/worktrees to determine completed and pending batches, unintegrated worker outputs, packet status, ready jobs, queue order, current checkpoint, and next action. If a worker fails or reaches a limit mid-batch, canonical main is unchanged; the named worktree/branch is resumed or discarded and the batch remains non-integrated. If a worker committed successfully, its output remains recoverable until coordinator integration.

## Validation and migration

Implementation adds deterministic batch-local ownership validation, coordinator reconciliation, registry/readiness/queue builders and validators, and focused tests. Production Python, schemas, validators, or orchestration behavior require the full suite; a purely data-only worker batch does not. The coordinator may run a full suite at an explicit periodic checkpoint.

Existing populated waves are migrated by deterministic reconstruction: ingest their already validated source metadata into the registry; derive readiness and queue from all canonical populations; generate the first integration audit and checkpoint. The migration fails closed on duplicate source IDs with incompatible metadata, changed frozen packet fields, duplicate packet ownership, non-rebuild-equivalent plan, or readiness/queue mismatch. No clinical claim is rewritten during migration.
