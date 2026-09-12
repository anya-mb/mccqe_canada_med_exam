from __future__ import annotations

import sqlite3

import pytest

from scripts.qbank.contrast_supply_v3 import (
    V3_CANDIDATE_BUDGET,
    build_global_candidate_catalogue,
    build_append_only_cache,
    discover_global_typed_candidates,
    select_transfer_12,
)


def _eligible_rows():
    rows = []
    for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"):
        for number in range(1, 5):
            rows.append(
                {
                    "development_id": f"RDY-{discipline}-{number:02d}",
                    "discipline": discipline,
                    "study_unit_id": f"SU-{discipline}-{number:02d}",
                    "learner_decision_id": f"LD-{discipline}-{number:02d}",
                    "learner_decision": f"Decision {discipline} {number}",
                    "audit_verdict": "ALIGNED_COMPLETE",
                }
            )
    return rows


def test_transfer_selection_is_balanced_deterministic_and_outcome_blind():
    rows = _eligible_rows()
    maps = [{"development_id": row["development_id"]} for row in rows]
    selected = select_transfer_12(
        rows,
        maps,
        excluded_ids={f"RDY-{d}-01" for d in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")},
    )
    assert [row["development_id"] for row in selected] == [
        f"RDY-{discipline}-{number:02d}"
        for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
        for number in (2, 3)
    ]
    assert all("cache" not in key.lower() and "candidate" not in key.lower()
               for row in selected for key in row)


def test_transfer_selection_fails_closed_when_a_discipline_has_fewer_than_two():
    rows = [row for row in _eligible_rows() if not (
        row["discipline"] == "PED" and row["development_id"] != "RDY-PED-01"
    )]
    maps = [{"development_id": row["development_id"]} for row in rows]
    with pytest.raises(ValueError, match="PED"):
        select_transfer_12(rows, maps, excluded_ids=set())


def _catalogue_db():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE study_units(study_unit_id TEXT PRIMARY KEY, chapter_code TEXT,
          study_unit_title TEXT, classification TEXT, scope_depth TEXT,
          tn_page_range TEXT, start_pdf_page INTEGER, end_pdf_page INTEGER);
        CREATE TABLE chunks(chunk_id TEXT PRIMARY KEY, document_id TEXT, chapter_code TEXT,
          tn_node_id TEXT, section_path TEXT, subheading TEXT, pdf_page INTEGER,
          tn_page_label TEXT, ordinal INTEGER, block_kinds TEXT, text_sha256 TEXT,
          char_count INTEGER);
        CREATE TABLE chunk_study_units(chunk_id TEXT, study_unit_id TEXT);
        CREATE TABLE concepts(concept_id TEXT PRIMARY KEY, concept_type TEXT,
          preferred_label TEXT, vocabulary_source TEXT, provenance TEXT);
        CREATE TABLE concept_mentions(concept_id TEXT, chunk_id TEXT, pdf_page INTEGER,
          tn_node_id TEXT, subheading TEXT, matched_surface_form TEXT);
        """
    )
    connection.executemany(
        "INSERT INTO study_units VALUES (?,?,?,?,?,?,?,?)",
        [("SU-A", "C", "Alpha", "IN_SCOPE", "CORE", "1", 1, 2),
         ("SU-B", "P", "Beta", "IN_SCOPE", "CORE", "3", 3, 4)],
    )
    connection.executemany(
        "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [("CH-1", "D", "C", "C.S1", "Cardiology > Investigations > Transthoracic Echocardiography", "Investigations", 1, "1", 1, "heading", "x", 20),
         ("CH-2", "D", "P", "P.S1", "Pediatrics > Diabetes > HbA1c", "HbA1c", 3, "3", 1, "heading", "y", 8),
         ("CH-3", "D", "P", "P.S1", "Pediatrics > Diabetes > Figure 4. Treatment", "Figure 4. Treatment", 3, "3", 2, "caption", "z", 120)],
    )
    connection.executemany("INSERT INTO chunk_study_units VALUES (?,?)", [("CH-1", "SU-A"), ("CH-2", "SU-B"), ("CH-3", "SU-B")])
    connection.executemany(
        "INSERT INTO concepts VALUES (?,?,?,?,?)",
        [("CON-TTE", "INVESTIGATION", "Transthoracic Echocardiography", "canonical", "p"),
         ("CON-HBA1C", "INVESTIGATION", "HbA1c", "canonical", "p"),
         ("CON-GENERIC", "HEADING", "Treatment", "canonical", "p")],
    )
    connection.executemany(
        "INSERT INTO concept_mentions VALUES (?,?,?,?,?,?)",
        [("CON-TTE", "CH-1", 1, "C.S1", "Investigations", "TTE"),
         ("CON-HBA1C", "CH-2", 3, "P.S1", "HbA1c", "HbA1c"),
         ("CON-GENERIC", "CH-3", 3, "P.S1", "Figure 4. Treatment", "Treatment")],
    )
    return connection


def test_catalogue_excludes_generic_fragments_and_preserves_provenance():
    catalogue = build_global_candidate_catalogue(_catalogue_db(), reviewed_identities=[
        {"candidate_id": "CON-AOM", "normalized_label": "Otitis media with effusion",
         "aliases": ["OME"], "response_classes": ["PLAUSIBLE_DIAGNOSTIC_ENTITY"],
         "decision_granularities": ["DIAGNOSIS"], "provenance": [{"source": "reviewed"}]}
    ])
    labels = {row["normalized_label"] for row in catalogue}
    assert "Treatment" not in labels
    assert not any(label.startswith("Figure") for label in labels)
    assert {"Transthoracic Echocardiography", "HbA1c", "Otitis media with effusion"} <= labels
    assert next(row for row in catalogue if row["canonical_candidate_id"] == "CON-TTE")["provenance"]


def test_catalogue_merges_aliases_but_preserves_parent_subtype_metadata():
    catalogue = build_global_candidate_catalogue(_catalogue_db(), reviewed_identities=[
        {"candidate_id": "CON-TTE", "normalized_label": "Transthoracic Echocardiography",
         "aliases": ["TTE"], "parent_candidate_id": "CON-ECHO",
         "response_classes": ["STRUCTURAL"], "decision_granularities": ["DIAGNOSTIC_TEST"],
         "provenance": [{"source": "reviewed"}]}
    ])
    tte = next(row for row in catalogue if row["canonical_candidate_id"] == "CON-TTE")
    assert "TTE" in tte["aliases"]
    assert tte["parent_candidate_id"] == "CON-ECHO"
    assert len([row for row in catalogue if row["canonical_candidate_id"] == "CON-TTE"]) == 1


def test_catalogue_keeps_independently_reviewed_canonical_label_with_slash():
    catalogue = build_global_candidate_catalogue(_catalogue_db(), reviewed_identities=[
        {"candidate_id": "CON-HBA1C-REVIEWED",
         "normalized_label": "Confirm diagnosis via HbA1c / standard criteria",
         "aliases": [], "response_classes": ["DIAGNOSTIC_ORDER"],
         "decision_granularities": ["SINGLE_NEXT_ACTION"],
         "provenance": [{"source": "independent-review"}]},
    ])
    assert any(row["canonical_candidate_id"] == "CON-HBA1C-REVIEWED" for row in catalogue)


def test_v3_discovers_global_typed_candidates_without_locality_ceiling():
    catalogue = build_global_candidate_catalogue(_catalogue_db(), reviewed_identities=[
        {"candidate_id": "CON-TTE", "normalized_label": "Transthoracic Echocardiography",
         "aliases": ["TTE"], "response_classes": ["STRUCTURAL"],
         "decision_granularities": ["DIAGNOSTIC_TEST"], "semantic_families": ["imaging"],
         "provenance": [{"source": "reviewed"}]},
        {"candidate_id": "CON-HBA1C", "normalized_label": "HbA1c",
         "aliases": [], "response_classes": ["DIAGNOSTIC_ORDER"],
         "decision_granularities": ["SINGLE_NEXT_ACTION"], "semantic_families": ["diabetes"],
         "provenance": [{"source": "reviewed"}]},
    ])
    found = discover_global_typed_candidates(
        catalogue,
        opportunity={"study_unit_id": "SU-OTHER", "chapter_code": "X",
                     "demanded_response_class": "STRUCTURAL",
                     "decision_granularity": "DIAGNOSTIC_TEST",
                     "semantic_families": ["imaging"], "key_aliases": ["Chest ultrasound"]},
    )
    assert found[0]["canonical_candidate_id"] == "CON-TTE"
    assert found[0]["cross_study_unit"] is True
    assert len(found) <= V3_CANDIDATE_BUDGET == 10
    assert all(row["normalized_label"] != "Treatment" for row in found)


def test_v3_excludes_wrong_response_class_and_key_alias():
    catalogue = build_global_candidate_catalogue(_catalogue_db(), reviewed_identities=[])
    found = discover_global_typed_candidates(
        catalogue,
        opportunity={"study_unit_id": "SU-B", "chapter_code": "P",
                     "demanded_response_class": "DIAGNOSTIC_ORDER",
                     "decision_granularity": "SINGLE_NEXT_ACTION",
                     "semantic_families": [], "key_aliases": ["HbA1c"]},
    )
    assert found == []


def test_v3_generic_response_class_accepts_specific_token_on_same_closed_axis():
    catalogue = [{
        "canonical_candidate_id": "CON-DX", "normalized_label": "Specific diagnosis",
        "aliases": [], "study_unit_ids": ["SU-X"], "chapters": ["X"],
        "semantic_families": [], "response_classes": ["LOCALIZED_INFLAMMATION"],
        "decision_granularities": ["DIAGNOSIS"], "provenance": [{"source": "reviewed"}],
    }]
    found = discover_global_typed_candidates(
        catalogue,
        opportunity={"study_unit_id": "SU-Y", "chapter_code": "Y",
                     "demanded_response_class": "PLAUSIBLE_DIAGNOSTIC_ENTITY",
                     "decision_granularity": "DIAGNOSIS", "key_aliases": []},
    )
    assert [row["canonical_candidate_id"] for row in found] == ["CON-DX"]


def test_v3_does_not_reject_reviewed_synonymous_slash_label_as_structural_ambiguity():
    found = discover_global_typed_candidates(
        [{"canonical_candidate_id": "CON-ADH", "normalized_label": "Serum ADH / central-DI evaluation",
          "aliases": [], "study_unit_ids": ["SU-X"], "chapters": ["X"],
          "semantic_families": [], "response_classes": ["DIAGNOSTIC_ORDER"],
          "decision_granularities": ["SINGLE_NEXT_ACTION"],
          "provenance": [{"source": "REUSABLE_CONTRAST_CACHE_V1"}]}],
        opportunity={"study_unit_id": "SU-Y", "chapter_code": "Y",
                     "demanded_response_class": "DIAGNOSTIC_ORDER",
                     "decision_granularity": "SINGLE_NEXT_ACTION", "key_aliases": []},
    )
    assert [row["canonical_candidate_id"] for row in found] == ["CON-ADH"]


def test_append_only_cache_preserves_parent_and_admits_only_approved_anchored_additions():
    parent = {"content_sha256": "a" * 64, "entries": {"old": {"seed_id": "OLD"}}}
    cache = build_append_only_cache(parent, [{"cache_key": "new", "seed_id": "NEW",
        "review_status": "APPROVED", "anchor_id": "ANCHOR"}], version="V2")
    assert cache["entries"]["old"] == parent["entries"]["old"]
    assert cache["entries"]["new"]["seed_id"] == "NEW"
    assert cache["parent_content_sha256"] == "a" * 64
    with pytest.raises(ValueError, match="approved anchor"):
        build_append_only_cache(parent, [{"cache_key": "bad", "seed_id": "BAD",
            "review_status": "UNCERTAIN", "anchor_id": None}], version="V2")


def test_append_only_cache_refuses_overwriting_parent_key():
    parent = {"content_sha256": "a" * 64, "entries": {"old": {"seed_id": "OLD"}}}
    with pytest.raises(ValueError, match="overwrite"):
        build_append_only_cache(parent, [{"cache_key": "old", "seed_id": "NEW",
            "review_status": "APPROVED", "anchor_id": "ANCHOR"}], version="V2")
