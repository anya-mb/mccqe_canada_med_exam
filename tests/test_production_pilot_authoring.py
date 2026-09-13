"""Deterministic controls for the first production authoring pilot."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.qbank import production_pilot_authoring as ppa
from scripts.qbank.independent_item_verification import canonical_hash

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return ppa.load_pilot_manifest(ROOT)


@pytest.fixture(scope="module")
def evidence() -> dict:
    return ppa.build_evidence_index(ROOT)


@pytest.fixture(scope="module")
def items() -> dict:
    return ppa.load_authored_items(ROOT)


@pytest.fixture(scope="module")
def packages(items, manifest, evidence) -> dict:
    return ppa.build_verification_packages(ROOT)


def test_frozen_inputs_reproduce_their_declared_hashes(manifest):
    assert manifest["content_sha256"] == ppa.REGISTRY_V3_PILOT_MANIFEST_SHA256
    assert manifest["registry_v3_sha256"] == ppa.REGISTRY_V3_SHA256
    assert len(manifest["manifest"]) == 36


def test_every_manifest_row_is_production_eligible(manifest):
    registry = ppa.load_registry_v3(ROOT)
    for row in manifest["manifest"]:
        assert registry[row["opportunity_id"]]["lifecycle_state"] == "PRODUCTION_ELIGIBLE"


def test_evidence_index_resolves_only_repository_backed_facts(evidence):
    assert evidence
    for fact_id, fact in evidence.items():
        assert fact["statement"].strip()
        assert fact["sources"], fact_id
        for source in fact["sources"]:
            assert source["source_id"] and source["organization"] and source["locator"]


def test_authored_items_target_distinct_manifest_opportunities(items, manifest):
    ids = [row["registry_v3_opportunity_id"] for row in items["items"]]
    assert len(ids) == len(set(ids))
    allowed = {row["opportunity_id"] for row in manifest["manifest"]}
    assert set(ids) <= allowed


def test_every_manifest_opportunity_has_exactly_one_disposition(items, manifest):
    dispositions = {row["registry_v3_opportunity_id"]: row["disposition"] for row in items["items"]}
    dispositions.update({row["opportunity_id"]: row["disposition"] for row in items["not_authored"]})
    assert set(dispositions) == {row["opportunity_id"] for row in manifest["manifest"]}
    assert len(dispositions) == 36


def test_no_authored_item_claims_independent_verification(items):
    blob = json.dumps(items)
    assert "VERIFIED_ACCEPT" not in blob
    for row in items["items"]:
        assert row["verification_status"] == ppa.PENDING_VERIFICATION


def test_deterministic_validation_accepts_the_authored_batch(items, manifest, evidence):
    errors = ppa.validate_authored_batch(ROOT)
    assert errors == []


def test_validation_rejects_a_key_absent_from_the_options(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    row["author_proposed_key"] = "An option that does not appear in the list."
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("KEY_NOT_IN_OPTIONS" in error for error in errors)


def test_validation_rejects_a_missing_distractor_rationale(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    row["per_distractor_rationales"] = row["per_distractor_rationales"][:-1]
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("DISTRACTOR_RATIONALE" in error for error in errors)


def test_validation_rejects_duplicate_options(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    row["answer_choices"][1] = row["answer_choices"][0]
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("DUPLICATE_OPTION" in error for error in errors)


def test_validation_rejects_an_unresolvable_evidence_fact(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    row["evidence_fact_ids"] = ["CLM-THAT-DOES-NOT-EXIST"]
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("EVIDENCE_FACT_NOT_IN_REPOSITORY" in error for error in errors)


def test_validation_rejects_an_item_outside_the_frozen_manifest(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    row["registry_v3_opportunity_id"] = "QOP-V3C-NOTINMANIFEST"
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("OPPORTUNITY_NOT_IN_PILOT_MANIFEST" in error for error in errors)


def test_validation_rejects_a_self_declared_verified_accept(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    row["verification_status"] = "VERIFIED_ACCEPT"
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("AUTHOR_MAY_NOT_SET_VERIFIED_ACCEPT" in error for error in errors)


def test_packages_conform_to_the_frozen_v1_schema(packages):
    schema = json.loads((ROOT / "schemas/production-item-verification-package-v1.schema.json").read_text())
    required, allowed = set(schema["required"]), set(schema["properties"])
    for package in packages["packages"]:
        assert set(package) == allowed
        assert required <= set(package)
        assert package["schema_version"] == "1.0"
        assert len(package["answer_choices"]) >= 4
        assert package["author_proposed_key"] in package["answer_choices"]
        assert len(package["per_distractor_rationales"]) == len(package["answer_choices"]) - 1
        assert package["non_production_validation_item"] is False


def test_package_hashes_are_reproducible(packages):
    for package in packages["packages"]:
        body = {key: value for key, value in package.items() if key != "content_sha256"}
        assert package["content_sha256"] == canonical_hash(body)


def test_blind_projection_hides_key_rationale_and_evidence(packages):
    from scripts.qbank.independent_item_verification import blind_projection

    for package in packages["packages"]:
        blind = blind_projection(package)
        blob = json.dumps(blind)
        assert package["author_proposed_key"] not in blob or package["author_proposed_key"] in package["answer_choices"]
        assert "author_rationale" not in blind
        assert "per_distractor_rationales" not in blind
        assert "evidence_fact_ids" not in blind
        assert "canadian_source_refs" not in blind


def test_author_session_may_not_verify_its_own_package(packages):
    from scripts.qbank.independent_item_verification import (
        VerificationError, blind_projection, freeze_blind_solve, open_evidence_audit,
    )

    package = packages["packages"][0]
    blind = blind_projection(package)
    frozen = freeze_blind_solve(blind, {
        "reviewer_session_id": ppa.AUTHOR_SESSION_ID,
        "chosen_best_answer": package["answer_choices"][0],
        "confidence": "HIGH", "possible_second_key": False, "ambiguity": "NONE",
        "missing_information": "NONE", "mccqe_realism": "REALISTIC",
    })
    with pytest.raises(VerificationError, match="NONINDEPENDENT_VERIFIER_SESSION"):
        open_evidence_audit(package, frozen, verifier_session_id=ppa.AUTHOR_SESSION_ID)


def test_handoff_manifest_is_pending_and_carries_every_package(packages):
    handoff = ppa.build_verification_handoff_manifest(ROOT)
    assert handoff["verification_status"] == ppa.PENDING_VERIFICATION
    assert handoff["authoring_session_verdict"] == "NOT_AUTHORIZED"
    assert handoff["separate_session_required"] is True
    assert handoff["web_export_authorized"] is False
    assert len(handoff["packages"]) == len(packages["packages"])
    ids = {row["item_id"] for row in handoff["packages"]}
    assert ids == {row["item_id"] for row in packages["packages"]}
    for row in handoff["packages"]:
        assert row["verification_status"] == ppa.PENDING_VERIFICATION
        assert row["registry_v3_opportunity_id"].startswith("QOP-V3C-")


def test_items_are_educationally_distinct(items):
    flags = ppa.detect_near_duplicate_items(items["items"])
    assert flags == []


def test_batch_report_hides_nothing(items):
    report = ppa.build_authoring_batch_report(ROOT)
    assert report["manifest_opportunities"] == 36
    accounted = (
        report["author_complete_items"]
        + report["insufficient_evidence_items"]
        + report["needs_source_research_items"]
        + report["rejected_items"]
        + report["second_key_failures"]
    )
    assert accounted == 36
    assert report["any_item_marked_verified_accept"] is False
    assert report["web_export_authorized"] is False
    assert report["commits_created"] == 0


def test_validation_reuses_adm5_realization_parity(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    row["answer_choices"] = [
        "Measure the level after 48 hours", "Observe without further testing",
        "Refer to the specialty clinic", "Repeat the physical examination",
    ]
    row["author_proposed_key"] = "Observe without further testing"
    row["per_distractor_rationales"] = [
        {"choice": choice, "why_plausible": "x" * 60, "why_inferior_here": "x" * 60,
         "what_would_make_correct": "x" * 60}
        for choice in row["answer_choices"] if choice != row["author_proposed_key"]
    ]
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("SOLE_NUMERAL_BEARING_OPTION" in error for error in errors)


def test_validation_rejects_a_key_far_longer_than_every_distractor(items, manifest, evidence):
    row = deepcopy(items["items"][0])
    long_key = row["answer_choices"][0] + " " + "and a great deal of additional qualifying detail" * 4
    row["answer_choices"] = [long_key] + row["answer_choices"][1:]
    row["author_proposed_key"] = long_key
    row["per_distractor_rationales"] = [
        {"choice": choice, "why_plausible": "x" * 60, "why_inferior_here": "x" * 60,
         "what_would_make_correct": "x" * 60}
        for choice in row["answer_choices"] if choice != long_key
    ]
    errors = ppa.validate_item(row, manifest, evidence)
    assert any("KEY_DISTRACTOR_LENGTH_ASYMMETRY" in error for error in errors)


def test_copyright_audit_passes_and_its_detector_fires_on_real_toronto_notes_prose():
    import sqlite3

    audit = ppa.build_copyright_audit(ROOT)
    assert audit["copyright_audit"] == "PASS"
    assert audit["longest_toronto_notes_word_overlap"] == 0

    connection = sqlite3.connect(ROOT / "derived/tn_index/tn_index.sqlite3")
    prose = connection.execute(
        "SELECT text FROM chunk_text WHERE length(text) > 400 LIMIT 1"
    ).fetchone()[0]
    connection.close()
    assert ppa.measure_toronto_notes_overlap(ROOT, [prose]) >= 12


def test_near_duplicate_detector_fires_on_a_copied_item(items):
    twin = deepcopy(items["items"][0])
    twin["item_id"] = "QPILOT-V1-TWIN"
    flags = ppa.detect_near_duplicate_items([items["items"][0], twin])
    assert any("NEAR_DUPLICATE_ITEM_PAIR" in flag for flag in flags)


def test_frozen_pilot_artifacts_on_disk_match_a_fresh_rebuild():
    for name, builder in (
        ("pilot_verification_packages.json", ppa.build_verification_packages),
        ("pilot_stage_1_blind_packets.json", ppa.build_blind_packets),
        ("pilot_independent_verification_handoff.json", ppa.build_verification_handoff_manifest),
        ("pilot_copyright_audit.json", ppa.build_copyright_audit),
        ("pilot_authoring_batch_report.json", ppa.build_authoring_batch_report),
    ):
        frozen = json.loads((ROOT / ppa.PILOT_DIR / name).read_text())
        assert frozen["content_sha256"] == builder(ROOT)["content_sha256"], name
