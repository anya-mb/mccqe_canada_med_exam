"""Tests for the deterministic, non-LLM scope-chapter packet preparer
(qbank.scope_packet), used by `python -m scripts.qbank prepare-scope-chapter`.
"""
import json
from pathlib import Path

import pytest

from qbank.scope_packet import (
    ScopePacketError,
    packet_output_path,
    prepare_chapter_packet,
    search_objectives,
)

REPO = Path(__file__).resolve().parents[1]


class TestPrepareChapterPacket:
    def test_valid_known_chapter_succeeds(self):
        packet, report = prepare_chapter_packet(REPO, "CP")
        assert packet["chapter"]["code"] == "CP"
        assert packet["chapter"]["title"] == "Clinical Pharmacology"
        assert report.chapter_code == "CP"
        assert report.source_node_count > 0

    def test_invalid_chapter_raises(self):
        with pytest.raises(ScopePacketError):
            prepare_chapter_packet(REPO, "ZZ_NOT_A_CHAPTER")

    def test_only_requested_chapter_nodes_included(self):
        packet, _ = prepare_chapter_packet(REPO, "CP")
        node_ids = {node["node_id"] for node in packet["source_nodes"]}
        assert all(node_id == "CP" or node_id.startswith("CP.") for node_id in node_ids)

    def test_candidate_objectives_come_from_canonical_registry(self):
        packet, _ = prepare_chapter_packet(REPO, "CP")
        registry = json.loads(
            (REPO / "research/mcc/objectives_registry.json").read_text(encoding="utf-8")
        )
        valid_ids = {o["mcc_id"] for o in registry["objectives"]}
        for candidate in packet["candidate_mcc_objectives"]:
            assert candidate["mcc_id"] in valid_ids

    def test_explicit_study_smarter_candidates_preserved(self):
        packet, report = prepare_chapter_packet(REPO, "CP", max_candidates=1)
        registry = json.loads(
            (REPO / "research/mcc/objectives_registry.json").read_text(encoding="utf-8")
        )
        registered_legacy_ids = {o["legacy_id"] for o in registry["objectives"]}
        # explicit Study Smarter rows whose legacy_id resolves in the registry
        # must never be pruned by the candidate cap
        explicit_legacy_ids = {
            row["legacy_id"] for row in packet["study_smarter"]["explicit_discipline_rows"]
            if row.get("legacy_id") in registered_legacy_ids
        }
        candidate_legacy_ids = {
            c["legacy_id"] for c in packet["candidate_mcc_objectives"]
            if "STUDY_SMARTER_DISCIPLINE" in c["matched_by"]
        }
        assert explicit_legacy_ids, "fixture should have at least one resolvable explicit row"
        assert explicit_legacy_ids.issubset(candidate_legacy_ids)

    def test_no_medical_classifications_generated(self):
        packet, _ = prepare_chapter_packet(REPO, "CP")
        for node in packet["source_nodes"]:
            assert "classification" not in node
        for candidate in packet["candidate_mcc_objectives"]:
            assert "classification" not in candidate
        for row in packet["study_smarter"]["explicit_discipline_rows"]:
            assert "classification" not in row

    def test_deterministic_repeat_output(self):
        packet_a, _ = prepare_chapter_packet(REPO, "CP")
        packet_b, _ = prepare_chapter_packet(REPO, "CP")
        assert packet_a == packet_b

    def test_no_source_path_leakage(self):
        packet, _ = prepare_chapter_packet(REPO, "CP")
        serialized = json.dumps(packet)
        assert "/Users/" not in serialized
        assert str(REPO) not in serialized

    def test_candidate_set_truncation_flag_set_when_cap_is_tight(self):
        _, report = prepare_chapter_packet(REPO, "C", max_candidates=2)
        assert report.candidate_set_truncated is True

    def test_packet_output_path_is_derived_and_gitignored_location(self):
        path = packet_output_path(REPO, "CP")
        assert path.parts[-3:] == ("derived", "scope_packets", "CP.json")


class TestSearchObjectives:
    def test_search_returns_registry_matches(self):
        matches = search_objectives(REPO, "hypertension", limit=5)
        assert len(matches) <= 5
        for match in matches:
            assert match["mcc_id"]

    def test_search_empty_query_returns_nothing(self):
        assert search_objectives(REPO, "") == []
