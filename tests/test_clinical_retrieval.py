"""BM25, graph and hybrid retrieval, and the low-token context packet.

The load-bearing property under test is that no arm gets its own copy of the
safety layers. Every arm builds candidate rows and then hands them to the same
retrieve_profile_aware_contrasts the production wave uses, so the validated
stem-anchor floor and the ADM-3 second-key ceiling are the same code in all four
arms rather than four reimplementations that could drift apart.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from qbank.clinical_retrieval import (
    ARMS,
    ClinicalRetrievalError,
    build_bm25_rows,
    build_context_packet,
    build_graph_rows,
    build_query,
    retrieve_competitors,
)
from qbank.clinical_graph import build_clinical_graph
from qbank.tn_index import build_tn_index

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "derived/toronto-notes-2025"

pytestmark = pytest.mark.skipif(
    not (CORPUS / "ocr/pages").is_dir(), reason="local Toronto Notes corpus is not present"
)

PLAN = {
    entry["opportunity_label"]: entry
    for entry in json.loads(
        (ROOT / "research/qgen/safe_yield/g2_profile_pilot.wave_plan.json").read_text()
    )["plan"]
}
OPPORTUNITIES = {
    row["wave_label"]: row
    for row in json.loads(
        (ROOT / "research/qgen/safe_yield/g2_profile_pilot.opportunities.json").read_text()
    )["opportunities"]
}


@pytest.fixture(scope="module")
def database(tmp_path_factory):
    path = tmp_path_factory.mktemp("retrieval") / "tn_index.sqlite3"
    build_tn_index(ROOT, path)
    build_clinical_graph(ROOT, path)
    return path


@pytest.fixture(scope="module")
def connection(database):
    return sqlite3.connect(database)


def scenario(label="G2-MED-01"):
    opportunity = OPPORTUNITIES[label]
    return {
        "wave_label": label,
        "discipline_profile_id": opportunity["discipline_profile_id"],
        "item_archetype": opportunity["item_archetype"],
        "option_set_archetype": opportunity["option_set_archetype"],
        "learner_decision_id": opportunity["learner_decision_id"],
        "anchor_study_unit_id": opportunity["anchor_study_unit_id"],
        "stem_feature_map": {"features": PLAN[label]["stem_feature_map"]},
    }


# ----------------------------------------------------------------- queries


def test_a_query_is_built_only_from_canonical_opportunity_data():
    query = build_query(scenario())
    assert query["present_feature_ids"]
    assert all(term for term in query["terms"])
    assert query["anchor_study_unit_id"] == "SU-C-21"
    assert "match_expression" in query


def test_the_same_opportunity_always_produces_the_same_query():
    assert build_query(scenario()) == build_query(scenario())


def test_a_query_never_uses_the_key_or_any_authored_option():
    query = build_query(scenario())
    serialized = json.dumps(query).lower()
    for leaked in ("nstemi", "correct answer", "key"):
        assert f'"{leaked}"' not in serialized


# ------------------------------------------------------------ candidate rows


def test_bm25_rows_carry_their_chunk_and_page_provenance(connection):
    rows = build_bm25_rows(connection, scenario(), limit=40)
    assert rows
    for row in rows:
        assert row["retrieval_provenance"]["arm"] == "BM25"
        hits = row["retrieval_provenance"]["text_hits"]
        assert hits
        for hit in hits:
            assert hit["chunk_id"].startswith("TNC-")
            assert isinstance(hit["pdf_page"], int)


def test_graph_rows_carry_the_typed_path_that_produced_them(connection):
    rows = build_graph_rows(connection, scenario(), max_depth=2)
    assert rows
    for row in rows:
        paths = row["retrieval_provenance"]["graph_paths"]
        assert paths
        for step in paths[0]:
            assert step["relation"]
            assert step["edge_id"].startswith("EDG-")


def test_an_untyped_discovery_is_reported_rather_than_dressed_up_as_a_competitor(connection):
    rows = build_bm25_rows(connection, scenario(), limit=40)
    untyped = [row for row in rows if row["typing_state"] == "DISCOVERED_BUT_UNTYPED"]
    for row in untyped:
        assert row["plausibility_anchor_feature_ids"] == []
        assert row["condition_predicates"] == []
        assert row["response_class_tokens"] == []


# ----------------------------------------------------------- shared filters


@pytest.mark.parametrize("arm", ARMS)
def test_every_arm_routes_through_the_same_floor_and_ceiling(connection, arm):
    result = retrieve_competitors(connection, scenario(), arm=arm)
    rules = {row["rule"] for row in result["retrieval"]["excluded"]}
    assert rules <= {"ADM_1", "ADM_3", "SAF_1"}
    for competitor in result["retrieval"]["ranked_competitors"]:
        assert competitor["anchors_present"] >= 1
        assert competitor["satisfied_conditions"] < competitor["total_conditions"] or \
            competitor["total_conditions"] == 0


@pytest.mark.parametrize("arm", ARMS)
def test_no_arm_can_return_a_second_key(connection, arm):
    result = retrieve_competitors(connection, scenario(), arm=arm)
    for competitor in result["retrieval"]["ranked_competitors"]:
        if competitor["total_conditions"]:
            assert competitor["satisfied_conditions"] != competitor["total_conditions"]


@pytest.mark.parametrize("arm", ARMS)
def test_no_arm_can_return_an_anchorless_competitor(connection, arm):
    result = retrieve_competitors(connection, scenario(), arm=arm)
    for competitor in result["retrieval"]["ranked_competitors"]:
        assert competitor["anchors_present"] > 0


def test_the_current_library_arm_reproduces_the_frozen_g2_result(connection):
    """Arm A must be today's behaviour exactly, or it is not a baseline."""
    frozen = {
        row["wave_label"]: row for row in json.loads(
            (ROOT / "reports/qgen_g2_stem_anchor_retest_execution.json").read_text()
        )["results"]
    }
    for label in ("G2-MED-01", "G2-MED-04", "G2-PHELO-01"):
        result = retrieve_competitors(connection, scenario(label), arm="CURRENT_LIBRARY")
        expected = frozen[label]["retrieval"]["ranked_seed_ids"]
        assert result["retrieval"]["ranked_seed_ids"] == expected, label


def test_component_scores_are_preserved_and_not_averaged_away(connection):
    result = retrieve_competitors(connection, scenario(), arm="HYBRID")
    for competitor in result["retrieval"]["ranked_competitors"]:
        components = competitor["component_scores"]
        for dimension in (
            "decision_match", "archetype_match", "granularity_match",
            "stem_anchor_support", "text_relevance", "graph_relation_strength",
            "source_confidence", "second_key_risk",
        ):
            assert dimension in components


def test_an_unknown_arm_fails_closed(connection):
    with pytest.raises(ClinicalRetrievalError):
        retrieve_competitors(connection, scenario(), arm="VIBES")


# --------------------------------------------------------------- packet


def test_the_context_packet_is_bounded_and_carries_no_raw_chunk_dumps(connection):
    result = retrieve_competitors(connection, scenario(), arm="HYBRID")
    packet = build_context_packet(connection, scenario(), result)
    payload = {key: value for key, value in packet.items() if key != "size"}
    serialized = json.dumps(packet)
    assert packet["size"]["characters"] == len(json.dumps(payload, sort_keys=True))
    assert packet["size"]["measured_over"].startswith("PACKET_PAYLOAD")
    assert packet["size"]["words"] > 0
    assert len(packet["competitors"]) <= 6
    assert "chunk_text" not in serialized
    for competitor in packet["competitors"]:
        assert "text" not in competitor


def test_the_packet_reports_its_own_measured_size_rather_than_an_estimate(connection):
    result = retrieve_competitors(connection, scenario(), arm="HYBRID")
    packet = build_context_packet(connection, scenario(), result)
    assert packet["size"]["measurement"] == "MEASURED"
    assert "tokens" not in packet["size"] or packet["size"]["tokens"] is None
