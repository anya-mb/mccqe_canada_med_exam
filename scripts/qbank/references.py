"""Canonical reference identity and conservative registry merging."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from .errors import QbankError


class ReferenceMergeError(QbankError):
    """A registry cannot be merged without losing source provenance."""


_REQUIRED_FIELDS = (
    "reference_id",
    "title",
    "organization",
    "url",
    "publication_or_update_date",
    "accessed_date",
    "source_tier",
    "supports",
)


def _normalize_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ReferenceMergeError(f"reference {field} must be a string")
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not normalized:
        raise ReferenceMergeError(f"reference {field} must not be empty")
    return normalized


def _normalize_url(value: object) -> tuple[str, str | None]:
    url = _normalize_text(value, "url")
    parsed = urlsplit(url)
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise ReferenceMergeError("reference url must be an absolute https URL")
    if parsed.username is not None or parsed.password is not None:
        raise ReferenceMergeError("reference url must not contain userinfo")

    hostname = parsed.hostname.casefold()
    try:
        port = parsed.port
    except ValueError as exc:
        raise ReferenceMergeError("reference url has an invalid port") from exc
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    authority = hostname if port in {None, 443} else f"{hostname}:{port}"
    path = parsed.path.rstrip("/")
    canonical = urlunsplit(("https", authority, path, parsed.query, ""))
    return canonical, parsed.fragment or None


def _identity(record: dict) -> tuple[str, str, str, str]:
    """Return canonical source metadata; support claims are intentionally absent."""
    return (
        record["organization"].casefold(),
        record["title"].casefold(),
        record["url"],
        record["publication_or_update_date"],
    )


def _organization_slug(organization: str) -> str:
    ascii_organization = (
        unicodedata.normalize("NFKD", organization).encode("ascii", "ignore").decode()
    )
    slug = "-".join(re.findall(r"[A-Za-z0-9]+", ascii_organization.upper()))
    return (slug or "SOURCE")[:48].rstrip("-")


def _stable_id(record: dict) -> str:
    encoded_identity = json.dumps(_identity(record), separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(encoded_identity.encode("utf-8")).hexdigest()[:12].upper()
    return f"REF-{_organization_slug(_identity(record)[0])}-{digest}"


def _normalize_supports(
    value: object, *, url_fragment: str | None = None
) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ReferenceMergeError("reference supports must be a non-empty list")
    pairs: set[tuple[str, str]] = set()
    for support in value:
        if not isinstance(support, dict):
            raise ReferenceMergeError("reference support must be an object")
        locator = _normalize_text(support.get("locator"), "support locator")
        if url_fragment is not None:
            locator = f"{locator} (URL fragment: #{url_fragment})"
        pairs.add((_normalize_text(support.get("claim"), "support claim"), locator))
    return [
        {"claim": claim, "locator": locator}
        for claim, locator in sorted(pairs, key=lambda pair: (pair[0].casefold(), pair[1].casefold(), pair))
    ]


def _canonicalize(record: object) -> dict:
    if not isinstance(record, dict):
        raise ReferenceMergeError("reference must be an object")
    missing = [field for field in _REQUIRED_FIELDS if field not in record]
    if missing:
        raise ReferenceMergeError(f"reference is missing required fields: {', '.join(missing)}")
    source_tier = record["source_tier"]
    if type(source_tier) is not int or not 1 <= source_tier <= 4:
        raise ReferenceMergeError("reference source_tier must be an integer from 1 through 4")
    url, url_fragment = _normalize_url(record["url"])
    return {
        "reference_id": _normalize_text(record["reference_id"], "reference_id"),
        "title": _normalize_text(record["title"], "title"),
        "organization": _normalize_text(record["organization"], "organization"),
        "url": url,
        "publication_or_update_date": _normalize_text(
            record["publication_or_update_date"], "publication_or_update_date"
        ),
        "accessed_date": _normalize_text(record["accessed_date"], "accessed_date"),
        "source_tier": source_tier,
        "supports": _normalize_supports(
            record["supports"], url_fragment=url_fragment
        ),
    }


def _immutable_metadata(record: dict) -> tuple[str, str, str, str, int]:
    return (*_identity(record), record["source_tier"])


def _index_records(records: list[object]) -> tuple[dict[tuple[str, str, str, str], dict], dict[str, dict]]:
    by_identity: dict[tuple[str, str, str, str], dict] = {}
    by_id: dict[str, dict] = {}
    for source_record in records:
        record = _canonicalize(source_record)
        identity = _identity(record)
        if identity in by_identity:
            raise ReferenceMergeError("registry contains a canonical identity collision")
        if record["reference_id"] in by_id:
            raise ReferenceMergeError("registry contains a reference_id collision")
        by_identity[identity] = record
        by_id[record["reference_id"]] = record
    return by_identity, by_id


def _merge_supports(current: list[dict], incoming: list[dict]) -> list[dict[str, str]]:
    return _normalize_supports([*current, *incoming])


def merge_references(registry: dict, incoming: list[dict]) -> tuple[dict, dict[str, str]]:
    """Merge validated references without conflating distinct canonical sources.

    Identity consists only of normalized organization, title, HTTPS URL, and
    publication/update date. Source tier is immutable metadata and therefore a
    disagreement for the same source fails closed. Access dates are observed
    metadata, so the latest ISO date is retained. Claims are merged only when
    their normalized claim and locator pair is exactly equal.
    """
    if not isinstance(registry, dict) or not isinstance(registry.get("references"), list):
        raise ReferenceMergeError("registry must contain a references list")
    if not isinstance(incoming, list):
        raise ReferenceMergeError("incoming references must be a list")

    merged_registry = deepcopy(registry)
    by_identity, by_id = _index_records(merged_registry["references"])
    mapping: dict[str, str] = {}
    incoming_ids: dict[str, dict] = {}

    for raw_record in incoming:
        record = _canonicalize(raw_record)
        incoming_id = record["reference_id"]
        identity = _identity(record)

        prior_incoming = incoming_ids.get(incoming_id)
        if (
            prior_incoming is not None
            and _immutable_metadata(prior_incoming) != _immutable_metadata(record)
        ):
            raise ReferenceMergeError(f"reference_id collision for {incoming_id}")
        incoming_ids[incoming_id] = record

        prior_id_record = by_id.get(incoming_id)
        if prior_id_record is not None and _immutable_metadata(prior_id_record) != _immutable_metadata(record):
            raise ReferenceMergeError(f"reference_id collision for {incoming_id}")

        existing = by_identity.get(identity)
        if existing is not None:
            if _immutable_metadata(existing) != _immutable_metadata(record):
                raise ReferenceMergeError("conflicting immutable metadata for canonical reference")
            existing["accessed_date"] = max(existing["accessed_date"], record["accessed_date"])
            existing["supports"] = _merge_supports(existing["supports"], record["supports"])
            stable_id = existing["reference_id"]
        else:
            stable_id = _stable_id(record)
            id_collision = by_id.get(stable_id)
            if id_collision is not None and _identity(id_collision) != identity:
                raise ReferenceMergeError(f"stable reference_id collision for {stable_id}")
            record["reference_id"] = stable_id
            by_identity[identity] = record
            by_id[stable_id] = record

        mapping[incoming_id] = stable_id

    merged_registry["references"] = sorted(
        by_identity.values(), key=lambda record: record["reference_id"]
    )
    return merged_registry, mapping
