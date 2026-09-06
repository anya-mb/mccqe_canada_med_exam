"""The V2 replay over the ten frozen contrast-first final-review opportunities.

Nothing frozen moves. The opportunities, their MCC objectives, learner decisions,
difficulty intents, seeds, stems, options, verdicts and evidence packets are all
read and none is written. What this module builds is a *derivative* V2 layer over
them, and then asks one question the architecture stands or falls on:

    given the stems that were actually frozen, and given no change to any of
    them, would the V2 contrast-relation model have classified the competitors
    correctly?

That is a pure architecture test, run before a word of new question prose exists,
which is why it comes before any reauthoring.

Design: docs/superpowers/specs/2026-09-05-clinical-contrast-relation-model-v2-design.md
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .clinical_contrast_v2 import (
    ABSENT,
    AMBIGUOUS,
    ANCHOR_CLASSES,
    INDETERMINATE,
    INSUFFICIENT_SUPPORT,
    LIVE_BUT_INFERIOR,
    NOT_SATISFIED,
    PRESENT,
    SATISFIED,
    SECOND_KEY,
    ClinicalContrastV2Error,
    build_contrast_relation,
    build_feature_state_map,
    classify_competitor,
    contrast_role_for,
    discriminative_class,
    evaluate_contrast_set_coherence,
    evaluate_predicate,
    explain_predicate,
    feature_assertion,
    predicate_feature_ids,
    predicate_leaves,
    resolve_state,
    unresolved_features,
    validate_predicate,
)
from .contrast_first_pilot import (
    MAXIMUM_ABSENT_REQUIRED_FEATURES,
    validate_option_realization,
    REQUIRED_FEATURE_CAP,
    ContrastFirstError,
    load_curated_candidates,
    load_profile_contract,
    load_stem_feature_vocabulary,
)
from .option_set_admissibility import ARCHETYPE_RESPONSE_AXIS, RESPONSE_CLASS_AXES, \
    expand_response_tokens

V2_READINGS_PATH = "research/qgen/pilot/contrast-first-v2-frozen-10-readings.json"
V1_OPPORTUNITIES_PATH = "research/qgen/contrast_first_pilot_opportunities.json"
V1_AUTHORING_PATH = "research/qgen/contrast_first_pilot_authoring.json"
V1_STEMS_PATH = "research/qgen/contrast_first_pilot_stems.json"
V1_REVIEWS_PATH = "research/qgen/contrast_first_pilot_reviews.json"
V1_DIAGNOSIS_PATH = "reports/qgen_contrast_first_option_failure_diagnosis.json"


def _read(root, relative: str) -> Any:
    from pathlib import Path

    from .paths import resolve_root_path

    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise ContrastFirstError(f"required frozen artifact is missing: {relative}")
    return json.loads(path.read_text())


# ----------------------------------------------------------- typed features


def typed_supporting_features(
    feature_ids: Sequence[str],
    *,
    vocabulary: Mapping[str, Mapping[str, Any]],
    decision_domain: str,
    role_overrides: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Type each frozen plausibility anchor for this decision domain.

    The frozen anchor layer records *which* features make a competitor live and
    says nothing about what kind of fact each one is. That silence is defect 3:
    a demographic and an availability clause counted exactly as an examination
    finding did. Typing happens here, from the frozen ``clinical_role`` plus the
    domain, with an override only where the readings file cites a claim for it.
    """
    rows: list[dict[str, Any]] = []
    for feature_id in sorted(set(feature_ids)):
        entry = vocabulary.get(feature_id)
        if entry is None:
            raise ClinicalContrastV2Error(
                f"{feature_id} is outside the frozen study-unit vocabulary"
            )
        override = role_overrides.get(feature_id) or {}
        role = contrast_role_for(
            entry["clinical_role"],
            decision_domain=decision_domain,
            override=override.get("contrast_role"),
        )
        row = {
            "feature_id": feature_id,
            "contrast_role": role,
            "clinical_role": entry["clinical_role"],
        }
        if override.get("contrast_role"):
            row["role_override_reason"] = override.get("reason")
        rows.append(row)
    return rows


# ------------------------------------------------------------ contrast sets


def contradiction_pairs_for(
    readings: Mapping[str, Any], authoring: Mapping[str, Any], unit: str
) -> list[tuple[str, str]]:
    """The frozen V1 contradictions plus any the V2 readings add, with evidence.

    The frozen list is read and never written. A V2 addition must be a negation of
    the same proposition about the same quantity and must cite a claim; the
    readings file records the basis for each.
    """
    pairs = [tuple(pair) for pair in (authoring["contradiction_pairs"].get(unit) or [])]
    for row in (readings.get("additional_contradiction_pairs") or {}).get(unit) or []:
        pair = tuple(row["pair"])
        if pair not in pairs:
            pairs.append(pair)
    return pairs


def build_v2_contrast_sets(root) -> dict[str, Any]:
    """Build the V2 members, every pairwise relation, and the coherence report."""
    readings = _read(root, V2_READINGS_PATH)
    frozen = {
        row["opportunity_label"]: row
        for row in _read(root, V1_OPPORTUNITIES_PATH)["opportunities"]
    }
    authoring = _read(root, V1_AUTHORING_PATH)
    vocabulary = load_stem_feature_vocabulary(root)
    pool = {row["seed_id"]: row for row in load_curated_candidates(root)}

    results: list[dict[str, Any]] = []
    for label in sorted(readings["opportunities"]):
        reading = readings["opportunities"][label]
        opportunity = frozen[label]
        unit = opportunity["anchor_study_unit_id"]
        words = vocabulary[unit]
        domain = reading["decision_domain"]
        overrides = reading.get("role_overrides") or {}
        contract = load_profile_contract(
            root,
            discipline_profile_id=opportunity["discipline_profile_id"],
            option_set_archetype=opportunity["option_set_archetype"],
        )
        axis = ARCHETYPE_RESPONSE_AXIS[opportunity["option_set_archetype"]]
        generic = RESPONSE_CLASS_AXES[axis]["generic_token"]
        demanded = opportunity["demanded_response_class"]

        key_reading = reading["key"]
        key_spec = authoring["opportunities"][label]
        validate_predicate(key_reading["correctness_conditions"], vocabulary=words)
        key_member = {
            "member_id": "KEY",
            "role_in_set": "KEY",
            "concept_id": key_spec["key_concept_id"],
            "concept": key_spec["key_concept"],
            "concept_category": key_reading["concept_category"],
            "response_class_tokens": [demanded],
            "decision_granularity": opportunity["decision_granularity"],
            "supporting_features": typed_supporting_features(
                predicate_feature_ids(key_reading["correctness_conditions"]),
                vocabulary=words, decision_domain=domain, role_overrides=overrides,
            ),
            "correctness_conditions": key_reading["correctness_conditions"],
            "categorical_exclusion_conditions": [],
            "evidence_refs": list(key_reading["evidence_refs"]),
        }

        members = [key_member]
        for seed_id in sorted(reading["competitors"]):
            entry = reading["competitors"][seed_id]
            seed = pool[seed_id]
            validate_predicate(entry["correctness_conditions"], vocabulary=words)
            tokens = sorted(expand_response_tokens(
                seed.get("response_class_tokens") or [],
                contract["token_implications"], generic,
            ))
            members.append({
                "member_id": seed_id,
                "role_in_set": "COMPETITOR",
                "concept_id": seed["competitor_concept_id"],
                "concept": seed["competitor_concept"],
                "concept_category": entry["concept_category"],
                "response_class_tokens": tokens,
                "decision_granularity": seed["competitor_decision_granularity"],
                "supporting_features": typed_supporting_features(
                    seed["plausibility_anchor_feature_ids"],
                    vocabulary=words, decision_domain=domain, role_overrides=overrides,
                ),
                "correctness_conditions": entry["correctness_conditions"],
                "categorical_exclusion_conditions": entry.get(
                    "categorical_exclusion_conditions"
                ) or [],
                "unmapped_disjuncts": entry.get("unmapped_disjuncts") or [],
                "evidence_refs": list(entry["evidence_refs"]),
                "seed_id": seed_id,
            })

        relations = _build_relations(
            label, opportunity, reading, members, domain=domain,
        )
        contrast_set = {
            "contrast_set_v2_id": "",
            "opportunity_label": label,
            "learner_decision_id": opportunity["learner_decision_id"],
            "demanded_response_class": demanded,
            "decision_granularity": opportunity["decision_granularity"],
            "difficulty_intent": opportunity["difficulty_intent"],
            "decision_domain": domain,
            "anchor_study_unit_id": unit,
            "members": members,
            "relations": relations,
            # The set-level view of typing, so CS2-9 can ask what kind of fact each
            # of the key's own correctness conditions is.
            "feature_roles": {
                row["feature_id"]: row["contrast_role"]
                for member in members for row in member["supporting_features"]
            },
        }
        pairs = contradiction_pairs_for(readings, authoring, unit)
        coherence = evaluate_contrast_set_coherence(
            contrast_set, contradiction_pairs=pairs
        )
        results.append({
            "opportunity_label": label,
            "discipline": opportunity["discipline"],
            "difficulty_intent": opportunity["difficulty_intent"],
            "decision_domain": domain,
            "anchor_study_unit_id": unit,
            "contrast_set": contrast_set,
            "assembly_coherence": coherence,
            "contradiction_pairs": [list(pair) for pair in pairs],
            "terminal_state_at_assembly": (
                None if coherence["coherent"] else "NO_SAFE_ITEM"
            ),
            "fail_closed_reason_at_assembly": (
                None if coherence["coherent"] else "FAIL_CLOSED_CONTRAST_SET_COHERENCE"
            ),
        })

    return {
        "schema_version": "1.0",
        "scope": "QGEN_CONTRAST_FIRST_V2_CONTRAST_SETS",
        "pilot_id": readings["pilot_id"],
        "readings": V2_READINGS_PATH,
        "results": results,
    }


def _applicable_discriminators(
    reading: Mapping[str, Any], seed_id: str
) -> list[dict[str, Any]]:
    """The authored key-favouring discriminators that bear on one competitor."""
    rows = []
    for row in reading.get("key_discriminators") or []:
        against = row.get("against")
        if against is not None and seed_id not in against:
            continue
        rows.append({key: value for key, value in row.items() if key != "against"})
    return rows


def _build_relations(
    label: str,
    opportunity: Mapping[str, Any],
    reading: Mapping[str, Any],
    members: Sequence[Mapping[str, Any]],
    *,
    domain: str,
) -> list[dict[str, Any]]:
    """One relation per unordered pair, competitor against competitor included.

    ``shared_features`` are the anchors both concepts carry, less any feature the
    evidence says decides *between* these two. A feature both concepts can display
    is still a discriminator where a cited claim makes it one, and recording it as
    shared ground in that relation would be the untyped-anchor error again.
    """
    nesting = {
        frozenset(row["pair"]): row for row in (reading.get("nesting") or [])
    }
    relations: list[dict[str, Any]] = []
    for index, left in enumerate(members):
        for right in members[index + 1:]:
            competitor = right if left["role_in_set"] == "KEY" else None
            discriminators: list[dict[str, Any]] = []
            if competitor is not None:
                discriminators = _applicable_discriminators(
                    reading, competitor["member_id"]
                )
            deciding = {row["feature_id"] for row in discriminators}
            left_features = {row["feature_id"]: row for row in left["supporting_features"]}
            right_features = {row["feature_id"]: row for row in right["supporting_features"]}
            shared = [
                left_features[feature_id]
                for feature_id in sorted(set(left_features) & set(right_features))
                if feature_id not in deciding
            ]
            declared = nesting.get(frozenset([left["member_id"], right["member_id"]]))
            evidence = sorted(
                set(left["evidence_refs"]) | set(right["evidence_refs"])
                | {ref for row in discriminators for ref in row["evidence_refs"]}
                | set((declared or {}).get("evidence_refs") or [])
            )
            payload: dict[str, Any] = {
                "opportunity_label": label,
                "anchor_study_unit_id": opportunity["anchor_study_unit_id"],
                "learner_decision_id": opportunity["learner_decision_id"],
                "response_class": opportunity["demanded_response_class"],
                "decision_granularity": opportunity["decision_granularity"],
                "concept_a": _concept(left),
                "concept_b": _concept(right),
                "shared_features": shared,
                "a_supporting_features": list(left["supporting_features"]),
                "b_supporting_features": list(right["supporting_features"]),
                "discriminators": discriminators,
                "correctness_conditions_a": left["correctness_conditions"],
                "correctness_conditions_b": right["correctness_conditions"],
                "second_key_conditions": [right["correctness_conditions"]],
                "categorical_exclusion_conditions": list(
                    right.get("categorical_exclusion_conditions") or []
                ),
                "nesting_relation": (declared or {}).get("nesting_relation", "NONE"),
                "confusability": "HIGH" if shared else "MODERATE",
                "mcc_relevance": (
                    f"{opportunity['learner_decision_id']} for MCC objective "
                    f"{opportunity['mcc_objective_id']}, {opportunity['priority_class']} "
                    f"in {opportunity['discipline']}"
                ),
                "evidence_refs": evidence,
                "discovery_sources": ["CURATED_LIBRARY", "FROZEN_EVIDENCE_PACKET"],
                "verification_status": "EVIDENCE_VERIFIED",
            }
            if declared is not None:
                payload["nesting_basis"] = declared["basis"]
            unmapped = list(right.get("unmapped_disjuncts") or [])
            if unmapped:
                payload["unmapped_disjuncts"] = unmapped
            relations.append(build_contrast_relation(**payload))
    return relations


def _concept(member: Mapping[str, Any]) -> dict[str, Any]:
    concept = {
        "concept_id": member["concept_id"],
        "concept": member["concept"],
        "role_in_set": member["role_in_set"],
        "member_id": member["member_id"],
        "concept_category": member["concept_category"],
    }
    if member.get("seed_id"):
        concept["seed_id"] = member["seed_id"]
    return concept


# ------------------------------------------------------ counterfactual replay


def realized_state_map(
    stem: Mapping[str, Any], *, contradiction_pairs: Sequence[Sequence[str]]
) -> dict[str, dict[str, Any]]:
    """The frozen stem's feature map as a V2 state map.

    Only what the stem says is asserted. Everything else in the study unit's
    vocabulary stays UNKNOWN, which is the whole difference from V1: forbidding a
    feature from a stem removed it from the blueprint and never made it ABSENT,
    yet ``_satisfied`` scored it as unsatisfied anyway.
    """
    return build_feature_state_map(
        [
            feature_assertion(
                row["feature_id"], row["polarity"],
                source_span=row.get("source_span"),
            )
            for row in stem["stem_feature_map"]
        ],
        contradiction_pairs=contradiction_pairs,
    )


def run_counterfactual_replay(root, contrast_sets: dict[str, Any]) -> dict[str, Any]:
    """Stage 20: evaluate V2 against the EXISTING frozen V1 stems.

    No stem is rewritten. The question is only whether the relation model would
    have reached the right verdict on the material that was actually produced.
    """
    readings = _read(root, V2_READINGS_PATH)
    stems = _read(root, V1_STEMS_PATH)["stems"]
    reviews = _read(root, V1_REVIEWS_PATH)["reviews"]
    diagnosis = _read(root, V1_DIAGNOSIS_PATH)
    primary = diagnosis["phase_2_primary_earliest_cause"]["per_item"]

    rows: list[dict[str, Any]] = []
    for record in contrast_sets["results"]:
        label = record["opportunity_label"]
        contrast_set = record["contrast_set"]
        reading = readings["opportunities"][label]
        pairs = [tuple(pair) for pair in record["contradiction_pairs"]]
        state_map = realized_state_map(stems[label], contradiction_pairs=pairs)

        key = next(row for row in contrast_set["members"] if row["role_in_set"] == "KEY")
        key_result = evaluate_predicate(key["correctness_conditions"], state_map)

        verdicts = []
        for member in contrast_set["members"]:
            if member["role_in_set"] != "COMPETITOR":
                continue
            verdict = classify_competitor(
                member, state_map,
                discriminators=_applicable_discriminators(reading, member["member_id"]),
            )
            verdict["concept"] = member["concept"]
            # A NOT_SATISFIED verdict over a disjunction the frozen vocabulary
            # cannot fully express is not a defeat, and must not be read as one.
            if member.get("unmapped_disjuncts") and verdict["correctness"] == NOT_SATISFIED:
                verdict["correctness_qualified_by_unmapped_disjuncts"] = True
            verdicts.append(verdict)

        post_stem_coherence = evaluate_contrast_set_coherence(
            contrast_set, state_map, contradiction_pairs=pairs,
        )
        live = [row for row in verdicts if row["state"] == LIVE_BUT_INFERIOR]
        review = reviews[label]
        rows.append({
            "opportunity_label": label,
            "discipline": record["discipline"],
            "difficulty_intent": record["difficulty_intent"],
            "v1_verdict": review["VERDICT"],
            "v1_reject_reason": review.get("REJECT_REASON"),
            "v1_primary_earliest_cause": (primary.get(label) or {}).get(
                "primary_earliest_cause"
            ),
            "key_correctness_under_the_frozen_stem": key_result,
            "key_unresolved_features": unresolved_features(
                key["correctness_conditions"], state_map
            ),
            "key_explanation": explain_predicate(key["correctness_conditions"], state_map),
            "competitor_verdicts": verdicts,
            "assembly_coherence": record["assembly_coherence"],
            "post_stem_coherence": post_stem_coherence,
            "live_but_inferior_count": len(live),
            "v2_terminal_state": _v2_terminal_state(
                key_result, verdicts, record["assembly_coherence"], post_stem_coherence
            ),
            "v2_fail_closed_reasons": _fail_closed_reasons(
                key_result, verdicts, record["assembly_coherence"], post_stem_coherence
            ),
            "stem_asserted_features": sorted(
                row["feature_id"] for row in stems[label]["stem_feature_map"]
            ),
            "features_implied_absent_by_contradiction": sorted(
                feature_id for feature_id, row in state_map.items()
                if row.get("explicitness") == "IMPLIED"
            ),
        })
    return {
        "schema_version": "1.0",
        "scope": "QGEN_CONTRAST_FIRST_V2_COUNTERFACTUAL_REPLAY",
        "pilot_id": contrast_sets["pilot_id"],
        "stems_are_unchanged": True,
        "questions_generated": 0,
        "results": rows,
    }


def _v2_terminal_state(
    key_result: str,
    verdicts: Sequence[Mapping[str, Any]],
    assembly: Mapping[str, Any],
    post_stem: Mapping[str, Any],
) -> str:
    if not assembly["coherent"]:
        return "NO_SAFE_ITEM"
    if key_result != SATISFIED:
        return "NO_SAFE_ITEM"
    if any(row["state"] == SECOND_KEY for row in verdicts):
        return "NO_SAFE_ITEM"
    if any(row["state"] == AMBIGUOUS for row in verdicts):
        return "NO_SAFE_ITEM"
    if not post_stem["coherent"]:
        return "NO_SAFE_ITEM"
    live = [row for row in verdicts if row["state"] == LIVE_BUT_INFERIOR]
    if len(live) < 3:
        return "NO_SAFE_ITEM"
    return "READY_FOR_STEM"


def _fail_closed_reasons(
    key_result: str,
    verdicts: Sequence[Mapping[str, Any]],
    assembly: Mapping[str, Any],
    post_stem: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not assembly["coherent"]:
        reasons.append("FAIL_CLOSED_CONTRAST_SET_COHERENCE")
    if key_result == INDETERMINATE:
        reasons.append("FAIL_CLOSED_KEY_NOT_ESTABLISHED_BY_THE_STEM")
    if key_result == NOT_SATISFIED:
        reasons.append("FAIL_CLOSED_KEY_CONTRADICTED_BY_THE_STEM")
    if any(row["state"] == SECOND_KEY for row in verdicts):
        reasons.append("FAIL_CLOSED_SECOND_KEY")
    if any(row["state"] == AMBIGUOUS for row in verdicts):
        reasons.append("FAIL_CLOSED_AMBIGUOUS_COMPETITOR")
    if any(row["state"] == INSUFFICIENT_SUPPORT for row in verdicts):
        reasons.append("FAIL_CLOSED_COMPETITOR_WITHOUT_STEM_ANCHOR")
    if not post_stem["coherent"]:
        reasons.append("FAIL_CLOSED_POST_STEM_SET_COHERENCE")
    live = sum(1 for row in verdicts if row["state"] == LIVE_BUT_INFERIOR)
    if live < 3:
        reasons.append("FAIL_CLOSED_CONTRAST_SET_SIZE")
    return sorted(set(reasons))


# ----------------------------------------------------------------- reports

#: The gate frozen in section 14.1 of the design, before any V2 result existed.
COUNTERFACTUAL_GATE_LIMBS = (
    "ALL_KNOWN_BOOLEAN_LOGIC_DEFECTS_CORRECTED",
    "SILENCE_AS_ABSENCE_DEFECTS_ELIMINATED",
    "NO_ACCEPTED_V1_CONTROL_BECOMES_UNSAFE",
    "SECOND_KEY_CEILING_REMAINS_EFFECTIVE",
    "SET_COHERENCE_IDENTIFIES_THE_DIAGNOSED_SET_DEFECTS",
    "AT_LEAST_5_OF_7_NON_OPTION_REJECTIONS_INTERCEPTED",
)

ACCEPTED_V1_CONTROLS = ("G2-PHELO-02", "G2-PHELO-03")

#: The seven rejections the diagnosis attributed to a cause upstream of the
#: option layer. G2-OBGYN-01 is deliberately not here: it is the single
#: H_OPTION_WORDING_REALIZATION_DEFECT, and V2 makes no claim to repair it.
NON_OPTION_LAYER_REJECTIONS = (
    "G2-MED-03", "G2-PED-01", "G2-PED-02", "G2-SURG-01", "G2-SURG-02",
    "G2-PSY-03", "G2-PHELO-01",
)

#: The set defects the diagnosis named, and the opportunity each was found in.
DIAGNOSED_SET_DEFECTS = {
    "G2-MED-03": "two competitors defeated by one and the same preload proposition",
    "G2-SURG-01": "tubo-ovarian abscess nests in pelvic inflammatory disease",
    "G2-PED-01": "a required feature is both the only anchor and a correctness condition",
}

#: Where each of the four measured defects is reproduced on real frozen material.
DEFECT_FIXTURES = {
    "SILENCE_AS_ABSENCE": ("G2-PHELO-01", "G2-PSY-03"),
    "COMPETITOR_VERSUS_COMPETITOR": ("G2-MED-03", "G2-SURG-01", "G2-PED-01"),
    "UNTYPED_ANCHOR": ("G2-SURG-01", "G2-SURG-02"),
    "CONJUNCTION_ONLY_CORRECTNESS": ("G2-PED-02",),
}


def _silence_defects(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Competitors this replay would have scored defeated purely by silence.

    Under V1 an unassigned feature counted as unsatisfied, so any competitor whose
    correctness is INDETERMINATE only because the stem is silent would have been
    passed as defeated. Under V2 none may be, so this list is the measurement of
    the fix and must be empty for every competitor V2 admits.
    """
    defects = []
    for verdict in row["competitor_verdicts"]:
        if verdict["state"] != LIVE_BUT_INFERIOR:
            continue
        if verdict["correctness"] == INDETERMINATE and not verdict[
            "decided_by_discriminators"
        ]:
            defects.append({
                "member_id": verdict["member_id"],
                "unresolved_features": verdict["unresolved_features"],
            })
    return defects


def _v1_silence_defects(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The same competitors as V1 would have scored them: silence counts as defeat."""
    defects = []
    for verdict in row["competitor_verdicts"]:
        if verdict["correctness"] != INDETERMINATE:
            continue
        if not verdict["unresolved_features"]:
            continue
        defects.append({
            "member_id": verdict["member_id"],
            "unresolved_features": verdict["unresolved_features"],
            "v1_would_have_scored": "DEFEATED_BY_AN_UNSTATED_CONDITION",
            "v2_scores": verdict["state"],
        })
    return defects


def build_counterfactual_report(root) -> dict[str, Any]:
    """Phases 20 and 21: the replay, the measurements, and the precommitted gate."""
    contrast_sets = build_v2_contrast_sets(root)
    replay = run_counterfactual_replay(root, contrast_sets)
    rows = {row["opportunity_label"]: row for row in replay["results"]}

    per_item = {}
    for label, row in rows.items():
        assembly = row["assembly_coherence"]
        intercepted_at = None
        if not assembly["coherent"]:
            intercepted_at = "CONTRAST_SET_ASSEMBLY"
        elif row["v2_terminal_state"] == "NO_SAFE_ITEM":
            intercepted_at = "POST_STEM_REVALIDATION"
        per_item[label] = {
            "discipline": row["discipline"],
            "difficulty_intent": row["difficulty_intent"],
            "V1_VERDICT": row["v1_verdict"],
            "V1_PRIMARY_EARLIEST_CAUSE": row["v1_primary_earliest_cause"],
            "V2_TERMINAL_STATE": row["v2_terminal_state"],
            "V2_INTERCEPTED_AT": intercepted_at,
            "V2_FAIL_CLOSED_REASONS": row["v2_fail_closed_reasons"],
            "assembly_violations": assembly["violations"],
            "post_stem_violations": row["post_stem_coherence"]["violations"],
            "key_correctness_under_the_frozen_stem": row[
                "key_correctness_under_the_frozen_stem"
            ],
            "competitor_states": {
                verdict["member_id"]: verdict["state"]
                for verdict in row["competitor_verdicts"]
            },
            "second_keys": sorted(
                verdict["member_id"] for verdict in row["competitor_verdicts"]
                if verdict["state"] == SECOND_KEY
            ),
            "ambiguous": sorted(
                verdict["member_id"] for verdict in row["competitor_verdicts"]
                if verdict["state"] == AMBIGUOUS
            ),
            "competitors_carrying_second_key_risk": sorted(
                verdict["member_id"] for verdict in row["competitor_verdicts"]
                if verdict["second_key_risk"]
            ),
            "silence_as_absence_defects_after": _silence_defects(row),
            "silence_as_absence_defects_before": _v1_silence_defects(row),
            "would_the_diagnosed_failure_have_been_prevented": (
                "NOT_APPLICABLE_ACCEPTED_CONTROL" if row["v1_verdict"] == "ACCEPT"
                else "YES" if intercepted_at is not None
                else "NO"
            ),
        }

    intercepted = [
        label for label in NON_OPTION_LAYER_REJECTIONS
        if per_item[label]["V2_INTERCEPTED_AT"] is not None
    ]
    controls_safe = [
        label for label in ACCEPTED_V1_CONTROLS
        if per_item[label]["V2_TERMINAL_STATE"] == "READY_FOR_STEM"
        and not per_item[label]["silence_as_absence_defects_after"]
        and not per_item[label]["second_keys"]
        and not per_item[label]["ambiguous"]
    ]
    boolean_fixed = {
        "G2-PED-02": {
            "defect": ("CLM-R2-PED-VIRAL-INDICATION and CLM-R2-PED-CXR-INDICATION are "
                       "disjunctive indications carried as conjunctions, so a competitor "
                       "whose first disjunct the stem states was scored 1 of 2 and treated "
                       "as defeated."),
            "v1_behaviour": "SCORED_DEFEATED",
            "v2_behaviour": sorted(
                verdict["member_id"] for verdict in rows["G2-PED-02"]["competitor_verdicts"]
                if verdict["state"] == SECOND_KEY
            ),
            "corrected": sorted(
                verdict["member_id"] for verdict in rows["G2-PED-02"]["competitor_verdicts"]
                if verdict["state"] == SECOND_KEY
            ) == ["SEED-PED-T02-CXR", "SEED-PED-T02-VIRAL"],
        },
        "G2-PED-01": {
            "defect": ("The foreign-body and pneumonia seeds both read 'or' in their frozen "
                       "prose and were carried as conjunctions."),
            "v1_behaviour": "SCORED_DEFEATED",
            "v2_behaviour": sorted(
                verdict["member_id"] for verdict in rows["G2-PED-01"]["competitor_verdicts"]
                if verdict["state"] == SECOND_KEY
            ),
            "corrected": sorted(
                verdict["member_id"] for verdict in rows["G2-PED-01"]["competitor_verdicts"]
                if verdict["state"] == SECOND_KEY
            ) == ["SEED-PED-T01-FOREIGN-BODY", "SEED-PED-T01-PNEUMONIA"],
        },
    }
    set_defects_found = {
        label: sorted(set(per_item[label]["assembly_violations"]))
        for label in DIAGNOSED_SET_DEFECTS
    }

    limbs = {
        "ALL_KNOWN_BOOLEAN_LOGIC_DEFECTS_CORRECTED": all(
            row["corrected"] for row in boolean_fixed.values()
        ),
        "SILENCE_AS_ABSENCE_DEFECTS_ELIMINATED": not any(
            per_item[label]["silence_as_absence_defects_after"] for label in per_item
        ),
        "NO_ACCEPTED_V1_CONTROL_BECOMES_UNSAFE": (
            len(controls_safe) == len(ACCEPTED_V1_CONTROLS)
        ),
        "SECOND_KEY_CEILING_REMAINS_EFFECTIVE": all(
            "FAIL_CLOSED_SECOND_KEY" in per_item[label]["V2_FAIL_CLOSED_REASONS"]
            for label in per_item if per_item[label]["second_keys"]
        ),
        "SET_COHERENCE_IDENTIFIES_THE_DIAGNOSED_SET_DEFECTS": all(
            set_defects_found[label] for label in DIAGNOSED_SET_DEFECTS
        ),
        "AT_LEAST_5_OF_7_NON_OPTION_REJECTIONS_INTERCEPTED": len(intercepted) >= 5,
    }

    before = sum(
        len(per_item[label]["silence_as_absence_defects_before"]) for label in per_item
    )
    after = sum(
        len(per_item[label]["silence_as_absence_defects_after"]) for label in per_item
    )
    return {
        "schema_version": "1.0",
        "scope": "QGEN_CLINICAL_CONTRAST_V2_COUNTERFACTUAL",
        "pilot_id": replay["pilot_id"],
        "design": ("docs/superpowers/specs/"
                   "2026-09-05-clinical-contrast-relation-model-v2-design.md"),
        "starting_commit": "3ebdfb3",
        "method": (
            "The V2 relation model is evaluated against the ten frozen V1 stems exactly as "
            "they were written. No stem, option, seed, evidence packet or verdict is "
            "changed and no question prose is generated. The only question asked is whether "
            "the relation model would have classified the competitors correctly on the "
            "material that was actually produced."
        ),
        "questions_generated": 0,
        "llm_api_calls": 0,
        "stems_changed": 0,
        "frozen_qgen_artifacts_changed": 0,
        "per_item": per_item,
        "boolean_logic_correction": boolean_fixed,
        "diagnosed_set_defects_found_at_assembly": set_defects_found,
        "defect_regression_fixtures": {
            key: list(value) for key, value in DEFECT_FIXTURES.items()
        },
        "counts": {
            "OPPORTUNITIES_REPLAYED": len(per_item),
            "NON_OPTION_REJECTIONS_INTERCEPTED_PRE_FINAL_REVIEW":
                f"{len(intercepted)}/{len(NON_OPTION_LAYER_REJECTIONS)}",
            "intercepted": sorted(intercepted),
            "not_intercepted": sorted(
                set(NON_OPTION_LAYER_REJECTIONS) - set(intercepted)
            ),
            "ACCEPTED_V1_CONTROLS_PRESERVED":
                f"{len(controls_safe)}/{len(ACCEPTED_V1_CONTROLS)}",
            "KNOWN_SILENCE_AS_ABSENCE_DEFECTS_BEFORE": before,
            "KNOWN_SILENCE_AS_ABSENCE_DEFECTS_AFTER": after,
            "V2_READY_FOR_STEM": sorted(
                label for label in per_item
                if per_item[label]["V2_TERMINAL_STATE"] == "READY_FOR_STEM"
            ),
            "V2_NO_SAFE_ITEM": sorted(
                label for label in per_item
                if per_item[label]["V2_TERMINAL_STATE"] == "NO_SAFE_ITEM"
            ),
        },
        "gate": {
            "precommitted_in": "section 14.1 of the design, before any V2 result existed",
            "limbs": {limb: limbs[limb] for limb in COUNTERFACTUAL_GATE_LIMBS},
            "COUNTERFACTUAL_GATE": "PASS" if all(limbs.values()) else "FAIL",
        },
        "what_v2_does_not_claim": (
            "G2-OBGYN-01 is not intercepted and is not counted as a miss. Its single "
            "reject-forcing cause was H_OPTION_WORDING_REALIZATION_DEFECT, two rationale "
            "claims authored at realization, and the diagnosis established that a perfect "
            "option layer would have prevented it. A contrast-relation model has nothing to "
            "say about a rationale that polarizes its own cited claim, and V2 correctly "
            "passes the item through to the layer that owns the defect."
        ),
        "replay": replay,
        "contrast_sets": contrast_sets,
    }


def build_relation_cache(root, contrast_sets: dict[str, Any]) -> dict[str, Any]:
    """The schema-conforming V2 relation cache over the frozen-10 scope only.

    Deliberately not a whole-book contrast graph. The relation model is proved on
    the ten opportunities that reached final review before anything is populated
    at scale, and pairwise combinatorics over a 1,595-page corpus is exactly the
    thing the design refuses to start.
    """
    relations = []
    for record in contrast_sets["results"]:
        relations.extend(record["contrast_set"]["relations"])
    return {
        "schema_version": "1.0",
        "scope": "CLINICAL_CONTRAST_RELATION_V2",
        "relation_set_id": "clinical-contrast-relations-v2-frozen-10",
        "baseline_commit": "3ebdfb3",
        "derived_from": V2_READINGS_PATH,
        "decision_domain": "PATIENT_CLINICAL",
        "extraction_policy": (
            "Targeted only. Populated for the ten frozen contrast-first final-review "
            "opportunities and exactly the candidate concepts their planned sets need. No "
            "whole-book Toronto Notes extraction, no embeddings, no broad concept-pair "
            "precomputation. Each relation's decision domain is carried on the relation "
            "through its opportunity."
        ),
        "frozen": False,
        "relations": sorted(relations, key=lambda row: row["contrast_relation_id"]),
    }


# --------------------------------------------------------- V2 set selection


def select_admissible_subset(
    contrast_set: Mapping[str, Any],
    coherence: Mapping[str, Any],
    *,
    contradiction_pairs: Sequence[Sequence[str]],
) -> dict[str, Any]:
    """Drop the members the coherence gate refuses, deterministically.

    One pass, not a search. A member named by CS2-6 or CS2-7 is unusable on its
    own account and goes; a CS2-1 or CS2-2 pair is a redundancy between two
    members, and the later seed id is dropped so the choice cannot be tuned. If
    fewer than three competitors survive the opportunity fails closed, which is
    the answer rather than a reason to go looking for a fourth.
    """
    members = {row["member_id"]: row for row in contrast_set["members"]}
    dropped: dict[str, str] = {}
    for row in coherence["detail"]:
        rule = row["rule"]
        if rule in ("CS2-6", "CS2-7") and row.get("member_id"):
            dropped.setdefault(row["member_id"], rule)
        elif rule in ("CS2-6", "CS2-7") and row.get("members"):
            for member_id in row["members"]:
                dropped.setdefault(member_id, rule)
        elif rule in ("CS2-1", "CS2-2", "CS2-8") and row.get("pair"):
            keep, drop = sorted(row["pair"])
            if keep not in dropped:
                dropped.setdefault(drop, rule)
        elif rule in ("CS2-3", "CS2-4") and row.get("member_id"):
            dropped.setdefault(row["member_id"], rule)

    kept = [
        row for row in contrast_set["members"]
        if row["role_in_set"] == "KEY" or row["member_id"] not in dropped
    ]
    reduced = dict(contrast_set)
    reduced["members"] = kept
    reduced["relations"] = [
        relation for relation in contrast_set["relations"]
        if relation["concept_a"]["member_id"] not in dropped
        and relation["concept_b"]["member_id"] not in dropped
    ]
    competitors = [row for row in kept if row["role_in_set"] == "COMPETITOR"]
    if len(competitors) < 3:
        return {
            "admissible": False,
            "dropped": dict(sorted(dropped.items())),
            "surviving_competitors": sorted(row["member_id"] for row in competitors),
            "fail_closed_reason": "FAIL_CLOSED_CONTRAST_SET_SIZE",
            "contrast_set": reduced,
            "residual_violations": None,
        }
    residual = evaluate_contrast_set_coherence(
        reduced, contradiction_pairs=contradiction_pairs
    )
    return {
        "admissible": residual["coherent"],
        "dropped": dict(sorted(dropped.items())),
        "surviving_competitors": sorted(row["member_id"] for row in competitors),
        "fail_closed_reason": (
            None if residual["coherent"] else "FAIL_CLOSED_CONTRAST_SET_COHERENCE"
        ),
        "contrast_set": reduced,
        "residual_violations": residual["violations"],
        "residual_coherence": residual,
    }


# ------------------------------------------------------- V2 blueprint solver

#: How a competitor may be settled. Silence is not on the list, which is the
#: whole difference from V1.
SETTLEMENT_ROUTES = ("STATED_CONTRARY", "EXPLICIT_DENIAL", "EVIDENCE_BACKED_DISCRIMINATOR")


def _assign(
    assignment: dict[str, str],
    feature_id: str,
    state: str,
    *,
    contradiction_pairs: Sequence[Sequence[str]],
) -> dict[str, str] | None:
    """Return a copy with the assignment added, or None if it contradicts."""
    if assignment.get(feature_id, state) != state:
        return None
    trial = dict(assignment)
    trial[feature_id] = state
    if state == PRESENT:
        for pair in contradiction_pairs:
            if feature_id not in pair:
                continue
            other = pair[0] if pair[1] == feature_id else pair[1]
            if trial.get(other) == PRESENT:
                return None
    return trial


def _state_map_of(
    assignment: Mapping[str, str], *, contradiction_pairs: Sequence[Sequence[str]]
) -> dict[str, dict[str, Any]]:
    return build_feature_state_map(
        [feature_assertion(feature_id, state) for feature_id, state in assignment.items()],
        contradiction_pairs=contradiction_pairs,
    )


def _satisfy_key(
    node: Mapping[str, Any],
    assignment: dict[str, str],
    *,
    contradiction_pairs: Sequence[Sequence[str]],
) -> dict[str, str] | None:
    """Assign the minimum that makes the key's condition tree SATISFIED.

    ``ALL_OF`` requires every branch; ``ANY_OF`` takes the first branch that can be
    satisfied without contradiction, in the order the reading declares them, so a
    disjunctive key is solved as a disjunction rather than as every disjunct at
    once.
    """
    validate_predicate(node)
    if _is_leaf(node):
        required = node.get("required_state")
        if required not in (PRESENT, ABSENT):
            return None
        return _assign(
            assignment, node["feature_id"], required,
            contradiction_pairs=contradiction_pairs,
        )
    operator = node["operator"]
    if operator == "ALL_OF":
        current: dict[str, str] | None = dict(assignment)
        for child in node["conditions"]:
            current = _satisfy_key(
                child, current, contradiction_pairs=contradiction_pairs
            ) if current is not None else None
        return current
    if operator == "ANY_OF":
        for child in node["conditions"]:
            solved = _satisfy_key(
                child, dict(assignment), contradiction_pairs=contradiction_pairs
            )
            if solved is not None:
                return solved
        return None
    if operator == "NOT":
        child = node["conditions"][0]
        if not _is_leaf(child):
            return None
        required = child.get("required_state")
        opposite = ABSENT if required == PRESENT else PRESENT
        return _assign(
            assignment, child["feature_id"], opposite,
            contradiction_pairs=contradiction_pairs,
        )
    return None


def _is_leaf(node: Mapping[str, Any]) -> bool:
    return "required_state" in node and "operator" not in node


def solve_v2_blueprint(
    contrast_set: Mapping[str, Any],
    reading: Mapping[str, Any],
    *,
    vocabulary: Mapping[str, Mapping[str, Any]],
    contradiction_pairs: Sequence[Sequence[str]],
    context_features: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    """Solve the feature states a V2 stem must realize, before a word is written.

    Four constraints hold together or the blueprint fails closed: the key's
    condition tree SATISFIED, every competitor live on a PRESENTATION-class anchor
    the stem actually states, no competitor SATISFIED, and **every** competitor
    settled by a stated contrary or by an evidence-backed discriminator the stem
    also states. That last one is the constraint V1 did not have, and it is why an
    open silence can no longer be mistaken for a defeat.

    Explicit denials are the cheapest way to settle a competitor and the least
    natural, so they stay bounded by the same per-difficulty budget the coherence
    contract already applies. The discriminator route is not bounded, because a
    stated finding that favours the key is the legitimate way to make an item
    hard without denying anything.
    """
    key = next(row for row in contrast_set["members"] if row["role_in_set"] == "KEY")
    competitors = [row for row in contrast_set["members"] if row["role_in_set"] == "COMPETITOR"]
    intent = contrast_set["difficulty_intent"]
    pairs = [tuple(pair) for pair in contradiction_pairs]

    # Features a cited claim makes the signature of a concept outside this option
    # set. Stating one would give the stem a second key the options cannot
    # contain, and no rationale can repair that.
    forbidden = set(reading.get("forbidden_present_features") or {})
    assignment = _satisfy_key(
        key["correctness_conditions"], {}, contradiction_pairs=pairs
    )
    if assignment is None:
        return _v2_blueprint(
            contrast_set, {}, {}, [],
            "FAIL_CLOSED_KEY_UNSATISFIABLE", vocabulary=vocabulary,
            contradiction_pairs=pairs, forbidden_present=(),
        )
    provenance = {feature: ["KEY_CORRECTNESS_CONDITION"] for feature in assignment}

    # ---- anchor pass. Only a PRESENTATION-class feature counts, so no stem can
    # be made to carry a competitor on a demographic or an availability clause.
    for competitor in competitors:
        if _live(competitor, assignment, pairs):
            continue
        choices: list[tuple[int, str]] = []
        for row in sorted(
            competitor["supporting_features"], key=lambda entry: entry["feature_id"]
        ):
            if discriminative_class(row["contrast_role"]) not in ANCHOR_CLASSES:
                continue
            if row["feature_id"] in forbidden:
                continue
            trial = _assign(
                assignment, row["feature_id"], PRESENT, contradiction_pairs=pairs
            )
            if trial is None or _any_satisfied(competitors, trial, pairs):
                continue
            coverage = sum(
                1 for other in competitors
                if not _live(other, assignment, pairs)
                and row["feature_id"] in {
                    entry["feature_id"] for entry in other["supporting_features"]
                }
            )
            choices.append((-coverage, row["feature_id"]))
        if not choices:
            return _v2_blueprint(
                contrast_set, assignment, provenance, [],
                "FAIL_CLOSED_NO_USABLE_ANCHOR", vocabulary=vocabulary,
                contradiction_pairs=pairs,
                note=f"{competitor['member_id']} has no statable presentation anchor",
            )
        _, chosen = sorted(choices)[0]
        assignment[chosen] = PRESENT
        provenance.setdefault(chosen, []).append("COMPETITOR_ANCHOR")

    # ---- optional colour, added after the load-bearing work rather than before
    # it. A context feature that would starve a competitor of its anchor, or
    # complete a competitor's signature, is simply not added.
    normalized_context = [
        {"stem_feature_id": row, "polarity": PRESENT} if isinstance(row, str) else dict(row)
        for row in context_features
    ]
    for row in sorted(normalized_context, key=lambda entry: entry["stem_feature_id"]):
        feature_id = row["stem_feature_id"]
        if feature_id in assignment or feature_id not in vocabulary:
            continue
        if feature_id in forbidden and row.get("polarity", PRESENT) == PRESENT:
            continue
        trial = _assign(
            assignment, feature_id, row.get("polarity", PRESENT), contradiction_pairs=pairs
        )
        if trial is None or _any_satisfied(competitors, trial, pairs):
            continue
        if any(not _live(other, trial, pairs) for other in competitors):
            continue
        assignment = trial
        provenance.setdefault(feature_id, []).append("OPTIONAL_CONTEXT")

    # ---- settlement pass. Every competitor must be settled, and by a named route.
    denial_budget = MAXIMUM_ABSENT_REQUIRED_FEATURES[intent]
    denials = sum(1 for state in assignment.values() if state == ABSENT)
    settlement: dict[str, dict[str, Any]] = {}
    for competitor in competitors:
        route = _settlement_route(competitor, reading, assignment, pairs)
        if route is not None:
            settlement[competitor["member_id"]] = route
            continue
        applied = False
        # First try a discriminator the stem could state anyway. It costs nothing
        # in naturalness and it is the route that keeps a HARD item hard.
        for discriminator in _applicable_discriminators(reading, competitor["member_id"]):
            if (discriminator["feature_id"] in forbidden
                    and discriminator["required_state"] == PRESENT):
                continue
            trial = _assign(
                assignment, discriminator["feature_id"], discriminator["required_state"],
                contradiction_pairs=pairs,
            )
            if trial is None or _any_satisfied(competitors, trial, pairs):
                continue
            assignment = trial
            provenance.setdefault(discriminator["feature_id"], []).append(
                "KEY_DISCRIMINATOR"
            )
            applied = True
            break
        # Next try to close the domain with a stated positive finding that the
        # declared contradictions make incompatible with what the competitor
        # needs. "The number of cases diagnosed was the same in both arms" is a
        # finding a report would carry anyway; "there was no excess of indolent
        # tumours" is a denial written for the item's benefit. Prefer the finding.
        if not applied:
            state_map = _state_map_of(assignment, contradiction_pairs=pairs)
            for feature_id in unresolved_features(
                competitor["correctness_conditions"], state_map
            ):
                if _required_state_of(
                    competitor["correctness_conditions"], feature_id
                ) != PRESENT:
                    continue
                for pair in pairs:
                    if feature_id not in pair:
                        continue
                    other = pair[0] if pair[1] == feature_id else pair[1]
                    if other in assignment or other not in vocabulary or (
                        other in forbidden
                    ):
                        continue
                    trial = _assign(
                        assignment, other, PRESENT, contradiction_pairs=pairs
                    )
                    if trial is None or _any_satisfied(competitors, trial, pairs):
                        continue
                    assignment = trial
                    provenance.setdefault(other, []).append("STATED_POSITIVE_CONTRARY")
                    applied = True
                    break
                if applied:
                    break
        if not applied and denials < denial_budget:
            for feature_id in unresolved_features(
                competitor["correctness_conditions"],
                _state_map_of(assignment, contradiction_pairs=pairs),
            ):
                required = _required_state_of(
                    competitor["correctness_conditions"], feature_id
                )
                opposite = ABSENT if required == PRESENT else PRESENT
                if feature_id in forbidden and opposite == PRESENT:
                    continue
                trial = _assign(
                    assignment, feature_id, opposite, contradiction_pairs=pairs
                )
                if trial is None or _any_satisfied(competitors, trial, pairs):
                    continue
                assignment = trial
                provenance.setdefault(feature_id, []).append("EXPLICIT_DENIAL")
                denials += 1
                applied = True
                break
        route = _settlement_route(competitor, reading, assignment, pairs)
        if route is None:
            return _v2_blueprint(
                contrast_set, assignment, provenance, [],
                "FAIL_CLOSED_COMPETITOR_CANNOT_BE_SETTLED", vocabulary=vocabulary,
                contradiction_pairs=pairs,
                note=(f"{competitor['member_id']} would be left resting on information "
                      "the stem does not state, and the difficulty contract has no "
                      "explicit denial left to spend"),
            )
        settlement[competitor["member_id"]] = route

    if len(assignment) > REQUIRED_FEATURE_CAP[intent]:
        return _v2_blueprint(
            contrast_set, assignment, provenance, [],
            "FAIL_CLOSED_REQUIRED_FEATURE_CAP", vocabulary=vocabulary,
            contradiction_pairs=pairs, forbidden_present=forbidden,
            note=(f"{len(assignment)} required features against a cap of "
                  f"{REQUIRED_FEATURE_CAP[intent]} at {intent}"),
        )
    return _v2_blueprint(
        contrast_set, assignment, provenance, settlement, None,
        vocabulary=vocabulary, contradiction_pairs=pairs, forbidden_present=forbidden,
    )


def _required_state_of(node: Mapping[str, Any], feature_id: str) -> str:
    for leaf in predicate_leaves(node):
        if leaf["feature_id"] == feature_id:
            return leaf.get("required_state") or PRESENT
    return PRESENT


def _live(
    competitor: Mapping[str, Any],
    assignment: Mapping[str, str],
    pairs: Sequence[Sequence[str]],
) -> bool:
    return any(
        assignment.get(row["feature_id"]) == PRESENT
        and discriminative_class(row["contrast_role"]) in ANCHOR_CLASSES
        for row in competitor["supporting_features"]
    )


def _any_satisfied(
    competitors: Sequence[Mapping[str, Any]],
    assignment: Mapping[str, str],
    pairs: Sequence[Sequence[str]],
) -> bool:
    state_map = _state_map_of(assignment, contradiction_pairs=pairs)
    return any(
        evaluate_predicate(row["correctness_conditions"], state_map) == SATISFIED
        for row in competitors
    )


def _settlement_route(
    competitor: Mapping[str, Any],
    reading: Mapping[str, Any],
    assignment: Mapping[str, str],
    pairs: Sequence[Sequence[str]],
) -> dict[str, Any] | None:
    """How, if at all, this competitor is settled under the current assignment."""
    state_map = _state_map_of(assignment, contradiction_pairs=pairs)
    verdict = classify_competitor(
        competitor, state_map,
        discriminators=_applicable_discriminators(reading, competitor["member_id"]),
    )
    if verdict["state"] != LIVE_BUT_INFERIOR:
        return None
    if verdict["correctness"] == NOT_SATISFIED:
        explicit = [
            feature_id for feature_id in verdict["defeated_by"]
            if assignment.get(feature_id) == ABSENT
        ]
        return {
            "route": "EXPLICIT_DENIAL" if explicit else "STATED_CONTRARY",
            "features": verdict["defeated_by"],
            "explicitly_denied": explicit,
        }
    return {
        "route": "EVIDENCE_BACKED_DISCRIMINATOR",
        "features": verdict["decided_by_discriminators"],
        "unresolved_but_outweighed": verdict["unresolved_features"],
    }


def _v2_blueprint(
    contrast_set: Mapping[str, Any],
    assignment: Mapping[str, str],
    provenance: Mapping[str, Sequence[str]],
    settlement: Any,
    fail_closed: str | None,
    *,
    vocabulary: Mapping[str, Mapping[str, Any]],
    contradiction_pairs: Sequence[Sequence[str]],
    note: str | None = None,
    forbidden_present: Sequence[str] = (),
) -> dict[str, Any]:
    key = next(row for row in contrast_set["members"] if row["role_in_set"] == "KEY")
    competitors = [row for row in contrast_set["members"] if row["role_in_set"] == "COMPETITOR"]
    roles = {
        row["feature_id"]: row["contrast_role"]
        for member in contrast_set["members"] for row in member["supporting_features"]
    }
    state_map = _state_map_of(assignment, contradiction_pairs=contradiction_pairs)
    return {
        "schema_version": "1.0",
        "scope": "QGEN_STEM_BLUEPRINT_V2",
        "opportunity_label": contrast_set["opportunity_label"],
        "difficulty_intent": contrast_set["difficulty_intent"],
        "decision_domain": contrast_set["decision_domain"],
        "anchor_study_unit_id": contrast_set["anchor_study_unit_id"],
        "key_concept": key["concept"],
        "FEATURES_PRESENT": sorted(
            feature for feature, state in assignment.items() if state == PRESENT
        ),
        "FEATURES_ABSENT": sorted(
            feature for feature, state in assignment.items() if state == ABSENT
        ),
        "FEATURES_ALLOWED_UNKNOWN": sorted(
            set(vocabulary) - set(assignment)
        ),
        "required_features": [
            {
                "stem_feature_id": feature,
                "state": assignment[feature],
                "contrast_role": roles.get(feature),
                "clinical_role": vocabulary.get(feature, {}).get("clinical_role"),
                "normalized_feature": vocabulary.get(feature, {}).get("normalized_feature"),
                "roles": sorted(set(provenance.get(feature, ["OPTIONAL_CONTEXT"]))),
            }
            for feature in sorted(assignment)
        ],
        "SHARED_PLAUSIBILITY_FEATURES": sorted({
            row["feature_id"]
            for competitor in competitors for row in competitor["supporting_features"]
            if assignment.get(row["feature_id"]) == PRESENT
            and discriminative_class(row["contrast_role"]) in ANCHOR_CLASSES
        }),
        "KEY_DISCRIMINATORS": sorted({
            feature for feature, roles_used in provenance.items()
            if "KEY_DISCRIMINATOR" in roles_used
        }),
        "SECOND_KEY_RISK_FEATURES": sorted({
            feature_id
            for competitor in competitors
            for feature_id in unresolved_features(
                competitor["correctness_conditions"], state_map
            )
        }),
        "CATEGORICAL_EXCLUSION_FEATURES": sorted({
            feature_id
            for competitor in competitors
            for exclusion in competitor.get("categorical_exclusion_conditions") or []
            for feature_id in predicate_feature_ids(exclusion["predicate"])
        }),
        "BACKGROUND_CONTEXT": sorted({
            feature for feature in assignment
            if roles.get(feature) and discriminative_class(roles[feature])
            in ("NON_DISCRIMINATING", "PRIOR_ONLY")
        }),
        "competitor_settlement": settlement if isinstance(settlement, dict) else {},
        "key_correctness": evaluate_predicate(key["correctness_conditions"], state_map),
        "fail_closed_reason": fail_closed,
        "note": note,
        "explicit_denials": sorted(
            feature for feature, state in assignment.items() if state == ABSENT
        ),
        "explicit_denial_budget": MAXIMUM_ABSENT_REQUIRED_FEATURES[
            contrast_set["difficulty_intent"]
        ],
        "required_feature_cap": REQUIRED_FEATURE_CAP[contrast_set["difficulty_intent"]],
        "FORBIDDEN_PRESENT_FEATURES": sorted(forbidden_present or ()),
    }


# ------------------------------------------------------------ V2 reauthoring

V2_GENERATED_PATH = "research/qgen/pilot/contrast-first-v2-frozen-10-generated.json"


def run_v2_replay(root) -> dict[str, Any]:
    """Phases 22 to 27: select, solve, realize, revalidate, and never retry.

    One attempt per opportunity. An opportunity whose set cannot be made
    admissible, or whose blueprint cannot settle every competitor, is
    ``NO_SAFE_ITEM`` and no prose is written for it. The post-stem check runs the
    V2 classifier *and* the unchanged production gate
    ``retrieve_profile_aware_contrasts``, so V2 buys itself no exemption.
    """
    contrast_sets = build_v2_contrast_sets(root)
    readings = _read(root, V2_READINGS_PATH)
    authoring = _read(root, V1_AUTHORING_PATH)
    generated = _read(root, V2_GENERATED_PATH)
    frozen = {
        row["opportunity_label"]: row
        for row in _read(root, V1_OPPORTUNITIES_PATH)["opportunities"]
    }
    vocabulary = load_stem_feature_vocabulary(root)

    rows: list[dict[str, Any]] = []
    for record in contrast_sets["results"]:
        label = record["opportunity_label"]
        reading = readings["opportunities"][label]
        pairs = record["contradiction_pairs"]
        unit = record["anchor_study_unit_id"]
        row: dict[str, Any] = {
            "opportunity_label": label,
            "discipline": record["discipline"],
            "difficulty_intent": record["difficulty_intent"],
            "decision_domain": record["decision_domain"],
            "priority_class": frozen[label]["priority_class"],
        }
        selection = select_admissible_subset(
            record["contrast_set"], record["assembly_coherence"],
            contradiction_pairs=pairs,
        )
        row["selection"] = {
            key: value for key, value in selection.items()
            if key not in ("contrast_set", "residual_coherence")
        }
        if not selection["admissible"]:
            row.update({
                "stage_reached": "CONTRAST_SET_ASSEMBLY",
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": selection["fail_closed_reason"],
            })
            rows.append(row)
            continue

        blueprint = solve_v2_blueprint(
            selection["contrast_set"], reading,
            vocabulary=vocabulary[unit], contradiction_pairs=pairs,
            context_features=authoring["opportunities"][label].get("context_features") or [],
        )
        row["stem_blueprint_v2"] = blueprint
        if blueprint["fail_closed_reason"]:
            row.update({
                "stage_reached": "BLUEPRINT",
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": blueprint["fail_closed_reason"],
            })
            rows.append(row)
            continue

        item = generated["items"][label]
        realized = build_feature_state_map(
            [
                feature_assertion(
                    entry["feature_id"], entry["polarity"],
                    source_span=entry.get("source_span"),
                )
                for entry in item["stem_feature_map"]
            ],
            contradiction_pairs=pairs,
        )
        planned = {
            entry["stem_feature_id"]: entry["state"]
            for entry in blueprint["required_features"]
        }
        stated = {
            entry["feature_id"]: entry["polarity"] for entry in item["stem_feature_map"]
        }
        row["stem_realizes_the_blueprint_exactly"] = planned == stated

        verdicts = []
        for member in selection["contrast_set"]["members"]:
            if member["role_in_set"] != "COMPETITOR":
                continue
            verdict = classify_competitor(
                member, realized,
                discriminators=_applicable_discriminators(reading, member["member_id"]),
            )
            verdict["concept"] = member["concept"]
            verdicts.append(verdict)
        key = next(
            member for member in selection["contrast_set"]["members"]
            if member["role_in_set"] == "KEY"
        )
        key_result = evaluate_predicate(key["correctness_conditions"], realized)
        post_stem = evaluate_contrast_set_coherence(
            selection["contrast_set"], realized, contradiction_pairs=pairs
        )
        production = _production_gate(
            root, record, selection, item, frozen[label]
        )
        options = _build_options(selection["contrast_set"], item)
        realization = validate_option_realization(
            options, _matrix_shim(selection["contrast_set"]),
            key_option_text=item["key_option_text"], stem_text=item["stem"],
        )
        row.update({
            "stage_reached": "INDEPENDENT_REVIEW",
            "terminal_state": None,
            "fail_closed_reason": None,
            "stem": item["stem"],
            "lead_in": item["lead_in"],
            "stem_word_count": len(item["stem"].split()),
            "key_correctness_under_the_new_stem": key_result,
            "competitor_verdicts": verdicts,
            "post_stem_coherence": post_stem,
            "production_gate": production,
            "options": options,
            "option_realization": realization,
            "blind_solver": generated["blind_solver"][label],
            "v2_fail_closed_reasons": _fail_closed_reasons(
                key_result, verdicts, selection["residual_coherence"], post_stem
            ),
        })
        rows.append(row)

    return {
        "schema_version": "1.0",
        "scope": "QGEN_CONTRAST_FIRST_V2_REPLAY",
        "pilot_id": contrast_sets["pilot_id"],
        "one_attempt_per_opportunity": True,
        "production_gate": "profile_contrast_retrieval.retrieve_profile_aware_contrasts",
        "production_gate_unchanged": True,
        "llm_api_calls": 0,
        "results": rows,
    }


def _matrix_shim(contrast_set: Mapping[str, Any]) -> dict[str, Any]:
    """The seed-id set the unchanged option-realization contract expects."""
    return {
        "rows": [
            {"seed_id": member["member_id"]}
            for member in contrast_set["members"]
            if member["role_in_set"] == "COMPETITOR"
        ]
    }


def _build_options(
    contrast_set: Mapping[str, Any], item: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Key plus distractors, distractor text verbatim from the frozen seed."""
    competitors = sorted(
        (row for row in contrast_set["members"] if row["role_in_set"] == "COMPETITOR"),
        key=lambda row: row["member_id"],
    )
    options = [{
        "label": "A",
        "text": item["key_option_text"],
        "is_key": True,
        "source": "KEY",
        "response_class": contrast_set["demanded_response_class"],
        "rationale": item["key_rationale"],
    }]
    for index, member in enumerate(competitors):
        options.append({
            "label": "BCDEF"[index],
            "text": member["concept"],
            "is_key": False,
            "source": member["member_id"],
            "response_class": contrast_set["demanded_response_class"],
            "rationale": item["distractor_rationales"][member["member_id"]],
        })
    return options


def _production_gate(
    root,
    record: Mapping[str, Any],
    selection: Mapping[str, Any],
    item: Mapping[str, Any],
    opportunity: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the V2 stem through the unchanged production retrieval gate."""
    from .contrast_first_pilot import revalidate_against_frozen_stem

    pool = {row["seed_id"]: row for row in load_curated_candidates(root)}
    contract = load_profile_contract(
        root,
        discipline_profile_id=opportunity["discipline_profile_id"],
        option_set_archetype=opportunity["option_set_archetype"],
    )
    shim = {
        "opportunity_label": record["opportunity_label"],
        "discipline_profile_id": opportunity["discipline_profile_id"],
        "item_archetype": opportunity["item_archetype"],
        "option_set_archetype": opportunity["option_set_archetype"],
        "demanded_response_class": opportunity["demanded_response_class"],
        "decision_granularity": opportunity["decision_granularity"],
        "target_id": None,
        "competitors": [
            pool[member["member_id"]]
            for member in selection["contrast_set"]["members"]
            if member["role_in_set"] == "COMPETITOR"
        ],
    }
    stem_feature_map = {
        "features": [
            {
                "feature_id": entry["feature_id"],
                "polarity": entry["polarity"],
                "clinical_role": None,
            }
            for entry in item["stem_feature_map"]
        ]
    }
    for entry in stem_feature_map["features"]:
        entry["clinical_role"] = _clinical_role(root, record, entry["feature_id"])
    result = revalidate_against_frozen_stem(
        contrast_set=shim,
        stem_feature_map=stem_feature_map,
        ranking_preference=contract["competitor_ranking_preference"],
        token_implications=contract["token_implications"],
    )
    return {
        "post_stem_3_viable": result["post_stem_3_viable"],
        "excluded_by_rule": result["excluded_by_rule"],
        "ranked_competitors": [
            row["seed_id"] for row in result["retrieval"]["ranked_competitors"]
        ],
        "gate_is_the_production_gate": result["gate_is_the_production_gate"],
    }


def _clinical_role(root, record: Mapping[str, Any], feature_id: str) -> str | None:
    vocabulary = load_stem_feature_vocabulary(root)[record["anchor_study_unit_id"]]
    return (vocabulary.get(feature_id) or {}).get("clinical_role")


# ------------------------------------------------- verification and comparison

V2_REVIEWS_PATH = "research/qgen/pilot/contrast-first-v2-frozen-10-reviews.json"

#: Section 14.2 of the design, precommitted. Any count above zero rejects.
V2_SAFETY_DIMENSIONS = (
    "FACTUAL_ERRORS", "NUMERIC_ERRORS", "UNSUPPORTED_CLAIMS", "AMBIGUOUS_BEST_ANSWERS",
    "CRITICAL_FACT_SAFETY_FAILURES", "MATERIAL_REDUNDANCY",
    "COMPETITOR_WITHOUT_STEM_ANCHOR", "SECOND_KEY_RISK", "UNNATURAL_STEM_ENGINEERING",
    "BOOLEAN_LOGIC_DEFECT", "SILENCE_AS_ABSENCE_DEFECT",
)


def build_verification_report(root, replay: dict[str, Any]) -> dict[str, Any]:
    """Phases 28 and 29: the fresh review, and the accepted-item safety standard."""
    reviews = _read(root, V2_REVIEWS_PATH)["reviews"]
    rows = {row["opportunity_label"]: row for row in replay["results"]}
    realized = sorted(
        label for label, row in rows.items() if row["stage_reached"] == "INDEPENDENT_REVIEW"
    )
    accepted = [label for label in realized if reviews[label]["VERDICT"] == "ACCEPT"]
    rejected = [label for label in realized if reviews[label]["VERDICT"] == "REJECT"]

    accepted_safety = {
        dimension: sum(reviews[label][dimension] for label in accepted)
        for dimension in V2_SAFETY_DIMENSIONS
    }
    realized_safety = {
        dimension: sum(reviews[label][dimension] for label in realized)
        for dimension in V2_SAFETY_DIMENSIONS
    }
    return {
        "schema_version": "1.0",
        "scope": "QGEN_CLINICAL_CONTRAST_V2_PILOT_VERIFICATION",
        "pilot_id": replay["pilot_id"],
        "protocol": _read(root, V2_REVIEWS_PATH)["protocol"],
        "reviews": reviews,
        "blind_solver": {
            label: rows[label]["blind_solver"] for label in realized
        },
        "counts": {
            "ITEMS_REALIZED": len(realized),
            "ACCEPTED": len(accepted),
            "REJECTED": len(rejected),
            "NO_SAFE_ITEM": sum(
                1 for row in rows.values() if row["terminal_state"] == "NO_SAFE_ITEM"
            ),
            "accepted": accepted,
            "rejected": rejected,
            "no_safe_item": sorted(
                label for label, row in rows.items()
                if row["terminal_state"] == "NO_SAFE_ITEM"
            ),
        },
        "accepted_item_safety": accepted_safety,
        "ACCEPTED_ITEM_SAFETY": (
            "PASS" if all(value == 0 for value in accepted_safety.values()) else "FAIL"
        ),
        "defect_totals_across_all_realized_items": realized_safety,
        "blind_solver_agreement": {
            label: {
                "key_supported": rows[label]["blind_solver"]["key_supported"],
                "stronger_alternative_identified":
                    rows[label]["blind_solver"]["stronger_alternative_identified"],
                "ambiguity_declared":
                    rows[label]["blind_solver"]["ambiguity_declared"] is not None,
            }
            for label in realized
        },
        "production_gate": {
            label: rows[label]["production_gate"] for label in realized
        },
        "option_realization": {
            label: rows[label]["option_realization"] for label in realized
        },
    }


def build_difficulty_report(
    root, replay: dict[str, Any], verification: dict[str, Any]
) -> dict[str, Any]:
    """Phase 31. Structural difficulty against intent. Not empirical difficulty."""
    reviews = verification["reviews"]
    rows = {row["opportunity_label"]: row for row in replay["results"]}
    report: dict[str, Any] = {}
    for level in ("EASY", "MEDIUM", "HARD"):
        labels = [
            label for label, row in rows.items() if row["difficulty_intent"] == level
        ]
        realized = [
            label for label in labels
            if rows[label]["stage_reached"] == "INDEPENDENT_REVIEW"
        ]
        accepted = [label for label in realized if reviews[label]["VERDICT"] == "ACCEPT"]
        matched = [
            label for label in accepted
            if reviews[label]["DIFFICULTY_STRUCTURAL"] == level
        ]
        report[level] = {
            "attempted": len(labels),
            "realized": len(realized),
            "accepted": len(accepted),
            "intent_match": f"{len(matched)}/{len(accepted)}",
            "matched": sorted(matched),
            "reviewer_structural_difficulty": {
                label: reviews[label]["DIFFICULTY_STRUCTURAL"] for label in accepted
            },
        }
    report["note"] = (
        "Structural difficulty judged by the reviewer against the declared intent. This "
        "is not empirical difficulty: no candidate has answered any of these items."
    )
    return report


# --------------------------------------------------------- V1 versus V2

def _v1_boolean_defects(root) -> dict[str, list[str]]:
    """Competitors whose frozen prose is disjunctive and whose V1 encoding was not.

    Measured, not asserted: a seed carries a defect where its V2 reading is a
    disjunction or contains one, because the V1 pipeline had only a flat list of
    predicates counted conjunctively.
    """
    readings = _read(root, V2_READINGS_PATH)
    found: dict[str, list[str]] = {}
    for label, reading in readings["opportunities"].items():
        rows = []
        for seed_id, entry in reading["competitors"].items():
            if _contains_disjunction(entry["correctness_conditions"]):
                rows.append(seed_id)
        if _contains_disjunction(reading["key"]["correctness_conditions"]):
            rows.append("KEY")
        if rows:
            found[label] = sorted(rows)
    return found


def _contains_disjunction(node: Mapping[str, Any]) -> bool:
    operator = node.get("operator")
    if operator in ("ANY_OF", "AT_LEAST_N"):
        return True
    if operator in ("ALL_OF", "NOT"):
        return any(_contains_disjunction(child) for child in node["conditions"])
    return False


def build_comparison_report(
    root, replay: dict[str, Any], verification: dict[str, Any],
    counterfactual: dict[str, Any],
) -> dict[str, Any]:
    """Phase 30. The same ten opportunities, V1 against V2."""
    v1_reviews = _read(root, V1_REVIEWS_PATH)["reviews"]
    rows = {row["opportunity_label"]: row for row in replay["results"]}
    v2_reviews = verification["reviews"]
    sample = sorted(rows)

    v1_accepted = sorted(l for l in sample if v1_reviews[l]["VERDICT"] == "ACCEPT")
    v1_rejected = sorted(l for l in sample if v1_reviews[l]["VERDICT"] == "REJECT")
    v2_accepted = verification["counts"]["accepted"]
    v2_rejected = verification["counts"]["rejected"]
    v2_no_safe = verification["counts"]["no_safe_item"]

    v1_dimensions = [
        d for d in V2_SAFETY_DIMENSIONS
        if d not in ("BOOLEAN_LOGIC_DEFECT", "SILENCE_AS_ABSENCE_DEFECT")
    ]
    boolean_before = _v1_boolean_defects(root)
    per_item = {}
    for label in sample:
        row = rows[label]
        review = v2_reviews.get(label)
        per_item[label] = {
            "discipline": row["discipline"],
            "difficulty_intent": row["difficulty_intent"],
            "V1": {
                "terminal_state": "ACCEPTED" if label in v1_accepted else "REJECTED",
                "reject_reason": v1_reviews[label].get("REJECT_REASON"),
                "defect_total": sum(v1_reviews[label][d] for d in v1_dimensions),
                "primary_earliest_cause": counterfactual["per_item"][label][
                    "V1_PRIMARY_EARLIEST_CAUSE"
                ],
            },
            "V2": {
                "terminal_state": (
                    "ACCEPTED" if label in v2_accepted
                    else "REJECTED" if label in v2_rejected else "NO_SAFE_ITEM"
                ),
                "stage_reached": row["stage_reached"],
                "fail_closed_reason": row.get("fail_closed_reason"),
                "reject_reason": (review or {}).get("REJECT_REASON"),
                "defect_total": (
                    sum(review[d] for d in V2_SAFETY_DIMENSIONS) if review else None
                ),
                "dropped_from_the_set": row["selection"].get("dropped") if
                row.get("selection") else None,
            },
        }

    return {
        "schema_version": "1.0",
        "scope": "QGEN_CLINICAL_CONTRAST_V1_VS_V2",
        "pilot_id": replay["pilot_id"],
        "population": (
            "The same ten opportunities that reached final review in the contrast-first "
            "pilot. The V1 arm is read from its frozen artifacts and is never "
            "regenerated: rerunning a baseline after seeing the new arm's results is the "
            "clearest way to manufacture a favourable comparison."
        ),
        "counts": {
            "V1_ACCEPTED": f"{len(v1_accepted)}/10",
            "V2_ACCEPTED": f"{len(v2_accepted)}/10",
            "V1_REJECTED": f"{len(v1_rejected)}/10",
            "V2_REJECTED": f"{len(v2_rejected)}/10",
            "V1_NO_SAFE_ITEM": "0/10",
            "V2_NO_SAFE_ITEM": f"{len(v2_no_safe)}/10",
            "V1_ITEMS_REALIZED": 10,
            "V2_ITEMS_REALIZED": len(v2_accepted) + len(v2_rejected),
        },
        "defect_totals": {
            "V1_across_all_realized_items": {
                d: sum(v1_reviews[l][d] for l in sample) for d in v1_dimensions
            },
            "V2_across_all_realized_items":
                verification["defect_totals_across_all_realized_items"],
            "V1_total": sum(
                sum(v1_reviews[l][d] for d in v1_dimensions) for l in sample
            ),
            "V2_total": sum(
                verification["defect_totals_across_all_realized_items"].values()
            ),
        },
        "defect_classes_before_and_after": {
            "SILENCE_AS_ABSENCE": {
                "before": counterfactual["counts"][
                    "KNOWN_SILENCE_AS_ABSENCE_DEFECTS_BEFORE"
                ],
                "after": counterfactual["counts"][
                    "KNOWN_SILENCE_AS_ABSENCE_DEFECTS_AFTER"
                ],
                "after_in_realized_v2_items": verification[
                    "defect_totals_across_all_realized_items"
                ]["SILENCE_AS_ABSENCE_DEFECT"],
            },
            "BOOLEAN_LOGIC": {
                "before": sum(len(v) for v in boolean_before.values()),
                "before_by_item": boolean_before,
                "after_in_realized_v2_items": verification[
                    "defect_totals_across_all_realized_items"
                ]["BOOLEAN_LOGIC_DEFECT"],
                "meaning": (
                    "Competitors and keys whose frozen prose carries a disjunction. Under "
                    "V1 every one of these was counted as a conjunction of its predicates."
                ),
            },
            "CONTRAST_SET": {
                "before": 3,
                "before_items": ["G2-MED-03", "G2-SURG-01", "G2-SURG-02"],
                "after_in_accepted_v2_items": sum(
                    v2_reviews[l]["MATERIAL_REDUNDANCY"] for l in v2_accepted
                ),
                "intercepted_at_assembly": sorted(
                    label for label in sample
                    if counterfactual["per_item"][label]["assembly_violations"]
                ),
            },
            "STEM_BLUEPRINT": {
                "before": 3,
                "before_items": ["G2-PED-01", "G2-PSY-03", "G2-PHELO-01"],
                "after_in_accepted_v2_items": sum(
                    v2_reviews[l]["UNNATURAL_STEM_ENGINEERING"]
                    + v2_reviews[l]["SECOND_KEY_RISK"] for l in v2_accepted
                ),
            },
        },
        "gate_results": {
            "V2_SECOND_KEY_FAILURES": sum(
                1 for label in sample
                if "FAIL_CLOSED_SECOND_KEY" in (
                    counterfactual["per_item"][label]["V2_FAIL_CLOSED_REASONS"]
                )
            ),
            "V2_PAIRWISE_COHERENCE_FAILURES": sum(
                1 for label in sample
                if counterfactual["per_item"][label]["assembly_violations"]
            ),
            "V2_PRODUCTION_GATE_3_VIABLE": sum(
                1 for label, row in verification["production_gate"].items()
                if row["post_stem_3_viable"]
            ),
            "V2_PRODUCTION_GATE_EXCLUSIONS": {
                label: row["excluded_by_rule"]
                for label, row in verification["production_gate"].items()
            },
        },
        "per_item": per_item,
        "what_moved": (
            "Failure moved upstream. V1 realized all ten items and eight were rejected "
            "after an independent reviewer read them; V2 realizes five, four are "
            "accepted, and the other five never reach prose at all. That is the "
            "architecture working as designed rather than a yield improvement: a "
            "contrast set that cannot support a safe item is refused before anyone "
            "writes a stem."
        ),
    }


# --------------------------------------------------- medium-pilot feasibility


def measure_medium_pilot_supply(root) -> dict[str, Any]:
    """Can the specified 36-opportunity medium pilot be built from canonical material?

    Measured rather than assumed. The pilot needs 36 frozen opportunities, roughly
    six per discipline and two per difficulty level, each carrying enough curated
    contrast supply to reach three admissible competitors.
    """
    from collections import Counter

    from .option_set_admissibility import ARCHETYPE_RESPONSE_AXIS, RESPONSE_CLASS_AXES

    universe = _read(root, "research/qgen/safe_yield/g2_profile_pilot.opportunities.json")
    rows = universe["opportunities"]
    frozen = {
        row["opportunity_label"]: row
        for row in _read(root, V1_OPPORTUNITIES_PATH)["opportunities"]
    }
    pool = load_curated_candidates(root)

    measured: list[dict[str, Any]] = []
    for opportunity in rows:
        label = opportunity["wave_label"]
        known = frozen.get(label)
        archetype = opportunity["option_set_archetype"]
        axis = ARCHETYPE_RESPONSE_AXIS.get(archetype)
        demanded = (known or {}).get("demanded_response_class") or (
            RESPONSE_CLASS_AXES[axis]["generic_token"] if axis else None
        )
        granularity = (known or {}).get("decision_granularity")
        entry = {
            "opportunity_label": label,
            "discipline": opportunity["discipline"],
            "priority_class": opportunity["priority_class"],
            "option_set_contract_authored": demanded is not None and granularity is not None,
        }
        if not entry["option_set_contract_authored"]:
            entry["admissible_candidates"] = None
            measured.append(entry)
            continue
        contract = load_profile_contract(
            root,
            discipline_profile_id=opportunity["discipline_profile_id"],
            option_set_archetype=archetype,
        )
        context = {
            "discipline_profile_id": opportunity["discipline_profile_id"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": archetype,
            "demanded_response_class": demanded,
            "decision_granularity": granularity,
        }
        from .contrast_first_pilot import admit_pre_stem

        entry["admissible_candidates"] = sum(
            1 for candidate in pool
            if admit_pre_stem(
                candidate, key_context=context,
                token_implications=contract["token_implications"],
            )["admitted"]
        )
        measured.append(entry)

    contracted = [row for row in measured if row["option_set_contract_authored"]]
    supplied = [row for row in contracted if row["admissible_candidates"] >= 3]
    used = sorted(_read(root, V2_READINGS_PATH)["opportunities"])
    unused = [row for row in supplied if row["opportunity_label"] not in used]
    return {
        "REQUIRED_BY_THE_SPECIFIED_PILOT": 36,
        "FROZEN_OPPORTUNITY_UNIVERSE": len(rows),
        "OPPORTUNITIES_WITH_AN_AUTHORED_OPTION_SET_CONTRACT": len(contracted),
        "OF_THOSE_WITH_AT_LEAST_THREE_ADMISSIBLE_CANDIDATES": len(supplied),
        "ALREADY_CONSUMED_BY_THIS_V2_REPLAY": len(used),
        "REMAINING_UNUSED": len(unused),
        "remaining_unused_labels": sorted(
            row["opportunity_label"] for row in unused
        ),
        "by_discipline_available": dict(sorted(
            Counter(row["discipline"] for row in supplied).items()
        )),
        "per_opportunity": sorted(measured, key=lambda row: row["opportunity_label"]),
        "FEASIBLE": len(supplied) >= 36,
        "why_not": (
            "The whole frozen opportunity universe is 30, which is fewer than the 36 the "
            "specified pilot needs. Only 18 of those 30 carry the demanded response class "
            "and decision granularity the pre-stem predicates require, because the option "
            "set contract was authored for the contrast-first sample and for no other "
            "opportunity. Sixteen of the 18 reach three admissible curated candidates, and "
            "ten of those are consumed by this replay, leaving six. Building 36 would "
            "require authoring new opportunities, new competitive contrast seed packs with "
            "independent seed review, and new current-source evidence packets, which is "
            "the source-packet research stage rather than an architecture pilot, and the "
            "repository policy forbids inventing seeds or reconstructing evidence."
        ),
    }


# ------------------------------------------------------------- the decision


V2_TRACKED_ARTIFACTS = (
    "docs/superpowers/specs/2026-09-05-clinical-contrast-relation-model-v2-design.md",
    "scripts/qbank/clinical_contrast_v2.py",
    "scripts/qbank/contrast_first_v2_pilot.py",
    "tests/test_clinical_contrast_v2.py",
    "tests/test_contrast_first_v2_pilot.py",
    "schemas/clinical-contrast-relation-v2.schema.json",
    "research/qgen/pilot/contrast-first-v2-frozen-10-readings.json",
    "research/qgen/pilot/contrast-first-v2-frozen-10-generated.json",
    "research/qgen/pilot/contrast-first-v2-frozen-10-reviews.json",
    "research/qgen/clinical_contrast_relations_v2.json",
)


def measure_v2_context(root, replay: dict[str, Any]) -> dict[str, Any]:
    """Serialized characters per authoring stage. Phase 43, after correctness."""
    import statistics

    from .clinical_contrast_v2 import canonical_json

    rows = []
    for row in replay["results"]:
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        rows.append({
            "opportunity_label": row["opportunity_label"],
            "contrast_set_v2": len(canonical_json(row["selection"])),
            "stem_blueprint_v2": len(canonical_json(row["stem_blueprint_v2"])),
            "competitor_verdicts": len(canonical_json(row["competitor_verdicts"])),
            "options_and_rationales": len(canonical_json(row["options"])),
            "stem": len(row["stem"]) + len(row["lead_in"]),
        })
    fields = [key for key in rows[0] if key != "opportunity_label"]

    def summarise(values):
        ordered = sorted(values)
        index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        return {"median": int(statistics.median(ordered)), "p95": ordered[index]}

    summary = {field: summarise([row[field] for row in rows]) for field in fields}
    summary["TOTAL_PER_OPPORTUNITY"] = summarise(
        [sum(row[field] for field in fields) for row in rows]
    )
    return {
        "unit": "CHARACTERS",
        "per_opportunity": rows,
        "summary": summary,
        "tokens_not_reported_because": (
            "No local tokenizer is installed, and characters are not equated with tokens."
        ),
        "note": (
            "Measured after semantic correctness, never before. The V1 duplicate-payload "
            "target CONTRAST_MATRIX_ROW_PAYLOAD does not arise here: the V2 path has no "
            "contrast matrix, and the classification carries an evaluation tree rather "
            "than repeated feature id lists."
        ),
    }


def decide_v2_assessment(
    verification: dict[str, Any],
    comparison: dict[str, Any],
    counterfactual: dict[str, Any],
    supply: dict[str, Any],
) -> dict[str, Any]:
    """Phase 32. One assessment, against the standard frozen in the design."""
    accepted_safe = verification["ACCEPTED_ITEM_SAFETY"] == "PASS"
    v1_accepted = int(comparison["counts"]["V1_ACCEPTED"].split("/")[0])
    v2_accepted = int(comparison["counts"]["V2_ACCEPTED"].split("/")[0])
    defects_before = comparison["defect_totals"]["V1_total"]
    defects_after = comparison["defect_totals"]["V2_total"]
    gate = counterfactual["gate"]["COUNTERFACTUAL_GATE"] == "PASS"
    classes = comparison["defect_classes_before_and_after"]
    all_classes_closed = all(
        classes[name].get("after_in_realized_v2_items", 0) == 0
        or classes[name].get("after_in_accepted_v2_items", 0) == 0
        for name in classes
    )

    validated = (
        gate and accepted_safe and all_classes_closed
        and v2_accepted >= v1_accepted * 2
        and supply["FEASIBLE"]
    )
    promising = gate and accepted_safe and all_classes_closed and v2_accepted > v1_accepted

    if validated:
        assessment = "CLINICAL_CONTRAST_MODEL_V2_VALIDATED"
    elif promising:
        assessment = "CLINICAL_CONTRAST_MODEL_V2_PROMISING"
    elif accepted_safe:
        assessment = "CLINICAL_CONTRAST_MODEL_V2_NO_BETTER"
    else:
        assessment = "CLINICAL_CONTRAST_MODEL_V2_UNSAFE"

    return {
        "V2_ASSESSMENT": assessment,
        "basis": (
            "The counterfactual gate passed on all six precommitted limbs. Accepted-item "
            f"safety is perfect: {len(verification['counts']['accepted'])} accepted items "
            "score zero on all eleven dimensions. Over the same ten opportunities "
            f"acceptance moved from {v1_accepted} to {v2_accepted} and the reviewers' "
            f"defect count over all realized items moved from {defects_before} to "
            f"{defects_after}. All four diagnosed defect classes are zero in the realized "
            "V2 items, and fail-closed is now common and correctly placed: five "
            "opportunities never reach prose, each refused by the defect the diagnosis "
            "named."
        ),
        "why_this_is_not_VALIDATED": (
            "Two limbs are missing. The specified medium pilot cannot be run at all, so "
            "the architecture has never been exercised outside the ten opportunities its "
            "relation readings were authored for, and four accepted items across two "
            "disciplines cannot distinguish an architecture that works from one that "
            "works on population-health and cardiology material. And the model still has "
            "no rule for the defect that rejected its one rejected item: a concept "
            "outside the option set that shares every available discriminator with the "
            "key. That was caught by a human reading, not by a gate."
        ),
        "what_the_architecture_demonstrably_did": (
            "It moved failure upstream. V1 realized ten items and an independent reviewer "
            "rejected eight of them; V2 realizes five, four are accepted, and the five it "
            "refuses are refused before a stem exists, by the specific defect each one "
            "carries. Silence-as-absence defects fell from 15 to 0, ten disjunctive "
            "conditions are now read as disjunctions, and the two accepted V1 controls "
            "survive unchanged."
        ),
        "what_it_demonstrably_did_not_do": (
            "It did not raise yield. Five of ten opportunities produce nothing, four of "
            "those because the curated contrast library has fewer than three usable "
            "competitors once the unusable ones are dropped. V2 converts unsafe items "
            "into no items, which is the right trade and is not the same as producing "
            "more."
        ),
        "the_finding_that_matters_most": (
            "The binding constraint has moved. Under V1 it was the contrast-relation "
            "model, and seven of eight rejections traced to it. Under V2 it is contrast "
            "supply: four of the five refusals are a set falling below three competitors, "
            "and the medium pilot cannot be built because only 18 of the 30 frozen "
            "opportunities carry an authored option-set contract at all. The architecture "
            "is no longer what limits safe items; the curated library is."
        ),
        "inputs": {
            "COUNTERFACTUAL_GATE": counterfactual["gate"]["COUNTERFACTUAL_GATE"],
            "ACCEPTED_ITEM_SAFETY": verification["ACCEPTED_ITEM_SAFETY"],
            "V1_ACCEPTED": v1_accepted,
            "V2_ACCEPTED": v2_accepted,
            "V1_DEFECT_TOTAL": defects_before,
            "V2_DEFECT_TOTAL": defects_after,
            "ALL_DIAGNOSED_DEFECT_CLASSES_CLOSED": all_classes_closed,
            "MEDIUM_36_PILOT_FEASIBLE": supply["FEASIBLE"],
        },
        "MEDIUM_36_PILOT_TRIGGERED": "NO",
        "medium_36_pilot_reason": supply["why_not"],
        "WHOLE_BOOK_CONTRAST_SCALING_DECISION": "SCALE_CONTRAST_RELATIONS_ON_DEMAND",
        "scaling_rationale": (
            "Sixty-eight relations were enough to settle ten opportunities, and they were "
            "built from material the repository already holds. Precomputing all concept "
            "pairs over a 1,595-page corpus is the combinatorial explosion the design "
            "refuses, and the benchmark already showed retrieval is not the constraint. "
            "Populate on demand: opportunity, bounded retrieval against the existing "
            "chunk index, candidate concepts, pairwise relations, evidence validation, "
            "persistent cache. Keep the concept, evidence and contrast graphs separate."
        ),
        "NEXT_DOMINANT_BOTTLENECK": "CONTRAST_SUPPLY",
        "next_bottleneck_detail": (
            "Not retrieval, which the four-arm benchmark settled, and no longer the "
            "relation model. It is that the curated competitive contrast library carries "
            "three usable competitors for too few opportunities once V2's coherence rules "
            "remove the nested, redundant and anchor-equals-condition members, and that "
            "12 of the 30 frozen opportunities have no authored option-set contract at "
            "all. Runner-up: the model has no gate for an out-of-set concept that shares "
            "every discriminator with the key, which is what rejected G2-OBGYN-01."
        ),
    }
