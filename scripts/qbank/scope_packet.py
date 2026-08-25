"""Deterministic, non-LLM preparation of compact scope-chapter context packets.

Retrieves only the data needed to scope-map one Toronto Notes chapter against
the canonical MCC objectives registry, so a downstream LLM session does not
need to load the full TOC inventory or objectives registry into context.
This module makes no medical judgments and assigns no scope classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re

from .errors import QbankError
from .jsonio import read_json
from .paths import resolve_root_path


class ScopePacketError(QbankError):
    """A scope-chapter packet could not be prepared."""


SCHEMA_VERSION = "1.0"
DEFAULT_MAX_CANDIDATES = 60
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "of", "the", "to", "in", "on", "or", "for", "with",
        "by", "at", "as", "is", "are", "be", "its", "it", "this", "that",
        "chapter", "general", "principles", "overview", "approach",
    }
)
_CLASSIFICATION_VALUES = (
    "DIRECT", "COMPONENT", "CROSS_DISCIPLINE", "SUPPORTING_KNOWLEDGE",
    "SPECIALIST_DETAIL", "REFERENCE_ONLY", "UNCERTAIN",
)
_DEPTH_VALUES = (
    "CORE_ACTION", "RECOGNIZE_AND_ACT", "RECOGNIZE", "CONTEXT_ONLY",
    "OUT_OF_SCOPE_DETAIL",
)
_MAPPING_STRENGTH_VALUES = ("STRONG", "MODERATE", "WEAK")
_COVERAGE_WEIGHT_VALUES = (1, 2, 3, 4, 5)


def _normalize_tokens(text: str) -> set[str]:
    if not isinstance(text, str):
        return set()
    return {
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


@dataclass(frozen=True)
class PacketReport:
    chapter_code: str
    source_node_count: int
    candidate_objective_count: int
    explicit_study_smarter_count: int
    unresolved_heading_count: int
    packet_bytes: int
    candidate_set_truncated: bool
    estimated_tokens: int


def _read_object(root: Path, relative: str, *, label: str) -> dict:
    path = resolve_root_path(root, relative, label=label)
    if not path.is_file():
        raise ScopePacketError(f"required source file is missing: {relative}")
    value = read_json(path)
    if not isinstance(value, dict):
        raise ScopePacketError(f"{label} must be a JSON object: {relative}")
    return value


def load_progress_ledger(root: Path) -> dict:
    return _read_object(root, "reports/scope_scaling_progress.json", label="progress ledger")


def chapter_title(ledger: dict, chapter_code: str) -> str:
    names = ledger.get("chapter_names")
    if not isinstance(names, dict) or chapter_code not in names:
        raise ScopePacketError(f"unknown chapter code (not in progress ledger): {chapter_code}")
    return names[chapter_code]


def load_toc_nodes(root: Path) -> list[dict]:
    inventory = _read_object(root, "research/tn2025/toc_inventory.json", label="toc inventory")
    nodes = inventory.get("nodes")
    if not isinstance(nodes, list):
        raise ScopePacketError("toc_inventory.json nodes must be a list")
    return nodes


def select_chapter_nodes(nodes: list[dict], chapter_code: str) -> list[dict]:
    selected = [
        node for node in nodes
        if isinstance(node, dict) and node.get("chapter_code") == chapter_code
    ]
    if not selected:
        raise ScopePacketError(f"no toc_inventory nodes found for chapter: {chapter_code}")
    return selected


def _node_source_summary(node: dict) -> dict:
    return {
        "node_id": node.get("node_id"),
        "parent_id": node.get("parent_id"),
        "title": node.get("title"),
        "level": node.get("level"),
        "structural_type": node.get("structural_type"),
        "start_tn_page": node.get("start_tn_page"),
        "end_tn_page": node.get("end_tn_page"),
        "start_pdf_page": node.get("start_pdf_page"),
        "end_pdf_page": node.get("end_pdf_page"),
        "confidence": node.get("confidence"),
        "extraction_method": node.get("extraction_method"),
        "merged_duplicate_headings": node.get("merged_duplicate_headings"),
    }


def load_unresolved_headings(root: Path, chapter_code: str) -> list[dict]:
    document = _read_object(
        root, "research/tn2025/unresolved_headings.json", label="unresolved headings"
    )
    headings = document.get("unresolved_headings")
    if not isinstance(headings, list):
        raise ScopePacketError("unresolved_headings.json unresolved_headings must be a list")
    return [
        heading for heading in headings
        if isinstance(heading, dict) and heading.get("chapter_code") == chapter_code
    ]


def load_objectives_registry(root: Path) -> list[dict]:
    registry = _read_object(
        root, "research/mcc/objectives_registry.json", label="objectives registry"
    )
    objectives = registry.get("objectives")
    if not isinstance(objectives, list):
        raise ScopePacketError("objectives_registry.json objectives must be a list")
    return objectives


def load_study_smarter(root: Path) -> dict:
    return _read_object(
        root,
        "research/mcc/study_smarter_discipline_mapping.json",
        label="study smarter mapping",
    )


def _objectives_by_legacy_id(objectives: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for objective in objectives:
        legacy_id = objective.get("legacy_id")
        if isinstance(legacy_id, str) and legacy_id:
            index.setdefault(legacy_id, objective)
    return index


def _explicit_study_smarter_rows(
    study_smarter: dict, chapter_tokens: set[str]
) -> list[dict]:
    disciplines = study_smarter.get("disciplines")
    if not isinstance(disciplines, dict):
        return []
    matches: list[dict] = []
    for discipline, rows in disciplines.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = row.get("title_as_printed", "")
            row_tokens = _normalize_tokens(title)
            if row_tokens and (row_tokens & chapter_tokens):
                matches.append(
                    {
                        "discipline": discipline,
                        "title_as_printed": title,
                        "legacy_id": row.get("legacy_id"),
                        "source": row.get("source"),
                        "source_page": row.get("source_page"),
                    }
                )
    return matches


def _candidate_from_objective(
    objective: dict, matched_by: list[str], score: float
) -> dict:
    content = objective.get("content") if isinstance(objective.get("content"), dict) else {}
    excerpt = content.get("key_objectives") or content.get("rationale") or ""
    if isinstance(excerpt, str) and len(excerpt) > 400:
        excerpt = excerpt[:400] + "..."
    return {
        "mcc_id": objective.get("mcc_id"),
        "legacy_id": objective.get("legacy_id"),
        "title": objective.get("title"),
        "role": objective.get("role"),
        "medical_expert_category": objective.get("medical_expert_category"),
        "matched_by": sorted(set(matched_by)),
        "match_score": round(score, 3),
        "relevant_excerpt": excerpt,
        "official_provenance": {
            "official_url": objective.get("official_url"),
            "version": objective.get("version"),
            "legacy_id_verification": objective.get("legacy_id_verification"),
        },
    }


def _build_candidates(
    objectives: list[dict],
    chapter_tokens: set[str],
    explicit_rows: list[dict],
    *,
    max_candidates: int,
) -> tuple[list[dict], bool]:
    by_legacy = _objectives_by_legacy_id(objectives)
    explicit_legacy_ids = {
        row["legacy_id"] for row in explicit_rows if row.get("legacy_id")
    }

    scored: dict[str, dict] = {}

    for legacy_id in explicit_legacy_ids:
        objective = by_legacy.get(legacy_id)
        if objective is None:
            continue
        mcc_id = objective.get("mcc_id")
        scored[mcc_id] = _candidate_from_objective(
            objective, ["STUDY_SMARTER_DISCIPLINE"], score=1.0
        )

    for objective in objectives:
        title_tokens = _normalize_tokens(objective.get("title", ""))
        if not title_tokens:
            continue
        overlap = title_tokens & chapter_tokens
        if not overlap:
            continue
        score = len(overlap) / len(title_tokens)
        if score < 0.3:
            continue
        mcc_id = objective.get("mcc_id")
        if mcc_id in scored:
            scored[mcc_id]["matched_by"] = sorted(
                set(scored[mcc_id]["matched_by"]) | {"TOKEN_OVERLAP"}
            )
            scored[mcc_id]["match_score"] = max(scored[mcc_id]["match_score"], round(score, 3))
        else:
            scored[mcc_id] = _candidate_from_objective(objective, ["TOKEN_OVERLAP"], score)

    # Always-retained: explicit Study Smarter candidates never get pruned.
    always_keep = [
        candidate for candidate in scored.values()
        if "STUDY_SMARTER_DISCIPLINE" in candidate["matched_by"]
    ]
    ranked = sorted(
        (c for c in scored.values() if "STUDY_SMARTER_DISCIPLINE" not in c["matched_by"]),
        key=lambda c: (-c["match_score"], c["mcc_id"] or ""),
    )

    truncated = False
    remaining_budget = max_candidates - len(always_keep)
    if remaining_budget < 0:
        remaining_budget = 0
    if len(ranked) > remaining_budget:
        truncated = True
        ranked = ranked[:remaining_budget]

    combined = always_keep + ranked
    combined.sort(key=lambda c: (-c["match_score"], c["mcc_id"] or ""))
    return combined, truncated


def prepare_chapter_packet(
    root: Path,
    chapter_code: str,
    *,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> tuple[dict, PacketReport]:
    """Build a compact, deterministic scope packet for one TN chapter.

    Retrieval only: no LLM call, no scope classification, no candidate
    objective is implied to be a valid mapping.
    """
    ledger = load_progress_ledger(root)
    title = chapter_title(ledger, chapter_code)

    all_nodes = load_toc_nodes(root)
    chapter_nodes = select_chapter_nodes(all_nodes, chapter_code)
    chapter_nodes_sorted = sorted(chapter_nodes, key=lambda n: n.get("node_id", ""))

    root_node = next(
        (n for n in chapter_nodes_sorted if n.get("node_id") == chapter_code), None
    )
    source_range = {
        "start_tn_page": root_node.get("start_tn_page") if root_node else None,
        "end_tn_page": root_node.get("end_tn_page") if root_node else None,
        "start_pdf_page": root_node.get("start_pdf_page") if root_node else None,
        "end_pdf_page": root_node.get("end_pdf_page") if root_node else None,
    }

    unresolved = load_unresolved_headings(root, chapter_code)
    low_confidence = [
        n for n in chapter_nodes_sorted if n.get("confidence") in ("LOW", "MEDIUM")
    ]

    chapter_tokens: set[str] = {chapter_code.lower()}
    for token in _normalize_tokens(title):
        chapter_tokens.add(token)
    for node in chapter_nodes_sorted:
        chapter_tokens |= _normalize_tokens(node.get("title", ""))

    study_smarter = load_study_smarter(root)
    explicit_rows = _explicit_study_smarter_rows(study_smarter, chapter_tokens)

    objectives = load_objectives_registry(root)
    candidates, truncated = _build_candidates(
        objectives, chapter_tokens, explicit_rows, max_candidates=max_candidates
    )

    packet = {
        "schema_version": SCHEMA_VERSION,
        "chapter": {
            "code": chapter_code,
            "title": title,
            "chapter_source_range": source_range,
        },
        "source_nodes": [_node_source_summary(n) for n in chapter_nodes_sorted],
        "source_quality": {
            "unresolved_headings": unresolved,
            "low_confidence_nodes": [
                {"node_id": n.get("node_id"), "confidence": n.get("confidence")}
                for n in low_confidence
            ],
            "page_precision_note": (
                "page precision is not stored on toc_inventory nodes; assign "
                "page_mapping_precision per study unit during scope mapping"
            ),
        },
        "study_smarter": {"explicit_discipline_rows": explicit_rows},
        "candidate_mcc_objectives": candidates,
        "candidate_set_truncated": truncated,
        "scope_methodology": {
            "classification_values": list(_CLASSIFICATION_VALUES),
            "depth_values": list(_DEPTH_VALUES),
            "mapping_strength_values": list(_MAPPING_STRENGTH_VALUES),
            "coverage_weight_values": list(_COVERAGE_WEIGHT_VALUES),
        },
    }

    payload_bytes = len(json.dumps(packet, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    report = PacketReport(
        chapter_code=chapter_code,
        source_node_count=len(chapter_nodes_sorted),
        candidate_objective_count=len(candidates),
        explicit_study_smarter_count=len(explicit_rows),
        unresolved_heading_count=len(unresolved),
        packet_bytes=payload_bytes,
        candidate_set_truncated=truncated,
        estimated_tokens=payload_bytes // 4,
    )
    return packet, report


def packet_output_path(root: Path, chapter_code: str) -> Path:
    return resolve_root_path(
        root, Path("derived/scope_packets") / f"{chapter_code}.json", label="scope packet output"
    )


def search_objectives(root: Path, query: str, *, limit: int = 20) -> list[dict]:
    """On-demand deterministic full-registry search, for when a packet's
    bounded candidate set is missing the correct objective."""
    objectives = load_objectives_registry(root)
    query_tokens = _normalize_tokens(query)
    if not query_tokens:
        return []
    scored: list[tuple[float, dict]] = []
    for objective in objectives:
        title_tokens = _normalize_tokens(objective.get("title", ""))
        overlap = title_tokens & query_tokens
        if not overlap:
            continue
        score = len(overlap) / max(len(title_tokens), 1)
        scored.append((score, _candidate_from_objective(objective, ["TOKEN_OVERLAP"], score)))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["mcc_id"] or ""))
    return [candidate for _score, candidate in scored[:limit]]
