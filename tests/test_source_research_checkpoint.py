from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
from pathlib import Path

import pytest

from qbank.source_research_checkpoint import (
    RESUME_END,
    RESUME_START,
    checkpoint_source_research,
    derive_next_source_research_action,
    render_memory_source_research_resume,
)
from qbank.source_research_coordinator import (
    build_source_research_state,
    discover_source_research_workers,
    resolve_git_commit,
)


REPO = Path(__file__).resolve().parents[1]


def _progress(*, pending: int = 0, blocked: int = 0) -> dict[str, int]:
    return {
        "SOURCE_PACKETS_PENDING": pending,
        "SOURCE_PACKETS_BLOCKED": blocked,
    }


def _queue(*, jobs: int = 0) -> dict[str, object]:
    return {"summary": {"GENERATION_QUEUE_JOBS": jobs}, "jobs": [{}] * jobs}


def test_next_action_priority_is_awaiting_then_retry_then_source_ready_then_pending_then_blocked() -> None:
    workers = [{"state": "AWAITING_INTEGRATION"}, {"state": "RETRY_RESUME"}]
    assert derive_next_source_research_action(_progress(pending=1), _queue(jobs=1), workers) == "INTEGRATE_SOURCE_RESEARCH_WORKERS"
    assert derive_next_source_research_action(_progress(pending=1), _queue(jobs=1), [{"state": "RETRY_RESUME"}]) == "RESUME_SOURCE_RESEARCH_BATCH"
    assert derive_next_source_research_action(_progress(pending=1), _queue(jobs=1), []) == "PLAN_SOURCE_READY_GENERATION"
    assert derive_next_source_research_action(_progress(pending=1), _queue(), []) == "CONTINUE_SOURCE_PACKET_RESEARCH"
    assert derive_next_source_research_action(_progress(blocked=1), _queue(), []) == "RESOLVE_SOURCE_PACKET_BLOCKERS"
    assert derive_next_source_research_action(_progress(), _queue(), []) == "SOURCE_RESEARCH_COMPLETE"


def test_memory_renderer_changes_only_marked_resume_sections() -> None:
    state = build_source_research_state(REPO, resolve_git_commit(REPO, "HEAD"))
    existing = f"before\n{RESUME_START}\nold\n{RESUME_END}\nafter\n"

    rendered = render_memory_source_research_resume(existing, state, [])

    assert rendered.startswith(f"before\n{RESUME_START}\n")
    assert rendered.endswith(f"{RESUME_END}\nafter\n")
    assert "old" not in rendered


def test_memory_renderer_uses_artifact_counts_and_current_head_checkpoint_marker() -> None:
    state = build_source_research_state(REPO, resolve_git_commit(REPO, "HEAD"))
    existing = f"{RESUME_START}\nold\n{RESUME_END}\n"

    rendered = render_memory_source_research_resume(existing, state, [])

    assert "Source packets READY: 90." in rendered
    assert "Source packets PENDING: 1,434." in rendered
    assert "Research batches complete: 10." in rendered
    assert "Research batches pending: 149." in rendered
    assert "Source documents: 75." in rendered
    assert "Generation jobs SOURCE_READY: 11." in rendered
    assert "Generation queue jobs: 11." in rendered
    assert "Canonical checkpoint: current Git HEAD." in rendered
    assert state.audit["coordinator_input_commit"] in rendered
    assert "Current next action: `PLAN_SOURCE_READY_GENERATION`." in rendered


def test_memory_renderer_uses_counts_from_state_artifacts() -> None:
    state = build_source_research_state(REPO, resolve_git_commit(REPO, "HEAD"))
    progress = deepcopy(state.progress)
    readiness = deepcopy(state.readiness)
    queue = deepcopy(state.queue)
    registry = deepcopy(state.registry)
    progress.update({"SOURCE_PACKETS_READY": 71, "SOURCE_PACKETS_PENDING": 1453})
    readiness["summary"]["GENERATION_JOBS_SOURCE_READY"] = 1
    readiness["summary"]["GENERATION_JOBS_PENDING"] = 219
    queue["summary"]["GENERATION_QUEUE_JOBS"] = 1
    queue["jobs"] = [{"job_id": "derived-test"}]
    registry["documents"].append({"document_id": "derived-test"})

    rendered = render_memory_source_research_resume(
        f"{RESUME_START}\nold\n{RESUME_END}\n",
        replace(state, progress=progress, readiness=readiness, queue=queue, registry=registry),
        [],
    )

    assert "Source packets READY: 71." in rendered
    assert "Source packets PENDING: 1,453." in rendered
    assert "Source documents: 76." in rendered
    assert "Generation jobs SOURCE_READY: 1." in rendered
    assert "Generation queue jobs: 1." in rendered


def test_memory_renderer_rejects_malformed_markers() -> None:
    state = build_source_research_state(REPO, resolve_git_commit(REPO, "HEAD"))

    with pytest.raises(ValueError, match="markers"):
        render_memory_source_research_resume("no markers\n", state, [])


def test_checkpoint_command_is_idempotent_and_fails_before_write_on_invalid_state(monkeypatch: pytest.MonkeyPatch) -> None:
    memory = REPO / "MEMORY.md"
    before = memory.read_bytes()

    def invalid_state(*_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid state")

    monkeypatch.setattr("qbank.source_research_checkpoint.build_source_research_state", invalid_state)
    with pytest.raises(ValueError, match="invalid state"):
        checkpoint_source_research(REPO, "HEAD")
    assert memory.read_bytes() == before

    monkeypatch.undo()
    first = checkpoint_source_research(REPO, "HEAD")
    snapshot = {
        path: path.read_bytes()
        for path in (
            REPO / "MEMORY.md",
            REPO / "research/qgen/source_document_registry.json",
            REPO / "research/qgen/generation_source_readiness.json",
            REPO / "research/qgen/generation_queue.json",
            REPO / "reports/source_packet_research_progress.json",
            REPO / "reports/source_research_integration_audit.json",
        )
    }
    second = checkpoint_source_research(REPO, "HEAD")

    assert first.next_action == second.next_action == "PLAN_SOURCE_READY_GENERATION"
    assert snapshot == {path: path.read_bytes() for path in snapshot}


def test_fresh_session_contract_is_reconstructible_from_repo_and_git_state() -> None:
    canonical = resolve_git_commit(REPO, "HEAD")
    state = build_source_research_state(REPO, canonical)
    workers = discover_source_research_workers(REPO, canonical)

    assert derive_next_source_research_action(state.progress, state.queue, workers) == "PLAN_SOURCE_READY_GENERATION"
