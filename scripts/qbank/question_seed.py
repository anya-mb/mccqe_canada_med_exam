"""Deterministic question-seed and semantic duplicate-prevention contracts."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping


REQUIRED_SEED_FIELDS = (
    "seed_id", "discipline", "toronto_notes_chapter_topic", "study_unit_id",
    "clinical_concept", "learner_decision", "response_class", "clinical_stage",
    "population", "key", "mcc_blueprint_dimensions", "difficulty_target",
    "primary_discriminator", "candidate_universe_id", "candidate_subset_strategy",
    "generation_family", "decision_granularity",
)


class QuestionSeedError(ValueError):
    """Raised when a seed cannot safely drive deterministic generation."""


def _normalize(value: Any) -> str:
    return " ".join(str(value).casefold().strip().split())


def _intent(value: Any) -> str:
    text = _normalize(value)
    if any(token in text for token in ("diagnos", "identify", "most likely")):
        return "DIAGNOSIS"
    if any(token in text for token in ("investig", "test", "screen")):
        return "INVESTIGATION"
    if any(token in text for token in ("manage", "treat", "action", "next step")):
        return "MANAGEMENT"
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def validate_question_seed(seed: Mapping[str, Any]) -> list[str]:
    errors = [f"MISSING_REQUIRED_FIELD:{field}" for field in REQUIRED_SEED_FIELDS if seed.get(field) in (None, "", [])]
    if seed.get("candidate_subset_strategy") not in (None, "TIER_BALANCED_DISTINCT"):
        errors.append("UNKNOWN_CANDIDATE_SUBSET_STRATEGY")
    return errors


def _seed_semantics(seed: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "topic": _normalize(seed.get("clinical_concept")),
        "learner_decision_intent": _intent(seed.get("learner_decision")),
        "key": _normalize(seed.get("key")),
        "clinical_stage": _normalize(seed.get("clinical_stage")),
        "population": _normalize(seed.get("population")),
        "primary_discriminator": _normalize(seed.get("primary_discriminator")),
        "response_class": _normalize(seed.get("response_class")),
        "decision_granularity": _normalize(seed.get("decision_granularity")),
        "generation_family": _normalize(seed.get("generation_family")),
    }


def seed_fingerprint(seed: Mapping[str, Any]) -> str:
    errors = validate_question_seed(seed)
    if errors:
        raise QuestionSeedError(str(errors))
    encoded = json.dumps(_seed_semantics(seed), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def classify_seed_duplicate(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    if seed_fingerprint(left) == seed_fingerprint(right):
        return "DUPLICATE"
    lsem, rsem = _seed_semantics(left), _seed_semantics(right)
    if lsem["topic"] == rsem["topic"] and lsem["key"] == rsem["key"]:
        if lsem["clinical_stage"] != rsem["clinical_stage"]:
            return "RELATED_BUT_DISTINCT"
        if lsem["learner_decision_intent"] == rsem["learner_decision_intent"]:
            return "NEAR_DUPLICATE"
        return "RELATED_BUT_DISTINCT"
    return "DISTINCT"


def select_candidate_subset(
    seed: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]], *, size: int = 3
) -> list[str]:
    errors = validate_question_seed(seed)
    if errors:
        raise QuestionSeedError(str(errors))
    eligible = [
        row for row in candidates
        if row.get("final_admission_state") == "ADMITTED"
        and row.get("response_class") == seed["response_class"]
        and row.get("granularity") == seed["decision_granularity"]
    ]
    if len(eligible) < size:
        raise QuestionSeedError("fewer than three live compatible candidates")
    tier_rank = {"TIER_A_STRONG_DISTRACTOR": 0, "TIER_B_GOOD_DISTRACTOR": 1, "TIER_C_CONTEXT_DEPENDENT_RESERVE": 2}
    def rank(row: Mapping[str, Any]) -> tuple[int, str]:
        stable = hashlib.sha256(f"{seed['seed_id']}|{row['canonical_candidate_id']}".encode()).hexdigest()
        return tier_rank.get(str(row.get("quality_tier")), 3), stable
    return [str(row["canonical_candidate_id"]) for row in sorted(eligible, key=rank)[:size]]


def _item_semantics(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "learner_objective": _normalize(item.get("learner_objective")),
        "stem_clinical_state": _normalize(item.get("stem_clinical_state")),
        "clinical_stage": _normalize(item.get("clinical_stage")),
        "lead_in_intent": _intent(item.get("lead_in")),
        "correct_concept": _normalize(item.get("correct_concept")),
        "primary_discriminator": _normalize(item.get("primary_discriminator")),
        "option_concept_set": sorted({_normalize(value) for value in item.get("option_concept_set", ())}),
    }


def item_semantic_fingerprint(item: Mapping[str, Any]) -> str:
    encoded = json.dumps(_item_semantics(item), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def classify_item_duplicate(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    if item_semantic_fingerprint(left) == item_semantic_fingerprint(right):
        return "DUPLICATE"
    lsem, rsem = _item_semantics(left), _item_semantics(right)
    topic_fields = ("learner_objective", "lead_in_intent", "correct_concept")
    if all(lsem[field] == rsem[field] for field in topic_fields):
        if lsem["clinical_stage"] and rsem["clinical_stage"] and lsem["clinical_stage"] != rsem["clinical_stage"]:
            return "RELATED_BUT_DISTINCT"
        return "NEAR_DUPLICATE"
    stable_fields = ("learner_objective", "lead_in_intent", "correct_concept", "primary_discriminator", "option_concept_set")
    if all(lsem[field] == rsem[field] for field in stable_fields):
        return "NEAR_DUPLICATE"
    if lsem["correct_concept"] == rsem["correct_concept"]:
        return "RELATED_BUT_DISTINCT"
    return "DISTINCT"
