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
    resolve_state,
    unresolved_features,
    validate_predicate,
)
from .contrast_first_pilot import (
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
        pairs = [tuple(pair) for pair in (authoring["contradiction_pairs"].get(unit) or [])]
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
