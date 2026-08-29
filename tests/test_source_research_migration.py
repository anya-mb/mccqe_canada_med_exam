import json
from pathlib import Path

from qbank.source_research_coordinator import (
    build_source_research_state,
    resolve_git_commit,
)


REPO = Path(__file__).resolve().parents[1]


def _render(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def test_current_repository_reconstructs_valid_source_research_state() -> None:
    """Reject a coordinator build that loses canonical packet/source/job reconciliation."""
    coordinator_input_commit = resolve_git_commit(REPO, "HEAD")

    state = build_source_research_state(REPO, coordinator_input_commit)
    repeated = build_source_research_state(REPO, coordinator_input_commit)

    assert state.progress["SOURCE_PACKETS_READY"] == 70
    assert state.progress["SOURCE_PACKETS_PENDING"] == 1454
    assert state.progress["RESEARCH_BATCHES_COMPLETE"] == 8
    assert state.progress["RESEARCH_BATCHES_PENDING"] == 151
    assert state.progress["AUTHORITATIVE_SOURCE_RECORDS"] == 95
    assert len(state.registry["documents"]) == 67
    assert len(state.registry["input_populations"]) == 8
    assert len(state.readiness["jobs"]) == 220
    assert state.readiness["summary"] == {
        "GENERATION_JOBS_TOTAL": 220,
        "GENERATION_JOBS_SOURCE_READY": 0,
        "GENERATION_JOBS_PENDING": 220,
        "GENERATION_JOBS_BLOCKED": 0,
        "QUESTION_SLOTS_TOTAL": 6086,
        "QUESTION_SLOTS_SOURCE_READY": 0,
    }
    assert state.queue["jobs"] == []
    assert state.queue["summary"] == {
        "GENERATION_QUEUE_JOBS": 0,
        "QUESTION_SLOTS_QUEUED": 0,
    }
    assert state.audit["status"] == "PASS"
    assert state.audit["coordinator_input_commit"] == coordinator_input_commit
    assert state.audit["checks"]["DISJOINT_WORKER_OWNERSHIP"] == "PASS"

    for name in ("progress", "registry", "readiness", "queue", "audit"):
        assert _render(getattr(state, name)) == _render(getattr(repeated, name))
