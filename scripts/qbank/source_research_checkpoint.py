"""Fail-closed deterministic source-research checkpoint rendering."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Any

from .jsonio import read_json
from .paths import resolve_root_path
from .source_research_coordinator import (
    SourceResearchState,
    build_source_research_state,
    derive_next_source_research_action,
    discover_source_research_workers,
    resolve_git_commit,
    write_validated_source_research_state,
)


RESUME_START = "<!-- SOURCE_RESEARCH_RESUME:START -->"
RESUME_END = "<!-- SOURCE_RESEARCH_RESUME:END -->"
_STATE_PATHS = {
    "registry": "research/qgen/source_document_registry.json",
    "readiness": "research/qgen/generation_source_readiness.json",
    "queue": "research/qgen/generation_queue.json",
    "progress": "reports/source_packet_research_progress.json",
    "audit": "reports/source_research_integration_audit.json",
}


@dataclass(frozen=True)
class SourceResearchCheckpoint:
    state: SourceResearchState
    workers: list[dict[str, Any]]
    next_action: str
    coordinator_input_commit: str


def _resume_bounds(existing: str) -> tuple[int, int]:
    if existing.count(RESUME_START) != 1 or existing.count(RESUME_END) != 1:
        raise ValueError("MEMORY.md source-research resume markers must occur exactly once")
    start = existing.index(RESUME_START) + len(RESUME_START)
    end = existing.index(RESUME_END)
    if end < start:
        raise ValueError("MEMORY.md source-research resume markers are malformed")
    return start, end


def render_memory_source_research_resume(
    existing: str, state: SourceResearchState, workers: list[dict[str, Any]]
) -> str:
    """Replace only the marked resume summary with artifact-derived content."""
    start, end = _resume_bounds(existing)
    progress = state.progress
    readiness = state.readiness["summary"]
    queue = state.queue["summary"]
    next_action = derive_next_source_research_action(progress, state.queue, workers)
    worker_states = [
        f"`{worker.get('batch_id', 'UNKNOWN')}` = {worker['state']}"
        for worker in sorted(workers, key=lambda item: (str(item.get("batch_id", "")), str(item.get("branch", ""))))
    ]
    worker_summary = "; ".join(worker_states) if worker_states else "none"
    block = "\n".join((
        "",
        "## Current phase",
        "",
        "- Current phase: scaled current-Canadian source-packet research.",
        "- Source-packet planning is complete and frozen (`SOURCE_PACKET_PLAN = PASS`).",
        f"- Total planned source packets: {progress['TOTAL_SOURCE_PACKETS']:,}.",
        f"- Source packets READY: {progress['SOURCE_PACKETS_READY']:,}.",
        f"- Source packets PENDING: {progress['SOURCE_PACKETS_PENDING']:,}.",
        f"- Source packets BLOCKED: {progress['SOURCE_PACKETS_BLOCKED']:,}.",
        f"- Source packets INCOMPLETE: {progress['SOURCE_PACKETS_INCOMPLETE']:,}.",
        f"- Total research batches: {progress['RESEARCH_BATCHES_TOTAL']:,}.",
        f"- Research batches complete: {progress['RESEARCH_BATCHES_COMPLETE']:,}.",
        f"- Research batches pending: {progress['RESEARCH_BATCHES_PENDING']:,}.",
        f"- Source documents: {len(state.registry['documents']):,}.",
        f"- Generation jobs total: {readiness['GENERATION_JOBS_TOTAL']:,}.",
        f"- Generation jobs SOURCE_READY: {readiness['GENERATION_JOBS_SOURCE_READY']:,}.",
        f"- Generation jobs PENDING: {readiness['GENERATION_JOBS_PENDING']:,}.",
        f"- Generation jobs BLOCKED: {readiness['GENERATION_JOBS_BLOCKED']:,}.",
        f"- Generation queue jobs: {queue['GENERATION_QUEUE_JOBS']:,}.",
        f"- Worker states: {worker_summary}.",
        "- Canonical checkpoint: current Git HEAD.",
        f"- Audited coordinator input commit: `{state.audit['coordinator_input_commit']}`.",
        f"- Current next action: `{next_action}`.",
        "",
        "## Frozen layers",
        "",
        "- Scope, MCC mapping, ownership, competency-component ownership, discipline routing, question planning, and question-bank targets are complete and frozen.",
        "- Do not reopen a frozen layer unless explicitly authorized or a concrete validator/audit failure requires repair.",
        "",
        "## Canonical question-bank target",
        "",
        "- Final study-bank target: 6,086 questions.",
        "- MED = 1,086.",
        "- PED = 1,000.",
        "- OBGYN = 1,000.",
        "- SURG = 1,000.",
        "- PSY = 1,000.",
        "- PHELO = 1,000.",
        "- MED exactly equals its effective minimum; do not reduce MED minima merely to restore a 1,000-question MED target.",
        "- The separate 230-question MCCQE simulation is not part of the 6,086-question study bank.",
        "",
        "## Blocker and next step",
        "",
        "- No upstream blocker remains. Continue research one bounded canonical wave at a time.",
        f"- NEXT_STEP = `{next_action}`",
        "",
    ))
    return existing[:start] + block + existing[end:]


def _write_text_atomic(path: Path, value: str) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(value)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def checkpoint_source_research(root: Path, coordinator_input_commit: str) -> SourceResearchCheckpoint:
    """Build, validate, render, write, and revalidate one complete checkpoint."""
    root = Path(root).resolve()
    canonical = resolve_git_commit(root, coordinator_input_commit)
    state = build_source_research_state(root, canonical)
    workers = discover_source_research_workers(root, canonical)
    next_action = derive_next_source_research_action(state.progress, state.queue, workers)
    memory_path = resolve_root_path(root, "MEMORY.md", label="source research memory")
    rendered_memory = render_memory_source_research_resume(memory_path.read_text(encoding="utf-8"), state, workers)

    write_validated_source_research_state(root, state)
    _write_text_atomic(memory_path, rendered_memory)

    written_state = build_source_research_state(root, canonical)
    written_workers = discover_source_research_workers(root, canonical)
    written_action = derive_next_source_research_action(written_state.progress, written_state.queue, written_workers)
    for name, relative in _STATE_PATHS.items():
        artifact = read_json(resolve_root_path(root, relative, label="source research checkpoint artifact"))
        if artifact != getattr(written_state, name):
            raise ValueError(f"written source research checkpoint artifact is invalid: {relative}")
    expected_memory = render_memory_source_research_resume(memory_path.read_text(encoding="utf-8"), written_state, written_workers)
    if memory_path.read_text(encoding="utf-8") != expected_memory:
        raise ValueError("written MEMORY.md source-research resume is invalid")
    return SourceResearchCheckpoint(written_state, written_workers, written_action, canonical)
