"""The typed clinical contrast graph and its provenance contract.

Every medically meaningful edge in this graph is projected deterministically from
an artifact that was already frozen and already independently reviewed. No new
clinical relation is authored here, no page is read by a model, and no LLM is
called. The tests below exist to hold three lines that are easy to cross quietly:

- a Toronto Notes edge may propose a competitor and may never justify one;
- an unstated context is NULL, never a plausible-looking default;
- an edge that cannot name where it came from does not get created.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from qbank.clinical_graph import (
    AUTHORITY_ROLES,
    CONTEXT_FIELDS,
    RELATIONS,
    ClinicalGraphError,
    build_clinical_graph,
    edges_eligible_to_justify,
    graph_neighbourhood,
)
from qbank.tn_index import build_tn_index

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "derived/toronto-notes-2025"

pytestmark = pytest.mark.skipif(
    not (CORPUS / "ocr/pages").is_dir(), reason="local Toronto Notes corpus is not present"
)


@pytest.fixture(scope="module")
def graph_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("graph") / "tn_index.sqlite3"
    build_tn_index(ROOT, path)
    build_clinical_graph(ROOT, path)
    return path


@pytest.fixture(scope="module")
def connection(graph_db):
    return sqlite3.connect(graph_db)


# --------------------------------------------------------------- projection


def test_only_declared_relations_are_created(connection):
    relations = {row[0] for row in connection.execute("SELECT DISTINCT relation FROM edges")}
    assert relations <= set(RELATIONS)
    assert "PLAUSIBILITY_ANCHOR" in relations
    assert "DEFEATED_BY" in relations
    assert "ANSWERS" in relations


def test_every_frozen_seed_anchor_becomes_a_plausibility_anchor_edge(connection):
    anchors = json.loads(
        (ROOT / "research/qgen/generalization/"
         "competitive_contrast_seed_pack_r4.stem_anchors.json").read_text()
    )
    expected = sum(len(seed["plausibility_anchors"]) for seed in anchors["seeds"])
    built = connection.execute(
        "SELECT count(*) FROM edges WHERE relation = 'PLAUSIBILITY_ANCHOR' "
        "AND derivation_source = ?",
        ("research/qgen/generalization/competitive_contrast_seed_pack_r4.stem_anchors.json",),
    ).fetchone()[0]
    assert built == expected > 0


def test_a_defeated_by_edge_carries_the_polarity_its_predicate_required(connection):
    polarities = {
        row[0] for row in connection.execute(
            "SELECT DISTINCT polarity FROM edges WHERE relation = 'DEFEATED_BY'"
        )
    }
    assert polarities and polarities <= {"PRESENT", "ABSENT"}


def test_answers_edges_carry_the_full_decision_triple(connection):
    rows = list(connection.execute(
        "SELECT option_set_archetype, decision_granularity, target_node "
        "FROM edges WHERE relation = 'ANSWERS'"
    ))
    assert rows
    for archetype, granularity, decision in rows:
        assert archetype and granularity and decision


# ------------------------------------------------------- provenance contract


def test_every_edge_carries_the_whole_provenance_contract(connection):
    columns = {row[1] for row in connection.execute("PRAGMA table_info(edges)")}
    for required in (
        "edge_id", "source_node", "relation", "target_node", "source_type",
        "authority_role", "polarity", "confidence", "verification_status",
        "derivation_rule", "derivation_source", "content_sha256",
    ):
        assert required in columns, required
    incomplete = connection.execute(
        "SELECT count(*) FROM edges WHERE edge_id IS NULL OR source_node IS NULL "
        "OR relation IS NULL OR target_node IS NULL OR authority_role IS NULL "
        "OR derivation_rule IS NULL OR content_sha256 IS NULL"
    ).fetchone()[0]
    assert incomplete == 0


def test_edge_ids_are_content_addressed_and_unique(connection):
    total, distinct = connection.execute(
        "SELECT count(*), count(DISTINCT edge_id) FROM edges"
    ).fetchone()
    assert total == distinct > 0


def test_authority_role_is_always_one_of_the_two_declared_roles(connection):
    roles = {row[0] for row in connection.execute("SELECT DISTINCT authority_role FROM edges")}
    assert roles <= set(AUTHORITY_ROLES)


def test_unstated_context_is_null_and_never_an_invented_default(connection):
    for field in CONTEXT_FIELDS:
        values = {
            row[0] for row in connection.execute(f"SELECT DISTINCT {field} FROM edges")
        }
        assert "UNKNOWN" not in values, field
        assert "" not in values, field
        assert "N/A" not in values, field


def test_every_toronto_notes_edge_is_a_discovery_source(connection):
    leaked = connection.execute(
        "SELECT count(*) FROM edges WHERE source_type = 'TORONTO_NOTES' "
        "AND authority_role != 'TOPIC_DISCOVERY_SOURCE'"
    ).fetchone()[0]
    assert leaked == 0


# ------------------------------------------------------------ authority rule


def test_a_discovery_edge_may_propose_a_competitor_but_never_justify_one(connection):
    proposed = connection.execute(
        "SELECT count(*) FROM edges WHERE authority_role = 'TOPIC_DISCOVERY_SOURCE'"
    ).fetchone()[0]
    assert proposed > 0
    justifying = edges_eligible_to_justify(connection)
    assert all(row["authority_role"] == "CURRENT_CLINICAL_AUTHORITY" for row in justifying)


def test_an_edge_supported_only_by_toronto_notes_cannot_justify_a_claim(connection):
    justifying_ids = {row["edge_id"] for row in edges_eligible_to_justify(connection)}
    discovery_ids = {
        row[0] for row in connection.execute(
            "SELECT edge_id FROM edges WHERE source_type = 'TORONTO_NOTES'"
        )
    }
    assert not (justifying_ids & discovery_ids)


def test_a_justifying_edge_resolves_to_a_dated_source(connection):
    for row in edges_eligible_to_justify(connection):
        assert row["currentness_date"], row["edge_id"]


# --------------------------------------------------------------- traversal


def test_graph_neighbourhood_honours_its_depth_bound(connection):
    seeds = [row[0] for row in connection.execute(
        "SELECT DISTINCT source_node FROM edges WHERE relation = 'PLAUSIBILITY_ANCHOR' LIMIT 1"
    )]
    shallow = graph_neighbourhood(connection, seeds, max_depth=1)
    deep = graph_neighbourhood(connection, seeds, max_depth=2)
    assert len(shallow["nodes"]) <= len(deep["nodes"])
    assert all(len(node["path"]) <= 1 for node in shallow["nodes"].values())
    assert all(len(node["path"]) <= 2 for node in deep["nodes"].values())


def test_unrestricted_wandering_is_refused(connection):
    with pytest.raises(ClinicalGraphError):
        graph_neighbourhood(connection, ["SF-C21-TROPONIN-RISE-OR-FALL"], max_depth=9)


def test_every_reached_node_reports_the_path_that_produced_it(connection):
    seeds = [row[0] for row in connection.execute(
        "SELECT DISTINCT source_node FROM edges WHERE relation = 'PLAUSIBILITY_ANCHOR' LIMIT 3"
    )]
    reached = graph_neighbourhood(connection, seeds, max_depth=2)
    for node_id, node in reached["nodes"].items():
        if node_id in seeds:
            continue
        assert node["path"], node_id
        for step in node["path"]:
            assert step["relation"] in RELATIONS
            assert step["edge_id"]


def test_traversal_is_restricted_to_the_declared_relation_set(connection):
    seeds = [row[0] for row in connection.execute(
        "SELECT DISTINCT source_node FROM edges WHERE relation = 'ANSWERS' LIMIT 2"
    )]
    reached = graph_neighbourhood(
        connection, seeds, max_depth=2, relations=("CONFUSED_WITH",)
    )
    for node in reached["nodes"].values():
        for step in node["path"]:
            assert step["relation"] == "CONFUSED_WITH"


# ------------------------------------------------------------------ hygiene


def test_the_graph_stores_no_toronto_notes_prose_in_an_edge(connection):
    long_values = connection.execute(
        "SELECT count(*) FROM edges WHERE length(evidence_span_reference) > 300"
    ).fetchone()[0]
    assert long_values == 0


def test_rebuilding_the_graph_is_idempotent(graph_db):
    connection = sqlite3.connect(graph_db)
    before = [row[0] for row in connection.execute("SELECT edge_id FROM edges ORDER BY edge_id")]
    connection.close()
    build_clinical_graph(ROOT, graph_db)
    connection = sqlite3.connect(graph_db)
    after = [row[0] for row in connection.execute("SELECT edge_id FROM edges ORDER BY edge_id")]
    assert before == after
