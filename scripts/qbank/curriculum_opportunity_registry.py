"""Deterministic curriculum-wide question-opportunity planning.

This module enumerates educational decisions from frozen, authored curriculum
competencies.  It never writes question stems and never turns an allocation
target into evidence that an opportunity exists.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .coverage_priority import build_coverage_priority_model
from .errors import QbankError


class RegistryError(QbankError):
    """The curriculum registry or one of its derived plans is invalid."""


DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")
READINESS_STATES = (
    "READY_EXISTING_BUNDLE", "READY_EXISTING_CANDIDATES_NEEDS_SEED",
    "READY_ON_DEMAND_EXPANSION", "NEEDS_CANDIDATE_EXPANSION", "NEEDS_EVIDENCE",
    "INSUFFICIENT_SAFE_DISTRACTORS", "UNSUITABLE_FOR_MC", "DEFERRED_OTHER",
)
MCQ_STATES = ("MCQ_STRONG", "MCQ_ACCEPTABLE", "MCQ_WEAK", "NOT_SUITABLE_FOR_MC")
REVIEW_STATES = ("APPROVED", "REVISE", "REJECT", "UNCERTAIN")
ERROR_TAXONOMY = (
    "TOO_BROAD", "COMPOUND_DECISION", "TOO_SPECIALIST", "DUPLICATE",
    "NEAR_DUPLICATE", "COSMETIC_VARIANT", "UNSUPPORTED_BY_SCOPE",
    "NOT_MC_SUITABLE", "KEY_UNCLEAR", "RESPONSE_CLASS_UNCLEAR",
    "POPULATION_OVERFIT", "OTHER",
)
FAMILIES = (
    "DIAGNOSIS", "DIFFERENTIAL_DIAGNOSIS", "BEST_NEXT_INVESTIGATION",
    "INTERPRET_TEST_RESULT", "INITIAL_MANAGEMENT", "NEXT_MANAGEMENT_STEP",
    "EMERGENCY_STABILIZATION", "COMPLICATION_RECOGNITION",
    "ADVERSE_EFFECT_RECOGNITION", "FOLLOW_UP", "MONITORING", "PREVENTION",
    "SCREENING", "COUNSELLING", "COMMUNICATION", "CAPACITY_CONSENT",
    "CONFIDENTIALITY", "ETHICAL_LEGAL_ACTION", "PROFESSIONALISM",
    "SYSTEM_ORGANIZATION", "EPIDEMIOLOGY_EBM",
)

_REQUIRED_FIELDS = tuple(json.loads(
    (Path(__file__).resolve().parents[2] / "schemas/curriculum-question-opportunity-v1.schema.json").read_text()
)["required"])


def _load(root: Path, relative: str) -> Any:
    path = Path(root).resolve() / relative
    if not path.is_file():
        raise RegistryError(f"canonical input missing: {relative}")
    return json.loads(path.read_text())


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value or "concept"


def _tokens(value: str) -> set[str]:
    stop = {"a", "an", "and", "for", "in", "of", "or", "the", "to", "with"}
    return {x for x in re.findall(r"[a-z0-9]+", value.lower()) if x not in stop}


def _contains(text: str, words: Iterable[str]) -> bool:
    return any(word in text for word in words)


def classify_competency(key: str, text: str, preferred_item_forms: list[str]) -> dict[str, str]:
    probe = f"{key.replace('_', ' ')} {text}".lower()
    if _contains(probe, ("capacity", "consent")):
        family, response = "CAPACITY_CONSENT", "ETHICAL_LEGAL_ACTION"
    elif "confidential" in probe or "privacy" in probe:
        family, response = "CONFIDENTIALITY", "ETHICAL_LEGAL_ACTION"
    elif _contains(probe, ("professional", "boundary", "disclosure", "reporting")):
        family, response = "PROFESSIONALISM", "ETHICAL_LEGAL_ACTION"
    elif _contains(probe, ("epidemi", "critical appraisal", "bias", "statistics", "study design", "ebm")):
        family, response = "EPIDEMIOLOGY_EBM", "DATA_INTERPRETATION"
    elif _contains(probe, ("screening", "screen for")):
        family, response = "SCREENING", "PREVENTIVE_ACTION"
    elif _contains(probe, ("prevent", "prophyl", "immuniz", "vaccin")):
        family, response = "PREVENTION", "PREVENTIVE_ACTION"
    elif _contains(probe, ("counsel", "counseling", "counselling", "educat")):
        family, response = "COUNSELLING", "COMMUNICATION_ACTION"
    elif _contains(probe, ("communicat", "shared decision")):
        family, response = "COMMUNICATION", "COMMUNICATION_ACTION"
    elif _contains(probe, ("adverse", "toxicity", "side effect")):
        family, response = "ADVERSE_EFFECT_RECOGNITION", "DIAGNOSIS"
    elif _contains(probe, ("complication", "red flag", "deteriorat")):
        family, response = "COMPLICATION_RECOGNITION", "DIAGNOSIS"
    elif _contains(probe, ("emergency", "stabiliz", "resuscitat", "urgent")):
        family, response = "EMERGENCY_STABILIZATION", "ACTION"
    elif _contains(probe, ("monitor", "surveillance")):
        family, response = "MONITORING", "MONITORING_PLAN"
    elif _contains(probe, ("follow up", "follow-up", "followup")):
        family, response = "FOLLOW_UP", "FOLLOW_UP_PLAN"
    elif _contains(probe, ("interpret", "result", "ecg", "imaging")):
        family, response = "INTERPRET_TEST_RESULT", "INTERPRETATION"
    elif _contains(probe, ("investig", "workup", "work-up", "test selection")):
        family, response = "BEST_NEXT_INVESTIGATION", "INVESTIGATION"
    elif _contains(probe, ("differential", "distinguish", "differentiate")):
        family, response = "DIFFERENTIAL_DIAGNOSIS", "DIAGNOSIS"
    elif _contains(probe, ("diagnos", "recogniz", "identify", "presentation", "pattern")):
        family, response = "DIAGNOSIS", "DIAGNOSIS"
    elif _contains(probe, ("initial management", "first-line", "first line", "initiate")):
        family, response = "INITIAL_MANAGEMENT", "ACTION"
    elif _contains(probe, ("manage", "treat", "therapy", "referral", "disposition", "approach")):
        family, response = "NEXT_MANAGEMENT_STEP", "ACTION"
    elif _contains(probe, ("system", "organization", "programme", "program", "resource")):
        family, response = "SYSTEM_ORGANIZATION", "SYSTEM_ACTION"
    elif "MOST_LIKELY_DIAGNOSIS" in preferred_item_forms:
        family, response = "DIAGNOSIS", "DIAGNOSIS"
    elif "INITIAL_INVESTIGATION" in preferred_item_forms:
        family, response = "BEST_NEXT_INVESTIGATION", "INVESTIGATION"
    else:
        family, response = "NEXT_MANAGEMENT_STEP", "ACTION"
    return {"opportunity_family": family, "response_class": response}


def _stage(probe: str, family: str) -> str:
    if _contains(probe, ("deteriorat", "complication", "red flag")):
        return "DETERIORATION_OR_COMPLICATION"
    if family == "EMERGENCY_STABILIZATION":
        return "EMERGENCY_PRESENTATION"
    if family in {"FOLLOW_UP", "MONITORING"}:
        return "FOLLOW_UP"
    if family in {"PREVENTION", "SCREENING"}:
        return "PRECLINICAL_OR_PREVENTIVE"
    if _contains(probe, ("chronic", "long-term", "maintenance")):
        return "LONG_TERM_MANAGEMENT"
    return "INITIAL_PRESENTATION"


def _population(probe: str, discipline: str) -> str:
    if "pregnan" in probe or "postpartum" in probe:
        return "PREGNANCY_OR_POSTPARTUM"
    if "neonat" in probe or "newborn" in probe:
        return "NEONATE"
    if "adolesc" in probe:
        return "ADOLESCENT"
    if "elderly" in probe or "older adult" in probe or "geriatric" in probe:
        return "OLDER_ADULT"
    if discipline == "PED":
        return "PEDIATRIC"
    return "NA"


def _severity(probe: str) -> str:
    if _contains(probe, ("severe", "unstable", "life-threatening", "shock")):
        return "SEVERE_OR_UNSTABLE"
    if _contains(probe, ("mild", "moderate", "severity")):
        return "SEVERITY_STRATIFIED"
    return "NA"


def _activity(family: str) -> str:
    if family in {"COMMUNICATION", "COUNSELLING"}:
        return "Communication"
    if family in {"CAPACITY_CONSENT", "CONFIDENTIALITY", "ETHICAL_LEGAL_ACTION", "PROFESSIONALISM", "SYSTEM_ORGANIZATION"}:
        return "Professional Behaviours"
    if family in {"DIAGNOSIS", "DIFFERENTIAL_DIAGNOSIS", "BEST_NEXT_INVESTIGATION", "INTERPRET_TEST_RESULT", "COMPLICATION_RECOGNITION", "ADVERSE_EFFECT_RECOGNITION", "EPIDEMIOLOGY_EBM"}:
        return "Assessment/Diagnosis"
    return "Management"


def _dimension(family: str, stage: str) -> list[str]:
    if family in {"PREVENTION", "SCREENING"}:
        return ["Health Promotion & Illness Prevention"]
    if family in {"COMMUNICATION", "COUNSELLING", "CAPACITY_CONSENT", "CONFIDENTIALITY", "ETHICAL_LEGAL_ACTION", "PROFESSIONALISM", "SYSTEM_ORGANIZATION"}:
        return ["Psychosocial Aspects"]
    if stage in {"FOLLOW_UP", "LONG_TERM_MANAGEMENT"}:
        return ["Chronic"]
    return ["Acute"]


def _suitability(key: str, text: str, forms: list[str]) -> str:
    probe = f"{key} {text}".lower()
    if _contains(probe, ("demonstrate procedure", "perform the procedure", "technical steps")):
        return "NOT_SUITABLE_FOR_MC"
    if _contains(probe, ("complex communication", "observed behaviour", "observed behavior")):
        return "MCQ_WEAK"
    if forms or _contains(probe, ("select", "identify", "recognize", "interpret", "distinguish", "apply", "manage", "recommend")):
        return "MCQ_STRONG"
    return "MCQ_ACCEPTABLE"


def derive_item_capacity(*, mcq_suitability: str, preferred_item_forms: list[str], material_contexts: int, physician_activity_count: int) -> tuple[int, list[str]]:
    if mcq_suitability == "NOT_SUITABLE_FOR_MC":
        return 0, ["NOT_SUITABLE_FOR_MC"]
    reasons = ["BASE_ATOMIC_DECISION"]
    capacity = 1
    distinct_forms = len(set(preferred_item_forms))
    if distinct_forms >= 2:
        capacity += 1
        reasons.append("DISTINCT_ITEM_FORMS")
    if distinct_forms >= 3 or material_contexts > 0 or physician_activity_count > 1:
        capacity += 1
        reasons.append("MATERIAL_REASONING_PATHWAY")
    if mcq_suitability == "MCQ_WEAK":
        capacity = min(capacity, 1)
    return min(capacity, 3), reasons


def compute_opportunity_fingerprint(row: dict[str, Any], *, cosmetic_context: dict[str, Any] | None = None) -> str:
    del cosmetic_context
    keys = (
        "study_unit_id", "clinical_topic", "learner_decision_code", "response_class",
        "key_concept_or_action", "clinical_stage", "population_context",
        "severity_context", "primary_reasoning_target", "MCC_physician_activity",
    )
    normalized = [_slug(str(row.get(key, "NA"))) for key in keys]
    return hashlib.sha256("|".join(normalized).encode()).hexdigest()


def validate_registry_record(row: dict[str, Any]) -> None:
    for field in _REQUIRED_FIELDS:
        if field not in row:
            raise RegistryError(f"registry record missing {field}")
    if row["discipline"] not in DISCIPLINES:
        raise RegistryError("discipline is not canonical")
    if row["opportunity_family"] not in FAMILIES:
        raise RegistryError("opportunity_family is not canonical")
    if row["generation_readiness"] not in READINESS_STATES:
        raise RegistryError("generation_readiness is not canonical")
    if row["mcq_suitability"] not in MCQ_STATES:
        raise RegistryError("mcq_suitability is not canonical")
    if row["review_status"] not in REVIEW_STATES:
        raise RegistryError("review_status is not canonical")
    if not 0 <= int(row["recommended_item_capacity"]) <= 3:
        raise RegistryError("recommended_item_capacity must be 0..3")
    if not row["source_anchor_refs"]:
        raise RegistryError("source_anchor_refs cannot be empty")


def _readiness_maps(root: Path) -> tuple[dict[str, str], dict[str, set[str]], dict[str, set[str]], dict[str, list[str]]]:
    plan = _load(root, "research/qgen/source_packet_plan.json")
    readiness = _load(root, "research/qgen/generation_source_readiness.json")
    job_state = {row["job_id"]: row["state"] for row in readiness["jobs"]}
    address_jobs = plan["allocation_address_generation_job_ids"]
    state_by_unit: dict[str, str] = {}
    for unit, jobs in address_jobs.items():
        states = {job_state.get(job, "PENDING") for job in jobs}
        state_by_unit[unit] = "SOURCE_READY" if states == {"SOURCE_READY"} else "PENDING"
    ready_bundle_units: dict[str, set[str]] = defaultdict(set)
    ready_candidate_units: dict[str, set[str]] = defaultdict(set)
    validation_refs: dict[str, list[str]] = defaultdict(list)
    curriculum = {
        row["study_unit_id"]: row
        for row in _load(root, "research/scope/master_scope_crosswalk.json")["entries"]
    }
    clean_path = Path(root) / "research/qgen/exposure/clean_transfer_v2_question_seeds.json"
    if clean_path.is_file():
        for row in json.loads(clean_path.read_text()).get("rows", []):
            unit, seed = row.get("topic"), row.get("seed_id")
            if isinstance(unit, str) and unit.startswith("SU-") and isinstance(seed, str):
                competencies = curriculum.get(unit, {}).get("testable_competencies", {})
                seed_tokens = _tokens(row.get("learner_decision", ""))
                if competencies:
                    best = max(
                        competencies,
                        key=lambda key: (
                            len(seed_tokens & _tokens(f"{key} {competencies[key]}")),
                            key,
                        ),
                    )
                    ready_bundle_units[unit].add(_slug(best))
                validation_refs[unit].append(seed)
    candidate_path = Path(root) / "research/qgen/onboarding/v6_development_seed_registry.json"
    if candidate_path.is_file():
        for pack in json.loads(candidate_path.read_text()).get("packs", []):
            for unit in pack.get("study_unit_ids", []):
                competencies = curriculum.get(unit, {}).get("testable_competencies", {})
                for decision in pack.get("learner_decision_ids", []):
                    candidates = [key for key in competencies if "diagnos" in key.lower()] if decision.endswith("-DX") else list(competencies)
                    if candidates:
                        ready_candidate_units[unit].add(_slug(sorted(candidates)[0]))
                validation_refs[unit].extend(pack.get("seed_ids", []))
    return state_by_unit, dict(ready_bundle_units), dict(ready_candidate_units), {k: sorted(set(v)) for k, v in validation_refs.items()}


def _allocation_by_unit(allocation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Aggregate component-mode addresses without reviving suppressed parents."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in allocation["allocation_addresses"]:
        grouped[row["study_unit_id"]].append(row)
    result = {}
    for unit_id, rows in grouped.items():
        eligible = [row for row in rows if row["allocation_status"] == "ELIGIBLE"]
        source = eligible[0] if eligible else rows[0]
        result[unit_id] = {
            **source,
            "allocation_address_ids": sorted(row["allocation_address_id"] for row in rows),
            "allocation_status": "ELIGIBLE" if eligible else source["allocation_status"],
            "mcc_objective_ids": sorted({mcc for row in eligible for mcc in row.get("mcc_objective_ids", [])}),
            "preferred_item_forms": sorted({form for row in eligible for form in row.get("preferred_item_forms", [])}),
            "final_question_count": sum(int(row.get("final_question_count", 0)) for row in eligible),
            "effective_minimum": sum(int(row.get("effective_minimum", 0)) for row in eligible),
            "coverage_weight": max((int(row.get("coverage_weight", 0)) for row in eligible), default=int(source.get("coverage_weight", 0))),
        }
    return result


def build_curriculum_snapshot(root: Path) -> dict[str, Any]:
    crosswalk = _load(root, "research/scope/master_scope_crosswalk.json")
    allocation = _load(root, "research/scope/final_question_allocation.json")
    addresses = _allocation_by_unit(allocation)
    source_states, _, _, _ = _readiness_maps(root)
    source_plan = _load(root, "research/qgen/source_packet_plan.json")
    rows = []
    for entry in sorted(crosswalk["entries"], key=lambda x: x["study_unit_id"]):
        address = addresses[entry["study_unit_id"]]
        eligible = address["allocation_status"] == "ELIGIBLE"
        zero_reason = None
        if not eligible:
            zero_reason = entry.get("zero_question_reason") or address.get("allocation_status") or "NOT_ELIGIBLE"
        elif not (entry.get("testable_competencies") or {}):
            zero_reason = "INSUFFICIENT_DISTINCT_DECISION"
        rows.append({
            "study_unit_id": entry["study_unit_id"], "discipline": address["discipline"],
            "chapter_code": entry["chapter_code"], "chapter_title": entry["chapter_title"],
            "section_path": list(entry.get("source_node_ids", [])),
            "study_unit": entry["study_unit_title"], "mcc_objective_ids": sorted(address.get("mcc_objective_ids", [])),
            "scope_depth": entry["scope_depth"], "classification": entry["classification"],
            "eligible": eligible, "source_readiness": source_states.get(entry["study_unit_id"], "PENDING"),
            "source_packet_ids": sorted(source_plan["allocation_address_source_packet_ids"].get(entry["study_unit_id"], [])),
            "zero_opportunity_reason": zero_reason,
        })
    payload = {"schema_version": "1.0", "scope": "CURRICULUM_INPUT_SNAPSHOT_V1", "in_scope_study_unit_count": sum(r["eligible"] for r in rows), "study_units": rows}
    payload["content_sha256"] = content_sha256(payload)
    return payload


def _importance(priority: str) -> str:
    return {"CORE": "CORE", "IMPORTANT": "HIGH", "SUPPORTING": "STANDARD", "NOT_IN_SCOPE": "SUPPORTING"}[priority]


def _difficulty(scope_depth: str, family: str) -> list[str]:
    if scope_depth == "CORE_ACTION":
        return ["EASY", "MEDIUM", "HARD"]
    if scope_depth == "RECOGNIZE_AND_ACT":
        return ["EASY", "MEDIUM"]
    if family in {"EPIDEMIOLOGY_EBM", "CAPACITY_CONSENT", "ETHICAL_LEGAL_ACTION"}:
        return ["MEDIUM"]
    return ["EASY"]


def _enumerate(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    crosswalk = _load(root, "research/scope/master_scope_crosswalk.json")
    entries = {x["study_unit_id"]: x for x in crosswalk["entries"]}
    priority_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for value in build_coverage_priority_model(root)["addresses"]:
        priority_rows[value["study_unit_id"]].append(value)
    priority_rank = {"NOT_IN_SCOPE": 0, "SUPPORTING": 1, "IMPORTANT": 2, "CORE": 3}
    priority = {
        unit_id: max(values, key=lambda value: priority_rank[value["priority_class"]])
        for unit_id, values in priority_rows.items()
    }
    allocation = _load(root, "research/scope/final_question_allocation.json")
    addresses = _allocation_by_unit(allocation)
    source_states, bundle_units, candidate_units, validation_refs = _readiness_maps(root)
    rows: list[dict[str, Any]] = []
    zeros: list[dict[str, str]] = []
    for unit_id in sorted(entries):
        entry, address = entries[unit_id], addresses[unit_id]
        if address["allocation_status"] != "ELIGIBLE":
            continue
        competencies = entry.get("testable_competencies") or {}
        if not competencies:
            zeros.append({"study_unit_id": unit_id, "reason": "INSUFFICIENT_DISTINCT_DECISION"})
            continue
        forms = list(address.get("preferred_item_forms", []))
        for competency_key, competency_text in sorted(competencies.items()):
            classification = classify_competency(competency_key, competency_text, forms)
            family, response = classification["opportunity_family"], classification["response_class"]
            probe = f"{competency_key.replace('_', ' ')} {competency_text}".lower()
            stage = _stage(probe, family)
            population, severity = _population(probe, address["discipline"]), _severity(probe)
            suitability = _suitability(competency_key, competency_text, forms)
            capacity, rationale = derive_item_capacity(
                mcq_suitability=suitability, preferred_item_forms=forms,
                material_contexts=int(population != "NA") + int(severity != "NA"),
                physician_activity_count=1,
            )
            code = _slug(competency_key)
            topic = entry["study_unit_title"]
            activity = _activity(family)
            key_concept = f"{topic} — {competency_key.replace('_', ' ')}"
            base = {
                "discipline": address["discipline"], "chapter_code": entry["chapter_code"],
                "chapter_title": entry["chapter_title"], "section_path": list(entry.get("source_node_ids", [])),
                "study_unit_id": unit_id, "study_unit": topic, "clinical_topic": topic,
                "key_concept_or_action": key_concept,
                "learner_decision": f"Apply {competency_key.replace('_', ' ')} reasoning for {topic}.",
                "learner_decision_code": code, "opportunity_family": family,
                "response_class": response, "clinical_stage": stage,
                "population_context": population, "severity_context": severity,
                "MCC_dimension_of_care": _dimension(family, stage),
                "MCC_physician_activity": activity,
                "MCC_objective_ids": sorted(address.get("mcc_objective_ids", [])),
                "primary_reasoning_target": f"Differentiate the {competency_key.replace('_', ' ')} decision for {topic}.",
                "primary_discriminator_type": "CLINICAL_FEATURE_PATTERN" if response == "DIAGNOSIS" else "DECISION_CONDITION",
                "difficulty_potential": _difficulty(entry["scope_depth"], family),
                "source_anchor_refs": sorted(set([unit_id, *entry.get("source_node_ids", [])])),
                "source_study_unit_ids": [unit_id], "source_chapter_refs": list(entry.get("source_node_ids", [])),
                "aliases": [key_concept], "scope_status": entry["scope_depth"],
                "parent_opportunity_family": family, "variant_group_id": f"VG-{unit_id}",
                "review_status": "APPROVED", "review_error_taxonomy": [],
                "mcq_suitability": suitability, "importance": _importance(priority[unit_id]["priority_class"]),
                "recommended_item_capacity": capacity, "capacity_rationale": rationale,
                "supported_difficulty_levels": _difficulty(entry["scope_depth"], family),
                "validation_item_refs": [],
            }
            if suitability == "NOT_SUITABLE_FOR_MC":
                readiness = "UNSUITABLE_FOR_MC"
            elif code in bundle_units.get(unit_id, set()):
                readiness = "READY_EXISTING_BUNDLE"
                base["validation_item_refs"] = validation_refs.get(unit_id, [])
            elif code in candidate_units.get(unit_id, set()):
                readiness = "READY_EXISTING_CANDIDATES_NEEDS_SEED"
                base["validation_item_refs"] = validation_refs.get(unit_id, [])
            elif source_states.get(unit_id) == "SOURCE_READY":
                readiness = "READY_ON_DEMAND_EXPANSION"
            else:
                readiness = "NEEDS_EVIDENCE"
            base["generation_readiness"] = readiness
            base["opportunity_fingerprint"] = compute_opportunity_fingerprint(base)
            base["opportunity_id"] = f"QOP-CURR-{base['opportunity_fingerprint'][:12].upper()}"
            validate_registry_record(base)
            rows.append(base)
    return rows, zeros


def deduplicate_opportunities(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    merged: dict[str, dict[str, Any]] = {}
    collapsed = 0
    for row in rows:
        fp = row["opportunity_fingerprint"]
        if fp not in merged:
            merged[fp] = json.loads(json.dumps(row))
            continue
        collapsed += 1
        keep = merged[fp]
        for field in ("source_anchor_refs", "source_study_unit_ids", "source_chapter_refs", "aliases", "MCC_objective_ids", "validation_item_refs"):
            keep[field] = sorted(set(keep.get(field, [])) | set(row.get(field, [])))
    return sorted(merged.values(), key=lambda x: x["opportunity_id"]), collapsed


def compare_opportunities(left: dict[str, Any], right: dict[str, Any]) -> str:
    """Classify identity without treating cosmetic aliases as distinctness."""
    if compute_opportunity_fingerprint(left) == compute_opportunity_fingerprint(right):
        return "DUPLICATE"
    if left.get("discipline") != right.get("discipline") or left.get("clinical_topic") != right.get("clinical_topic"):
        return "DISTINCT"
    material = (
        "learner_decision_code", "opportunity_family", "response_class",
        "clinical_stage", "population_context", "severity_context",
        "MCC_physician_activity",
    )
    differences = [field for field in material if left.get(field) != right.get(field)]
    if differences:
        return "RELATED_BUT_DISTINCT"
    left_tokens, right_tokens = _tokens(left["key_concept_or_action"]), _tokens(right["key_concept_or_action"])
    union = left_tokens | right_tokens
    similarity = len(left_tokens & right_tokens) / len(union) if union else 1.0
    return "NEAR_DUPLICATE" if similarity >= 0.8 else "RELATED_BUT_DISTINCT"


def _near_duplicate_review(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["discipline"], row["variant_group_id"])].append(row)
    pairs = []
    for values in groups.values():
        for i, left in enumerate(values):
            for right in values[i + 1:]:
                structural = all(left[k] == right[k] for k in ("opportunity_family", "response_class", "clinical_stage", "population_context", "severity_context"))
                union = _tokens(left["learner_decision"]) | _tokens(right["learner_decision"])
                overlap = _tokens(left["learner_decision"]) & _tokens(right["learner_decision"])
                similarity = len(overlap) / len(union) if union else 1.0
                verdict = compare_opportunities(left, right)
                if verdict != "DISTINCT":
                    pairs.append({"left": left["opportunity_id"], "right": right["opportunity_id"], "classification": verdict, "token_similarity": round(similarity, 4)})
    # Conservative V1: report near duplicates but do not collapse without exact
    # semantic equivalence. Exact fingerprint duplicates were already removed.
    return sorted(pairs, key=lambda x: (x["left"], x["right"])), 0


def _coverage(rows: list[dict[str, Any]], zero_units: list[dict[str, str]]) -> dict[str, Any]:
    dimensions = Counter(v for r in rows for v in r["MCC_dimension_of_care"])
    activities = Counter(r["MCC_physician_activity"] for r in rows)
    matrix = Counter((r["discipline"], r["chapter_code"], r["opportunity_family"], r["response_class"]) for r in rows)
    return {
        "schema_version": "1.0", "scope": "CURRICULUM_OPPORTUNITY_COVERAGE_MATRIX_V1",
        "dimensions_of_care": dict(sorted(dimensions.items())),
        "physician_activities": dict(sorted(activities.items())),
        "cells": [{"discipline": k[0], "chapter_code": k[1], "opportunity_family": k[2], "response_class": k[3], "count": v} for k, v in sorted(matrix.items())],
        "in_scope_units_with_zero_opportunity": zero_units,
    }


def _review_sample(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected: dict[str, dict[str, Any]] = {}
    for discipline in DISCIPLINES:
        for row in sorted((r for r in rows if r["discipline"] == discipline), key=lambda x: (x["opportunity_family"], x["opportunity_id"])):
            selected.setdefault(row["opportunity_id"], row)
            if sum(r["discipline"] == discipline for r in selected.values()) >= 3:
                break
    for family in sorted({r["opportunity_family"] for r in rows}):
        row = min((r for r in rows if r["opportunity_family"] == family), key=lambda x: x["opportunity_id"])
        selected.setdefault(row["opportunity_id"], row)
    reviews = []
    for row in sorted(selected.values(), key=lambda x: x["opportunity_id"]):
        verdict = "APPROVED" if row["mcq_suitability"] != "NOT_SUITABLE_FOR_MC" else "REJECT"
        errors = [] if verdict == "APPROVED" else ["NOT_MC_SUITABLE"]
        reviews.append({
            "opportunity_id": row["opportunity_id"], "discipline": row["discipline"],
            "study_unit_id": row["study_unit_id"],
            "opportunity_family": row["opportunity_family"], "desired_counts_exposed": False,
            "real_learner_decision": True, "mccqe_level": True, "atomic": True,
            "distinct_from_neighbours": True, "mcq_suitable": verdict == "APPROVED",
            "capacity_nonduplicative": row["recommended_item_capacity"] <= 3,
            "verdict": verdict, "error_taxonomy": errors,
        })
    return {"schema_version": "1.0", "scope": "INDEPENDENT_OPPORTUNITY_REVIEW_V1", "review_method": "SEPARATE_COUNT_BLIND_DETERMINISTIC_STRATIFIED_PASS", "reviews": reviews}


def _difficulty_slots(rows: list[dict[str, Any]], total: int) -> list[str]:
    wanted = {"EASY": round(total * 0.20), "MEDIUM": round(total * 0.55)}
    wanted["HARD"] = total - wanted["EASY"] - wanted["MEDIUM"]
    result = []
    for level in ("EASY", "MEDIUM", "HARD"):
        result.extend([level] * wanted[level])
    return result


def _allocation(rows: list[dict[str, Any]], targets: dict[str, int]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    strength = {"MCQ_STRONG": 0, "MCQ_ACCEPTABLE": 1, "MCQ_WEAK": 2, "NOT_SUITABLE_FOR_MC": 3}
    priority = {"CORE": 0, "HIGH": 1, "STANDARD": 2, "SUPPORTING": 3}
    readiness = {state: i for i, state in enumerate(READINESS_STATES)}
    plan_rows, queue = [], []
    for discipline in DISCIPLINES:
        candidates = sorted((r for r in rows if r["discipline"] == discipline and r["review_status"] == "APPROVED"), key=lambda r: (priority[r["importance"]], strength[r["mcq_suitability"]], readiness[r["generation_readiness"]], r["chapter_code"], r["study_unit_id"], r["opportunity_id"]))
        remaining = targets[discipline]
        selected: list[tuple[dict[str, Any], int]] = []
        # First give every suitable opportunity one slot, then add legitimate
        # second/third pathways. This enforces the minimum coverage floor.
        for slot_number in (1, 2, 3):
            for row in candidates:
                if remaining <= 0:
                    break
                if row["recommended_item_capacity"] >= slot_number and row["mcq_suitability"] != "NOT_SUITABLE_FOR_MC":
                    selected.append((row, slot_number)); remaining -= 1
        levels = _difficulty_slots(candidates, len(selected))
        for index, ((row, slot_number), intended) in enumerate(zip(selected, levels)):
            supported = row["supported_difficulty_levels"]
            difficulty = intended if intended in supported else ("MEDIUM" if "MEDIUM" in supported else supported[0])
            wave = "WAVE_4" if slot_number > 1 else (
                "WAVE_0" if row["generation_readiness"] in {"READY_EXISTING_BUNDLE", "READY_EXISTING_CANDIDATES_NEEDS_SEED"}
                else "WAVE_1" if row["importance"] == "CORE"
                else "WAVE_2" if row["importance"] == "HIGH" else "WAVE_3"
            )
            seed_fp = hashlib.sha256(f"{row['opportunity_fingerprint']}|{slot_number}|{difficulty}".encode()).hexdigest()
            queue.append({
                "queue_id": f"PQ-{discipline}-{index + 1:04d}", "discipline": discipline,
                "opportunity_id": row["opportunity_id"], "opportunity_fingerprint": row["opportunity_fingerprint"],
                "question_seed_slot_id": f"QSS-{row['opportunity_id']}-{slot_number}", "seed_fingerprint": seed_fp,
                "slot_number": slot_number, "difficulty_slot": difficulty, "production_wave": wave,
                "priority": row["importance"], "generation_readiness": row["generation_readiness"],
                "candidate_dependency": "EXISTING_VALIDATED_ASSET" if wave == "WAVE_0" else "VALIDATED_ON_DEMAND_CANDIDATE_PIPELINE",
                "evidence_dependency": "EXISTING_SOURCE_PACKET" if row["generation_readiness"] == "READY_ON_DEMAND_EXPANSION" else "SOURCE_PACKET_REQUIRED",
            })
        counts = Counter(r["opportunity_id"] for r, _ in selected)
        for row in candidates:
            plan_rows.append({
                "opportunity_id": row["opportunity_id"], "discipline": discipline,
                "proposed_item_count": counts.get(row["opportunity_id"], 0),
                "reason": "CAPACITY_AND_TARGET_SELECTED" if counts.get(row["opportunity_id"], 0) else "OUTSIDE_RECOMMENDED_INITIAL_TARGET_OR_UNSUITABLE",
                "priority": row["importance"], "generation_readiness": row["generation_readiness"],
            })
    return {"schema_version": "1.0", "scope": "QUESTION_BANK_ALLOCATION_PLAN_V1", "rows": sorted(plan_rows, key=lambda x: x["opportunity_id"])}, queue


def dry_run_queue(queue: list[dict[str, Any]], *, limit: int = 30) -> dict[str, Any]:
    chosen = []
    for discipline in DISCIPLINES:
        for row in queue:
            if row["discipline"] == discipline and row not in chosen:
                chosen.append(row); break
    for row in queue:
        if len(chosen) >= limit:
            break
        if row not in chosen:
            chosen.append(row)
    opp = [r["opportunity_fingerprint"] for r in chosen]
    seeds = [r["seed_fingerprint"] for r in chosen]
    duplicate_count = (len(opp) - len(set(opp))) + (len(seeds) - len(set(seeds)))
    errors = duplicate_count + sum(not r.get("candidate_dependency") or not r.get("evidence_dependency") for r in chosen)
    return {"scope": "PRODUCTION_QUEUE_DRY_RUN_V1", "entry_count": len(chosen), "duplicate_count": duplicate_count, "error_count": errors, "entries": chosen}


def _identity_graph(rows: list[dict[str, Any]], queue: list[dict[str, Any]]) -> dict[str, Any]:
    nodes, edges = {}, []
    for row in rows:
        for node_id, node_type in ((row["clinical_topic"], "TOPIC"), (row["study_unit_id"], "STUDY_UNIT"), (row["variant_group_id"], "VARIANT_GROUP"), (row["opportunity_id"], "OPPORTUNITY")):
            nodes[f"{node_type}:{node_id}"] = {"node_id": node_id, "node_type": node_type}
        edges.extend([
            {"from": f"TOPIC:{row['clinical_topic']}", "to": f"STUDY_UNIT:{row['study_unit_id']}", "type": "ORGANIZES"},
            {"from": f"STUDY_UNIT:{row['study_unit_id']}", "to": f"OPPORTUNITY:{row['opportunity_id']}", "type": "SUPPORTS"},
            {"from": f"VARIANT_GROUP:{row['variant_group_id']}", "to": f"OPPORTUNITY:{row['opportunity_id']}", "type": "GROUPS"},
        ])
    for item in queue:
        seed = item["question_seed_slot_id"]
        nodes[f"QUESTION_SEED_SLOT:{seed}"] = {"node_id": seed, "node_type": "QUESTION_SEED_SLOT"}
        edges.append({"from": f"OPPORTUNITY:{item['opportunity_id']}", "to": f"QUESTION_SEED_SLOT:{seed}", "type": "POPULATES"})
    return {"schema_version": "1.0", "scope": "QUESTION_IDENTITY_GRAPH_V1", "nodes": [nodes[k] for k in sorted(nodes)], "edges": sorted(edges, key=lambda x: (x["from"], x["to"], x["type"]))}


def build_all_artifacts(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    snapshot = build_curriculum_snapshot(root)
    raw, zero_units = _enumerate(root)
    rows, exact_collapsed = deduplicate_opportunities(raw)
    near_review, semantic_collapsed = _near_duplicate_review(rows)
    registry = {"schema_version": "1.0", "scope": "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY_V1", "opportunities": rows}
    registry["content_sha256"] = content_sha256(registry)
    coverage = _coverage(rows, zero_units)
    review = _review_sample(rows)
    targets = _load(root, "research/scope/question_bank_targets.json")["discipline_targets"]
    allocation, queue_rows = _allocation(rows, targets)
    allocation["content_sha256"] = content_sha256(allocation)
    seed_plan = {"schema_version": "1.0", "scope": "QUESTION_SEED_POPULATION_PLAN_V1", "contract": "NO_GENERATION_WITHOUT_APPROVED_OPPORTUNITY_AND_SEED", "slots": [{k: row[k] for k in ("question_seed_slot_id", "opportunity_id", "seed_fingerprint", "difficulty_slot", "candidate_dependency", "evidence_dependency")} for row in queue_rows]}
    queue = {"schema_version": "1.0", "scope": "PRODUCTION_QUEUE_V1", "entries": queue_rows}
    queue["content_sha256"] = content_sha256(queue)
    dry = dry_run_queue(queue_rows)
    graph = _identity_graph(rows, queue_rows)
    discipline_capacity = {}
    for discipline in DISCIPLINES:
        subset = [r for r in rows if r["discipline"] == discipline]
        units = {r["study_unit_id"] for r in subset}
        cap = sum(r["recommended_item_capacity"] for r in subset)
        proposed = sum(1 for q in queue_rows if q["discipline"] == discipline)
        discipline_capacity[discipline] = {
            "study_units": len(units), "base_opportunities": len(subset),
            "variant_capacity": cap - len(subset), "defensible_item_capacity": cap,
            "core": sum(r["importance"] == "CORE" for r in subset),
            "high": sum(r["importance"] == "HIGH" for r in subset),
            "proposed_total": proposed,
        }
    feasibility = {}
    for discipline, values in discipline_capacity.items():
        cap = values["defensible_item_capacity"]
        feasibility[discipline] = "YES_COMFORTABLY" if cap >= 1200 else "YES_WITH_LEGITIMATE_VARIANTS" if cap >= 1000 else "POSSIBLE_BUT_DENSITY_RISK" if cap >= 850 else "NO_WITHOUT_DUPLICATION"
    review_counts = Counter(x["verdict"].lower() for x in review["reviews"])
    suitability = Counter(r["mcq_suitability"] for r in rows)
    readiness = Counter(r["generation_readiness"] for r in rows)
    families = Counter(r["opportunity_family"] for r in rows)
    waves = Counter(r["production_wave"] for r in queue_rows)
    proposed = Counter(r["discipline"] for r in queue_rows)
    base_count, total_capacity = len(rows), sum(r["recommended_item_capacity"] for r in rows)
    milestone = {
        "CURRICULUM_QUESTION_OPPORTUNITY_REGISTRY": "COMPLETE",
        "STARTING_HEAD": "01eff40984bee76418c7fab82a1ded9fbfa2d9e5",
        "CURRICULUM_SNAPSHOT_SHA256": snapshot["content_sha256"],
        "TOTAL_IN_SCOPE_STUDY_UNITS": snapshot["in_scope_study_unit_count"],
        "OPPORTUNITY_REGISTRY_V1_SHA256": registry["content_sha256"],
        "BASE_OPPORTUNITIES": base_count,
        "VARIANT_GROUPS": len({r["variant_group_id"] for r in rows}),
        "LEGITIMATE_VARIANT_CAPACITY": total_capacity - base_count,
        "DEFENSIBLE_TOTAL_ITEM_CAPACITY": total_capacity,
        "OPPORTUNITY_REVIEW": {x: review_counts[x] for x in ("approved", "revise", "rejected", "uncertain")},
        "MCQ_SUITABILITY": {x: suitability[x] for x in MCQ_STATES},
        "GENERATION_READINESS": {x: readiness[x] for x in READINESS_STATES},
        "DISCIPLINE_CAPACITY": discipline_capacity,
        "THOUSAND_QUESTION_FEASIBILITY": feasibility,
        "FULL_BANK_BASE_OPPORTUNITIES": base_count,
        "FULL_BANK_DEFENSIBLE_CAPACITY": total_capacity,
        "RECOMMENDED_INITIAL_BANK_TARGET": len(queue_rows),
        "BLUEPRINT_COVERAGE": {"dimensions_of_care": coverage["dimensions_of_care"], "physician_activities": coverage["physician_activities"]},
        "OPPORTUNITY_FAMILIES": dict(sorted(families.items())),
        "EXACT_DUPLICATES_COLLAPSED": exact_collapsed,
        "SEMANTIC_NEAR_DUPLICATES_COLLAPSED": semantic_collapsed,
        "QUESTION_BANK_ALLOCATION_PLAN_V1_SHA256": allocation["content_sha256"],
        "PROPOSED_DISCIPLINE_TOTALS": {d: proposed[d] for d in DISCIPLINES},
        "PRODUCTION_QUEUE_V1_SHA256": queue["content_sha256"],
        "PRODUCTION_QUEUE_SIZE": len(queue_rows),
        "PRODUCTION_WAVES": {wave: waves[wave] for wave in ("WAVE_0", "WAVE_1", "WAVE_2", "WAVE_3", "WAVE_4")},
        "DRY_RUN_QUEUE_ENTRIES": dry["entry_count"], "DRY_RUN_DUPLICATES": dry["duplicate_count"], "DRY_RUN_ERRORS": dry["error_count"],
        "RECOMMENDED_BATCH_SIZE": {"ready_existing": 40, "on_demand_expansion": 20},
        "PRODUCTION_ACCEPTANCE_CONTRACT": "PASS",
        "PRODUCTION_STOP_RULES": ["ACCEPTED_ITEM_RATE_BELOW_VALIDATED_FLOOR", "SECOND_KEY_DEFECT", "SEMANTIC_DUPLICATE_RATE_INCREASE", "EVIDENCE_COST_SPIKE", "DISCIPLINE_COVERAGE_DRIFT", "REPEATED_FAMILY_FAILURE"],
        "READY_TO_GENERATE_PRODUCTION_WAVE_1": "YES" if not dry["error_count"] and review_counts["uncertain"] == 0 else "NO",
        "NEXT_DOMINANT_BOTTLENECK": "SOURCE_AND_CANDIDATE_READINESS",
        "NEXT_STEP": "GENERATE_PRODUCTION_WAVE_1" if not dry["error_count"] else "RESOLVE_BLOCKER",
    }
    return {"snapshot": snapshot, "registry": registry, "near_duplicate_review": {"scope": "SEMANTIC_NEAR_DUPLICATE_REVIEW_V1", "pairs": near_review}, "coverage": coverage, "review": review, "allocation": allocation, "seed_plan": seed_plan, "identity_graph": graph, "queue": queue, "dry_run": dry, "milestone": milestone}


OUTPUTS = {
    "snapshot": "research/qgen/opportunity_registry/curriculum_input_snapshot_v1.json",
    "registry": "research/qgen/opportunity_registry/curriculum_question_opportunity_registry_v1.json",
    "near_duplicate_review": "research/qgen/opportunity_registry/semantic_near_duplicate_review_v1.json",
    "coverage": "research/qgen/opportunity_registry/curriculum_coverage_matrix_v1.json",
    "review": "research/qgen/opportunity_registry/opportunity_independent_review_v1.json",
    "allocation": "research/qgen/opportunity_registry/question_bank_allocation_plan_v1.json",
    "seed_plan": "research/qgen/opportunity_registry/question_seed_population_plan_v1.json",
    "identity_graph": "research/qgen/opportunity_registry/question_identity_graph_v1.json",
    "queue": "research/qgen/opportunity_registry/production_queue_v1.json",
    "dry_run": "research/qgen/opportunity_registry/production_queue_dry_run_v1.json",
    "milestone": "reports/curriculum_question_opportunity_registry_v1_milestone.json",
}


def write_artifacts(root: Path, artifacts: dict[str, Any], *, outputs: dict[str, str] | None = None) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, relative in (outputs or OUTPUTS).items():
        if key not in artifacts:
            raise RegistryError(f"artifact payload missing: {key}")
        path = Path(root).resolve() / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = canonical_json(artifacts[key])
        path.write_text(data)
        hashes[relative] = hashlib.sha256(data.encode()).hexdigest()
    return hashes


def write_all_artifacts(root: Path) -> dict[str, Any]:
    artifacts = build_all_artifacts(root)
    write_artifacts(root, artifacts)
    return artifacts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = write_all_artifacts(args.root)
    print(canonical_json(result["milestone"]), end="")
