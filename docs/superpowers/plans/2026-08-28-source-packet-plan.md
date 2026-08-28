# Source Packet Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, pending-only source-packet plan that maps all frozen generation demand to future current-Canadian evidence research packets.

**Architecture:** `qbank.source_packet_plan` reads only the committed generation manifest, frozen final allocation, and existing deterministic validators. It produces a many-to-many evidence-requirement map: an allocation address can require several packets and a packet can cover several addresses only when its deterministic canonical evidence key has a recorded reuse basis. Same-address split occurrences always reuse their complete packet set; absence of a safe cross-address key keeps packets separate.

**Tech Stack:** Python 3.11, repository JSON I/O, pytest.

**Spec:** User-approved source-packet plan requirements (2026-08-28 chat).

## Global Constraints

- Read only frozen generation manifests, final allocation, and manifest-carried canonical metadata.
- Do not retrieve sources, write recommendations, or generate MCQs.
- Do not modify scope, MCC mappings, ownership, routing, targets, allocation, or generation manifests.
- Every packet starts as `PENDING_RESEARCH`; authoritative-source and recommendation fields are empty.
- A cross-address packet reuse must record a non-empty canonical reuse basis; unsupported reuse fails validation.
- Build twice and require byte-identical JSON outputs.

---

### Task 1: Specify the source-plan contract with focused tests

**Files:**
- Create: `tests/test_source_packet_plan.py`

**Interfaces:**
- Consumes: `qbank.source_packet_plan.build_source_packet_plan(root)` and `validate_source_packet_plan(root, plan, audit)`.
- Produces: behavioural assertions for complete job/address mapping, deterministic IDs/reuse/batching, initial status, classification metadata, and unsupported-reuse rejection.

- [ ] **Step 1: Write failing tests for frozen-demand mapping and policy fields**

```python
def test_source_plan_maps_every_frozen_job_and_address():
    plan, audit = build_source_packet_plan(REPO)
    assert validate_source_packet_plan(REPO, plan, audit).status == "PASS"
    assert audit["reconciliation"]["GENERATION_JOBS_MAPPED"] == 220
    assert audit["reconciliation"]["ALLOCATION_ADDRESSES_MAPPED"] == 1175

def test_every_packet_is_pending_and_has_required_metadata():
    plan, _ = build_source_packet_plan(REPO)
    for packet in plan["source_packets"]:
        assert packet["status"] == "PENDING_RESEARCH"
        assert packet["evidence_requirement_key"]
        assert packet["evidence_requirement_types"]
        assert packet["source_family_targets"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_source_packet_plan.py -v`

Expected: FAIL because `qbank.source_packet_plan` does not exist.

### Task 2: Implement conservative evidence-packet construction

**Files:**
- Create: `scripts/qbank/source_packet_plan.py`

**Interfaces:**
- Consumes: frozen manifest assignments with allocation address, discipline, chapter, MCC IDs, item forms, source nodes, and title metadata.
- Produces: `build_source_packet_plan(root) -> tuple[dict[str, Any], dict[str, Any]]`, `validate_source_packet_plan(root, plan, audit) -> SourcePacketPlanValidation`, and `write_source_packet_plan(root) -> tuple[dict[str, Any], dict[str, Any]]`.

- [ ] **Step 1: Implement deterministic requirement records and canonical keys**

```python
def _requirement_key(assignment: dict[str, Any], requirement_type: str) -> str:
    return "|".join((
        assignment["discipline"],
        requirement_type,
        ",".join(sorted(assignment["source_node_ids"])),
        ",".join(sorted(assignment["mcc_objective_ids"])),
    ))

def _reuse_basis(requirement_key: str, addresses: set[str]) -> str:
    return "SAME_ALLOCATION_ADDRESS" if len(addresses) == 1 else ""
```

- [ ] **Step 2: Implement packet registry, job/address mappings, batches, and audit**

```python
def build_source_packet_plan(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _load_manifest(root)
    allocation = _load_frozen_allocation(root)
    plan = _plan_from_requirements(manifest, allocation)
    audit = _audit(plan)
    return plan, audit
```

- [ ] **Step 3: Run the focused tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_source_packet_plan.py -v`

Expected: PASS.

### Task 3: Expose safe build/validation commands and materialize artifacts

**Files:**
- Modify: `scripts/qbank/cli.py`
- Create: `research/qgen/source_packet_plan.json`
- Create: `reports/source_packet_plan_audit.json`

**Interfaces:**
- Consumes: `write_source_packet_plan(root)` and `validate_source_packet_plan(root, plan, audit)`.
- Produces: `qbank build-source-packet-plan` and `qbank validate-source-packet-plan` commands plus stable canonical plan/audit JSON.

- [ ] **Step 1: Add build and validation CLI handlers**

```python
("build-source-packet-plan", "build deterministic pending current-Canadian source-packet plan", _command_build_source_packet_plan),
("validate-source-packet-plan", "validate deterministic source-packet plan", _command_validate_source_packet_plan),
```

- [ ] **Step 2: Build twice and validate artifacts**

Run: `.venv/bin/python -m qbank.cli build-source-packet-plan && .venv/bin/python -m qbank.cli validate-source-packet-plan`

Expected: internal repeated output comparison and validator both report PASS.

### Task 4: Verify frozen-layer protection and commit

**Files:**
- Modify: only files from Tasks 1–3 and this implementation plan.

- [ ] **Step 1: Run focused tests and the full suite**

Run: `.venv/bin/python -m pytest tests/test_source_packet_plan.py -v && .venv/bin/python -m pytest`

Expected: all tests pass.

- [ ] **Step 2: Confirm protected artifacts have no diff**

Run: `git diff -- research/qgen/question_generation_manifest.json research/scope/final_question_allocation.json research/scope/question_bank_targets.json research/scope/master_scope_crosswalk.json research/scope/global_ownership_decisions.json research/scope/competency_component_ownership.json`

Expected: no output.

- [ ] **Step 3: Commit verified files**

Run: `git add docs/superpowers/plans/2026-08-28-source-packet-plan.md scripts/qbank/source_packet_plan.py scripts/qbank/cli.py tests/test_source_packet_plan.py research/qgen/source_packet_plan.json reports/source_packet_plan_audit.json && git commit -m "qgen: build source packet plan"`

Expected: the commit contains only approved source-plan tooling, tests, artifacts, and plan documentation.
