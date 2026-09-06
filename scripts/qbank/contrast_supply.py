"""On-demand clinical contrast supply for the Clinical Contrast Relation Model V2.

The V2 replay refused five of ten frozen opportunities before a stem existed. That
refusal is the model working, not failing, and this module does **not** relax it.
It asks the one question the refusals leave open:

    can the *supply* of independently validated, evidence-backed
    LIVE_BUT_INFERIOR competitors be raised, on demand and per opportunity,
    without weakening a single V2 semantic rule?

Nothing here re-implements V2. Candidate discovery, deduplication, pairwise
relation acquisition, independent admissibility review and a decision-context
cache all sit *upstream* of `evaluate_contrast_set_coherence`, and every candidate
this module admits is then handed to that unmodified gate. If the gate refuses it,
it is refused.

Design: docs/superpowers/specs/2026-09-05-on-demand-clinical-contrast-supply-design.md
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable, Mapping, Sequence

from .clinical_contrast_v2 import (
    ANCHOR_CLASSES,
    ClinicalContrastV2Error,
    can_be_live_without_being_correct,
    content_sha256,
    contrast_role_for,
    discriminative_class,
    evaluate_contrast_set_coherence,
    evaluate_predicate,
    predicate_feature_ids,
    predicate_leaves,
    validate_predicate,
)
from .contrast_first_pilot import (
    ContrastFirstError,
    load_curated_candidates,
    load_profile_contract,
    load_stem_feature_vocabulary,
)
from .contrast_first_v2_pilot import (
    V1_AUTHORING_PATH,
    V1_OPPORTUNITIES_PATH,
    V2_READINGS_PATH,
    _read,
    build_v2_contrast_sets,
    contradiction_pairs_for,
    select_admissible_subset,
    typed_supporting_features,
)
from .errors import QbankError
from .option_set_admissibility import (
    ARCHETYPE_RESPONSE_AXIS,
    RESPONSE_CLASS_AXES,
    expand_response_tokens,
)


class ContrastSupplyError(QbankError):
    """A supply request, candidate, relation or cache entry is unusable."""


SUPPLY_DIAGNOSIS_PATH = "reports/qgen_v2_contrast_supply_diagnosis.json"
SUPPLY_CACHE_PATH = "research/qgen/clinical_contrast_supply_cache.json"
SUPPLY_ACQUISITION_PATH = "research/qgen/clinical_contrast_supply_acquisition.json"
FROZEN5_RECOVERY_PATH = "reports/qgen_v2_frozen5_supply_recovery.json"
TN_INDEX_PATH = "derived/tn_index/tn_index.sqlite3"

#: The five V2 NO_SAFE_ITEM opportunities, read off the frozen verification
#: report rather than restated by hand.
V2_VERIFICATION_PATH = "reports/qgen_clinical_contrast_v2_pilot_verification.json"

#: One bounded acquisition wave per opportunity. Phase 14 of the milestone: if a
#: single wave does not reach three admissible competitors, NO_SAFE_ITEM stands.
ACQUISITION_WAVES_PER_OPPORTUNITY = 1

#: Retrieval stays small on purpose. The whole point of on-demand supply is that
#: it never sends a chapter to a reasoner.
TN_CHUNK_FLOOR = 5
TN_CHUNK_CEILING = 15


# --------------------------------------------------------------- primary causes

#: The milestone's classification vocabulary, extended by two causes the measured
#: funnels forced. `L_OTHER_*` codes are Phase 1's `L. OTHER` with the specific
#: mechanism named, because "OTHER" on its own would hide the finding.
PRIMARY_SUPPLY_CAUSES = (
    "A_TOO_FEW_CLINICALLY_RELEVANT_COMPETITORS",
    "B_COMPETITORS_EXIST_BUT_WRONG_LEARNER_DECISION",
    "C_COMPETITORS_EXIST_BUT_WRONG_RESPONSE_CLASS",
    "D_COMPETITORS_EXIST_BUT_WRONG_GRANULARITY",
    "E_COMPETITORS_EXIST_BUT_CATEGORICALLY_EXCLUDED",
    "F_COMPETITORS_EXIST_BUT_SECOND_KEY_RISK",
    "G_COMPETITORS_EXIST_BUT_INSUFFICIENT_EVIDENCE",
    "H_CURRENT_CONTRAST_LIBRARY_COVERAGE_GAP",
    "I_GRAPH_DISCOVERY_GAP",
    "J_TN_INDEX_DISCOVERY_GAP",
    "K_NATURALLY_LOW_CONTRAST_TOPIC",
    "L_OTHER_FROZEN_STEM_FEATURE_VOCABULARY_CEILING",
    "L_OTHER_KEY_CONDITION_NOT_OBSERVABLE",
    "L_OTHER_DIFFICULTY_SETTLEMENT_BUDGET",
)


def _cause(code: str) -> str:
    if code not in PRIMARY_SUPPLY_CAUSES:
        raise ContrastSupplyError(f"unknown primary supply cause: {code}")
    return code


# ---------------------------------------------------------- deterministic funnel


def frozen_five_labels(root) -> list[str]:
    """The five NO_SAFE_ITEM opportunity labels, read off the frozen V2 report."""
    verification = _read(root, V2_VERIFICATION_PATH)
    return sorted(verification["counts"]["no_safe_item"])


def library_eligible_candidates(root, opportunity: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Curated candidates that clear the opportunity's own declared filters.

    Response class and decision granularity are the two filters V2 itself applies
    as `CS2-3` and `CS2-4`; applying them here is not a second copy of the rule but
    the same question asked before a relation is worth acquiring at all.
    """
    contract = load_profile_contract(
        root,
        discipline_profile_id=opportunity["discipline_profile_id"],
        option_set_archetype=opportunity["option_set_archetype"],
    )
    axis = ARCHETYPE_RESPONSE_AXIS[opportunity["option_set_archetype"]]
    generic = RESPONSE_CLASS_AXES[axis]["generic_token"]
    demanded = opportunity["demanded_response_class"]
    rows = []
    for candidate in load_curated_candidates(root):
        if candidate["anchor_study_unit_id"] != opportunity["anchor_study_unit_id"]:
            continue
        if candidate["competitor_decision_granularity"] != opportunity["decision_granularity"]:
            continue
        tokens = set(expand_response_tokens(
            candidate["response_class_tokens"], contract["token_implications"], generic,
        ))
        if demanded not in tokens:
            continue
        rows.append(candidate)
    return sorted(rows, key=lambda row: row["seed_id"])


def measure_frozen_five_funnel(root) -> dict[str, Any]:
    """Recompute, from code, exactly where each of the five refusals happens.

    Read from the frozen artifacts through `build_v2_contrast_sets` and
    `select_admissible_subset` rather than copied out of the pilot narrative, so
    the diagnosis cannot drift from what the gate actually does.
    """
    labels = set(frozen_five_labels(root))
    opportunities = {
        row["opportunity_label"]: row
        for row in _read(root, V1_OPPORTUNITIES_PATH)["opportunities"]
    }
    verification = _read(root, V2_VERIFICATION_PATH)
    replay = {row["opportunity_label"]: row for row in verification["replay"]["results"]}
    readings = _read(root, V2_READINGS_PATH)["opportunities"]

    measured: list[dict[str, Any]] = []
    for row in build_v2_contrast_sets(root)["results"]:
        label = row["opportunity_label"]
        if label not in labels:
            continue
        opportunity = opportunities[label]
        contrast_set = row["contrast_set"]
        coherence = row["assembly_coherence"]
        selection = select_admissible_subset(
            contrast_set, coherence, contradiction_pairs=row["contradiction_pairs"],
        )
        eligible = library_eligible_candidates(root, opportunity)
        in_set = {
            member["member_id"] for member in contrast_set["members"]
            if member["role_in_set"] == "COMPETITOR"
        }
        measured.append({
            "opportunity_label": label,
            "opportunity_id": opportunity["opportunity_id"],
            "discipline": opportunity["discipline"],
            "priority_class": opportunity["priority_class"],
            "anchor_study_unit_id": opportunity["anchor_study_unit_id"],
            "learner_decision_id": opportunity["learner_decision_id"],
            "learner_decision": opportunity["lead_in_from_frozen_baseline"],
            "difficulty_intent": opportunity["difficulty_intent"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": opportunity["option_set_archetype"],
            "demanded_response_class": opportunity["demanded_response_class"],
            "decision_granularity": opportunity["decision_granularity"],
            "key_concept": readings[label]["key"].get("concept_category"),
            "key_correctness_features": sorted(predicate_feature_ids(
                readings[label]["key"]["correctness_conditions"]
            )),
            "candidates_in_the_v2_set": sorted(in_set),
            "current_candidate_count": len(in_set),
            "library_eligible_candidates": [row["seed_id"] for row in eligible],
            "library_eligible_but_unused": sorted(
                row["seed_id"] for row in eligible if row["seed_id"] not in in_set
            ),
            "relations_available": sum(
                1 for relation in contrast_set["relations"]
            ),
            "assembly_violations": coherence["violations"],
            "assembly_detail": [
                {key: value for key, value in entry.items() if key != "note"}
                for entry in coherence["detail"]
            ],
            "dropped_by_rule": selection["dropped"],
            "surviving_competitors": selection["surviving_competitors"],
            "valid_v2_relation_count_before": len(selection["surviving_competitors"]),
            "stage_reached": replay[label]["stage_reached"],
            "fail_closed_reason": replay[label]["fail_closed_reason"],
        })
    return {
        "measured_from": [V1_OPPORTUNITIES_PATH, V2_READINGS_PATH, V2_VERIFICATION_PATH],
        "opportunities": sorted(measured, key=lambda row: row["opportunity_label"]),
    }


# ------------------------------------------------------------ authored diagnosis

#: Phase 1. One primary cause per opportunity, each stating the *minimum* missing
#: supply rather than a wish list, and each resting on the measured funnel above.
#: Frozen before any relation was acquired.
FROZEN_FIVE_DIAGNOSIS: dict[str, dict[str, Any]] = {
    "G2-PED-01": {
        "primary_supply_cause": "H_CURRENT_CONTRAST_LIBRARY_COVERAGE_GAP",
        "why_each_candidate_failed": {
            "SEED-PED-T01-ASTHMA": "Admissible. Its usable anchor SF-P147-ATOPY-OR-RECURRENCE "
                                   "leaves the age precondition unresolved, so the anchor does "
                                   "not complete the correctness signature.",
            "SEED-PED-T01-FOREIGN-BODY": "CS2-6. Its frozen stem-anchor row is "
                                         "{ABRUPT-ONSET-NO-PRODROME, FOCAL-ASYMMETRIC-FINDINGS} "
                                         "and its correctness conditions are the disjunction of "
                                         "the same two features, so every usable anchor also "
                                         "makes it correct.",
            "SEED-PED-T01-PNEUMONIA": "CS2-6, for the same reason over "
                                      "{FAILING-TO-IMPROVE, FOCAL-ASYMMETRIC-FINDINGS, "
                                      "SEVERE-OR-BACTERIAL-CONCERN}.",
        },
        "minimum_missing_supply": (
            "Two admissible competitors. Either two new concepts, or an "
            "evidence-cited plausibility anchor for each of the two refused seeds "
            "that is a presentation feature shared with the key and is not on its "
            "own sufficient for that seed's correctness."
        ),
        "supply_sources_that_could_close_it": ["EXISTING_LIBRARY", "TN_FTS", "EXTERNAL_EVIDENCE"],
        "note": (
            "The T01 pool is exactly three candidates and all three are already in "
            "the set, so the library cannot supply a fourth concept. The refusals "
            "are a property of the frozen stem-anchor layer, not of the concepts."
        ),
    },
    "G2-PED-02": {
        "primary_supply_cause": "H_CURRENT_CONTRAST_LIBRARY_COVERAGE_GAP",
        "why_each_candidate_failed": {
            "SEED-PED-T02-CONTINUOUS": "Admissible.",
            "SEED-PED-T02-CXR": "Admissible.",
            "SEED-PED-T02-VIRAL": "CS2-6. Its only usable anchor is "
                                  "SF-P147-HIGH-RISK-EARLY-COURSE, which is also one "
                                  "disjunct of its correctness conditions; its other "
                                  "declared anchor is a SYSTEM_CONSTRAINT and cannot "
                                  "carry plausibility.",
        },
        "minimum_missing_supply": (
            "One admissible competitor. SEED-PED-T02-CBC is library-eligible and "
            "unused, but as frozen it carries a single anchor that is also its sole "
            "correctness condition, so it would be refused by CS2-6 on arrival."
        ),
        "supply_sources_that_could_close_it": ["EXISTING_LIBRARY", "TN_FTS"],
        "note": (
            "The one unused library candidate needs an added, evidence-cited "
            "plausibility anchor before it is supply at all."
        ),
    },
    "G2-PSY-03": {
        "primary_supply_cause": "L_OTHER_DIFFICULTY_SETTLEMENT_BUDGET",
        "why_each_candidate_failed": {
            "SEED-PSY-T03-DIGITAL": "Admissible at assembly and unsettleable at blueprint. "
                                    "Its correctness conditions are a conjunction of a stated "
                                    "preference and an access barrier; the stem can defeat it "
                                    "only by denying one of them explicitly, and EASY allows a "
                                    "single explicit denial which the key's own "
                                    "HIGH-IMMINENT-SUICIDE-RISK ABSENT already spends.",
            "SEED-PSY-T03-EXERCISE": "Admissible and settleable: MILD-SEVERITY is contradicted "
                                     "by the key's MODERATE-SEVERITY.",
            "SEED-PSY-T03-PSYCHOTHERAPY": "Admissible; its first disjunct rests on the same "
                                          "unstated access barrier.",
        },
        "minimum_missing_supply": (
            "At least one further admissible competitor that is settleable by "
            "STATED_CONTRARY alone, so that an unsettleable member can be dropped "
            "with three still standing."
        ),
        "supply_sources_that_could_close_it": ["EXISTING_LIBRARY"],
        "note": (
            "This is not a shortage of candidates: three library-eligible "
            "candidates are unused. It is a shortage of candidates the difficulty "
            "contract can afford to defeat."
        ),
    },
    "G2-SURG-01": {
        "primary_supply_cause": "L_OTHER_FROZEN_STEM_FEATURE_VOCABULARY_CEILING",
        "why_each_candidate_failed": {
            "SEED-SURG-T01-PID": "Admissible.",
            "SEED-SURG-T01-TORSION": "Admissible.",
            "SEED-SURG-T01-TOA": "CS2-1. An evidence-backed COMPLICATION_OF nesting in "
                                 "pelvic inflammatory disease, so the pair tests one and "
                                 "the same discrimination.",
        },
        "minimum_missing_supply": (
            "One admissible competitor that is NOT a gynaecologic cause. CS2-5 fires "
            "twice on the assembled set: the key is alone in its category and the "
            "competitors close ranks in a single category of their own, so a fourth "
            "gynaecologic competitor would make the imbalance worse, not better."
        ),
        "supply_sources_that_could_close_it": [],
        "note": (
            "Discovery is not the constraint. CLM-R4-SURG-FEMALE-DDX and "
            "CLM-R4-SURG-PID-SURGICAL name further differentials and the Toronto "
            "Notes index carries more. The constraint is that the frozen SU-GS-76 "
            "vocabulary holds no presentation feature in which a non-gynaecologic "
            "differential could state a correctness condition without also being "
            "its own sole plausibility anchor, which CS2-6 then refuses."
        ),
    },
    "G2-SURG-02": {
        "primary_supply_cause": "L_OTHER_KEY_CONDITION_NOT_OBSERVABLE",
        "why_each_candidate_failed": {
            "SEED-SURG-T02-MRI": "Admissible.",
            "SEED-SURG-T02-OBSERVE": "Admissible.",
            "SEED-SURG-T02-KUB": "CS2-6. Its only usable anchor "
                                 "SF-GS76-URETERAL-STONE-LEADING-DIAGNOSIS is also its "
                                 "sole correctness condition.",
            "SEED-SURG-T02-US": "CS2-7 NO_USABLE_ANCHOR. Every one of its declared anchors "
                                "types to PRIOR_ONLY or RESOURCE_AVAILABILITY, so none can "
                                "carry its plausibility.",
        },
        "minimum_missing_supply": (
            "None that supply can provide. CS2-9 fires on the key itself: both of "
            "its correctness conditions are NON_DISCRIMINATING, an Alvarado "
            "suspicion band the frozen reading deliberately refuses to retype and a "
            "resource clause, so the stem could only declare the answer. Any set "
            "built around this key stays incoherent however many competitors it has."
        ),
        "supply_sources_that_could_close_it": [],
        "note": (
            "Recorded as a supply diagnosis result because it is the answer to the "
            "supply question for this opportunity: the bottleneck is upstream of "
            "supply and the key is frozen."
        ),
    },
}


def build_supply_diagnosis(root) -> dict[str, Any]:
    """Phase 1. The measured funnel plus one frozen primary cause per opportunity."""
    funnel = measure_frozen_five_funnel(root)
    rows = []
    for measured in funnel["opportunities"]:
        label = measured["opportunity_label"]
        authored = FROZEN_FIVE_DIAGNOSIS.get(label)
        if authored is None:
            raise ContrastSupplyError(f"no authored diagnosis for {label}")
        merged = dict(measured)
        merged.update(authored)
        merged["primary_supply_cause"] = _cause(authored["primary_supply_cause"])
        rows.append(merged)

    causes: dict[str, list[str]] = {}
    for row in rows:
        causes.setdefault(row["primary_supply_cause"], []).append(row["opportunity_label"])

    return {
        "schema_version": "1.0",
        "scope": "QGEN_V2_CONTRAST_SUPPLY_DIAGNOSIS",
        "starting_commit": "b591226",
        "v2_baseline": {
            "V2_ACCEPTED": "4/10",
            "V2_REJECTED": "1/10",
            "V2_NO_SAFE_ITEM": "5/10",
        },
        "frozen_before_any_relation_was_acquired": True,
        "method": (
            "Every count is recomputed from the frozen artifacts through "
            "build_v2_contrast_sets and select_admissible_subset. No gate, seed, "
            "reading, key, stem or evidence packet is modified or re-read from a "
            "narrative."
        ),
        "reuse_matrix": REUSE_MATRIX,
        "cause_vocabulary": list(PRIMARY_SUPPLY_CAUSES),
        "FROZEN5_ANALYZED": len(rows),
        "FROZEN5_PRIMARY_SUPPLY_CAUSES": {
            cause: sorted(labels) for cause, labels in sorted(causes.items())
        },
        "opportunities": rows,
        "what_the_measurement_shows": (
            "Six competitor refusals across the five opportunities. Four are CS2-6 "
            "ANCHOR_EQUALS_CONDITION, one is CS2-7 NO_USABLE_ANCHOR and one is CS2-1 "
            "nesting. Every CS2-6 and CS2-7 refusal is a property of the frozen "
            "stem-anchor layer -- which features were recorded as making a seed "
            "plausible -- and not of the clinical concept. The dominant missing "
            "supply is therefore anchor supply, not concept supply."
        ),
        "what_it_does_not_show": (
            "It does not show that adding anchors is safe. An anchor that is not a "
            "genuine shared presentation feature would defeat CS2-6 while leaving "
            "the competitor exactly as unusable as before. That is what the "
            "independent admissibility review in the acquisition wave is for."
        ),
    }


# ------------------------------------------------------------------ Phase 0 reuse

REUSE_MATRIX = [
    {
        "component": "clinical_contrast_v2 (feature states, predicates, roles, CS2-1..CS2-9)",
        "decision": "REUSE",
        "why": "It is the model this milestone supplies input to. Redesigning it is "
               "explicitly out of scope, and every acquired candidate is handed to "
               "the unmodified gate.",
    },
    {
        "component": "contrast_first_v2_pilot (set build, subset selection, blueprint, replay)",
        "decision": "REUSE",
        "why": "The replay path is the canonical V2 pipeline. Supply builds its input; "
               "it does not re-implement a stage of it.",
    },
    {
        "component": "research/qgen/clinical_contrast_relations_v2.json (68 frozen relations)",
        "decision": "REUSE",
        "why": "First place a relation request looks. A cache hit costs nothing and "
               "cannot drift from what the counterfactual validated.",
    },
    {
        "component": "research/qgen/chapter_global_contrast_library.json (12 curated edges)",
        "decision": "REUSE",
        "why": "Second discovery source. Small, independently reviewed, already carries "
               "decision_context and excluded_contexts.",
    },
    {
        "component": "curated seed packs r4 / g2_targeted / g2_extensions (81 candidates)",
        "decision": "REUSE",
        "why": "Third discovery source and the only one that already carries response "
               "class tokens, decision granularity and archetype applicability.",
    },
    {
        "component": "derived/tn_index/tn_index.sqlite3 chunks_fts (14,909 chunks)",
        "decision": "REUSE",
        "why": "Fourth discovery source, used for concept discovery and evidence context "
               "only. The four-arm benchmark already showed BM25 cannot produce "
               "competitor objects directly, and this milestone does not ask it to.",
    },
    {
        "component": "typed clinical graph (4,275 nodes, 5,916 edges)",
        "decision": "REUSE",
        "why": "Fifth discovery source and a provenance aid. Measured, not expanded: "
               "GRAPH_UNIQUE_USEFUL_CONTRIBUTIONS was 0 in the contrast-first pilot.",
    },
    {
        "component": "evidence claim packets and the source registries",
        "decision": "REUSE",
        "why": "Phase 13. A relation cites existing claims before any new research is "
               "considered, and every acquired relation must cite at least one.",
    },
    {
        "component": "research/qgen/safe_yield/g2_stem_feature_vocabulary.json",
        "decision": "REUSE",
        "why": "Frozen with a content hash and read-only. Supply may not invent a "
               "feature id; where a discovered competitor cannot state its conditions "
               "in this vocabulary it is refused, and that refusal is a finding.",
    },
    {
        "component": "frozen stem-anchor layer of the curated seed packs",
        "decision": "EXTEND",
        "why": "Read and never written. Supply may ADD an evidence-cited plausibility "
               "anchor to a candidate in its own acquisition record; it may never "
               "remove one, and the frozen pack keeps its bytes.",
    },
    {
        "component": "contrast supply cache (new)",
        "decision": "EXTEND",
        "why": "New artifact. Keys a relation by concept pair plus learner decision, "
               "response class, decision granularity and anchor unit, so a DIAGNOSIS "
               "relation can never be reused for a MANAGEMENT decision.",
    },
    {
        "component": "profile_contrast_retrieval.retrieve_profile_aware_contrasts",
        "decision": "REUSE",
        "why": "The production gate. Recovered items must still clear it unchanged.",
    },
    {
        "component": "embeddings",
        "decision": "DO_NOT_USE",
        "why": "LOCAL_EMBEDDING_TRIGGER_MET was NO and nothing in this diagnosis moves "
               "it: the competitors that are missing are missing because they cannot "
               "be expressed, not because they cannot be found.",
    },
    {
        "component": "a broad prepopulated Toronto Notes contrast graph",
        "decision": "DO_NOT_USE",
        "why": "All-pairs precomputation over 1,595 pages is the combinatorial "
               "explosion the V2 design refuses. Sixty-eight relations settled ten "
               "opportunities.",
    },
    {
        "component": "the production question generator",
        "decision": "DO_NOT_USE",
        "why": "Out of scope. PRODUCTION_GENERATOR_REPLACED = NO.",
    },
]
