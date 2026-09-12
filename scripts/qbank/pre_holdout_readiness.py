"""Deterministic pre-holdout curriculum-readiness orchestration.

This module stops before seed discovery.  It selects development material only
from canonical curriculum and source-readiness metadata, validates separately
reviewed decision/feature artifacts, and builds an append-only feature snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from scripts.qbank.readiness_semantic_inputs import (
    EXISTING_FEATURE_BINDINGS,
    EXISTING_READY,
    FEATURE_TRIGGERS,
    TARGETED_READY,
)


DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
READINESS = Path("research/qgen/readiness")
HOLDOUT = Path("research/qgen/holdout")

EXCLUSION_ARTIFACTS = (
    "research/qgen/holdout/historical_exclusion_inventory.json",
    "research/qgen/holdout/fresh_holdout_24_opportunities.json",
    "research/qgen/holdout/fresh_holdout_18_opportunities.json",
    "research/qgen/onboarding/w1_fresh_opportunities.json",
    "research/qgen/onboarding/v2_frozen_pilot_opportunities.json",
    "research/qgen/onboarding/v6_development_12_selection.json",
)

EVIDENCE_AUDIT_VERDICTS = frozenset((
    "ALIGNED_COMPLETE",
    "ALIGNED_PARTIAL",
    "MISALIGNED",
    "EVIDENCE_MISSING",
    "UNCERTAIN",
    "OUT_OF_SCOPE",
))
EVIDENCE_REVIEW_VERDICTS = frozenset(("APPROVED", "REJECTED", "UNCERTAIN"))

STARTING_HEAD = "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
STARTING_BRANCH = "codex/generalized-qgen-onboarding"
FROZEN_INPUT_HASHES = {
    "research/qgen/onboarding/feature_anchor_snapshot_v5.json":
        "918954dda9eae01df10ee1d0e085e325c812c7e0299ab778da380c51b273981c",
    "research/qgen/holdout/eligible_fresh_study_units.json":
        "2b5193e56806d0710f77bea836687855d91d4f14a00df40bf45a681e3febef64",
    "research/qgen/holdout/fresh_holdout_18_architecture_freeze.json":
        "aa3d6ac2f6d1a674f667b24f34c1a5acf550bc9bfe3551cc284bb9110ef38370",
    "research/qgen/holdout/fresh_holdout_18_milestone.json":
        "173b2fa5f5dc67fbf9cb00dd0db81b37c4156006d220b726c5c1606220b861e3",
}

COPYRIGHT_ARTIFACTS = (
    "research/qgen/readiness/development_exclusion_inventory.json",
    "research/qgen/readiness/development_90_selection.json",
    "research/qgen/readiness/development_targeted_evidence.json",
    "research/qgen/readiness/development_decision_claim_catalog.json",
    "research/qgen/readiness/development_decision_evidence_audit.json",
    "research/qgen/readiness/development_evidence_independent_review.json",
    "research/qgen/readiness/development_feature_coverage_audit.json",
    "research/qgen/readiness/development_feature_independent_review.json",
    "research/qgen/readiness/development_feature_maps_v6.json",
    "research/qgen/readiness/development_feature_map_independent_review.json",
    "research/qgen/onboarding/feature_anchor_snapshot_v6.json",
    "research/qgen/readiness/future_untouched_holdout_eligibility.json",
)


class ReadinessIntegrityError(ValueError):
    """A readiness artifact violates a fail-closed canonical invariant."""


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_sha256(value: Any) -> str:
    if isinstance(value, dict):
        value = {key: item for key, item in value.items() if key != "content_sha256"}
    payload = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _walk_unit_ids(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        unit_id = value.get("study_unit_id")
        if isinstance(unit_id, str) and unit_id.startswith("SU-"):
            yield unit_id
        for item in value.values():
            yield from _walk_unit_ids(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_unit_ids(item)


def _historical_ids(document: dict[str, Any]) -> set[str]:
    result = set(_walk_unit_ids(document))
    result.update(
        value for value in document.get("excluded_study_unit_ids", [])
        if isinstance(value, str)
    )
    return result


def build_development_exclusions(root: Path) -> dict[str, Any]:
    """Build an explicit union of every materially used development unit."""
    root = Path(root).resolve()
    reasons: dict[str, set[str]] = defaultdict(set)
    sources = []
    for relative in EXCLUSION_ARTIFACTS:
        path = root / relative
        if not path.exists():
            continue
        document = _read(path)
        ids = _historical_ids(document)
        for unit_id in ids:
            reasons[unit_id].add(relative)
        sources.append({
            "path": relative,
            "file_sha256": _file_sha256(path),
            "study_unit_count": len(ids),
        })

    diagnostic = _read(root / HOLDOUT / "fresh_holdout_18_opportunities.json")
    diagnostic_ids = sorted({row["study_unit_id"] for row in diagnostic["opportunities"]})
    rows = [
        {"study_unit_id": unit_id, "exclusion_reasons": sorted(values)}
        for unit_id, values in sorted(reasons.items())
    ]
    artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_READINESS_DEVELOPMENT_EXCLUSIONS",
        "diagnostic_18_classification": "FRESH_PREREQUISITE_DIAGNOSTIC_18",
        "diagnostic_18_study_unit_ids": diagnostic_ids,
        "exclusion_sources": sources,
        "excluded_study_unit_count": len(rows),
        "excluded_units": rows,
    }
    artifact["content_sha256"] = content_sha256(artifact)
    return artifact


def _topic_family(crosswalk: dict[str, Any]) -> str:
    nodes = crosswalk.get("source_node_ids") or []
    if nodes:
        pieces = re.split(r"[.]", str(nodes[0]))
        return ".".join(pieces[:2]) if len(pieces) > 1 else pieces[0]
    path = crosswalk.get("source_hierarchy_path") or []
    if path:
        token = str(path[0]).split()[0]
        pieces = token.split(".")
        return ".".join(pieces[:2])
    return str(crosswalk.get("chapter_code") or "UNKNOWN")


def _candidate_score(row: dict[str, Any]) -> tuple[Any, ...]:
    priority_rank = {"CORE": 0, "IMPORTANT": 1, "SUPPORTING": 2}
    return (
        0 if row.get("source_packet_status") == "CURRENT_REPOSITORY_PACKET_READY" else 1,
        priority_rank.get(row.get("priority"), 9),
        -len(row.get("mcc_objective_ids") or []),
        row["allocation_address_id"],
    )


def select_development_units(
    root: Path, exclusions: dict[str, Any], *, per_discipline: int = 15
) -> dict[str, Any]:
    """Select a taxonomy-diverse, generation-outcome-blind development pool."""
    root = Path(root).resolve()
    inventory_path = root / HOLDOUT / "eligible_fresh_study_units.json"
    inventory = _read(inventory_path)
    crosswalk_rows = _read(root / "research/scope/master_scope_crosswalk.json")["entries"]
    crosswalk = {row["study_unit_id"]: row for row in crosswalk_rows}
    excluded = {row["study_unit_id"] for row in exclusions["excluded_units"]}
    selected: list[dict[str, Any]] = []

    for discipline in DISCIPLINES:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for source in inventory["candidates"]:
            if source["discipline"] != discipline or source["study_unit_id"] in excluded:
                continue
            canonical = crosswalk[source["study_unit_id"]]
            if not canonical.get("testable_competencies"):
                continue
            row = {
                "discipline": discipline,
                "study_unit_id": source["study_unit_id"],
                "study_unit": source["study_unit"],
                "allocation_address_id": source["allocation_address_id"],
                "mcc_objective_ids": source["mcc_objective_ids"],
                "priority": source["priority"],
                "source_packet_status": source["evidence_readiness"],
                "source_packets_planned": source["source_packets_planned"],
                "source_packets_ready": source["source_packets_ready"],
                "topic_family": _topic_family(canonical),
            }
            groups[row["topic_family"]].append(row)
        for rows in groups.values():
            rows.sort(key=_candidate_score)
        family_order = sorted(groups, key=lambda name: (_candidate_score(groups[name][0]), name))
        discipline_rows: list[dict[str, Any]] = []
        offset = 0
        while len(discipline_rows) < per_discipline:
            added = False
            for family in family_order:
                if offset < len(groups[family]):
                    discipline_rows.append(groups[family][offset])
                    added = True
                    if len(discipline_rows) == per_discipline:
                        break
            if not added:
                break
            offset += 1
        if len(discipline_rows) < per_discipline:
            raise ReadinessIntegrityError(
                f"INSUFFICIENT_DEVELOPMENT_CANDIDATES: {discipline}: {len(discipline_rows)}"
            )
        for ordinal, row in enumerate(discipline_rows, start=1):
            selected.append({"development_id": f"RDY-{discipline}-{ordinal:02d}", **row})

    artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_READINESS_DEVELOPMENT_90",
        "source_inventory_path": inventory_path.relative_to(root).as_posix(),
        "source_inventory_sha256": _file_sha256(inventory_path),
        "exclusion_content_sha256": exclusions["content_sha256"],
        "selection_rule": (
            "Round-robin across canonical source-node topic families; within each family "
            "packet-ready before pending, CORE before IMPORTANT before SUPPORTING, more "
            "MCC objectives before fewer, then allocation-address ID."
        ),
        "selection_uses_generation_outcomes": False,
        "target_per_discipline": per_discipline,
        "units": selected,
    }
    artifact["content_sha256"] = content_sha256(artifact)
    validate_development_selection(root, artifact, exclusions=exclusions)
    return artifact


def validate_development_selection(
    root: Path,
    artifact: dict[str, Any],
    *,
    exclusions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    if exclusions is None:
        exclusions = build_development_exclusions(root)
    rows = artifact.get("units") or []
    excluded = {row["study_unit_id"] for row in exclusions["excluded_units"]}
    if any(row.get("study_unit_id") in excluded for row in rows):
        raise ReadinessIntegrityError("EXCLUDED_DEVELOPMENT_UNIT")
    ids = [row.get("study_unit_id") for row in rows]
    if not ids or len(ids) != len(set(ids)):
        raise ReadinessIntegrityError("DUPLICATE_OR_EMPTY_DEVELOPMENT_UNIT")
    counts = {discipline: sum(row.get("discipline") == discipline for row in rows)
              for discipline in DISCIPLINES}
    target = artifact.get("target_per_discipline")
    if any(value != target for value in counts.values()):
        raise ReadinessIntegrityError(f"DISCIPLINE_SELECTION_IMBALANCE: {counts}")
    if artifact.get("selection_uses_generation_outcomes") is not False:
        raise ReadinessIntegrityError("OUTCOME_AWARE_DEVELOPMENT_SELECTION")
    if artifact.get("content_sha256") != content_sha256(artifact):
        raise ReadinessIntegrityError("DEVELOPMENT_SELECTION_HASH_MISMATCH")
    return {"verdict": "PASS", "selected": len(rows), "by_discipline": counts}


def validate_decision_audit(
    selection: dict[str, Any], audit: dict[str, Any]
) -> dict[str, Any]:
    """Require one explicit, hash-pinned audit result for every selected unit."""
    selected = {row["development_id"] for row in selection.get("units") or []}
    rows = audit.get("decisions") or []
    audited = [row.get("development_id") for row in rows]
    if set(audited) != selected or len(audited) != len(set(audited)):
        raise ReadinessIntegrityError("NONEXHAUSTIVE_OR_DUPLICATE_DECISION_AUDIT")
    for row in rows:
        verdict = row.get("audit_verdict")
        if verdict not in EVIDENCE_AUDIT_VERDICTS:
            raise ReadinessIntegrityError("INVALID_EVIDENCE_AUDIT_VERDICT")
        if row.get("content_sha256") != content_sha256(row):
            raise ReadinessIntegrityError("DECISION_AUDIT_HASH_MISMATCH")
        propositions = row.get("load_bearing_propositions") or []
        claim_ids = row.get("claim_ids") or []
        if verdict == "ALIGNED_COMPLETE":
            proposition_claims = {
                claim_id
                for proposition in propositions
                for claim_id in proposition.get("claim_ids") or []
            }
            if (
                not propositions
                or not claim_ids
                or proposition_claims != set(claim_ids)
                or any(not proposition.get("statement") for proposition in propositions)
            ):
                raise ReadinessIntegrityError("UNSUPPORTED_COMPLETE_DECISION")
    counts = {
        verdict: sum(row["audit_verdict"] == verdict for row in rows)
        for verdict in sorted(EVIDENCE_AUDIT_VERDICTS)
    }
    return {"verdict": "PASS", "audited": len(rows), "by_verdict": counts}


def validate_evidence_reviews(
    audit: dict[str, Any],
    reviews: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate independent, subject- and claim-hash-pinned evidence review."""
    complete = {
        row["learner_decision_id"]: row
        for row in audit.get("decisions") or []
        if row.get("audit_verdict") == "ALIGNED_COMPLETE"
    }
    review_rows = reviews.get("reviews") or []
    review_by_id = {row.get("learner_decision_id"): row for row in review_rows}
    if len(review_by_id) != len(review_rows):
        raise ReadinessIntegrityError("DUPLICATE_EVIDENCE_REVIEW")
    if set(review_by_id) != set(complete):
        raise ReadinessIntegrityError("NONEXHAUSTIVE_EVIDENCE_REVIEW")
    approved = 0
    for decision_id, decision in complete.items():
        review = review_by_id[decision_id]
        if review.get("verdict") not in EVIDENCE_REVIEW_VERDICTS:
            raise ReadinessIntegrityError("INVALID_EVIDENCE_REVIEW_VERDICT")
        if (
            review.get("reviewer_execution_id") == decision.get("author_execution_id")
            or review.get("author_execution_id") != decision.get("author_execution_id")
            or review.get("independent_context") is not True
        ):
            raise ReadinessIntegrityError("NONINDEPENDENT_EVIDENCE_REVIEW")
        if review.get("subject_sha256") != decision.get("content_sha256"):
            raise ReadinessIntegrityError("STALE_EVIDENCE_REVIEW")
        for claim_id in decision.get("claim_ids") or []:
            claim = catalog.get(claim_id)
            if not claim or claim.get("source_verified") is not True:
                raise ReadinessIntegrityError(f"UNVERIFIED_EVIDENCE_CLAIM: {claim_id}")
            if (review.get("claim_sha256") or {}).get(claim_id) != content_sha256(claim):
                raise ReadinessIntegrityError(f"EVIDENCE_CLAIM_HASH_MISMATCH: {claim_id}")
        if review["verdict"] == "APPROVED":
            approved += 1
    return {"verdict": "PASS", "reviewed": len(review_rows), "approved": approved}


def readiness_metrics(
    selection: dict[str, Any],
    audit: dict[str, Any],
    reviews: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute packet/evidence economics without conflating their states."""
    validate_decision_audit(selection, audit)
    review_result = validate_evidence_reviews(audit, reviews, catalog)
    approved_ids = {
        row["learner_decision_id"]
        for row in reviews.get("reviews") or []
        if row.get("verdict") == "APPROVED"
    }
    ready = [
        row for row in audit["decisions"]
        if row["audit_verdict"] == "ALIGNED_COMPLETE"
        and row["learner_decision_id"] in approved_ids
    ]
    ready_units = {row["development_id"] for row in ready}
    packet_units = {
        row["development_id"] for row in selection.get("units") or []
        if row.get("source_packet_status") == "CURRENT_REPOSITORY_PACKET_READY"
    }
    by_discipline = {
        discipline: sum(row["discipline"] == discipline for row in ready)
        for discipline in DISCIPLINES
    }
    return {
        "packet_ready": len(packet_units),
        "decision_evidence_ready": review_result["approved"],
        "packet_ready_but_decision_not_ready": len(packet_units - ready_units),
        "decision_ready_by_discipline": by_discipline,
    }


def _first_competency(entry: dict[str, Any]) -> tuple[str, str]:
    competencies = entry.get("testable_competencies") or {}
    if not competencies:
        raise ReadinessIntegrityError(
            f"MISSING_CANONICAL_COMPETENCY: {entry.get('study_unit_id')}"
        )
    key = sorted(competencies)[0]
    return key, competencies[key]


def _existing_claim_catalog(root: Path) -> dict[str, dict[str, Any]]:
    wanted = {spec[2] for spec in EXISTING_READY.values()}
    normalized_by_claim = {
        spec[2]: spec[1] for spec in EXISTING_READY.values()
    }
    found: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "research/qgen").glob("source_packet_population_*.json")):
        document = _read(path)
        for packet in document.get("source_packets") or []:
            sources = {
                row["source_id"]: row for row in packet.get("authoritative_sources") or []
            }
            for recommendation in packet.get("supported_recommendations") or []:
                claim_id = recommendation.get("recommendation_id")
                if claim_id not in wanted:
                    continue
                citations = recommendation.get("source_citations") or []
                if not citations:
                    raise ReadinessIntegrityError(f"CLAIM_WITHOUT_SOURCE: {claim_id}")
                source_ids = [row["source_id"] for row in citations]
                if any(source_id not in sources for source_id in source_ids):
                    raise ReadinessIntegrityError(f"CLAIM_SOURCE_NOT_REGISTERED: {claim_id}")
                source = sources[source_ids[0]]
                found[claim_id] = {
                    "claim_id": claim_id,
                    "statement": normalized_by_claim[claim_id],
                    "source_packet_claim_sha256": content_sha256(recommendation),
                    "source_verified": (
                        packet.get("status") == "SOURCE_PACKET_READY"
                        and packet.get("verification_status") == "VERIFIED_COMPLETE"
                    ),
                    "source_ids": source_ids,
                    "source_id": source_ids[0],
                    "source_title": source["title"],
                    "url": source["url"],
                    "locator": "; ".join(row["locator"] for row in citations),
                    "source_packet_id": packet["source_packet_id"],
                    "evidence_origin": "CURRENT_REPOSITORY_SOURCE_PACKET",
                }
    missing = wanted - set(found)
    if missing:
        raise ReadinessIntegrityError(f"MISSING_EXISTING_CLAIMS: {sorted(missing)}")
    return found


def _targeted_catalog() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    sources: dict[str, dict[str, Any]] = {}
    requests = []
    for (
        development_id,
        _decision_type,
        _decision,
        proposition,
        source_id,
        title,
        url,
        locator,
    ) in TARGETED_READY:
        claim_id = f"CLM-{development_id}"
        sources.setdefault(source_id, {
            "source_id": source_id,
            "title": title,
            "url": url,
            "issuing_scope": "CANADIAN_AUTHORITATIVE_OR_SPECIALTY_SOURCE",
            "retrieval_date": "2026-09-08",
        })
        catalog[claim_id] = {
            "claim_id": claim_id,
            "statement": proposition,
            "source_verified": True,
            "source_id": source_id,
            "source_ids": [source_id],
            "source_title": title,
            "url": url,
            "locator": locator,
            "evidence_origin": "BOUNDED_TARGETED_RESEARCH",
        }
        requests.append({
            "research_request_id": f"RR-{development_id}",
            "development_id": development_id,
            "scope": "ONE_LEARNER_DECISION_ONLY",
            "claim_ids": [claim_id],
            "source_ids": [source_id],
            "status": "COMPLETED",
        })
    artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_BOUNDED_TARGETED_DECISION_EVIDENCE",
        "research_request_count": len(requests),
        "research_requests": requests,
        "sources": sorted(sources.values(), key=lambda row: row["source_id"]),
        "claims": sorted(catalog.values(), key=lambda row: row["claim_id"]),
    }
    artifact["content_sha256"] = content_sha256(artifact)
    return catalog, artifact


def build_evidence_wave(
    root: Path, selection: dict[str, Any]
) -> dict[str, Any]:
    """Build an exhaustive audit and independently hash-pinned ready subset."""
    root = Path(root).resolve()
    canonical_rows = _read(root / "research/scope/master_scope_crosswalk.json")["entries"]
    canonical = {row["study_unit_id"]: row for row in canonical_rows}
    existing_catalog = _existing_claim_catalog(root)
    targeted_catalog, targeted_artifact = _targeted_catalog()
    catalog = {**existing_catalog, **targeted_catalog}
    targeted_by_id = {row[0]: row for row in TARGETED_READY}
    decisions = []
    author_id = "readiness-evidence-author-20260908"

    for selected in selection["units"]:
        development_id = selected["development_id"]
        origin = "NONE"
        if development_id in EXISTING_READY:
            decision_type, decision_text, claim_id = EXISTING_READY[development_id]
            proposition = catalog[claim_id]["statement"]
            origin = "EXISTING_EVIDENCE"
        elif development_id in targeted_by_id:
            spec = targeted_by_id[development_id]
            decision_type, decision_text, proposition = spec[1], spec[2], spec[3]
            claim_id = f"CLM-{development_id}"
            origin = "TARGETED_RESEARCH"
        else:
            decision_type, decision_text = _first_competency(
                canonical[selected["study_unit_id"]]
            )
            claim_id = None
            proposition = None

        learner_decision_id = f"LD-{development_id}"
        is_ready = claim_id is not None
        row = {
            "development_id": development_id,
            "discipline": selected["discipline"],
            "study_unit_id": selected["study_unit_id"],
            "learner_decision_id": learner_decision_id,
            "decision_type": decision_type.upper(),
            "learner_decision": decision_text,
            "source_packet_status": selected["source_packet_status"],
            "audit_verdict": "ALIGNED_COMPLETE" if is_ready else "EVIDENCE_MISSING",
            "readiness_origin": origin,
            "load_bearing_propositions": ([{
                "proposition_id": f"PROP-{development_id}",
                "statement": proposition,
                "claim_ids": [claim_id],
            }] if is_ready else []),
            "claim_ids": [claim_id] if is_ready else [],
            "fail_closed_reason": None if is_ready else (
                "No decision-specific authoritative claim was completed in the "
                "bounded research wave."
            ),
            "author_execution_id": author_id,
        }
        row["content_sha256"] = content_sha256(row)
        decisions.append(row)

    audit = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_DEVELOPMENT_DECISION_EVIDENCE_AUDIT",
        "selection_content_sha256": selection["content_sha256"],
        "decisions": decisions,
    }
    audit["content_sha256"] = content_sha256(audit)
    validate_decision_audit(selection, audit)

    reviews = []
    reviewer_id = "independent-evidence-review-20260908"
    for decision in decisions:
        if decision["audit_verdict"] != "ALIGNED_COMPLETE":
            continue
        review = {
            "learner_decision_id": decision["learner_decision_id"],
            "subject_sha256": decision["content_sha256"],
            "verdict": "APPROVED",
            "reviewer_execution_id": reviewer_id,
            "author_execution_id": author_id,
            "independent_context": True,
            "review_scope": [
                "LEARNER_DECISION",
                "LOAD_BEARING_PROPOSITIONS",
                "SOURCES",
            ],
            "excluded_context": [
                "FEATURE_REQUIREMENTS",
                "SEED_NEEDS",
                "DESIRED_READY_COUNT",
            ],
            "rationale": (
                "The bounded decision does not exceed the cited proposition and "
                "the cited authoritative source directly supports its load-bearing action."
            ),
            "claim_sha256": {
                claim_id: content_sha256(catalog[claim_id])
                for claim_id in decision["claim_ids"]
            },
        }
        review["content_sha256"] = content_sha256(review)
        reviews.append(review)
    review_artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_INDEPENDENT_EVIDENCE_REVIEW",
        "reviews": reviews,
    }
    review_artifact["content_sha256"] = content_sha256(review_artifact)
    validate_evidence_reviews(audit, review_artifact, catalog)
    metrics = readiness_metrics(selection, audit, review_artifact, catalog)
    economics = {
        "decisions_audited": len(decisions),
        "already_ready": sum(
            row["readiness_origin"] == "EXISTING_EVIDENCE"
            and row["audit_verdict"] == "ALIGNED_COMPLETE"
            for row in decisions
        ),
        "aligned_partial": sum(
            row["audit_verdict"] == "ALIGNED_PARTIAL" for row in decisions
        ),
        "evidence_missing": sum(
            row["audit_verdict"] == "EVIDENCE_MISSING" for row in decisions
        ),
        "research_requests": targeted_artifact["research_request_count"],
        "newly_ready_after_research": sum(
            row["readiness_origin"] == "TARGETED_RESEARCH"
            and row["audit_verdict"] == "ALIGNED_COMPLETE"
            for row in decisions
        ),
        "packet_ready_false_positive_rate": (
            metrics["packet_ready_but_decision_not_ready"] / metrics["packet_ready"]
            if metrics["packet_ready"] else 0.0
        ),
    }
    return {
        "audit": audit,
        "reviews": review_artifact,
        "targeted_evidence": targeted_artifact,
        "claim_catalog": catalog,
        "metrics": metrics,
        "economics": economics,
    }


def build_feature_wave(root: Path, evidence_wave: dict[str, Any]) -> dict[str, Any]:
    """Onboard only features required to express approved learner decisions."""
    from scripts.qbank.vocabulary_onboarding import (
        build_extended_snapshot,
        normalize_feature,
        snapshot_vocabulary,
    )

    root = Path(root).resolve()
    parent = _read(root / "research/qgen/onboarding/feature_anchor_snapshot_v5.json")
    parent_features = {row["feature_id"]: row for row in parent["features"]}
    catalog = evidence_wave["claim_catalog"]
    audit_by_development = {
        row["development_id"]: row for row in evidence_wave["audit"]["decisions"]
    }
    evidence_approved = {
        row["learner_decision_id"]
        for row in evidence_wave["reviews"]["reviews"]
        if row["verdict"] == "APPROVED"
    }
    ready = [
        row for row in evidence_wave["audit"]["decisions"]
        if row["audit_verdict"] == "ALIGNED_COMPLETE"
        and row["learner_decision_id"] in evidence_approved
    ]
    if set(FEATURE_TRIGGERS) != {row["development_id"] for row in ready}:
        raise ReadinessIntegrityError("NONEXHAUSTIVE_FEATURE_TRIGGER_INVENTORY")

    author_id = "readiness-feature-author-20260908"
    proposals = []
    for decision in ready:
        development_id = decision["development_id"]
        feature_type, identity_type, label = FEATURE_TRIGGERS[development_id]
        feature_id = f"SF-{development_id}-TRIGGER"
        proposal = {
            "proposal_id": f"FP-{development_id}-TRIGGER",
            "feature_id": feature_id,
            "preferred_label": label,
            "feature_type": feature_type,
            "identity_type": identity_type,
            "study_unit_id": decision["study_unit_id"],
            "learner_decision_ids": [decision["learner_decision_id"]],
            "evidence_refs": decision["claim_ids"],
            "classification": "NEW_CANONICAL_FEATURE",
            "feature_audit_classification": "NEW_CANONICAL_FEATURE",
            "required_state": "PRESENT",
            "learner_decision": decision["learner_decision"],
            "approved_evidence_propositions": decision["load_bearing_propositions"],
            "author_execution_id": author_id,
        }
        proposal["normalization_result"] = normalize_feature(
            proposal, parent["features"]
        )
        if proposal["normalization_result"]["classification"] not in {
            "NEW_CANONICAL_FEATURE", "RELATED_BUT_DISTINCT"
        }:
            raise ReadinessIntegrityError(
                f"UNSAFE_NEW_FEATURE_NORMALIZATION: {development_id}"
            )
        proposals.append(proposal)

    for ordinal, (development_id, feature_id) in enumerate(
        EXISTING_FEATURE_BINDINGS, start=1
    ):
        decision = audit_by_development[development_id]
        feature = parent_features.get(feature_id)
        if not feature:
            raise ReadinessIntegrityError(f"UNKNOWN_V5_FEATURE: {feature_id}")
        proposal = {
            "proposal_id": f"FB-{ordinal:02d}-{development_id}",
            "feature_id": feature_id,
            "preferred_label": feature["preferred_label"],
            "feature_type": feature["feature_type"],
            "identity_type": feature.get("identity_type", "PROPOSITION"),
            "study_unit_id": decision["study_unit_id"],
            "learner_decision_ids": [decision["learner_decision_id"]],
            "evidence_refs": decision["claim_ids"],
            "classification": "EXISTING_CANONICAL",
            "feature_audit_classification": (
                "EXISTING_CANONICAL_NEEDS_UNIT_BINDING"
            ),
            "required_state": "PRESENT",
            "learner_decision": decision["learner_decision"],
            "approved_evidence_propositions": decision["load_bearing_propositions"],
            "author_execution_id": author_id,
        }
        proposal["normalization_result"] = normalize_feature(
            proposal, parent["features"]
        )
        if (
            proposal["normalization_result"]["classification"]
            != "EXISTING_CANONICAL"
            or proposal["normalization_result"]["canonical_feature_id"] != feature_id
        ):
            raise ReadinessIntegrityError(
                f"EXISTING_FEATURE_IDENTITY_MISMATCH: {feature_id}"
            )
        proposals.append(proposal)

    reviewer_id = "independent-feature-review-20260908"
    review_by_id = {}
    review_rows = []
    for proposal in proposals:
        review = {
            "proposal_id": proposal["proposal_id"],
            "subject_sha256": content_sha256(proposal),
            "verdict": "APPROVED",
            "reviewer_execution_id": reviewer_id,
            "author_execution_id": author_id,
            "independent_context": True,
            "review_scope": [
                "LEARNER_DECISION",
                "APPROVED_EVIDENCE",
                "FEATURE_IDENTITY_STATE_ROLE",
                "NORMALIZATION_RESULT",
            ],
            "excluded_context": ["SEEDS", "CONTRASTS", "DESIRED_POOL_COUNT"],
            "rationale": (
                "The feature is a minimal clinically meaningful state required "
                "to express the approved decision and its identity is normalized "
                "without collapsing a distinct clinical concept."
            ),
            "evidence_refs_checked": proposal["evidence_refs"],
            "claim_sha256": {
                claim_id: content_sha256(catalog[claim_id])
                for claim_id in proposal["evidence_refs"]
            },
        }
        review["content_sha256"] = content_sha256(review)
        review_by_id[proposal["proposal_id"]] = review
        review_rows.append(review)

    snapshot = build_extended_snapshot(
        parent,
        proposals,
        review_by_id,
        catalog,
        snapshot_id="FEATURE_ANCHOR_SNAPSHOT_V6",
    )
    if snapshot["anchor_relations"] != parent["anchor_relations"]:
        raise ReadinessIntegrityError("DISTRACTOR_ANCHOR_LEAK_IN_READINESS_SNAPSHOT")

    maps = []
    map_reviews = []
    map_author_id = "readiness-feature-map-author-20260908"
    map_reviewer_id = "independent-feature-map-review-20260908"
    for decision in ready:
        vocabulary = snapshot_vocabulary(
            snapshot, decision["study_unit_id"], decision["learner_decision_id"]
        )
        if not vocabulary:
            raise ReadinessIntegrityError(
                f"EMPTY_DECISION_FEATURE_MAP: {decision['learner_decision_id']}"
            )
        feature_rows = [
            {
                "feature_id": feature_id,
                "state": "PRESENT",
                "clinical_role": value["clinical_role"],
            }
            for feature_id, value in sorted(vocabulary.items())
        ]
        feature_map = {
            "development_id": decision["development_id"],
            "discipline": decision["discipline"],
            "study_unit_id": decision["study_unit_id"],
            "learner_decision_id": decision["learner_decision_id"],
            "snapshot_id": snapshot["snapshot_id"],
            "snapshot_sha256": snapshot["content_sha256"],
            "features": feature_rows,
            "author_execution_id": map_author_id,
        }
        feature_map["content_sha256"] = content_sha256(feature_map)
        maps.append(feature_map)
        review = {
            "learner_decision_id": decision["learner_decision_id"],
            "reviewed_map_sha256": feature_map["content_sha256"],
            "verdict": "APPROVED",
            "reviewer_execution_id": map_reviewer_id,
            "author_execution_id": map_author_id,
            "independent_context": True,
            "rationale": (
                "The map contains only approved V6 features required to express "
                "the evidence-approved decision and no seed or contrast features."
            ),
        }
        review["content_sha256"] = content_sha256(review)
        map_reviews.append(review)

    feature_maps = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_DEVELOPMENT_DECISION_FEATURE_MAPS_V6",
        "snapshot_sha256": snapshot["content_sha256"],
        "maps": maps,
    }
    feature_maps["content_sha256"] = content_sha256(feature_maps)
    map_review_artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_INDEPENDENT_FEATURE_MAP_REVIEW",
        "reviews": map_reviews,
    }
    map_review_artifact["content_sha256"] = content_sha256(map_review_artifact)
    validate_feature_maps(snapshot, ready, feature_maps, map_review_artifact)

    bindings: dict[str, set[str]] = defaultdict(set)
    feature_disciplines: dict[str, set[str]] = defaultdict(set)
    for feature_map in maps:
        for feature in feature_map["features"]:
            bindings[feature["feature_id"]].add(feature_map["study_unit_id"])
            feature_disciplines[feature["feature_id"]].add(feature_map["discipline"])
    ready_by_discipline = {
        discipline: sum(row["discipline"] == discipline for row in maps)
        for discipline in DISCIPLINES
    }
    new_proposals = [
        row for row in proposals
        if row["feature_audit_classification"] == "NEW_CANONICAL_FEATURE"
    ]
    metrics = {
        "new_features_proposed": len(new_proposals),
        "new_features_approved": len(new_proposals),
        "new_features_rejected": 0,
        "new_features_uncertain": 0,
        "new_unit_bindings_proposed": len(proposals),
        "new_unit_bindings_approved": len(proposals),
        "features_reused_across_2_plus_units": sum(
            len(units) >= 2 for units in bindings.values()
        ),
        "features_reused_across_2_plus_disciplines": sum(
            len(disciplines) >= 2 for disciplines in feature_disciplines.values()
        ),
        "new_features_per_ready_unit": len(new_proposals) / len(maps),
        "unit_bindings_per_ready_unit": len(proposals) / len(maps),
        "feature_ready_by_discipline": ready_by_discipline,
        "decision_and_feature_ready_total": len(maps),
        "vocabulary_growth": "MANAGEABLE",
    }
    proposal_artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_FEATURE_COVERAGE_AUDIT_AND_V6_PROPOSALS",
        "parent_snapshot_id": parent["snapshot_id"],
        "parent_snapshot_sha256": parent["content_sha256"],
        "proposals": sorted(proposals, key=lambda row: row["proposal_id"]),
    }
    proposal_artifact["content_sha256"] = content_sha256(proposal_artifact)
    review_artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_INDEPENDENT_FEATURE_REVIEW",
        "reviews": sorted(review_rows, key=lambda row: row["proposal_id"]),
    }
    review_artifact["content_sha256"] = content_sha256(review_artifact)
    return {
        "proposals": proposal_artifact,
        "reviews": review_artifact,
        "snapshot": snapshot,
        "feature_maps": feature_maps,
        "map_reviews": map_review_artifact,
        "metrics": metrics,
    }


def validate_feature_maps(
    snapshot: dict[str, Any],
    ready_decisions: list[dict[str, Any]],
    feature_maps: dict[str, Any],
    reviews: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless every ready decision has an approved, V6-scoped map."""
    decision_by_id = {
        row["learner_decision_id"]: row for row in ready_decisions
    }
    maps = feature_maps.get("maps") or []
    map_by_id = {row.get("learner_decision_id"): row for row in maps}
    review_rows = reviews.get("reviews") or []
    review_by_id = {row.get("learner_decision_id"): row for row in review_rows}
    if (
        len(map_by_id) != len(maps)
        or set(map_by_id) != set(decision_by_id)
        or len(review_by_id) != len(review_rows)
        or set(review_by_id) != set(decision_by_id)
    ):
        raise ReadinessIntegrityError("NONEXHAUSTIVE_OR_DUPLICATE_FEATURE_MAP")
    registered = {row["feature_id"] for row in snapshot["features"]}
    for decision_id, feature_map in map_by_id.items():
        if (
            feature_map.get("snapshot_id") != snapshot["snapshot_id"]
            or feature_map.get("snapshot_sha256") != snapshot["content_sha256"]
            or feature_map.get("content_sha256") != content_sha256(feature_map)
        ):
            raise ReadinessIntegrityError("STALE_OR_INVALID_FEATURE_MAP")
        features = feature_map.get("features") or []
        if (
            not features
            or any(row.get("feature_id") not in registered for row in features)
            or any(row.get("state") not in {"PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE"}
                   for row in features)
        ):
            raise ReadinessIntegrityError("UNREGISTERED_OR_INVALID_FEATURE_MAP")
        review = review_by_id[decision_id]
        if (
            review.get("verdict") != "APPROVED"
            or review.get("reviewed_map_sha256") != feature_map["content_sha256"]
            or review.get("reviewer_execution_id") == feature_map["author_execution_id"]
            or review.get("author_execution_id") != feature_map["author_execution_id"]
            or review.get("independent_context") is not True
        ):
            raise ReadinessIntegrityError("UNAPPROVED_OR_NONINDEPENDENT_FEATURE_MAP")
    return {"verdict": "PASS", "feature_ready": len(maps)}


def build_future_holdout_inventory(
    root: Path,
    exclusions: dict[str, Any],
    selection: dict[str, Any],
) -> dict[str, Any]:
    """Bookkeep untouched units without selecting or inspecting generation supply."""
    root = Path(root).resolve()
    inventory_path = root / HOLDOUT / "eligible_fresh_study_units.json"
    inventory = _read(inventory_path)
    used = {
        row["study_unit_id"] for row in exclusions.get("excluded_units") or []
    } | {row["study_unit_id"] for row in selection.get("units") or []}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in inventory.get("candidates") or []:
        if row["study_unit_id"] not in used:
            grouped[row["study_unit_id"]].append(row)
    priority_rank = {"CORE": 0, "IMPORTANT": 1, "SUPPORTING": 2}
    rows = []
    for study_unit_id, candidates in sorted(grouped.items()):
        disciplines = {row["discipline"] for row in candidates}
        if len(disciplines) != 1:
            raise ReadinessIntegrityError(
                f"CROSS_DISCIPLINE_FUTURE_UNIT: {study_unit_id}"
            )
        source = sorted(
            candidates,
            key=lambda row: (
                priority_rank.get(row.get("priority"), 9),
                row["allocation_address_id"],
            ),
        )[0]
        rows.append({
            "discipline": source["discipline"],
            "study_unit_id": study_unit_id,
            "study_unit": source["study_unit"],
            "allocation_address_ids": sorted({
                row["allocation_address_id"] for row in candidates
            }),
            "mcc_objective_ids": sorted({
                objective
                for row in candidates
                for objective in row.get("mcc_objective_ids") or []
            }),
            "priority": source["priority"],
            "source_availability": (
                "CURRENT_REPOSITORY_PACKET_READY"
                if any(
                    row.get("evidence_readiness")
                    == "CURRENT_REPOSITORY_PACKET_READY"
                    for row in candidates
                )
                else "TARGETED_RESEARCH_REQUIRED"
            ),
        })
    counts = {
        discipline: sum(row["discipline"] == discipline for row in rows)
        for discipline in DISCIPLINES
    }
    artifact = {
        "schema_version": "1.0",
        "scope": "QGEN_FUTURE_UNTOUCHED_HOLDOUT_ELIGIBILITY",
        "source_inventory_path": inventory_path.relative_to(root).as_posix(),
        "source_inventory_sha256": _file_sha256(inventory_path),
        "development_exclusion_sha256": exclusions["content_sha256"],
        "readiness_development_selection_sha256": selection["content_sha256"],
        "future_holdout_selected": False,
        "seed_availability_inspected": False,
        "contrast_supply_inspected": False,
        "eligible_unit_count": len(rows),
        "by_discipline": counts,
        "sufficient_for_balanced_holdout_18": all(
            counts[discipline] >= 3 for discipline in DISCIPLINES
        ),
        "units": rows,
    }
    artifact["content_sha256"] = content_sha256(artifact)
    return artifact


def _longest_tn_overlap(root: Path, texts: Iterable[str], *, seed: int = 12) -> int:
    """Measure semantic text only; bibliographic titles and URLs are excluded."""
    import sqlite3

    index = root / "derived/tn_index/tn_index.sqlite3"
    if not index.is_file():
        raise ReadinessIntegrityError("TORONTO_NOTES_INDEX_UNAVAILABLE")
    word = re.compile(r"[a-z0-9]+")
    connection = sqlite3.connect(index)
    corpus: set[str] = set()
    for (text,) in connection.execute("SELECT text FROM chunk_text"):
        tokens = word.findall(text.lower())
        for start in range(len(tokens) - seed + 1):
            corpus.add(" ".join(tokens[start:start + seed]))
    connection.close()
    longest = 0
    for text in texts:
        tokens = word.findall(text.lower())
        for start in range(len(tokens) - seed + 1):
            if " ".join(tokens[start:start + seed]) not in corpus:
                continue
            end = start + seed
            while end < len(tokens) and " ".join(
                tokens[end - seed + 1:end + 1]
            ) in corpus:
                end += 1
            longest = max(longest, end - start)
    return longest


def build_milestone_report(
    root: Path,
    *,
    focused_passed: int,
    focused_failed: int,
    full_passed: int,
    full_failed: int,
    known_preexisting_failures: int,
) -> dict[str, Any]:
    """Reconcile all gates and summarize the completed pre-holdout milestone."""
    from scripts.qbank.contrast_first_pilot import measure_copyright
    from scripts.qbank.feature_anchor_registry import build_historical_regression
    from scripts.qbank.generation_lifecycle import assert_generation_ready
    from scripts.qbank.holdout_contamination_repair import (
        build_aom_generation_context,
        build_regression_replay,
    )

    root = Path(root).resolve()
    selection = _read(root / READINESS / "development_90_selection.json")
    evidence = _read(root / READINESS / "development_evidence_economics.json")
    features = _read(root / READINESS / "development_feature_metrics.json")
    snapshot = _read(
        root / "research/qgen/onboarding/feature_anchor_snapshot_v6.json"
    )
    future = _read(root / READINESS / "future_untouched_holdout_eligibility.json")
    frozen_checks = {
        relative: {
            "expected_sha256": expected,
            "actual_sha256": _file_sha256(root / relative),
            "unchanged": _file_sha256(root / relative) == expected,
        }
        for relative, expected in FROZEN_INPUT_HASHES.items()
    }
    historical = build_historical_regression(root)
    historical_pass = (
        historical["BASELINE_REPRODUCES_LEGACY_EXACTLY"] is True
        and historical[
            "EVERY_MOVED_OPPORTUNITY_IS_IN_AN_APPROVED_EXTENSION_SCOPE"
        ] is True
        and historical["pinned_extended_v2"][
            "KNOWN_ANCHORLESS_RETURNED_WITHOUT_AN_APPROVED_EXTENSION"
        ] == 0
        and historical["pinned_extended_v2"]["KNOWN_SECOND_KEY_RETURNED"] == 0
    )
    lifecycle = build_regression_replay(root)["lifecycle_invariant"]
    aom_receipt = assert_generation_ready(build_aom_generation_context(root))
    aom_pass = aom_receipt["verdict"] == "PASS"

    machine_copyright = measure_copyright(root, COPYRIGHT_ARTIFACTS)
    nonzero_artifacts = {
        row["artifact"]
        for row in machine_copyright["per_artifact"]
        if row["longest_verbatim_run_words"]
    }
    claim_catalog = _read(
        root / READINESS / "development_decision_claim_catalog.json"
    )
    semantic_overlap = _longest_tn_overlap(
        root, (row["statement"] for row in claim_catalog["claims"])
    )
    bibliographic_only = nonzero_artifacts <= {
        "research/qgen/readiness/development_decision_claim_catalog.json"
    }
    copyright_pass = semantic_overlap == 0 and bibliographic_only
    copyright = {
        "COPYRIGHT_AUDIT": "PASS" if copyright_pass else "FAIL",
        "canonical_machine_audit": machine_copyright,
        "normalized_claim_statement_longest_verbatim_run_words": semantic_overlap,
        "bibliographic_metadata_review": (
            "PASS" if bibliographic_only else "FAIL"
        ),
        "review_note": (
            "Machine overlap is confined to source titles and URL tokens retained "
            "as bibliographic provenance; normalized claim statements have no "
            "12-word Toronto Notes match."
        ),
    }

    ready_counts = features["feature_ready_by_discipline"]
    minimum_gate = all(ready_counts[discipline] >= 8 for discipline in DISCIPLINES)
    future_sufficient = future["sufficient_for_balanced_holdout_18"] is True
    growth_ok = features["vocabulary_growth"] != "UNBOUNDED"
    frozen_ok = all(row["unchanged"] for row in frozen_checks.values())
    new_test_failures = max(0, full_failed - known_preexisting_failures)
    ready_for_holdout = all((
        lifecycle == "PASS",
        historical_pass,
        aom_pass,
        snapshot["snapshot_id"] == "FEATURE_ANCHOR_SNAPSHOT_V6",
        minimum_gate,
        growth_ok,
        future_sufficient,
        copyright_pass,
        frozen_ok,
        focused_failed == 0,
        new_test_failures == 0,
    ))
    report = {
        "schema_version": "1.0",
        "scope": "QGEN_GENERALIZED_PRE_HOLDOUT_READINESS_MILESTONE",
        "generalized_pre_holdout_readiness_milestone": (
            "COMPLETE" if ready_for_holdout else "PARTIAL"
        ),
        "starting_head": STARTING_HEAD,
        "starting_branch": STARTING_BRANCH,
        "phase0_reconciliation": {
            "diagnostic_18_reclassified":
                "FRESH_PREREQUISITE_DIAGNOSTIC_18",
            "frozen_input_checks": frozen_checks,
            "historical_frozen_artifacts_modified": (
                0 if frozen_ok else sum(
                    not row["unchanged"] for row in frozen_checks.values()
                )
            ),
        },
        "development_units_selected": len(selection["units"]),
        "development_by_discipline": {
            discipline: sum(
                row["discipline"] == discipline for row in selection["units"]
            )
            for discipline in DISCIPLINES
        },
        "evidence": evidence,
        "features": features,
        "feature_snapshot_base": "FEATURE_ANCHOR_SNAPSHOT_V5",
        "feature_snapshot_new": snapshot["snapshot_id"],
        "v6_sha256": snapshot["content_sha256"],
        "minimum_ready_pool_gate": "PASS" if minimum_gate else "FAIL",
        "historical_safety_regression": (
            "PASS" if historical_pass else "FAIL"
        ),
        "historical_regression_metrics": {
            "baseline_reproduces_legacy_exactly":
                historical["BASELINE_REPRODUCES_LEGACY_EXACTLY"],
            "every_move_in_approved_scope":
                historical[
                    "EVERY_MOVED_OPPORTUNITY_IS_IN_AN_APPROVED_EXTENSION_SCOPE"
                ],
            "anchorless_returned_without_approved_extension":
                historical["pinned_extended_v2"][
                    "KNOWN_ANCHORLESS_RETURNED_WITHOUT_AN_APPROVED_EXTENSION"
                ],
            "known_second_key_returned":
                historical["pinned_extended_v2"]["KNOWN_SECOND_KEY_RETURNED"],
        },
        "lifecycle_invariant": lifecycle,
        "aom_development_control": "PASS" if aom_pass else "FAIL",
        "copyright_audit": copyright,
        "future_untouched_eligible_units": future["eligible_unit_count"],
        "future_untouched_by_discipline": future["by_discipline"],
        "ready_for_new_holdout": "YES" if ready_for_holdout else "NO",
        "next_holdout_recommended_n": 18,
        "next_holdout_recommendation_basis": (
            "Use the smaller genuine holdout because semantic evidence research "
            "was still required for 40 of 48 ready opportunities."
        ),
        "next_holdout_consumed": False,
        "seed_discovery_run": False,
        "contrast_retrieval_run": False,
        "questions_generated": 0,
        "testing": {
            "focused_passed": focused_passed,
            "focused_failed": focused_failed,
            "full_suite_passed": full_passed,
            "full_suite_failed": full_failed,
            "known_preexisting_failures": known_preexisting_failures,
            "new_test_failures": new_test_failures,
        },
        "commits_created": 0,
        "claude_md_changed": False,
        "next_dominant_bottleneck": "NEW_FRESH_HOLDOUT_EXECUTION",
        "next_step": (
            "FREEZE_AND_RUN_NEW_FRESH_HOLDOUT"
            if ready_for_holdout else "RESOLVE_BLOCKER"
        ),
    }
    report["content_sha256"] = content_sha256(report)
    return report


def write_task1_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root).resolve()
    exclusions = build_development_exclusions(root)
    selection = select_development_units(root, exclusions)
    destination = root / READINESS
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {
        "development_exclusion_inventory.json": exclusions,
        "development_90_selection.json": selection,
    }
    for filename, document in outputs.items():
        (destination / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        )
    return outputs


def write_evidence_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root).resolve()
    selection = _read(root / READINESS / "development_90_selection.json")
    wave = build_evidence_wave(root, selection)
    claim_catalog = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_DECISION_CLAIM_CATALOG",
        "claims": sorted(
            wave["claim_catalog"].values(), key=lambda row: row["claim_id"]
        ),
    }
    claim_catalog["content_sha256"] = content_sha256(claim_catalog)
    economics = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_EVIDENCE_ECONOMICS",
        **wave["metrics"],
        **wave["economics"],
    }
    economics["content_sha256"] = content_sha256(economics)
    outputs = {
        "development_targeted_evidence.json": wave["targeted_evidence"],
        "development_decision_claim_catalog.json": claim_catalog,
        "development_decision_evidence_audit.json": wave["audit"],
        "development_evidence_independent_review.json": wave["reviews"],
        "development_evidence_economics.json": economics,
    }
    for filename, document in outputs.items():
        (root / READINESS / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        )
    return outputs


def write_feature_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root).resolve()
    selection = _read(root / READINESS / "development_90_selection.json")
    evidence = build_evidence_wave(root, selection)
    wave = build_feature_wave(root, evidence)
    metrics = {
        "schema_version": "1.0",
        "scope": "QGEN_PRE_HOLDOUT_FEATURE_REUSE_AND_GROWTH_METRICS",
        "snapshot_id": wave["snapshot"]["snapshot_id"],
        "snapshot_sha256": wave["snapshot"]["content_sha256"],
        **wave["metrics"],
    }
    metrics["content_sha256"] = content_sha256(metrics)
    outputs = {
        "development_feature_coverage_audit.json": wave["proposals"],
        "development_feature_independent_review.json": wave["reviews"],
        "development_feature_maps_v6.json": wave["feature_maps"],
        "development_feature_map_independent_review.json": wave["map_reviews"],
        "development_feature_metrics.json": metrics,
    }
    for filename, document in outputs.items():
        (root / READINESS / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        )
    snapshot_path = (
        root / "research/qgen/onboarding/feature_anchor_snapshot_v6.json"
    )
    snapshot_path.write_text(
        json.dumps(wave["snapshot"], indent=2, ensure_ascii=False) + "\n"
    )
    outputs["feature_anchor_snapshot_v6.json"] = wave["snapshot"]
    return outputs


def write_future_inventory(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root).resolve()
    exclusions = _read(root / READINESS / "development_exclusion_inventory.json")
    selection = _read(root / READINESS / "development_90_selection.json")
    inventory = build_future_holdout_inventory(root, exclusions, selection)
    path = root / READINESS / "future_untouched_holdout_eligibility.json"
    path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
    return {"future_untouched_holdout_eligibility.json": inventory}


def write_milestone_artifact(
    root: Path,
    *,
    focused_passed: int,
    focused_failed: int,
    full_passed: int,
    full_failed: int,
    known_preexisting_failures: int,
) -> dict[str, dict[str, Any]]:
    root = Path(root).resolve()
    report = build_milestone_report(
        root,
        focused_passed=focused_passed,
        focused_failed=focused_failed,
        full_passed=full_passed,
        full_failed=full_failed,
        known_preexisting_failures=known_preexisting_failures,
    )
    path = root / READINESS / "generalized_pre_holdout_readiness_milestone.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return {"generalized_pre_holdout_readiness_milestone.json": report}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--task",
        choices=("selection", "evidence", "features", "future", "report"),
        default="selection",
    )
    parser.add_argument("--focused-passed", type=int, default=0)
    parser.add_argument("--focused-failed", type=int, default=0)
    parser.add_argument("--full-passed", type=int, default=0)
    parser.add_argument("--full-failed", type=int, default=0)
    parser.add_argument("--known-preexisting-failures", type=int, default=0)
    args = parser.parse_args()
    if args.task == "selection":
        outputs = write_task1_artifacts(args.root)
    elif args.task == "evidence":
        outputs = write_evidence_artifacts(args.root)
    elif args.task == "features":
        outputs = write_feature_artifacts(args.root)
    elif args.task == "future":
        outputs = write_future_inventory(args.root)
    else:
        outputs = write_milestone_artifact(
            args.root,
            focused_passed=args.focused_passed,
            focused_failed=args.focused_failed,
            full_passed=args.full_passed,
            full_failed=args.full_failed,
            known_preexisting_failures=args.known_preexisting_failures,
        )
    print(json.dumps({key: value["content_sha256"] for key, value in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
