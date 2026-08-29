from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from qbank.source_document_registry import (
    build_source_document_registry,
    validate_source_document_registry,
)


REPO = Path(__file__).resolve().parents[1]


def _source(
    source_id: str,
    url: str,
    *,
    title: str = "National guidance",
    retrieval_date: str = "2026-08-28",
) -> dict:
    return {
        "source_id": source_id,
        "title": title,
        "issuing_organization": "Canadian Authority",
        "source_family": "CANADIAN_SPECIALTY_SOCIETY",
        "source_type": "CANADIAN_NATIONAL_GUIDELINE",
        "jurisdiction": "CANADA_NATIONAL",
        "is_canadian": True,
        "international_fallback": False,
        "publication_date": "2025-01-01",
        "update_date": None,
        "guideline_version": "Version 1",
        "date_status": "AVAILABLE",
        "version_status": "AVAILABLE",
        "currentness_status": "CURRENT",
        "currentness_notes": "Issuer site checked.",
        "retrieval_date": retrieval_date,
        "url": url,
    }


def _population(batch_id: str, packet_id: str, sources: list[dict]) -> dict:
    return {
        "research_batch_id": batch_id,
        "source_packets": [{
            "source_packet_id": packet_id,
            "authoritative_sources": sources,
        }],
    }


def test_registry_deduplicates_by_canonical_https_url_and_contains_metadata_only() -> None:
    populations = [
        _population("SRB-002", "SRC-MED-002", [_source("AUTH-002", " https://example.ca/guidance ")]),
        _population("SRB-001", "SRC-MED-001", [_source("AUTH-001", "https://example.ca/guidance")]),
    ]

    registry = build_source_document_registry(REPO, populations)

    assert registry["documents"] == [{
        "canonical_url": "https://example.ca/guidance",
        "currentness_status": "CURRENT",
        "date_status": "AVAILABLE",
        "document_id": "SRDOC-" + hashlib.sha256(b"https://example.ca/guidance").hexdigest()[:16].upper(),
        "first_packet_id": "SRC-MED-001",
        "guideline_version": "Version 1",
        "international_fallback": False,
        "is_canadian": True,
        "issuing_organization": "Canadian Authority",
        "jurisdiction": "CANADA_NATIONAL",
        "last_packet_id": "SRC-MED-002",
        "latest_retrieval_date": "2026-08-28",
        "packet_ids": ["SRC-MED-001", "SRC-MED-002"],
        "publication_date": "2025-01-01",
        "source_family": "CANADIAN_SPECIALTY_SOCIETY",
        "source_ids": ["AUTH-001", "AUTH-002"],
        "source_type": "CANADIAN_NATIONAL_GUIDELINE",
        "title": "National guidance",
        "update_date": None,
        "version_status": "AVAILABLE",
    }]
    rendered = repr(registry["documents"])
    assert all(term not in rendered for term in ("recommendation", "boundary", "exception", "statement"))


def test_registry_preserves_source_and_packet_provenance_in_canonical_order() -> None:
    populations = [
        _population("SRB-010", "SRC-Z", [_source("AUTH-Z", "https://example.ca/z")]),
        _population("SRB-001", "SRC-B", [_source("AUTH-B", "https://example.ca/shared")]),
        _population("SRB-001", "SRC-A", [_source("AUTH-A", "https://example.ca/shared")]),
    ]

    registry = build_source_document_registry(REPO, populations)

    shared = next(item for item in registry["documents"] if item["canonical_url"] == "https://example.ca/shared")
    assert shared["source_ids"] == ["AUTH-A", "AUTH-B"]
    assert shared["packet_ids"] == ["SRC-A", "SRC-B"]
    assert shared["first_packet_id"] == "SRC-A"
    assert shared["last_packet_id"] == "SRC-B"


def test_registry_rejects_one_source_id_with_incompatible_metadata() -> None:
    populations = [_population("SRB-001", "SRC-A", [
        _source("AUTH-1", "https://example.ca/a"),
        _source("AUTH-1", "https://example.ca/b", title="Different guidance"),
    ])]

    result = validate_source_document_registry(REPO, populations, {"documents": []})

    assert result.status == "FAIL"
    assert any("source ID has incompatible metadata" in error for error in result.errors)


def test_registry_rejects_one_url_with_incompatible_document_identity() -> None:
    populations = [_population("SRB-001", "SRC-A", [
        _source("AUTH-1", "https://example.ca/a"),
        _source("AUTH-2", "https://example.ca/a", title="Different guidance"),
    ])]

    result = validate_source_document_registry(REPO, populations, {"documents": []})

    assert result.status == "FAIL"
    assert any("canonical URL has incompatible document identity" in error for error in result.errors)


def test_registry_rebuild_is_byte_deterministic() -> None:
    populations = [_population("SRB-001", "SRC-A", [_source("AUTH-1", "https://example.ca/a", retrieval_date="2026-08-27")])]

    first = build_source_document_registry(REPO, populations)
    second = build_source_document_registry(REPO, deepcopy(populations))

    assert first == second
    assert validate_source_document_registry(REPO, populations, first).status == "PASS"
