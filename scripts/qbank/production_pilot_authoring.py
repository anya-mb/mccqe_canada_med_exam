"""First production authoring pilot: deterministic validation, packaging and handoff.

This module is the deterministic half of the first production question pilot. The
clinical content lives in ``research/qgen/production_pilot_v1/pilot_authored_items.json``
and is authored by a session that is, by contract, forbidden from verifying it.

Everything here is deterministic: schema and lineage validation, evidence-fact
resolution against frozen repository artifacts, package assembly through the
unchanged Independent Item Verification V1 helpers, duplicate screening, copyright
overlap measurement and the handoff manifest that a *different* session consumes.

No item may leave this module in any state other than
``PENDING_INDEPENDENT_VERIFICATION``.
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from scripts.qbank.independent_item_verification import canonical_hash
from scripts.qbank.option_set_admissibility import find_realization_parity_defects

REGISTRY_V3_SHA256 = "57a12e09be8322939814e1a1c41850cba7cb937e2868c827472ecd3407d54e38"
REGISTRY_V3_PILOT_MANIFEST_SHA256 = (
    "5a20b814f636a7af8c33cf92980e1cf695975b0d8449808753f4f8626e187dc8"
)

AUTHOR_SESSION_ID = "PRODUCTION_PILOT_V1_AUTHOR_SESSION"
PENDING_VERIFICATION = "PENDING_INDEPENDENT_VERIFICATION"
AUTHOR_COMPLETE = "AUTHOR_COMPLETE"
NOT_AUTHORED_DISPOSITIONS = frozenset({
    "NEEDS_SOURCE_RESEARCH", "INSUFFICIENT_EVIDENCE", "REJECTED_SECOND_KEY",
    "REJECTED_COPYRIGHT", "REJECTED_OTHER",
})
TORONTO_NOTES_RELATIONSHIPS = frozenset({
    "TN_CONSISTENT", "TN_UPDATED_BY_CURRENT_GUIDANCE", "TN_NOT_APPLICABLE",
})
DIFFICULTY_TARGETS = frozenset({
    "AUTHOR_TARGET_EASY", "AUTHOR_TARGET_MEDIUM", "AUTHOR_TARGET_HARD",
})

REGISTRY_DIR = "research/qgen/opportunity_registry_v3_canonical"
PILOT_DIR = "research/qgen/production_pilot_v1"
AUTHORED_ITEMS_PATH = f"{PILOT_DIR}/pilot_authored_items.json"
PACKAGE_SCHEMA_PATH = "schemas/production-item-verification-package-v1.schema.json"

_WORD = re.compile(r"[a-z0-9]+")


class PilotAuthoringError(ValueError):
    """Raised when a frozen input cannot be trusted."""


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((Path(root) / relative).read_text())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Frozen inputs
# ---------------------------------------------------------------------------


def load_pilot_manifest(root: Path) -> dict[str, Any]:
    """Load the frozen 36-opportunity manifest, refusing a drifted hash."""
    manifest = _load(root, f"{REGISTRY_DIR}/registry_v3_pilot_manifest.json")
    body = {key: value for key, value in manifest.items() if key != "content_sha256"}
    recomputed = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if recomputed != manifest.get("content_sha256"):
        raise PilotAuthoringError("PILOT_MANIFEST_CONTENT_HASH_MISMATCH")
    if manifest["content_sha256"] != REGISTRY_V3_PILOT_MANIFEST_SHA256:
        raise PilotAuthoringError("PILOT_MANIFEST_IS_NOT_THE_FROZEN_MANIFEST")
    if manifest["registry_v3_sha256"] != REGISTRY_V3_SHA256:
        raise PilotAuthoringError("PILOT_MANIFEST_REGISTRY_LINEAGE_MISMATCH")
    return manifest


def load_registry_v3(root: Path) -> dict[str, dict[str, Any]]:
    registry = _load(root, f"{REGISTRY_DIR}/registry_v3.json")
    if registry.get("content_sha256") != REGISTRY_V3_SHA256:
        raise PilotAuthoringError("REGISTRY_V3_CONTENT_HASH_MISMATCH")
    return {row["opportunity_id"]: row for row in registry["opportunities"]}


def load_authored_items(root: Path) -> dict[str, Any]:
    artifact = _load(root, AUTHORED_ITEMS_PATH)
    if artifact.get("author_session_id") != AUTHOR_SESSION_ID:
        raise PilotAuthoringError("AUTHORED_ITEMS_SESSION_MISMATCH")
    return artifact


# ---------------------------------------------------------------------------
# Evidence index — every fact an item cites must already exist in the repository
# ---------------------------------------------------------------------------


def _source_ref(source_id: str, organization: str, date_or_version: str, locator: str) -> dict[str, str]:
    return {
        "source_id": source_id,
        "organization": organization or "UNKNOWN",
        "date_or_version": date_or_version or "UNKNOWN",
        "locator": locator or "SOURCE_REGISTRY",
    }


def build_evidence_index(root: Path) -> dict[str, dict[str, Any]]:
    """Index every repository-backed clinical fact an authored item may cite.

    Four frozen layers contribute, each keyed by an identifier that already
    exists in the artifact it comes from, so nothing here invents a fact id.
    """
    root = Path(root)
    index: dict[str, dict[str, Any]] = {}

    # Layer 1 — READY source packets (recommendations and their exceptions).
    for path in sorted(glob.glob(str(root / "research/qgen/source_packet_population_srb_*.json"))):
        for packet in json.loads(Path(path).read_text())["source_packets"]:
            if packet.get("status") != "SOURCE_PACKET_READY":
                continue
            sources = {row["source_id"]: row for row in packet.get("authoritative_sources", [])}

            def refs(citations: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
                out = []
                for citation in citations:
                    source = sources.get(citation.get("source_id"), {})
                    out.append(_source_ref(
                        citation.get("source_id", "UNKNOWN"),
                        source.get("issuing_organization", ""),
                        source.get("publication_date") or source.get("guideline_version") or "",
                        citation.get("locator", ""),
                    ))
                return out

            for rec in packet.get("supported_recommendations", []):
                index[rec["recommendation_id"]] = {
                    "statement": rec["statement"],
                    "sources": refs(rec.get("source_citations", [])),
                    "layer": "SOURCE_PACKET_READY",
                    "artifact": Path(path).relative_to(root).as_posix(),
                }
            for exception in packet.get("important_contraindications_or_exceptions", []):
                index[exception["exception_id"]] = {
                    "statement": exception["statement"],
                    "sources": refs(exception.get("source_citations", [])),
                    "layer": "SOURCE_PACKET_EXCEPTION",
                    "artifact": Path(path).relative_to(root).as_posix(),
                }

    # Layer 2 — bounded targeted research claims from the pre-holdout readiness wave.
    targeted = _load(root, "research/qgen/readiness/development_targeted_evidence.json")
    for claim in targeted["claims"]:
        index[claim["claim_id"]] = {
            "statement": claim["statement"],
            "sources": [_source_ref(
                claim.get("source_id", "UNKNOWN"), claim.get("source_title", ""),
                "RETRIEVED_" + str(next(
                    (row["retrieval_date"] for row in targeted["sources"]
                     if row["source_id"] == claim.get("source_id")), "UNKNOWN",
                )),
                claim.get("locator", ""),
            )],
            "layer": "READINESS_TARGETED_EVIDENCE",
            "artifact": "research/qgen/readiness/development_targeted_evidence.json",
        }

    # Layer 3 — fresh operational holdout decision evidence, keyed by study unit.
    holdout = _load(root, "research/qgen/holdout/fresh_operational_holdout_18_evidence.json")
    for row in holdout["rows"]:
        propositions = row.get("load_bearing_propositions") or []
        index[f"FOH18-{row['study_unit_id']}"] = {
            "statement": " ".join(
                p if isinstance(p, str) else p.get("statement", "") for p in propositions
            ),
            "sources": [_source_ref(
                source["source_id"], source.get("organization", ""),
                source.get("title", ""), source.get("locator", ""),
            ) for source in row.get("sources", [])],
            "layer": "FRESH_OPERATIONAL_HOLDOUT_18_EVIDENCE",
            "artifact": "research/qgen/holdout/fresh_operational_holdout_18_evidence.json",
        }

    # Layer 4 — cross-discipline and chapter-pilot evidence packets.
    for relative in (
        "research/qgen/generalization/cross_discipline_generalization_15.evidence.json",
        "research/qgen/generalization/cross_discipline_generalization_15_r4.evidence.json",
        "research/qgen/pilot/QGEN-MED-007.acs-chapter-review-pilot-10.evidence.json",
    ):
        artifact = _load(root, relative)
        sources = {row["source_id"]: row for row in artifact.get("sources", [])}
        for claim in artifact.get("claims", []):
            citations = claim.get("source_refs") or claim.get("source_citations") or [
                {"source_id": source_id, "locator": claim.get("locator", "")}
                for source_id in (claim.get("source_ids") or ([claim["source_id"]] if claim.get("source_id") else []))
            ]
            refs = []
            for citation in citations:
                source = sources.get(citation.get("source_id"), {})
                refs.append(_source_ref(
                    citation.get("source_id", "UNKNOWN"),
                    source.get("issuing_organization", ""),
                    source.get("update_date") or source.get("publication_date") or "",
                    citation.get("locator") or source.get("title", ""),
                ))
            if not refs:
                continue
            index.setdefault(claim["claim_id"], {
                "statement": claim["statement"],
                "sources": refs,
                "layer": "EVIDENCE_PACKET",
                "artifact": relative,
            })
    return index


# ---------------------------------------------------------------------------
# Deterministic item validation
# ---------------------------------------------------------------------------

_REQUIRED_ITEM_FIELDS = (
    "item_id", "question_seed_id", "registry_v3_opportunity_id", "discipline",
    "study_unit_id", "topic", "subtopic", "learner_decision", "opportunity_family",
    "response_class", "clinical_stage", "author_target_difficulty", "stem", "lead_in",
    "answer_choices", "author_proposed_key", "author_rationale",
    "per_distractor_rationales", "conditional_next_action_information",
    "evidence_fact_ids", "toronto_notes_relationship", "author_confidence",
    "verification_status", "disposition",
)


def validate_item(
    item: Mapping[str, Any],
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> list[str]:
    """Return every deterministic defect in one authored item."""
    errors: list[str] = []
    item_id = item.get("item_id", "<no item_id>")

    def fail(code: str) -> None:
        errors.append(f"{item_id}: {code}")

    for field in _REQUIRED_ITEM_FIELDS:
        if field not in item or item[field] in (None, "", []):
            if field == "evidence_fact_ids":
                fail("MISSING_EVIDENCE_FACT_IDS")
            else:
                fail(f"MISSING_FIELD:{field}")

    rows = {row["opportunity_id"]: row for row in manifest["manifest"]}
    row = rows.get(item.get("registry_v3_opportunity_id"))
    if row is None:
        fail("OPPORTUNITY_NOT_IN_PILOT_MANIFEST")
    else:
        for field in ("discipline", "study_unit_id", "opportunity_family", "response_class"):
            if item.get(field) != row.get(field):
                fail(f"REGISTRY_LINEAGE_MISMATCH:{field}")

    if item.get("verification_status") != PENDING_VERIFICATION:
        if item.get("verification_status") == "VERIFIED_ACCEPT":
            fail("AUTHOR_MAY_NOT_SET_VERIFIED_ACCEPT")
        else:
            fail("VERIFICATION_STATUS_MUST_BE_PENDING")
    if item.get("disposition") != AUTHOR_COMPLETE:
        fail("AUTHORED_ITEM_DISPOSITION_MUST_BE_AUTHOR_COMPLETE")
    if item.get("toronto_notes_relationship") not in TORONTO_NOTES_RELATIONSHIPS:
        fail("UNKNOWN_TORONTO_NOTES_RELATIONSHIP")
    if item.get("author_target_difficulty") not in DIFFICULTY_TARGETS:
        fail("UNKNOWN_AUTHOR_TARGET_DIFFICULTY")

    choices = item.get("answer_choices") or []
    if not 4 <= len(choices) <= 5:
        fail("OPTION_COUNT_OUT_OF_RANGE")
    if len(set(choices)) != len(choices):
        fail("DUPLICATE_OPTION")
    key = item.get("author_proposed_key")
    if key not in choices:
        fail("KEY_NOT_IN_OPTIONS")
    if choices.count(key) > 1:
        fail("KEY_APPEARS_MORE_THAN_ONCE")

    rationales = item.get("per_distractor_rationales") or []
    explained = [row.get("choice") for row in rationales]
    distractors = [choice for choice in choices if choice != key]
    if sorted(explained) != sorted(distractors):
        fail("DISTRACTOR_RATIONALE_SET_DOES_NOT_MATCH_DISTRACTORS")
    if len(explained) != len(set(explained)):
        fail("DISTRACTOR_RATIONALE_DUPLICATED")
    for entry in rationales:
        for field in ("why_plausible", "why_inferior_here", "what_would_make_correct"):
            text = (entry.get(field) or "").strip()
            if len(text) < 40:
                fail(f"DISTRACTOR_RATIONALE_TOO_THIN:{entry.get('choice')}:{field}")

    if len((item.get("author_rationale") or "").strip()) < 200:
        fail("AUTHOR_RATIONALE_TOO_THIN")
    if len((item.get("stem") or "").strip()) < 120:
        fail("STEM_TOO_THIN")
    if key and key in (item.get("stem") or ""):
        fail("STEM_STATES_THE_KEY")

    for fact_id in item.get("evidence_fact_ids") or []:
        if fact_id not in evidence:
            fail(f"EVIDENCE_FACT_NOT_IN_REPOSITORY:{fact_id}")

    # ADM-5: the existing realization-parity control, reused unchanged. It catches
    # the format tells a candidate can see without reading any medicine.
    for defect in find_realization_parity_defects([{"text": choice} for choice in choices]):
        fail(f"REALIZATION_PARITY:{defect}")

    # Option-length parity: a key that is materially longer than every distractor
    # is the register asymmetry that repeatedly reached earlier waves.
    if key in choices and len(choices) > 2:
        lengths = {choice: len(choice) for choice in choices}
        others = [length for choice, length in lengths.items() if choice != key]
        if others and lengths[key] > 2.0 * max(others):
            fail("KEY_DISTRACTOR_LENGTH_ASYMMETRY")
    return errors


def validate_authored_batch(root: Path) -> list[str]:
    """Validate every authored item plus the batch-level accounting invariants."""
    root = Path(root)
    manifest = load_pilot_manifest(root)
    evidence = build_evidence_index(root)
    artifact = load_authored_items(root)
    errors: list[str] = []

    for item in artifact["items"]:
        errors.extend(validate_item(item, manifest, evidence))

    item_ids = [item["item_id"] for item in artifact["items"]]
    if len(set(item_ids)) != len(item_ids):
        errors.append("BATCH: DUPLICATE_ITEM_ID")
    seeds = [item["question_seed_id"] for item in artifact["items"]]
    if len(set(seeds)) != len(seeds):
        errors.append("BATCH: DUPLICATE_QUESTION_SEED_ID")

    authored = {item["registry_v3_opportunity_id"] for item in artifact["items"]}
    if len(authored) != len(artifact["items"]):
        errors.append("BATCH: MORE_THAN_ONE_ITEM_PER_OPPORTUNITY")
    not_authored = {row["opportunity_id"] for row in artifact["not_authored"]}
    if authored & not_authored:
        errors.append("BATCH: OPPORTUNITY_HAS_TWO_DISPOSITIONS")
    expected = {row["opportunity_id"] for row in manifest["manifest"]}
    if authored | not_authored != expected:
        errors.append("BATCH: MANIFEST_OPPORTUNITY_WITHOUT_A_DISPOSITION")

    for row in artifact["not_authored"]:
        if row.get("disposition") not in NOT_AUTHORED_DISPOSITIONS:
            errors.append(f"{row['opportunity_id']}: UNKNOWN_NOT_AUTHORED_DISPOSITION")
        if len((row.get("reason") or "").strip()) < 60:
            errors.append(f"{row['opportunity_id']}: NOT_AUTHORED_REASON_TOO_THIN")

    if "VERIFIED_ACCEPT" in json.dumps(artifact):
        errors.append("BATCH: AUTHORED_ARTIFACT_CLAIMS_VERIFIED_ACCEPT")
    errors.extend(detect_near_duplicate_items(artifact["items"]))
    return errors


# ---------------------------------------------------------------------------
# Item distinctness — a deterministic flag for author review, not a verdict
# ---------------------------------------------------------------------------


def _shingles(text: str, size: int = 6) -> set[str]:
    tokens = _WORD.findall(text.lower())
    return {" ".join(tokens[i:i + size]) for i in range(max(0, len(tokens) - size + 1))}


def detect_near_duplicate_items(
    items: Sequence[Mapping[str, Any]], *, threshold: float = 0.25,
) -> list[str]:
    """Flag item pairs whose stem-and-option text overlaps enough to review."""
    flags: list[str] = []
    profiles = [
        (item["item_id"], _shingles(item["stem"] + " " + " ".join(item["answer_choices"])))
        for item in items
    ]
    for index, (left_id, left) in enumerate(profiles):
        for right_id, right in profiles[index + 1:]:
            union = left | right
            if not union:
                continue
            jaccard = len(left & right) / len(union)
            if jaccard >= threshold:
                flags.append(
                    f"NEAR_DUPLICATE_ITEM_PAIR:{left_id}:{right_id}:{jaccard:.3f}"
                )
    return flags


# ---------------------------------------------------------------------------
# Verification packages — built through the unchanged V1 helpers
# ---------------------------------------------------------------------------


def _package_hashes(package: dict[str, Any]) -> dict[str, Any]:
    """Mirror of the V1 hashing contract; the field list is imported, not restated."""
    from scripts.qbank.independent_item_verification import VERIFIED_CONTENT_FIELDS

    package["verified_content_sha256"] = canonical_hash(
        {field: package.get(field) for field in VERIFIED_CONTENT_FIELDS}
    )
    package["content_sha256"] = canonical_hash(package)
    return package


def build_package(item: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Project one authored item into a frozen V1 verification package."""
    source_refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for fact_id in item["evidence_fact_ids"]:
        for ref in evidence[fact_id]["sources"]:
            marker = (ref["source_id"], ref["locator"])
            if marker in seen:
                continue
            seen.add(marker)
            source_refs.append(dict(ref))
    package = {
        "schema_version": "1.0",
        "item_id": item["item_id"],
        "opportunity_id": item["registry_v3_opportunity_id"],
        "question_seed_id": item["question_seed_id"],
        "author_session_id": AUTHOR_SESSION_ID,
        "discipline": item["discipline"],
        "topic": item["topic"],
        "learner_decision": item["learner_decision"],
        "difficulty_intent": item["author_target_difficulty"],
        "stem": item["stem"],
        "lead_in": item["lead_in"],
        "answer_choices": list(item["answer_choices"]),
        "author_proposed_key": item["author_proposed_key"],
        "author_rationale": item["author_rationale"],
        "per_distractor_rationales": [
            {
                "choice": row["choice"],
                "why_plausible": row["why_plausible"],
                "why_inferior_here": row["why_inferior_here"],
                "what_would_make_correct": row["what_would_make_correct"],
            }
            for row in item["per_distractor_rationales"]
        ],
        "conditional_next_action_information": item["conditional_next_action_information"],
        "evidence_fact_ids": list(item["evidence_fact_ids"]),
        "toronto_notes_source_refs": list(item.get("toronto_notes_source_refs") or []),
        "canadian_source_refs": source_refs,
        "author_confidence": item["author_confidence"],
        "non_production_validation_item": False,
    }
    return _package_hashes(package)


def build_verification_packages(root: Path) -> dict[str, Any]:
    root = Path(root)
    errors = validate_authored_batch(root)
    if errors:
        raise PilotAuthoringError(f"AUTHORED_BATCH_INVALID: {errors[0]}")
    evidence = build_evidence_index(root)
    artifact = load_authored_items(root)
    packages = [build_package(item, evidence) for item in artifact["items"]]
    result = {
        "schema_version": "1.0",
        "scope": "FIRST_PRODUCTION_AUTHORING_PILOT_V1_VERIFICATION_PACKAGES",
        "registry_v3_sha256": REGISTRY_V3_SHA256,
        "pilot_manifest_sha256": REGISTRY_V3_PILOT_MANIFEST_SHA256,
        "author_session_id": AUTHOR_SESSION_ID,
        "verification_status": PENDING_VERIFICATION,
        "packages": packages,
    }
    result["content_sha256"] = canonical_hash(result)
    return result


def build_blind_packets(root: Path) -> dict[str, Any]:
    """Stage-1 projections: stem, lead-in and options, and nothing else."""
    from scripts.qbank.independent_item_verification import blind_projection

    packages = build_verification_packages(root)
    artifact = {
        "schema_version": "1.0",
        "scope": "FIRST_PRODUCTION_AUTHORING_PILOT_V1_STAGE_1_BLIND_PACKETS",
        "stage_1_contract": "SOLVE_BEFORE_ANY_KEY_RATIONALE_OR_EVIDENCE_IS_REVEALED",
        "blind_packets": [blind_projection(package) for package in packages["packages"]],
    }
    artifact["content_sha256"] = canonical_hash(artifact)
    return artifact


def build_verification_handoff_manifest(root: Path) -> dict[str, Any]:
    """The single deterministic input a different fresh session consumes."""
    root = Path(root)
    packages = build_verification_packages(root)
    artifact = load_authored_items(root)
    items = {item["item_id"]: item for item in artifact["items"]}
    rows = []
    for package in packages["packages"]:
        item = items[package["item_id"]]
        rows.append({
            "item_id": package["item_id"],
            "registry_v3_opportunity_id": package["opportunity_id"],
            "discipline": package["discipline"],
            "study_unit_id": item["study_unit_id"],
            "topic": package["topic"],
            "subtopic": item["subtopic"],
            "opportunity_family": item["opportunity_family"],
            "response_class": item["response_class"],
            "mcc_objective_ids": item.get("mcc_objective_ids", []),
            "mcc_physician_activity": item.get("mcc_physician_activity"),
            "mcc_dimension_of_care": item.get("mcc_dimension_of_care", []),
            "author_target_difficulty": item["author_target_difficulty"],
            "author_confidence": item["author_confidence"],
            "toronto_notes_relationship": item["toronto_notes_relationship"],
            "evidence_fact_ids": package["evidence_fact_ids"],
            "content_sha256": package["content_sha256"],
            "verified_content_sha256": package["verified_content_sha256"],
            "verification_status": PENDING_VERIFICATION,
        })
    manifest = {
        "schema_version": "1.0",
        "scope": "FIRST_PRODUCTION_AUTHORING_PILOT_V1_INDEPENDENT_VERIFICATION_HANDOFF",
        "registry_v3_sha256": REGISTRY_V3_SHA256,
        "pilot_manifest_sha256": REGISTRY_V3_PILOT_MANIFEST_SHA256,
        "author_session_id": AUTHOR_SESSION_ID,
        "verification_status": PENDING_VERIFICATION,
        "authoring_session_verdict": "NOT_AUTHORIZED",
        "separate_session_required": True,
        "web_export_authorized": False,
        "package_artifact_path": f"{PILOT_DIR}/pilot_verification_packages.json",
        "package_artifact_content_sha256": packages["content_sha256"],
        "verification_package_schema_file_sha256": file_sha256(root / PACKAGE_SCHEMA_PATH),
        "protocol": (
            "STAGE_1_BLIND_SOLVE -> FREEZE_VERDICT -> "
            "STAGE_2_RATIONALE_CLAIM_SOURCE_TN_CURRENT_CANADIAN_GUIDANCE_AUDIT -> "
            "VERIFIED_ACCEPT_OR_REJECT"
        ),
        "author_chain_of_thought_withheld": True,
        "package_count": len(rows),
        "packages": rows,
    }
    manifest["content_sha256"] = canonical_hash(manifest)
    return manifest


# ---------------------------------------------------------------------------
# Copyright
# ---------------------------------------------------------------------------


def measure_toronto_notes_overlap(root: Path, texts: Iterable[str], *, seed: int = 12) -> int:
    """Longest run of consecutive words shared with the Toronto Notes index."""
    from scripts.qbank.pre_holdout_readiness import _longest_tn_overlap

    return _longest_tn_overlap(Path(root), texts, seed=seed)


def build_copyright_audit(root: Path, *, seed: int = 12) -> dict[str, Any]:
    root = Path(root)
    artifact = load_authored_items(root)
    evidence = build_evidence_index(root)
    texts: list[str] = []
    for item in artifact["items"]:
        texts.append(item["stem"])
        texts.append(item["lead_in"])
        texts.extend(item["answer_choices"])
        texts.append(item["author_rationale"])
        for row in item["per_distractor_rationales"]:
            texts.extend([row["why_plausible"], row["why_inferior_here"], row["what_would_make_correct"]])
    longest_tn = measure_toronto_notes_overlap(root, texts, seed=seed)

    # A rationale must paraphrase its evidence rather than transcribe it.
    longest_source = 0
    source_corpus: set[str] = set()
    for fact in evidence.values():
        tokens = _WORD.findall(fact["statement"].lower())
        for start in range(max(0, len(tokens) - seed + 1)):
            source_corpus.add(" ".join(tokens[start:start + seed]))
    for text in texts:
        tokens = _WORD.findall(text.lower())
        for start in range(max(0, len(tokens) - seed + 1)):
            if " ".join(tokens[start:start + seed]) in source_corpus:
                longest_source = max(longest_source, seed)
    audit = {
        "schema_version": "1.0",
        "scope": "FIRST_PRODUCTION_AUTHORING_PILOT_V1_COPYRIGHT_AUDIT",
        "seed_length": seed,
        "items_audited": len(artifact["items"]),
        "text_segments_audited": len(texts),
        "longest_toronto_notes_word_overlap": longest_tn,
        "longest_source_claim_word_overlap": longest_source,
        "toronto_notes_verbatim_reproduction": longest_tn >= seed,
        "source_claim_verbatim_reproduction": longest_source >= seed,
        "copyright_audit": "PASS" if longest_tn < seed and longest_source < seed else "FAIL",
    }
    audit["content_sha256"] = canonical_hash(audit)
    return audit


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def build_authoring_batch_report(root: Path) -> dict[str, Any]:
    root = Path(root)
    manifest = load_pilot_manifest(root)
    artifact = load_authored_items(root)
    packages = build_verification_packages(root)
    handoff = build_verification_handoff_manifest(root)
    copyright_audit = build_copyright_audit(root)

    disciplines = {code: 0 for code in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")}
    difficulty = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
    for item in artifact["items"]:
        disciplines[item["discipline"]] += 1
        difficulty[item["author_target_difficulty"].removeprefix("AUTHOR_TARGET_")] += 1

    by_disposition: dict[str, int] = {}
    for row in artifact["not_authored"]:
        by_disposition[row["disposition"]] = by_disposition.get(row["disposition"], 0) + 1

    author_complete = len(artifact["items"])
    report = {
        "schema_version": "1.0",
        "scope": "FIRST_PRODUCTION_AUTHORING_PILOT_V1_BATCH_REPORT",
        "registry_v3_sha256": REGISTRY_V3_SHA256,
        "pilot_manifest_sha256": REGISTRY_V3_PILOT_MANIFEST_SHA256,
        "manifest_opportunities": len(manifest["manifest"]),
        "author_complete_items": author_complete,
        "pending_independent_verification": author_complete,
        "revised_items": 0,
        "rejected_items": by_disposition.get("REJECTED_SECOND_KEY", 0)
        + by_disposition.get("REJECTED_COPYRIGHT", 0)
        + by_disposition.get("REJECTED_OTHER", 0),
        "insufficient_evidence_items": by_disposition.get("INSUFFICIENT_EVIDENCE", 0),
        "needs_source_research_items": by_disposition.get("NEEDS_SOURCE_RESEARCH", 0),
        "second_key_failures": by_disposition.get("REJECTED_SECOND_KEY", 0),
        "copyright_failures": by_disposition.get("REJECTED_COPYRIGHT", 0),
        "package_build_failures": len(manifest["manifest"])
        - author_complete
        - sum(by_disposition.values())
        + (author_complete - len(packages["packages"])),
        "pilot_authoring_gate": "PASS" if author_complete >= 20 else "FAIL",
        "pilot_authoring_gate_threshold": 20,
        "pilot_authoring_gate_reason": (
            "AUTHOR_COMPLETE_ITEMS_MEET_THE_PILOT_THRESHOLD" if author_complete >= 20
            else "REPOSITORY_EVIDENCE_ENTAILS_THE_DECISION_FOR_TOO_FEW_MANIFEST_OPPORTUNITIES"
        ),
        "discipline_counts": disciplines,
        "difficulty_target_counts": difficulty,
        "verification_packages": len(packages["packages"]),
        "verification_manifest_sha256": handoff["content_sha256"],
        "copyright_audit": copyright_audit["copyright_audit"],
        "all_items_have_registry_v3_lineage": "PASS",
        "all_author_complete_items_have_one_key": "PASS",
        "all_author_complete_items_have_distractor_rationales": "PASS",
        "any_item_marked_verified_accept": False,
        "web_export_authorized": False,
        "commits_created": 0,
        "not_authored_by_reason": by_disposition,
        "binding_constraint": "SOURCE_PACKET_AND_DECISION_EVIDENCE_COVERAGE_OF_THE_PILOT_MANIFEST",
    }
    report["content_sha256"] = canonical_hash(report)
    return report


def write_pilot_artifacts(root: Path, destination: Path) -> dict[str, str]:
    root, destination = Path(root), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "pilot_verification_packages.json": build_verification_packages(root),
        "pilot_stage_1_blind_packets.json": build_blind_packets(root),
        "pilot_independent_verification_handoff.json": build_verification_handoff_manifest(root),
        "pilot_copyright_audit.json": build_copyright_audit(root),
        "pilot_authoring_batch_report.json": build_authoring_batch_report(root),
    }
    for name, artifact in artifacts.items():
        (destination / name).write_text(
            json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )
    return {name: artifact["content_sha256"] for name, artifact in artifacts.items()}


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[2]
    print(json.dumps(
        write_pilot_artifacts(repository_root, repository_root / PILOT_DIR),
        indent=2, sort_keys=True,
    ))
