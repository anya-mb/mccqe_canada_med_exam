"""Validate the additive foundational-evidence claim-card corpus."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from .jsonio import read_json, write_json_atomic
from .paths import resolve_root_path
from .schema import validate_instance
from .source_document_registry import _canonical_url


_REGISTRY_PATH = "research/qgen/source_document_registry.json"
_SCOPE_PATH = "research/scope/master_scope_crosswalk.json"
_ALLOCATION_PATH = "research/scope/final_question_allocation.json"
_ARTIFACT_PATH = "research/qgen/foundational_evidence_claim_cards.json"
_AUDIT_PATH = "reports/foundational_evidence_audit.json"
_AUDIT_INPUTS = (_ARTIFACT_PATH, _REGISTRY_PATH, _SCOPE_PATH, _ALLOCATION_PATH)


@dataclass(frozen=True)
class FoundationalEvidenceModel:
    """Validated canonical corpus plus the frozen identifiers it may reference."""

    artifact: dict[str, Any]
    study_unit_ids: frozenset[str]
    allocation_address_ids: frozenset[str]
    registry_document_ids: frozenset[str]


@dataclass
class FoundationalEvidenceValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _root_json(root: Path, relative: str, label: str) -> dict[str, Any]:
    return _object(read_json(resolve_root_path(root, relative, label=label)), label)


def _frozen_ids(root: Path) -> tuple[frozenset[str], frozenset[str]]:
    crosswalk = _root_json(root, _SCOPE_PATH, "master scope crosswalk")
    allocation = _root_json(root, _ALLOCATION_PATH, "final question allocation")
    entries = crosswalk.get("entries")
    addresses = allocation.get("allocation_addresses")
    if not isinstance(entries, list) or not isinstance(addresses, list):
        raise ValueError("frozen scope inputs have invalid identifier collections")
    study_unit_ids = frozenset(
        entry["study_unit_id"] for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("study_unit_id"), str)
    )
    allocation_address_ids = frozenset(
        address["allocation_address_id"] for address in addresses
        if isinstance(address, dict) and isinstance(address.get("allocation_address_id"), str)
    )
    if not study_unit_ids or not allocation_address_ids:
        raise ValueError("frozen scope identifiers are missing")
    return study_unit_ids, allocation_address_ids


def build_foundational_evidence_model(root: Path, artifact: dict[str, Any]) -> FoundationalEvidenceModel:
    """Build the bounded model after validating canonical artifact shape."""
    root = Path(root).resolve()
    validate_instance(root, "foundational-evidence-claim-cards", artifact)
    study_unit_ids, allocation_address_ids = _frozen_ids(root)
    registry = _root_json(root, _REGISTRY_PATH, "source document registry")
    documents = registry.get("documents")
    if not isinstance(documents, list):
        raise ValueError("source document registry documents must be a list")
    registry_document_ids = frozenset(
        document["document_id"] for document in documents
        if isinstance(document, dict) and isinstance(document.get("document_id"), str)
    )
    return FoundationalEvidenceModel(
        artifact=artifact,
        study_unit_ids=study_unit_ids,
        allocation_address_ids=allocation_address_ids,
        registry_document_ids=registry_document_ids,
    )


def _semantic_errors(root: Path, artifact: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = artifact.get("source_document_registry")
    registry_path = resolve_root_path(root, _REGISTRY_PATH, label="source document registry")
    if isinstance(source, dict) and source.get("sha256") != hashlib.sha256(registry_path.read_bytes()).hexdigest():
        errors.append("source_document_registry sha256 does not match the canonical registry")

    try:
        study_unit_ids, allocation_address_ids = _frozen_ids(root)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    canonical_registry = _root_json(root, _REGISTRY_PATH, "source document registry")
    if registry != canonical_registry:
        errors.append("source document registry does not match canonical registry content")
    registry_documents = registry.get("documents", [])
    if not isinstance(registry_documents, list):
        errors.append("source document registry documents must be a list")
        registry_documents = []
    registry_by_id: dict[str, str] = {}
    registry_urls: set[str] = set()
    for document in registry_documents:
        if not isinstance(document, dict):
            errors.append("source document registry document must be an object")
            continue
        document_id = document.get("document_id")
        url = document.get("canonical_url")
        if not isinstance(document_id, str) or not isinstance(url, str):
            errors.append("source document registry document ID or canonical URL is missing")
            continue
        try:
            canonical_url = _canonical_url(url)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        expected_id = "SRDOC-" + hashlib.sha256(canonical_url.encode()).hexdigest()[:16].upper()
        if document_id != expected_id:
            errors.append(f"SRDOC document-ID/content mismatch: {document_id}")
        if document_id in registry_by_id or canonical_url in registry_urls:
            errors.append(f"duplicate SRDOC document reference: {document_id}")
        registry_by_id[document_id] = canonical_url
        registry_urls.add(canonical_url)
    fndoc_ids: set[str] = set()
    fndoc_urls: set[str] = set()
    documents = artifact.get("documents", [])
    if isinstance(documents, list):
        for document in documents:
            if isinstance(document, dict):
                document_id = document.get("document_id")
                url = document.get("canonical_url")
                if isinstance(document_id, str):
                    if document_id in fndoc_ids:
                        errors.append(f"duplicate FNDOC document_id: {document_id}")
                    fndoc_ids.add(document_id)
                try:
                    if isinstance(url, str):
                        canonical_url = _canonical_url(url)
                        if canonical_url != url:
                            errors.append(f"FNDOC canonical_url is not normalized: {url}")
                        expected_id = "FNDOC-" + hashlib.sha256(canonical_url.encode()).hexdigest()[:16].upper()
                        if document_id != expected_id:
                            errors.append(f"FNDOC document-ID/content mismatch: {document_id}")
                        if canonical_url in fndoc_urls:
                            errors.append(f"duplicate FNDOC canonical_url: {canonical_url}")
                        if canonical_url in registry_urls:
                            errors.append(f"FNDOC canonical_url collides with SRDOC: {canonical_url}")
                        fndoc_urls.add(canonical_url)
                except ValueError as exc:
                    errors.append(str(exc))

    cards = artifact.get("claim_cards", [])
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, dict):
                continue
            claim_id = card.get("claim_card_id", "<unknown>")
            claim = card.get("claim")
            if isinstance(claim, str) and (";" in claim or "\n" in claim or "\r" in claim):
                errors.append(f"{claim_id}: claim must be atomic")
            for reference in card.get("scope_references", []):
                if not isinstance(reference, dict):
                    continue
                unit_id = reference.get("study_unit_id")
                address_id = reference.get("allocation_address_id")
                if isinstance(unit_id, str) and unit_id not in study_unit_ids:
                    errors.append(f"{claim_id}: unknown study_unit_id {unit_id}")
                if isinstance(address_id, str) and address_id not in allocation_address_ids:
                    errors.append(f"{claim_id}: unknown allocation_address_id {address_id}")
            for citation in card.get("citations", []):
                if not isinstance(citation, dict):
                    continue
                document_id = citation.get("document_id")
                if isinstance(document_id, str) and document_id not in registry_by_id.keys() | fndoc_ids:
                    errors.append(f"{claim_id}: unknown citation document_id {document_id}")
    return errors


def validate_foundational_evidence(root: Path, artifact: dict[str, Any], registry: dict[str, Any]) -> FoundationalEvidenceValidation:
    """Fail closed when a foundational card violates canonical boundaries."""
    root = Path(root).resolve()
    errors: list[str] = []
    try:
        build_foundational_evidence_model(root, artifact)
    except Exception as exc:  # schema errors are reported as validation failures
        errors.append(str(exc))
    try:
        errors.extend(_semantic_errors(root, artifact, registry))
    except (OSError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    status = "FAIL" if errors else "PASS"
    return FoundationalEvidenceValidation(status, {"FOUNDATIONAL_EVIDENCE": status}, errors)


def _fingerprints(root: Path) -> list[dict[str, str]]:
    return [
        {"path": relative, "sha256": hashlib.sha256(resolve_root_path(root, relative, label="foundational evidence audit input").read_bytes()).hexdigest()}
        for relative in _AUDIT_INPUTS
    ]


def build_foundational_evidence_audit(root: Path, artifact: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the exact provenance audit from canonical evidence inputs."""
    root = Path(root).resolve()
    validation = validate_foundational_evidence(root, artifact, registry)
    if validation.status != "PASS":
        raise ValueError("foundational evidence validation failed: " + "; ".join(validation.errors))
    cards = artifact["claim_cards"]
    documents = artifact["documents"]
    citations = [citation for card in cards for citation in card["citations"]]
    cited_ids = sorted({citation["document_id"] for citation in citations})
    srdoc_references = sum(citation["document_id"].startswith("SRDOC-") for citation in citations)
    fndoc_references = sum(citation["document_id"].startswith("FNDOC-") for citation in citations)
    return {
        "schema_version": "1.0",
        "scope": "FOUNDATIONAL_EVIDENCE_AUDIT",
        "input_fingerprints": _fingerprints(root),
        "claim_card_ids": sorted(card["claim_card_id"] for card in cards),
        "document_ids": sorted(document["document_id"] for document in documents),
        "cited_document_ids": cited_ids,
        "counts": {
            "CLAIM_CARDS": len(cards),
            "CITATIONS": len(citations),
            "SRDOC_REFERENCES": srdoc_references,
            "FNDOC_REFERENCES": fndoc_references,
            "FNDOC_DOCUMENTS": len(documents),
            "DUPLICATE_DOCUMENT_REFERENCES": 0,
            "MISSING_DOCUMENT_REFERENCES": 0,
        },
        "checks": {
            "FOUNDATIONAL_EVIDENCE": "PASS",
            "PROVENANCE": "PASS",
            "INPUT_FINGERPRINTS": "PASS",
        },
        "status": "PASS",
    }


def validate_foundational_evidence_audit(root: Path, artifact: dict[str, Any], registry: dict[str, Any], audit: dict[str, Any]) -> FoundationalEvidenceValidation:
    """Fail closed unless an audit exactly matches its deterministic rebuild."""
    try:
        expected = build_foundational_evidence_audit(Path(root), artifact, registry)
    except (OSError, TypeError, ValueError) as exc:
        return FoundationalEvidenceValidation("FAIL", {"FOUNDATIONAL_EVIDENCE_AUDIT": "FAIL"}, [str(exc)])
    errors = [] if audit == expected else ["foundational evidence audit does not match deterministic rebuild"]
    status = "FAIL" if errors else "PASS"
    return FoundationalEvidenceValidation(status, {"FOUNDATIONAL_EVIDENCE_AUDIT": status}, errors)


def write_foundational_evidence_audit(root: Path) -> dict[str, Any]:
    """Validate canonical inputs before atomically writing the derived audit."""
    root = Path(root).resolve()
    artifact = _root_json(root, _ARTIFACT_PATH, "foundational evidence claim cards")
    registry = _root_json(root, _REGISTRY_PATH, "source document registry")
    audit = build_foundational_evidence_audit(root, artifact, registry)
    validation = validate_foundational_evidence_audit(root, artifact, registry, audit)
    if validation.status != "PASS":
        raise ValueError("foundational evidence audit validation failed: " + "; ".join(validation.errors))
    write_json_atomic(resolve_root_path(root, _AUDIT_PATH, label="foundational evidence audit"), audit)
    return audit
