"""Catalogue-integrity and decision-compatible global discovery utilities.

This module is a child of the frozen Discovery-V3 implementation.  It imports
only stable hash helpers and never mutates the V1 catalogue or V3 outputs.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any, Mapping, Sequence

from .contrast_supply_v3 import canonical_content_sha256
from .option_set_admissibility import RESPONSE_CLASS_AXES


CATALOGUE_TAXONOMY = (
    "VALID_CONCEPT",
    "EXTRACTION_SENTENCE_FRAGMENT",
    "OCR_GARBLED_LABEL",
    "FIGURE_OR_TABLE_FRAGMENT",
    "STRUCTURAL_FURNITURE",
    "GENERIC_NONOPTION_HEADING",
    "AMBIGUOUS_CONCEPT_LABEL",
    "OTHER_INVALID",
    "UNCERTAIN",
)
SIGNATURE_DIMENSIONS = ("decision_intent", "target_domain", "clinical_stage")
V4_CANDIDATE_BUDGET = 10
DISCOVERY_V4_VERSION = "GLOBAL_DECISION_COMPATIBLE_DISCOVERY_V4_1"

_REVIEWED_SOURCES = frozenset({
    "INDEPENDENTLY_APPROVED_SEED",
    "INDEPENDENTLY_APPROVED_AOM_CONTROL",
    "REUSABLE_CONTRAST_CACHE_V1",
    "independent-review",
    "reviewed",
})
_GENERIC_HEADINGS = frozenset({
    "approach", "complications", "diagnosis", "differential diagnosis",
    "investigations", "management", "overview", "principles", "treatment",
})
_TRAILING_FRAGMENT_WORDS = frozenset({
    "a", "an", "and", "as", "at", "by", "co", "for", "from", "if",
    "in", "of", "on", "or", "reasonably", "that", "the", "this", "to",
    "with", "without",
})
_IMPERATIVE_OR_SENTENCE_START = re.compile(
    r"^(?:add|administer|admit|apply|arrange|check|commission|complete|confirm|"
    r"discharge|express|feed|give|launch|observe|obtain|offer|proceed|pump|raise|"
    r"refer|start|transfer|use|this is|these are|it is|there is|there are|no treatment)\b",
    re.IGNORECASE,
)
_FILLER_TOKEN = re.compile(r"\b(?:c{2,}e*|e{2,}s?|o{2,}|teens)\b", re.IGNORECASE)
_EMBEDDED_PAGE_CODE = re.compile(r"\b[A-Z]{1,4}\d{1,3}\b")
_CAPTION = re.compile(r"^(?:figure|table|box)\s+\d+[.:]", re.IGNORECASE)
_LEADING_FURNITURE = re.compile(r"^(?:appendix\b|\.?\s*\d+[.)]?\s+)", re.IGNORECASE)
_TOC_BRAND = re.compile(r"\bToronto Notes\s+20\d{2}\b", re.IGNORECASE)
_SUSPICIOUS_LOWERCASE_START = re.compile(r"^(?:aoe\b|chilles\b|f\s+Approach\b|lron\b)", re.IGNORECASE)
_BROKEN_CAMEL_TOKEN = re.compile(r"\b(?:[a-z]{3,}[A-Z][a-z]+|[A-Z][a-z]+[A-Z])\b")
_SPLIT_WORD_SEQUENCE = re.compile(r"\b[A-Z][a-z]?\s+[a-z]{3,}\s+[a-z]{1,2}\b")
_OCR_ROMAN_NUMERAL = re.compile(r"\bFactor\s+V(?:ill|l{2,})\b", re.IGNORECASE)
_QUOTED_WORD_FRAGMENT = re.compile(r"^[“\"]?[a-z]{1,4}[”\"]?\s+")


def _has_reviewed_provenance(row: Mapping[str, Any]) -> bool:
    return any(item.get("source") in _REVIEWED_SOURCES for item in row.get("provenance", []))


def _result(classification: str, *reasons: str) -> dict[str, Any]:
    if classification not in CATALOGUE_TAXONOMY:
        raise ValueError(f"unknown catalogue taxonomy value: {classification}")
    return {"classification": classification, "reason_codes": list(reasons)}


def classify_catalogue_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one canonical label using structural extraction signals only."""
    label = " ".join(str(row.get("normalized_label") or "").strip().split())
    if not label:
        return _result("OTHER_INVALID", "EMPTY_LABEL")
    lower = label.casefold()
    reviewed = _has_reviewed_provenance(row)
    vocabulary_source = (row.get("graph_identity") or {}).get("vocabulary_source")

    if vocabulary_source == "CANONICAL_STEM_FEATURE_VOCABULARY":
        return _result("OTHER_INVALID", "STEM_FEATURE_STATEMENT_NOT_CANDIDATE_IDENTITY")

    if _CAPTION.match(label):
        return _result("FIGURE_OR_TABLE_FRAGMENT", "CAPTION_PREFIX")
    if _TOC_BRAND.search(label):
        return _result("STRUCTURAL_FURNITURE", "DOCUMENT_BRAND_AND_YEAR")
    if _LEADING_FURNITURE.match(label):
        return _result("STRUCTURAL_FURNITURE", "LEADING_PAGE_OR_APPENDIX_FURNITURE")
    filler_count = len(_FILLER_TOKEN.findall(label))
    if filler_count >= 2:
        return _result("OCR_GARBLED_LABEL", "REPEATED_EXTRACTION_FILLER_TOKENS")
    if _SUSPICIOUS_LOWERCASE_START.match(label):
        return _result("OCR_GARBLED_LABEL", "TRUNCATED_OR_SUBSTITUTED_INITIAL_TOKEN")
    if _BROKEN_CAMEL_TOKEN.search(label) and not re.search(r"\b(?:HbA1c|rTMS)\b", label):
        return _result("OCR_GARBLED_LABEL", "BROKEN_WORD_BOUNDARY_OR_JOINED_TOKENS")
    if _SPLIT_WORD_SEQUENCE.search(label):
        return _result("OCR_GARBLED_LABEL", "SPLIT_WORD_TOKEN_SEQUENCE")
    if "|" in label or _OCR_ROMAN_NUMERAL.search(label):
        return _result("OCR_GARBLED_LABEL", "OCR_SYMBOL_OR_ROMAN_NUMERAL_SUBSTITUTION")
    if re.search(r"\s\.\s", label):
        return _result("OCR_GARBLED_LABEL", "MULTIPLE_HEADINGS_JOINED_BY_EXTRACTION_SEPARATOR")
    if _EMBEDDED_PAGE_CODE.search(label) and filler_count:
        return _result("OCR_GARBLED_LABEL", "PAGE_CODE_WITH_EXTRACTION_FILLER")
    if lower in _GENERIC_HEADINGS:
        return _result("GENERIC_NONOPTION_HEADING", "GENERIC_STRUCTURAL_HEADING")
    if re.search(r"\b(?:vs\.?|versus)\b", lower):
        return _result("AMBIGUOUS_CONCEPT_LABEL", "MULTIPLE_CONCEPT_COMPARISON")
    if label.count("(") != label.count(")") or label.count("[") != label.count("]"):
        return _result("OTHER_INVALID", "UNBALANCED_BRACKETS")
    if label.startswith("."):
        return _result("STRUCTURAL_FURNITURE", "LEADING_PUNCTUATION_FURNITURE")
    words = label.split()
    last = words[-1].strip(".,;").casefold()
    title_like = all(
        not any(character.isalpha() for character in word)
        or word[0].isupper()
        for word in words
    )
    prose_start = bool(_IMPERATIVE_OR_SENTENCE_START.match(label)) and not title_like
    if not reviewed and (prose_start or last in _TRAILING_FRAGMENT_WORDS):
        return _result("EXTRACTION_SENTENCE_FRAGMENT", "PROSE_OR_INCOMPLETE_CLAUSE")
    if not reviewed and len(words) > 14:
        return _result("UNCERTAIN", "LONG_UNREVIEWED_STRUCTURAL_LABEL")
    if label[0].islower() and not re.match(r"^(?:a-Thalassemia|von\s)", label):
        return _result("UNCERTAIN", "ABNORMAL_LOWERCASE_INITIAL")
    if label.startswith(("“", '"')) and _QUOTED_WORD_FRAGMENT.match(label):
        return _result("UNCERTAIN", "QUOTED_WORD_FRAGMENT")
    return _result("VALID_CONCEPT", "NO_INTEGRITY_DEFECT_DETECTED")


def audit_candidate_catalogue(
    rows: Sequence[Mapping[str, Any]], *, parent_content_sha256: str
) -> dict[str, Any]:
    """Audit every row and reconcile the required one-of taxonomy."""
    if len(parent_content_sha256) != 64:
        raise ValueError("parent hash must be a 64-character content SHA256")
    audited = []
    counts: Counter[str] = Counter()
    seen: set[str] = set()
    for row in rows:
        candidate_id = str(row["canonical_candidate_id"])
        if candidate_id in seen:
            raise ValueError(f"duplicate catalogue identity: {candidate_id}")
        seen.add(candidate_id)
        verdict = classify_catalogue_row(row)
        counts[verdict["classification"]] += 1
        label = str(row["normalized_label"])
        audited.append({
            "canonical_candidate_id": candidate_id,
            "normalized_label_sha256": hashlib.sha256(label.encode()).hexdigest(),
            "normalized_label_token_count": len(label.split()),
            **verdict,
        })
    value = {
        "schema_version": "GLOBAL_CANDIDATE_CATALOGUE_INTEGRITY_AUDIT_V1",
        "parent_catalogue_content_sha256": parent_content_sha256,
        "audited_concept_count": len(audited),
        "counts": {name: counts[name] for name in CATALOGUE_TAXONOMY},
        "rows": audited,
    }
    value["content_sha256"] = canonical_content_sha256(value)
    return value


def build_clean_catalogue_v2(
    rows: Sequence[Mapping[str, Any]], *, audit: Mapping[str, Any],
    parent_content_sha256: str,
) -> dict[str, Any]:
    """Create an immutable clean child from a freshly rebuilt source catalogue."""
    if audit.get("parent_catalogue_content_sha256") != parent_content_sha256:
        raise ValueError("audit parent hash does not match requested parent hash")
    row_ids = {str(row["canonical_candidate_id"]) for row in rows}
    audit_ids = {str(row["canonical_candidate_id"]) for row in audit.get("rows", [])}
    if row_ids != audit_ids or len(rows) != len(audit.get("rows", [])):
        raise ValueError("catalogue and audit row identities do not match")
    verdicts = {row["canonical_candidate_id"]: row for row in audit["rows"]}
    concepts = [dict(row) for row in rows
                if verdicts[row["canonical_candidate_id"]]["classification"] == "VALID_CONCEPT"]
    concepts.sort(key=lambda row: row["canonical_candidate_id"])
    counts = dict(audit["counts"])
    removed = len(rows) - len(concepts)
    value = {
        "schema_version": "GLOBAL_CANDIDATE_CONCEPT_CATALOGUE_V2",
        "scope": "CLEAN_STRUCTURAL_AND_REVIEWED_CANONICAL_CANDIDATE_IDENTITIES",
        "parent_catalogue_content_sha256": parent_content_sha256,
        "source_policy": "Fresh rebuild from canonical graph and independently reviewed identities; no chunk prose.",
        "concept_count": len(concepts),
        "typed_concept_count": sum(bool(row.get("response_classes")) for row in concepts),
        "removed_invalid_count": removed,
        "uncertain_count": counts["UNCERTAIN"],
        "integrity_reason_counts": counts,
        "integrity_audit_content_sha256": audit["content_sha256"],
        "concepts": concepts,
    }
    value["content_sha256"] = canonical_content_sha256(value)
    return value


def reconstruct_v3_wrong_decisions(
    discovery: Mapping[str, Any],
    review: Mapping[str, Any],
    semantics: Mapping[str, Any],
    selection: Mapping[str, Any],
    *,
    expected_count: int = 52,
) -> list[dict[str, Any]]:
    """Join frozen V3 candidates to their prior verdict and decision context."""
    reviews: dict[tuple[str, str], Mapping[str, Any]] = {}
    for batch in review.get("batches", []):
        for row in batch.get("rows", []):
            key = (str(row["development_id"]), str(row["canonical_candidate_id"]))
            if key in reviews:
                raise ValueError(f"duplicate review for {key[0]} / {key[1]}")
            reviews[key] = row
    semantic_by_id = {row["development_id"]: row for row in semantics.get("opportunities", [])}
    selection_by_id = {row["development_id"]: row for row in selection.get("opportunities", [])}
    result: list[dict[str, Any]] = []
    for opportunity in discovery.get("opportunities", []):
        opportunity_id = opportunity["development_id"]
        if opportunity_id not in semantic_by_id or opportunity_id not in selection_by_id:
            raise ValueError(f"missing decision context for {opportunity_id}")
        semantic = semantic_by_id[opportunity_id]
        selected = selection_by_id[opportunity_id]
        for candidate in opportunity.get("candidates", []):
            key = (opportunity_id, candidate["canonical_candidate_id"])
            prior = reviews.get(key)
            if not prior or prior.get("classification") != "WRONG_DECISION":
                continue
            result.append({
                "opportunity_id": opportunity_id,
                "discipline": selected["discipline"],
                "study_unit_id": selected["study_unit_id"],
                "learner_decision_id": semantic["learner_decision_id"],
                "learner_decision": semantic["learner_decision"],
                "key": semantic["learner_decision"],
                "candidate_id": candidate["canonical_candidate_id"],
                "candidate_label": candidate["normalized_label"],
                "candidate_response_classes": candidate.get("response_classes", []),
                "candidate_decision_granularities": candidate.get("decision_granularities", []),
                "candidate_source_metadata": {
                    field: candidate.get(field)
                    for field in (
                        "source_ids", "chapters", "study_unit_ids", "section_paths",
                        "graph_identity", "provenance",
                    )
                },
                "v3_admission_and_ranking": {
                    "demanded_response_class": semantic["demanded_response_class"],
                    "decision_granularity": semantic["decision_granularity"],
                    "ranking_signals": candidate.get("ranking_signals", {}),
                },
                "previous_clinical_verdict": prior["classification"],
                "previous_clinical_reason": prior["reason"],
            })
    result.sort(key=lambda row: (row["opportunity_id"], row["candidate_id"]))
    if len(result) != expected_count:
        raise ValueError(f"expected {expected_count} frozen WRONG_DECISION rows, found {len(result)}")
    return result


def validate_decision_signature(
    signature: Mapping[str, Any], *,
    controlled_vocabularies: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, str]:
    """Validate the closed three-dimensional signature contract."""
    missing = [field for field in SIGNATURE_DIMENSIONS if not signature.get(field)]
    if missing:
        raise ValueError(f"missing signature dimension: {missing[0]}")
    unknown_fields = set(signature) - set(SIGNATURE_DIMENSIONS)
    if unknown_fields:
        raise ValueError(f"unknown signature field: {sorted(unknown_fields)[0]}")
    result = {field: str(signature[field]) for field in SIGNATURE_DIMENSIONS}
    if controlled_vocabularies is not None:
        for field, token in result.items():
            if token not in set(controlled_vocabularies.get(field, [])):
                raise ValueError(f"unknown {field}: {token}")
    return result


def signatures_compatible(
    opportunity_signature: Mapping[str, Any],
    candidate_signature: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the earliest incompatible signature dimension, or compatibility."""
    opportunity = validate_decision_signature(opportunity_signature)
    candidate = validate_decision_signature(candidate_signature)
    checks = (
        ("decision_intent", "WRONG_DECISION_INTENT"),
        ("target_domain", "WRONG_TARGET_DOMAIN"),
        ("clinical_stage", "WRONG_CLINICAL_STAGE"),
    )
    for field, reason in checks:
        if opportunity[field] != candidate[field]:
            return {"compatible": False, "reason": reason}
    return {"compatible": True, "reason": None}


def _response_class_compatible(demanded: str, candidate_classes: set[str]) -> bool:
    compatible = {demanded}
    for definition in RESPONSE_CLASS_AXES.values():
        if demanded == definition["generic_token"]:
            compatible.update(definition["tokens"])
            break
    return bool(candidate_classes & compatible)


def discover_global_typed_candidates_v4(
    catalogue: Sequence[Mapping[str, Any]], *,
    opportunity: Mapping[str, Any],
    opportunity_signature: Mapping[str, Any],
    candidate_signatures: Mapping[str, Mapping[str, Any]],
    budget: int = V4_CANDIDATE_BUDGET,
) -> dict[str, Any]:
    """Filter globally by V3 structural typing plus Decision Signature V1."""
    if budget <= 0:
        raise ValueError("candidate budget must be positive")
    opportunity_signature = validate_decision_signature(opportunity_signature)
    response_class = str(opportunity["demanded_response_class"])
    granularity = str(opportunity["decision_granularity"])
    key_aliases = {str(value).casefold() for value in opportunity.get("key_aliases", [])}
    wanted_families = set(opportunity.get("semantic_families", []))
    cheap_rejections: Counter[str] = Counter()
    signature_rejections: list[dict[str, str]] = []
    ranked: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []
    for original in catalogue:
        candidate_id = str(original["canonical_candidate_id"])
        label = str(original["normalized_label"])
        aliases = {label.casefold(), *(str(value).casefold() for value in original.get("aliases", []))}
        if aliases & key_aliases:
            cheap_rejections["KEY_ALIAS"] += 1
            continue
        candidate_classes = set(original.get("response_classes", []))
        if not _response_class_compatible(response_class, candidate_classes):
            cheap_rejections["WRONG_RESPONSE_CLASS"] += 1
            continue
        granularities = set(original.get("decision_granularities", []))
        if granularities and granularity not in granularities:
            cheap_rejections["WRONG_GRANULARITY"] += 1
            continue
        candidate_signature = candidate_signatures.get(candidate_id)
        if candidate_signature is None:
            signature_rejections.append({
                "candidate_id": candidate_id, "reason": "MISSING_CANDIDATE_SIGNATURE"
            })
            continue
        compatibility = signatures_compatible(opportunity_signature, candidate_signature)
        if not compatibility["compatible"]:
            signature_rejections.append({
                "candidate_id": candidate_id, "reason": compatibility["reason"]
            })
            continue
        same_unit = opportunity.get("study_unit_id") in set(original.get("study_unit_ids", []))
        same_chapter = opportunity.get("chapter_code") in set(original.get("chapters", []))
        family_match = bool(wanted_families & set(original.get("semantic_families", [])))
        row = dict(original)
        row["cross_study_unit"] = not same_unit
        row["cross_chapter"] = not same_chapter
        row["decision_signature"] = dict(candidate_signature)
        row["ranking_signals"] = {
            "response_class_match": True,
            "granularity_match": not granularities or granularity in granularities,
            "decision_signature_match": True,
            "semantic_family_match": family_match,
            "same_study_unit": same_unit,
            "same_chapter": same_chapter,
        }
        score = (
            0 if family_match else 1,
            0 if same_unit else 1,
            0 if same_chapter else 1,
            candidate_id,
        )
        ranked.append((score, row))
    candidates = [row for _, row in sorted(ranked, key=lambda item: item[0])[:budget]]
    signature_counts = Counter(row["reason"] for row in signature_rejections)
    return {
        "discovery_v4_version": DISCOVERY_V4_VERSION,
        "candidate_budget": budget,
        "catalogue_rows_scanned": len(catalogue),
        "cheap_rejection_counts": dict(sorted(cheap_rejections.items())),
        "signature_rejection_counts": dict(sorted(signature_counts.items())),
        "signature_rejections": signature_rejections,
        "compatible_before_budget_count": len(ranked),
        "candidates": candidates,
    }


def candidate_context_sha256(
    opportunity: Mapping[str, Any], candidate: Mapping[str, Any]
) -> str:
    """Hash only fields that define the candidate's semantic review context."""
    value = {
        "development_id": opportunity["development_id"],
        "learner_decision": opportunity["learner_decision"],
        "demanded_response_class": opportunity["demanded_response_class"],
        "decision_granularity": opportunity["decision_granularity"],
        "canonical_candidate_id": candidate["canonical_candidate_id"],
        "normalized_label": candidate["normalized_label"],
        "candidate_response_classes": candidate.get("response_classes", []),
        "candidate_decision_granularities": candidate.get("decision_granularities", []),
    }
    return canonical_content_sha256(value)


def reuse_frozen_candidate_verdicts(
    current_opportunities: Sequence[Mapping[str, Any]],
    frozen_opportunities: Sequence[Mapping[str, Any]],
    frozen_review: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Reuse a verdict only when candidate and decision context hashes match."""
    frozen_contexts: dict[tuple[str, str], str] = {}
    for opportunity in frozen_opportunities:
        for candidate in opportunity.get("candidates", []):
            key = (opportunity["development_id"], candidate["canonical_candidate_id"])
            frozen_contexts[key] = candidate_context_sha256(opportunity, candidate)
    reviews: dict[tuple[str, str], Mapping[str, Any]] = {}
    for batch in frozen_review.get("batches", []):
        for row in batch.get("rows", []):
            key = (row["development_id"], row["canonical_candidate_id"])
            if key in reviews:
                raise ValueError(f"duplicate frozen review for {key[0]} / {key[1]}")
            reviews[key] = row
    result = []
    for opportunity in current_opportunities:
        for candidate in opportunity.get("candidates", []):
            key = (opportunity["development_id"], candidate["canonical_candidate_id"])
            context_hash = candidate_context_sha256(opportunity, candidate)
            prior = reviews.get(key)
            reusable = frozen_contexts.get(key) == context_hash and prior is not None
            result.append({
                "development_id": opportunity["development_id"],
                "canonical_candidate_id": candidate["canonical_candidate_id"],
                "candidate_context_sha256": context_hash,
                "verdict_reused": reusable,
                "classification": prior["classification"] if reusable else "UNCERTAIN",
                "reason": prior["reason"] if reusable else "No exact frozen candidate-context hash match; new semantic review required.",
            })
    return result
