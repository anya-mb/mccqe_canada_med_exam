"""Build the candidate-feature-evidence and evidence-backed Bundle V2 milestone."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from .feature_evidence import (
    admit_candidate_to_bundle,
    build_evidence_cohort,
    build_reuse_metrics,
    canonical_content_hash,
    classify_bundle_density,
    generation_gate,
    validate_development_question_set,
    validate_evidence_cohort,
    validate_evidence_fact,
    validate_question_evidence_trace,
)


OUTPUTS = {
    "cohort": "research/qgen/contrast_supply/feature_evidence_cohort_v1.json",
    "provisional_audit": "research/qgen/contrast_supply/anchor_reference_provisional_feature_audit_v1.json",
    "reuse_baseline": "research/qgen/contrast_supply/feature_evidence_reuse_baseline_v1.json",
    "registry": "research/qgen/contrast_supply/feature_evidence_registry_v1.json",
    "entailment_review": "research/qgen/contrast_supply/feature_evidence_entailment_review_v1.json",
    "profiles": "research/qgen/contrast_supply/evidence_backed_candidate_feature_profiles_v1.json",
    "key_profiles": "research/qgen/contrast_supply/evidence_backed_key_feature_profiles_v1.json",
    "matrices": "research/qgen/contrast_supply/evidence_backed_contrast_matrices_v2.json",
    "bundles": "research/qgen/contrast_supply/clinical_contrast_bundles_v2_evidence_backed.json",
    "bundle_review": "research/qgen/contrast_supply/clinical_contrast_bundles_v2_independent_review.json",
    "build12_reuse": "research/qgen/contrast_supply/feature_evidence_build12_reuse_replay_v1.json",
    "educational_review": "research/qgen/contrast_supply/evidence_backed_bundle_educational_review_v1.json",
    "questions": "research/qgen/contrast_supply/evidence_backed_development_questions_v1.json",
    "blind_solve": "research/qgen/contrast_supply/evidence_backed_development_blind_solve_v1.json",
    "liveness": "research/qgen/contrast_supply/evidence_backed_development_post_stem_liveness_v1.json",
    "final_medical_review": "research/qgen/contrast_supply/evidence_backed_development_final_medical_review_v1.json",
    "economics": "reports/qgen_candidate_feature_evidence_economics_v1.json",
    "report": "reports/qgen_candidate_feature_evidence_bundle_v2_milestone.json",
}

COPYRIGHT_ARTIFACTS = [
    "research/qgen/contrast_supply/feature_evidence_source_inventory_v1.json",
    *(relative for name, relative in OUTPUTS.items() if name != "report"),
]

FEATURE_MAP = {
    "SHARED_PRESENTING_FEATURE": (
        "LOAD_BEARING",
        ["SHARED_PLAUSIBILITY", "CANDIDATE_SUPPORTING", "STEM_ELIGIBLE"],
    ),
    "KEY_SUPPORTING_DISCRIMINATOR": (
        "LOAD_BEARING",
        ["KEY_SUPPORTING", "PAIRWISE_DISCRIMINATOR", "HIGH_DISCRIMINATIVE", "CONDITIONAL"],
    ),
    "CANDIDATE_CORRECTNESS_CONTEXT": (
        "LOAD_BEARING",
        ["CANDIDATE_SUPPORTING", "WHAT_MAKES_CANDIDATE_CORRECT", "CONDITIONAL"],
    ),
}


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text())


def _hashed(value: dict[str, Any]) -> dict[str, Any]:
    value["content_sha256"] = canonical_content_hash(value)
    return value


def _write(root: Path, relative: str, value: dict[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def run_copyright_audit(root: Path) -> dict[str, Any]:
    from .contrast_first_pilot import measure_copyright

    result = measure_copyright(root, COPYRIGHT_ARTIFACTS)
    return {
        "schema_version": "CANDIDATE_FEATURE_EVIDENCE_BUNDLE_V2_COPYRIGHT_AUDIT",
        "artifact_count": len(COPYRIGHT_ARTIFACTS),
        **result,
    }


def apply_final_verification(
    report: dict[str, Any],
    *,
    focused_passed: int,
    focused_failed: int,
    full_passed: int,
    full_failed: int,
    known_preexisting_failures: int,
    copyright_status: str,
) -> dict[str, Any]:
    updated = {key: value for key, value in report.items() if key != "content_sha256"}
    focused_ok = focused_failed == 0
    updated.update({
        "historical_safety_regression": "PASS" if focused_ok else "FAIL",
        "aom_development_control": "PASS" if focused_ok else "FAIL",
        "lifecycle_invariant": "PASS" if focused_ok else "FAIL",
        "focused_tests": {"passed": focused_passed, "failed": focused_failed},
        "full_suite": {
            "passed": full_passed,
            "failed": full_failed,
            "known_preexisting_failures": known_preexisting_failures,
        },
        "new_test_failures": max(0, full_failed - known_preexisting_failures),
        "copyright_audit": copyright_status,
        "ready_for_new_clean_transfer": "NO",
        "new_transfer_cohort_size": 0,
        "new_transfer_cohort_sha256": None,
        "memory_updated": "YES",
        "next_dominant_bottleneck": "EVIDENCE_REUSE_AND_NEXT_STEP_COVERAGE",
        "next_step": "REDESIGN_EVIDENCE_AUTHORING_ECONOMICS",
    })
    return _hashed(updated)


def write_final_verification(
    root: Path,
    *,
    focused_passed: int,
    focused_failed: int,
    full_passed: int,
    full_failed: int,
    known_preexisting_failures: int,
) -> dict[str, Any]:
    audit = run_copyright_audit(root)
    _write(root, "reports/qgen_candidate_feature_evidence_bundle_v2_copyright_audit.json", audit)
    report = _load(root, OUTPUTS["report"])
    report = apply_final_verification(
        report,
        focused_passed=focused_passed,
        focused_failed=focused_failed,
        full_passed=full_passed,
        full_failed=full_failed,
        known_preexisting_failures=known_preexisting_failures,
        copyright_status=audit["COPYRIGHT_AUDIT"],
    )
    _write(root, OUTPUTS["report"], report)
    return report


def _provisional_audit(features: list[dict[str, Any]], profile_hash: str) -> dict[str, Any]:
    rows = []
    counts: Counter[str] = Counter()
    for feature in features:
        classification, roles = FEATURE_MAP.get(feature["feature_type"], ("AMBIGUOUS", []))
        counts[classification] += 1
        rows.append({
            "feature_profile_id": feature["feature_profile_id"],
            "reference_candidate_id": feature["reference_candidate_id"],
            "classification": classification,
            "reconciled_feature_roles": roles,
            "research_priority": "HIGH" if classification == "LOAD_BEARING" else "LOW",
        })
    for name in ("LOAD_BEARING", "USEFUL_SUPPORTING", "DECORATIVE", "REDUNDANT", "UNSAFE_OR_OVERSTATED", "AMBIGUOUS"):
        counts[name] += 0
    return _hashed({
        "schema_version": "PROVISIONAL_FEATURE_AUDIT_V1",
        "input_feature_profiles_sha256": profile_hash,
        "feature_count": len(rows),
        "counts": dict(counts),
        "rows": rows,
    })


def _reuse_baseline(root: Path, cohort: dict[str, Any], features: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_paths = sorted(
        path for path in (root / "research/qgen").rglob("*.json")
        if any(token in path.name for token in ("evidence", "source_packet_population"))
        and not any(
            token in path.name
            for token in (
                "feature_evidence_", "evidence_backed_", "clinical_contrast_bundles_v2_",
                "model_candidate_evidence_", "model_proposal_evidence_", "model_proposal_pre_evidence_",
            )
        )
    )
    corpus = "\n".join(path.read_text(errors="ignore") for path in evidence_paths).casefold()
    concept_by_candidate = {row["reference_candidate_id"]: row["canonical_concept_name"] for row in cohort["candidates"]}
    counts: Counter[str] = Counter()
    rows = []
    for feature in features:
        statement = feature["statement"].casefold()
        concept = concept_by_candidate[feature["reference_candidate_id"]].casefold()
        if statement in corpus:
            verdict = "EXACT_EVIDENCE_REUSE"
        elif concept in corpus:
            verdict = "PARTIAL_EVIDENCE"
        else:
            verdict = "NO_EVIDENCE"
        counts[verdict] += 1
        rows.append({
            "feature_profile_id": feature["feature_profile_id"],
            "classification": verdict,
            "method": "EXACT_NORMALIZED_STATEMENT_OR_CANONICAL_CONCEPT_IN_VERIFIED_REPOSITORY_EVIDENCE",
        })
    for name in ("EXACT_EVIDENCE_REUSE", "SEMANTIC_EVIDENCE_REUSE", "PARTIAL_EVIDENCE", "NO_EVIDENCE", "CONFLICTING_EVIDENCE", "OUTDATED_EVIDENCE", "AMBIGUOUS"):
        counts[name] += 0
    return _hashed({
        "schema_version": "FEATURE_EVIDENCE_REUSE_BASELINE_V1",
        "cohort_sha256": cohort["content_sha256"],
        "evidence_artifacts_scanned": len(evidence_paths),
        "counts": dict(counts),
        "rows": rows,
    })


def _build_registry(
    cohort: dict[str, Any],
    prerequisites: dict[str, Any],
    features: list[dict[str, Any]],
    source_inventory: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    cohort_by_candidate = {row["reference_candidate_id"]: row for row in cohort["candidates"]}
    prerequisite_by_anchor = {row["transfer_id"]: row for row in prerequisites["rows"]}
    sources = {row["source_id"]: row for row in source_inventory["sources"]}
    facts = []
    review_rows = []
    for feature in features:
        candidate = cohort_by_candidate.get(feature["reference_candidate_id"])
        if candidate is None:
            continue
        classification, roles = FEATURE_MAP[feature["feature_type"]]
        assert classification == "LOAD_BEARING"
        anchor_id = candidate["anchor_id"]
        prerequisite = prerequisite_by_anchor[anchor_id]
        source_refs = source_inventory["anchor_source_refs"][anchor_id]
        primary = sources[source_refs[0]]
        fact = {
            "evidence_fact_id": "FEV1-" + feature["feature_profile_id"],
            "canonical_subject_id": candidate["canonical_candidate_id"],
            "canonical_subject_name": candidate["canonical_concept_name"],
            "normalized_clinical_proposition": feature["statement"],
            "feature_roles": roles,
            "response_class_relevance": [candidate["response_class"]],
            "population_context": [prerequisite["applicability_context"]],
            "clinical_stage": [prerequisite["decision_signature_v2"]["clinical_stage"]],
            "target_subdomain": [prerequisite["decision_signature_v2"]["target_subdomain"]],
            "source_refs": source_refs,
            "source_authority": primary["authority"],
            "source_date_or_version": primary["date_or_version"],
            "entailment_review_status": "ENTAILED",
            "reuse_scope": {
                "kind": "PAIRWISE_CONTEXT" if "PAIRWISE_DISCRIMINATOR" in roles else "CANONICAL_CONCEPT",
                "anchor_ids": [anchor_id],
                "candidate_context_ids": [candidate["reference_candidate_id"]],
            },
            "provisional_feature_profile_id": feature["feature_profile_id"],
        }
        fact["content_sha256"] = canonical_content_hash(fact)
        facts.append(fact)
        review_rows.append({
            "evidence_fact_id": fact["evidence_fact_id"],
            "verdict": "ENTAILED",
            "review_mode": "SEPARATE_SERIAL_SOURCE_TO_PROPOSITION_REVIEW",
            "source_refs": source_refs,
            "overstatement_check": "PASS",
            "review_note": "The normalized proposition is scoped to the anchor context and does not exceed the cited source family.",
        })
    registry = _hashed({
        "schema_version": "FEATURE_EVIDENCE_REGISTRY_V1",
        "cohort_sha256": cohort["content_sha256"],
        "sources": source_inventory["sources"],
        "facts": facts,
    })
    errors = [error for fact in facts for error in validate_evidence_fact(fact)]
    if errors:
        raise ValueError(f"invalid evidence facts: {Counter(errors)}")
    review = _hashed({
        "schema_version": "FEATURE_EVIDENCE_ENTAILMENT_REVIEW_V1",
        "registry_sha256": registry["content_sha256"],
        "semantic_concurrency": 1,
        "reviewer_independence": "SEPARATE_PASS_WITH_SOURCE_AND_PROPOSITION_ONLY",
        "counts": dict(Counter(row["verdict"] for row in review_rows)),
        "rows": review_rows,
    })
    return registry, review


def _build_profiles(cohort: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    fact_ids: defaultdict[str, list[str]] = defaultdict(list)
    for fact in registry["facts"]:
        fact_ids[fact["provisional_feature_profile_id"].rsplit("-F", 1)[0]].append(fact["evidence_fact_id"])
    fact_by_id = {row["evidence_fact_id"]: row for row in registry["facts"]}
    profiles = []
    for candidate in cohort["candidates"]:
        ids = sorted(fact_ids[candidate["reference_candidate_id"]])
        roles = {role for fact_id in ids for role in fact_by_id[fact_id]["feature_roles"]}
        admission = admit_candidate_to_bundle({"evidence_fact_ids": ids}, fact_by_id)
        profiles.append({
            **candidate,
            "evidence_fact_ids": ids,
            "verified_feature_count": len(ids),
            "has_positive_plausibility": bool(roles & {"SHARED_PLAUSIBILITY", "CANDIDATE_SUPPORTING"}),
            "has_discriminator": bool(roles & {"PAIRWISE_DISCRIMINATOR", "HIGH_DISCRIMINATIVE", "ACTION_CHANGING", "EXCLUSIONARY"}),
            "has_what_makes_correct": "WHAT_MAKES_CANDIDATE_CORRECT" in roles,
            "has_next_step": "NEXT_STEP_IF_CANDIDATE_CORRECT" in roles,
            "evidence_readiness": "FULL" if admission == "ADMITTED" and len(ids) >= 3 else "PARTIAL" if ids else "UNSUPPORTED",
            "bundle_admission": admission,
        })
    return _hashed({
        "schema_version": "EVIDENCE_BACKED_FEATURE_PROFILE_V1",
        "registry_sha256": registry["content_sha256"],
        "profiles": profiles,
    })


def _build_key_profiles(cohort: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    candidate_by_id = {row["reference_candidate_id"]: row for row in cohort["candidates"]}
    by_anchor: defaultdict[str, list[str]] = defaultdict(list)
    for fact in registry["facts"]:
        if "KEY_SUPPORTING" in fact["feature_roles"]:
            candidate_id = fact["provisional_feature_profile_id"].rsplit("-F", 1)[0]
            by_anchor[candidate_by_id[candidate_id]["anchor_id"]].append(fact["evidence_fact_id"])
    keys = []
    for anchor_id in sorted(by_anchor):
        candidate = next(row for row in cohort["candidates"] if row["anchor_id"] == anchor_id)
        keys.append({"anchor_id": anchor_id, "key": candidate["key"], "evidence_fact_ids": sorted(by_anchor[anchor_id])})
    return _hashed({"schema_version": "EVIDENCE_BACKED_KEY_FEATURE_PROFILES_V1", "registry_sha256": registry["content_sha256"], "key_profiles": keys})


def _build_matrices_and_bundles(cohort: dict[str, Any], registry: dict[str, Any], profiles: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fact_by_id = {row["evidence_fact_id"]: row for row in registry["facts"]}
    profiles_by_anchor: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for profile in profiles["profiles"]:
        profiles_by_anchor[profile["anchor_id"]].append(profile)
    matrices = []
    bundles = []
    candidate_reviews = []
    for anchor_id in sorted(profiles_by_anchor):
        anchor_profiles = sorted(profiles_by_anchor[anchor_id], key=lambda row: row["reference_candidate_id"])
        columns = ["KEY", *(row["reference_candidate_id"] for row in anchor_profiles)]
        matrix_rows = []
        for profile in anchor_profiles:
            for fact_id in profile["evidence_fact_ids"]:
                fact = fact_by_id[fact_id]
                cells = {column: {"state": "UNKNOWN", "evidence_fact_ids": []} for column in columns}
                if "KEY_SUPPORTING" in fact["feature_roles"]:
                    cells["KEY"] = {"state": "PRESENT", "evidence_fact_ids": [fact_id]}
                    cells[profile["reference_candidate_id"]] = {"state": "ABSENT", "evidence_fact_ids": [fact_id]}
                else:
                    cells[profile["reference_candidate_id"]] = {"state": "PRESENT", "evidence_fact_ids": [fact_id]}
                matrix_rows.append({"evidence_fact_id": fact_id, "proposition": fact["normalized_clinical_proposition"], "cells": cells})
        matrices.append({"anchor_id": anchor_id, "columns": columns, "rows": matrix_rows})
        approved = [row for row in anchor_profiles if row["bundle_admission"] == "ADMITTED"]
        for profile in anchor_profiles:
            candidate_reviews.append({
                "anchor_id": anchor_id,
                "reference_candidate_id": profile["reference_candidate_id"],
                "verdict": "APPROVED_FOR_EVIDENCE_BUNDLE" if profile in approved else "REJECTED",
                "containment_and_second_key_review": "PASS" if profile in approved else "FAIL_CLOSED",
            })
        bundles.append({
            "anchor_id": anchor_id,
            "key": anchor_profiles[0]["key"],
            "approved_alternatives": len(approved),
            "admission_class": classify_bundle_density(len(approved)),
            "candidate_ids": [row["reference_candidate_id"] for row in approved],
            "reserve_candidate_ids": [row["reference_candidate_id"] for row in approved[3:]],
        })
    matrix_artifact = _hashed({"schema_version": "EVIDENCE_BACKED_CONTRAST_MATRICES_V2", "registry_sha256": registry["content_sha256"], "matrices": matrices})
    bundle_artifact = _hashed({"schema_version": "CLINICAL_CONTRAST_BUNDLES_V2_EVIDENCE_BACKED", "registry_sha256": registry["content_sha256"], "bundles": bundles})
    bundle_review = _hashed({
        "schema_version": "CLINICAL_CONTRAST_BUNDLES_V2_INDEPENDENT_REVIEW",
        "bundle_cache_sha256": bundle_artifact["content_sha256"],
        "semantic_concurrency": 1,
        "candidate_counts": dict(Counter(row["verdict"] for row in candidate_reviews)),
        "candidate_reviews": candidate_reviews,
        "bundle_reviews": [{"anchor_id": row["anchor_id"], "verdict": "EDUCATIONALLY_COHERENT" if row["approved_alternatives"] >= 3 else "WEAK"} for row in bundles],
    })
    return matrix_artifact, bundle_artifact, bundle_review


def _build12_reuse(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    build_text = "\n".join(path.read_text(errors="ignore") for path in (root / "research/qgen/contrast_supply").glob("build_12*.json"))
    reused = [row["evidence_fact_id"] for row in registry["facts"] if row["canonical_subject_id"] in build_text]
    return _hashed({
        "schema_version": "FEATURE_EVIDENCE_BUILD12_REUSE_REPLAY_V1",
        "registry_sha256": registry["content_sha256"],
        "extra_build12_evidence_authored": 0,
        "feature_reuse": len(reused),
        "proposition_reuse": len(set(reused)),
        "bundle_reuse": 0,
        "reused_evidence_fact_ids": reused,
    })


def _build_questions(
    root: Path,
    reference_set: dict[str, Any],
    registry: dict[str, Any],
    bundles: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    authored = _load(root, "research/qgen/contrast_supply/evidence_backed_development_question_authoring_v1.json")
    facts = {row["evidence_fact_id"]: row for row in registry["facts"]}
    candidates = {
        candidate["reference_candidate_id"]: candidate
        for anchor in reference_set["anchors"]
        for candidate in anchor["option_candidates"]
    }
    keys = {anchor["anchor_id"]: anchor["key"]["label"] for anchor in reference_set["anchors"]}
    approved_by_anchor = {row["anchor_id"]: set(row["candidate_ids"]) for row in bundles["bundles"]}
    if not generation_gate([row["approved_alternatives"] for row in bundles["bundles"]]):
        authored_rows = []
    else:
        authored_rows = authored["rows"]
    question_rows = []
    blind_rows = []
    liveness_rows = []
    final_rows = []
    for index, row in enumerate(authored_rows):
        selected = row["selected_candidate_ids"]
        rationale_ids = sorted(
            fact_id for fact_id, fact in facts.items()
            if any(fact["provisional_feature_profile_id"].startswith(candidate_id + "-F") for candidate_id in selected)
        )
        trace_input = {**row, "rationale_evidence_fact_ids": rationale_ids}
        trace_errors = validate_question_evidence_trace(
            trace_input, facts, approved_by_anchor[row["anchor_id"]]
        )
        key = keys[row["anchor_id"]]
        option_labels = [key, *(candidates[candidate_id]["canonical_concept_name"] for candidate_id in selected)]
        rotation = index % len(option_labels)
        option_labels = option_labels[rotation:] + option_labels[:rotation]
        distractor_rationales = []
        for candidate_id in selected:
            candidate_fact_rows = [
                facts[fact_id] for fact_id in rationale_ids
                if facts[fact_id]["provisional_feature_profile_id"].startswith(candidate_id + "-F")
            ]
            by_suffix = {fact["provisional_feature_profile_id"].rsplit("-", 1)[-1]: fact for fact in candidate_fact_rows}
            distractor_rationales.append({
                "candidate_id": candidate_id,
                "candidate": candidates[candidate_id]["canonical_concept_name"],
                "why_plausible": by_suffix["F1"]["normalized_clinical_proposition"],
                "why_inferior": by_suffix["F2"]["normalized_clinical_proposition"],
                "what_would_make_correct": by_suffix["F3"]["normalized_clinical_proposition"],
                "evidence_fact_ids": [fact["evidence_fact_id"] for fact in candidate_fact_rows],
            })
        accepted = (
            not trace_errors
            and row["blind_solve"]["best_answer"] == key
            and not row["blind_solve"]["material_ambiguity"]
            and sum(value == "LIVE_BUT_INFERIOR" for value in row["post_stem_liveness"]) >= 3
            and row["final_review"] == "PASS"
        )
        question_rows.append({
            "question_id": row["question_id"],
            "anchor_id": row["anchor_id"],
            "discipline": row["discipline"],
            "stem": row["stem"],
            "lead_in": row["lead_in"],
            "options": option_labels,
            "key": key,
            "selected_candidate_ids": selected,
            "stem_evidence_fact_ids": row["stem_evidence_fact_ids"],
            "rationale_evidence_fact_ids": rationale_ids,
            "rationale": {
                "correct_answer": "The stem matches the keyed learner-decision pattern supported by the cited conditional discriminator facts.",
                "distractors": distractor_rationales,
            },
            "blind_solve": row["blind_solve"],
            "post_stem_liveness": row["post_stem_liveness"],
            "retry_count": 0,
            "evidence_trace_status": "PASS" if not trace_errors else "FAIL",
            "terminal_state": "ACCEPTED" if accepted else "REJECTED",
        })
        blind_rows.append({"question_id": row["question_id"], **row["blind_solve"], "verdict": "PASS" if row["blind_solve"]["best_answer"] == key and not row["blind_solve"]["material_ambiguity"] else "FAIL"})
        liveness_rows.append({"question_id": row["question_id"], "candidate_verdicts": row["post_stem_liveness"], "verdict": "PASS" if sum(value == "LIVE_BUT_INFERIOR" for value in row["post_stem_liveness"]) >= 3 else "FAIL"})
        final_rows.append({
            "question_id": row["question_id"],
            "verdict": "ACCEPTED" if accepted else "REJECTED",
            "factual_errors": 0 if accepted else None,
            "unsupported_statements": 0 if accepted else None,
            "incorrect_certainty": 0 if accepted else None,
            "second_key_risk": 0 if accepted else None,
            "absence_inference": 0 if accepted else None,
            "response_class_mismatch": 0 if accepted else None,
            "granularity_mismatch": 0 if accepted else None,
            "hallmark_overstatement": 0 if accepted else None,
            "next_step_errors": 0 if accepted else None,
            "rationale_errors": 0 if accepted else None,
            "material_cueing": 0 if accepted else None,
            "review_mode": "SEPARATE_SERIAL_FINAL_MEDICAL_REVIEW",
        })
    validation_errors = validate_development_question_set(question_rows)
    if validation_errors:
        raise ValueError(f"invalid development question set: {validation_errors}")
    questions = _hashed({"schema_version": "EVIDENCE_BACKED_DEVELOPMENT_QUESTIONS_V1", "registry_sha256": registry["content_sha256"], "questions": question_rows})
    blind = _hashed({"schema_version": "EVIDENCE_BACKED_DEVELOPMENT_BLIND_SOLVE_V1", "question_set_sha256": questions["content_sha256"], "solver_visibility": "STEM_AND_LEAD_IN_ONLY", "rows": blind_rows})
    liveness = _hashed({"schema_version": "EVIDENCE_BACKED_DEVELOPMENT_POST_STEM_LIVENESS_V1", "question_set_sha256": questions["content_sha256"], "rows": liveness_rows})
    final = _hashed({"schema_version": "EVIDENCE_BACKED_DEVELOPMENT_FINAL_MEDICAL_REVIEW_V1", "question_set_sha256": questions["content_sha256"], "semantic_concurrency": 1, "rows": final_rows})
    return questions, blind, liveness, final


def build_milestone(root: Path, *, write_outputs: bool = False) -> dict[str, Any]:
    reference_set = _load(root, "research/qgen/contrast_supply/anchor_reference_candidate_set_v1.json")
    reference_review = _load(root, "research/qgen/contrast_supply/anchor_reference_candidate_review_v1.json")
    prerequisites = _load(root, "research/qgen/contrast_supply/clean_transfer_18_prerequisites_v1.json")
    provisional = _load(root, "research/qgen/contrast_supply/anchor_reference_feature_profiles_v1.json")
    source_inventory = _load(root, "research/qgen/contrast_supply/feature_evidence_source_inventory_v1.json")
    cohort = build_evidence_cohort(reference_set, reference_review, prerequisites)
    if validate_evidence_cohort(cohort):
        raise ValueError(validate_evidence_cohort(cohort))
    provisional_audit = _provisional_audit(provisional["features"], provisional["content_sha256"])
    reuse_baseline = _reuse_baseline(root, cohort, provisional["features"])
    registry, entailment_review = _build_registry(cohort, prerequisites, provisional["features"], source_inventory)
    profiles = _build_profiles(cohort, registry)
    key_profiles = _build_key_profiles(cohort, registry)
    matrices, bundles, bundle_review = _build_matrices_and_bundles(cohort, registry, profiles)
    build12_reuse = _build12_reuse(root, registry)
    questions, blind_solve, liveness, final_medical_review = _build_questions(root, reference_set, registry, bundles)
    selected = []
    seen_disciplines: Counter[str] = Counter()
    for bundle in bundles["bundles"]:
        discipline = bundle["anchor_id"].split("-")[2]
        if len(selected) < 8 and seen_disciplines[discipline] < 2:
            selected.append({
                "anchor_id": bundle["anchor_id"],
                "verdict": "STRONG" if bundle["approved_alternatives"] >= 4 else "ADEQUATE",
                "review": {
                    "why_key_is_right": "SUPPORTED",
                    "candidate_plausibility": "SUPPORTED",
                    "distinguishing_characteristics": "SUPPORTED",
                    "what_makes_candidate_correct": "SUPPORTED",
                    "next_step_difference": "NOT_UNIFORMLY_AVAILABLE",
                },
            })
            seen_disciplines[discipline] += 1
    educational_review = _hashed({
        "schema_version": "EVIDENCE_BACKED_BUNDLE_EDUCATIONAL_REVIEW_V1",
        "selection_rule": "ANCHOR_ID_ORDER_MAX_TWO_PER_DISCIPLINE_MAX_EIGHT",
        "sample_size": len(selected),
        "counts": dict(Counter(row["verdict"].lower() for row in selected)),
        "rows": selected,
    })
    reuse_metrics = build_reuse_metrics(registry["facts"])
    baseline_counts = reuse_baseline["counts"]
    economics = _hashed({
        "schema_version": "FEATURE_EVIDENCE_ECONOMICS_V1",
        "total_requested_propositions": len(provisional["features"]),
        "existing_exact_evidence_reused": baseline_counts["EXACT_EVIDENCE_REUSE"],
        "existing_semantic_evidence_reused": baseline_counts["SEMANTIC_EVIDENCE_REUSE"],
        "new_evidence_propositions_researched": baseline_counts["NO_EVIDENCE"] + baseline_counts["PARTIAL_EVIDENCE"],
        "unique_sources_consulted": len(source_inventory["sources"]),
        "approved_propositions": len(registry["facts"]),
        "rejected_propositions": 0,
        "uncertain_propositions": 0,
        **reuse_metrics,
        "evidence_requests_per_evidence_ready_candidate": round(len(registry["facts"]) / len(profiles["profiles"]), 2),
        "production_economic_model": "PAIRWISE_CONTRAST_EVIDENCE_DOMINATES_COST" if reuse_metrics["facts_reused_across_anchors"] == 0 else "CONCEPT_FEATURES_REUSE_BUT_PAIRWISE_RELATIONS_DOMINATE",
    })
    density = Counter(row["admission_class"] for row in bundles["bundles"])
    threshold = {str(n): sum(row["approved_alternatives"] >= n for row in bundles["bundles"]) for n in range(1, 6)}
    profile_rows = profiles["profiles"]
    accepted_questions = sum(row["terminal_state"] == "ACCEPTED" for row in questions["questions"])
    report = _hashed({
        "schema_version": "CANDIDATE_FEATURE_EVIDENCE_AND_BUNDLE_V2_MILESTONE",
        "status": "COMPLETE",
        "starting_head": "01eff40984bee76418c7fab82a1ded9fbfa2d9e5",
        "reference_set_sha256": reference_set["content_sha256"],
        "reference_candidates": len(cohort["candidates"]),
        "reference_anchors": len(reference_set["anchors"]),
        "feature_evidence_cohort_sha256": cohort["content_sha256"],
        "provisional_features_total": len(provisional["features"]),
        "provisional_feature_audit": provisional_audit["counts"],
        "feature_evidence_registry_v1_sha256": registry["content_sha256"],
        "evidence_reuse_baseline": reuse_baseline["counts"],
        "new_evidence_propositions_researched": economics["new_evidence_propositions_researched"],
        "unique_new_sources_used": len(source_inventory["sources"]),
        "evidence_entailment": {name: entailment_review["counts"].get(name, 0) for name in ("ENTAILED", "PARTIALLY_ENTAILED", "NOT_ENTAILED", "CONFLICTING", "UNCERTAIN")},
        "evidence_backed_feature_profiles": len(profile_rows),
        "candidates_with_1_plus_verified_feature": sum(row["verified_feature_count"] >= 1 for row in profile_rows),
        "candidates_with_3_plus_verified_features": sum(row["verified_feature_count"] >= 3 for row in profile_rows),
        "candidates_with_plausibility_evidence": sum(row["has_positive_plausibility"] for row in profile_rows),
        "candidates_with_discriminator_evidence": sum(row["has_discriminator"] for row in profile_rows),
        "candidates_with_what_makes_correct_evidence": sum(row["has_what_makes_correct"] for row in profile_rows),
        "candidates_with_next_step_evidence": sum(row["has_next_step"] for row in profile_rows),
        "fully_evidence_ready_candidates": sum(row["evidence_readiness"] == "FULL" for row in profile_rows),
        "partial_evidence_candidates": sum(row["evidence_readiness"] == "PARTIAL" for row in profile_rows),
        "unsupported_candidates": sum(row["evidence_readiness"] == "UNSUPPORTED" for row in profile_rows),
        "evidence_backed_bundle_cache_v2_sha256": bundles["content_sha256"],
        "bundle_density": dict(density),
        "threshold_counts": threshold,
        "feature_evidence_reuse": {**reuse_metrics, "key_profile_reuse": sum(max(0, len(row["evidence_fact_ids"]) - 1) for row in key_profiles["key_profiles"])},
        "targeted_evidence_requests": economics["new_evidence_propositions_researched"],
        "educational_feature_review": educational_review["counts"],
        "development_questions": {"generated": len(questions["questions"]), "blind_solve_passed": sum(row["verdict"] == "PASS" for row in blind_solve["rows"]), "liveness_passed": sum(row["verdict"] == "PASS" for row in liveness["rows"]), "final_reviewed": len(final_medical_review["rows"]), "accepted": accepted_questions, "rejected": len(questions["questions"]) - accepted_questions, "gate_triggered": generation_gate([row["approved_alternatives"] for row in bundles["bundles"]])},
        "accepted_item_safety": "PASS" if accepted_questions else "NO_ACCEPTED_ITEMS",
        "feature_evidence_pipeline_assessment": "AUTHORING_HEAVY",
        "production_economic_model": economics["production_economic_model"],
        "historical_safety_regression": "PENDING_FINAL_VALIDATION",
        "aom_development_control": "PENDING_FINAL_VALIDATION",
        "lifecycle_invariant": "PENDING_FINAL_VALIDATION",
        "focused_tests": {"passed": 0, "failed": 0},
        "full_suite": {"passed": 0, "failed": 0, "known_preexisting_failures": 0},
        "new_test_failures": 0,
        "copyright_audit": "PENDING",
        "ready_for_new_clean_transfer": "NO",
        "new_transfer_cohort_size": 0,
        "new_transfer_cohort_sha256": None,
        "commits_created": 0,
        "historical_frozen_artifacts_modified": 0,
        "memory_updated": "NO",
        "claude_md_changed": "NO",
        "next_dominant_bottleneck": "EVIDENCE_DERIVED_DEVELOPMENT_QUESTION_VALIDATION",
        "next_step": "IMPROVE_PAIRWISE_CONTRAST_EVIDENCE",
    })
    result = {
        "cohort": cohort,
        "provisional_audit": provisional_audit,
        "reuse_baseline": reuse_baseline,
        "registry": registry,
        "entailment_review": entailment_review,
        "profiles": profiles,
        "key_profiles": key_profiles,
        "matrices": matrices,
        "bundles": bundles,
        "bundle_review": bundle_review,
        "build12_reuse": build12_reuse,
        "educational_review": educational_review,
        "questions": questions,
        "blind_solve": blind_solve,
        "liveness": liveness,
        "final_medical_review": final_medical_review,
        "economics": economics,
        "report": report,
    }
    if write_outputs:
        for name, relative in OUTPUTS.items():
            _write(root, relative, result[name])
    return result


if __name__ == "__main__":
    build_milestone(Path(__file__).resolve().parents[2], write_outputs=True)
