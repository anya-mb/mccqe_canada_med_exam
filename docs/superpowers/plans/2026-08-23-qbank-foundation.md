# MCCQE Qbank Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic, fail-closed filesystem pipeline that Codex-native medical agents will use to produce and verify the MCCQE question bank without external LLM APIs.

**Architecture:** A focused Python package owns configuration, JSON Schema validation, source integrity, lifecycle transitions, durable jobs, blind-packet creation, references, reporting, and production export. Codex-native agents operate outside Python and exchange only validated JSON artifacts through the filesystem queue.

**Tech Stack:** Python 3.11+, `jsonschema` 4.x, pytest 8.x, JSON Schema Draft 2020-12, Git, Poppler `pdfinfo` for source inspection.

**Spec:** `docs/superpowers/specs/2026-08-23-qbank-foundation-design.md`

## Global Constraints

- `CODEX_NATIVE` is the default research mode.
- `MANUAL_RESEARCH` is the fallback research mode.
- `API_AUTOMATED` remains disabled until explicitly approved.
- Python must not call any LLM provider, require `OPENAI_API_KEY`, or incur external model/API charges.
- Toronto Notes remains private, Git-ignored, and absent from all deploy artifacts.
- JSON is canonical and all validation fails closed.
- Only `QA_PASS` or documented `HUMAN_REVIEWED` questions may be exported.
- No substantive medical content is generated in this milestone.
- The recorded Toronto Notes source has 1,595 pages and SHA-256 `9cafb5f2064335c8e4ee00abf446ab78d12b469802aa134fb84effcef3704288`.

---

### Task 1: Project policy, packaging, and repository skeleton

**Files:**
- Modify: `.gitignore`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Create: `pyproject.toml`
- Create: `config/project.json`
- Create: `config/project.local.example.json`
- Create: `config/project.local.json`
- Create: `source/README.md`
- Create: lifecycle directory `.gitkeep` files
- Create: `scripts/qbank/__init__.py`
- Test: `tests/test_repository_policy.py`

**Interfaces:**
- Consumes: the approved design and existing Toronto Notes source location.
- Produces: installable `qbank` package, portable committed configuration, ignored local source override, and required directory layout.

- [ ] **Step 1: Write failing repository-policy tests**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_directories_exist():
    for relative in (
        "manifests", "jobs/pending", "jobs/running", "jobs/completed",
        "jobs/failed", "batches", "candidates", "blind",
        "blind_verification", "verified", "quarantine", "rejected",
        "retired", "references", "reports", "schemas",
        "app/public/data/qbank",
    ):
        assert (ROOT / relative).is_dir(), relative


def test_private_source_patterns_are_ignored():
    ignore = (ROOT / ".gitignore").read_text()
    for pattern in ("*.pdf", "config/project.local.json", "derived/"):
        assert pattern in ignore


def test_agents_prohibits_external_llm_billing():
    policy = (ROOT / "AGENTS.md").read_text()
    assert "CODEX_NATIVE" in policy
    assert "OPENAI_API_KEY" in policy
    assert "accuracy over quantity" in policy.lower()
```

- [ ] **Step 2: Run the tests and confirm the skeleton test fails**

Run: `pytest -q tests/test_repository_policy.py`

Expected: failure because the required directories and complete policy do not yet exist.

- [ ] **Step 3: Create package configuration and repository policy**

Use `pyproject.toml` with:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "mccqe-qbank-pipeline"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["jsonschema>=4.23,<5"]

[project.optional-dependencies]
dev = ["pytest>=8,<9"]

[project.scripts]
qbank = "qbank.cli:main"

[tool.setuptools]
package-dir = {"" = "scripts"}

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Extend `AGENTS.md` with every permanent medical, copyright, validation, status, human-review, and no-external-API rule from the design. Create the requested directories and `.gitkeep` files. Set `config/project.json` to `CODEX_NATIVE`, concurrency `4`, blind confidence `0.85`, maximum revisions `2`, and the expected source metadata. Put the absolute PDF path only in ignored `config/project.local.json` and a placeholder path in the committed example.

- [ ] **Step 4: Install the local project environment and rerun tests**

Run: `uv sync --extra dev`

Run: `uv run pytest -q tests/test_repository_policy.py`

Expected: all repository-policy tests pass.

- [ ] **Step 5: Commit the skeleton**

```bash
git add .gitignore AGENTS.md README.md pyproject.toml config/project.json config/project.local.example.json source/README.md scripts/qbank/__init__.py tests/test_repository_policy.py manifests jobs batches candidates blind blind_verification verified quarantine rejected retired references reports schemas app/public/data/qbank
git commit -m "chore: scaffold qbank production pipeline"
```

Do not add `config/project.local.json` or the PDF.

### Task 2: Configuration and atomic JSON I/O

**Files:**
- Create: `scripts/qbank/errors.py`
- Create: `scripts/qbank/jsonio.py`
- Create: `scripts/qbank/config.py`
- Test: `tests/test_config.py`
- Test: `tests/test_jsonio.py`

**Interfaces:**
- Consumes: `config/project.json` and optional `config/project.local.json`.
- Produces: `load_config(root: Path) -> dict`, `read_json(path: Path) -> object`, and `write_json_atomic(path: Path, value: object) -> None`.

- [ ] **Step 1: Write failing config and I/O tests**

```python
def test_local_config_recursively_overrides_committed_config(tmp_path):
    write_json(tmp_path / "config/project.json", {"research_mode": "CODEX_NATIVE", "limits": {"generation": 4, "verification": 4}})
    write_json(tmp_path / "config/project.local.json", {"limits": {"generation": 2}})
    assert load_config(tmp_path)["limits"] == {"generation": 2, "verification": 4}


def test_unknown_research_mode_fails(tmp_path):
    write_json(tmp_path / "config/project.json", {"research_mode": "MEMORY_ONLY"})
    with pytest.raises(ConfigError, match="research_mode"):
        load_config(tmp_path)


def test_atomic_json_is_sorted_and_newline_terminated(tmp_path):
    target = tmp_path / "nested/data.json"
    write_json_atomic(target, {"z": 1, "a": 2})
    assert target.read_text() == '{\n  "a": 2,\n  "z": 1\n}\n'
```

- [ ] **Step 2: Run tests and confirm missing modules fail**

Run: `uv run pytest -q tests/test_config.py tests/test_jsonio.py`

Expected: import failures for the new `qbank` modules.

- [ ] **Step 3: Implement typed errors, recursive merge, mode validation, and atomic writes**

Define `QbankError`, `ConfigError`, `SchemaValidationError`, `SourceValidationError`, `TransitionError`, and `ExportError`. Atomic writes use a temporary sibling file, flush and `os.fsync`, then `os.replace`. Reject research modes outside `{CODEX_NATIVE, MANUAL_RESEARCH, API_AUTOMATED}` and reject `API_AUTOMATED` unless `api_automated_enabled` is exactly `true`.

- [ ] **Step 4: Run focused tests**

Run: `uv run pytest -q tests/test_config.py tests/test_jsonio.py`

Expected: all tests pass.

- [ ] **Step 5: Commit configuration infrastructure**

```bash
git add scripts/qbank/errors.py scripts/qbank/jsonio.py scripts/qbank/config.py tests/test_config.py tests/test_jsonio.py
git commit -m "feat: add deterministic config and JSON storage"
```

### Task 3: Canonical JSON Schemas

**Files:**
- Create: `schemas/project.schema.json`
- Create: `schemas/manifest.schema.json`
- Create: `schemas/job.schema.json`
- Create: `schemas/reference.schema.json`
- Create: `schemas/reference-registry.schema.json`
- Create: `schemas/question.schema.json`
- Create: `schemas/blind-packet.schema.json`
- Create: `schemas/blind-verification.schema.json`
- Create: `schemas/rationale-verification.schema.json`
- Create: `schemas/progress.schema.json`
- Create: `schemas/production-manifest.schema.json`
- Create: `scripts/qbank/schema.py`
- Create: `tests/fixtures/valid/` JSON fixtures
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: a schema name and Python JSON value.
- Produces: `validate_instance(root: Path, schema_name: str, instance: object) -> None`, raising `SchemaValidationError` with JSON paths.

- [ ] **Step 1: Write failing schema contract tests**

```python
@pytest.mark.parametrize("schema_name,fixture", [
    ("project", "project.json"),
    ("manifest", "manifest.json"),
    ("job", "job.json"),
    ("reference-registry", "reference-registry.json"),
    ("question", "question.json"),
    ("blind-packet", "blind-packet.json"),
    ("blind-verification", "blind-verification.json"),
    ("rationale-verification", "rationale-verification.json"),
    ("progress", "progress.json"),
    ("production-manifest", "production-manifest.json"),
])
def test_valid_fixture(schema_name, fixture, repo_root):
    validate_instance(repo_root, schema_name, read_json(repo_root / "tests/fixtures/valid" / fixture))


def test_question_requires_exactly_five_options(valid_question, repo_root):
    valid_question["question"]["options"].pop()
    with pytest.raises(SchemaValidationError):
        validate_instance(repo_root, "question", valid_question)


@pytest.mark.parametrize("mutation", [
    lambda q: q.update(correct_answer="Z"),
    lambda q: q["explanation"].update(clinical_reasoning=""),
    lambda q: q["explanation"].update(distractor_rationales={}),
    lambda q: q.update(references=[]),
    lambda q: q.update(toronto_notes={}),
    lambda q: q.update(mcc={}),
])
def test_question_rejects_missing_canonical_content(valid_question, repo_root, mutation):
    mutation(valid_question)
    with pytest.raises(SchemaValidationError):
        validate_instance(repo_root, "question", valid_question)


def test_blind_packet_forbids_answer_and_explanation(valid_blind, repo_root):
    valid_blind["correct_answer"] = "A"
    with pytest.raises(SchemaValidationError):
        validate_instance(repo_root, "blind-packet", valid_blind)
```

- [ ] **Step 2: Run schema tests and confirm failure**

Run: `uv run pytest -q tests/test_schemas.py`

Expected: failures because schemas and validator are absent.

- [ ] **Step 3: Implement Draft 2020-12 schemas and validator**

Every object uses `additionalProperties: false` unless an explicitly documented extensibility map is required. Define `$defs` for Toronto Notes mapping, MCC mapping, five unique A–E options, explanations, verification, references, statuses, timestamps, and failure classes. The validator sorts all errors and includes paths such as `question.options` in its exception message.

- [ ] **Step 4: Run schema tests**

Run: `uv run pytest -q tests/test_schemas.py`

Expected: all valid fixtures pass and invalid mutations fail.

- [ ] **Step 5: Commit schemas**

```bash
git add schemas scripts/qbank/schema.py tests/fixtures tests/test_schemas.py
git commit -m "feat: define canonical qbank schemas"
```

### Task 4: Source integrity and deployment leakage checks

**Files:**
- Create: `scripts/qbank/source.py`
- Test: `tests/test_source.py`

**Interfaces:**
- Consumes: merged project config and repository root.
- Produces: `validate_source(root: Path, config: dict) -> SourceReport` and `scan_deploy_leaks(root: Path) -> list[Path]`.

- [ ] **Step 1: Write failing source tests**

```python
def test_source_validation_checks_hash_pages_and_git_exclusion(source_repo):
    report = validate_source(source_repo.root, source_repo.config)
    assert report.valid
    assert report.pages == source_repo.expected_pages


def test_missing_source_fails_closed(tmp_path, minimal_config):
    with pytest.raises(SourceValidationError, match="missing"):
        validate_source(tmp_path, minimal_config)


def test_pdf_in_public_assets_is_a_leak(tmp_path):
    leaked = tmp_path / "app/public/notes.pdf"
    leaked.parent.mkdir(parents=True)
    leaked.write_bytes(b"%PDF")
    assert scan_deploy_leaks(tmp_path) == [leaked]
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest -q tests/test_source.py`

Expected: import failure for `qbank.source`.

- [ ] **Step 3: Implement streaming SHA-256, `pdfinfo` parsing, Git tracking checks, and leakage scan**

Use `subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True, text=True)` without a shell. Use `git ls-files --error-unmatch -- <path>` to detect tracking. Reject any source under `app/public`, any `public` directory, or `dist`. Scan those deploy roots for PDF files and private lifecycle directory names.

- [ ] **Step 4: Run focused and real-source validation**

Run: `uv run pytest -q tests/test_source.py`

Run: `uv run qbank validate-source`

Expected: tests pass; real source reports 1,595 pages and the configured hash.

- [ ] **Step 5: Commit source validation**

```bash
git add scripts/qbank/source.py tests/test_source.py
git commit -m "feat: enforce Toronto Notes source integrity"
```

### Task 5: Lifecycle state machine

**Files:**
- Create: `scripts/qbank/states.py`
- Test: `tests/test_states.py`

**Interfaces:**
- Consumes: current status, requested status, and optional human-review metadata.
- Produces: `validate_transition(current: str, target: str, *, human_review: dict | None = None) -> None`.

- [ ] **Step 1: Write exhaustive failing transition tests**

```python
ALLOWED = {
    ("DRAFT", "CANDIDATE"),
    ("CANDIDATE", "STRUCTURE_PASS"),
    ("CANDIDATE", "QUARANTINE"),
    ("STRUCTURE_PASS", "BLIND_PASS"),
    ("STRUCTURE_PASS", "QUARANTINE"),
    ("BLIND_PASS", "MEDICAL_PASS"),
    ("BLIND_PASS", "QUARANTINE"),
    ("MEDICAL_PASS", "QA_PASS"),
    ("MEDICAL_PASS", "QUARANTINE"),
    ("QA_PASS", "PUBLISHED"),
    ("QUARANTINE", "REVISED"),
    ("QUARANTINE", "REJECTED"),
    ("REVISED", "CANDIDATE"),
}


@pytest.mark.parametrize("transition", ALLOWED)
def test_allowed_transition(transition):
    validate_transition(*transition)


def test_draft_cannot_publish():
    with pytest.raises(TransitionError):
        validate_transition("DRAFT", "PUBLISHED")


def test_human_review_requires_real_reviewer_metadata():
    with pytest.raises(TransitionError):
        validate_transition("MEDICAL_PASS", "HUMAN_REVIEWED", human_review={})
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest -q tests/test_states.py`

Expected: import failure for `qbank.states`.

- [ ] **Step 3: Implement explicit adjacency rules and terminal statuses**

Human review metadata must include non-empty `reviewer_name`, `credentials`, `reviewed_at`, and `scope`. `REJECTED`, `RETIRED`, and `PUBLISHED` are terminal. Add transitions from `MEDICAL_PASS` and `QA_PASS` to `HUMAN_REVIEWED`, and from `HUMAN_REVIEWED` to `PUBLISHED`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q tests/test_states.py`

Expected: all tests pass.

- [ ] **Step 5: Commit lifecycle enforcement**

```bash
git add scripts/qbank/states.py tests/test_states.py
git commit -m "feat: enforce qbank lifecycle transitions"
```

### Task 6: Manifest validation and deterministic queue generation

**Files:**
- Create: `scripts/qbank/manifests.py`
- Create: `scripts/qbank/jobs.py`
- Test: `tests/test_manifests.py`
- Test: `tests/test_jobs.py`

**Interfaces:**
- Consumes: schema-valid discipline manifests.
- Produces: `validate_manifest_set(manifests: list[dict]) -> ManifestSummary`, `create_generation_jobs(root: Path, manifests: list[dict]) -> list[Path]`, and `transition_job(root: Path, job_id: str, target: str, failure: dict | None = None) -> Path`.

- [ ] **Step 1: Write failing manifest and queue tests**

```python
def test_manifest_set_rejects_cross_discipline_id_collision(valid_manifests):
    valid_manifests[1]["batches"][0]["question_ids"][0] = valid_manifests[0]["batches"][0]["question_ids"][0]
    with pytest.raises(SchemaValidationError, match="duplicate question ID"):
        validate_manifest_set(valid_manifests)


def test_generation_jobs_are_deterministic(tmp_path, valid_manifest):
    first = create_generation_jobs(tmp_path, [valid_manifest])
    first_bytes = [path.read_bytes() for path in first]
    second = create_generation_jobs(tmp_path, [valid_manifest])
    assert [path.read_bytes() for path in second] == first_bytes


def test_failed_job_preserves_artifacts_and_increments_attempt(tmp_path, pending_job):
    failed = transition_job(tmp_path, pending_job["job_id"], "failed", {"class": "SOURCE_FAILURE", "message": "unavailable"})
    value = read_json(failed)
    assert value["attempt"] == 1
    assert value["failure"]["class"] == "SOURCE_FAILURE"
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest -q tests/test_manifests.py tests/test_jobs.py`

Expected: imports fail for manifest and job modules.

- [ ] **Step 3: Implement cross-manifest validation and durable queue operations**

Reject batch targets outside 40–60, mismatched target/ID counts, missing page mappings, duplicated batch IDs, duplicated question IDs, target totals that disagree with section or batch totals, and non-contiguous sequence allocation within a batch. Jobs use sorted deterministic content and stable paths `jobs/<status>/<job_id>.json`. Existing identical pending jobs are idempotent; differing content with the same ID fails.

- [ ] **Step 4: Run focused tests**

Run: `uv run pytest -q tests/test_manifests.py tests/test_jobs.py`

Expected: all tests pass.

- [ ] **Step 5: Commit manifest and queue tooling**

```bash
git add scripts/qbank/manifests.py scripts/qbank/jobs.py tests/test_manifests.py tests/test_jobs.py
git commit -m "feat: generate deterministic qbank job queues"
```

### Task 7: Candidate structure, blind packets, and independent-answer gate

**Files:**
- Create: `scripts/qbank/blind.py`
- Test: `tests/test_blind.py`

**Interfaces:**
- Consumes: schema-valid candidate and blind-verification result.
- Produces: `build_blind_packet(candidate: dict) -> dict` and `evaluate_blind_result(candidate: dict, result: dict, threshold: float = 0.85) -> BlindDecision`.

- [ ] **Step 1: Write failing blind-isolation and comparator tests**

```python
FORBIDDEN = {"correct_answer", "explanation", "distractor_rationales", "generator_notes", "verification"}


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_blind_packet_recursively_excludes_generator_fields(valid_question):
    packet = build_blind_packet(valid_question)
    assert FORBIDDEN.isdisjoint(set(walk_keys(packet)))


def test_mismatched_key_quarantines_without_autocorrection(valid_question, valid_blind_result):
    valid_blind_result["independent_answer"] = "B"
    decision = evaluate_blind_result(valid_question, valid_blind_result)
    assert decision.status == "QUARANTINE"
    assert decision.reason == "BLIND_KEY_MISMATCH"
    assert valid_question["correct_answer"] == "A"


def test_low_confidence_quarantines(valid_question, valid_blind_result):
    valid_blind_result["confidence"] = 0.84
    assert evaluate_blind_result(valid_question, valid_blind_result).status == "QUARANTINE"
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest -q tests/test_blind.py`

Expected: import failure for `qbank.blind`.

- [ ] **Step 3: Implement explicit projection and fail-closed comparison**

Construct the blind packet from an allowlist, never by deleting a blacklist. Advance to `BLIND_PASS` only when keys match, confidence meets threshold, `single_best_answer` is true, `other_defensible_options` is empty, `stem_sufficient` and guideline support are true, and recommendation is `PASS`. Return a structured quarantine reason for every failed gate.

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q tests/test_blind.py`

Expected: all tests pass.

- [ ] **Step 5: Commit blind verification boundary**

```bash
git add scripts/qbank/blind.py tests/test_blind.py
git commit -m "feat: add isolated blind verification gate"
```

### Task 8: Reference registry and high-risk classification

**Files:**
- Create: `references/registry.json`
- Create: `scripts/qbank/references.py`
- Create: `scripts/qbank/risk.py`
- Test: `tests/test_references.py`
- Test: `tests/test_risk.py`

**Interfaces:**
- Consumes: validated reference records and candidate questions.
- Produces: `merge_references(registry: dict, incoming: list[dict]) -> tuple[dict, dict[str, str]]` and `classify_risk(question: dict) -> list[str]`.

- [ ] **Step 1: Write failing registry and risk tests**

```python
def test_same_canonical_guideline_reuses_stable_id(empty_registry, reference):
    registry, mapping = merge_references(empty_registry, [reference])
    duplicate = {**reference, "reference_id": "TEMP-999", "url": reference["url"] + "/"}
    merged, second_mapping = merge_references(registry, [duplicate])
    assert len(merged["references"]) == 1
    assert second_mapping["TEMP-999"] == mapping[reference["reference_id"]]


@pytest.mark.parametrize("text,flag", [
    ("What dose should be administered?", "DOSE"),
    ("She is 24 weeks pregnant.", "PREGNANCY"),
    ("Which screening interval is recommended?", "SCREENING"),
    ("This condition must be reported to public health.", "PUBLIC_HEALTH_REPORTING"),
])
def test_high_risk_text_is_flagged(valid_question, text, flag):
    valid_question["question"]["stem"] = text
    assert flag in classify_risk(valid_question)
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest -q tests/test_references.py tests/test_risk.py`

Expected: imports fail for new modules.

- [ ] **Step 3: Implement canonical reference identity and deterministic risk flags**

Normalize URL scheme/host case, trailing slashes, organization, normalized title, and publication date. Allocate stable IDs from organization slug plus a short SHA-256 identity suffix. Preserve support claims separately and merge only exact normalized claim/locator pairs. Risk flags are sorted from the fixed enum `NUMERICAL_THRESHOLD`, `DOSE`, `SCREENING`, `VACCINATION`, `PREGNANCY`, `PEDIATRICS`, `ANTICOAGULATION`, `LEGAL`, `PUBLIC_HEALTH_REPORTING`, and `EMERGENCY_TREATMENT`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q tests/test_references.py tests/test_risk.py`

Expected: all tests pass.

- [ ] **Step 5: Commit registry and risk tooling**

```bash
git add references/registry.json scripts/qbank/references.py scripts/qbank/risk.py tests/test_references.py tests/test_risk.py
git commit -m "feat: normalize references and flag medical risk"
```

### Task 9: Progress reports and production export

**Files:**
- Create: `scripts/qbank/progress.py`
- Create: `scripts/qbank/export.py`
- Test: `tests/test_progress.py`
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: filesystem questions, manifests, jobs, and reference registry.
- Produces: `build_progress(root: Path) -> dict`, `write_progress(root: Path) -> tuple[Path, Path]`, and `build_production(root: Path, version: str, now: datetime) -> dict`.

- [ ] **Step 1: Write failing reporting and export tests**

```python
def test_progress_counts_filesystem_truth(populated_repo):
    report = build_progress(populated_repo)
    assert report["generated"] == 3
    assert report["qa_passed"] == 1
    assert report["quarantined"] == 1
    assert report["jobs"]["pending"] == 2


def test_export_includes_only_publication_eligible_items(populated_repo):
    result = build_production(populated_repo, "2026.1", FIXED_NOW)
    assert result["manifest"]["total_questions"] == 2
    assert {q["status"] for q in result["questions"]} == {"QA_PASS", "HUMAN_REVIEWED"}
    assert {q["id"] for q in result["questions"]}.isdisjoint({"CANDIDATE-1", "REJECTED-1", "RETIRED-1"})


def test_human_review_without_reviewer_metadata_is_not_exported(populated_repo):
    remove_reviewer_metadata(populated_repo / "verified/human.json")
    with pytest.raises(ExportError, match="human review metadata"):
        build_production(populated_repo, "2026.1", FIXED_NOW)


def test_unknown_reference_blocks_export(populated_repo):
    set_question_references(populated_repo, ["REF-UNKNOWN"])
    with pytest.raises(ExportError, match="unknown reference"):
        build_production(populated_repo, "2026.1", FIXED_NOW)
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `uv run pytest -q tests/test_progress.py tests/test_export.py`

Expected: imports fail for reporting and export modules.

- [ ] **Step 3: Implement derived reporting and staged production writes**

Progress walks canonical lifecycle directories and validated jobs, groups by discipline/chapter, and emits deterministic Markdown. Export builds into a temporary staging directory, schema-validates every item, validates reference IDs, scans for forbidden private fields, computes counts, then atomically replaces only `app/public/data/qbank`. It writes discipline-specific question files, `references.json`, and `manifest.json` with the supplied clock value.

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q tests/test_progress.py tests/test_export.py`

Expected: all tests pass.

- [ ] **Step 5: Commit reporting and safe export**

```bash
git add scripts/qbank/progress.py scripts/qbank/export.py tests/test_progress.py tests/test_export.py
git commit -m "feat: build progress reports and safe production data"
```

### Task 10: CLI integration and full foundation verification

**Files:**
- Create: `scripts/qbank/cli.py`
- Modify: `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: all earlier module interfaces.
- Produces: commands `validate-project`, `validate-source`, `validate-manifests`, `create-jobs`, `create-blind`, `evaluate-blind`, `progress`, and `export`.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_validate_project_succeeds(repo_root):
    result = run_cli(repo_root, "validate-project")
    assert result.returncode == 0
    assert "PROJECT_VALID" in result.stdout


def test_validate_project_stops_on_missing_source(project_copy):
    remove_local_source(project_copy)
    result = run_cli(project_copy, "validate-project")
    assert result.returncode != 0
    assert "SOURCE_FAILURE" in result.stderr


def test_create_jobs_requires_all_six_valid_manifests(project_copy):
    result = run_cli(project_copy, "create-jobs")
    assert result.returncode != 0
    assert "six manifests" in result.stderr.lower()
```

- [ ] **Step 2: Run CLI tests and confirm failure**

Run: `uv run pytest -q tests/test_cli.py`

Expected: command import or entry-point failure.

- [ ] **Step 3: Implement argparse CLI with machine-readable failures**

Every command accepts `--root`, writes normal output to stdout, writes `FAILURE_CLASS: message` to stderr, and returns a nonzero code on any validation error. `validate-project` runs config/schema, prompt presence, source integrity, Git/deploy exclusion, and schema self-tests; it reports that manifest generation remains blocked until all six manifests exist. Update the README with setup, modes, commands, lifecycle, private-source rules, Codex-native execution contract, and milestone sequence.

- [ ] **Step 4: Run complete verification**

Run: `uv run pytest -q`

Run: `uv run qbank validate-project`

Run: `git ls-files | rg -i '\\.pdf$|^derived/|project\\.local\\.json$'` 

Expected: all tests pass; project validation reports the source is valid and generation is not yet permitted because manifests do not exist; the leakage command prints nothing.

- [ ] **Step 5: Inspect changes and commit milestone 1**

Run: `git diff --check`

Run: `git status --short`

```bash
git add scripts/qbank/cli.py README.md tests/test_cli.py
git commit -m "feat: complete deterministic qbank foundation"
```

### Task 11: Milestone handoff report

**Files:**
- Create: `reports/milestone-1-foundation.md`
- Create: `reports/progress.json`
- Create: `reports/progress.md`

**Interfaces:**
- Consumes: verified milestone outputs and test evidence.
- Produces: a factual checkpoint recording source validation, implemented controls, test command/result, and explicit blockers before medical generation.

- [ ] **Step 1: Generate initial progress reports**

Run: `uv run qbank progress`

Expected: planned/generated/verified counts are zero and queue counts reflect the empty foundation.

- [ ] **Step 2: Write the milestone report with exact verification evidence**

Record the Git commit IDs, `uv run pytest -q` result, source hash/page count, research mode, and the next authorized milestone: private Toronto Notes ingestion. State explicitly that no questions have been generated or published.

- [ ] **Step 3: Re-run final verification**

Run: `uv run pytest -q`

Run: `uv run qbank validate-project`

Run: `git diff --check`

Expected: all tests pass, source validates, and no whitespace errors exist.

- [ ] **Step 4: Commit the milestone report**

```bash
git add reports/milestone-1-foundation.md reports/progress.json reports/progress.md
git commit -m "docs: checkpoint qbank foundation milestone"
```

After this commit, invoke brainstorming for Milestone 2 Toronto Notes ingestion. That milestone must establish private extraction quality and page mapping before any Cardiology medical-content work begins.
