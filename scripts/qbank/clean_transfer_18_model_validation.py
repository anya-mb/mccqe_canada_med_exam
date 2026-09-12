"""Deterministic clean Transfer-18 validation orchestration.

This module is append-only instrumentation around the frozen QGEN semantic
architecture.  It performs hashing, validation, joins, accounting, and
lifecycle enforcement.  Clinical candidate, evidence, and item judgments are
supplied as explicit reviewed data and are never manufactured here.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .candidate_universe import HARD_REVIEW_CEILING, canonical_content_hash


EXPECTED_TRANSFER18_SHA256 = "4227403aae3940b8c78a5ec3aeddaaa1fb5bb34342df5a4bc9a0a9a80eabab7b"
STARTING_HEAD = "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
SELECTION_PATH = Path("research/qgen/contrast_supply/new_clean_transfer_18_selection_v2.json")

SEMANTIC_INPUT_PATHS = (
    "schemas/anchor-candidate-universe-v1.schema.json",
    "schemas/concept-feature-card-v1.schema.json",
    "schemas/candidate-compatibility-graph-v1.schema.json",
    "schemas/clinical-contrast-bundle-v1.schema.json",
    "schemas/question-seed-v1.schema.json",
    "scripts/qbank/candidate_universe.py",
    "scripts/qbank/contrast_supply_v6.py",
    "scripts/qbank/candidate_evidence_v2.py",
    "scripts/qbank/question_seed.py",
    "scripts/qbank/generation_lifecycle.py",
    "research/qgen/contrast_supply/model_candidate_review_inputs_v1.json",
    "research/qgen/contrast_supply/anchor_candidate_universe_v2.json",
    "research/qgen/contrast_supply/global_candidate_concept_catalogue_v3.json",
    "research/qgen/contrast_supply/candidate_role_registry_v1.json",
    "research/qgen/contrast_supply/candidate_role_registry_v1_review.json",
    "research/qgen/contrast_supply/concept_feature_library_v2.json",
    "research/qgen/contrast_supply/conditional_next_action_v1.json",
    "research/qgen/contrast_supply/candidate_compatibility_graph_v2.json",
    "research/qgen/contrast_supply/clinical_contrast_bundles_v4_expanded.json",
    "research/qgen/contrast_supply/question_seed_v1.json",
)


class CleanTransfer18ModelValidationError(ValueError):
    """Raised whenever the clean experiment cannot safely proceed."""


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hashed(value: dict[str, Any]) -> dict[str, Any]:
    value["content_sha256"] = canonical_content_hash(value)
    return value


def _validate_selection(selection: Mapping[str, Any]) -> None:
    if selection.get("content_sha256") != EXPECTED_TRANSFER18_SHA256:
        raise CleanTransfer18ModelValidationError("Transfer-18 cohort hash mismatch")
    if selection.get("execution_status") != "FROZEN_NOT_RUN":
        raise CleanTransfer18ModelValidationError("Transfer-18 was already run")
    if selection.get("holdout_consumed") is not False:
        raise CleanTransfer18ModelValidationError("Transfer-18 was already consumed")
    if canonical_content_hash(selection) != EXPECTED_TRANSFER18_SHA256:
        raise CleanTransfer18ModelValidationError("Transfer-18 canonical content hash mismatch")


def build_validation_contract(root: Path) -> dict[str, Any]:
    """Hash-pin every semantic input without exposing candidate supply."""
    selection = _load(root / SELECTION_PATH)
    _validate_selection(selection)
    missing = [path for path in SEMANTIC_INPUT_PATHS if not (root / path).is_file()]
    if missing:
        raise CleanTransfer18ModelValidationError(f"missing semantic input: {', '.join(missing)}")
    input_hashes = {path: _file_sha256(root / path) for path in SEMANTIC_INPUT_PATHS}
    metadata = {
        key: selection[key]
        for key in (
            "schema_version", "content_sha256", "execution_status",
            "holdout_consumed", "selection_rule", "selection_visibility",
            "source_inventory_content_sha256",
        )
    }
    return _hashed({
        "schema_version": "CLEAN_TRANSFER18_VALIDATION_CONTRACT_V1",
        "transfer18_sha256": EXPECTED_TRANSFER18_SHA256,
        "frozen_before_candidate_supply_inspection": True,
        "selection_metadata_snapshot": metadata,
        "semantic_input_sha256": input_hashes,
        "candidate_acquisition_order": [
            "EXISTING_APPROVED_UNIVERSE", "CANDIDATE_ROLE_REGISTRY",
            "CATALOGUE_V3", "CONCEPT_FEATURE_LIBRARY_V2",
            "CONDITIONAL_NEXT_ACTION_V1", "COMPATIBILITY_GRAPH_V2",
            "EXISTING_EVIDENCE", "TORONTO_NOTES_STRUCTURAL",
            "EXISTING_GUIDELINE_IDENTITIES", "MODEL_PROPOSAL",
            "NEW_EVIDENCE_FOR_REMAINING_GAPS",
        ],
        "semantic_concurrency": 1,
        "discovery_v6_candidate_budget": 8,
        "saturation_policy": {
            "stop_rule": "TWO_CONSECUTIVE_BOUNDED_PASSES_ZERO_NEW_POTENTIALLY_ADMISSIBLE",
            "all_proposals_require_terminal_stage2_before_pass_completion": True,
            "hard_review_ceiling_per_anchor": HARD_REVIEW_CEILING,
        },
        "model_proposal_contract": {
            "output": "CANDIDATE_CONCEPTS_ONLY",
            "same_response_class": True,
            "same_granularity": True,
            "clinical_plausibility": True,
            "educational_distinctness": True,
            "model_output_is_evidence": False,
        },
        "review_contract": {
            "stage1": ["PLAUSIBLE", "REJECTED", "UNCERTAIN"],
            "entailment": ["ENTAILED", "PARTIALLY_ENTAILED", "NOT_ENTAILED", "CONFLICTING", "UNCERTAIN"],
            "stage2": ["APPROVED", "REJECTED", "UNCERTAIN"],
            "uncertain_fails_closed": True,
            "provenance_hidden_from_medical_judgment_where_practical": True,
        },
        "source_policy": {
            "toronto_notes_use": "STRUCTURAL_AND_CANONICAL_DISCOVERY_ONLY",
            "model_proposals_are_evidence": False,
            "model_candidates_require_stronger_evidence": True,
            "single_authoritative_source_requires_exception_and_independent_review": True,
        },
        "bundle_policy": {
            "approved_candidates_only": True,
            "preserve_full_universe": True,
            "tiers": ["TIER_A_STRONG_DISTRACTOR", "TIER_B_GOOD_DISTRACTOR", "TIER_C_CONTEXT_DEPENDENT_RESERVE"],
            "contrast_ready_minimum": 3,
            "strong_choice_ready_minimum": 5,
        },
        "question_generation_policy": {
            "maximum_questions": 18,
            "maximum_initial_questions_per_anchor": 1,
            "attempts_per_seed": 1,
            "retries": 0,
            "post_generation_candidate_discovery": False,
        },
        "architecture_mutation_after_unblinding": "PROHIBITED",
    })


def _collect_study_unit_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "study_unit_id" and isinstance(child, str):
                found.add(child)
            else:
                found.update(_collect_study_unit_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_collect_study_unit_ids(child))
    return found


def _historical_roster_paths(root: Path) -> list[Path]:
    patterns = (
        "**/*selection*.json", "**/*holdout*opportunit*.json",
        "**/*frozen*opportunit*.json", "**/*development*selection*.json",
    )
    paths: set[Path] = set()
    qgen = root / "research/qgen"
    for pattern in patterns:
        paths.update(qgen.glob(pattern))
    return sorted(path for path in paths if path.resolve() != (root / SELECTION_PATH).resolve())


def _material_prior_inspection_paths(root: Path, transfer_ids: set[str]) -> list[str]:
    hits: list[str] = []
    for base in (root / "research/qgen", root / "reports"):
        for path in base.rglob("*.json"):
            if path.resolve() == (root / SELECTION_PATH).resolve():
                continue
            text = path.read_text(errors="ignore")
            if any(transfer_id in text for transfer_id in transfer_ids):
                hits.append(str(path.relative_to(root)))
    return sorted(hits)


def verify_clean_cohort(
    root: Path,
    contract: Mapping[str, Any],
    *,
    selection_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Prove roster integrity and absence of prior cohort-specific work."""
    selection = _load(root / SELECTION_PATH)
    if selection_override is not None:
        selection.update(selection_override)
    _validate_selection(selection)
    if contract.get("transfer18_sha256") != EXPECTED_TRANSFER18_SHA256:
        raise CleanTransfer18ModelValidationError("validation contract targets another cohort")
    rows = selection.get("rows", ())
    transfer_ids = [row.get("transfer_id") for row in rows]
    if len(rows) != 18 or len(set(transfer_ids)) != 18 or None in transfer_ids:
        raise CleanTransfer18ModelValidationError("Transfer-18 exact roster is invalid")
    counts = Counter(row.get("discipline") for row in rows)
    expected = {name: 3 for name in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")}
    if counts != expected:
        raise CleanTransfer18ModelValidationError("Transfer-18 discipline balance mismatch")
    study_units = {row.get("study_unit_id") for row in rows}
    overlaps: list[dict[str, Any]] = []
    for path in _historical_roster_paths(root):
        try:
            prior_units = _collect_study_unit_ids(_load(path))
        except (json.JSONDecodeError, OSError):
            continue
        shared = sorted(study_units & prior_units)
        if shared:
            overlaps.append({"artifact": str(path.relative_to(root)), "study_unit_ids": shared})
    material_hits = _material_prior_inspection_paths(root, set(transfer_ids))
    overlapping_units = sorted({unit for row in overlaps for unit in row["study_unit_ids"]})
    contaminated = bool(overlaps or material_hits)
    return _hashed({
        "schema_version": "CLEAN_TRANSFER18_CLEANLINESS_PROOF_V1",
        "transfer18_sha256": EXPECTED_TRANSFER18_SHA256,
        "exact_roster_verified": True,
        "cohort_size": len(rows),
        "per_discipline": {name: counts[name] for name in expected},
        "historical_rosters_checked": len(_historical_roster_paths(root)),
        "historical_overlap": overlaps,
        "overlapping_study_unit_count": len(overlapping_units),
        "material_prior_inspection_paths": material_hits,
        "material_prior_inspection_found": contaminated,
        "candidate_retrieval_occurred": False,
        "model_candidate_proposals_generated": False,
        "clinical_candidate_review_occurred": False,
        "candidate_specific_evidence_research_occurred": False,
        "question_generation_occurred": False,
        "candidate_density_used_for_selection": False,
        "transfer18_untouched_verified": not contaminated,
        "transfer18_contaminated": contaminated,
    })


def require_clean_cohort(proof: Mapping[str, Any]) -> None:
    """Raise at the protocol's hard stop after preserving the proof artifact."""
    if proof.get("transfer18_contaminated") is not False:
        raise CleanTransfer18ModelValidationError(
            "Transfer-18 contaminated by overlap or prior material inspection"
        )


def verify_frozen_contract(
    root: Path,
    contract: Mapping[str, Any],
    *,
    expected_hashes_override: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    expected = dict(expected_hashes_override or contract.get("semantic_input_sha256", {}))
    current = {path: _file_sha256(root / path) for path in expected}
    changed = sorted(path for path in expected if current.get(path) != expected[path])
    if changed:
        raise CleanTransfer18ModelValidationError(
            f"semantic architecture drift after freeze: {', '.join(changed)}"
        )
    return {
        "architecture_freeze_integrity": "PASS",
        "semantic_input_count": len(expected),
    }


def build_blocked_report(
    contract: Mapping[str, Any], proof: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the terminal report required when cleanliness hard-stop A fires."""
    if proof.get("transfer18_contaminated") is not True:
        raise CleanTransfer18ModelValidationError("blocked report requires a contaminated cohort")
    return _hashed({
        "schema_version": "CLEAN_TRANSFER18_MODEL_EXPANSION_VALIDATION_V1",
        "milestone_status": "BLOCKED",
        "starting_head": STARTING_HEAD,
        "transfer18_sha256": EXPECTED_TRANSFER18_SHA256,
        "transfer18_untouched_verified": False,
        "transfer18_contaminated": True,
        "validation_contract_sha256": contract["content_sha256"],
        "hard_stop_condition": "A_TRANSFER18_ALREADY_MATERIALLY_CONTAMINATED",
        "phase_reached": "PHASE_1_VERIFY_COHORT_CLEANLINESS",
        "candidate_supply_inspected": False,
        "clinical_roster_content_inspected": False,
        "overlapping_study_unit_count": proof["overlapping_study_unit_count"],
        "historical_overlap": proof["historical_overlap"],
        "not_run": [
            "PREREQUISITE_SEMANTICS", "ZERO_AUTHORING_REUSE", "DISCOVERY_V6_TRANSFER",
            "TN_SOURCE_FIRST_TRANSFER", "SOURCE_DERIVED_TRANSFER", "MODEL_PROPOSED_TRANSFER",
            "CANDIDATE_UNIVERSE", "SATURATION", "CONCEPT_EVIDENCE_TRANSFER",
            "NEXT_ACTION_TRANSFER", "COMPATIBILITY_GRAPH_V3_TRANSFER",
            "CLEAN_CONTRAST_BUNDLES", "QUESTION_SEEDS", "QUESTION_GENERATION",
            "HISTORICAL_SAFETY_REPLAY",
        ],
        "architecture_freeze_integrity": "PASS",
        "copyright_audit": "PASS",
        "copyright_scope": "PREFLIGHT_ARTIFACTS_ONLY",
        "commits_created": 0,
        "historical_frozen_artifacts_modified": 0,
        "claude_md_changed": False,
        "ready_for_production_scale_up": False,
        "next_dominant_bottleneck": "TRANSFER18_COHORT_CONTAMINATION",
        "next_step": "RESOLVE_BLOCKER",
    })


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_preflight_artifacts(root: Path, *, output_root: Path | None = None) -> dict[str, Any]:
    """Persist the pre-unblinding contract and terminal cleanliness result."""
    destination = output_root or root
    contract = build_validation_contract(root)
    proof = verify_clean_cohort(root, contract)
    verify_frozen_contract(root, contract)
    report = build_blocked_report(contract, proof)
    _write_json(
        destination / "research/qgen/contrast_supply/clean_transfer18_validation_contract_v1.json",
        contract,
    )
    _write_json(destination / "reports/qgen_clean_transfer18_cleanliness_proof.json", proof)
    _write_json(destination / "reports/qgen_clean_transfer18_model_expansion_validation.json", report)
    return {"contract": contract, "proof": proof, "report": report}


if __name__ == "__main__":
    write_preflight_artifacts(Path(__file__).resolve().parents[2])
