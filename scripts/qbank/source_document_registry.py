"""Build a metadata-only registry of documents used by source packets."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from .jsonio import write_json_atomic
from .paths import resolve_root_path


_IDENTITY_FIELDS = (
    "title", "issuing_organization", "source_family", "source_type",
    "jurisdiction", "is_canadian", "international_fallback",
    "publication_date", "update_date", "guideline_version", "date_status",
    "version_status", "currentness_status",
)
_REGISTRY_PATH = "research/qgen/source_document_registry.json"


@dataclass
class SourceDocumentRegistryValidation:
    status: str
    checks: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _canonical_url(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("source URL must be a string")
    canonical = value.strip()
    if not canonical.startswith("https://"):
        raise ValueError("source URL must use HTTPS")
    return canonical


def _identity(source: dict[str, Any]) -> tuple[Any, ...]:
    missing = [name for name in _IDENTITY_FIELDS if name not in source]
    if missing:
        raise ValueError(f"source document identity is incomplete: {', '.join(missing)}")
    return tuple(source[name] for name in _IDENTITY_FIELDS)


def _input_population_record(root: Path, population: dict[str, Any]) -> dict[str, str]:
    batch_id = population.get("research_batch_id", population.get("pilot_research_batch_id"))
    if not isinstance(batch_id, str) or not batch_id:
        raise ValueError("population research batch ID is missing")
    relative = f"research/qgen/source_packet_population_{batch_id.lower().replace('-', '_')}.json"
    path = resolve_root_path(root, relative, label="source packet population")
    if path.is_file():
        payload = path.read_bytes()
    else:
        payload = (json.dumps(population, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    return {"path": relative, "sha256": hashlib.sha256(payload).hexdigest()}


def _sources(populations: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    for population in populations:
        if not isinstance(population, dict):
            raise ValueError("source packet population must be an object")
        packets = population.get("source_packets")
        if not isinstance(packets, list):
            raise ValueError("source packet population packets must be a list")
        for packet in packets:
            if not isinstance(packet, dict) or not isinstance(packet.get("source_packet_id"), str):
                raise ValueError("source packet ID is missing")
            sources = packet.get("authoritative_sources", [])
            if not isinstance(sources, list):
                raise ValueError(f"{packet['source_packet_id']}: authoritative sources must be a list")
            for source in sources:
                if not isinstance(source, dict):
                    raise ValueError(f"{packet['source_packet_id']}: authoritative source must be an object")
                records.append((packet["source_packet_id"], source))
    return records


def build_source_document_registry(root: Path, populations: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministically derive metadata-only records from integrated populations."""
    root = Path(root).resolve()
    if not isinstance(populations, list):
        raise ValueError("source packet populations must be a list")
    by_url: dict[str, dict[str, Any]] = {}
    identity_by_source_id: dict[str, tuple[Any, ...]] = {}
    for packet_id, source in _sources(populations):
        source_id = source.get("source_id")
        retrieval_date = source.get("retrieval_date")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError(f"{packet_id}: source ID is missing")
        if not isinstance(retrieval_date, str) or not retrieval_date.strip():
            raise ValueError(f"{packet_id}: source retrieval date is missing")
        canonical_url = _canonical_url(source.get("url"))
        identity = _identity(source)
        existing_source_identity = identity_by_source_id.setdefault(source_id, identity)
        if existing_source_identity != identity:
            raise ValueError(f"{source_id}: source ID has incompatible metadata")
        existing = by_url.setdefault(canonical_url, {"identity": identity, "source_ids": set(), "packet_ids": set(), "retrieval_dates": set()})
        if existing["identity"] != identity:
            raise ValueError(f"{canonical_url}: canonical URL has incompatible document identity")
        existing["source_ids"].add(source_id)
        existing["packet_ids"].add(packet_id)
        existing["retrieval_dates"].add(retrieval_date)

    documents: list[dict[str, Any]] = []
    for canonical_url, metadata in sorted(by_url.items()):
        identity = dict(zip(_IDENTITY_FIELDS, metadata["identity"], strict=True))
        packet_ids = sorted(metadata["packet_ids"])
        documents.append({
            "document_id": "SRDOC-" + hashlib.sha256(canonical_url.encode()).hexdigest()[:16].upper(),
            "canonical_url": canonical_url,
            **identity,
            "source_ids": sorted(metadata["source_ids"]),
            "packet_ids": packet_ids,
            "first_packet_id": packet_ids[0],
            "last_packet_id": packet_ids[-1],
            "latest_retrieval_date": max(metadata["retrieval_dates"]),
        })
    inputs = sorted((_input_population_record(root, population) for population in populations), key=lambda item: item["path"])
    return {
        "schema_version": "1.0",
        "scope": "SOURCE_DOCUMENT_REGISTRY",
        "input_populations": inputs,
        "documents": documents,
    }


def validate_source_document_registry(root: Path, populations: list[dict[str, Any]], registry: dict[str, Any]) -> SourceDocumentRegistryValidation:
    """Fail closed when source metadata conflicts or registry output is not rebuilt exactly."""
    try:
        expected = build_source_document_registry(root, populations)
    except (TypeError, ValueError) as exc:
        return SourceDocumentRegistryValidation("FAIL", {"SOURCE_DOCUMENT_REGISTRY": "FAIL"}, [str(exc)])
    errors = [] if registry == expected else ["source document registry does not match deterministic rebuild"]
    return SourceDocumentRegistryValidation("FAIL" if errors else "PASS", {"SOURCE_DOCUMENT_REGISTRY": "FAIL" if errors else "PASS"}, errors)


def write_source_document_registry(root: Path, populations: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate before atomically writing the derived registry artifact."""
    registry = build_source_document_registry(root, populations)
    validation = validate_source_document_registry(root, populations, registry)
    if validation.status != "PASS":
        raise ValueError("source document registry validation failed: " + "; ".join(validation.errors))
    write_json_atomic(resolve_root_path(Path(root).resolve(), _REGISTRY_PATH, label="source document registry"), registry)
    return registry
