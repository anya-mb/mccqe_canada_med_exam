"""Independent two-stage verification contracts for production-candidate items.

This module never authors questions and never grants generation readiness.  It
packages already-authored items, enforces blind-first review, validates direct
evidence traces, and records immutable external-verification outcomes.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class VerificationError(ValueError):
    pass


VERIFIED_CONTENT_FIELDS = (
    "stem", "lead_in", "answer_choices", "author_proposed_key", "author_rationale",
    "per_distractor_rationales", "evidence_fact_ids", "toronto_notes_source_refs", "canadian_source_refs",
)

FINAL_VERDICTS = (
    "VERIFIED_ACCEPT", "REJECT_WRONG_KEY", "REJECT_SECOND_KEY", "REJECT_AMBIGUOUS",
    "REJECT_UNSUPPORTED_RATIONALE", "REJECT_HALLUCINATION",
    "REJECT_CANADIAN_GUIDELINE_CONFLICT", "REJECT_TORONTO_NOTES_CONFLICT",
    "REJECT_OUTDATED_GUIDANCE", "REJECT_WEAK_DISTRACTORS", "NEEDS_SOURCE_UPDATE",
    "NEEDS_HUMAN_ADJUDICATION",
)

EXPECTED_MUTATION_RESULT_KEYS = frozenset({
    "wrong_key_detected", "second_key_detected", "unsupported_claim_detected",
    "false_citation_detected", "outdated_guidance_detected", "tn_conflict_detected",
    "canadian_guideline_conflict_detected",
})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _verified_content(package: Mapping[str, Any]) -> dict[str, Any]:
    return {field: package.get(field) for field in VERIFIED_CONTENT_FIELDS}


def blind_projection(package: Mapping[str, Any]) -> dict[str, Any]:
    blind = {
        "schema_version": "1.0",
        "item_id": package["item_id"],
        "stem": package["stem"],
        "lead_in": package["lead_in"],
        "answer_choices": deepcopy(package["answer_choices"]),
    }
    blind["blind_packet_sha256"] = canonical_hash(blind)
    return blind


def freeze_blind_solve(blind_packet: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    if blind_packet.get("blind_packet_sha256") != canonical_hash({
        key: value for key, value in blind_packet.items() if key != "blind_packet_sha256"
    }):
        raise VerificationError("BLIND_PACKET_HASH_MISMATCH")
    required = {
        "reviewer_session_id", "chosen_best_answer", "confidence", "possible_second_key",
        "ambiguity", "missing_information", "mccqe_realism",
    }
    if set(result) != required:
        raise VerificationError("INVALID_BLIND_SOLVE_FIELDS")
    frozen = {
        "schema_version": "1.0",
        "item_id": blind_packet["item_id"],
        "blind_packet_sha256": blind_packet["blind_packet_sha256"],
        **deepcopy(dict(result)),
        "frozen": True,
    }
    frozen["content_sha256"] = canonical_hash(frozen)
    return frozen


def open_evidence_audit(
    package: Mapping[str, Any], frozen_blind_solve: Mapping[str, Any], *, verifier_session_id: str,
) -> dict[str, Any]:
    stored = frozen_blind_solve.get("content_sha256")
    computed = canonical_hash({key: value for key, value in frozen_blind_solve.items() if key != "content_sha256"})
    if not stored or stored != computed or frozen_blind_solve.get("frozen") is not True:
        raise VerificationError("BLIND_SOLVE_HASH_MISMATCH")
    if verifier_session_id == package.get("author_session_id"):
        raise VerificationError("NONINDEPENDENT_VERIFIER_SESSION")
    if verifier_session_id != frozen_blind_solve.get("reviewer_session_id"):
        raise VerificationError("STAGE_SESSION_MISMATCH")
    if package.get("content_sha256") != canonical_hash({
        key: value for key, value in package.items() if key != "content_sha256"
    }):
        raise VerificationError("AUTHOR_PACKAGE_HASH_MISMATCH")
    return {
        "schema_version": "1.0",
        "item_id": package["item_id"],
        "verifier_session_id": verifier_session_id,
        "frozen_blind_solve_sha256": stored,
        "author_package_sha256": package["content_sha256"],
        "revealed_package": deepcopy(dict(package)),
    }


def validate_evidence_audit(package: Mapping[str, Any], audit: Mapping[str, Any]) -> None:
    allowed_claim_statuses = {
        "VERIFIED", "SUPPORTED_WITH_SCOPE_LIMITATION", "UNSUPPORTED", "CONTRADICTED",
        "OUTDATED", "SOURCE_NOT_FOUND", "OVERSTATED", "NOT_LOAD_BEARING",
    }
    for claim in audit.get("claims", []):
        if claim.get("status") not in allowed_claim_statuses:
            raise VerificationError("UNKNOWN_CLAIM_STATUS")
        if claim.get("load_bearing") and not claim.get("source_traces"):
            raise VerificationError("LOAD_BEARING_CLAIM_MISSING_DIRECT_TRACE")
    if audit.get("blind_answer_matches_key") is True and not package.get("author_proposed_key"):
        raise VerificationError("MISSING_AUTHOR_KEY")


def derive_verification_verdict(audit: Mapping[str, Any]) -> str:
    if not audit.get("blind_answer_matches_key", False):
        return "REJECT_WRONG_KEY"
    if audit.get("possible_second_key"):
        return "REJECT_SECOND_KEY"
    if not audit.get("one_best_answer", False):
        return "REJECT_AMBIGUOUS"
    if audit.get("unsupported_claim"):
        return "REJECT_UNSUPPORTED_RATIONALE"
    if audit.get("hallucination_flags"):
        return "REJECT_HALLUCINATION"
    if audit.get("canadian_guidance_status") == "MATERIAL_CONFLICT":
        return "REJECT_CANADIAN_GUIDELINE_CONFLICT"
    if audit.get("tn_status") == "MATERIAL_TN_CONTRADICTION":
        return "REJECT_TORONTO_NOTES_CONFLICT"
    if audit.get("outdated_guidance"):
        return "REJECT_OUTDATED_GUIDANCE"
    if audit.get("plausible_inferior_distractor_count", 0) < 3:
        return "REJECT_WEAK_DISTRACTORS"
    if not audit.get("same_response_class") or not audit.get("compatible_granularity"):
        return "REJECT_WEAK_DISTRACTORS"
    if audit.get("rationale_quality") != "PASS":
        return "REJECT_UNSUPPORTED_RATIONALE"
    if audit.get("source_conflict_status") in {"MATERIAL_CONFLICT", "UNCERTAIN"}:
        return "NEEDS_HUMAN_ADJUDICATION"
    return "VERIFIED_ACCEPT"


def requires_reverification(previous_entry: Mapping[str, Any], current_package: Mapping[str, Any]) -> bool:
    if previous_entry.get("final_verification_status") != "VERIFIED_ACCEPT":
        return True
    return previous_entry.get("verified_content_sha256") != canonical_hash(_verified_content(current_package))


def append_ledger_entry(ledger: Mapping[str, Any], entry: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(ledger))
    entries = result.setdefault("entries", [])
    prior = entries[-1]["entry_sha256"] if entries else None
    added = deepcopy(dict(entry))
    if added.get("final_verification_status") not in FINAL_VERDICTS:
        raise VerificationError("UNKNOWN_FINAL_VERIFICATION_STATUS")
    added["previous_entry_sha256"] = prior
    added["entry_sha256"] = canonical_hash(added)
    entries.append(added)
    result["content_sha256"] = canonical_hash({key: value for key, value in result.items() if key != "content_sha256"})
    return result


def verify_ledger_chain(ledger: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_content_hash = canonical_hash({
        key: value for key, value in ledger.items() if key != "content_sha256"
    })
    if ledger.get("content_sha256") != expected_content_hash:
        errors.append("LEDGER_CONTENT_HASH_MISMATCH")
    prior = None
    for index, entry in enumerate(ledger.get("entries", [])):
        if entry.get("previous_entry_sha256") != prior:
            errors.append(f"ENTRY_{index}_PREVIOUS_HASH_MISMATCH")
        computed = canonical_hash({key: value for key, value in entry.items() if key != "entry_sha256"})
        if entry.get("entry_sha256") != computed:
            errors.append(f"ENTRY_{index}_HASH_MISMATCH")
        prior = entry.get("entry_sha256")
    return errors


def build_disagreement_packet(
    package: Mapping[str, Any], blind_result: Mapping[str, Any], *, author_verdict: str, verifier_verdict: str,
) -> dict[str, Any]:
    if author_verdict == verifier_verdict:
        raise VerificationError("NO_DISAGREEMENT_TO_ADJUDICATE")
    return {
        "schema_version": "1.0",
        "item_id": package["item_id"],
        "item": {key: deepcopy(package.get(key)) for key in ("stem", "lead_in", "answer_choices", "author_proposed_key")},
        "author_verdict": author_verdict,
        "verifier_verdict": verifier_verdict,
        "verifier_session_id": blind_result.get("reviewer_session_id"),
        "relevant_source_evidence": deepcopy(package.get("canadian_source_refs", [])),
        "allowed_outcomes": [
            "AUTHOR_CORRECT", "VERIFIER_CORRECT", "BOTH_INCOMPLETE", "ITEM_AMBIGUOUS", "SOURCE_CONFLICT", "REJECT"
        ],
        "third_session_required": True,
    }


def _package_hashes(package: dict[str, Any]) -> dict[str, Any]:
    package["verified_content_sha256"] = canonical_hash(_verified_content(package))
    package["content_sha256"] = canonical_hash(package)
    return package


def build_validation_packages(root: Path) -> dict[str, Any]:
    root = Path(root)
    items = json.loads((root / "research/qgen/exposure/clean_transfer_v2_questions.json").read_text())["rows"]
    seeds = {
        row["seed_id"]: row
        for row in json.loads((root / "research/qgen/exposure/clean_transfer_v2_question_seeds.json").read_text())["rows"]
    }
    sources_artifact = json.loads((root / "research/qgen/exposure/clean_transfer_v2_source_registry.json").read_text())
    source_rows = sources_artifact.get("sources") or sources_artifact.get("rows") or []
    sources = {row["source_id"]: row for row in source_rows}
    discipline_by_unit = {
        "SU-A-09": "MED", "SU-P-011": "PED", "SU-GY-15": "OBGYN",
        "SU-GS-07": "SURG", "SU-PS-10": "PSY", "SU-ELOM-17": "PHELO",
    }
    packages = []
    for item in items:
        seed = seeds[item["seed_id"]]
        unit = item["item_id"].removeprefix("CTV2-ITEM-")
        source_refs = []
        for source_id in item.get("evidence_source_ids", []):
            source = sources.get(source_id, {})
            source_refs.append({
                "source_id": source_id,
                "organization": source.get("organization", "UNKNOWN"),
                "date_or_version": source.get("retrieved_on") or source.get("version") or "UNKNOWN",
                "locator": source.get("url", "SOURCE_REGISTRY"),
            })
        distractors = []
        for row in item.get("distractor_liveness", []):
            distractors.append({
                "choice": row["option"],
                "why_plausible": row.get("review", "Plausible in a nearby clinical state."),
                "why_inferior_here": item.get("reason", "Inferior under the stated discriminator."),
                "what_would_make_correct": "Requires an independently verified alternate clinical state before production use.",
            })
        package = {
            "schema_version": "1.0", "item_id": item["item_id"], "opportunity_id": unit,
            "question_seed_id": item["seed_id"], "author_session_id": "HISTORICAL_VALIDATION_AUTHOR_SESSION",
            "discipline": discipline_by_unit[unit], "topic": seed["topic"],
            "learner_decision": seed["learner_decision"], "difficulty_intent": seed["difficulty_intent"],
            "stem": item["stem"], "lead_in": item["lead_in"], "answer_choices": item["options"],
            "author_proposed_key": item["answer"], "author_rationale": item["reason"],
            "per_distractor_rationales": distractors,
            "conditional_next_action_information": "Not recorded in this historical validation item; independently assess applicability.",
            "evidence_fact_ids": item.get("evidence_source_ids", []),
            "toronto_notes_source_refs": [], "canadian_source_refs": source_refs,
            "author_confidence": "NOT_RECORDED", "non_production_validation_item": True,
        }
        packages.append(_package_hashes(package))
    artifact = {"schema_version": "1.0", "scope": "INDEPENDENT_VERIFICATION_V1_VALIDATION_PACKAGES", "packages": packages}
    artifact["content_sha256"] = canonical_hash(artifact)
    return artifact


def run_mutation_contract_tests(package: Mapping[str, Any]) -> dict[str, bool]:
    base = {
        "blind_answer_matches_key": True, "possible_second_key": False, "one_best_answer": True,
        "unsupported_claim": False, "hallucination_flags": [], "canadian_guidance_status": "CONSISTENT",
        "tn_status": "TN_CONSISTENT", "outdated_guidance": False, "plausible_inferior_distractor_count": 3,
        "same_response_class": True, "compatible_granularity": True, "rationale_quality": "PASS",
        "source_conflict_status": "NO_CONFLICT",
    }
    mutations = {
        "wrong_key_detected": ({"blind_answer_matches_key": False}, "REJECT_WRONG_KEY"),
        "second_key_detected": ({"possible_second_key": True}, "REJECT_SECOND_KEY"),
        "unsupported_claim_detected": ({"unsupported_claim": True}, "REJECT_UNSUPPORTED_RATIONALE"),
        "false_citation_detected": ({"hallucination_flags": ["FABRICATED_CITATION"]}, "REJECT_HALLUCINATION"),
        "outdated_guidance_detected": ({"outdated_guidance": True}, "REJECT_OUTDATED_GUIDANCE"),
        "tn_conflict_detected": ({"tn_status": "MATERIAL_TN_CONTRADICTION"}, "REJECT_TORONTO_NOTES_CONFLICT"),
        "canadian_guideline_conflict_detected": (
            {"canadian_guidance_status": "MATERIAL_CONFLICT"}, "REJECT_CANADIAN_GUIDELINE_CONFLICT"
        ),
    }
    results = {}
    for name, (change, expected) in mutations.items():
        audit = deepcopy(base)
        audit.update(change)
        results[name] = derive_verification_verdict(audit) == expected
    return results


def build_external_verifier_dry_run_manifest(root: Path) -> dict[str, Any]:
    """Pin non-production packages for manual launch in another Codex session."""
    root = Path(root)
    verification_dir = root / "research/qgen/independent_verification_v1"
    package_path = verification_dir / "validation_item_packages.json"
    ledger_path = verification_dir / "production_item_verification_ledger_v1.json"
    mutation_path = verification_dir / "verification_mutation_results.json"
    prompt_path = root / "docs/qgen/INDEPENDENT_PRODUCTION_ITEM_VERIFIER_PROMPT.md"
    schema_path = root / "schemas/production-item-verification-package-v1.schema.json"
    packages = json.loads(package_path.read_text())
    ledger = json.loads(ledger_path.read_text())
    mutations = json.loads(mutation_path.read_text())
    computed_package_hash = canonical_hash({
        key: value for key, value in packages.items() if key != "content_sha256"
    })
    if packages.get("content_sha256") != computed_package_hash:
        raise VerificationError("VALIDATION_PACKAGE_ARTIFACT_HASH_MISMATCH")
    if len(packages.get("packages", [])) != 6:
        raise VerificationError("EXTERNAL_DRY_RUN_REQUIRES_EXACTLY_SIX_PACKAGES")
    if any(not row.get("non_production_validation_item") for row in packages["packages"]):
        raise VerificationError("EXTERNAL_DRY_RUN_PACKAGE_IS_NOT_NONPRODUCTION")
    ledger_errors = verify_ledger_chain(ledger)
    if ledger_errors:
        raise VerificationError(ledger_errors[0])
    computed_mutation_hash = canonical_hash({
        key: value for key, value in mutations.items() if key != "content_sha256"
    })
    if mutations.get("content_sha256") != computed_mutation_hash:
        raise VerificationError("MUTATION_RESULT_HASH_MISMATCH")
    if set(mutations.get("results", {})) != EXPECTED_MUTATION_RESULT_KEYS:
        raise VerificationError("MUTATION_RESULT_KEYS_MISMATCH")
    if not all(value is True for value in mutations["results"].values()):
        raise VerificationError("MUTATION_DETECTION_FAILED")
    package_rows = [{
        "item_id": row["item_id"],
        "discipline": row["discipline"],
        "content_sha256": row["content_sha256"],
        "verified_content_sha256": row["verified_content_sha256"],
        "non_production_validation_item": True,
    } for row in packages["packages"]]
    manifest = {
        "schema_version": "1.0",
        "scope": "EXTERNAL_VERIFIER_DRY_RUN_MANIFEST_V1",
        "validation_package_count": len(package_rows),
        "package_artifact_path": str(package_path.relative_to(root)),
        "package_artifact_content_sha256": packages["content_sha256"],
        "package_artifact_file_sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
        "verification_package_schema_file_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
        "verification_ledger_content_sha256": ledger.get("content_sha256"),
        "verification_ledger_file_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "external_verifier_prompt_file_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "ledger_chain_errors": ledger_errors,
        "mutation_tests": deepcopy(mutations["results"]),
        "packages": package_rows,
        "launch_policy": "RUN_EACH_PACKAGE_IN_A_SEPARATE_CODEX_SESSION_USING_THE_FROZEN_EXTERNAL_VERIFIER_PROMPT",
        "authoring_session_verdict": "NOT_AUTHORIZED",
        "separate_session_required": True,
    }
    manifest["content_sha256"] = canonical_hash(manifest)
    return manifest


def write_verification_artifacts(root: Path, destination: Path) -> dict[str, str]:
    root, destination = Path(root), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    packages = build_validation_packages(root)
    source_paths = [
        "research/qgen/exposure/clean_transfer_v2_questions.json",
        "research/qgen/exposure/clean_transfer_v2_question_seeds.json",
        "research/qgen/exposure/clean_transfer_v2_source_registry.json",
        "scripts/qbank/generation_lifecycle.py",
    ]
    pins = {
        "schema_version": "1.0", "scope": "INDEPENDENT_VERIFICATION_V1_HISTORICAL_INPUT_PINS",
        "files": {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in source_paths},
    }
    pins["content_sha256"] = canonical_hash(pins)
    cases = {
        "schema_version": "1.0", "scope": "INDEPENDENT_VERIFICATION_V1_SYNTHETIC_MUTATIONS",
        "source_item_policy": "DEEP_COPY_ONLY_CANONICAL_VALIDATION_ITEMS_UNCHANGED",
        "mutation_kinds": [
            "WRONG_KEY", "SECOND_KEY", "UNSUPPORTED_RATIONALE_CLAIM", "FALSE_CITATION",
            "OUTDATED_GUIDANCE", "TORONTO_NOTES_CONTRADICTION", "CANADIAN_GUIDELINE_CONTRADICTION",
        ],
    }
    cases["content_sha256"] = canonical_hash(cases)
    mutation_results = {
        "schema_version": "1.0", "scope": "INDEPENDENT_VERIFICATION_V1_MUTATION_RESULTS",
        "validation_item_id": packages["packages"][0]["item_id"],
        "results": run_mutation_contract_tests(packages["packages"][0]),
    }
    mutation_results["content_sha256"] = canonical_hash(mutation_results)
    ledger = {
        "schema_version": "1.0", "scope": "PRODUCTION_ITEM_VERIFICATION_LEDGER_V1",
        "status": "EMPTY_UNTIL_REAL_EXTERNAL_PRODUCTION_VERIFICATION", "entries": [],
    }
    ledger["content_sha256"] = canonical_hash(ledger)
    artifacts = {
        "validation_item_packages.json": packages,
        "historical_input_pins.json": pins,
        "synthetic_mutation_cases.json": cases,
        "verification_mutation_results.json": mutation_results,
        "production_item_verification_ledger_v1.json": ledger,
    }
    for name, artifact in artifacts.items():
        (destination / name).write_text(json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return {name: artifact["content_sha256"] for name, artifact in artifacts.items()}


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[2]
    output_dir = repository_root / "research/qgen/independent_verification_v1"
    print(json.dumps(write_verification_artifacts(repository_root, output_dir), indent=2, sort_keys=True))
