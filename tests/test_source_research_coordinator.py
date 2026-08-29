from copy import deepcopy
import json
from pathlib import Path
import subprocess

from qbank.generation_source_state import (
    build_generation_queue,
    build_generation_source_readiness,
)
from qbank.source_document_registry import build_source_document_registry
from qbank.source_packet_population import load_integrated_source_packet_populations
from qbank.source_research_coordinator import (
    build_source_research_integration_audit,
    discover_source_research_workers,
    resolve_git_commit,
    validate_disjoint_worker_ownership,
    validate_source_research_integration_audit,
    validate_worker_commit,
)


REPO = Path(__file__).resolve().parents[1]


def _population(batch_id: str) -> dict:
    stem = batch_id.lower().replace("-", "_")
    return json.loads(
        (REPO / f"research/qgen/source_packet_population_{stem}.json").read_text(
            encoding="utf-8"
        )
    )


def test_disjoint_ownership_rejects_duplicate_pending_packet_or_integrated_batch() -> None:
    integrated = _population("SRB-001")
    duplicate = deepcopy(_population("SRB-002"))
    duplicate["source_packets"][0]["source_packet_id"] = integrated["source_packets"][0][
        "source_packet_id"
    ]

    result = validate_disjoint_worker_ownership(
        REPO, ["SRB-001", "SRB-001"], [integrated, duplicate]
    )

    assert result.status == "FAIL"
    assert any("duplicate pending batch" in error for error in result.errors)
    assert any("already integrated batch" in error for error in result.errors)
    assert any("not pairwise disjoint" in error for error in result.errors)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _worker_repository(tmp_path: Path, batch_id: str = "SRB-001") -> tuple[Path, str, dict[str, str]]:
    """Create a canonical checkpoint just before one real validated worker pair."""
    root = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "--quiet", str(REPO), str(root)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stem = batch_id.lower().replace("-", "_")
    paths = {
        "population": f"research/qgen/source_packet_population_{stem}.json",
        "audit": f"reports/source_packet_wave_{stem}_audit.json",
    }
    payloads = {
        name: (REPO / relative).read_text(encoding="utf-8")
        for name, relative in paths.items()
    }
    for relative in paths.values():
        (root / relative).unlink()
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "remove worker pair from canonical checkpoint")
    return root, _git(root, "rev-parse", "HEAD"), payloads


def _commit_worker_pair(root: Path, canonical: str, payloads: dict[str, str], batch_id: str = "SRB-001") -> tuple[str, str]:
    branch = f"codex/source-research/{batch_id}"
    _git(root, "checkout", "-b", branch, canonical)
    stem = batch_id.lower().replace("-", "_")
    population_path = root / f"research/qgen/source_packet_population_{stem}.json"
    audit_path = root / f"reports/source_packet_wave_{stem}_audit.json"
    population_path.write_text(payloads["population"], encoding="utf-8")
    audit_path.write_text(payloads["audit"], encoding="utf-8")
    _git(root, "add", str(population_path.relative_to(root)), str(audit_path.relative_to(root)))
    _git(root, "commit", "-m", f"populate {batch_id}")
    return branch, _git(root, "rev-parse", "HEAD")


def test_discovery_classifies_dirty_worktree_retry_and_committed_branch_awaiting_integration(tmp_path: Path) -> None:
    root, canonical, payloads = _worker_repository(tmp_path)
    committed_branch, _ = _commit_worker_pair(root, canonical, payloads)
    _git(root, "checkout", "main")

    dirty_branch = "codex/source-research/SRB-002"
    dirty_path = tmp_path / "dirty-worker"
    _git(root, "worktree", "add", "-b", dirty_branch, str(dirty_path), canonical)
    (dirty_path / "research/qgen/source_packet_population_srb_002.json").write_text(
        "{}\n", encoding="utf-8"
    )

    workers = discover_source_research_workers(root, canonical)
    states = {worker["branch"]: worker["state"] for worker in workers}

    assert states[committed_branch] == "AWAITING_INTEGRATION"
    assert states[dirty_branch] == "RETRY_RESUME"


def test_worker_commit_requires_codex_batch_branch_matching_parent_checkpoint(tmp_path: Path) -> None:
    root, canonical, payloads = _worker_repository(tmp_path)
    branch, _ = _commit_worker_pair(root, canonical, payloads)
    worker = {"branch": branch, "batch_id": "SRB-001", "commit": _git(root, "rev-parse", branch)}

    assert validate_worker_commit(root, worker, canonical).status == "PASS"
    bad_branch = {**worker, "branch": "codex/source-research/SRB-002"}
    bad_parent = {**worker, "commit": canonical}

    assert validate_worker_commit(root, bad_branch, canonical).status == "FAIL"
    assert validate_worker_commit(root, bad_parent, canonical).status == "FAIL"


def test_worker_commit_rejects_any_file_outside_expected_population_audit_pair(tmp_path: Path) -> None:
    root, canonical, payloads = _worker_repository(tmp_path)
    branch, _ = _commit_worker_pair(root, canonical, payloads)
    _git(root, "checkout", branch)
    (root / "unexpected.txt").write_text("forbidden\n", encoding="utf-8")
    _git(root, "add", "unexpected.txt")
    _git(root, "commit", "-m", "add forbidden path")
    worker = {"branch": branch, "batch_id": "SRB-001", "commit": _git(root, "rev-parse", "HEAD")}

    result = validate_worker_commit(root, worker, canonical)

    assert result.status == "FAIL"
    assert any("unexpected changed path" in error for error in result.errors)


def test_worker_set_rejects_overlapping_or_already_integrated_batches() -> None:
    integrated = _population("SRB-001")
    duplicate = deepcopy(_population("SRB-002"))
    duplicate["source_packets"][0]["source_packet_id"] = integrated["source_packets"][0]["source_packet_id"]

    result = validate_disjoint_worker_ownership(
        REPO, ["SRB-001", "SRB-001"], [integrated, duplicate]
    )

    assert result.status == "FAIL"
    assert any("already integrated batch" in error for error in result.errors)
    assert any("not pairwise disjoint" in error for error in result.errors)


def test_integration_audit_rebuild_detects_changed_prior_ready_packet_and_queue_mismatch() -> None:
    populations = load_integrated_source_packet_populations(REPO)
    registry = build_source_document_registry(REPO, populations)
    readiness = build_generation_source_readiness(REPO, populations)
    queue = build_generation_queue(REPO, readiness)
    workers: list[dict] = []
    canonical = resolve_git_commit(REPO, "HEAD")
    audit = build_source_research_integration_audit(
        REPO, canonical, populations, registry, readiness, queue, workers
    )

    changed_populations = deepcopy(populations)
    changed_populations[0]["source_packets"][0]["evidence_notes"] = ["changed"]
    bad_queue = deepcopy(queue)
    bad_queue["summary"]["GENERATION_QUEUE_JOBS"] += 1
    result = validate_source_research_integration_audit(
        REPO, audit, changed_populations, registry, readiness, bad_queue, workers
    )

    assert result.status == "FAIL"
    assert any("does not match deterministic rebuild" in error for error in result.errors)
    assert any("PRIOR_READY_PACKET_IMMUTABILITY" in error for error in result.errors)
