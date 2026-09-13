from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil

import jsonschema
import pytest

from scripts.qbank.independent_item_verification import (
    VerificationError,
    append_ledger_entry,
    blind_projection,
    build_disagreement_packet,
    build_external_verifier_dry_run_manifest,
    build_validation_packages,
    canonical_hash,
    derive_verification_verdict,
    freeze_blind_solve,
    open_evidence_audit,
    requires_reverification,
    run_mutation_contract_tests,
    validate_evidence_audit,
    verify_ledger_chain,
    write_verification_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def _package():
    value = {
        "schema_version": "1.0",
        "item_id": "DEV-1",
        "opportunity_id": "OPP-1",
        "question_seed_id": "SEED-1",
        "author_session_id": "AUTHOR-A",
        "discipline": "MED",
        "topic": "Example",
        "learner_decision": "Choose the best action.",
        "difficulty_intent": "MODERATE",
        "stem": "A patient has finding X.",
        "lead_in": "What is the best next step?",
        "answer_choices": ["A", "B", "C", "D"],
        "author_proposed_key": "A",
        "author_rationale": "A follows from claim F1.",
        "per_distractor_rationales": [
            {"choice": value, "why_plausible": "Nearby context.", "why_inferior_here": "X is present.",
             "what_would_make_correct": "X absent and Y present."}
            for value in ("B", "C", "D")
        ],
        "conditional_next_action_information": "Escalate if unstable.",
        "evidence_fact_ids": ["F1"],
        "toronto_notes_source_refs": ["TN:CHAPTER:SECTION"],
        "canadian_source_refs": [
            {"source_id": "SRC-1", "organization": "Canadian Society", "date_or_version": "2026",
             "locator": "section 2"}
        ],
        "author_confidence": "HIGH",
        "non_production_validation_item": True,
    }
    value["verified_content_sha256"] = canonical_hash({
        key: value[key] for key in (
            "stem", "lead_in", "answer_choices", "author_proposed_key", "author_rationale",
            "per_distractor_rationales", "evidence_fact_ids", "toronto_notes_source_refs", "canadian_source_refs",
        )
    })
    value["content_sha256"] = canonical_hash({key: item for key, item in value.items() if key != "content_sha256"})
    return value


def test_blind_projection_contains_only_item_stem_leadin_and_choices():
    blind = blind_projection(_package())
    assert set(blind) == {"schema_version", "item_id", "stem", "lead_in", "answer_choices", "blind_packet_sha256"}
    serialized = json.dumps(blind).lower()
    for secret in ("key", "rationale", "confidence", "evidence", "toronto", "source"):
        assert secret not in serialized


def test_stage_two_requires_frozen_matching_blind_result_and_independent_session():
    package = _package()
    blind = blind_projection(package)
    result = freeze_blind_solve(blind, {
        "reviewer_session_id": "VERIFIER-B", "chosen_best_answer": "A", "confidence": "HIGH",
        "possible_second_key": None, "ambiguity": "NONE", "missing_information": "NONE",
        "mccqe_realism": "PASS",
    })
    opened = open_evidence_audit(package, result, verifier_session_id="VERIFIER-B")
    assert opened["frozen_blind_solve_sha256"] == result["content_sha256"]
    changed = deepcopy(result)
    changed["chosen_best_answer"] = "B"
    with pytest.raises(VerificationError, match="BLIND_SOLVE_HASH_MISMATCH"):
        open_evidence_audit(package, changed, verifier_session_id="VERIFIER-B")
    with pytest.raises(VerificationError, match="NONINDEPENDENT_VERIFIER_SESSION"):
        open_evidence_audit(package, result, verifier_session_id="AUTHOR-A")


def test_claim_audit_requires_direct_trace_for_load_bearing_claims():
    package = _package()
    audit = {
        "claims": [{"claim_id": "C1", "claim": "A follows from F1", "load_bearing": True,
                    "status": "VERIFIED", "source_traces": []}],
        "tn_status": "TN_CONSISTENT", "canadian_guidance_status": "CONSISTENT",
        "source_conflict_status": "NO_CONFLICT", "hallucination_flags": [],
        "blind_answer_matches_key": True, "one_best_answer": True, "possible_second_key": False,
        "plausible_inferior_distractor_count": 3, "same_response_class": True,
        "compatible_granularity": True, "rationale_quality": "PASS",
    }
    with pytest.raises(VerificationError, match="LOAD_BEARING_CLAIM_MISSING_DIRECT_TRACE"):
        validate_evidence_audit(package, audit)


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"blind_answer_matches_key": False}, "REJECT_WRONG_KEY"),
        ({"possible_second_key": True}, "REJECT_SECOND_KEY"),
        ({"one_best_answer": False}, "REJECT_AMBIGUOUS"),
        ({"unsupported_claim": True}, "REJECT_UNSUPPORTED_RATIONALE"),
        ({"hallucination_flags": ["FABRICATED_CITATION"]}, "REJECT_HALLUCINATION"),
        ({"canadian_guidance_status": "MATERIAL_CONFLICT"}, "REJECT_CANADIAN_GUIDELINE_CONFLICT"),
        ({"tn_status": "MATERIAL_TN_CONTRADICTION"}, "REJECT_TORONTO_NOTES_CONFLICT"),
        ({"outdated_guidance": True}, "REJECT_OUTDATED_GUIDANCE"),
        ({"plausible_inferior_distractor_count": 2}, "REJECT_WEAK_DISTRACTORS"),
    ],
)
def test_controlled_verdict_precedence(change, expected):
    audit = {
        "blind_answer_matches_key": True, "possible_second_key": False, "one_best_answer": True,
        "unsupported_claim": False, "hallucination_flags": [], "canadian_guidance_status": "CONSISTENT",
        "tn_status": "TN_CONSISTENT", "outdated_guidance": False,
        "plausible_inferior_distractor_count": 3, "same_response_class": True,
        "compatible_granularity": True, "rationale_quality": "PASS", "source_conflict_status": "NO_CONFLICT",
    }
    audit.update(change)
    assert derive_verification_verdict(audit) == expected


def test_verified_accept_and_content_change_requires_reverification():
    package = _package()
    entry = {"final_verification_status": "VERIFIED_ACCEPT", "verified_content_sha256": package["verified_content_sha256"]}
    assert requires_reverification(entry, package) is False
    changed = deepcopy(package)
    changed["stem"] += " New material fact."
    assert requires_reverification(entry, changed) is True


def test_ledger_is_append_only_hash_chained_and_detects_tampering():
    ledger = {"schema_version": "1.0", "scope": "PRODUCTION_ITEM_VERIFICATION_LEDGER_V1", "entries": []}
    one = append_ledger_entry(ledger, {
        "item_id": "DEV-1", "author_package_hash": "a" * 64, "independent_session_identifier": "VERIFIER-B",
        "blind_solve_verdict_hash": "b" * 64, "evidence_audit_verdict_hash": "c" * 64,
        "adjudication_hash": None, "final_verification_status": "VERIFIED_ACCEPT",
        "verified_content_sha256": "d" * 64, "verified_source_versions_dates": ["SRC-1:2026"],
    })
    assert verify_ledger_chain(one) == []
    tampered = deepcopy(one)
    tampered["entries"][0]["final_verification_status"] = "REJECT_WRONG_KEY"
    assert verify_ledger_chain(tampered)
    top_level_tampered = deepcopy(one)
    top_level_tampered["status"] = "CORRUPTED"
    assert "LEDGER_CONTENT_HASH_MISMATCH" in verify_ledger_chain(top_level_tampered)


def test_disagreement_packet_requires_third_distinct_session():
    packet = build_disagreement_packet(_package(), {"reviewer_session_id": "VERIFIER-B"},
                                        author_verdict="A", verifier_verdict="B")
    assert packet["author_verdict"] != packet["verifier_verdict"]
    assert packet["allowed_outcomes"] == [
        "AUTHOR_CORRECT", "VERIFIER_CORRECT", "BOTH_INCOMPLETE", "ITEM_AMBIGUOUS", "SOURCE_CONFLICT", "REJECT"
    ]


def test_validation_packages_use_existing_nonproduction_items_and_conform_to_schema():
    artifact = build_validation_packages(ROOT)
    assert len(artifact["packages"]) >= 6
    assert {row["discipline"] for row in artifact["packages"]} == {"MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"}
    assert all(row["non_production_validation_item"] for row in artifact["packages"])
    schema = json.loads((ROOT / "schemas/production-item-verification-package-v1.schema.json").read_text())
    for row in artifact["packages"]:
        jsonschema.validate(row, schema)


def test_all_required_seeded_mutations_are_detected_without_touching_source_items():
    source_path = ROOT / "research/qgen/exposure/clean_transfer_v2_questions.json"
    before = canonical_hash(json.loads(source_path.read_text()))
    results = run_mutation_contract_tests(_package())
    assert results == {
        "wrong_key_detected": True,
        "second_key_detected": True,
        "unsupported_claim_detected": True,
        "false_citation_detected": True,
        "outdated_guidance_detected": True,
        "tn_conflict_detected": True,
        "canadian_guideline_conflict_detected": True,
    }
    assert canonical_hash(json.loads(source_path.read_text())) == before


def test_all_external_verification_schemas_exist_and_are_closed():
    names = [
        "production-item-verification-package-v1.schema.json",
        "production-item-blind-solve-v1.schema.json",
        "production-item-evidence-audit-v1.schema.json",
        "production-item-verification-adjudication-v1.schema.json",
        "production-item-verification-ledger-v1.schema.json",
    ]
    for name in names:
        schema = json.loads((ROOT / "schemas" / name).read_text())
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False


def test_writer_emits_hashed_nonproduction_validation_artifacts(tmp_path):
    outputs = write_verification_artifacts(ROOT, tmp_path)
    assert set(outputs) == {
        "historical_input_pins.json", "production_item_verification_ledger_v1.json",
        "synthetic_mutation_cases.json", "validation_item_packages.json",
        "verification_mutation_results.json",
    }
    for name, digest in outputs.items():
        assert json.loads((tmp_path / name).read_text())["content_sha256"] == digest


def test_external_verifier_dry_run_manifest_pins_six_packages_without_self_verdicts():
    manifest = build_external_verifier_dry_run_manifest(ROOT)
    assert manifest["scope"] == "EXTERNAL_VERIFIER_DRY_RUN_MANIFEST_V1"
    assert manifest["validation_package_count"] == 6
    assert {row["discipline"] for row in manifest["packages"]} == {
        "MED", "PED", "OBGYN", "SURG", "PSY", "PHELO",
    }
    assert len({row["item_id"] for row in manifest["packages"]}) == 6
    assert all(row["non_production_validation_item"] for row in manifest["packages"])
    assert manifest["package_artifact_content_sha256"] == (
        "57cd1b43af43f1544b0aac4848fadcf0cc6c82224a520e9157c28d5579d344e5"
    )
    assert manifest["verification_package_schema_file_sha256"] == (
        "a6d222bde3224983ef219d4e753f79a37e1ff521dd6d6ed64c4ff11825497e86"
    )
    assert manifest["verification_ledger_file_sha256"] == (
        "28bf5dcb49cc942a4ea9176bc1f0f2aab0e6a4996936c8127441154da8a13cb5"
    )
    assert manifest["external_verifier_prompt_file_sha256"] == (
        "d08b68006221dbb2a205b4ffe05aca00a843517fc3d2a1152764be2f351770f6"
    )
    assert manifest["ledger_chain_errors"] == []
    assert all(manifest["mutation_tests"].values())
    assert manifest["authoring_session_verdict"] == "NOT_AUTHORIZED"
    assert "VERIFIED_ACCEPT" not in {row.get("verdict") for row in manifest["packages"]}


def test_external_verifier_manifest_rejects_tampered_or_incomplete_integrity_receipts(tmp_path):
    verification_dir = tmp_path / "research/qgen/independent_verification_v1"
    verification_dir.mkdir(parents=True)
    (tmp_path / "docs/qgen").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    for name in (
        "validation_item_packages.json",
        "production_item_verification_ledger_v1.json",
        "verification_mutation_results.json",
    ):
        shutil.copy(ROOT / "research/qgen/independent_verification_v1" / name, verification_dir / name)
    shutil.copy(
        ROOT / "docs/qgen/INDEPENDENT_PRODUCTION_ITEM_VERIFIER_PROMPT.md",
        tmp_path / "docs/qgen/INDEPENDENT_PRODUCTION_ITEM_VERIFIER_PROMPT.md",
    )
    shutil.copy(
        ROOT / "schemas/production-item-verification-package-v1.schema.json",
        tmp_path / "schemas/production-item-verification-package-v1.schema.json",
    )

    ledger_path = verification_dir / "production_item_verification_ledger_v1.json"
    ledger = json.loads(ledger_path.read_text())
    ledger["status"] = "CORRUPTED"
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(VerificationError, match="LEDGER_CONTENT_HASH_MISMATCH"):
        build_external_verifier_dry_run_manifest(tmp_path)

    shutil.copy(
        ROOT / "research/qgen/independent_verification_v1/production_item_verification_ledger_v1.json",
        ledger_path,
    )
    mutation_path = verification_dir / "verification_mutation_results.json"
    mutations = json.loads(mutation_path.read_text())
    mutations["results"].pop("wrong_key_detected")
    mutations["content_sha256"] = canonical_hash({
        key: value for key, value in mutations.items() if key != "content_sha256"
    })
    mutation_path.write_text(json.dumps(mutations))
    with pytest.raises(VerificationError, match="MUTATION_RESULT_KEYS_MISMATCH"):
        build_external_verifier_dry_run_manifest(tmp_path)

    shutil.copy(
        ROOT / "research/qgen/independent_verification_v1/verification_mutation_results.json",
        mutation_path,
    )
    mutations = json.loads(mutation_path.read_text())
    mutations["results"]["wrong_key_detected"] = False
    mutations["content_sha256"] = canonical_hash({
        key: value for key, value in mutations.items() if key != "content_sha256"
    })
    mutation_path.write_text(json.dumps(mutations))
    with pytest.raises(VerificationError, match="MUTATION_DETECTION_FAILED"):
        build_external_verifier_dry_run_manifest(tmp_path)
