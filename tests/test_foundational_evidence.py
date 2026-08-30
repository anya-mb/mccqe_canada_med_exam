import copy
from pathlib import Path

from qbank.foundational_evidence import validate_foundational_evidence
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
