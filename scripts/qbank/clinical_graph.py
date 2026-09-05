"""The typed clinical contrast graph, projected from already-frozen artifacts.

Every medically meaningful edge here is a deterministic projection of something
the repository already holds and has already independently reviewed: the frozen
stem-anchor layer, the frozen seed enrichment, the twelve validated contrast
edges, and the evidence packets those seeds cite. No clinical relation is
authored in this module, no page is read by a model, and no LLM is called. That
is the whole reason the graph can be trusted at all -- under AGENTS.md model
agreement is not evidence, so a graph that a model wrote would add nothing a
reviewer could lean on.

Two lines are held structurally rather than by documentation:

- A Toronto Notes edge carries ``authority_role = TOPIC_DISCOVERY_SOURCE``. It
  may *propose* a competitor; it may never *justify* one. ``edges_eligible_to_
  justify`` returns only edges that resolve to a dated non-textbook source.
- An unstated context is NULL. Writing "UNKNOWN" into a pregnancy or severity
  context would make an unasked question look answered.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

from .clinical_concepts import (
    build_alias_index,
    build_concept_vocabulary,
    detect_mentions,
    normalize_surface_form,
)
from .errors import QbankError
from .paths import resolve_root_path


class ClinicalGraphError(QbankError):
    """A projection source, an edge, or a traversal request is unusable."""


RELATIONS = (
    "PLAUSIBILITY_ANCHOR",
    "DEFEATED_BY",
    "ANSWERS",
    "CONFUSED_WITH",
    "PRESENTS_WITH",
    "BELONGS_TO",
    "SUPPORTED_BY",
)

AUTHORITY_ROLES = ("TOPIC_DISCOVERY_SOURCE", "CURRENT_CLINICAL_AUTHORITY")

# Populated only where a source artifact actually states them.
CONTEXT_FIELDS = (
    "population",
    "age_range",
    "pregnancy_context",
    "severity_context",
    "temporal_context",
    "jurisdiction",
)

MAX_TRAVERSAL_DEPTH = 3

SEED_PACKS = (
    "research/qgen/generalization/competitive_contrast_seed_pack_r4",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted",
    "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions",
)
CONTRAST_LIBRARY_RELATIVE_PATH = "research/qgen/chapter_global_contrast_library.json"
EVIDENCE_PACKET_RELATIVE_PATHS = (
    "research/qgen/pilot/QGEN-MED-007.acs-chapter-review-pilot-10.evidence.json",
    "research/qgen/pilot/QGEN-MED-007.chapter-review-micro-3.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15_r2.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15_r3.evidence.json",
    "research/qgen/generalization/cross_discipline_generalization_15_r4.evidence.json",
)

# Toronto Notes section headings that carry deterministic clinical structure. The
# differential yield was measured before this was scoped: 89 chunks carry a
# "differential" subheading against 628 for clinical features and 439 for
# etiology, so co-membership of a differential list is a narrow seam and the
# feature sections are the broad one. Both are discovery only.
DIFFERENTIAL_HEADINGS = ("differential",)
PRESENTATION_HEADINGS = ("clinical features", "signs and symptoms", "presentation")

GRAPH_SCHEMA = """
DROP TABLE IF EXISTS edge_provenance;
DROP TABLE IF EXISTS edges;
DROP TABLE IF EXISTS nodes;
DROP TABLE IF EXISTS source_claims;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS learner_decisions;
DROP TABLE IF EXISTS concepts;
DROP TABLE IF EXISTS concept_aliases;
DROP TABLE IF EXISTS concept_mentions;
DROP TABLE IF EXISTS retrieval_cache;
CREATE TABLE nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    label TEXT NOT NULL,
    study_unit_id TEXT,
    chapter_code TEXT,
    provenance TEXT NOT NULL
);
CREATE INDEX nodes_by_type ON nodes(node_type);
CREATE TABLE edges (
    edge_id TEXT PRIMARY KEY,
    source_node TEXT NOT NULL,
    relation TEXT NOT NULL,
    target_node TEXT NOT NULL,
    source_type TEXT NOT NULL,
    authority_role TEXT NOT NULL,
    source_id TEXT,
    page INTEGER,
    tn_node_id TEXT,
    chunk_id TEXT,
    evidence_span_reference TEXT,
    polarity TEXT,
    option_set_archetype TEXT,
    decision_granularity TEXT,
    population TEXT,
    age_range TEXT,
    pregnancy_context TEXT,
    severity_context TEXT,
    temporal_context TEXT,
    jurisdiction TEXT,
    currentness_date TEXT,
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    derivation_rule TEXT NOT NULL,
    derivation_source TEXT NOT NULL,
    content_sha256 TEXT NOT NULL
);
CREATE INDEX edges_by_source ON edges(source_node, relation);
CREATE INDEX edges_by_target ON edges(target_node, relation);
CREATE INDEX edges_by_relation ON edges(relation);
CREATE TABLE edge_provenance (
    edge_id TEXT NOT NULL REFERENCES edges(edge_id),
    claim_id TEXT NOT NULL,
    claim_sha256 TEXT,
    source_id TEXT,
    PRIMARY KEY (edge_id, claim_id)
);
CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    issuing_organization TEXT,
    source_type TEXT,
    authority_class TEXT NOT NULL,
    currentness_date TEXT,
    currentness_status TEXT,
    sha256 TEXT
);
CREATE TABLE source_claims (
    claim_id TEXT PRIMARY KEY,
    source_id TEXT,
    claim_sha256 TEXT,
    transcription_status TEXT,
    packet_relative_path TEXT NOT NULL
);
CREATE TABLE learner_decisions (
    learner_decision_id TEXT PRIMARY KEY,
    decision_granularity TEXT,
    discipline TEXT,
    anchor_study_unit_id TEXT
);
CREATE TABLE concepts (
    concept_id TEXT PRIMARY KEY,
    concept_type TEXT NOT NULL,
    preferred_label TEXT NOT NULL,
    vocabulary_source TEXT NOT NULL,
    provenance TEXT NOT NULL
);
CREATE TABLE concept_aliases (
    normalized_surface_form TEXT NOT NULL,
    concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
    rule TEXT NOT NULL,
    PRIMARY KEY (normalized_surface_form, concept_id)
);
CREATE TABLE concept_mentions (
    concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
    chunk_id TEXT NOT NULL,
    pdf_page INTEGER NOT NULL,
    tn_node_id TEXT,
    subheading TEXT,
    matched_surface_form TEXT NOT NULL,
    PRIMARY KEY (concept_id, chunk_id, matched_surface_form)
);
CREATE INDEX concept_mentions_by_chunk ON concept_mentions(chunk_id);
CREATE TABLE retrieval_cache (
    cache_key TEXT PRIMARY KEY,
    arm TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


def _load(root: Path, relative: str) -> Any:
    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise ClinicalGraphError(f"projection source is unavailable: {relative}")
    return json.loads(path.read_text())


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# --------------------------------------------------------------- authority


def classify_source_authority(source: dict[str, Any]) -> str:
    """Map a packet source onto the design's coarse authority classes.

    Deterministic and stated: an explicit source type decides it, and where the
    packet schema predates that field the issuing organization does. Anything
    that resolves to neither is OTHER, and OTHER never justifies a claim.
    """
    declared = (source.get("source_type") or "").upper()
    organization = (source.get("issuing_organization") or "").upper()
    if "MCC" in declared or "MEDICAL COUNCIL OF CANADA" in organization:
        return "MCC"
    if "CANADIAN" in declared or "CANADA" in organization or "CANADIAN" in organization:
        return "CANADIAN_GUIDELINE"
    if declared:
        return "PEER_REVIEWED"
    return "OTHER"


def _currentness_date(source: dict[str, Any]) -> str | None:
    for field in ("publication_date", "update_date", "retrieval_date"):
        value = source.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def _load_evidence(root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    sources: dict[str, dict[str, Any]] = {}
    claims: dict[str, dict[str, Any]] = {}
    for relative in EVIDENCE_PACKET_RELATIVE_PATHS:
        try:
            packet = _load(root, relative)
        except ClinicalGraphError:
            continue
        for source in packet.get("sources", []):
            source_id = source.get("source_id")
            if not source_id:
                continue
            sources.setdefault(source_id, {
                "source_id": source_id,
                "title": source.get("title") or "",
                "issuing_organization": source.get("issuing_organization"),
                "source_type": source.get("source_type"),
                "authority_class": classify_source_authority(source),
                "currentness_date": _currentness_date(source),
                "currentness_status": source.get("currentness_status"),
                "sha256": source.get("sha256"),
            })
        for claim in packet.get("claims", []):
            claim_id = claim.get("claim_id")
            if not claim_id:
                continue
            references = claim.get("source_refs") or []
            claims.setdefault(claim_id, {
                "claim_id": claim_id,
                "source_id": (references[0] or {}).get("source_id") if references else None,
                "claim_sha256": claim.get("sha256"),
                # Named for what it actually asserts. VERIFIED_COMPLETE means the
                # transcription was checked, not that the statement is true; the
                # repository has been bitten by reading it as truth twice.
                "transcription_status": claim.get("verification_status"),
                "packet_relative_path": relative,
            })
    return sources, claims


def _authority_for_claims(
    claim_ids: Sequence[str],
    claims: dict[str, dict],
    sources: dict[str, dict],
) -> tuple[str, str, str | None, str | None]:
    """Resolve (source_type, authority_role, source_id, currentness_date) for an edge."""
    for claim_id in claim_ids:
        claim = claims.get(claim_id)
        if not claim:
            continue
        source = sources.get(claim.get("source_id") or "")
        if not source:
            continue
        if source["authority_class"] in {"MCC", "CANADIAN_GUIDELINE", "PEER_REVIEWED"} and \
                source["currentness_date"]:
            return (
                source["authority_class"],
                "CURRENT_CLINICAL_AUTHORITY",
                source["source_id"],
                source["currentness_date"],
            )
    return ("REPOSITORY_DERIVED", "TOPIC_DISCOVERY_SOURCE", None, None)


# ------------------------------------------------------------------- build


class _EdgeWriter:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.seen: set[str] = set()

    def add(
        self,
        *,
        source_node: str,
        relation: str,
        target_node: str,
        source_type: str,
        authority_role: str,
        derivation_rule: str,
        derivation_source: str,
        confidence: str,
        verification_status: str,
        claim_ids: Sequence[str] = (),
        **optional: Any,
    ) -> str:
        if relation not in RELATIONS:
            raise ClinicalGraphError(f"undeclared relation: {relation}")
        if authority_role not in AUTHORITY_ROLES:
            raise ClinicalGraphError(f"undeclared authority role: {authority_role}")
        payload = json.dumps(
            {
                "source_node": source_node, "relation": relation,
                "target_node": target_node, "polarity": optional.get("polarity"),
                "derivation_source": derivation_source,
                "option_set_archetype": optional.get("option_set_archetype"),
            },
            sort_keys=True,
        )
        content_sha256 = _sha256(payload)
        edge_id = f"EDG-{content_sha256[:24]}"
        if edge_id in self.seen:
            return edge_id
        self.seen.add(edge_id)
        self.connection.execute(
            "INSERT INTO edges (edge_id, source_node, relation, target_node, source_type,"
            " authority_role, source_id, page, tn_node_id, chunk_id, evidence_span_reference,"
            " polarity, option_set_archetype, decision_granularity, population, age_range,"
            " pregnancy_context, severity_context, temporal_context, jurisdiction,"
            " currentness_date, confidence, verification_status, derivation_rule,"
            " derivation_source, content_sha256)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                edge_id, source_node, relation, target_node, source_type, authority_role,
                optional.get("source_id"), optional.get("page"), optional.get("tn_node_id"),
                optional.get("chunk_id"), optional.get("evidence_span_reference"),
                optional.get("polarity"), optional.get("option_set_archetype"),
                optional.get("decision_granularity"),
                # Context fields are never defaulted. An unasked question stays NULL.
                *[optional.get(field) for field in CONTEXT_FIELDS],
                optional.get("currentness_date"), confidence, verification_status,
                derivation_rule, derivation_source, content_sha256,
            ),
        )
        for claim_id in claim_ids:
            self.connection.execute(
                "INSERT OR IGNORE INTO edge_provenance VALUES (?,?,?,?)",
                (edge_id, claim_id, None, optional.get("source_id")),
            )
        return edge_id


def build_clinical_graph(root: Path, index_path: Path) -> dict[str, Any]:
    """Project the typed contrast graph into the local index database."""
    root = Path(root).resolve()
    connection = sqlite3.connect(index_path)
    connection.executescript(GRAPH_SCHEMA)

    vocabulary = build_concept_vocabulary(root)
    alias_index = build_alias_index(vocabulary)
    sources, claims = _load_evidence(root)

    connection.executemany(
        "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)",
        [
            (s["source_id"], s["title"], s["issuing_organization"], s["source_type"],
             s["authority_class"], s["currentness_date"], s["currentness_status"], s["sha256"])
            for s in sorted(sources.values(), key=lambda row: row["source_id"])
        ],
    )
    connection.executemany(
        "INSERT INTO source_claims VALUES (?,?,?,?,?)",
        [
            (c["claim_id"], c["source_id"], c["claim_sha256"], c["transcription_status"],
             c["packet_relative_path"])
            for c in sorted(claims.values(), key=lambda row: row["claim_id"])
        ],
    )

    for concept in vocabulary["concepts"]:
        connection.execute(
            "INSERT INTO concepts VALUES (?,?,?,?,?)",
            (concept["concept_id"], concept["concept_type"], concept["preferred_label"],
             concept["vocabulary_source"], json.dumps(concept["provenance"], sort_keys=True)),
        )
        connection.execute(
            "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?)",
            (concept["concept_id"], concept["concept_type"], concept["preferred_label"],
             concept["provenance"].get("study_unit_id"),
             concept["provenance"].get("chapter_code"),
             json.dumps(concept["provenance"], sort_keys=True)),
        )
    for surface, entries in alias_index["aliases"].items():
        for entry in entries:
            connection.execute(
                "INSERT OR IGNORE INTO concept_aliases VALUES (?,?,?)",
                (surface, entry["concept_id"], entry["rule"]),
            )

    for row in connection.execute(
        "SELECT study_unit_id, study_unit_title, chapter_code FROM study_units"
    ).fetchall():
        connection.execute(
            "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?)",
            (row[0], "STUDY_UNIT", row[1] or row[0], row[0], row[2], "{}"),
        )
    for row in connection.execute("SELECT mcc_objective_id, title FROM mcc_objectives").fetchall():
        connection.execute(
            "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?)",
            (f"MCC-{row[0]}", "MCC_OBJECTIVE", row[1] or row[0], None, None, "{}"),
        )

    writer = _EdgeWriter(connection)
    _project_seed_relations(root, connection, writer, claims, sources)
    _project_structural_relations(connection, writer)
    _project_contrast_library(root, connection, writer, claims, sources)
    _project_toronto_notes_discovery(connection, writer, alias_index)

    connection.commit()
    counts = {
        "nodes": connection.execute("SELECT count(*) FROM nodes").fetchone()[0],
        "edges": connection.execute("SELECT count(*) FROM edges").fetchone()[0],
        "edges_by_relation": dict(connection.execute(
            "SELECT relation, count(*) FROM edges GROUP BY relation"
        )),
        "edges_with_claim_provenance": connection.execute(
            "SELECT count(DISTINCT edge_id) FROM edge_provenance"
        ).fetchone()[0],
        "concept_mentions": connection.execute(
            "SELECT count(*) FROM concept_mentions"
        ).fetchone()[0],
    }
    connection.close()
    return counts


def _project_seed_relations(root, connection, writer, claims, sources) -> None:
    """PLAUSIBILITY_ANCHOR, DEFEATED_BY and ANSWERS from the frozen seed layers."""
    for base in SEED_PACKS:
        pack = _load(root, f"{base}.json")
        enrichment = _load(root, f"{base}.enrichment.json")
        anchors = _load(root, f"{base}.stem_anchors.json")
        if not (enrichment.get("frozen") and anchors.get("frozen")):
            raise ClinicalGraphError(f"{base} enrichment or anchors are not frozen")
        tags = {seed["seed_id"]: seed for seed in enrichment.get("seeds", [])}
        anchor_rows = {seed["seed_id"]: seed for seed in anchors.get("seeds", [])}
        anchors_source = f"{base}.stem_anchors.json"
        enrichment_source = f"{base}.enrichment.json"

        for target in pack.get("targets", []):
            decision_id = target.get("target_id")
            connection.execute(
                "INSERT OR IGNORE INTO learner_decisions VALUES (?,?,?,?)",
                (decision_id, target.get("decision_granularity"), target.get("discipline"),
                 target.get("anchor_study_unit_id")),
            )
            connection.execute(
                "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?)",
                (decision_id, "LEARNER_DECISION", target.get("learner_decision") or decision_id,
                 target.get("anchor_study_unit_id"), None, "{}"),
            )
            for seed in target.get("seeds", []):
                seed_id = seed["seed_id"]
                tag = tags.get(seed_id)
                if tag is None:
                    continue
                concept_id = seed.get("competitor_concept_id")
                if not concept_id:
                    continue

                plausibility_claims = seed.get("evidence_refs_for_plausibility") or []
                discrimination_claims = seed.get("evidence_refs_for_discrimination") or []
                strength = (seed.get("independent_seed_review") or {}).get("reviewed_strength")

                anchor_row = anchor_rows.get(seed_id)
                if anchor_row:
                    p_type, p_role, p_source, p_date = _authority_for_claims(
                        plausibility_claims, claims, sources
                    )
                    for anchor in anchor_row.get("plausibility_anchors", []):
                        writer.add(
                            source_node=concept_id,
                            relation="PLAUSIBILITY_ANCHOR",
                            target_node=anchor["stem_feature_id"],
                            source_type=p_type,
                            authority_role=p_role,
                            source_id=p_source,
                            currentness_date=p_date,
                            polarity="PRESENT",
                            confidence="HIGH" if strength == "STRONG" else "MEDIUM",
                            verification_status="REVIEWED" if strength else "DERIVED",
                            derivation_rule=f"STEM_ANCHOR_{anchor.get('rule', 'R?')}",
                            derivation_source=anchors_source,
                            claim_ids=plausibility_claims,
                        )

                d_type, d_role, d_source, d_date = _authority_for_claims(
                    discrimination_claims, claims, sources
                )
                for predicate in tag.get("condition_predicates", []):
                    writer.add(
                        source_node=concept_id,
                        relation="DEFEATED_BY",
                        target_node=predicate["stem_feature_id"],
                        source_type=d_type,
                        authority_role=d_role,
                        source_id=d_source,
                        currentness_date=d_date,
                        polarity=predicate["required_polarity"],
                        confidence="HIGH" if strength == "STRONG" else "MEDIUM",
                        verification_status="REVIEWED" if strength else "DERIVED",
                        derivation_rule="ENRICHMENT_CONDITION_PREDICATE",
                        derivation_source=enrichment_source,
                        claim_ids=discrimination_claims,
                    )

                for archetype in tag.get("option_set_archetypes") or []:
                    writer.add(
                        source_node=concept_id,
                        relation="ANSWERS",
                        target_node=decision_id,
                        source_type="REPOSITORY_STRUCTURAL",
                        authority_role="TOPIC_DISCOVERY_SOURCE",
                        option_set_archetype=archetype,
                        decision_granularity=seed.get("competitor_decision_granularity")
                        or target.get("decision_granularity"),
                        confidence="HIGH",
                        verification_status="DERIVED",
                        derivation_rule="ENRICHMENT_ARCHETYPE_TAG",
                        derivation_source=enrichment_source,
                    )

                study_unit = seed.get("competitor_study_unit_id")
                if study_unit:
                    writer.add(
                        source_node=concept_id,
                        relation="BELONGS_TO",
                        target_node=study_unit,
                        source_type="REPOSITORY_STRUCTURAL",
                        authority_role="TOPIC_DISCOVERY_SOURCE",
                        confidence="HIGH",
                        verification_status="DERIVED",
                        derivation_rule="SEED_COMPETITOR_STUDY_UNIT",
                        derivation_source=f"{base}.json",
                    )


def _project_structural_relations(connection, writer) -> None:
    """BELONGS_TO from study units to their MCC objectives."""
    for study_unit, objective in connection.execute(
        "SELECT study_unit_id, mcc_objective_id FROM study_unit_objectives "
        "ORDER BY study_unit_id, mcc_objective_id"
    ).fetchall():
        writer.add(
            source_node=study_unit,
            relation="BELONGS_TO",
            target_node=f"MCC-{objective}",
            source_type="REPOSITORY_STRUCTURAL",
            authority_role="TOPIC_DISCOVERY_SOURCE",
            confidence="HIGH",
            verification_status="VALIDATED",
            derivation_rule="MASTER_SCOPE_MCC_EVIDENCE",
            derivation_source="research/scope/master_scope_crosswalk.json",
        )


def _project_contrast_library(root, connection, writer, claims, sources) -> None:
    """CONFUSED_WITH from the twelve independently validated contrast edges."""
    library = _load(root, CONTRAST_LIBRARY_RELATIVE_PATH)
    for edge in library.get("edges", []):
        claim_ids = [ref["claim_id"] for ref in edge.get("evidence_refs", [])]
        source_type, role, source_id, date = _authority_for_claims(claim_ids, claims, sources)
        anchor = edge.get("anchor") or {}
        pages = (edge.get("contrast") or {}).get("pdf_pages") or [None]
        writer.add(
            source_node=edge["anchor_concept_id"],
            relation="CONFUSED_WITH",
            target_node=edge["contrast_concept_id"],
            source_type=source_type,
            authority_role=role,
            source_id=source_id,
            currentness_date=date,
            page=pages[0] if isinstance(pages, list) else None,
            tn_node_id=(anchor.get("source_node_ids") or [None])[0],
            evidence_span_reference=edge.get("contrast_id"),
            confidence="HIGH" if edge.get("quality_status") == "VALIDATED" else "MEDIUM",
            verification_status="VALIDATED" if edge.get("quality_status") == "VALIDATED"
            else "REVIEWED",
            derivation_rule="VALIDATED_CONTRAST_LIBRARY_EDGE",
            derivation_source=CONTRAST_LIBRARY_RELATIVE_PATH,
            claim_ids=claim_ids,
        )
        for node_id, label, study_unit in (
            (edge["anchor_concept_id"], edge["anchor_concept_id"], anchor.get("study_unit_id")),
            (edge["contrast_concept_id"], edge.get("neighboring_choice")
             or edge["contrast_concept_id"],
             (edge.get("contrast") or {}).get("study_unit_id")),
        ):
            connection.execute(
                "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?)",
                (node_id, "CONDITION", label, study_unit, None, "{}"),
            )


def _project_toronto_notes_discovery(connection, writer, alias_index) -> None:
    """CONFUSED_WITH and PRESENTS_WITH from Toronto Notes' own printed structure.

    Discovery only. Co-membership of one printed differential list is a reason to
    *consider* two conditions together; it is never a reason to assert anything
    clinical, so every edge here is TORONTO_NOTES / TOPIC_DISCOVERY_SOURCE.
    """
    typed = {
        row[0] for row in connection.execute(
            "SELECT concept_id FROM concepts WHERE concept_type IN ('CONDITION','ACTION','TOPIC')"
        )
    }
    rows = connection.execute(
        "SELECT c.chunk_id, c.pdf_page, c.tn_node_id, c.subheading, t.normalized_text_for_search "
        "FROM chunks c JOIN chunk_text t ON t.chunk_id = c.chunk_id "
        "WHERE c.subheading IS NOT NULL ORDER BY c.pdf_page, c.ordinal"
    ).fetchall()

    for chunk_id, page, tn_node_id, subheading, text in rows:
        heading = (subheading or "").lower()
        is_differential = any(key in heading for key in DIFFERENTIAL_HEADINGS)
        is_presentation = any(key in heading for key in PRESENTATION_HEADINGS)
        if not (is_differential or is_presentation):
            continue
        hits = detect_mentions(alias_index, text)
        mentioned = sorted({hit["concept_id"] for hit in hits if hit["concept_id"] in typed})
        for hit in hits:
            connection.execute(
                "INSERT OR IGNORE INTO concept_mentions VALUES (?,?,?,?,?,?)",
                (hit["concept_id"], chunk_id, page, tn_node_id, subheading,
                 hit["matched_surface_form"]),
            )
        if len(mentioned) < 2 or len(mentioned) > 12:
            # A list naming one concept says nothing contrastive; one naming a
            # dozen is a chapter index, not a differential, and would create a
            # clique of meaningless edges.
            continue
        relation = "CONFUSED_WITH" if is_differential else "PRESENTS_WITH"
        rule = ("TN_DIFFERENTIAL_LIST_CO_MEMBERSHIP" if is_differential
                else "TN_PRESENTATION_SECTION_CO_MENTION")
        for index, left in enumerate(mentioned):
            for right in mentioned[index + 1:]:
                writer.add(
                    source_node=left,
                    relation=relation,
                    target_node=right,
                    source_type="TORONTO_NOTES",
                    authority_role="TOPIC_DISCOVERY_SOURCE",
                    page=page,
                    tn_node_id=tn_node_id,
                    chunk_id=chunk_id,
                    evidence_span_reference=f"{tn_node_id}#{chunk_id}",
                    confidence="LOW",
                    verification_status="DERIVED",
                    derivation_rule=rule,
                    derivation_source="derived/tn_index/tn_index.sqlite3",
                )


# --------------------------------------------------------------- retrieval


def edges_eligible_to_justify(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return the edges permitted to justify a candidate-facing clinical claim.

    A Toronto Notes edge is never in this set, however well it reads. That is the
    structural form of the repository's own rule that a 2025 textbook organizes
    topics and does not certify current practice.
    """
    columns = [row[1] for row in connection.execute("PRAGMA table_info(edges)")]
    rows = connection.execute(
        "SELECT * FROM edges WHERE authority_role = 'CURRENT_CLINICAL_AUTHORITY' "
        "AND currentness_date IS NOT NULL AND source_type != 'TORONTO_NOTES' "
        "ORDER BY edge_id"
    ).fetchall()
    return [dict(zip(columns, row)) for row in rows]


def graph_neighbourhood(
    connection: sqlite3.Connection,
    seed_nodes: Sequence[str],
    *,
    max_depth: int = 2,
    relations: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Bounded typed traversal returning the path that produced every node.

    Depth is bounded because unrestricted wandering is how a graph turns "related
    to the topic" into "a plausible option here", which is the exact confusion the
    stem-anchor floor exists to refuse.
    """
    if max_depth < 1 or max_depth > MAX_TRAVERSAL_DEPTH:
        raise ClinicalGraphError(
            f"traversal depth must be between 1 and {MAX_TRAVERSAL_DEPTH}: {max_depth}"
        )
    permitted = tuple(relations) if relations else RELATIONS
    unknown = sorted(set(permitted) - set(RELATIONS))
    if unknown:
        raise ClinicalGraphError(f"undeclared relation in traversal: {', '.join(unknown)}")

    reached: dict[str, dict[str, Any]] = {
        node: {"node_id": node, "depth": 0, "path": []} for node in seed_nodes
    }
    frontier = list(dict.fromkeys(seed_nodes))
    placeholders = ",".join("?" for _ in permitted)
    for depth in range(1, max_depth + 1):
        if not frontier:
            break
        next_frontier: list[str] = []
        for node in frontier:
            rows = connection.execute(
                "SELECT edge_id, relation, target_node, authority_role, source_type "
                "FROM edges WHERE source_node = ? AND relation IN "
                f"({placeholders}) ORDER BY edge_id",
                (node, *permitted),
            ).fetchall()
            rows += connection.execute(
                "SELECT edge_id, relation, source_node, authority_role, source_type "
                "FROM edges WHERE target_node = ? AND relation IN "
                f"({placeholders}) ORDER BY edge_id",
                (node, *permitted),
            ).fetchall()
            for edge_id, relation, other, authority_role, source_type in rows:
                if other in reached:
                    continue
                reached[other] = {
                    "node_id": other,
                    "depth": depth,
                    "path": reached[node]["path"] + [{
                        "edge_id": edge_id, "relation": relation, "from": node,
                        "to": other, "authority_role": authority_role,
                        "source_type": source_type,
                    }],
                }
                next_frontier.append(other)
        frontier = next_frontier
    return {"nodes": reached, "max_depth": max_depth, "relations": list(permitted)}
