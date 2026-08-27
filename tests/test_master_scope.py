"""Tests for deterministic master scope aggregation and validation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil

from qbank.cli import _parser


REPO = Path(__file__).resolve().parents[1]


def _project_copy(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "research").mkdir()
    shutil.copytree(REPO / "research/scope/chapters", root / "research/scope/chapters")
    shutil.copytree(REPO / "research/mcc", root / "research/mcc")
    shutil.copytree(REPO / "schemas", root / "schemas")
    (root / "reports").mkdir()
    shutil.copy(
        REPO / "reports/scope_scaling_progress.json",
        root / "reports/scope_scaling_progress.json",
    )
    return root


def _build(root: Path) -> dict:
    from qbank.master_scope import build_master_scope

    return build_master_scope(root)


def _validate(root: Path):
    from qbank.master_scope import validate_master_scope

    return validate_master_scope(root)


def _load(root: Path, filename: str) -> dict:
    return json.loads((root / "research/scope" / filename).read_text(encoding="utf-8"))


def _save(root: Path, filename: str, value: dict) -> None:
    (root / "research/scope" / filename).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def test_build_master_scope_command_is_registered():
    commands = _parser()._subparsers._group_actions[0].choices
    assert "build-master-scope" in commands


def test_validate_master_scope_command_is_registered():
    commands = _parser()._subparsers._group_actions[0].choices
    assert "validate-master-scope" in commands


def test_build_global_review_triage_accounts_for_every_review_candidate(tmp_path):
    """A dropped candidate or an oversized active-review batch must fail triage."""
    from qbank.global_review_triage import build_global_review_triage, validate_global_review_triage

    root = _project_copy(tmp_path)
    _build(root)
    result = build_global_review_triage(root)
    triage = _load(root, "global_review_triage.json")
    batches = _load(root, "global_review_batches.json")

    assert result["original_candidates"] == 598
    assert sum(triage["category_counts"].values()) == 598
    assert len(triage["entries"]) == 598
    assert {entry["study_unit_id"] for entry in triage["entries"]} == {
        item["study_unit_id"]
        for item in _load(root, "global_review_candidates.json")["candidates"]
    }
    assert all(len(batch["study_unit_ids"]) <= 25 for batch in batches["batches"])
    assert validate_global_review_triage(root).status == "PASS"


def test_global_review_triage_commands_are_registered():
    """The deterministic build and validation entry points remain available to operators."""
    commands = _parser()._subparsers._group_actions[0].choices
    assert "build-global-review-triage" in commands
    assert "validate-global-review-triage" in commands


def test_tier1_decomposition_partitions_tier1_and_keeps_packets_compact(tmp_path):
    """A Tier-1 unit cannot be omitted, duplicated, or mixed with another tier."""
    from qbank.global_review_triage import build_global_review_triage
    from qbank.tier1_decomposition import (
        build_tier1_decomposition,
        validate_tier1_decomposition,
    )

    root = _project_copy(tmp_path)
    _build(root)
    build_global_review_triage(root)
    result = build_tier1_decomposition(root)
    source = _load(root, "tier1_source_review.json")
    mapping = _load(root, "tier1_mapping_review.json")
    jurisdiction = _load(root, "tier1_jurisdiction_review.json")
    status = _load(root, "tier1_status_adjudication.json")
    tier1 = _load(root, "global_review_tier1.json")

    packet_ids = [
        entry["study_unit_id"]
        for packet in (source, mapping, jurisdiction, status)
        for entry in packet["entries"]
    ]
    tier1_ids = {entry["study_unit_id"] for entry in tier1["entries"]}
    assert result["total_study_units"] == 0
    assert set(packet_ids) == tier1_ids
    assert len(packet_ids) == len(set(packet_ids)) == 0
    assert result["work_type_counts"] == {
        "SOURCE_REVIEW": 0,
        "MAPPING_REVIEW": 0,
        "JURISDICTION_REVIEW": 0,
        "STATUS_ADJUDICATION": 0,
        "OTHER": 0,
    }
    assert mapping["mapping_review_counts"] == {
        "UNCERTAIN_PRIMARY": 0,
        "ONLY_WEAK": 0,
        "OTHER_MAPPING_ISSUE": 0,
    }
    assert source["source_review_counts"] == {"OPEN_SOURCE": 0, "OTHER": 0}
    assert all(entry["primary_work_type"] == "SOURCE_REVIEW" for entry in source["entries"])
    assert all("source_provenance" in entry for entry in source["entries"])
    assert validate_tier1_decomposition(root).status == "PASS"


def test_triage_retains_unresolved_review_recommended_chapter_items(tmp_path):
    """An open, review-recommended local item cannot be downgraded as history."""
    from qbank.global_review_triage import build_global_review_triage

    root = _project_copy(tmp_path)
    _build(root)
    path = root / "research/scope/chapters/A/review_items.json"
    review_items = json.loads(path.read_text(encoding="utf-8"))
    review_items["items"].append(
        {
            "issue_type": "mapping_scope_review",
            "severity": "review-recommended",
            "study_unit_id": "SU-A-07",
            "summary": "Existing deterministic review record without a resolution status.",
        }
    )
    path.write_text(json.dumps(review_items), encoding="utf-8")
    triage = build_global_review_triage(root)
    item = next(entry for entry in triage["entries"] if entry["study_unit_id"] == "SU-A-07")
    assert "UNRESOLVED_CHAPTER_REVIEW_ITEM" in item["review_reasons"]
    assert item["primary_triage_category"] == "TIER_3_SECONDARY"


def test_triage_treats_resolved_status_with_unresolved_detail_as_resolved():
    """Resolution-status text must take precedence over explanatory detail."""
    from qbank.global_review_triage import _is_open_review_item

    assert not _is_open_review_item(
        {
            "resolution_status": (
                "INDEPENDENTLY RESOLVED - retained with UNRESOLVED "
                "page_mapping_precision."
            ),
            "severity": "informational",
        }
    )


def test_triage_treats_resolved_issue_type_without_status_as_resolved():
    """A structured resolved issue type must not be reopened by severity."""
    from qbank.global_review_triage import _is_open_review_item

    assert not _is_open_review_item(
        {
            "issue_type": "severe_two_column_toc_corruption_resolved_via_body_evidence",
            "severity": "review_recommended",
        }
    )


def test_explicit_review_record_statuses_control_triage_semantics():
    """Canonical status overrides historic severity and free-text wording."""
    from qbank.global_review_triage import _review_record_status

    assert _review_record_status({"resolution_status": "RESOLVED", "summary": "unresolved"}) == "RESOLVED"
    assert _review_record_status({"resolution_status": "INFORMATIONAL"}) == "INFORMATIONAL"
    assert _review_record_status({"resolution_status": "DEFERRED_OWNERSHIP"}) == "DEFERRED_OWNERSHIP"
    assert _review_record_status({"resolution_status": "OPEN_SOURCE"}) == "OPEN_SOURCE"
    assert _review_record_status({"resolution_status": "OPEN_MAPPING"}) == "OPEN_MAPPING"
    assert _review_record_status({"resolution_status": "INSUFFICIENT_METADATA"}) == "INSUFFICIENT_METADATA"


def test_explicit_review_record_statuses_map_to_required_triage_categories():
    """Each standardized record status has a deterministic review destination."""
    from qbank.global_review_triage import _category

    assert _category(["RESOLVED_CHAPTER_REVIEW_ITEM"]) == "NO_CURRENT_SEMANTIC_REVIEW"
    assert _category(["INFORMATIONAL_CHAPTER_REVIEW_ITEM"]) == "NO_CURRENT_SEMANTIC_REVIEW"
    assert _category(["DEFERRED_OWNERSHIP_REVIEW_ITEM"]) == "OWNERSHIP_ONLY"
    assert _category(["OPEN_SOURCE_REVIEW_ITEM"]) == "TIER_1_CRITICAL"
    assert _category(["OPEN_MAPPING_REVIEW_ITEM"]) == "TIER_3_SECONDARY"
    assert _category(["STATUS_REQUIRES_ADJUDICATION"]) == "TIER_1_CRITICAL"


def test_persistent_scope_uncertainty_is_visible_without_reentering_active_triage():
    """A completed Tier-1 adjudication may defer an evidenced scope gap."""
    from qbank.global_review_triage import _category, _reasons

    reasons = _reasons(
        {"classification": "UNCERTAIN", "mcc_evidence": []},
        ["UNCERTAIN"],
        [],
        [{
            "issue_type": "persistent_global_scope_uncertainty",
            "review_record_status": "INFORMATIONAL",
        }],
        set(),
    )

    assert "PERSISTENT_GLOBAL_SCOPE_UNCERTAINTY" in reasons
    assert "UNCERTAIN_PRIMARY" not in reasons
    assert _category(reasons) == "NO_CURRENT_SEMANTIC_REVIEW"


def test_resolved_source_metadata_triage_suppresses_historical_page_precision_flag():
    """An explicit source-triage resolution prevents reopening known history."""
    from qbank.global_review_triage import _reasons

    reasons = _reasons(
        {"page_mapping_precision": "UNRESOLVED"},
        [],
        [],
        [{
            "issue_type": "source_review_other_metadata_triage",
            "review_record_status": "RESOLVED",
        }],
        set(),
    )

    assert "SOURCE_AMBIGUITY_UNRESOLVED" not in reasons


def test_build_includes_every_chapter_crosswalk_entry_once(tmp_path):
    root = _project_copy(tmp_path)
    result = _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    expected = sum(
        len(json.loads(path.read_text(encoding="utf-8"))["entries"])
        for path in (root / "research/scope/chapters").glob("*/crosswalk.json")
    )
    ids = [entry["study_unit_id"] for entry in master["entries"]]
    assert result["total_study_units"] == expected
    assert len(ids) == expected
    assert len(ids) == len(set(ids))


def test_duplicate_study_unit_id_fails_validation(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    master["entries"].append(copy.deepcopy(master["entries"][0]))
    _save(root, "master_scope_crosswalk.json", master)
    result = _validate(root)
    assert result.status == "FAIL"
    assert any("duplicate study_unit_id" in error for error in result.errors)


def test_invalid_mcc_evidence_reference_fails_validation(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    entry = next(entry for entry in master["entries"] if entry["mcc_evidence"])
    evidence = next(
        item for item in entry["mcc_evidence"] if item["evidence_type"] == "OBJECTIVE_REFERENCE"
    )
    evidence["mcc_id"] = "NOT-A-REAL-MCC-ID"
    _save(root, "master_scope_crosswalk.json", master)
    result = _validate(root)
    assert result.status == "FAIL"
    assert any("NOT-A-REAL-MCC-ID" in error for error in result.errors)


def test_accounting_weak_metrics_candidates_and_coverage_reconcile(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    master = _load(root, "master_scope_crosswalk.json")
    report = _load(root, "master_scope_report.json")
    candidates = _load(root, "global_review_candidates.json")
    coverage = _load(root, "mcc_objective_coverage.json")
    entries = master["entries"]
    classifications = report["classification_counts"]
    evidence = report["mcc_evidence_references"]
    assert sum(classifications.values()) == len(entries)
    assert sum(evidence.values()) == sum(len(entry["mcc_evidence"]) for entry in entries)
    any_weak = sum(any(item["mapping_strength"] == "WEAK" for item in entry["mcc_evidence"]) for entry in entries)
    only_weak = sum(
        any(item["mapping_strength"] == "WEAK" for item in entry["mcc_evidence"])
        and not any(item["mapping_strength"] in {"STRONG", "MODERATE"} for item in entry["mcc_evidence"])
        for entry in entries
    )
    assert report["study_units_with_any_weak_evidence"] == any_weak
    assert report["study_units_with_only_weak_evidence"] == only_weak
    entry_ids = {entry["study_unit_id"] for entry in entries}
    assert {item["study_unit_id"] for item in candidates["candidates"]} <= entry_ids
    mapped_ids = {
        evidence["mcc_id"]
        for entry in entries
        for evidence in entry["mcc_evidence"]
        if evidence["evidence_type"] == "OBJECTIVE_REFERENCE"
    }
    assert {item["objective_id"] for item in coverage["objectives"] if item["mapped_study_unit_count"]} == mapped_ids


def test_final_adjudication_packet_reconciles_coverage_and_persistent_uncertainties(tmp_path):
    """The final packet contains only deterministic coverage-risk records and links."""
    root = _project_copy(tmp_path)
    _build(root)
    coverage = _load(root, "mcc_objective_coverage.json")
    packet = _load(root, "final_scope_adjudication_candidates.json")

    states = [item["coverage_state"] for item in coverage["objectives"]]
    assert len(states) == 198
    assert states.count("UNMAPPED_OBJECTIVE_CANDIDATE") == 9
    assert sum(states.count(state) for state in (
        "STRONG_OR_MODERATE_COVERAGE",
        "WEAK_ONLY_COVERAGE",
        "UNMAPPED_OBJECTIVE_CANDIDATE",
    )) == 198
    assert len(packet["unmapped_objective_candidates"]) == 9
    assert len(packet["persistent_uncertain_study_units"]) == 3
    assert packet["validation"]["status"] == "PASS"
    assert _validate(root).status == "PASS"


def test_final_adjudication_packet_excludes_resolved_persistent_uncertainties(tmp_path):
    """A final non-UNCERTAIN classification leaves the adjudication candidate set."""
    root = _project_copy(tmp_path)
    path = root / "research/scope/chapters/GS/crosswalk.json"
    crosswalk = json.loads(path.read_text(encoding="utf-8"))
    entry = next(
        item for item in crosswalk["entries"]
        if item["study_unit_id"] == "SU-GS-75"
    )
    entry["classification"] = "SUPPORTING_KNOWLEDGE"
    entry.pop("uncertain_reason")
    path.write_text(json.dumps(crosswalk), encoding="utf-8")

    _build(root)
    packet = _load(root, "final_scope_adjudication_candidates.json")

    assert len(packet["persistent_uncertain_study_units"]) == 2
    assert "SU-GS-75" not in {
        item["study_unit_id"]
        for item in packet["persistent_uncertain_study_units"]
    }
    assert packet["validation"]["status"] == "PASS"


def test_build_output_is_deterministic(tmp_path):
    root = _project_copy(tmp_path)
    _build(root)
    first = {
        name: (root / "research/scope" / name).read_bytes()
        for name in (
            "master_scope_crosswalk.json",
            "master_scope_report.json",
            "global_review_candidates.json",
            "global_ownership_candidates.json",
            "mcc_objective_coverage.json",
            "final_scope_adjudication_candidates.json",
        )
    }
    _build(root)
    assert first == {name: (root / "research/scope" / name).read_bytes() for name in first}
