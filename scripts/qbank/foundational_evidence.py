"""Validate the additive foundational-evidence claim-card corpus."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from .jsonio import read_json
from .paths import resolve_root_path
from .schema import validate_instance
from .source_document_registry import _canonical_url


_REGISTRY_PATH = "research/qgen/source_document_registry.json"
_SCOPE_PATH = "research/scope/master_scope_crosswalk.json"
_ALLOCATION_PATH = "research/scope/final_question_allocation.json"


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
    registry_ids = {
        document.get("document_id") for document in registry.get("documents", [])
        if isinstance(document, dict) and isinstance(document.get("document_id"), str)
    }
    fndoc_ids: set[str] = set()
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
                    if isinstance(url, str) and _canonical_url(url) != url:
                        errors.append(f"FNDOC canonical_url is not normalized: {url}")
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
                if isinstance(document_id, str) and document_id not in registry_ids | fndoc_ids:
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
