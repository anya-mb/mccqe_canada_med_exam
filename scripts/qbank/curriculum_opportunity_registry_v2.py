from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from itertools import combinations
from typing import Any, Iterable


class RegistryV2Error(RuntimeError):
    pass


EXPECTED_HEAD = "01eff40984bee76418c7fab82a1ded9fbfa2d9e5"
EXPECTED_HASHES = {
    "CURRICULUM_SNAPSHOT_SHA256": (
        "research/qgen/opportunity_registry/curriculum_input_snapshot_v1.json",
        "70c0875060e8aa5ae8563b70074fa365941b2eb7d4a2a32a2a6ed0fe776817a9",
    ),
    "OPPORTUNITY_REGISTRY_V1_SHA256": (
        "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json",
        "aa465f77c65ba21955e01c3ddf0f32de18022d6a76583bf1ed1da34e62a5e11e",
    ),
    "QUESTION_BANK_ALLOCATION_PLAN_V1_SHA256": (
        "research/qgen/opportunity_registry/question_bank_allocation_plan_v1.json",
        "73fbf8675c9221d98c5fe18edbce4edf7d45b5f451d61a6aeb6a511cd117c50b",
    ),
    "PRODUCTION_QUEUE_V1_SHA256": (
        "research/qgen/opportunity_registry/production_queue_v1.json",
        "7d88f03a109e68a82864f591369081b3098671633dfeadf134c5f1221fca58f3",
    ),
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _load(root: Path, relative: str) -> Any:
    path = Path(root).resolve() / relative
    if not path.is_file():
        raise RegistryV2Error(f"canonical input missing: {relative}")
    return json.loads(path.read_text())


def _verify_self_hash(label: str, artifact: dict[str, Any], expected: str) -> None:
    declared = artifact.get("content_sha256")
    payload = {key: value for key, value in artifact.items() if key != "content_sha256"}
    actual = content_sha256(payload)
    if declared != expected or actual != expected:
        raise RegistryV2Error(
            f"{label} mismatch: expected {expected}, declared {declared}, actual {actual}"
        )


def verify_safe_resume(
    root: Path,
    *,
    checks: Iterable[str] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    requested = tuple(checks or EXPECTED_HASHES)
    result: dict[str, Any] = {}
    for label in requested:
        if label not in EXPECTED_HASHES:
            raise RegistryV2Error(f"unknown safe-resume check: {label}")
        relative, expected = EXPECTED_HASHES[label]
        _verify_self_hash(label, _load(root, relative), expected)
        result[label] = expected

    if checks is not None:
        return result

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RegistryV2Error("cannot verify STARTING_HEAD") from exc
    try:
        ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", EXPECTED_HEAD, head],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RegistryV2Error("cannot verify historical starting-head ancestry") from exc
    if ancestry.returncode != 0:
        raise RegistryV2Error(
            "CURRENT_HEAD_NOT_DESCENDANT_OF_HISTORICAL_STARTING_HEAD: "
            f"historical {EXPECTED_HEAD}, current {head}"
        )

    milestone = _load(root, "reports/curriculum_question_opportunity_registry_v1_milestone.json")
    result.update(
        {
            "STARTING_HEAD": EXPECTED_HEAD,
            "HISTORICAL_STARTING_HEAD": EXPECTED_HEAD,
            "CURRENT_REPOSITORY_HEAD": head,
            "HEAD_DESCENDS_FROM_HISTORICAL_BASELINE": True,
            "TOTAL_IN_SCOPE_STUDY_UNITS": milestone["TOTAL_IN_SCOPE_STUDY_UNITS"],
            "BASE_OPPORTUNITIES": milestone["BASE_OPPORTUNITIES"],
            "HISTORICAL_SAFETY": milestone["HISTORICAL_SAFETY_REGRESSION"],
            "COPYRIGHT": milestone["COPYRIGHT_AUDIT"],
        }
    )
    if result["TOTAL_IN_SCOPE_STUDY_UNITS"] != 1165 or result["BASE_OPPORTUNITIES"] != 1541:
        raise RegistryV2Error("V1 canonical counts do not match the milestone contract")
    if result["HISTORICAL_SAFETY"] != "PASS" or result["COPYRIGHT"] != "PASS":
        raise RegistryV2Error("V1 historical safety or copyright precondition failed")
    return result


def build_v1_comparison_contract(root: Path) -> dict[str, Any]:
    resume = verify_safe_resume(root)
    milestone = _load(root, "reports/curriculum_question_opportunity_registry_v1_milestone.json")
    contract = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V1_IMMUTABLE_COMPARISON_CONTRACT",
        "registry_v1_sha256": resume["OPPORTUNITY_REGISTRY_V1_SHA256"],
        "study_unit_count": milestone["TOTAL_IN_SCOPE_STUDY_UNITS"],
        "opportunity_count": milestone["BASE_OPPORTUNITIES"],
        "family_distribution": dict(sorted(milestone["OPPORTUNITY_FAMILIES"].items())),
        "blueprint_distribution": milestone["BLUEPRINT_COVERAGE"],
        "discipline_capacity": milestone["DISCIPLINE_CAPACITY"],
        "duplicate_metrics": {
            "exact_duplicates_collapsed": milestone["EXACT_DUPLICATES_COLLAPSED"],
            "semantic_near_duplicates_collapsed": milestone["SEMANTIC_NEAR_DUPLICATES_COLLAPSED"],
        },
        "mcq_suitability_metrics": {
            state: milestone["MCQ_SUITABILITY"].get(state, 0)
            for state in ("MCQ_STRONG", "MCQ_ACCEPTABLE", "MCQ_WEAK", "NOT_SUITABLE_FOR_MC")
        },
    }
    contract["content_sha256"] = content_sha256(contract)
    return contract


DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
PRIORITY_ORDER = {"CORE": 0, "HIGH": 1, "STANDARD": 2, "SUPPORTING": 2}
BENCHMARK_FAMILIES = (
    "DIAGNOSIS",
    "DIFFERENTIAL_DIAGNOSIS",
    "RED_FLAG_RECOGNITION",
    "BEST_NEXT_INVESTIGATION",
    "INTERPRET_TEST_RESULT",
    "INITIAL_MANAGEMENT",
    "NEXT_MANAGEMENT_STEP",
    "EMERGENCY_STABILIZATION",
    "COMPLICATION_RECOGNITION",
    "ADVERSE_EFFECT_RECOGNITION",
    "MONITORING",
    "FOLLOW_UP",
    "SCREENING",
    "PREVENTION",
    "COUNSELLING",
    "COMMUNICATION",
    "CAPACITY_CONSENT",
    "CONFIDENTIALITY",
    "PROFESSIONALISM",
    "ETHICAL_LEGAL_ACTION",
    "SYSTEM_ORGANIZATION",
    "EPIDEMIOLOGY_EBM",
)
BENCHMARK_RESPONSE_CLASSES = (
    "DIAGNOSIS",
    "INVESTIGATION",
    "INTERPRETATION",
    "ACTION",
    "PREVENTIVE_ACTION",
    "COMMUNICATION_ACTION",
    "ETHICAL_LEGAL_ACTION",
    "SYSTEM_ACTION",
    "QUANTITATIVE_INTERPRETATION",
)
MATCH_STATES = (
    "EXACT_MATCH",
    "SEMANTIC_MATCH",
    "PARTIAL_MATCH",
    "MISSING_FROM_V1",
    "INVALID_BENCHMARK_OPPORTUNITY",
)
MISS_TAXONOMY = (
    "MISSING_DIAGNOSIS",
    "MISSING_DIFFERENTIAL",
    "MISSING_INVESTIGATION",
    "MISSING_MANAGEMENT",
    "MISSING_EMERGENCY",
    "MISSING_COMPLICATION",
    "MISSING_FOLLOW_UP",
    "MISSING_PREVENTION",
    "MISSING_COUNSELLING",
    "MISSING_COMMUNICATION",
    "MISSING_ETHICAL_LEGAL",
    "MISSING_POPULATION_VARIANT",
    "MISSING_STAGE_VARIANT",
    "MISSING_DISCRIMINATOR_VARIANT",
    "OTHER",
)
OVERGENERATION_TAXONOMY = (
    "COMPOUND",
    "TOO_SPECIALIST",
    "NOT_ATOMIC",
    "COSMETIC_VARIANT",
    "DUPLICATE",
    "NOT_MC_SUITABLE",
    "UNSUPPORTED_BY_SCOPE",
    "KEY_UNCLEAR",
    "OTHER",
)
MCQ_STATES = ("MCQ_STRONG", "MCQ_ACCEPTABLE", "MCQ_WEAK", "NOT_SUITABLE_FOR_MC")
DIMENSIONS_OF_CARE = ("Acute", "Chronic", "Health Promotion & Illness Prevention", "Psychosocial Aspects")
PHYSICIAN_ACTIVITIES = ("Assessment/Diagnosis", "Management", "Communication", "Professional Behaviours")
DUPLICATE_STATES = ("DISTINCT", "RELATED_BUT_DISTINCT", "NEAR_DUPLICATE", "DUPLICATE")


def _stable_rank(study_unit_id: str) -> str:
    return hashlib.sha256(f"completeness-benchmark-v1|{study_unit_id}".encode()).hexdigest()


def _density_stratum(count: int) -> str:
    if count <= 1:
        return "LOW"
    if count == 2:
        return "MEDIUM"
    return "HIGH"


def _structural_stratum(section_path: list[str]) -> str:
    if not section_path:
        return "UNMAPPED"
    first = section_path[0]
    parts = first.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else first


def select_benchmark_roster(root: Path, *, per_discipline: int = 12) -> list[dict[str, Any]]:
    if per_discipline < 1:
        raise RegistryV2Error("per_discipline must be positive")
    snapshot = _load(root, "research/qgen/opportunity_registry/curriculum_input_snapshot_v1.json")
    registry = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    crosswalk = _load(root, "research/scope/master_scope_crosswalk.json")
    opportunity_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry["opportunities"]:
        opportunity_rows[row["study_unit_id"]].append(row)
    crosswalk_by_id = {row["study_unit_id"]: row for row in crosswalk["entries"]}

    candidates: list[dict[str, Any]] = []
    for unit in snapshot["study_units"]:
        rows = opportunity_rows.get(unit["study_unit_id"], [])
        if not unit["eligible"] or not rows:
            continue
        best_priority = min(
            (row["importance"] for row in rows),
            key=lambda value: PRIORITY_ORDER[value],
        )
        priority = "STANDARD" if best_priority == "SUPPORTING" else best_priority
        source = crosswalk_by_id[unit["study_unit_id"]]
        weight = source.get("question_planning", {}).get("coverage_weight", 1)
        candidates.append(
            {
                "study_unit_id": unit["study_unit_id"],
                "study_unit": unit["study_unit"],
                "discipline": unit["discipline"],
                "chapter_code": unit["chapter_code"],
                "priority_stratum": priority,
                "commonness_stratum": "COMMON" if weight >= 4 else "LESS_COMMON",
                "density_stratum": _density_stratum(len(rows)),
                "v1_opportunity_count": len(rows),
                "structural_stratum": _structural_stratum(unit["section_path"]),
                "selection_rank": _stable_rank(unit["study_unit_id"]),
            }
        )

    selected: list[dict[str, Any]] = []
    for discipline in DISCIPLINES:
        pool = [row for row in candidates if row["discipline"] == discipline]
        if len(pool) < per_discipline:
            raise RegistryV2Error(
                f"insufficient eligible units for {discipline}: {len(pool)} < {per_discipline}"
            )
        priority_counts: Counter[str] = Counter()
        density_counts: Counter[str] = Counter()
        commonness_counts: Counter[str] = Counter()
        structure_counts: Counter[str] = Counter()
        chapter_counts: Counter[str] = Counter()
        chosen_ids: set[str] = set()
        while len(chosen_ids) < per_discipline:
            remaining = [row for row in pool if row["study_unit_id"] not in chosen_ids]
            choice = min(
                remaining,
                key=lambda row: (
                    priority_counts[row["priority_stratum"]],
                    density_counts[row["density_stratum"]],
                    commonness_counts[row["commonness_stratum"]],
                    chapter_counts[row["chapter_code"]],
                    structure_counts[row["structural_stratum"]],
                    row["selection_rank"],
                ),
            )
            chosen_ids.add(choice["study_unit_id"])
            priority_counts[choice["priority_stratum"]] += 1
            density_counts[choice["density_stratum"]] += 1
            commonness_counts[choice["commonness_stratum"]] += 1
            chapter_counts[choice["chapter_code"]] += 1
            structure_counts[choice["structural_stratum"]] += 1
            selected.append(choice)
    return sorted(selected, key=lambda row: (DISCIPLINES.index(row["discipline"]), row["selection_rank"]))


def build_blind_benchmark_input(root: Path, roster: list[dict[str, Any]]) -> dict[str, Any]:
    crosswalk = _load(root, "research/scope/master_scope_crosswalk.json")
    objectives = _load(root, "research/mcc/objectives_registry.json")
    crosswalk_by_id = {row["study_unit_id"]: row for row in crosswalk["entries"]}
    objective_by_id = {row["mcc_id"]: row for row in objectives["objectives"] if row.get("mcc_id")}
    rows: list[dict[str, Any]] = []
    for roster_row in roster:
        source = crosswalk_by_id[roster_row["study_unit_id"]]
        mapped_ids = sorted(
            {
                evidence["mcc_id"]
                for evidence in source.get("mcc_evidence", [])
                if evidence.get("mcc_id")
            }
        )
        rows.append(
            {
                "study_unit_id": source["study_unit_id"],
                "study_unit": source["study_unit_title"],
                "discipline": roster_row["discipline"],
                "chapter_code": source["chapter_code"],
                "chapter_title": source["chapter_title"],
                "classification": source["classification"],
                "scope_depth": source["scope_depth"],
                "source_hierarchy_path": source["source_hierarchy_path"],
                "source_node_ids": source["source_node_ids"],
                "structural_rationale": source["structural_rationale"],
                "testable_competencies": source["testable_competencies"],
                "preferred_item_forms": source.get("question_planning", {}).get("preferred_item_forms", []),
                "mcc_mapping_evidence": source.get("mcc_evidence", []),
                "mcc_objectives": [
                    {
                        "mcc_id": objective_by_id[mcc_id]["mcc_id"],
                        "title": objective_by_id[mcc_id]["title"],
                        "role": objective_by_id[mcc_id]["role"],
                        "medical_expert_category": objective_by_id[mcc_id].get("medical_expert_category"),
                        "key_objectives": objective_by_id[mcc_id].get("content", {}).get("key_objectives", ""),
                        "enabling_objectives": objective_by_id[mcc_id].get("content", {}).get("enabling_objectives", ""),
                    }
                    for mcc_id in mapped_ids
                    if mcc_id in objective_by_id
                ],
            }
        )
    packet = {
        "schema_version": "1.0",
        "scope": "INDEPENDENT_COMPLETENESS_BENCHMARK_BLIND_INPUT_V1",
        "blindness_contract": "REGISTRY_V1_OPPORTUNITIES_WITHHELD",
        "reviewer_instruction": (
            "Enumerate every genuinely distinct, atomic learner decision appropriate for a graduating "
            "Canadian medical student. Do not force categories, infer a desired count, or include specialist detail."
        ),
        "study_units": rows,
    }
    packet["content_sha256"] = content_sha256(packet)
    return packet


def _normalized_text(value: str) -> str:
    return " ".join("".join(character.lower() if character.isalnum() else " " for character in value).split())


def benchmark_opportunity_fingerprint(row: dict[str, Any]) -> str:
    identity = {
        "study_unit_id": row.get("study_unit_id", ""),
        "principal_decision": _normalized_text(row.get("principal_decision", "")),
        "decision_code": _normalized_text(row.get("decision_code", "")),
        "opportunity_family": row.get("opportunity_family", ""),
        "response_class": row.get("response_class", ""),
        "clinical_stage": row.get("clinical_stage", ""),
        "population_context": row.get("population_context", ""),
        "primary_reasoning_target": _normalized_text(row.get("primary_reasoning_target", "")),
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_benchmark(
    artifact: dict[str, Any],
    *,
    roster_ids: set[str],
    verify_hash: bool = True,
) -> None:
    if artifact.get("scope") != "INDEPENDENT_OPPORTUNITY_BENCHMARK_V1":
        raise RegistryV2Error("invalid benchmark scope")
    required = {
        "benchmark_opportunity_id",
        "study_unit_id",
        "discipline",
        "principal_decision",
        "decision_code",
        "opportunity_family",
        "response_class",
        "clinical_stage",
        "population_context",
        "primary_reasoning_target",
        "atomicity_verdict",
        "mccqe_level_review",
        "source_anchor_refs",
        "reviewer_rationale",
        "opportunity_fingerprint",
    }
    ids: set[str] = set()
    fingerprints: set[str] = set()
    for index, row in enumerate(artifact.get("opportunities", [])):
        missing = sorted(required - row.keys())
        if missing:
            raise RegistryV2Error(f"benchmark row {index} missing fields: {missing}")
        if row["study_unit_id"] not in roster_ids:
            raise RegistryV2Error(f"benchmark row {index} study unit not in frozen roster")
        if row["discipline"] not in DISCIPLINES:
            raise RegistryV2Error(f"benchmark row {index} has invalid discipline")
        if row["atomicity_verdict"] != "ATOMIC":
            raise RegistryV2Error(f"benchmark row {index} failed atomicity review")
        if row["mccqe_level_review"] != "IN_SCOPE_GENERALIST":
            raise RegistryV2Error(f"benchmark row {index} failed MCCQE level review")
        if row["opportunity_family"] not in BENCHMARK_FAMILIES:
            raise RegistryV2Error(f"benchmark row {index} has uncontrolled opportunity family")
        if row["response_class"] not in BENCHMARK_RESPONSE_CLASSES:
            raise RegistryV2Error(f"benchmark row {index} has uncontrolled response class")
        if not row["principal_decision"].strip() or not row["primary_reasoning_target"].strip():
            raise RegistryV2Error(f"benchmark row {index} has empty semantic content")
        if len(row["source_anchor_refs"]) < 2:
            raise RegistryV2Error(f"benchmark row {index} has insufficient source anchors")
        expected_fingerprint = benchmark_opportunity_fingerprint(row)
        if row["opportunity_fingerprint"] != expected_fingerprint:
            raise RegistryV2Error(f"benchmark row {index} has invalid opportunity fingerprint")
        if row["benchmark_opportunity_id"] in ids:
            raise RegistryV2Error("duplicate benchmark opportunity id")
        if row["opportunity_fingerprint"] in fingerprints:
            raise RegistryV2Error("duplicate opportunity fingerprint")
        ids.add(row["benchmark_opportunity_id"])
        fingerprints.add(row["opportunity_fingerprint"])
    if verify_hash:
        declared = artifact.get("content_sha256")
        actual = content_sha256({key: value for key, value in artifact.items() if key != "content_sha256"})
        if declared != actual:
            raise RegistryV2Error(f"benchmark content hash mismatch: declared {declared}, actual {actual}")


def _audit_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "opportunity_id",
            "discipline",
            "chapter_code",
            "chapter_title",
            "section_path",
            "study_unit_id",
            "study_unit",
            "clinical_topic",
            "key_concept_or_action",
            "learner_decision",
            "clinical_stage",
            "population_context",
            "severity_context",
            "MCC_objective_ids",
            "primary_reasoning_target",
            "primary_discriminator_type",
            "scope_status",
            "importance",
            "source_anchor_refs",
        )
    }


def build_blind_v1_audit_sample(root: Path, *, per_discipline: int = 20) -> dict[str, Any]:
    registry = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    selected: list[dict[str, Any]] = []
    for discipline in DISCIPLINES:
        pool = [row for row in registry["opportunities"] if row["discipline"] == discipline]
        if len(pool) < per_discipline:
            raise RegistryV2Error(f"insufficient V1 opportunities for {discipline} audit")
        family_counts: Counter[str] = Counter()
        priority_counts: Counter[str] = Counter()
        chapter_counts: Counter[str] = Counter()
        unit_counts: Counter[str] = Counter()
        chosen: set[str] = set()
        while len(chosen) < per_discipline:
            choice = min(
                (row for row in pool if row["opportunity_id"] not in chosen),
                key=lambda row: (
                    family_counts[row["opportunity_family"]],
                    priority_counts[row["importance"]],
                    chapter_counts[row["chapter_code"]],
                    unit_counts[row["study_unit_id"]],
                    hashlib.sha256(f"v1-blind-audit|{row['opportunity_id']}".encode()).hexdigest(),
                ),
            )
            chosen.add(choice["opportunity_id"])
            family_counts[choice["opportunity_family"]] += 1
            priority_counts[choice["importance"]] += 1
            chapter_counts[choice["chapter_code"]] += 1
            unit_counts[choice["study_unit_id"]] += 1
            selected.append(_audit_projection(choice))
    packet = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V1_BLIND_SUITABILITY_BLUEPRINT_FAMILY_AUDIT_SAMPLE",
        "blindness_contract": "CURRENT_SUITABILITY_BLUEPRINT_FAMILY_AND_REVIEW_LABELS_WITHHELD",
        "opportunities": selected,
    }
    packet["content_sha256"] = content_sha256(packet)
    return packet


def _pair_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "opportunity_id",
            "discipline",
            "study_unit_id",
            "study_unit",
            "clinical_topic",
            "key_concept_or_action",
            "learner_decision",
            "learner_decision_code",
            "opportunity_family",
            "response_class",
            "clinical_stage",
            "population_context",
            "severity_context",
            "primary_reasoning_target",
            "variant_group_id",
        )
    }


def _pair_likelihood(left: dict[str, Any], right: dict[str, Any]) -> tuple[Any, ...]:
    left_tokens = set(_normalized_text(left["learner_decision"] + " " + left["key_concept_or_action"]).split())
    right_tokens = set(_normalized_text(right["learner_decision"] + " " + right["key_concept_or_action"]).split())
    union = left_tokens | right_tokens
    similarity = len(left_tokens & right_tokens) / len(union) if union else 0.0
    return (
        -(left["variant_group_id"] == right["variant_group_id"]),
        -(left["opportunity_family"] == right["opportunity_family"]),
        -(left["key_concept_or_action"] == right["key_concept_or_action"]),
        -(left["clinical_stage"] == right["clinical_stage"]),
        -(left["population_context"] == right["population_context"]),
        -similarity,
        left["opportunity_id"],
        right["opportunity_id"],
    )


def select_semantic_duplicate_pairs(root: Path, *, minimum_pairs: int = 150) -> dict[str, Any]:
    registry = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry["opportunities"]:
        by_unit[row["study_unit_id"]].append(row)
    candidates: list[tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]] = []
    for rows in by_unit.values():
        for left, right in combinations(sorted(rows, key=lambda row: row["opportunity_id"]), 2):
            candidates.append((_pair_likelihood(left, right), left, right))
    if len(candidates) < minimum_pairs:
        raise RegistryV2Error(f"only {len(candidates)} within-unit semantic-neighbor pairs available")
    selected = sorted(candidates, key=lambda value: value[0])[:minimum_pairs]
    pairs = []
    for _, left, right in selected:
        pair_key = f"{left['opportunity_id']}|{right['opportunity_id']}"
        pairs.append(
            {
                "pair_id": "PAIR-" + hashlib.sha256(pair_key.encode()).hexdigest()[:16].upper(),
                "left": _pair_projection(left),
                "right": _pair_projection(right),
            }
        )
    packet = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V1_SEMANTIC_DUPLICATE_BLIND_STRESS_SAMPLE",
        "blindness_contract": "CURRENT_DUPLICATE_VERDICT_WITHHELD",
        "pairs": pairs,
    }
    packet["content_sha256"] = content_sha256(packet)
    return packet


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def compute_benchmark_metrics(
    benchmark: dict[str, Any],
    registry: dict[str, Any],
    comparison: dict[str, Any],
    *,
    registry_review_key: str = "v1_reviews",
) -> dict[str, Any]:
    benchmark_by_id = {row["benchmark_opportunity_id"]: row for row in benchmark["opportunities"]}
    v1_by_id = {row["opportunity_id"]: row for row in registry["opportunities"]}
    match_states = (
        "EXACT_MATCH",
        "SEMANTIC_MATCH",
        "PARTIAL_MATCH",
        "MISSING_FROM_V1",
        "INVALID_BENCHMARK_OPPORTUNITY",
    )
    match_counts = Counter(row["classification"] for row in comparison["benchmark_reviews"])
    valid_denominator = sum(match_counts[state] for state in match_states[:-1])
    full_matches = match_counts["EXACT_MATCH"] + match_counts["SEMANTIC_MATCH"]
    registry_reviews = comparison[registry_review_key]
    v1_counts = Counter(row["classification"] for row in registry_reviews)
    precision_denominator = sum(v1_counts.values())
    misses = Counter(
        row["miss_taxonomy"]
        for row in comparison["benchmark_reviews"]
        if row["classification"] in {"PARTIAL_MATCH", "MISSING_FROM_V1"} and row.get("miss_taxonomy")
    )
    unit_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry["opportunities"]:
        unit_rows[row["study_unit_id"]].append(row)
    unit_metadata = {
        unit_id: {
            "priority": min(
                ("STANDARD" if row["importance"] == "SUPPORTING" else row["importance"] for row in rows),
                key=lambda value: PRIORITY_ORDER[value],
            ),
            "chapter": rows[0]["chapter_code"],
        }
        for unit_id, rows in unit_rows.items()
    }

    def recall_rollup(field: str) -> dict[str, dict[str, Any]]:
        groups: dict[str, Counter[str]] = defaultdict(Counter)
        for review in comparison["benchmark_reviews"]:
            source = benchmark_by_id[review["benchmark_opportunity_id"]]
            groups[source[field]][review["classification"]] += 1
        return {
            key: {
                "matched": counts["EXACT_MATCH"] + counts["SEMANTIC_MATCH"],
                "valid": sum(counts[state] for state in match_states[:-1]),
                "recall": _ratio(
                    counts["EXACT_MATCH"] + counts["SEMANTIC_MATCH"],
                    sum(counts[state] for state in match_states[:-1]),
                ),
            }
            for key, counts in sorted(groups.items())
        }

    def recall_unit_rollup(field: str) -> dict[str, dict[str, Any]]:
        groups: dict[str, Counter[str]] = defaultdict(Counter)
        for review in comparison["benchmark_reviews"]:
            source = benchmark_by_id[review["benchmark_opportunity_id"]]
            groups[unit_metadata[source["study_unit_id"]][field]][review["classification"]] += 1
        return {
            key: {
                "matched": counts["EXACT_MATCH"] + counts["SEMANTIC_MATCH"],
                "valid": sum(counts[state] for state in match_states[:-1]),
                "recall": _ratio(
                    counts["EXACT_MATCH"] + counts["SEMANTIC_MATCH"],
                    sum(counts[state] for state in match_states[:-1]),
                ),
            }
            for key, counts in sorted(groups.items())
        }

    def precision_rollup(field: str) -> dict[str, dict[str, Any]]:
        groups: dict[str, Counter[str]] = defaultdict(Counter)
        for review in registry_reviews:
            source = v1_by_id[review["opportunity_id"]]
            groups[source[field]][review["classification"]] += 1
        return {
            key: {
                "supported": counts["SUPPORTED_BY_BENCHMARK"],
                "reviewed": sum(counts.values()),
                "precision": _ratio(counts["SUPPORTED_BY_BENCHMARK"], sum(counts.values())),
            }
            for key, counts in sorted(groups.items())
        }

    overgeneration = Counter(row["classification"] for row in registry_reviews)
    over_taxonomy = Counter(
        row["overgeneration_taxonomy"]
        for row in registry_reviews
        if row.get("overgeneration_taxonomy")
    )
    return {
        "match_counts": {state: match_counts[state] for state in match_states},
        "opportunity_recall": _ratio(full_matches, valid_denominator),
        "opportunity_precision": _ratio(v1_counts["SUPPORTED_BY_BENCHMARK"], precision_denominator),
        "recall_by_discipline": recall_rollup("discipline"),
        "recall_by_family": recall_rollup("opportunity_family"),
        "recall_by_priority": recall_unit_rollup("priority"),
        "recall_by_chapter": recall_unit_rollup("chapter"),
        "precision_by_discipline": precision_rollup("discipline"),
        "precision_by_family": precision_rollup("opportunity_family"),
        "precision_by_priority": precision_rollup("importance"),
        "precision_by_chapter": precision_rollup("chapter_code"),
        "missed_opportunity_taxonomy": dict(sorted(misses.items())),
        "v1_overgeneration": {
            "supported": overgeneration["SUPPORTED_BY_BENCHMARK"],
            "overgenerated": overgeneration["OVERGENERATED"],
            "ambiguous": overgeneration["AMBIGUOUS"],
            "taxonomy": dict(sorted(over_taxonomy.items())),
        },
    }


def compute_blueprint_audit(registry: dict[str, Any], reviews: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["opportunity_id"]: row for row in registry["opportunities"]}
    dimension_matrix: dict[str, Counter[str]] = defaultdict(Counter)
    activity_matrix: dict[str, Counter[str]] = defaultdict(Counter)
    dimension_correct = 0
    activity_correct = 0
    for review in reviews:
        original = by_id[review["opportunity_id"]]
        original_dimension = "|".join(original["MCC_dimension_of_care"])
        reviewed_dimension = review["dimension_of_care"]
        original_activity = original["MCC_physician_activity"]
        reviewed_activity = review["physician_activity"]
        dimension_matrix[original_dimension][reviewed_dimension] += 1
        activity_matrix[original_activity][reviewed_activity] += 1
        dimension_correct += reviewed_dimension in original["MCC_dimension_of_care"]
        activity_correct += reviewed_activity == original_activity
    total = len(reviews)
    return {
        "dimension_accuracy": _ratio(dimension_correct, total),
        "activity_accuracy": _ratio(activity_correct, total),
        "dimension_confusion_matrix": {key: dict(sorted(values.items())) for key, values in sorted(dimension_matrix.items())},
        "activity_confusion_matrix": {key: dict(sorted(values.items())) for key, values in sorted(activity_matrix.items())},
    }


def build_benchmark_comparison_input(root: Path, benchmark: dict[str, Any]) -> dict[str, Any]:
    registry = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    unit_ids = {row["study_unit_id"] for row in benchmark["opportunities"]}
    v1_fields = (
        "opportunity_id",
        "discipline",
        "chapter_code",
        "chapter_title",
        "study_unit_id",
        "study_unit",
        "clinical_topic",
        "key_concept_or_action",
        "learner_decision",
        "learner_decision_code",
        "opportunity_family",
        "response_class",
        "clinical_stage",
        "population_context",
        "severity_context",
        "MCC_objective_ids",
        "primary_reasoning_target",
        "primary_discriminator_type",
        "scope_status",
        "importance",
        "source_anchor_refs",
        "variant_group_id",
    )
    packet = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V1_VS_FROZEN_INDEPENDENT_BENCHMARK_REVIEW_INPUT",
        "benchmark_sha256": benchmark["content_sha256"],
        "review_contract": "BENCHMARK_FROZEN_BEFORE_REGISTRY_V1_UNBLINDING",
        "benchmark_opportunities": benchmark["opportunities"],
        "v1_opportunities": [
            {key: row[key] for key in v1_fields}
            for row in registry["opportunities"]
            if row["study_unit_id"] in unit_ids
        ],
    }
    packet["content_sha256"] = content_sha256(packet)
    return packet


def validate_benchmark_comparison(
    comparison: dict[str, Any],
    *,
    benchmark_ids: set[str],
    v1_ids: set[str],
    registry_review_key: str = "v1_reviews",
    matched_registry_ids_key: str = "matched_v1_ids",
) -> None:
    benchmark_reviews = comparison.get("benchmark_reviews", [])
    v1_reviews = comparison.get(registry_review_key, [])
    reviewed_benchmark_ids = [row.get("benchmark_opportunity_id") for row in benchmark_reviews]
    reviewed_v1_ids = [row.get("opportunity_id") for row in v1_reviews]
    if len(reviewed_benchmark_ids) != len(set(reviewed_benchmark_ids)) or set(reviewed_benchmark_ids) != benchmark_ids:
        raise RegistryV2Error("benchmark verdict coverage must be exactly one review per benchmark opportunity")
    if len(reviewed_v1_ids) != len(set(reviewed_v1_ids)) or set(reviewed_v1_ids) != v1_ids:
        raise RegistryV2Error("V1 verdict coverage must be exactly one review per V1 opportunity")

    for row in benchmark_reviews:
        state = row.get("classification")
        matched = row.get(matched_registry_ids_key, [])
        taxonomy = row.get("miss_taxonomy")
        if state not in MATCH_STATES:
            raise RegistryV2Error(f"invalid benchmark match classification: {state}")
        if not set(matched).issubset(v1_ids):
            raise RegistryV2Error("benchmark review references unknown V1 opportunity")
        if state in {"EXACT_MATCH", "SEMANTIC_MATCH"} and not matched:
            raise RegistryV2Error("full benchmark match requires a V1 opportunity")
        if state == "PARTIAL_MATCH" and (not matched or taxonomy not in MISS_TAXONOMY):
            raise RegistryV2Error("partial benchmark match requires a valid miss taxonomy")
        if state == "MISSING_FROM_V1" and (matched or taxonomy not in MISS_TAXONOMY):
            raise RegistryV2Error("missing benchmark opportunity requires a valid miss taxonomy")
        if state == "INVALID_BENCHMARK_OPPORTUNITY" and (matched or taxonomy is not None):
            raise RegistryV2Error("invalid benchmark opportunity cannot match V1 or carry a miss taxonomy")

    for row in v1_reviews:
        state = row.get("classification")
        matched = row.get("matched_benchmark_ids", [])
        taxonomy = row.get("overgeneration_taxonomy")
        if state not in {"SUPPORTED_BY_BENCHMARK", "OVERGENERATED", "AMBIGUOUS"}:
            raise RegistryV2Error(f"invalid V1 support classification: {state}")
        if not set(matched).issubset(benchmark_ids):
            raise RegistryV2Error("V1 review references unknown benchmark opportunity")
        if state == "SUPPORTED_BY_BENCHMARK" and not matched:
            raise RegistryV2Error("supported V1 opportunity requires a benchmark match")
        if state == "OVERGENERATED" and taxonomy not in OVERGENERATION_TAXONOMY:
            raise RegistryV2Error("overgenerated V1 opportunity requires a valid taxonomy")
        if state != "OVERGENERATED" and taxonomy is not None:
            raise RegistryV2Error("non-overgenerated V1 opportunity cannot carry overgeneration taxonomy")


def validate_v1_blind_audit_reviews(reviews: list[dict[str, Any]], *, sample_ids: set[str]) -> None:
    reviewed_ids = [row.get("opportunity_id") for row in reviews]
    if len(reviewed_ids) != len(set(reviewed_ids)) or set(reviewed_ids) != sample_ids:
        raise RegistryV2Error("audit verdict coverage must be exactly one review per sampled opportunity")
    for row in reviews:
        if row.get("mcq_suitability") not in MCQ_STATES:
            raise RegistryV2Error("invalid independent MCQ suitability verdict")
        if row.get("dimension_of_care") not in DIMENSIONS_OF_CARE:
            raise RegistryV2Error("invalid independent Dimension of Care")
        if row.get("physician_activity") not in PHYSICIAN_ACTIVITIES:
            raise RegistryV2Error("invalid independent Physician Activity")
        if row.get("opportunity_family") not in BENCHMARK_FAMILIES:
            raise RegistryV2Error("invalid independent opportunity-family verdict")
        if len(row.get("rationale", "").strip()) < 8:
            raise RegistryV2Error("independent audit rationale is missing")


def summarize_v1_blind_audit(registry: dict[str, Any], reviews: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["opportunity_id"]: row for row in registry["opportunities"]}
    suitability = Counter(row["mcq_suitability"] for row in reviews)
    family_matrix: dict[str, Counter[str]] = defaultdict(Counter)
    family_correct = 0
    for review in reviews:
        current = by_id[review["opportunity_id"]]["opportunity_family"]
        independent = review["opportunity_family"]
        family_matrix[current][independent] += 1
        family_correct += current == independent
    return {
        "mcq_suitability": {state: suitability[state] for state in MCQ_STATES},
        "blueprint": compute_blueprint_audit(registry, reviews),
        "family_accuracy": _ratio(family_correct, len(reviews)),
        "family_confusion_matrix": {
            family: dict(sorted(values.items())) for family, values in sorted(family_matrix.items())
        },
    }


def validate_duplicate_reviews(reviews: list[dict[str, Any]], *, pair_ids: set[str]) -> None:
    reviewed_ids = [row.get("pair_id") for row in reviews]
    if len(reviewed_ids) != len(set(reviewed_ids)) or set(reviewed_ids) != pair_ids:
        raise RegistryV2Error("duplicate-review coverage must be exactly one verdict per sampled pair")
    for row in reviews:
        if row.get("classification") not in DUPLICATE_STATES:
            raise RegistryV2Error("invalid semantic duplicate verdict")
        if len(row.get("rationale", "").strip()) < 8:
            raise RegistryV2Error("semantic duplicate rationale is missing")


def summarize_duplicate_stress_test(reviews: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["classification"] for row in reviews)
    return {
        "pairs_reviewed": len(reviews),
        "distinct": counts["DISTINCT"],
        "related_but_distinct": counts["RELATED_BUT_DISTINCT"],
        "near_duplicate": counts["NEAR_DUPLICATE"],
        "duplicate": counts["DUPLICATE"],
    }


def assess_registry_v1(
    *,
    benchmark_metrics: dict[str, Any],
    audit_summary: dict[str, Any],
    duplicate_summary: dict[str, Any],
) -> dict[str, Any]:
    recall = benchmark_metrics["opportunity_recall"]
    precision = benchmark_metrics["opportunity_precision"]
    major_underenumeration = recall < 0.5
    moderate_underenumeration = 0.5 <= recall < 0.85
    overgeneration = precision < 0.85
    blueprint = audit_summary["blueprint"]
    classification_bias = (
        blueprint["dimension_accuracy"] < 0.85
        or blueprint["activity_accuracy"] < 0.85
        or audit_summary["family_accuracy"] < 0.85
    )
    mcq_suitability_overclaim = (
        audit_summary["mcq_suitability"]["MCQ_WEAK"]
        + audit_summary["mcq_suitability"]["NOT_SUITABLE_FOR_MC"]
        > 0
    )
    semantic_dedupe_gap = duplicate_summary["near_duplicate"] + duplicate_summary["duplicate"] > 0
    issue_count = sum(
        (
            major_underenumeration or moderate_underenumeration,
            overgeneration,
            classification_bias,
            mcq_suitability_overclaim,
            semantic_dedupe_gap,
        )
    )
    if issue_count > 1:
        assessment = "MULTIPLE_ISSUES"
    elif overgeneration:
        assessment = "V1_OVERGENERATES"
    elif classification_bias:
        assessment = "V1_CLASSIFICATION_BIASED"
    elif major_underenumeration:
        assessment = "V1_MAJOR_UNDERENUMERATION"
    elif moderate_underenumeration:
        assessment = "V1_GOOD_BUT_UNDERENUMERATES"
    else:
        assessment = "V1_COMPLETE_ENOUGH"
    return {
        "assessment": assessment,
        "major_underenumeration": major_underenumeration,
        "moderate_underenumeration": moderate_underenumeration,
        "overgeneration": overgeneration,
        "classification_bias": classification_bias,
        "mcq_suitability_overclaim": mcq_suitability_overclaim,
        "semantic_dedupe_gap": semantic_dedupe_gap,
    }


_ACTION_VERBS = (
    "arrange",
    "assess",
    "calculate",
    "choose",
    "communicate",
    "counsel",
    "determine",
    "diagnose",
    "differentiate",
    "evaluate",
    "explain",
    "identify",
    "initiate",
    "interpret",
    "maintain",
    "manage",
    "monitor",
    "obtain",
    "perform",
    "prevent",
    "recommend",
    "recognize",
    "refer",
    "screen",
    "select",
    "stabilize",
    "stage",
    "treat",
    "use",
)
_ACTION_PATTERN = "(?:" + "|".join(_ACTION_VERBS) + ")"


def _family_for_atomic_clause(key: str, clause: str) -> tuple[str, str]:
    probe = clause.lower().replace("_", " ")
    lead_match = re.search(rf"\b({_ACTION_PATTERN})\b", clause, flags=re.IGNORECASE)
    lead_action = lead_match.group(1).lower() if lead_match else ""
    if "confidential" in probe or "privacy" in probe:
        return "CONFIDENTIALITY", "ETHICAL_LEGAL_ACTION"
    if "capacity" in probe or "consent" in probe:
        return "CAPACITY_CONSENT", "ETHICAL_LEGAL_ACTION"
    if any(term in probe for term in ("legal", "mandatory report", "duty to", "ethic")):
        return "ETHICAL_LEGAL_ACTION", "ETHICAL_LEGAL_ACTION"
    if any(term in probe for term in ("communicat", "disclos", "shared decision")):
        return "COMMUNICATION", "COMMUNICATION_ACTION"
    if "counsel" in probe or "anticipatory guidance" in probe:
        return "COUNSELLING", "COMMUNICATION_ACTION"
    if lead_action != "stabilize" and (
        "red flag" in probe or "red-flag" in probe or "warning sign" in probe or "urgency" in probe
    ):
        return "RED_FLAG_RECOGNITION", "DIAGNOSIS"
    if any(term in probe for term in ("stabiliz", "resuscitat", "primary survey", "airway, breathing", "immediate abc")):
        return "EMERGENCY_STABILIZATION", "ACTION"
    if "complication" in probe:
        return "COMPLICATION_RECOGNITION", "DIAGNOSIS"
    if "adverse effect" in probe or "toxicity" in probe:
        return "ADVERSE_EFFECT_RECOGNITION", "DIAGNOSIS"
    if "follow-up" in probe or "follow up" in probe or "followup" in probe:
        return "FOLLOW_UP", "ACTION"
    if "monitor" in probe or "surveillance" in probe:
        return "MONITORING", "ACTION"
    if "screen" in probe:
        return "SCREENING", "PREVENTIVE_ACTION"
    if any(term in probe for term in ("prevent", "risk reduction", "smoking cessation", "immuniz", "vaccin")):
        return "PREVENTION", "PREVENTIVE_ACTION"
    if re.search(r"\binterpret\b", probe) or any(term in probe for term in ("result", "tracing", "image finding")):
        return "INTERPRET_TEST_RESULT", "INTERPRETATION"
    if any(term in probe for term in ("investigat", "workup", "test", "imaging", "radiograph", "ecg", "troponin")):
        return "BEST_NEXT_INVESTIGATION", "INVESTIGATION"
    if any(term in probe for term in ("differentiat", "differential", "distinguish", "classif")):
        return "DIFFERENTIAL_DIAGNOSIS", "DIAGNOSIS"
    if lead_action in {"recognize", "diagnose", "identify"}:
        return "DIAGNOSIS", "DIAGNOSIS"
    if any(term in probe for term in ("diagnos", "recogniz", "identify", "assess", "evaluate")):
        return "DIAGNOSIS", "DIAGNOSIS"
    if any(term in probe for term in ("system", "navigate", "organize", "resource")):
        return "SYSTEM_ORGANIZATION", "SYSTEM_ACTION"
    if any(term in probe for term in ("epidemi", "evidence", "calculate", "risk measure", "bias")):
        return "EPIDEMIOLOGY_EBM", "QUANTITATIVE_INTERPRETATION"
    if any(term in probe for term in ("initiat", "first-line", "initial management", "immediate treatment")):
        return "INITIAL_MANAGEMENT", "ACTION"
    if any(term in probe for term in ("manage", "treat", "refer", "arrange", "recommend", "use", "choose")):
        return "NEXT_MANAGEMENT_STEP", "ACTION"
    return "DIAGNOSIS", "DIAGNOSIS"


def _stage_for_family(family: str, clause: str) -> str:
    probe = clause.lower()
    if family in {"SCREENING", "PREVENTION"}:
        return "PRECLINICAL_OR_PREVENTIVE"
    if family in {"FOLLOW_UP", "MONITORING"}:
        return "FOLLOW_UP"
    if family in {"EMERGENCY_STABILIZATION", "RED_FLAG_RECOGNITION"} or any(
        term in probe for term in ("urgent", "emergency", "unstable")
    ):
        return "EMERGENCY_PRESENTATION"
    if "chronic" in probe or "long-term" in probe:
        return "LONG_TERM_MANAGEMENT"
    return "INITIAL_PRESENTATION"


def _clinical_object(clause: str) -> str:
    value = re.sub(rf"^(?:{_ACTION_PATTERN})\s+", "", clause.strip(), flags=re.IGNORECASE)
    return value.strip(" .")


def _atomic_row(
    *,
    key: str,
    clause: str,
    clinical_object: str | None = None,
    rule_id: str,
    study_unit_id: str | None,
) -> dict[str, Any]:
    family, response = _family_for_atomic_clause(key, clause)
    action_match = re.search(rf"\b({_ACTION_PATTERN})\b", clause, flags=re.IGNORECASE)
    return {
        "study_unit_id": study_unit_id,
        "principal_decision": clause.strip().rstrip(".") + ".",
        "clinical_object": (clinical_object or _clinical_object(clause)).strip(),
        "action_lemma": action_match.group(1).lower() if action_match else "apply",
        "decision_code": _normalized_text(f"{family} {clinical_object or _clinical_object(clause)}").replace(" ", "_"),
        "opportunity_family": family,
        "response_class": response,
        "clinical_stage": _stage_for_family(family, clause),
        "atomicity_verdict": "ATOMIC",
        "enumeration_rule_id": rule_id,
    }


def enumerate_competency_v2(
    key: str,
    text: str,
    *,
    study_unit_id: str | None = None,
) -> list[dict[str, Any]]:
    probe = f"{key} {text}".lower().replace("_", " ")
    if any(term in probe for term in ("rare subspecialty", "operative technique minutiae", "reference only")):
        return []
    if not re.search(rf"\b{_ACTION_PATTERN}\b", text, flags=re.IGNORECASE):
        return []
    if any(term in probe for term in ("terminology", "chapter acronyms")) and not any(
        verb in probe for verb in ("diagnose", "select", "manage", "interpret", "counsel")
    ):
        return []

    list_rows: list[dict[str, Any]] = []
    spans_to_remove: list[tuple[int, int]] = []
    for match in re.finditer(r"\(([^()]*)\)", text):
        inside = match.group(1).strip()
        lowered = inside.lower()
        if lowered.startswith(("e.g.", "eg.", "such as", "including")):
            continue
        items = [item.strip() for item in re.split(r",|\band\b", inside) if item.strip()]
        if not 2 <= len(items) <= 6 or any(len(item.split()) > 8 for item in items):
            continue
        prefix = text[max(0, match.start() - 100):match.start()].strip()
        verb_match = list(re.finditer(rf"\b({_ACTION_PATTERN})\b", prefix, flags=re.IGNORECASE))
        if not verb_match:
            continue
        verb = verb_match[-1].group(1)
        governing = prefix[verb_match[-1].start():].strip(" ,")
        if not any(
            term in f"{key} {governing}".lower()
            for term in ("select", "investig", "screen", "risk factor", "complication", "interpret", "manage", "treat")
        ):
            continue
        for item in items:
            clause = f"{verb.capitalize()} {item} for {governing[len(verb):].strip()}".strip()
            list_rows.append(
                _atomic_row(
                    key=key,
                    clause=clause,
                    clinical_object=item,
                    rule_id="V2_PARALLEL_OBJECT_EXPANSION",
                    study_unit_id=study_unit_id,
                )
            )
        spans_to_remove.append((match.start(), match.end()))

    residual = text
    for start, end in reversed(spans_to_remove):
        residual = residual[:start] + residual[end:]
    split_pattern = re.compile(
        rf"(?:;|,\s*(?=(?:and\s+)?{_ACTION_PATTERN}\b)|\s+and\s+(?={_ACTION_PATTERN}\b))",
        flags=re.IGNORECASE,
    )
    clauses = [re.sub(r"^and\s+", "", part.strip(), flags=re.IGNORECASE) for part in split_pattern.split(residual)]
    rows = list_rows
    for clause in clauses:
        if not clause or not re.search(rf"\b{_ACTION_PATTERN}\b", clause, flags=re.IGNORECASE):
            continue
        # A parent clause replaced by a parallel-object expansion would duplicate its children.
        if spans_to_remove and any(term in f"{key} {clause}".lower() for term in ("investig", "complication")):
            if not re.search(r"\b(counsel|communicat|arrange|refer|monitor|follow)\b", clause, flags=re.IGNORECASE):
                continue
        clause_probe = clause.lower()
        if ("red flag" in clause_probe or "red-flag" in clause_probe) and "stabiliz" in clause_probe:
            rows.append(
                _atomic_row(
                    key=key,
                    clause=clause,
                    clinical_object="red-flag features",
                    rule_id="V2_MULTI_RESPONSE_CLASS_SPLIT",
                    study_unit_id=study_unit_id,
                )
            )
            rows.append(
                _atomic_row(
                    key=key,
                    clause="Stabilize the patient when red-flag features are present",
                    clinical_object="patient with red-flag features",
                    rule_id="V2_MULTI_RESPONSE_CLASS_SPLIT",
                    study_unit_id=study_unit_id,
                )
            )
            continue
        rows.append(
            _atomic_row(
                key=key,
                clause=clause,
                rule_id="V2_EXPLICIT_DECISION_CLAUSE",
                study_unit_id=study_unit_id,
            )
        )

    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        identity = (row["opportunity_family"], row["response_class"], _normalized_text(row["clinical_object"]))
        unique.setdefault(identity, row)
    return list(unique.values())


def _canonical_action(action: str, response_class: str) -> str:
    action = action.lower()
    if response_class == "DIAGNOSIS" and action in {"recognize", "identify", "diagnose", "assess", "evaluate"}:
        return "diagnose"
    if action in {"manage", "treat"}:
        return "manage"
    if action in {"choose", "select"}:
        return "select"
    return action


def _v2_fingerprint(row: dict[str, Any]) -> str:
    identity = {
        "study_unit_id": row["study_unit_id"],
        "family": row["opportunity_family"],
        "response": row["response_class"],
        "action": _canonical_action(row["action_lemma"], row["response_class"]),
        "object": _normalized_text(row["clinical_object"]),
        "stage": row["clinical_stage"],
        "population": row["population_context"],
        "severity": row["severity_context"],
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _merge_v2_rows(kept: dict[str, Any], incoming: dict[str, Any]) -> None:
    for field in (
        "aliases",
        "source_anchor_refs",
        "source_study_unit_ids",
        "source_chapter_refs",
        "source_v1_opportunity_ids",
        "enumeration_rule_ids",
        "validation_item_refs",
    ):
        kept[field] = sorted(set(kept.get(field, [])) | set(incoming.get(field, [])))
    if incoming.get("provenance_type") == "V1_PRESERVED":
        kept["provenance_type"] = "V1_PRESERVED"


def deduplicate_v2_candidates(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    exact: dict[str, dict[str, Any]] = {}
    exact_count = 0
    for row in rows:
        fingerprint = row["opportunity_fingerprint"]
        if fingerprint in exact:
            _merge_v2_rows(exact[fingerprint], row)
            exact_count += 1
        else:
            exact[fingerprint] = dict(row)

    semantic: dict[tuple[str, ...], dict[str, Any]] = {}
    semantic_count = 0
    for row in exact.values():
        key = (
            row["study_unit_id"],
            row["response_class"],
            _canonical_action(row["action_lemma"], row["response_class"]),
            _normalized_text(row["clinical_object"]),
            row["clinical_stage"],
            row["population_context"],
            row["severity_context"],
        )
        if key in semantic:
            _merge_v2_rows(semantic[key], row)
            semantic_count += 1
        else:
            semantic[key] = row
    return sorted(semantic.values(), key=lambda row: row["opportunity_id"]), exact_count, semantic_count


def _dimension_v2(family: str, stage: str) -> list[str]:
    if family in {"SCREENING", "PREVENTION"}:
        return ["Health Promotion & Illness Prevention"]
    if family in {"COMMUNICATION", "COUNSELLING", "CAPACITY_CONSENT", "CONFIDENTIALITY", "PROFESSIONALISM", "ETHICAL_LEGAL_ACTION", "SYSTEM_ORGANIZATION"}:
        return ["Psychosocial Aspects"]
    if family in {"FOLLOW_UP", "MONITORING"} or stage == "LONG_TERM_MANAGEMENT":
        return ["Chronic"]
    return ["Acute"]


def _activity_v2(family: str) -> str:
    if family in {"COMMUNICATION", "COUNSELLING"}:
        return "Communication"
    if family in {"CAPACITY_CONSENT", "CONFIDENTIALITY", "PROFESSIONALISM", "ETHICAL_LEGAL_ACTION", "SYSTEM_ORGANIZATION", "EPIDEMIOLOGY_EBM"}:
        return "Professional Behaviours"
    if family in {"INITIAL_MANAGEMENT", "NEXT_MANAGEMENT_STEP", "EMERGENCY_STABILIZATION", "FOLLOW_UP", "MONITORING", "SCREENING", "PREVENTION"}:
        return "Management"
    return "Assessment/Diagnosis"


def _suitability_v2(key: str, clinical_object: str, family: str) -> tuple[str, str]:
    probe = f"{key} {clinical_object}".lower().replace("_", " ")
    if any(term in probe for term in ("reference only", "chapter acronym", "terminology only")):
        return "NOT_SUITABLE_FOR_MC", "REFERENCE_OR_TERMINOLOGY_NOT_A_DECISION"
    if any(term in probe for term in ("awareness", "overview", "anatomy", "terminology", "vocabulary", "foundational", "physiology")):
        return "MCQ_WEAK", "VAGUE_OR_FOUNDATIONAL_DECISION"
    if any(term in probe for term in ("approach", "framework", "principles", "equity", "barrier")) or family in {
        "COMMUNICATION",
        "COUNSELLING",
        "PROFESSIONALISM",
        "SYSTEM_ORGANIZATION",
    }:
        return "MCQ_ACCEPTABLE", "VALID_BUT_CONTEXT_DEPENDENT_DECISION"
    if len(clinical_object.split()) > 24:
        return "MCQ_ACCEPTABLE", "BROAD_OBJECT_REQUIRES_TIGHT_STEM"
    return "MCQ_STRONG", "CONCRETE_ATOMIC_DECISION"


def _discriminator_for_response(response_class: str) -> str:
    return {
        "DIAGNOSIS": "CLINICAL_FEATURE_PATTERN",
        "INVESTIGATION": "TEST_SELECTION_CONDITION",
        "INTERPRETATION": "RESULT_PATTERN",
        "DATA_INTERPRETATION": "QUANTITATIVE_RELATIONSHIP",
        "ACTION": "CLINICAL_STAGE_AND_SEVERITY",
        "FOLLOW_UP_PLAN": "FOLLOW_UP_TRIGGER_OR_INTERVAL",
        "MONITORING_PLAN": "MONITORING_TRIGGER_OR_INTERVAL",
        "PREVENTIVE_ACTION": "ELIGIBILITY_OR_RISK_PROFILE",
        "COMMUNICATION_ACTION": "PATIENT_CONTEXT_AND_GOAL",
        "ETHICAL_LEGAL_ACTION": "LEGAL_OR_ETHICAL_TRIGGER",
        "SYSTEM_ACTION": "CARE_PATHWAY_CONTEXT",
        "QUANTITATIVE_INTERPRETATION": "QUANTITATIVE_RELATIONSHIP",
    }[response_class]


def _build_v2_row(
    base: dict[str, Any],
    atomic: dict[str, Any],
    *,
    competency_key: str,
    competency_text: str,
    provenance_type: str,
    source_v1_id: str,
    preserved: bool,
) -> dict[str, Any]:
    suitability, suitability_basis = _suitability_v2(
        competency_key, atomic["clinical_object"], atomic["opportunity_family"]
    )
    population = base["population_context"]
    stage = atomic["clinical_stage"]
    row = dict(base)
    row.update(
        {
            "schema_version": "2.0",
            "key_concept_or_action": f"{base['study_unit']} — {atomic['clinical_object']}",
            "learner_decision": atomic["principal_decision"],
            "learner_decision_code": atomic["decision_code"],
            "opportunity_family": atomic["opportunity_family"],
            "response_class": atomic["response_class"],
            "clinical_stage": stage,
            "population_context": population,
            "MCC_dimension_of_care": _dimension_v2(atomic["opportunity_family"], stage),
            "MCC_physician_activity": _activity_v2(atomic["opportunity_family"]),
            "primary_reasoning_target": atomic["principal_decision"],
            "primary_discriminator_type": _discriminator_for_response(atomic["response_class"]),
            "parent_opportunity_family": atomic["opportunity_family"],
            "review_status": "APPROVED" if suitability in {"MCQ_STRONG", "MCQ_ACCEPTABLE"} else "REVISE",
            "review_error_taxonomy": [] if suitability in {"MCQ_STRONG", "MCQ_ACCEPTABLE"} else [suitability_basis],
            "mcq_suitability": suitability,
            "recommended_item_capacity": 0 if suitability in {"MCQ_WEAK", "NOT_SUITABLE_FOR_MC"} else 1,
            "capacity_rationale": ["ONE_ATOMIC_DECISION"] if suitability in {"MCQ_STRONG", "MCQ_ACCEPTABLE"} else ["NO_ALLOCATABLE_MC_CAPACITY"],
            "generation_readiness": (
                "UNSUITABLE_FOR_MC"
                if suitability in {"MCQ_WEAK", "NOT_SUITABLE_FOR_MC"}
                else base["generation_readiness"]
                if preserved
                else "READY_ON_DEMAND_EXPANSION"
                if base["generation_readiness"].startswith("READY_")
                else "NEEDS_EVIDENCE"
            ),
            "clinical_object": atomic["clinical_object"],
            "action_lemma": atomic["action_lemma"],
            "atomicity_verdict": "ATOMIC",
            "provenance_type": provenance_type,
            "source_competency_key": competency_key,
            "source_competency_text": competency_text,
            "source_v1_opportunity_ids": [source_v1_id],
            "enumeration_rule_ids": [atomic["enumeration_rule_id"]],
            "suitability_basis": suitability_basis,
        }
    )
    row["opportunity_fingerprint"] = _v2_fingerprint(row)
    row["opportunity_id"] = "QOP-V2-" + row["opportunity_fingerprint"][:12].upper()
    row["variant_group_id"] = "VG2-" + hashlib.sha256(
        f"{row['study_unit_id']}|{row['response_class']}|{_normalized_text(row['clinical_object'])}".encode()
    ).hexdigest()[:12].upper()
    row["aliases"] = sorted(set(base.get("aliases", [])) | {atomic["principal_decision"]})
    return row


def build_registry_v2(root: Path) -> dict[str, Any]:
    v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    crosswalk = _load(root, "research/scope/master_scope_crosswalk.json")
    source_by_id = {row["study_unit_id"]: row for row in crosswalk["entries"]}
    raw: list[dict[str, Any]] = []
    for base in v1["opportunities"]:
        source = source_by_id[base["study_unit_id"]]
        competency_key = base["learner_decision_code"]
        competency_text = source["testable_competencies"][competency_key]
        atomics = enumerate_competency_v2(
            competency_key, competency_text, study_unit_id=base["study_unit_id"]
        )
        if not atomics:
            action = competency_key.split("_")[0]
            atomics = [
                {
                    "principal_decision": base["learner_decision"],
                    "clinical_object": competency_key.replace("_", " "),
                    "action_lemma": action,
                    "decision_code": competency_key,
                    "opportunity_family": base["opportunity_family"],
                    "response_class": base["response_class"],
                    "clinical_stage": base["clinical_stage"],
                    "atomicity_verdict": "ATOMIC",
                    "enumeration_rule_id": "V1_FALLBACK_NO_EXPLICIT_ATOMIC_SPLIT",
                }
            ]
        preserved_index = next(
            (index for index, atomic in enumerate(atomics) if atomic["opportunity_family"] == base["opportunity_family"]),
            0,
        )
        for index, atomic in enumerate(atomics):
            preserved = index == preserved_index
            if preserved:
                provenance = "V1_PRESERVED"
            elif atomic["opportunity_family"] != base["opportunity_family"]:
                provenance = "V2_NEW_FAMILY"
            elif atomic["clinical_stage"] != base["clinical_stage"]:
                provenance = "V2_STAGE_EXPANSION"
            else:
                provenance = "V2_OTHER"
            raw.append(
                _build_v2_row(
                    base,
                    atomic,
                    competency_key=competency_key,
                    competency_text=competency_text,
                    provenance_type=provenance,
                    source_v1_id=base["opportunity_id"],
                    preserved=preserved,
                )
            )
    rows, exact_collapsed, semantic_collapsed = deduplicate_v2_candidates(raw)
    registry = {
        "schema_version": "2.0",
        "scope": "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V2",
        "v1_registry_sha256": v1["content_sha256"],
        "enumeration_design": "docs/superpowers/specs/2026-09-11-curriculum-opportunity-enumeration-v2-design.md",
        "raw_candidate_count": len(raw),
        "exact_duplicates_collapsed": exact_collapsed,
        "semantic_near_duplicates_collapsed": semantic_collapsed,
        "opportunities": rows,
    }
    registry["content_sha256"] = content_sha256(registry)
    return registry


def _preserved_atomic(base: dict[str, Any]) -> dict[str, Any]:
    """Represent a V1 opportunity without rewriting its semantic decision."""
    action = base["learner_decision_code"].split("_", 1)[0]
    clinical_object = base["key_concept_or_action"].split("—", 1)[-1].strip()
    return {
        "principal_decision": base["learner_decision"],
        "clinical_object": clinical_object,
        "action_lemma": action,
        "decision_code": base["learner_decision_code"],
        "opportunity_family": base["opportunity_family"],
        "response_class": base["response_class"],
        "clinical_stage": base["clinical_stage"],
        "atomicity_verdict": "ATOMIC",
        "enumeration_rule_id": "V1_EXACT_SEMANTIC_PRESERVATION",
    }


def build_registry_v2_final_review_input(root: Path) -> dict[str, Any]:
    """Build a benchmark-blind semantic gate over preserved and proposed decisions."""
    v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    crosswalk = _load(root, "research/scope/master_scope_crosswalk.json")
    source_by_id = {row["study_unit_id"]: row for row in crosswalk["entries"]}
    candidates: list[dict[str, Any]] = []
    proposals: dict[str, dict[str, Any]] = {}

    for base in v1["opportunities"]:
        source = source_by_id[base["study_unit_id"]]
        competency_key = base["learner_decision_code"]
        competency_text = source["testable_competencies"][competency_key]
        preserved = _preserved_atomic(base)
        candidates.append(
            {
                "candidate_id": "PRESERVE-" + base["opportunity_id"],
                "candidate_kind": "V1_PRESERVED",
                "source_v1_opportunity_id": base["opportunity_id"],
                "source_v1_opportunity_ids": [base["opportunity_id"]],
                "discipline": base["discipline"],
                "study_unit_id": base["study_unit_id"],
                "study_unit": base["study_unit"],
                "importance": base["importance"],
                "source_competency_key": competency_key,
                "source_competency_text": competency_text,
                "principal_decision": preserved["principal_decision"],
                "clinical_object": preserved["clinical_object"],
                "proposed_opportunity_family": preserved["opportunity_family"],
                "proposed_response_class": preserved["response_class"],
                "proposed_clinical_stage": preserved["clinical_stage"],
                "proposed_MCC_dimension_of_care": base["MCC_dimension_of_care"],
                "proposed_MCC_physician_activity": base["MCC_physician_activity"],
            }
        )
        for atomic in enumerate_competency_v2(
            competency_key, competency_text, study_unit_id=base["study_unit_id"]
        ):
            identity = {
                "study_unit_id": base["study_unit_id"],
                "competency_key": competency_key,
                "family": atomic["opportunity_family"],
                "response": atomic["response_class"],
                "stage": atomic["clinical_stage"],
                "decision": _normalized_text(atomic["principal_decision"]),
                "object": _normalized_text(atomic["clinical_object"]),
            }
            digest = hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            candidate_id = "PROPOSE-" + digest[:16].upper()
            if candidate_id not in proposals:
                proposals[candidate_id] = {
                    "candidate_id": candidate_id,
                    "candidate_kind": "V2_PROPOSAL",
                    "source_v1_opportunity_id": base["opportunity_id"],
                    "source_v1_opportunity_ids": [base["opportunity_id"]],
                    "discipline": base["discipline"],
                    "study_unit_id": base["study_unit_id"],
                    "study_unit": base["study_unit"],
                    "importance": base["importance"],
                    "source_competency_key": competency_key,
                    "source_competency_text": competency_text,
                    "principal_decision": atomic["principal_decision"],
                    "clinical_object": atomic["clinical_object"],
                    "action_lemma": atomic["action_lemma"],
                    "decision_code": atomic["decision_code"],
                    "enumeration_rule_id": atomic["enumeration_rule_id"],
                    "proposed_opportunity_family": atomic["opportunity_family"],
                    "proposed_response_class": atomic["response_class"],
                    "proposed_clinical_stage": atomic["clinical_stage"],
                    "proposed_MCC_dimension_of_care": _dimension_v2(
                        atomic["opportunity_family"], atomic["clinical_stage"]
                    ),
                    "proposed_MCC_physician_activity": _activity_v2(atomic["opportunity_family"]),
                }
            else:
                proposals[candidate_id]["source_v1_opportunity_ids"] = sorted(
                    set(proposals[candidate_id]["source_v1_opportunity_ids"]) | {base["opportunity_id"]}
                )

    candidates.extend(proposals[key] for key in sorted(proposals))
    packet = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V2_FINAL_SEMANTIC_ADJUDICATION_INPUT",
        "v1_registry_sha256": v1["content_sha256"],
        "instructions": {
            "blindness": "Do not inspect any benchmark, V1/V2 comparison, or prior audit verdict.",
            "v1_policy": "PRESERVE every V1 candidate; independently correct classification and suitability.",
            "proposal_policy": "APPROVE only one atomic, explicit, in-scope MCCQE decision with a clear keyed answer; otherwise REJECT.",
            "quality_policy": "Reject compound, cosmetic, vague, specialist, unsupported, duplicate, or unclear-key proposals.",
        },
        "candidates": candidates,
    }
    packet["content_sha256"] = content_sha256(packet)
    return packet


def validate_registry_v2_final_review(review_input: dict[str, Any], review: dict[str, Any]) -> None:
    if review.get("input_sha256") != review_input.get("content_sha256"):
        raise RegistryV2Error("final review input hash mismatch")
    expected = [row["candidate_id"] for row in review_input.get("candidates", [])]
    actual = [row.get("candidate_id") for row in review.get("decisions", [])]
    if len(actual) != len(expected) or set(actual) != set(expected) or len(set(actual)) != len(actual):
        raise RegistryV2Error("every final-review candidate must be adjudicated exactly once")
    candidate_kind = {row["candidate_id"]: row["candidate_kind"] for row in review_input["candidates"]}
    for row in review["decisions"]:
        allowed_verdicts = {"PRESERVE", "DEFER"} if candidate_kind[row["candidate_id"]] == "V1_PRESERVED" else {"APPROVE", "REJECT"}
        if row.get("verdict") not in allowed_verdicts:
            raise RegistryV2Error("invalid final review verdict")
        required = {
            "opportunity_family",
            "response_class",
            "clinical_stage",
            "MCC_dimension_of_care",
            "MCC_physician_activity",
            "mcq_suitability",
            "rationale_codes",
        }
        if not required.issubset(row):
            raise RegistryV2Error("final review classification is incomplete")
        if not row["opportunity_family"] or not row["response_class"]:
            raise RegistryV2Error("final review classification is invalid")
        if row["mcq_suitability"] not in {"MCQ_STRONG", "MCQ_ACCEPTABLE", "MCQ_WEAK", "NOT_SUITABLE_FOR_MC"}:
            raise RegistryV2Error("final review suitability is invalid")


def build_registry_v2_from_final_review(
    root: Path, review_input: dict[str, Any], review: dict[str, Any]
) -> dict[str, Any]:
    validate_registry_v2_final_review(review_input, review)
    v1 = _load(root, "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json")
    by_v1 = {row["opportunity_id"]: row for row in v1["opportunities"]}
    decisions = {row["candidate_id"]: row for row in review["decisions"]}
    raw: list[dict[str, Any]] = []
    for candidate in review_input["candidates"]:
        decision = decisions[candidate["candidate_id"]]
        if candidate["candidate_kind"] == "V2_PROPOSAL" and decision["verdict"] != "APPROVE":
            continue
        base = by_v1[candidate["source_v1_opportunity_id"]]
        if candidate["candidate_kind"] == "V1_PRESERVED":
            atomic = _preserved_atomic(base)
            provenance = "V1_PRESERVED"
            preserved = True
        else:
            atomic = {
                "principal_decision": candidate["principal_decision"],
                "clinical_object": candidate["clinical_object"],
                "action_lemma": candidate["action_lemma"],
                "decision_code": candidate["decision_code"],
                "opportunity_family": candidate["proposed_opportunity_family"],
                "response_class": candidate["proposed_response_class"],
                "clinical_stage": candidate["proposed_clinical_stage"],
                "enumeration_rule_id": candidate["enumeration_rule_id"],
            }
            provenance = (
                "V2_NEW_FAMILY"
                if atomic["opportunity_family"] != base["opportunity_family"]
                else "V2_STAGE_EXPANSION"
                if atomic["clinical_stage"] != base["clinical_stage"]
                else "V2_OTHER"
            )
            preserved = False
        atomic.update(
            {
                "opportunity_family": decision["opportunity_family"],
                "response_class": decision["response_class"],
                "clinical_stage": decision["clinical_stage"],
            }
        )
        row = _build_v2_row(
            base,
            atomic,
            competency_key=candidate["source_competency_key"],
            competency_text=candidate["source_competency_text"],
            provenance_type=provenance,
            source_v1_id=base["opportunity_id"],
            preserved=preserved,
        )
        row["source_v1_opportunity_ids"] = candidate["source_v1_opportunity_ids"]
        row["MCC_dimension_of_care"] = decision["MCC_dimension_of_care"]
        row["MCC_physician_activity"] = decision["MCC_physician_activity"]
        row["mcq_suitability"] = decision["mcq_suitability"]
        row["suitability_basis"] = decision["rationale_codes"][0]
        allocatable = decision["mcq_suitability"] in {"MCQ_STRONG", "MCQ_ACCEPTABLE"} and decision["verdict"] in {"PRESERVE", "APPROVE"}
        row["recommended_item_capacity"] = (
            base["recommended_item_capacity"] if allocatable and preserved else 1 if allocatable else 0
        )
        row["review_status"] = "APPROVED" if allocatable else "REVISE"
        row["review_error_taxonomy"] = [] if allocatable else decision["rationale_codes"]
        row["capacity_rationale"] = ["INDEPENDENT_SEMANTIC_GATE_APPROVED"] if allocatable else ["NO_ALLOCATABLE_MC_CAPACITY"]
        if preserved:
            row["learner_decision"] = base["learner_decision"]
            row["key_concept_or_action"] = base["key_concept_or_action"]
            row["primary_reasoning_target"] = base["primary_reasoning_target"]
        row["opportunity_fingerprint"] = _v2_fingerprint(row)
        row["opportunity_id"] = "QOP-V2-" + row["opportunity_fingerprint"][:12].upper()
        raw.append(row)
    rows, exact_collapsed, semantic_collapsed = deduplicate_v2_candidates(raw)
    registry = {
        "schema_version": "2.0",
        "scope": "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V2",
        "v1_registry_sha256": v1["content_sha256"],
        "enumeration_design": "docs/superpowers/specs/2026-09-11-curriculum-opportunity-enumeration-v2-design.md",
        "semantic_adjudication_input_sha256": review_input["content_sha256"],
        "semantic_adjudication_sha256": review.get("content_sha256", content_sha256(review)),
        "raw_candidate_count": len(raw),
        "exact_duplicates_collapsed": exact_collapsed,
        "semantic_near_duplicates_collapsed": semantic_collapsed,
        "opportunities": rows,
    }
    registry["content_sha256"] = content_sha256(registry)
    return registry


def validate_registry_v2(registry: dict[str, Any]) -> None:
    if registry.get("scope") != "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V2":
        raise RegistryV2Error("invalid Registry V2 scope")
    ids: set[str] = set()
    fingerprints: set[str] = set()
    allowed_provenance = {
        "V1_PRESERVED",
        "V2_NEW_FAMILY",
        "V2_STAGE_EXPANSION",
        "V2_POPULATION_EXPANSION",
        "V2_OTHER",
    }
    for row in registry.get("opportunities", []):
        if row["opportunity_id"] in ids or row["opportunity_fingerprint"] in fingerprints:
            raise RegistryV2Error("Registry V2 contains duplicate identity")
        if row["provenance_type"] not in allowed_provenance:
            raise RegistryV2Error("Registry V2 contains invalid provenance type")
        if not row["source_competency_text"] or not row["source_v1_opportunity_ids"]:
            raise RegistryV2Error("Registry V2 opportunity lacks canonical provenance")
        if row["mcq_suitability"] in {"MCQ_WEAK", "NOT_SUITABLE_FOR_MC"} and row["recommended_item_capacity"] != 0:
            raise RegistryV2Error("weak or unsuitable opportunity has allocatable capacity")
        if row["opportunity_fingerprint"] != _v2_fingerprint(row):
            raise RegistryV2Error("Registry V2 opportunity fingerprint mismatch")
        ids.add(row["opportunity_id"])
        fingerprints.add(row["opportunity_fingerprint"])
    actual = content_sha256({key: value for key, value in registry.items() if key != "content_sha256"})
    if registry.get("content_sha256") != actual:
        raise RegistryV2Error("Registry V2 content hash mismatch")


def build_v2_benchmark_comparison_input(
    benchmark: dict[str, Any], registry_v2: dict[str, Any]
) -> dict[str, Any]:
    unit_ids = {row["study_unit_id"] for row in benchmark["opportunities"]}
    visible_fields = (
        "opportunity_id",
        "discipline",
        "chapter_code",
        "chapter_title",
        "study_unit_id",
        "study_unit",
        "clinical_object",
        "key_concept_or_action",
        "learner_decision",
        "learner_decision_code",
        "opportunity_family",
        "response_class",
        "clinical_stage",
        "population_context",
        "severity_context",
        "MCC_objective_ids",
        "primary_reasoning_target",
        "primary_discriminator_type",
        "source_competency_key",
        "source_competency_text",
        "source_anchor_refs",
    )
    packet = {
        "schema_version": "1.0",
        "scope": "REGISTRY_V2_VS_FROZEN_INDEPENDENT_BENCHMARK_REVIEW_INPUT",
        "benchmark_sha256": benchmark["content_sha256"],
        "registry_v2_sha256": registry_v2["content_sha256"],
        "review_contract": "NO_RULE_TUNING_DURING_THIS_EVALUATION_PASS",
        "benchmark_opportunities": benchmark["opportunities"],
        "v2_opportunities": [
            {key: row[key] for key in visible_fields}
            for row in registry_v2["opportunities"]
            if row["study_unit_id"] in unit_ids
        ],
    }
    packet["content_sha256"] = content_sha256(packet)
    return packet


def build_v2_operational_artifacts(registry: dict[str, Any]) -> dict[str, Any]:
    """Derive capacity, allocation, and queue from validated quality—not quotas."""
    rows = registry["opportunities"]
    allocatable = [
        row
        for row in rows
        if row["review_status"] == "APPROVED"
        and row["mcq_suitability"] in {"MCQ_STRONG", "MCQ_ACCEPTABLE"}
        and row["recommended_item_capacity"] > 0
    ]
    priority_rank = {"CORE": 0, "HIGH": 1, "STANDARD": 2, "SUPPORTING": 3}
    readiness_rank = {
        state: index
        for index, state in enumerate(
            (
                "READY_EXISTING_BUNDLE",
                "READY_EXISTING_CANDIDATES_NEEDS_SEED",
                "READY_ON_DEMAND_EXPANSION",
                "NEEDS_CANDIDATE_EXPANSION",
                "NEEDS_EVIDENCE",
                "INSUFFICIENT_SAFE_DISTRACTORS",
                "UNSUITABLE_FOR_MC",
                "DEFERRED",
            )
        )
    }
    ordered = sorted(
        allocatable,
        key=lambda row: (
            priority_rank.get(row["importance"], 9),
            0 if row["mcq_suitability"] == "MCQ_STRONG" else 1,
            readiness_rank.get(row["generation_readiness"], 9),
            row["discipline"],
            row["chapter_code"],
            row["study_unit_id"],
            row["opportunity_id"],
        ),
    )
    selected: list[tuple[dict[str, Any], int]] = [(row, 1) for row in ordered]
    for slot_number in (2, 3):
        selected.extend(
            (row, slot_number)
            for row in ordered
            if row["mcq_suitability"] == "MCQ_STRONG"
            and row["importance"] in {"CORE", "HIGH"}
            and row["recommended_item_capacity"] >= slot_number
        )

    proposed_counts = Counter(row["opportunity_id"] for row, _ in selected)
    allocation_rows = []
    for row in sorted(rows, key=lambda item: item["opportunity_id"]):
        count = proposed_counts[row["opportunity_id"]]
        allocation_rows.append(
            {
                "opportunity_id": row["opportunity_id"],
                "discipline": row["discipline"],
                "priority": row["importance"],
                "generation_readiness": row["generation_readiness"],
                "proposed_item_count": count,
                "reason": (
                    "FIRST_PASS_COVERAGE_AND_HIGH_CONFIDENCE_VARIANTS"
                    if count
                    else "UNSUITABLE_DEFERRED_OR_VARIANT_OUTSIDE_RECOMMENDED_TARGET"
                ),
            }
        )
    allocation = {
        "schema_version": "2.0",
        "scope": "QUESTION_BANK_ALLOCATION_PLAN_V2",
        "registry_v2_sha256": registry["content_sha256"],
        "policy": "ALL_ALLOCATABLE_BASE_OPPORTUNITIES_FIRST; ONLY_STRONG_CORE_OR_HIGH_VARIANTS; NO_DISCIPLINE_QUOTAS",
        "rows": allocation_rows,
    }
    allocation["content_sha256"] = content_sha256(allocation)

    queue_entries = []
    discipline_index: Counter[str] = Counter()
    for row, slot_number in selected:
        discipline_index[row["discipline"]] += 1
        supported = row["supported_difficulty_levels"]
        intended = {1: "EASY", 2: "MEDIUM", 3: "HARD"}[slot_number]
        difficulty = intended if intended in supported else ("MEDIUM" if "MEDIUM" in supported else supported[0])
        wave = (
            "WAVE_4"
            if slot_number > 1
            else "WAVE_0"
            if row["generation_readiness"] in {"READY_EXISTING_BUNDLE", "READY_EXISTING_CANDIDATES_NEEDS_SEED"}
            else "WAVE_1"
            if row["importance"] == "CORE"
            else "WAVE_2"
            if row["importance"] == "HIGH"
            else "WAVE_3"
        )
        seed_fingerprint = hashlib.sha256(
            f"{row['opportunity_fingerprint']}|{slot_number}|{difficulty}".encode()
        ).hexdigest()
        queue_entries.append(
            {
                "queue_id": f"PQ2-{row['discipline']}-{discipline_index[row['discipline']]:04d}",
                "discipline": row["discipline"],
                "opportunity_id": row["opportunity_id"],
                "opportunity_fingerprint": row["opportunity_fingerprint"],
                "question_seed_slot_id": f"QSS2-{row['opportunity_id']}-{slot_number}",
                "seed_fingerprint": seed_fingerprint,
                "slot_number": slot_number,
                "difficulty_slot": difficulty,
                "production_wave": wave,
                "priority": row["importance"],
                "generation_readiness": row["generation_readiness"],
                "candidate_dependency": (
                    "EXISTING_VALIDATED_ASSET" if wave == "WAVE_0" else "VALIDATED_ON_DEMAND_CANDIDATE_PIPELINE"
                ),
                "evidence_dependency": (
                    "EXISTING_SOURCE_PACKET"
                    if row["generation_readiness"].startswith("READY_")
                    else "SOURCE_PACKET_REQUIRED"
                ),
            }
        )
    queue = {
        "schema_version": "2.0",
        "scope": "PRODUCTION_QUEUE_V2",
        "registry_v2_sha256": registry["content_sha256"],
        "allocation_v2_sha256": allocation["content_sha256"],
        "entries": queue_entries,
    }
    queue["content_sha256"] = content_sha256(queue)

    capacities: dict[str, Any] = {}
    for discipline in ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO"):
        discipline_rows = [row for row in rows if row["discipline"] == discipline]
        discipline_allocatable = [row for row in allocatable if row["discipline"] == discipline]
        base = len(discipline_rows)
        suitable_base = len(discipline_allocatable)
        total = sum(row["recommended_item_capacity"] for row in discipline_allocatable)
        capacities[discipline] = {
            "study_units": len({row["study_unit_id"] for row in discipline_rows}),
            "base_opportunities": base,
            "mcq_suitable_base_opportunities": suitable_base,
            "legitimate_variant_capacity": total - suitable_base,
            "defensible_item_capacity": total,
        }
    feasibility = {}
    for discipline, values in capacities.items():
        total = values["defensible_item_capacity"]
        feasibility[discipline] = (
            "YES_COMFORTABLY"
            if total >= 1200
            else "YES_WITH_LEGITIMATE_VARIANTS"
            if total >= 1000
            else "POSSIBLE_BUT_DENSITY_RISK"
            if total >= 850
            else "NO_WITHOUT_DUPLICATION"
        )
    dimensions = Counter(value for row in rows for value in row["MCC_dimension_of_care"])
    activities = Counter(row["MCC_physician_activity"] for row in rows)
    return {
        "discipline_capacity": capacities,
        "thousand_question_feasibility": feasibility,
        "bank_capacity": {
            "conservative_floor": sum(row["mcq_suitability"] == "MCQ_STRONG" for row in allocatable),
            "recommended_target": len(selected),
            "upper_defensible_capacity": sum(row["recommended_item_capacity"] for row in allocatable),
        },
        "blueprint": {
            "dimensions_of_care": dict(sorted(dimensions.items())),
            "physician_activities": dict(sorted(activities.items())),
        },
        "allocation": allocation,
        "queue": queue,
    }
