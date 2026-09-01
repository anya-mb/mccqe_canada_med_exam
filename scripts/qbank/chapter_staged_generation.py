"""Fail-closed contracts for chapter-anchored, globally contrastive MCQ construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


class ChapterStagedGenerationError(ValueError):
    """A chapter anchor, contrast, staged item, or pilot is unsafe to accept."""


STAGE_SEQUENCE = [
    "TORONTO_NOTES_ANCHOR",
    "MCC_OBJECTIVE_PHYSICIAN_ACTIVITY",
    "PRIMARY_LEARNER_DECISION",
    "ANCHOR_FIDELITY",
    "OPEN_ENDED_STEM_KEY",
    "BLIND_COVER_OPTIONS_SOLVER",
    "GLOBAL_CONTRAST_RETRIEVAL",
    "CONTRASTIVE_EVIDENCE_MATRIX",
    "SEPARATE_DISTRACTOR_CONSTRUCTION",
    "DISTRACTOR_ADVERSARIAL_RANKING",
    "MCQ_ASSEMBLY",
    "PLAN_FIDELITY_SHORTCUT_CUE_CHECK",
    "RATIONALES",
    "FRESH_INDEPENDENT_VERIFICATION",
]
STAGE_SEQUENCE_V2 = STAGE_SEQUENCE[:10] + [
    "OPTION_REALIZATION",
    "PARALLEL_OPTION_SET_REVIEW",
] + STAGE_SEQUENCE[10:]
PHYSICIAN_ACTIVITIES = {
    "Assessment/Diagnosis",
    "Management",
    "Communication",
    "Professional Behaviours",
}
ANCHOR_CRITERIA = {
    "decision_ownership",
    "key_ownership",
    "positive_anchor_evidence",
    "immediate_review_fit",
    "counterfactual_necessity",
    "contrast_role_integrity",
    "allocation_integrity",
}
DISTRACTOR_ASSESSMENTS = {
    "plausibility",
    "same_option_dimension",
    "mcc_level_relevance",
    "medical_professional_confusability",
    "no_key_ambiguity",
    "evidence_grounded_discriminator",
}
ACCEPTANCE_CHECKS = {
    "cover_the_options",
    "option_only_cues",
    "clang_keyword",
    "option_homogeneity",
    "answer_length_specificity",
    "plan_fidelity",
    "anchor_fidelity",
    "context_necessity",
}
VERIFICATION_DIMENSIONS = {
    "factual_correctness",
    "evidence_support",
    "single_best_answer",
    "mcc_objective_level",
    "anchor_fidelity",
    "plan_fidelity",
    "reasoning_quality",
    "stem_lead_in_quality",
    "context_necessity",
    "distractor_plausibility",
    "cross_chapter_contrast_quality",
    "rationale_quality",
    "item_writing_flaws",
    "cueing",
    "duplication",
}
DEFECT_CATEGORIES = {
    "FACTUAL_ERROR",
    "UNSUPPORTED_CLAIM",
    "AMBIGUOUS_BEST_ANSWER",
    "ANCHOR_FIDELITY_FAILURE",
    "PLAN_MISMATCH",
    "WEAK_DISTRACTOR",
    "CONTEXT_NECESSITY_FAILURE",
    "COVER_OPTIONS_FAILURE",
    "OPTION_CUE_FAILURE",
    "RATIONALE_DEFICIENCY",
    "MATERIAL_DUPLICATION",
}
SEMANTIC_CUE_CHECKS = {
    "key_only_specificity",
    "semantic_odd_one_out",
    "option_category_match",
    "convergence",
    "clang_testwise_detectability",
    "natural_parallelism",
    "meaning_preservation",
}
OPTION_CUE_CATEGORIES = {
    "ANSWER_LENGTH_CUE",
    "ANSWER_SPECIFICITY_CUE",
    "LEXICAL_OVERLAP_CLANG",
    "GRAMMATICAL_CUE",
    "OPTION_CATEGORY_MISMATCH",
    "KEY_ONLY_QUALIFIER",
    "ABSOLUTE_LANGUAGE_CUE",
    "OPTION_CONVERGENCE",
    "SEMANTIC_ODD_ONE_OUT",
    "POSITION_CUE",
    "PARALLELISM_FAILURE",
    "OTHER",
}
_PHRASE_STOPWORDS = {
    "and", "for", "from", "into", "only", "that", "the", "then", "this", "with",
}


def find_option_shape_cues(options: list[dict[str, Any]]) -> list[str]:
    """Return deterministic, high-specificity option-shape cues.

    Semantic cue review remains independent. This catches only an obvious key
    length extreme: at least five tokens and 1.5 times beyond the nearest
    distractor. The conservative threshold avoids treating ordinary wording
    variation as a defect.
    """
    if not isinstance(options, list):
        return ["INVALID_OPTION_SHAPE"]
    key_lengths: list[int] = []
    distractor_lengths: list[int] = []
    for option in options:
        if not isinstance(option, dict) or not isinstance(option.get("text"), str):
            return ["INVALID_OPTION_SHAPE"]
        length = len(re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", option["text"]))
        if option.get("role") == "KEY":
            key_lengths.append(length)
        elif option.get("role") == "DISTRACTOR":
            distractor_lengths.append(length)
    if len(key_lengths) != 1 or not distractor_lengths:
        return ["INVALID_OPTION_SHAPE"]

    key_length = key_lengths[0]
    longest_distractor = max(distractor_lengths)
    shortest_distractor = min(distractor_lengths)
    cues: list[str] = []
    if key_length - longest_distractor >= 5 and key_length >= 1.5 * longest_distractor:
        cues.append("KEY_UNIQUELY_LONG_AND_SPECIFIC")
    if shortest_distractor - key_length >= 5 and key_length * 1.5 <= shortest_distractor:
        cues.append("KEY_UNIQUELY_SHORT")
    return cues


def _meaningful_bigrams(text_value: str) -> set[tuple[str, str]]:
    tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text_value.lower())
    return {
        (left, right)
        for left, right in zip(tokens, tokens[1:])
        if left not in _PHRASE_STOPWORDS
        and right not in _PHRASE_STOPWORDS
        and len(left) >= 4
        and len(right) >= 4
    }


def find_option_text_cues(stem: str, options: list[dict[str, Any]]) -> list[str]:
    """Return deterministic surface defects without judging medical semantics."""
    if not isinstance(stem, str) or not isinstance(options, list):
        return ["INVALID_OPTION_TEXT_SET"]
    findings = find_option_shape_cues(options)
    normalized = [
        " ".join(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", option.get("text", "").lower()))
        if isinstance(option, dict)
        else ""
        for option in options
    ]
    if any(not value for value in normalized):
        return sorted(set(findings + ["INVALID_OPTION_TEXT_SET"]))
    if len(set(normalized)) != len(normalized):
        findings.append("DUPLICATE_OPTION_TEXT")
    forms = {
        option.get("grammatical_form")
        for option in options
        if isinstance(option, dict)
    }
    if len(forms) != 1 or any(not isinstance(form, str) or not form for form in forms):
        findings.append("NONPARALLEL_GRAMMATICAL_FORM")

    key_options = [option for option in options if option.get("role") == "KEY"]
    distractors = [option for option in options if option.get("role") == "DISTRACTOR"]
    if len(key_options) != 1 or not distractors:
        return sorted(set(findings + ["INVALID_OPTION_TEXT_SET"]))
    key_phrases = _meaningful_bigrams(key_options[0]["text"])
    distractor_phrases = [_meaningful_bigrams(option["text"]) for option in distractors]
    if key_phrases.intersection(_meaningful_bigrams(stem)).difference(
        set().union(*distractor_phrases)
    ):
        findings.append("KEY_ONLY_STEM_PHRASE")
    return sorted(set(findings))


def find_option_position_cues(items: list[dict[str, Any]]) -> list[str]:
    """Detect a repeated correct-answer position across an entire multi-item batch."""
    positions = [
        item.get("assembly", {}).get("correct_answer")
        for item in items
        if isinstance(item, dict)
    ]
    if len(positions) < 2 or any(position not in set("ABCDE") for position in positions):
        return ["INVALID_CORRECT_POSITION_BATCH"]
    counts = {position: positions.count(position) for position in set(positions)}
    if len(counts) == 1:
        return ["CORRECT_POSITION_REPEATED_ACROSS_ENTIRE_BATCH"]
    if len(positions) <= 5 and len(counts) != len(positions):
        return ["CORRECT_POSITIONS_NOT_BALANCED"]
    if len(positions) > 5 and max(counts.values()) - min(counts.values()) > 1:
        return ["CORRECT_POSITIONS_NOT_BALANCED"]
    return []


def validate_option_cue_review(
    staged: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    """Validate a fresh, option-only semantic cue review and its stop decision."""
    items = staged.get("items") if isinstance(staged, dict) else None
    if not isinstance(items, list) or len(items) != 3:
        raise ChapterStagedGenerationError("option cue review requires exactly three staged items")
    if (
        not isinstance(review, dict)
        or review.get("staged_artifact_sha256") != canonical_sha256(staged)
        or review.get("pilot_id") != staged.get("pilot_id")
    ):
        raise ChapterStagedGenerationError("option cue review lineage is invalid")

    reviewer_id = _nonempty(review.get("reviewer_id"), "option cue reviewer ID")
    prior_actors = {
        actor
        for item in items
        for actor in (
            item.get("author_id"),
            item.get("anchor_fidelity_preflight", {}).get("reviewer_id"),
            item.get("blind_solver", {}).get("solver_id"),
            item.get("global_contrast_retrieval", {}).get("semantic_ranker_id"),
            item.get("distractor_construction", {}).get("constructor_id"),
            item.get("distractor_adversarial_review", {}).get("reviewer_id"),
            item.get("option_realization", {}).get("realizer_id"),
            item.get("parallel_option_set_review", {}).get("reviewer_id"),
            item.get("assembly", {}).get("assembler_id"),
            item.get("acceptance_review", {}).get("reviewer_id"),
        )
        if actor
    }
    if reviewer_id in prior_actors:
        raise ChapterStagedGenerationError("option cue review requires a fresh reviewer")

    context = review.get("independent_context")
    expected_hidden = {
        "stem",
        "lead_in",
        "correct_answer",
        "semantic_option_text",
        "contrast_ids",
        "evidence",
        "provisional_self_review",
        "acceptance_review",
        "rationales",
    }
    if (
        not isinstance(context, dict)
        or context.get("first_pass_shown") != ["realized_option_text"]
        or set(context.get("first_pass_hidden", [])) != expected_hidden
        or context.get("verdict_independent_of_provisional_self_review") is not True
    ):
        raise ChapterStagedGenerationError("option cue review context is not independent")

    results = review.get("items")
    item_ids = [item.get("item_id") for item in items]
    if (
        not isinstance(results, list)
        or [row.get("item_id") for row in results if isinstance(row, dict)] != item_ids
    ):
        raise ChapterStagedGenerationError("option cue review item coverage is invalid")

    passed = 0
    material_count = 0
    false_positive_count = 0
    finding_ids: set[str] = set()
    for row in results:
        real_findings = row.get("real_findings")
        false_findings = row.get("false_positive_findings")
        if not isinstance(real_findings, list) or not isinstance(false_findings, list):
            raise ChapterStagedGenerationError("option cue review findings are invalid")
        if row.get("semantic_and_evidence_preservation") != "PASS" or row.get("single_best_answer") != "PASS":
            raise ChapterStagedGenerationError("option cue review detected semantic or answer drift")
        verdict = row.get("verdict")
        if verdict == "PASS":
            passed += 1
            if real_findings:
                raise ChapterStagedGenerationError("passing option set has a material cue")
        elif verdict == "FAIL":
            if not real_findings:
                raise ChapterStagedGenerationError("failed option set lacks a material cue")
        else:
            raise ChapterStagedGenerationError("option cue review verdict is invalid")

        for finding in real_findings:
            categories = finding.get("categories") if isinstance(finding, dict) else None
            finding_id = finding.get("finding_id") if isinstance(finding, dict) else None
            if (
                not isinstance(finding_id, str)
                or not finding_id
                or finding_id in finding_ids
                or not isinstance(categories, list)
                or not categories
                or not set(categories).issubset(OPTION_CUE_CATEGORIES)
                or finding.get("testwise_exploitable") is not True
            ):
                raise ChapterStagedGenerationError("material option cue finding is invalid")
            _nonempty(finding.get("cause"), "material option cue cause")
            _nonempty(finding.get("reason"), "material option cue reason")
            finding_ids.add(finding_id)
        for finding in false_findings:
            categories = finding.get("suspected_categories") if isinstance(finding, dict) else None
            finding_id = finding.get("finding_id") if isinstance(finding, dict) else None
            if (
                not isinstance(finding_id, str)
                or not finding_id
                or finding_id in finding_ids
                or not isinstance(categories, list)
                or not categories
                or not set(categories).issubset(OPTION_CUE_CATEGORIES)
                or finding.get("adjudication") != "FALSE_POSITIVE"
            ):
                raise ChapterStagedGenerationError("false-positive option cue finding is invalid")
            _nonempty(finding.get("reason"), "false-positive option cue reason")
            finding_ids.add(finding_id)
        material_count += len(real_findings)
        false_positive_count += len(false_findings)

    if (
        review.get("micro_items_generated") != 3
        or review.get("micro_items_passed") != passed
        or review.get("material_cue_findings") != material_count
        or review.get("false_positive_cue_findings") != false_positive_count
    ):
        raise ChapterStagedGenerationError("option cue review counts do not reconcile")
    expected_verdict = "PASS" if passed == 3 and material_count == 0 else "FAIL"
    if review.get("verdict") != expected_verdict:
        raise ChapterStagedGenerationError("option cue review aggregate verdict is invalid")
    candidate_status = staged.get("candidate_status")
    provisional = staged.get("provisional_parallel_option_review")
    if (
        expected_verdict == "PASS"
        and (candidate_status != "ACCEPTED" or provisional is not False)
    ) or (
        expected_verdict == "FAIL"
        and (
            candidate_status != "REJECTED_BY_FRESH_OPTION_CUE_REVIEW"
            or provisional is not True
        )
    ):
        raise ChapterStagedGenerationError("option cue verdict contradicts candidate status")
    if expected_verdict == "FAIL" and (
        review.get("pipeline_stop_stage") != "PARALLEL_OPTION_SET_REVIEW"
        or review.get("fresh_independent_verification_run") is not False
        or review.get("regeneration_attempted_after_failure") is not False
        or review.get("next_step") != "DIAGNOSE_REMAINING_MICRO_FAILURE"
    ):
        raise ChapterStagedGenerationError("failed option cue review did not stop correctly")
    return {
        "micro_items_generated": 3,
        "micro_items_passed": passed,
        "material_cue_findings": material_count,
        "false_positive_cue_findings": false_positive_count,
        "verdict": expected_verdict,
    }


def canonical_sha256(value: Any) -> str:
    """Return the deterministic JSON fingerprint used by all staged contracts."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ChapterStagedGenerationError(f"cannot read canonical JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ChapterStagedGenerationError(f"canonical JSON must be an object: {path}")
    return value


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChapterStagedGenerationError(f"{label} is required")
    return value


def _nonempty_strings(value: Any, label: str, *, minimum: int = 1) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) < minimum
        or len(set(value)) != len(value)
        or any(not isinstance(entry, str) or not entry.strip() for entry in value)
    ):
        raise ChapterStagedGenerationError(f"{label} is invalid")
    return value


def _pass_map(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected or any(result != "PASS" for result in value.values()):
        raise ChapterStagedGenerationError(f"{label} must contain only PASS results")


def _canonical_provenance(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "study_unit_id": row["study_unit_id"],
        "chapter_id": row["chapter_id"],
        "source_node_ids": row["source_node_ids"],
        "tn_pages": row["tn_pages"],
        "pdf_pages": row["pdf_pages"],
    }


def build_global_study_unit_index(root: Path) -> list[dict[str, Any]]:
    """Build the deterministic whole-book index without semantic inference."""
    root = Path(root).resolve()
    allocation = _read_object(root / "research/scope/final_question_allocation.json")
    addresses: dict[str, list[dict[str, Any]]] = {}
    for address in allocation.get("allocation_addresses", []):
        if isinstance(address, dict) and isinstance(address.get("study_unit_id"), str):
            addresses.setdefault(address["study_unit_id"], []).append(address)

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted((root / "research/scope/chapters").glob("*/study_units.json")):
        artifact = _read_object(path)
        for unit in artifact.get("study_units", []):
            if not isinstance(unit, dict):
                raise ChapterStagedGenerationError(f"invalid study unit in {path}")
            study_unit_id = _nonempty(unit.get("study_unit_id"), "study unit ID")
            if study_unit_id in seen:
                raise ChapterStagedGenerationError(f"duplicate study unit ID: {study_unit_id}")
            seen.add(study_unit_id)
            source_nodes = _nonempty_strings(unit.get("source_node_ids"), "study unit source nodes")
            pdf_pages = unit.get("pdf_page_range")
            if (
                not isinstance(pdf_pages, list)
                or len(pdf_pages) != 2
                or any(not isinstance(page, int) or page <= 0 for page in pdf_pages)
                or pdf_pages[0] > pdf_pages[1]
            ):
                raise ChapterStagedGenerationError(f"invalid PDF pages for {study_unit_id}")
            unit_addresses = sorted(addresses.get(study_unit_id, []), key=lambda value: value["allocation_address_id"])
            rows.append({
                "study_unit_id": study_unit_id,
                "title": _nonempty(unit.get("title"), "study unit title"),
                "chapter_id": _nonempty(unit.get("chapter_code"), "chapter ID"),
                "chapter_title": _nonempty(unit.get("chapter_title"), "chapter title"),
                "source_node_ids": source_nodes,
                "tn_pages": _nonempty(unit.get("tn_page_range"), "Toronto Notes pages"),
                "pdf_pages": pdf_pages,
                "allocation_address_ids": [value["allocation_address_id"] for value in unit_addresses],
                "allocation_statuses": sorted({value["allocation_status"] for value in unit_addresses}),
                "mcc_objective_ids": sorted({
                    objective
                    for value in unit_addresses
                    for objective in value.get("mcc_objective_ids", [])
                    if isinstance(objective, str)
                }),
            })
    if not rows:
        raise ChapterStagedGenerationError("global Toronto Notes study-unit index is empty")
    return sorted(rows, key=lambda row: (row["pdf_pages"][0], row["study_unit_id"]))


def resolve_chapter_anchor(
    root: Path,
    allocation_address_id: str,
    primary_mcc_objective: str,
    primary_physician_activity: str,
    primary_learner_decision: str,
) -> dict[str, Any]:
    """Resolve one chapter-review owner from frozen allocation and canonical MCC/TN data."""
    root = Path(root).resolve()
    _nonempty(primary_learner_decision, "primary learner decision")
    if primary_physician_activity not in PHYSICIAN_ACTIVITIES:
        raise ChapterStagedGenerationError("primary physician activity is not canonical")
    allocation = _read_object(root / "research/scope/final_question_allocation.json")
    matches = [
        row for row in allocation.get("allocation_addresses", [])
        if isinstance(row, dict) and row.get("allocation_address_id") == allocation_address_id
    ]
    if len(matches) != 1 or matches[0].get("allocation_status") != "ELIGIBLE":
        raise ChapterStagedGenerationError("anchor allocation address is not uniquely eligible")
    address = matches[0]
    if primary_mcc_objective not in address.get("mcc_objective_ids", []):
        raise ChapterStagedGenerationError("primary MCC objective is not owned by the anchor allocation")
    units = {row["study_unit_id"]: row for row in build_global_study_unit_index(root)}
    unit = units.get(address.get("study_unit_id"))
    if unit is None:
        raise ChapterStagedGenerationError("anchor study unit is absent from the canonical TN index")
    registry = _read_object(root / "research/mcc/objectives_registry.json")
    objectives = [
        row for row in registry.get("objectives", [])
        if isinstance(row, dict) and row.get("mcc_id") == primary_mcc_objective
    ]
    if len(objectives) != 1 or objectives[0].get("verification_status") != "OFFICIAL_CONFIRMED":
        raise ChapterStagedGenerationError("primary MCC objective is not official and unique")
    objective = objectives[0]
    return {
        "anchor_chapter_id": unit["chapter_id"],
        "anchor_chapter_title": unit["chapter_title"],
        "anchor_topic": unit["title"],
        "anchor_allocation_address_id": address["allocation_address_id"],
        "anchor_study_unit_id": unit["study_unit_id"],
        "anchor_source_node_ids": unit["source_node_ids"],
        "anchor_tn_pages": unit["tn_pages"],
        "anchor_pdf_pages": unit["pdf_pages"],
        "primary_mcc_objective": {"mcc_id": objective["mcc_id"], "title": objective["title"]},
        "primary_physician_activity": primary_physician_activity,
        "primary_competency": {
            "depth": address["depth"],
            "preferred_item_forms": address["preferred_item_forms"],
        },
        "primary_learner_decision": primary_learner_decision,
    }


def _validate_evidence_packet(evidence_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (
        not isinstance(evidence_packet, dict)
        or evidence_packet.get("scope") != "CHAPTER_REVIEW_MICRO_TARGETED_EVIDENCE"
    ):
        raise ChapterStagedGenerationError("targeted evidence packet identity is invalid")
    sources = evidence_packet.get("sources")
    claims = evidence_packet.get("claims")
    if not isinstance(sources, list) or not sources or not isinstance(claims, list) or not claims:
        raise ChapterStagedGenerationError("targeted evidence packet is incomplete")
    source_ids = []
    source_hashes: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, dict):
            raise ChapterStagedGenerationError("targeted evidence source is invalid")
        source_id = _nonempty(source.get("source_id"), "evidence source ID")
        source_ids.append(source_id)
        for field in ("title", "issuing_organization", "url", "retrieval_date", "currentness_status"):
            _nonempty(source.get(field), f"evidence source {field}")
        expected_source_hash = canonical_sha256(
            {key: value for key, value in source.items() if key != "sha256"}
        )
        if source.get("sha256") != expected_source_hash:
            raise ChapterStagedGenerationError("targeted evidence source fingerprint is invalid")
        source_hashes[source_id] = expected_source_hash
    if len(set(source_ids)) != len(source_ids):
        raise ChapterStagedGenerationError("targeted evidence source IDs are duplicated")
    by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, dict):
            raise ChapterStagedGenerationError("targeted evidence claim is invalid")
        claim_id = _nonempty(claim.get("claim_id"), "evidence claim ID")
        if claim_id in by_id:
            raise ChapterStagedGenerationError("targeted evidence claim IDs are duplicated")
        for field in ("statement", "exact_reason"):
            _nonempty(claim.get(field), f"evidence claim {field}")
        if claim.get("verification_status") != "VERIFIED_COMPLETE":
            raise ChapterStagedGenerationError("targeted evidence claim is not verified complete")
        refs = claim.get("source_refs")
        if not isinstance(refs, list) or not refs:
            raise ChapterStagedGenerationError("targeted evidence claim lacks source references")
        for ref in refs:
            if not isinstance(ref, dict) or ref.get("source_id") not in source_ids:
                raise ChapterStagedGenerationError("targeted evidence claim source reference is invalid")
            if ref.get("source_sha256") != source_hashes[ref["source_id"]]:
                raise ChapterStagedGenerationError("targeted evidence claim source fingerprint is invalid")
            _nonempty(ref.get("locator"), "targeted evidence locator")
        expected = canonical_sha256({key: value for key, value in claim.items() if key != "sha256"})
        if claim.get("sha256") != expected:
            raise ChapterStagedGenerationError("targeted evidence claim fingerprint is invalid")
        by_id[claim_id] = claim
    return by_id


def validate_contrast_library(
    root: Path,
    artifact: dict[str, Any],
    evidence_packet: dict[str, Any],
) -> dict[str, Any]:
    """Validate reusable directional edges against canonical TN and exact evidence bytes."""
    root = Path(root).resolve()
    claims = _validate_evidence_packet(evidence_packet)
    if (
        not isinstance(artifact, dict)
        or artifact.get("scope") != "CHAPTER_GLOBAL_CONTRAST_LIBRARY"
        or artifact.get("retrieval_policy") != "HYBRID_CACHE_FIRST_SEMANTIC_SECOND_EVIDENCE_THIRD"
    ):
        raise ChapterStagedGenerationError("global contrast library identity is invalid")
    edges = artifact.get("edges")
    if not isinstance(edges, list) or not edges:
        raise ChapterStagedGenerationError("global contrast library has no edges")
    units = {row["study_unit_id"]: row for row in build_global_study_unit_index(root)}
    edge_ids: list[str] = []
    for edge in edges:
        if not isinstance(edge, dict):
            raise ChapterStagedGenerationError("global contrast edge is invalid")
        edge_ids.append(_nonempty(edge.get("contrast_id"), "contrast ID"))
        anchor_concept_id = _nonempty(edge.get("anchor_concept_id"), "anchor concept ID")
        contrast_concept_id = _nonempty(edge.get("contrast_concept_id"), "contrast concept ID")
        if anchor_concept_id == contrast_concept_id:
            raise ChapterStagedGenerationError("contrast edge must join distinct concepts")
        if edge.get("quality_status") != "VALIDATED":
            raise ChapterStagedGenerationError("global contrast edge is not validated")
        for field in ("decision_context", "plausible_error", "neighboring_choice", "decisive_discriminant", "reviewer_id"):
            _nonempty(edge.get(field), f"contrast edge {field}")
        _nonempty_strings(edge.get("applicable_learner_decisions"), "contrast learner decisions")
        _nonempty_strings(edge.get("shared_features"), "clinical confusability shared features")
        _nonempty_strings(edge.get("excluded_contexts"), "contrast excluded contexts")
        if not isinstance(edge.get("anchor"), dict) or not isinstance(edge.get("contrast"), dict):
            raise ChapterStagedGenerationError("contrast edge provenance is invalid")
        anchor = units.get(edge["anchor"].get("study_unit_id"))
        contrast = units.get(edge["contrast"].get("study_unit_id"))
        if anchor is None or contrast is None:
            raise ChapterStagedGenerationError("contrast edge does not join canonical study units")
        if edge["anchor"] != _canonical_provenance(anchor) or edge["contrast"] != _canonical_provenance(contrast):
            raise ChapterStagedGenerationError("contrast edge Toronto Notes provenance is invalid")
        refs = edge.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            raise ChapterStagedGenerationError("contrast edge lacks authoritative evidence")
        for ref in refs:
            claim = claims.get(ref.get("claim_id")) if isinstance(ref, dict) else None
            if claim is None or ref.get("claim_sha256") != claim["sha256"]:
                raise ChapterStagedGenerationError("contrast edge evidence fingerprint is stale or invalid")
        expected = canonical_sha256({key: value for key, value in edge.items() if key != "content_sha256"})
        if edge.get("content_sha256") != expected:
            raise ChapterStagedGenerationError("contrast edge content fingerprint is invalid")
    if len(set(edge_ids)) != len(edge_ids):
        raise ChapterStagedGenerationError("contrast IDs are duplicated")
    return artifact


def retrieve_global_contrasts(
    root: Path,
    anchor_study_unit_id: str,
    decision_context: str,
    semantic_candidate_ids: list[str],
    library: dict[str, Any],
    evidence_packet: dict[str, Any],
) -> dict[str, Any]:
    """Return cached validated edges before bounded semantic candidates."""
    validate_contrast_library(root, library, evidence_packet)
    units = {row["study_unit_id"]: row for row in build_global_study_unit_index(root)}
    if anchor_study_unit_id not in units:
        raise ChapterStagedGenerationError("global retrieval anchor is not canonical")
    candidates = _nonempty_strings(semantic_candidate_ids, "semantic candidate IDs")
    if any(identifier not in units or identifier == anchor_study_unit_id for identifier in candidates):
        raise ChapterStagedGenerationError("semantic candidate is not a distinct canonical study unit")
    cached = sorted([
        edge for edge in library["edges"]
        if edge["anchor"]["study_unit_id"] == anchor_study_unit_id
        and edge["decision_context"] == decision_context
        and edge["quality_status"] == "VALIDATED"
    ], key=lambda edge: edge["contrast_id"])
    cached_units = {edge["contrast"]["study_unit_id"] for edge in cached}
    return {
        "strategy": "HYBRID_CACHE_FIRST_SEMANTIC_SECOND_EVIDENCE_THIRD",
        "cached_validated_edges": cached,
        "semantic_candidates_after_cache": [
            units[identifier] for identifier in candidates if identifier not in cached_units
        ],
    }


def _evidence_refs_exist(refs: Any, claims: dict[str, dict[str, Any]], label: str) -> list[str]:
    values = _nonempty_strings(refs, label)
    if any(value not in claims for value in values):
        raise ChapterStagedGenerationError(f"{label} contains an unsupported claim")
    return values


def _semantic_fingerprint(item: dict[str, Any]) -> str:
    assembly = item["assembly"]
    key = next(option for option in assembly["options"] if option.get("role") == "KEY")
    return canonical_sha256({
        "item_type": item["item_type"],
        "decision": item["anchor"]["primary_learner_decision"],
        "stem": assembly["stem"],
        "lead_in": assembly["lead_in"],
        "answer": key["text"],
    })


def _validate_option_realization(
    item: dict[str, Any],
    open_ended: dict[str, Any],
    key_row: dict[str, Any],
    distractors: list[dict[str, Any]],
    adversarial: dict[str, Any],
    claims: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    realization = item.get("option_realization")
    if (
        not isinstance(realization, dict)
        or realization.get("adversarial_review_sha256") != canonical_sha256(adversarial)
        or realization.get("policy") != "SEMANTIC_TO_CONCISE_NATURAL_PARALLEL_SURFACE"
    ):
        raise ChapterStagedGenerationError("option realization identity or lineage is invalid")
    realized = realization.get("options")
    if not isinstance(realized, list) or len(realized) != len(distractors) + 1:
        raise ChapterStagedGenerationError("option realization coverage is invalid")
    positions = [row.get("position") for row in realized if isinstance(row, dict)]
    if positions != list("ABCDE")[:len(realized)] or len(positions) != len(realized):
        raise ChapterStagedGenerationError("option realization positions are invalid")
    key_options = [row for row in realized if row.get("role") == "KEY"]
    realized_distractors = [row for row in realized if row.get("role") == "DISTRACTOR"]
    if len(key_options) != 1 or len(realized_distractors) != len(distractors):
        raise ChapterStagedGenerationError("option realization roles are invalid")
    dimensions = {row.get("option_dimension") for row in realized}
    if len(dimensions) != 1 or any(not isinstance(value, str) or not value for value in dimensions):
        raise ChapterStagedGenerationError("option realization option dimension is not homogeneous")
    grammatical_forms = {row.get("grammatical_form") for row in realized}
    if len(grammatical_forms) != 1 or any(
        not isinstance(value, str) or not value for value in grammatical_forms
    ):
        raise ChapterStagedGenerationError("option realization grammatical form is not parallel")

    key = key_options[0]
    if (
        key.get("semantic_option_text") != open_ended["intended_answer"]
        or key.get("meaning_preservation") != "PASS"
        or _evidence_refs_exist(key.get("evidence_refs"), claims, "realized key evidence")
        != key_row.get("anchor_evidence_refs")
    ):
        raise ChapterStagedGenerationError("realized key drifted from approved semantics")
    _nonempty(key.get("surface_text"), "realized key surface text")
    if key.get("contrast_id") is not None:
        raise ChapterStagedGenerationError("realized key cannot have a contrast ID")

    semantic_by_id = {row["contrast_id"]: row for row in distractors}
    realized_ids = [row.get("contrast_id") for row in realized_distractors]
    if set(realized_ids) != set(semantic_by_id) or len(realized_ids) != len(set(realized_ids)):
        raise ChapterStagedGenerationError("realized distractor contrast coverage is invalid")
    for row in realized_distractors:
        semantic = semantic_by_id[row["contrast_id"]]
        if (
            row.get("semantic_option_text") != semantic["option_text"]
            or row.get("meaning_preservation") != "PASS"
            or _evidence_refs_exist(
                row.get("evidence_refs"), claims, "realized distractor evidence"
            ) != semantic["evidence_refs"]
        ):
            raise ChapterStagedGenerationError("realized distractor drifted from approved semantics")
        _nonempty(row.get("surface_text"), "realized distractor surface text")

    review = item.get("parallel_option_set_review")
    if not isinstance(review, dict) or review.get("realization_sha256") != canonical_sha256(realization):
        raise ChapterStagedGenerationError("parallel option-set review lineage is invalid")
    deterministic_options = [
        {
            "role": row["role"],
            "text": row["surface_text"],
            "grammatical_form": row["grammatical_form"],
        }
        for row in realized
    ]
    findings = find_option_text_cues(open_ended["stem"], deterministic_options)
    if review.get("deterministic_findings") != findings or findings:
        raise ChapterStagedGenerationError("parallel option-set deterministic cue review failed")
    _pass_map(review.get("semantic_checks"), SEMANTIC_CUE_CHECKS, "semantic cue review")
    if review.get("option_only_key_identifiable") is not False or review.get("verdict") != "PASS":
        raise ChapterStagedGenerationError("semantic cue review must pass without option-only key identification")
    return realization, review, realized


def validate_staged_item(
    root: Path,
    item: dict[str, Any],
    library: dict[str, Any],
    evidence_packet: dict[str, Any],
) -> dict[str, Any]:
    """Validate the complete staged sequence without making semantic medical judgments."""
    root = Path(root).resolve()
    claims = _validate_evidence_packet(evidence_packet)
    validate_contrast_library(root, library, evidence_packet)
    if not isinstance(item, dict) or item.get("learning_mode") != "CHAPTER_REVIEW":
        raise ChapterStagedGenerationError("staged item identity is invalid")
    _nonempty(item.get("item_id"), "staged item ID")
    _nonempty(item.get("item_type"), "staged item type")
    author_id = _nonempty(item.get("author_id"), "staged item author")
    schema_version = item.get("schema_version")
    if schema_version not in {"1.0", "1.1"}:
        raise ChapterStagedGenerationError("staged item schema version is invalid")
    staged_sequence = STAGE_SEQUENCE_V2 if schema_version == "1.1" else STAGE_SEQUENCE
    if item.get("stage_sequence") != staged_sequence:
        raise ChapterStagedGenerationError("staged item sequence is invalid")

    anchor = item.get("anchor")
    if not isinstance(anchor, dict) or not isinstance(anchor.get("primary_mcc_objective"), dict):
        raise ChapterStagedGenerationError("staged item anchor is invalid")
    expected_anchor = resolve_chapter_anchor(
        root,
        anchor.get("anchor_allocation_address_id"),
        anchor["primary_mcc_objective"].get("mcc_id"),
        anchor.get("primary_physician_activity"),
        anchor.get("primary_learner_decision"),
    )
    if anchor != expected_anchor:
        raise ChapterStagedGenerationError("staged item anchor does not match canonical ownership")

    anchor_review = item.get("anchor_fidelity_preflight")
    if not isinstance(anchor_review, dict) or anchor_review.get("anchor_sha256") != canonical_sha256(anchor):
        raise ChapterStagedGenerationError("anchor-fidelity fingerprint is invalid")
    _pass_map(anchor_review.get("criteria"), ANCHOR_CRITERIA, "anchor-fidelity criteria")
    if anchor_review.get("verdict") != "PASS":
        raise ChapterStagedGenerationError("ANCHOR_FIDELITY must pass")

    open_ended = item.get("open_ended_stem_key")
    if not isinstance(open_ended, dict) or open_ended.get("anchor_fidelity_sha256") != canonical_sha256(anchor_review):
        raise ChapterStagedGenerationError("open-ended stage fingerprint is invalid")
    for field in ("context", "stem", "lead_in", "intended_answer"):
        _nonempty(open_ended.get(field), f"open-ended {field}")
    _nonempty_strings(open_ended.get("reasoning_chain"), "open-ended reasoning chain", minimum=2)
    _evidence_refs_exist(open_ended.get("key_evidence_refs"), claims, "open-ended key evidence")
    necessity = open_ended.get("context_necessity")
    if (
        not isinstance(necessity, dict)
        or necessity.get("answerable_after_context_ablation") is not False
        or not isinstance(necessity.get("context_type"), str)
        or not isinstance(necessity.get("explanation"), str)
    ):
        raise ChapterStagedGenerationError("context necessity is invalid")

    blind = item.get("blind_solver")
    hidden = {"intended_answer", "contrast_candidates", "answer_options", "author_self_evaluation"}
    if not isinstance(blind, dict) or blind.get("open_ended_sha256") != canonical_sha256(open_ended):
        raise ChapterStagedGenerationError("blind solver stage fingerprint is invalid")
    if set(blind.get("hidden_context", [])) != hidden:
        raise ChapterStagedGenerationError("blind solver hidden context is incomplete")
    if (
        blind.get("verdict") != "PASS"
        or " ".join(str(blind.get("independent_answer", "")).lower().split())
        != " ".join(open_ended["intended_answer"].lower().split())
    ):
        raise ChapterStagedGenerationError("blind cover-the-options solver did not independently reach the key")
    _nonempty(blind.get("independent_reasoning"), "blind solver reasoning")

    retrieval = item.get("global_contrast_retrieval")
    if not isinstance(retrieval, dict) or retrieval.get("blind_solver_sha256") != canonical_sha256(blind):
        raise ChapterStagedGenerationError("global contrast retrieval fingerprint is invalid")
    if (
        retrieval.get("strategy") != "HYBRID_CACHE_FIRST_SEMANTIC_SECOND_EVIDENCE_THIRD"
        or retrieval.get("complete_tn_corpus") is not True
        or retrieval.get("learner_progress_used") is not False
        or retrieval.get("lexical_similarity_only") is not False
    ):
        raise ChapterStagedGenerationError("global contrast retrieval cannot use lexical similarity alone")
    selected_ids = _nonempty_strings(retrieval.get("selected_contrast_ids"), "selected contrast IDs", minimum=3)
    if retrieval.get("cache_hits_first") != selected_ids:
        raise ChapterStagedGenerationError("global contrast retrieval did not use validated cache edges first")

    edges = {edge["contrast_id"]: edge for edge in library["edges"]}
    if any(
        identifier not in edges
        or edges[identifier]["anchor"]["study_unit_id"] != anchor["anchor_study_unit_id"]
        or edges[identifier]["quality_status"] != "VALIDATED"
        for identifier in selected_ids
    ):
        raise ChapterStagedGenerationError("global retrieval selected an unvalidated contrast")

    matrix = item.get("contrastive_evidence_matrix")
    if not isinstance(matrix, dict) or matrix.get("retrieval_sha256") != canonical_sha256(retrieval):
        raise ChapterStagedGenerationError("contrastive evidence matrix fingerprint is invalid")
    competitors = matrix.get("competitors")
    if not isinstance(competitors, list) or len(competitors) < 3:
        raise ChapterStagedGenerationError("contrastive matrix requires at least three validated competitors")
    competitor_ids = [row.get("contrast_id") for row in competitors if isinstance(row, dict)]
    if competitor_ids != selected_ids or len(competitor_ids) != len(competitors):
        raise ChapterStagedGenerationError("contrastive matrix does not match retrieved contrasts")
    key_row = matrix.get("key")
    if not isinstance(key_row, dict) or key_row.get("tn_alignment") not in {"CURRENT", "INCOMPLETE", "OUTDATED_CONFLICT"}:
        raise ChapterStagedGenerationError("contrastive matrix key is invalid")
    _nonempty(key_row.get("concept"), "matrix key concept")
    _nonempty_strings(key_row.get("decisive_discriminants"), "matrix key decisive discriminants")
    _evidence_refs_exist(key_row.get("anchor_evidence_refs"), claims, "matrix key evidence")
    for row in competitors:
        edge = edges[row["contrast_id"]]
        if row.get("status") != "VALIDATED" or row.get("ambiguity_verdict") != "KEY_REMAINS_SINGLE_BEST" or row.get("target_drift") != "ABSENT":
            raise ChapterStagedGenerationError("contrastive matrix competitor did not pass hard gates")
        if row.get("tn_provenance") != edge["contrast"]:
            raise ChapterStagedGenerationError("contrastive matrix competitor provenance is invalid")
        for field in ("contrast_concept", "why_plausible", "partial_mistaken_reasoning", "decisive_discriminant"):
            _nonempty(row.get(field), f"matrix competitor {field}")
        _nonempty_strings(row.get("shared_features"), "matrix competitor shared features")
        refs = _evidence_refs_exist(row.get("authoritative_evidence_refs"), claims, "matrix competitor evidence")
        if set(refs) != {ref["claim_id"] for ref in edge["evidence_refs"]}:
            raise ChapterStagedGenerationError("matrix competitor evidence does not instantiate its validated contrast")
    if matrix.get("verdict") != "PASS":
        raise ChapterStagedGenerationError("contrastive evidence matrix must pass")

    construction = item.get("distractor_construction")
    if not isinstance(construction, dict) or construction.get("matrix_sha256") != canonical_sha256(matrix):
        raise ChapterStagedGenerationError("separate distractor construction fingerprint is invalid")
    distractors = construction.get("distractors")
    if not isinstance(distractors, list) or len(distractors) != len(competitors):
        raise ChapterStagedGenerationError("separate distractor construction is incomplete")
    if len(distractors) not in {3, 4}:
        raise ChapterStagedGenerationError("distractor construction must contain three or four strong distractors")
    for distractor, row in zip(distractors, competitors, strict=True):
        if not isinstance(distractor, dict) or distractor.get("contrast_id") != row["contrast_id"]:
            raise ChapterStagedGenerationError("every distractor must instantiate a validated contrast")
        expected_fields = {
            "competing_concept": "contrast_concept",
            "why_temporarily_plausible": "why_plausible",
            "shared_features": "shared_features",
            "disqualifying_discriminant": "decisive_discriminant",
            "evidence_refs": "authoritative_evidence_refs",
        }
        if any(distractor.get(actual) != row.get(expected) for actual, expected in expected_fields.items()):
            raise ChapterStagedGenerationError("distractor construction drifted from its validated contrast")
        _nonempty(distractor.get("option_text"), "distractor option text")

    adversarial = item.get("distractor_adversarial_review")
    if not isinstance(adversarial, dict) or adversarial.get("construction_sha256") != canonical_sha256(construction):
        raise ChapterStagedGenerationError("distractor adversarial review fingerprint is invalid")
    review_rows = adversarial.get("rows")
    if not isinstance(review_rows, list) or [row.get("contrast_id") for row in review_rows if isinstance(row, dict)] != competitor_ids:
        raise ChapterStagedGenerationError("distractor adversarial review coverage is invalid")
    for row in review_rows:
        _pass_map(row.get("assessments"), DISTRACTOR_ASSESSMENTS, "distractor adversarial review")
        if row.get("verdict") != "PASS":
            raise ChapterStagedGenerationError("distractor adversarial review must pass")
    if adversarial.get("verdict") != "PASS":
        raise ChapterStagedGenerationError("distractor adversarial review must pass")

    realization = None
    parallel_review = None
    realized_options = None
    if schema_version == "1.1":
        realization, parallel_review, realized_options = _validate_option_realization(
            item,
            open_ended,
            key_row,
            distractors,
            adversarial,
            claims,
        )

    assembly = item.get("assembly")
    if not isinstance(assembly, dict):
        raise ChapterStagedGenerationError("MCQ assembly fingerprint is invalid")
    if schema_version == "1.1":
        if assembly.get("parallel_option_set_review_sha256") != canonical_sha256(parallel_review):
            raise ChapterStagedGenerationError("MCQ assembly option-review fingerprint is invalid")
    elif assembly.get("adversarial_review_sha256") != canonical_sha256(adversarial):
        raise ChapterStagedGenerationError("MCQ assembly fingerprint is invalid")
    if assembly.get("stem") != open_ended["stem"] or assembly.get("lead_in") != open_ended["lead_in"]:
        raise ChapterStagedGenerationError("MCQ assembly did not preserve the approved stem")
    expected_rewrite_status = (
        "SURFACE_REALIZATION_ONLY" if schema_version == "1.1" else "COMPONENTS_UNCHANGED"
    )
    if assembly.get("rewrite_status") != expected_rewrite_status:
        raise ChapterStagedGenerationError("MCQ assembly substantially rewrote approved components")
    component_hashes = assembly.get("approved_component_sha256")
    expected_component_hashes = (
        {
            "open_ended": canonical_sha256(open_ended),
            "option_realization": canonical_sha256(realization),
            "parallel_option_set_review": canonical_sha256(parallel_review),
        }
        if schema_version == "1.1"
        else {
            "open_ended": canonical_sha256(open_ended),
            "key": canonical_sha256(key_row),
            "distractors": canonical_sha256(distractors),
        }
    )
    if component_hashes != expected_component_hashes:
        raise ChapterStagedGenerationError("MCQ assembly approved-component fingerprints are invalid")
    options = assembly.get("options")
    if not isinstance(options, list) or len(options) != len(distractors) + 1 or len(options) not in {4, 5}:
        raise ChapterStagedGenerationError("MCQ assembly option count is invalid")
    keys = [option.get("key") for option in options if isinstance(option, dict)]
    if keys != list("ABCDE")[:len(options)] or len(keys) != len(options):
        raise ChapterStagedGenerationError("MCQ assembly option keys are invalid")
    key_options = [option for option in options if option.get("role") == "KEY"]
    expected_key_text = (
        next(row["surface_text"] for row in realized_options if row["role"] == "KEY")
        if schema_version == "1.1"
        else open_ended["intended_answer"]
    )
    if len(key_options) != 1 or assembly.get("correct_answer") != key_options[0]["key"] or key_options[0].get("text") != expected_key_text:
        raise ChapterStagedGenerationError("MCQ assembly key does not match the approved open-ended answer")
    actual_distractors = [option for option in options if option.get("role") == "DISTRACTOR"]
    if schema_version == "1.1":
        expected_assembly_options = [
            {
                "key": row["position"],
                "text": row["surface_text"],
                "role": row["role"],
                **({"contrast_id": row["contrast_id"]} if row["role"] == "DISTRACTOR" else {}),
            }
            for row in realized_options
        ]
        if options != expected_assembly_options:
            raise ChapterStagedGenerationError("MCQ assembly options do not match reviewed realization")
    elif [option.get("contrast_id") for option in actual_distractors] != competitor_ids or [option.get("text") for option in actual_distractors] != [row["option_text"] for row in distractors]:
        raise ChapterStagedGenerationError("MCQ assembly distractors do not match validated constructions")
    option_text_cues = find_option_text_cues(
        open_ended["stem"],
        [
            {
                **option,
                "grammatical_form": (
                    next(
                        row["grammatical_form"]
                        for row in realized_options
                        if row["position"] == option["key"]
                    )
                    if schema_version == "1.1"
                    else "LEGACY_UNSTRUCTURED"
                ),
            }
            for option in options
        ],
    )
    if option_text_cues:
        raise ChapterStagedGenerationError(
            f"MCQ assembly has deterministic option-shape cue: {', '.join(option_text_cues)}"
        )

    acceptance = item.get("acceptance_review")
    if not isinstance(acceptance, dict) or acceptance.get("assembly_sha256") != canonical_sha256(assembly):
        raise ChapterStagedGenerationError("post-assembly acceptance fingerprint is invalid")
    _pass_map(acceptance.get("checks"), ACCEPTANCE_CHECKS, "post-assembly acceptance checks")
    if acceptance.get("verdict") != "PASS":
        raise ChapterStagedGenerationError("post-assembly item acceptance must pass")

    rationales = item.get("rationales")
    if not isinstance(rationales, dict) or rationales.get("acceptance_sha256") != canonical_sha256(acceptance):
        raise ChapterStagedGenerationError("rationales were not generated after item acceptance")
    if rationales.get("unsupported_new_teaching_facts") is not False:
        raise ChapterStagedGenerationError("rationales contain unsupported teaching facts")
    correct = rationales.get("correct")
    if not isinstance(correct, dict):
        raise ChapterStagedGenerationError("correct-answer rationale is invalid")
    for field in ("why_best", "anchor_tn_topic_pages"):
        _nonempty(correct.get(field), f"correct rationale {field}")
    correct_refs = _evidence_refs_exist(correct.get("evidence_refs"), claims, "correct rationale evidence")
    if (
        correct_refs != key_row.get("anchor_evidence_refs")
        or correct.get("why_best") != open_ended["reasoning_chain"][-1]
        or correct.get("decisive_evidence") != key_row.get("decisive_discriminants")
        or correct.get("decisive_discriminants") != key_row.get("decisive_discriminants")
    ):
        raise ChapterStagedGenerationError("correct rationale lineage drifted from the approved key matrix")
    rationale_rows = rationales.get("distractors")
    if not isinstance(rationale_rows, list) or [row.get("contrast_id") for row in rationale_rows if isinstance(row, dict)] != competitor_ids:
        raise ChapterStagedGenerationError("distractor rationales are incomplete")
    for row, distractor in zip(rationale_rows, distractors, strict=True):
        for field in ("why_plausible", "exact_discriminator"):
            _nonempty(row.get(field), f"distractor rationale {field}")
        rationale_refs = _evidence_refs_exist(row.get("evidence_refs"), claims, "distractor rationale evidence")
        if (
            row.get("why_plausible") != distractor.get("why_temporarily_plausible")
            or row.get("exact_discriminator") != distractor.get("disqualifying_discriminant")
            or rationale_refs != distractor.get("evidence_refs")
        ):
            raise ChapterStagedGenerationError("distractor rationale lineage drifted from approved construction")

    actors = [
        author_id,
        anchor_review.get("reviewer_id"),
        blind.get("solver_id"),
        retrieval.get("semantic_ranker_id"),
        construction.get("constructor_id"),
        adversarial.get("reviewer_id"),
        *( [realization.get("realizer_id"), parallel_review.get("reviewer_id")] if schema_version == "1.1" else [] ),
        assembly.get("assembler_id"),
        acceptance.get("reviewer_id"),
    ]
    if any(not isinstance(actor, str) or not actor for actor in actors) or len(set(actors)) != len(actors):
        raise ChapterStagedGenerationError("fresh staged reviewers and solvers are required")
    if item.get("semantic_fingerprint") != _semantic_fingerprint(item):
        raise ChapterStagedGenerationError("staged item semantic fingerprint is invalid")
    return item


def validate_micro_pilot(
    root: Path,
    artifact: dict[str, Any],
    library: dict[str, Any],
    evidence_packet: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    """Enforce the exact 3/3 clinical micro-pilot success gate."""
    if not isinstance(artifact, dict) or artifact.get("scope") != "CHAPTER_REVIEW_CLINICAL_MICRO_3":
        raise ChapterStagedGenerationError("clinical micro-pilot identity is invalid")
    candidate_status = artifact.get("candidate_status")
    if (
        candidate_status not in {None, "ACCEPTED"}
        or artifact.get("provisional_parallel_option_review") not in {None, False}
    ):
        raise ChapterStagedGenerationError("rejected or provisional micro-pilot cannot pass the success gate")
    items = artifact.get("items")
    if not isinstance(items, list) or len(items) != 3:
        raise ChapterStagedGenerationError("clinical micro-pilot must contain exactly three items")
    expected_types = {
        "DIAGNOSIS_DIFFERENTIAL",
        "INVESTIGATION_INTERPRETATION",
        "MANAGEMENT_NEXT_BEST_STEP",
    }
    if {item.get("item_type") for item in items if isinstance(item, dict)} != expected_types:
        raise ChapterStagedGenerationError("clinical micro-pilot item-type mix is invalid")
    validated = [validate_staged_item(root, item, library, evidence_packet) for item in items]
    item_ids = [item["item_id"] for item in validated]
    if len(set(item_ids)) != 3:
        raise ChapterStagedGenerationError("clinical micro-pilot item IDs are duplicated")
    if any(
        item["anchor"]["anchor_chapter_id"] != artifact.get("anchor_chapter_id")
        or item["anchor"]["anchor_study_unit_id"] != artifact.get("anchor_study_unit_id")
        for item in validated
    ):
        raise ChapterStagedGenerationError("clinical micro-pilot chapter anchoring is inconsistent")
    semantic_fingerprints = [item["semantic_fingerprint"] for item in validated]
    if len(set(semantic_fingerprints)) != 3:
        raise ChapterStagedGenerationError("clinical micro-pilot contains material deterministic duplicates")
    position_cues = find_option_position_cues(validated)
    if position_cues:
        raise ChapterStagedGenerationError(
            f"clinical micro-pilot has deterministic option-position cue: {', '.join(position_cues)}"
        )

    if (
        not isinstance(verification, dict)
        or verification.get("scope") != "CHAPTER_REVIEW_MICRO_INDEPENDENT_VERIFICATION"
        or verification.get("staged_artifact_sha256") != canonical_sha256(artifact)
        or verification.get("evidence_traceability") != "PASS"
        or verification.get("independent_context") != "PASS"
    ):
        raise ChapterStagedGenerationError("independent verification identity or lineage is invalid")
    verdicts = verification.get("verdicts")
    if not isinstance(verdicts, list) or [row.get("item_id") for row in verdicts if isinstance(row, dict)] != item_ids:
        raise ChapterStagedGenerationError("independent verification does not cover exact micro items")
    verifier_id = _nonempty(verification.get("verifier_id"), "fresh independent verifier")
    prior_actors = {
        actor
        for item in validated
        for actor in (
            item["author_id"],
            item["anchor_fidelity_preflight"]["reviewer_id"],
            item["blind_solver"]["solver_id"],
            item["global_contrast_retrieval"]["semantic_ranker_id"],
            item["distractor_construction"]["constructor_id"],
            item["distractor_adversarial_review"]["reviewer_id"],
            item.get("option_realization", {}).get("realizer_id"),
            item.get("parallel_option_set_review", {}).get("reviewer_id"),
            item["assembly"]["assembler_id"],
            item["acceptance_review"]["reviewer_id"],
        )
        if actor
    }
    if verifier_id in prior_actors:
        raise ChapterStagedGenerationError("fresh independent verifier cannot share a prior generation role")
    defects = verification.get("defect_counts")
    all_pass = True
    for row in verdicts:
        if not isinstance(row, dict) or set(row.get("dimensions", {})) != VERIFICATION_DIMENSIONS:
            raise ChapterStagedGenerationError("independent verification dimensions are incomplete")
        row_pass = row.get("verdict") == "PASS" and all(value == "PASS" for value in row["dimensions"].values())
        if row_pass and row.get("root_cause") is not None:
            raise ChapterStagedGenerationError("passing independent verification cannot contain a root cause")
        if not row_pass and not isinstance(row.get("root_cause"), str):
            raise ChapterStagedGenerationError("failed independent verification requires root-cause attribution")
        all_pass = all_pass and row_pass
    if (
        not isinstance(defects, dict)
        or set(defects) != DEFECT_CATEGORIES
        or any(not isinstance(value, int) or value < 0 for value in defects.values())
        or any(defects.values())
        or not all_pass
        or verification.get("micro_pilot_assessment") != "SUCCESS"
    ):
        raise ChapterStagedGenerationError("micro success gate requires 3/3 PASS and zero defects")
    return {
        "micro_items_generated": 3,
        "micro_items_passed": 3,
        "defect_counts": defects,
        "evidence_traceability": "PASS",
        "independent_context": "PASS",
        "micro_pilot_assessment": "SUCCESS",
    }


def validate_micro_failure_review(
    root: Path,
    artifact: dict[str, Any],
    library: dict[str, Any],
    evidence_packet: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    """Validate a fail-closed adversarial review without promoting failed items."""
    root = Path(root).resolve()
    validate_contrast_library(root, library, evidence_packet)
    if not isinstance(artifact, dict) or artifact.get("scope") != "CHAPTER_REVIEW_CLINICAL_MICRO_3":
        raise ChapterStagedGenerationError("failed clinical micro-pilot identity is invalid")
    items = artifact.get("items")
    if not isinstance(items, list) or len(items) != 3:
        raise ChapterStagedGenerationError("failed clinical micro-pilot must contain exactly three items")
    item_ids = [item.get("item_id") for item in items if isinstance(item, dict)]
    if len(item_ids) != 3 or len(set(item_ids)) != 3:
        raise ChapterStagedGenerationError("failed clinical micro-pilot item coverage is invalid")
    if (
        not isinstance(review, dict)
        or review.get("scope") != "CHAPTER_REVIEW_MICRO_DISTRACTOR_ADVERSARIAL_REVIEW"
        or review.get("staged_artifact_sha256") != canonical_sha256(artifact)
        or review.get("contrast_library_sha256") != canonical_sha256(library)
        or review.get("evidence_packet_sha256") != canonical_sha256(evidence_packet)
    ):
        raise ChapterStagedGenerationError("failed micro review identity or byte lineage is invalid")
    excluded = review.get("excluded_context")
    if not isinstance(excluded, list) or not {"author deliberation", "author self-evaluation"}.issubset(excluded):
        raise ChapterStagedGenerationError("failed micro review independent context is invalid")
    reviewer_id = _nonempty(review.get("reviewer_id"), "failed micro reviewer")
    prior_actors = {
        actor
        for item in items
        for actor in (
            item.get("author_id"),
            item.get("anchor_fidelity_preflight", {}).get("reviewer_id"),
            item.get("blind_solver", {}).get("solver_id"),
            item.get("global_contrast_retrieval", {}).get("semantic_ranker_id"),
            item.get("distractor_construction", {}).get("constructor_id"),
            item.get("distractor_adversarial_review", {}).get("reviewer_id"),
            item.get("assembly", {}).get("assembler_id"),
            item.get("acceptance_review", {}).get("reviewer_id"),
        )
    }
    if reviewer_id in prior_actors:
        raise ChapterStagedGenerationError("failed micro review requires a fresh reviewer")

    expected_pairs = [
        (item["item_id"], row["contrast_id"])
        for item in items
        for row in item.get("distractor_construction", {}).get("distractors", [])
    ]
    distractor_results = review.get("distractor_results")
    actual_pairs = [
        (row.get("item_id"), row.get("contrast_id"))
        for row in distractor_results
        if isinstance(row, dict)
    ] if isinstance(distractor_results, list) else []
    if actual_pairs != expected_pairs or any(row.get("verdict") not in {"PASS", "FAIL"} for row in distractor_results):
        raise ChapterStagedGenerationError("failed micro review distractor coverage is invalid")

    item_results = review.get("item_results")
    if not isinstance(item_results, list) or [row.get("item_id") for row in item_results if isinstance(row, dict)] != item_ids:
        raise ChapterStagedGenerationError("failed micro review item coverage is invalid")
    passed = 0
    item_cue_failures = 0
    items_by_id = {item["item_id"]: item for item in items}
    for row in item_results:
        failed_checks = row.get("failed_checks")
        if not isinstance(failed_checks, list):
            raise ChapterStagedGenerationError("failed micro review check list is invalid")
        if row.get("verdict") == "PASS":
            if failed_checks or row.get("root_cause") is not None:
                raise ChapterStagedGenerationError("passing micro item has contradictory failure detail")
            passed += 1
        elif row.get("verdict") == "FAIL":
            _nonempty(row.get("root_cause"), "failed micro root cause")
            if not failed_checks:
                raise ChapterStagedGenerationError("failed micro item lacks failed checks")
            deterministic_shape_cues = find_option_shape_cues(
                items_by_id[row["item_id"]].get("assembly", {}).get("options", [])
            )
            reports_shape_cue = bool(
                {"option_only_cues", "answer_length_specificity"}.intersection(failed_checks)
            )
            if reports_shape_cue != bool(deterministic_shape_cues):
                raise ChapterStagedGenerationError("failed micro option-shape attribution is invalid")
            if deterministic_shape_cues:
                item_cue_failures += 1
        else:
            raise ChapterStagedGenerationError("failed micro item verdict is invalid")

    defects = review.get("defect_counts")
    position_defects = 1 if find_option_position_cues(items) else 0
    weak_distractors = sum(row["verdict"] == "FAIL" for row in distractor_results)
    if (
        not isinstance(defects, dict)
        or set(defects) != DEFECT_CATEGORIES
        or any(not isinstance(value, int) or value < 0 for value in defects.values())
        or defects["OPTION_CUE_FAILURE"] != item_cue_failures + position_defects
        or defects["WEAK_DISTRACTOR"] != weak_distractors
        or review.get("micro_items_generated") != 3
        or review.get("micro_items_passed") != passed
        or passed == 3
        or review.get("micro_pilot_assessment") != "FAILURE"
        or review.get("next_step") != "DIAGNOSE_MICRO_FAILURE"
        or review.get("regeneration_attempted") is not False
    ):
        raise ChapterStagedGenerationError("failed micro review defect reconciliation is invalid")
    _nonempty(review.get("root_cause_attribution"), "failed micro root-cause attribution")
    return {
        "micro_items_generated": 3,
        "micro_items_passed": passed,
        "defect_counts": defects,
        "evidence_traceability": "PASS",
        "independent_context": "PASS",
        "micro_pilot_assessment": "FAILURE",
    }
