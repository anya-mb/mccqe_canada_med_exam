from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from qbank.source_ready_generation_pilot import (
    RETRY_GENERATED_ARTIFACT_PATH,
    RETRY_V2_GENERATED_ARTIFACT_PATH,
    RETRY_V2_ITEM_SPEC_PATH,
    RETRY_V2_PREFLIGHT_PATH,
    SourceReadyGenerationPilotError,
    build_generator_input,
    build_retry_generator_input,
    build_retry_v2_generator_input,
    build_retry_v2_preflight_input,
    build_retry_v2_verifier_input,
    build_verifier_input,
    retry_v2_semantic_signature,
    validate_retry_v2_generated_artifact,
    validate_retry_v2_item_specs,
    validate_retry_v2_output_path,
    validate_retry_v2_semantic_preflight,
    validate_retry_v2_verification,
    validate_retry_generated_artifact,
    validate_retry_output_path,
    validate_generated_artifact,
    validate_verifier_verdicts,
)


REPO = Path(__file__).resolve().parents[1]
JOB_ID = "QGEN-PHELO-011"


def _generated_artifact(generator_id: str = "generator-a") -> dict:
    generator_input = build_generator_input(REPO, JOB_ID)
    packet = generator_input["source_packets"][0]
    recommendation = packet["supported_recommendations"][0]
    citation = recommendation["source_citations"][0]
    return {
        "job_id": JOB_ID,
        "generator_id": generator_id,
        "items": [
            {
                "slot_id": slot_id,
                "stem": f"Stem for {slot_id}",
                "options": [
                    {"key": "A", "text": "Correct"},
                    {"key": "B", "text": "Distractor one"},
                    {"key": "C", "text": "Distractor two"},
                    {"key": "D", "text": "Distractor three"},
                ],
                "correct_answer": "A",
                "correct_answer_rationale": "Supported correct-answer rationale.",
                "distractor_rationales": {
                    "B": "Why B is incorrect.",
                    "C": "Why C is incorrect.",
                    "D": "Why D is incorrect.",
                },
                "evidence_references": [{
                    "source_packet_id": packet["source_packet_id"],
                    "recommendation_id": recommendation["recommendation_id"],
                    "source_id": citation["source_id"],
                    "locator": citation["locator"],
                }],
            }
            for slot_id in generator_input["job"]["question_slot_ids"]
        ],
    }


def _retry_generated_artifact() -> dict:
    retry_input = build_retry_generator_input(REPO, JOB_ID)
    items = []
    for card in retry_input["concept_cards"]:
        references = card["authorized_evidence"]
        items.append({
            "retry_slot_id": card["retry_slot_id"],
            "concept_card_id": card["concept_card_id"],
            "allocation_address_id": card["allocation_address_id"],
            "study_unit_id": card["study_unit_id"],
            "planned_competency": card["target_competency"],
            "reasoning_task": card["reasoning_task"],
            "concept_target": card["concept_target"],
            "intended_item_form": card["intended_item_form"],
            "stem": "Evidence-bounded stem.",
            "options": [
                {"key": "A", "text": "Correct"},
                {"key": "B", "text": "Distractor one"},
                {"key": "C", "text": "Distractor two"},
                {"key": "D", "text": "Distractor three"},
            ],
            "correct_answer": "A",
            "correct_answer_rationale": "Supported correct-answer rationale.",
            "distractor_rationales": {
                "B": "Why B is incorrect.",
                "C": "Why C is incorrect.",
                "D": "Why D is incorrect.",
            },
            "evidence_references": references,
            "assertion_evidence": {
                "stem": references,
                "options": references,
                "correct_answer": references,
                "correct_answer_rationale": references,
                "distractor_rationales": references,
            },
        })
    return {"job_id": JOB_ID, "generator_id": "retry-generator", "items": items}


def _canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _signature_payload(card: dict) -> dict:
    normalize = lambda text: " ".join(text.lower().split())
    return {
        "learner_decision": normalize(card["learner_decision"]),
        "reasoning_chain": [normalize(value) for value in card["reasoning_chain"]],
        "evidence_discriminants": [normalize(value["fact"]) for value in card["evidence_discriminants"]],
        "closest_competing_concepts": [normalize(value["label"]) for value in card["closest_competing_concepts"]],
        "evidence_route": sorted([
            [reference.get("evidence_type") or "", reference.get("claim_card_id") or "", reference.get("source_packet_id") or "", reference.get("recommendation_id") or ""]
            for reference in card["authorized_evidence"]
        ]),
        "answer_category": normalize(card["answer_category"]),
    }


def _v2_item_specs(author_id: str = "v2-spec-author") -> dict:
    retry_input = build_retry_generator_input(REPO, JOB_ID)
    with (REPO / "research/qgen/pilot/QGEN-PHELO-011.retry-10.concept-plan.json").open() as handle:
        v1_plan = json.load(handle)
    raw_cards = {card["concept_card_id"]: card for card in v1_plan["concept_cards"]}
    cards = []
    for index, source in enumerate(retry_input["concept_cards"], start=1):
        refs = source["authorized_evidence"]
        competitors = [
            {
                "concept_id": f"ALT-{index}-{letter}",
                "label": f"plausible neighboring concept {index}-{letter}",
                "why_plausible": f"Scenario feature could initially support alternative {letter}.",
                "evidence_refs": refs,
            }
            for letter in ("B", "C", "D")
        ]
        card = {
            "v2_item_spec_id": f"QGEN-PHELO-011-RETRY-V2-{index:02d}",
            "retry_slot_id": source["retry_slot_id"],
            "disposition": (
                "REPLACE_AS_DUPLICATIVE" if index in {1, 6, 7}
                else "REDESIGN_CONCEPT" if index in {3, 4, 8}
                else "KEEP_CORE_CONCEPT"
            ),
            "allocation_address_id": source["allocation_address_id"],
            "study_unit_id": source["study_unit_id"],
            "target_competency": source["target_competency"],
            "authorized_evidence": refs,
            "learner_decision": f"Make distinct evidence-bounded educational decision {index}.",
            "competency_demonstration": f"Apply the assigned competency to decision {index}.",
            "reasoning_chain": [
                f"Interpret scenario feature for decision {index}.",
                f"Apply evidence discriminant for decision {index}.",
            ],
            "evidence_discriminants": [{
                "fact": f"Authorized evidence discriminant for decision {index}.",
                "evidence_refs": refs,
            }],
            "closest_competing_concepts": competitors,
            "distractor_blueprint": [
                {
                    "distractor_id": f"DIST-{index}-{letter}",
                    "competing_concept_id": f"ALT-{index}-{letter}",
                    "temptation": f"Alternative {letter} is tempting for a defined reason.",
                    "scenario_feature": f"Feature making alternative {letter} plausible.",
                    "evidence_discriminator": f"Evidence excludes alternative {letter} here.",
                    "evidence_refs": refs,
                }
                for letter in ("B", "C", "D")
            ],
            "vignette_requirements": {
                "required": True,
                "facts": [{
                    "requirement_id": f"VR-{index}-1",
                    "fact": f"Material scenario fact for decision {index}.",
                    "evidence_refs": refs,
                }],
                "necessity": f"Without the scenario fact, decision {index} collapses to recall.",
            },
            "difficulty_mechanism": f"Decision {index} requires applying a discriminator, not recognizing a definition.",
            "prohibited_shortcuts": [
                "definition giveaway", "keyword cue", "option-form cue",
                "answer-length cue", "redundant distractors", "reverse-label duplicate",
            ],
            "rationale_requirements": {
                "best_answer": f"Explain positive evidence for decision {index}.",
                "alternatives": [
                    {
                        "competing_concept_id": competitor["concept_id"],
                        "required_discriminator": f"Explain why {competitor['concept_id']} is not best.",
                        "evidence_refs": refs,
                    }
                    for competitor in competitors
                ],
            },
            "answer_category": f"distinct-answer-category-{index}",
            "semantic_signature": "",
            "lineage": {
                "v1_concept_plan_path": "research/qgen/pilot/QGEN-PHELO-011.retry-10.concept-plan.json",
                "v1_concept_plan_sha256": _canonical_sha(v1_plan),
                "v1_concept_card_id": source["concept_card_id"],
                "v1_concept_card_sha256": _canonical_sha(raw_cards[source["concept_card_id"]]),
                "authorized_evidence_fingerprints": [
                    {"reference": reference, "sha256": _canonical_sha(evidence)}
                    for reference, evidence in zip(
                        refs,
                        source["foundational_claims"] + source["current_packet_recommendations"],
                        strict=True,
                    )
                ],
                "revision": 0,
            },
        }
        card["semantic_signature"] = _canonical_sha(_signature_payload(card))
        cards.append(card)
    return {
        "schema_version": "2.0",
        "scope": "STRUCTURED_ITEM_SPEC_V2",
        "job_id": JOB_ID,
        "author_id": author_id,
        "allocation_apportionment": {"SU-PH-01": 5, "SU-PH-02": 3, "SU-PH-03": 2},
        "cards": cards,
    }


def _v2_preflight(specs: dict, reviewer_id: str = "fresh-preflight-reviewer") -> dict:
    return {
        "schema_version": "2.0",
        "scope": "RETRY_V2_SEMANTIC_PREFLIGHT",
        "job_id": JOB_ID,
        "reviewer_id": reviewer_id,
        "item_spec_author_id": specs["author_id"],
        "item_spec_path": RETRY_V2_ITEM_SPEC_PATH,
        "item_spec_sha256": _canonical_sha(specs),
        "revision_pass": 0,
        "independent_context": "PASS",
        "included_context": ["V2_ITEM_SPECS", "AUTHORIZED_EVIDENCE", "CANONICAL_MCCQE_LEVEL"],
        "set_level_duplication": "NONE",
        "verdicts": [
            {
                "v2_item_spec_id": card["v2_item_spec_id"],
                "retry_slot_id": card["retry_slot_id"],
                "verdict": "APPROVED_FOR_GENERATION",
                "assessments": {
                    "evidence_alignment": "PASS",
                    "educational_decision_distinctness": "PASS",
                    "reasoning_depth": "PASS",
                    "vignette_necessity": "PASS",
                    "competing_concept_plausibility": "PASS",
                    "distractor_blueprint_quality": "PASS",
                    "set_level_duplication": "PASS",
                    "mccqe_appropriateness": "PASS",
                },
                "rationale": "Independent evidence-bounded approval.",
            }
            for card in specs["cards"]
        ],
    }


def _v2_generated(specs: dict, preflight: dict, generator_id: str = "v2-generator") -> dict:
    items = []
    answer_keys = ("A", "B", "C", "D", "A", "B", "C", "D", "A", "B")
    for card, correct_key in zip(specs["cards"], answer_keys, strict=True):
        distractors = iter(card["distractor_blueprint"])
        options = []
        for key in ("A", "B", "C", "D"):
            if key == correct_key:
                options.append({"key": key, "text": "Best evidence-supported response", "blueprint_role": "BEST_ANSWER"})
                continue
            distractor = next(distractors)
            options.append({
                "key": key,
                "text": f"Plausible option for {distractor['competing_concept_id']}",
                "distractor_id": distractor["distractor_id"],
                "competing_concept_id": distractor["competing_concept_id"],
            })
        references = card["authorized_evidence"]
        items.append({
            "v2_item_spec_id": card["v2_item_spec_id"],
            "retry_slot_id": card["retry_slot_id"],
            "item_spec_sha256": _canonical_sha(card),
            "semantic_signature": card["semantic_signature"],
            "learner_decision": card["learner_decision"],
            "answer_category": card["answer_category"],
            "realized_reasoning_steps": card["reasoning_chain"],
            "stem": f"Applied scenario requiring the distinct decision for {card['v2_item_spec_id']}.",
            "options": options,
            "correct_answer": correct_key,
            "correct_answer_rationale": "Positive authorized evidence supports the best response.",
            "distractor_rationales": {
                key: f"The planned evidence discriminator makes option {key} not best."
                for key in ("A", "B", "C", "D") if key != correct_key
            },
            "vignette_requirement_ids_used": [
                fact["requirement_id"] for fact in card["vignette_requirements"]["facts"]
            ],
            "evidence_references": references,
            "assertion_evidence": {part: references for part in (
                "stem", "options", "correct_answer", "correct_answer_rationale", "distractor_rationales",
            )},
        })
    return {
        "schema_version": "2.0",
        "scope": "RETRY_V2_GENERATED_QUESTIONS",
        "job_id": JOB_ID,
        "generator_id": generator_id,
        "item_spec_path": RETRY_V2_ITEM_SPEC_PATH,
        "item_spec_sha256": _canonical_sha(specs),
        "semantic_preflight_path": RETRY_V2_PREFLIGHT_PATH,
        "semantic_preflight_sha256": _canonical_sha(preflight),
        "revision_cycle": 0,
        "revised_item_spec_ids": [],
        "items": items,
    }


_V2_FINAL_ASSESSMENTS = (
    "factual_correctness", "semantic_evidence_support", "single_best_answer",
    "distractor_plausibility", "mccqe_level_difficulty", "reasoning_quality",
    "item_spec_fidelity", "vignette_necessity", "rationale_quality",
    "item_writing_quality", "semantic_duplication",
)


def _v2_verification(specs: dict, preflight: dict, generated: dict) -> dict:
    rows = [{
        "v2_item_spec_id": card["v2_item_spec_id"],
        "retry_slot_id": card["retry_slot_id"],
        "verdict": "PASS",
        "reason_categories": [],
        "dimension_assessments": {key: "PASS" for key in _V2_FINAL_ASSESSMENTS},
        "explanation": "Fresh independent review found the item supported and fit for purpose.",
    } for card in specs["cards"]]
    return {
        "schema_version": "2.0",
        "scope": "RETRY_V2_INDEPENDENT_VERIFICATION",
        "job_id": JOB_ID,
        "verifier_id": "fresh-final-verifier",
        "item_spec_path": RETRY_V2_ITEM_SPEC_PATH,
        "item_spec_sha256": _canonical_sha(specs),
        "semantic_preflight_path": RETRY_V2_PREFLIGHT_PATH,
        "semantic_preflight_sha256": _canonical_sha(preflight),
        "generated_artifact_path": RETRY_V2_GENERATED_ARTIFACT_PATH,
        "generated_artifact_sha256": _canonical_sha(generated),
        "independent_context": "PASS",
        "evidence_traceability": "PASS",
        "set_level_duplication": "NONE",
        "systemic_failure": False,
        "systemic_failure_reasons": [],
        "local_failure_determination": "NONE",
        "final_revision_cycle_used": False,
        "questions_passed": 10,
        "questions_rejected": 0,
        "rejection_categories": {
            "FACTUAL_ERROR": 0, "UNSUPPORTED_CLAIM": 0, "AMBIGUOUS_BEST_ANSWER": 0,
            "WEAK_DISTRACTORS": 0, "INAPPROPRIATE_DIFFICULTY": 0, "PLAN_MISMATCH": 0,
            "RATIONALE_DEFICIENCY": 0, "ITEM_WRITING_PROBLEM": 0,
            "MATERIAL_DUPLICATION": 0, "OTHER": 0,
        },
        "verdicts": rows,
    }


def test_build_generator_input_derives_only_ready_job_slots_and_packets():
    payload = build_generator_input(REPO, JOB_ID)

    assert payload["job"]["job_id"] == JOB_ID
    assert len(payload["job"]["question_slot_ids"]) == 30
    assert [packet["source_packet_id"] for packet in payload["source_packets"]] == [
        "SRC-PHELO-006", "SRC-PHELO-007", "SRC-PHELO-008",
    ]
    assert all(packet["status"] == "SOURCE_PACKET_READY" for packet in payload["source_packets"])


def test_build_generator_input_rejects_job_that_is_not_source_ready():
    with pytest.raises(SourceReadyGenerationPilotError, match="SOURCE_READY"):
        build_generator_input(REPO, "QGEN-MED-001")


def test_generated_artifact_rejects_unsupported_item_evidence_reference():
    artifact = _generated_artifact()
    artifact["items"][0]["evidence_references"][0]["recommendation_id"] = "REC-NOT-AVAILABLE"

    with pytest.raises(SourceReadyGenerationPilotError, match="unsupported evidence reference"):
        validate_generated_artifact(REPO, JOB_ID, artifact)


def test_generated_artifact_requires_exact_slots_and_rationales():
    artifact = _generated_artifact()
    artifact["items"][0].pop("distractor_rationales")

    with pytest.raises(SourceReadyGenerationPilotError, match="rationales for every distractor"):
        validate_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _generated_artifact()
    artifact["items"] = artifact["items"][:-1]
    with pytest.raises(SourceReadyGenerationPilotError, match="slot IDs"):
        validate_generated_artifact(REPO, JOB_ID, artifact)


def test_verifier_input_fingerprints_artifact_and_sources_and_verdicts_require_independence():
    artifact = _generated_artifact("generator-a")
    verifier_input = build_verifier_input(REPO, JOB_ID, artifact)

    assert verifier_input["generated_artifact_fingerprint"]["sha256"]
    assert len(verifier_input["source_packet_fingerprints"]) == 3

    verdicts = {
        "job_id": JOB_ID,
        "verifier_id": "generator-a",
        "generated_artifact_sha256": verifier_input["generated_artifact_fingerprint"]["sha256"],
        "verdicts": [{"slot_id": item["slot_id"], "verdict": "PASS"} for item in artifact["items"]],
    }
    with pytest.raises(SourceReadyGenerationPilotError, match="self-verification"):
        validate_verifier_verdicts(REPO, JOB_ID, artifact, verdicts)


def test_verified_requires_every_slot_to_pass_and_rejections_keep_slot_ids():
    artifact = _generated_artifact()
    verifier_input = build_verifier_input(REPO, JOB_ID, artifact)
    verdicts = {
        "job_id": JOB_ID,
        "verifier_id": "verifier-b",
        "generated_artifact_sha256": verifier_input["generated_artifact_fingerprint"]["sha256"],
        "verdicts": [
            {"slot_id": item["slot_id"], "verdict": "REJECT" if index == 0 else "PASS"}
            for index, item in enumerate(artifact["items"])
        ],
    }

    result = validate_verifier_verdicts(REPO, JOB_ID, artifact, verdicts)
    assert result["status"] == "PENDING_REGENERATION"
    assert result["rejected_slot_ids"] == ["PHELO-Q0287"]

    incomplete = deepcopy(verdicts)
    incomplete["verdicts"] = incomplete["verdicts"][:-1]
    with pytest.raises(SourceReadyGenerationPilotError, match="slot IDs"):
        validate_verifier_verdicts(REPO, JOB_ID, artifact, incomplete)


def test_retry_input_uses_exactly_concept_plan_slots_not_original_manifest_slots():
    payload = build_retry_generator_input(REPO, JOB_ID)

    assert [card["retry_slot_id"] for card in payload["concept_cards"]] == [
        f"QGEN-PHELO-011-RETRY-{number:02d}" for number in range(1, 11)
    ]
    assert len(payload["concept_cards"]) == 10
    assert "question_slot_ids" not in payload["job"]


def test_retry_input_loads_only_each_cards_foundational_claims_and_ready_recommendations():
    payload = build_retry_generator_input(REPO, JOB_ID)
    foundational = payload["concept_cards"][0]
    packet = payload["concept_cards"][4]

    assert [claim["claim_card_id"] for claim in foundational["foundational_claims"]] == ["FNDCLM-PHELO-011-01A"]
    assert foundational["current_packet_recommendations"] == []
    assert packet["foundational_claims"] == []
    assert [reference["recommendation_id"] for reference in packet["current_packet_recommendations"]] == ["REC-SRC-PHELO-006-01"]


def test_retry_item_rejects_cross_slot_evidence_missing_claim_and_unsupported_recommendation():
    artifact = _retry_generated_artifact()
    artifact["items"][0]["evidence_references"] = artifact["items"][1]["evidence_references"]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _retry_generated_artifact()
    artifact["items"][0]["evidence_references"] = [{"evidence_type": "FOUNDATIONAL_CLAIM", "claim_card_id": "FNDCLM-NOT-VERIFIED"}]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _retry_generated_artifact()
    artifact["items"][4]["evidence_references"] = [{"evidence_type": "CURRENT_PACKET_RECOMMENDATION", "source_packet_id": "SRC-PHELO-006", "recommendation_id": "REC-NOT-SUPPORTED"}]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)


def test_retry_item_preserves_plan_identifiers_and_requires_slot_scoped_evidence_closure():
    artifact = _retry_generated_artifact()
    assert validate_retry_generated_artifact(REPO, JOB_ID, artifact) == artifact

    artifact["items"][0]["planned_competency"] = {"mcc_objective_id": "wrong"}
    with pytest.raises(SourceReadyGenerationPilotError, match="does not match concept card"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)

    artifact = _retry_generated_artifact()
    artifact["items"][0]["assertion_evidence"]["stem"] = [{"evidence_type": "TORONTO_NOTES", "node_id": "PH.S01.T01"}]
    with pytest.raises(SourceReadyGenerationPilotError, match="not authorized for retry slot"):
        validate_retry_generated_artifact(REPO, JOB_ID, artifact)


def test_retry_v2_item_specs_accept_exact_schema_allocation_signatures_and_lineage():
    specs = _v2_item_specs()

    validated = validate_retry_v2_item_specs(REPO, JOB_ID, specs)

    assert validated == specs
    assert [card["study_unit_id"] for card in specs["cards"]].count("SU-PH-01") == 5
    assert len({card["semantic_signature"] for card in specs["cards"]}) == 10


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value["cards"][0].pop("learner_decision"), "required V2 fields"),
        (lambda value: value["cards"][4].__setitem__("study_unit_id", "SU-PH-02"), "5/3/2"),
        (lambda value: value["cards"][0].__setitem__("semantic_signature", "forged"), "semantic signature"),
        (lambda value: value["cards"][0]["lineage"].__setitem__("v1_concept_plan_sha256", "forged"), "V1 concept plan fingerprint"),
        (lambda value: value["cards"][0].__setitem__("authorized_evidence", value["cards"][5]["authorized_evidence"]), "authorized evidence"),
    ],
)
def test_retry_v2_item_specs_fail_closed_on_deterministic_contract_breaks(mutate, message):
    specs = _v2_item_specs()
    mutate(specs)

    with pytest.raises(SourceReadyGenerationPilotError, match=message):
        validate_retry_v2_item_specs(REPO, JOB_ID, specs)


def test_retry_v2_semantic_signature_includes_evidence_route_and_rejects_true_duplicate_payload():
    specs = _v2_item_specs()
    changed_route = deepcopy(specs["cards"][0])
    changed_route["authorized_evidence"] = specs["cards"][1]["authorized_evidence"]
    assert retry_v2_semantic_signature(changed_route) != specs["cards"][0]["semantic_signature"]
    reordered_route = deepcopy(specs["cards"][9])
    reordered_route["authorized_evidence"].reverse()
    assert retry_v2_semantic_signature(reordered_route) == specs["cards"][9]["semantic_signature"]

    original = specs["cards"][0]
    duplicate = specs["cards"][1]
    for field in (
        "authorized_evidence", "learner_decision", "reasoning_chain", "evidence_discriminants",
        "closest_competing_concepts", "distractor_blueprint", "vignette_requirements",
        "rationale_requirements", "answer_category",
    ):
        duplicate[field] = deepcopy(original[field])
    duplicate["lineage"]["authorized_evidence_fingerprints"] = deepcopy(
        original["lineage"]["authorized_evidence_fingerprints"]
    )
    duplicate["semantic_signature"] = original["semantic_signature"]

    with pytest.raises(SourceReadyGenerationPilotError, match="duplicate candidates"):
        validate_retry_v2_item_specs(REPO, JOB_ID, specs)


def test_retry_v2_preflight_binds_fresh_reviewer_exact_specs_and_all_ten_approvals():
    specs = _v2_item_specs()
    packet = build_retry_v2_preflight_input(REPO, JOB_ID, specs)
    preflight = _v2_preflight(specs)

    assert packet["item_spec_fingerprint"]["sha256"] == _canonical_sha(specs)
    assert validate_retry_v2_semantic_preflight(REPO, JOB_ID, specs, preflight) == preflight


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda specs, review: review.__setitem__("reviewer_id", specs["author_id"]), "self-review"),
        (lambda specs, review: review.__setitem__("item_spec_sha256", "forged"), "item-spec fingerprint"),
        (lambda specs, review: review["verdicts"].pop(), "exactly match"),
        (lambda specs, review: review["verdicts"][0].__setitem__("verdict", "REJECTED_FOR_SPEC_REVISION"), "not approved"),
    ],
)
def test_retry_v2_preflight_fails_closed_on_nonindependence_mismatch_or_rejection(mutate, message):
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    mutate(specs, preflight)

    with pytest.raises(SourceReadyGenerationPilotError, match=message):
        validate_retry_v2_semantic_preflight(REPO, JOB_ID, specs, preflight)


def test_retry_v2_generation_requires_approved_preflight_and_separate_output_path():
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)

    payload = build_retry_v2_generator_input(REPO, JOB_ID, specs, preflight)

    assert payload["item_spec_fingerprint"]["sha256"] == _canonical_sha(specs)
    assert validate_retry_v2_output_path(REPO, RETRY_V2_GENERATED_ARTIFACT_PATH) == RETRY_V2_GENERATED_ARTIFACT_PATH
    with pytest.raises(SourceReadyGenerationPilotError, match="V1"):
        validate_retry_v2_output_path(REPO, RETRY_GENERATED_ARTIFACT_PATH)

    preflight["verdicts"][0]["verdict"] = "REJECTED_FOR_SPEC_REVISION"
    with pytest.raises(SourceReadyGenerationPilotError, match="not approved"):
        build_retry_v2_generator_input(REPO, JOB_ID, specs, preflight)


def test_retry_v2_generated_artifact_preserves_specs_blueprints_vignettes_and_evidence_closure():
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    generated = _v2_generated(specs, preflight)

    assert validate_retry_v2_generated_artifact(REPO, JOB_ID, specs, preflight, generated) == generated
    assert {key: [item["correct_answer"] for item in generated["items"]].count(key) for key in "ABCD"} == {
        "A": 3, "B": 3, "C": 2, "D": 2,
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.__setitem__("item_spec_sha256", "forged"), "item-spec fingerprint"),
        (lambda value: value["items"][0]["options"][1].__setitem__("distractor_id", "UNPLANNED"), "distractor blueprint"),
        (lambda value: value["items"][0].__setitem__("vignette_requirement_ids_used", []), "vignette requirements"),
        (lambda value: value["items"][0]["assertion_evidence"]["stem"].__setitem__(0, {"evidence_type": "FOUNDATIONAL_CLAIM", "claim_card_id": "UNAUTHORIZED"}), "authorized evidence"),
    ],
)
def test_retry_v2_generated_artifact_fails_closed_on_contract_breaks(mutate, message):
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    generated = _v2_generated(specs, preflight)
    mutate(generated)

    with pytest.raises(SourceReadyGenerationPilotError, match=message):
        validate_retry_v2_generated_artifact(REPO, JOB_ID, specs, preflight, generated)


def test_retry_v2_revision_lineage_requires_one_prior_artifact_and_only_local_items():
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    previous = _v2_generated(specs, preflight)
    revised = deepcopy(previous)
    revised["revision_cycle"] = 1
    revised["revised_item_spec_ids"] = [specs["cards"][0]["v2_item_spec_id"]]
    revised["previous_generated_artifact_sha256"] = _canonical_sha(previous)
    revised["items"][0]["stem"] = "Locally revised applied scenario."
    prior_verification = _v2_verification(specs, preflight, previous)
    failed_row = prior_verification["verdicts"][0]
    failed_row["verdict"] = "REJECTED_FOR_REVISION"
    failed_row["reason_categories"] = ["WEAK_DISTRACTORS"]
    failed_row["dimension_assessments"]["distractor_plausibility"] = "FAIL"
    prior_verification["questions_passed"] = 9
    prior_verification["questions_rejected"] = 1
    prior_verification["rejection_categories"]["WEAK_DISTRACTORS"] = 1
    prior_verification["local_failure_determination"] = "LOCAL"
    revised["previous_verification_sha256"] = _canonical_sha(prior_verification)

    with pytest.raises(SourceReadyGenerationPilotError, match="previous generated artifact"):
        validate_retry_v2_generated_artifact(REPO, JOB_ID, specs, preflight, revised)
    with pytest.raises(SourceReadyGenerationPilotError, match="previous verification"):
        validate_retry_v2_generated_artifact(
            REPO, JOB_ID, specs, preflight, revised, previous_artifact=previous
        )
    assert validate_retry_v2_generated_artifact(
        REPO, JOB_ID, specs, preflight, revised,
        previous_artifact=previous,
        previous_verification=prior_verification,
    ) == revised

    final_verification = _v2_verification(specs, preflight, revised)
    final_verification["final_revision_cycle_used"] = True
    assert validate_retry_v2_verification(
        REPO,
        JOB_ID,
        specs,
        preflight,
        revised,
        final_verification,
        previous_generated_artifact=previous,
        previous_verification=prior_verification,
    )["status"] == "PILOT_ACCEPTED"

    nonlocal_revision = deepcopy(revised)
    nonlocal_revision["items"][1]["stem"] = "Unlisted non-local change."
    with pytest.raises(SourceReadyGenerationPilotError, match="local revision set"):
        validate_retry_v2_generated_artifact(
            REPO, JOB_ID, specs, preflight, nonlocal_revision,
            previous_artifact=previous,
            previous_verification=prior_verification,
        )


def test_retry_v2_fresh_verifier_input_and_all_pass_verification_reach_pilot_gate():
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    generated = _v2_generated(specs, preflight)

    packet = build_retry_v2_verifier_input(REPO, JOB_ID, specs, preflight, generated)
    result = validate_retry_v2_verification(
        REPO, JOB_ID, specs, preflight, generated, _v2_verification(specs, preflight, generated)
    )

    assert packet["generated_artifact_fingerprint"]["sha256"] == _canonical_sha(generated)
    assert result["status"] == "PILOT_ACCEPTED"
    assert result["questions_passed"] == 10


def test_retry_v2_verification_rejects_context_overlap_incomplete_rows_and_acceptance_defects():
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    generated = _v2_generated(specs, preflight)
    verification = _v2_verification(specs, preflight, generated)
    verification["verifier_id"] = generated["generator_id"]
    with pytest.raises(SourceReadyGenerationPilotError, match="independent verifier"):
        validate_retry_v2_verification(REPO, JOB_ID, specs, preflight, generated, verification)

    verification = _v2_verification(specs, preflight, generated)
    verification["verdicts"].pop()
    with pytest.raises(SourceReadyGenerationPilotError, match="exactly match"):
        validate_retry_v2_verification(REPO, JOB_ID, specs, preflight, generated, verification)

    verification = _v2_verification(specs, preflight, generated)
    row = verification["verdicts"][0]
    row["verdict"] = "REJECTED_FOR_REVISION"
    row["reason_categories"] = ["FACTUAL_ERROR"]
    row["dimension_assessments"]["factual_correctness"] = "FAIL"
    verification["questions_passed"] = 9
    verification["questions_rejected"] = 1
    verification["rejection_categories"]["FACTUAL_ERROR"] = 1
    verification["local_failure_determination"] = "LOCAL"

    result = validate_retry_v2_verification(REPO, JOB_ID, specs, preflight, generated, verification)
    assert result["status"] == "PILOT_NOT_ACCEPTED"
    assert result["rejection_categories"]["FACTUAL_ERROR"] == 1


@pytest.mark.parametrize(
    ("failed_dimension", "expected_category", "message"),
    [
        ("factual_correctness", "FACTUAL_ERROR", "factual"),
        ("semantic_evidence_support", "UNSUPPORTED_CLAIM", "unsupported"),
    ],
)
def test_retry_v2_verification_cannot_hide_fatal_dimension_failure_under_other_category(
    failed_dimension, expected_category, message
):
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    generated = _v2_generated(specs, preflight)
    verification = _v2_verification(specs, preflight, generated)
    row = verification["verdicts"][0]
    row["verdict"] = "REJECTED_FOR_REVISION"
    row["reason_categories"] = ["OTHER"]
    row["dimension_assessments"][failed_dimension] = "FAIL"
    verification["questions_passed"] = 9
    verification["questions_rejected"] = 1
    verification["rejection_categories"]["OTHER"] = 1
    verification["local_failure_determination"] = "LOCAL"

    with pytest.raises(SourceReadyGenerationPilotError, match=message):
        validate_retry_v2_verification(REPO, JOB_ID, specs, preflight, generated, verification)

    row["reason_categories"] = [expected_category]
    verification["rejection_categories"]["OTHER"] = 0
    verification["rejection_categories"][expected_category] = 1
    result = validate_retry_v2_verification(REPO, JOB_ID, specs, preflight, generated, verification)
    assert result["status"] == "PILOT_NOT_ACCEPTED"


def test_retry_v2_verification_failure_state_fields_are_mutually_consistent():
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    generated = _v2_generated(specs, preflight)
    verification = _v2_verification(specs, preflight, generated)
    verification["local_failure_determination"] = "SYSTEMIC"

    with pytest.raises(SourceReadyGenerationPilotError, match="failure determination"):
        validate_retry_v2_verification(REPO, JOB_ID, specs, preflight, generated, verification)


def test_retry_v2_verification_material_duplication_blocks_acceptance_even_when_nine_pass():
    specs = _v2_item_specs()
    preflight = _v2_preflight(specs)
    generated = _v2_generated(specs, preflight)
    verification = _v2_verification(specs, preflight, generated)
    row = verification["verdicts"][0]
    row["verdict"] = "REJECTED_FOR_REVISION"
    row["reason_categories"] = ["MATERIAL_DUPLICATION"]
    row["dimension_assessments"]["semantic_duplication"] = "FAIL"
    verification["questions_passed"] = 9
    verification["questions_rejected"] = 1
    verification["rejection_categories"]["MATERIAL_DUPLICATION"] = 1
    verification["local_failure_determination"] = "LOCAL"
    verification["set_level_duplication"] = "LOW"

    result = validate_retry_v2_verification(REPO, JOB_ID, specs, preflight, generated, verification)
    assert result["status"] == "PILOT_NOT_ACCEPTED"


def test_retry_output_path_is_new_and_failed_pilot_path_is_rejected():
    assert validate_retry_output_path(REPO, RETRY_GENERATED_ARTIFACT_PATH) == RETRY_GENERATED_ARTIFACT_PATH
    with pytest.raises(SourceReadyGenerationPilotError, match="failed pilot"):
        validate_retry_output_path(REPO, "research/qgen/pilot/QGEN-PHELO-011.generated.json")


def test_existing_non_retry_generator_behavior_remains_valid():
    assert validate_generated_artifact(REPO, JOB_ID, _generated_artifact())["job_id"] == JOB_ID
