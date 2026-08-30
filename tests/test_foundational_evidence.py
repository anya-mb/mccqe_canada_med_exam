import copy
import hashlib
from pathlib import Path

from qbank.foundational_evidence import (
    build_foundational_evidence_audit,
    validate_foundational_evidence,
    validate_foundational_evidence_audit,
)
from qbank.jsonio import read_json


REPO = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = REPO / "research/qgen/foundational_evidence_claim_cards.json"
REGISTRY_PATH = REPO / "research/qgen/source_document_registry.json"


def _canonical_artifact() -> dict:
    return read_json(ARTIFACT_PATH)


def _registry() -> dict:
    return read_json(REGISTRY_PATH)


def _card(*, claim: str = "The illustrative structure has a stable factual property.", locator: str = "Section 1") -> dict:
    registry = _registry()
    return {
        "claim_card_id": "FNDCLM-0001",
        "claim": claim,
        "scope_references": [{"study_unit_id": "SU-A-03"}],
        "citations": [{
            "document_id": registry["documents"][0]["document_id"],
            "locator": locator,
        }],
        "use_classification": "STABLE_FACTUAL_SUPPORT",
        "verification_status": "VERIFIED_COMPLETE",
    }


def _fndoc(url: str = "https://foundational.example.ca/anatomy") -> dict:
    return {
        "document_id": "FNDOC-" + hashlib.sha256(url.encode()).hexdigest()[:16].upper(),
        "canonical_url": url,
        "title": "Foundational anatomy reference",
        "issuing_organization": "Example authority",
        "source_family": "FOUNDATIONAL_REFERENCE",
        "source_type": "REFERENCE_TEXT",
        "jurisdiction": "INTERNATIONAL",
        "is_canadian": False,
        "international_fallback": False,
        "publication_date": None,
        "update_date": None,
        "guideline_version": None,
        "date_status": "NOT_STATED",
        "version_status": "AVAILABLE",
        "currentness_status": "STABLE_FACTUAL_SUPPORT",
    }


def test_empty_canonical_artifact_is_valid() -> None:
    artifact = _canonical_artifact()

    assert artifact["documents"] == []
    assert artifact["claim_cards"] == []
    result = validate_foundational_evidence(REPO, artifact, _registry())

    assert result.status == "PASS"


def test_card_requires_verified_complete_atomic_claim_and_citation_locator() -> None:
    artifact = copy.deepcopy(_canonical_artifact())
    artifact["claim_cards"] = [_card(
        claim="One stable fact; another stable fact.",
        locator="",
    )]
    artifact["claim_cards"][0]["verification_status"] = "PENDING"

    result = validate_foundational_evidence(REPO, artifact, _registry())

    assert result.status == "FAIL"
    assert any("verification_status" in error for error in result.errors)
    assert any("locator" in error for error in result.errors)
    assert any("atomic" in error for error in result.errors)


def test_card_references_known_frozen_scope_identifier() -> None:
    artifact = copy.deepcopy(_canonical_artifact())
    artifact["claim_cards"] = [_card()]
    artifact["claim_cards"][0]["scope_references"] = [{"study_unit_id": "SU-NOT-REAL"}]

    result = validate_foundational_evidence(REPO, artifact, _registry())

    assert result.status == "FAIL"
    assert any("unknown study_unit_id" in error for error in result.errors)


def test_existing_registry_url_must_use_srdoc_not_fndoc() -> None:
    artifact = copy.deepcopy(_canonical_artifact())
    existing = _registry()["documents"][0]
    document = _fndoc(existing["canonical_url"])
    artifact["documents"] = [document]
    artifact["claim_cards"] = [_card()]
    artifact["claim_cards"][0]["citations"][0]["document_id"] = document["document_id"]

    result = validate_foundational_evidence(REPO, artifact, _registry())

    assert result.status == "FAIL"
    assert any("FNDOC canonical_url collides with SRDOC" in error for error in result.errors)


def test_new_fndoc_id_is_deterministic_and_cited() -> None:
    artifact = copy.deepcopy(_canonical_artifact())
    document = _fndoc()
    artifact["documents"] = [document]
    artifact["claim_cards"] = [_card()]
    artifact["claim_cards"][0]["citations"][0]["document_id"] = document["document_id"]

    audit = build_foundational_evidence_audit(REPO, artifact, _registry())

    assert document["document_id"] == "FNDOC-" + hashlib.sha256(document["canonical_url"].encode()).hexdigest()[:16].upper()
    assert audit["document_ids"] == [document["document_id"]]
    assert audit["counts"]["FNDOC_REFERENCES"] == 1
    assert validate_foundational_evidence_audit(REPO, artifact, _registry(), audit).status == "PASS"


def test_unknown_or_duplicate_document_reference_fails_closed() -> None:
    unknown_artifact = copy.deepcopy(_canonical_artifact())
    unknown_artifact["claim_cards"] = [_card()]
    unknown_artifact["claim_cards"][0]["citations"][0]["document_id"] = "FNDOC-0000000000000000"
    duplicate_artifact = copy.deepcopy(_canonical_artifact())
    duplicate_artifact["documents"] = [_fndoc(), _fndoc()]

    unknown = validate_foundational_evidence(REPO, unknown_artifact, _registry())
    duplicate = validate_foundational_evidence(REPO, duplicate_artifact, _registry())

    assert unknown.status == "FAIL"
    assert any("unknown citation document_id" in error for error in unknown.errors)
    assert duplicate.status == "FAIL"
    assert any("duplicate FNDOC document_id" in error for error in duplicate.errors)


def test_audit_rebuild_detects_changed_input_fingerprint() -> None:
    artifact = _canonical_artifact()
    audit = build_foundational_evidence_audit(REPO, artifact, _registry())
    stale_audit = copy.deepcopy(audit)
    stale_audit["input_fingerprints"][0]["sha256"] = "0" * 64

    result = validate_foundational_evidence_audit(REPO, artifact, _registry(), stale_audit)

    assert result.status == "FAIL"
    assert any("deterministic rebuild" in error for error in result.errors)
