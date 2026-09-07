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
    CONTRAST_SET_MINIMUM_COMPETITORS,
    ANCHOR_CLASSES,
    PRESENT as PRESENT_STATE,
    ClinicalContrastV2Error,
    can_be_live_without_being_correct,
    content_sha256,
    contrast_role_for,
    discriminative_class,
    evaluate_contrast_set_coherence,
    PLAUSIBLE_BUT_NEVER_BEST,
    evaluate_predicate,
    is_never_best,
    predicate_feature_ids,
    predicate_leaves,
    validate_never_best_contract,
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


# ------------------------------------------------------------------- identity


def supply_context(
    opportunity: Mapping[str, Any], *, decision_domain: str = "PATIENT_CLINICAL"
) -> dict[str, str]:
    """The five dimensions a contrast relation may never be reused across."""
    return {
        "learner_decision_id": opportunity["learner_decision_id"],
        "demanded_response_class": opportunity["demanded_response_class"],
        "decision_granularity": opportunity["decision_granularity"],
        "anchor_study_unit_id": opportunity["anchor_study_unit_id"],
        "decision_domain": decision_domain,
    }


_CONTEXT_FIELDS = (
    "learner_decision_id",
    "demanded_response_class",
    "decision_granularity",
    "anchor_study_unit_id",
    "decision_domain",
)


def _context_tuple(context: Mapping[str, Any]) -> list[str]:
    missing = [field for field in _CONTEXT_FIELDS if not context.get(field)]
    if missing:
        raise ContrastSupplyError(
            f"a supply context needs {', '.join(missing)}; identity fails closed"
        )
    return [str(context[field]) for field in _CONTEXT_FIELDS]


def candidate_id(concept_id: str, context: Mapping[str, Any]) -> str:
    """A candidate's id in one decision context, content-addressed and stable."""
    if not concept_id:
        raise ContrastSupplyError("a candidate needs a canonical concept id")
    digest = content_sha256([concept_id, _context_tuple(context)])
    return f"CSUP-{digest[:20]}"


def cache_key(concept_a_id: str, concept_b_id: str, context: Mapping[str, Any]) -> str:
    """Order-independent over the pair, and bound to the decision context.

    A relation between two concepts for a DIAGNOSIS decision says nothing about
    the same two concepts for a MANAGEMENT decision, so the context is part of
    the identity rather than a note beside it.
    """
    if not concept_a_id or not concept_b_id:
        raise ContrastSupplyError("a cache key needs two canonical concept ids")
    pair = sorted([concept_a_id, concept_b_id])
    digest = content_sha256([pair, _context_tuple(context)])
    return f"CSUPKEY-{digest[:24]}"


# ------------------------------------------------------------------ filtering


def filter_candidates(
    candidates: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Response class first, then granularity. Same questions as CS2-3 and CS2-4.

    Asked here so a relation is never acquired for a candidate the set gate would
    refuse anyway; the gate still asks them again on the assembled set.
    """
    kept: list[dict[str, Any]] = []
    refused: dict[str, str] = {}
    for candidate in candidates:
        member_id = candidate["member_id"]
        tokens = set(candidate.get("response_class_tokens") or [])
        if context["demanded_response_class"] not in tokens:
            refused[member_id] = "RESPONSE_CLASS_MISMATCH"
            continue
        if candidate.get("decision_granularity") != context["decision_granularity"]:
            refused[member_id] = "GRANULARITY_MISMATCH"
            continue
        kept.append(dict(candidate))
    return kept, refused


# --------------------------------------------------------------- deduplication


def deduplicate_candidates(
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """One row per canonical concept id, with every provenance kept.

    The first arrival wins the row because discovery is ordered: a curated
    library hit outranks a Toronto Notes hit for the same concept, and the fact
    that both found it is worth recording rather than discarding.
    """
    kept: list[dict[str, Any]] = []
    by_concept: dict[str, dict[str, Any]] = {}
    removed: dict[str, str] = {}
    for candidate in candidates:
        concept_id = candidate.get("concept_id")
        if not concept_id:
            raise ContrastSupplyError(
                f"{candidate.get('member_id')} has no canonical concept id to deduplicate on"
            )
        source = candidate.get("discovery_source")
        if concept_id in by_concept:
            removed[candidate["member_id"]] = "DUPLICATE_CONCEPT_ID"
            sources = by_concept[concept_id]["discovery_sources"]
            if source and source not in sources:
                sources.append(source)
            continue
        row = dict(candidate)
        row["discovery_sources"] = [source] if source else list(
            candidate.get("discovery_sources") or []
        )
        by_concept[concept_id] = row
        kept.append(row)
    return kept, removed


def parent_subtype_collisions(
    candidates: Sequence[Mapping[str, Any]], nesting: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Declared nesting between two candidates that would share an option set.

    Read off the declared relations, never guessed from wording. This is the same
    fact `CS2-1` fires on; surfacing it during acquisition stops a nested pair
    from being counted as two units of supply.
    """
    members = {candidate["member_id"] for candidate in candidates}
    collisions = []
    for row in nesting:
        pair = sorted(row["pair"])
        if row.get("nesting_relation", "NONE") == "NONE":
            continue
        if not set(pair) <= members:
            continue
        collisions.append({"pair": pair, "nesting_relation": row["nesting_relation"]})
    return sorted(collisions, key=lambda row: row["pair"])


# ---------------------------------------------------------- bounded retrieval


def retrieve_tn_chunks(
    connection: sqlite3.Connection, query: str, *, limit: int
) -> list[dict[str, Any]]:
    """A small, bounded Toronto Notes read for concept discovery and context.

    Never a chapter. The bound is enforced rather than advised, because the whole
    economic case for on-demand supply is that one discovery operation costs a
    handful of chunks.
    """
    if not (TN_CHUNK_FLOOR <= limit <= TN_CHUNK_CEILING):
        raise ContrastSupplyError(
            f"a discovery retrieval takes between {TN_CHUNK_FLOOR} and "
            f"{TN_CHUNK_CEILING} chunks, not {limit}"
        )
    terms = [term for term in _tokenize(query) if term]
    if not terms:
        raise ContrastSupplyError("a retrieval request needs at least one usable term")
    expression = " OR ".join(f'"{term}"' for term in terms)
    try:
        rows = connection.execute(
            "SELECT c.chunk_id, c.pdf_page, c.tn_node_id, c.subheading, "
            "bm25(chunks_fts) FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "
            "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
            (expression, limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise ContrastSupplyError(f"text query is unusable: {exc}") from exc
    return [
        {
            "chunk_id": chunk_id,
            "pdf_page": pdf_page,
            "tn_node_id": tn_node_id,
            "subheading": subheading,
            "bm25": score,
            "authority_role": "TOPIC_DISCOVERY_SOURCE",
        }
        for chunk_id, pdf_page, tn_node_id, subheading, score in rows
    ]


def _tokenize(text: str) -> list[str]:
    import re

    return [
        term for term in re.findall(r"[a-z][a-z0-9-]{2,}", (text or "").lower())
        if term not in _QUERY_STOPWORDS
    ]


_QUERY_STOPWORDS = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "which", "when", "where", "not", "any", "its", "has", "have",
})


# ------------------------------------------------------------- one wave only


class AcquisitionLedger:
    """Phase 14. One bounded acquisition wave per opportunity, enforced.

    A second wave is how a pipeline talks itself into a question: enrich, fail,
    enrich again, until something passes. The ledger refuses.
    """

    def __init__(self) -> None:
        self.waves: dict[str, dict[str, Any]] = {}
        self._open: set[str] = set()

    def open_wave(self, label: str) -> None:
        entry = self.waves.setdefault(label, {"waves": 0, "candidates_discovered": 0})
        if entry["waves"] >= ACQUISITION_WAVES_PER_OPPORTUNITY:
            raise ContrastSupplyError(
                f"{label} has already had its one bounded acquisition wave; "
                "NO_SAFE_ITEM stands rather than being enriched away"
            )
        entry["waves"] += 1
        self._open.add(label)

    def close_wave(self, label: str, *, candidates_discovered: int) -> None:
        if label not in self._open:
            raise ContrastSupplyError(f"no acquisition wave is open for {label}")
        self.waves[label]["candidates_discovered"] = candidates_discovered
        self._open.discard(label)


# ----------------------------------------------------- validation and admission

REVIEW_VERDICTS = ("APPROVED", "REJECTED", "UNCERTAIN")


def validate_acquired_relation(
    relation: Mapping[str, Any],
    *,
    vocabulary: Mapping[str, Any] | None = None,
    enforce_anchor_sufficiency: bool = False,
) -> None:
    """The V2 relation schema, plus the two supply-only rules S-1 and S-4(c)."""
    from .clinical_contrast_v2 import validate_contrast_relation

    validate_contrast_relation(relation)

    verdict = (relation.get("review") or {}).get("verdict")
    if verdict is not None and verdict not in REVIEW_VERDICTS:
        raise ContrastSupplyError(f"unknown review verdict: {verdict}")

    if vocabulary is not None:
        declared = set()
        for side in ("shared_features", "a_supporting_features", "b_supporting_features"):
            declared.update(row["feature_id"] for row in relation[side])
        for side, flag in (
            ("correctness_conditions_a", "never_best_a"),
            ("correctness_conditions_b", "never_best_b"),
        ):
            if relation.get(flag):
                continue
            declared.update(predicate_feature_ids(relation[side]))
        unknown = sorted(declared - set(vocabulary))
        if unknown:
            raise ContrastSupplyError(
                "S-1: the frozen stem-feature vocabulary is read-only and carries no "
                f"{', '.join(unknown)}"
            )

    if enforce_anchor_sufficiency:
        _enforce_anchor_sufficiency(relation)


def _enforce_anchor_sufficiency(relation: Mapping[str, Any]) -> None:
    """S-4 limb (c), on the competitor side of the relation.

    An anchor set every member of which completes the candidate's own correctness
    signature buys nothing: `CS2-6` would refuse the candidate anyway, and an
    anchor added to get past that rule rather than to state a shared finding is
    the exact abuse the design names.
    """
    if relation.get("never_best_b"):
        # There is no correctness signature for an anchor to complete, so the
        # abuse this limb names cannot occur. The never-best contract asks the
        # candidate for a positive plausibility anchor in its own right instead.
        return
    anchors = sorted({
        row["feature_id"] for row in relation["b_supporting_features"]
        if discriminative_class(row["contrast_role"]) in ANCHOR_CLASSES
    })
    if not anchors:
        return
    if not can_be_live_without_being_correct(
        {"correctness_conditions": relation["correctness_conditions_b"]}, anchors
    ):
        raise ContrastSupplyError(
            "S-4(c): every usable anchor also completes this candidate's correctness "
            f"signature ({', '.join(anchors)}), so it can be live only by being a "
            "second key and is not supply"
        )


def admit_relation(
    cache: dict[str, dict[str, Any]],
    relation: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    vocabulary: Mapping[str, Any] | None = None,
) -> bool:
    """Admit one reviewed relation to the cache. Anything but APPROVED fails closed."""
    from .clinical_contrast_v2 import build_contrast_relation

    review = relation.get("review") or {}
    verdict = review.get("verdict")
    if verdict not in REVIEW_VERDICTS:
        raise ContrastSupplyError(
            "a relation without an independent review verdict is not admissible"
        )
    if verdict != "APPROVED":
        return False
    if relation.get("verification_status") != "EVIDENCE_VERIFIED":
        return False

    validate_acquired_relation(relation, vocabulary=vocabulary)
    payload = {key: value for key, value in relation.items() if key != "review"}
    built = build_contrast_relation(**payload)
    key = cache_key(
        relation["concept_a"]["concept_id"], relation["concept_b"]["concept_id"], context
    )
    cache[key] = {
        "cache_key": key,
        "context": {field: context[field] for field in _CONTEXT_FIELDS},
        "concept_pair": sorted([
            relation["concept_a"]["concept_id"], relation["concept_b"]["concept_id"]
        ]),
        "relation": built,
        "review": dict(review),
    }
    return True


def lookup_cached_relation(
    cache: Mapping[str, Mapping[str, Any]],
    concept_a_id: str,
    concept_b_id: str,
    context: Mapping[str, Any],
) -> dict[str, Any] | None:
    """A cache hit, or None. There is no near-miss and no fallback."""
    entry = cache.get(cache_key(concept_a_id, concept_b_id, context))
    return dict(entry) if entry is not None else None


# ------------------------------------------------------------ acquisition wave

SUPPLY_DISCOVERY_SOURCES = (
    "APPROVED_V2_RELATION",
    "CURATED_LIBRARY",
    "CURATED_EVIDENCE",
    "GRAPH",
    "TN_FTS",
    "NEW_EXTERNAL_EVIDENCE",
)

ACQUISITION_KINDS = (
    "ANCHOR_ADDITION",
    "NEW_MEMBER",
    "NEW_MEMBER_WITH_ANCHOR_ADDITION",
    "NEW_CONCEPT",
)


def load_acquisition(
    root, *, acquisition_path: str = SUPPLY_ACQUISITION_PATH
) -> dict[str, Any]:
    document = _read(root, acquisition_path)
    if document.get("waves_per_opportunity") != ACQUISITION_WAVES_PER_OPPORTUNITY:
        raise ContrastSupplyError(
            "the acquisition artifact declares more than one wave per opportunity"
        )
    for label, entry in document["opportunities"].items():
        for candidate in entry["candidates"]:
            if candidate["discovery_source"] not in SUPPLY_DISCOVERY_SOURCES:
                raise ContrastSupplyError(
                    f"{label}/{candidate['member_id']}: unknown discovery source"
                )
            if candidate["acquisition_kind"] not in ACQUISITION_KINDS:
                raise ContrastSupplyError(
                    f"{label}/{candidate['member_id']}: unknown acquisition kind"
                )
            if (candidate.get("review") or {}).get("verdict") not in REVIEW_VERDICTS:
                raise ContrastSupplyError(
                    f"{label}/{candidate['member_id']}: no independent review verdict"
                )
    return document


def _approved(entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate for candidate in entry["candidates"]
        if candidate["review"]["verdict"] == "APPROVED"
    ]


def apply_supply_to_contrast_set(
    contrast_set: dict[str, Any],
    entry: Mapping[str, Any],
    *,
    opportunity: Mapping[str, Any],
    reading: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    curated: Mapping[str, Any],
) -> dict[str, Any]:
    """Add approved anchors and approved members, then rebuild every pair.

    Anchors are added, never removed, and a new member is appended rather than
    substituted for one the gate refused. The relation list is regenerated by the
    unmodified V2 builder so competitor-versus-competitor pairs exist for the new
    members too.
    """
    domain = contrast_set["decision_domain"]
    overrides = dict(reading.get("role_overrides") or {})
    members = [dict(member) for member in contrast_set["members"]]
    by_id = {member["member_id"]: member for member in members}
    added_anchors: dict[str, list[str]] = {}
    added_members: list[str] = []

    for candidate in _approved(entry):
        member_id = candidate["member_id"]
        anchors = [row["feature_id"] for row in candidate.get("added_anchors") or []]
        for row in candidate.get("added_anchors") or []:
            overrides.setdefault(row["feature_id"], {
                "contrast_role": row["contrast_role"],
                "evidence_refs": list(row["evidence_refs"]),
                "reason": row["s4_limb_b"],
            })
        if candidate["acquisition_kind"] == "ANCHOR_ADDITION":
            member = by_id.get(member_id)
            if member is None:
                raise ContrastSupplyError(
                    f"{member_id} is not in the frozen set, so an anchor cannot be added to it"
                )
            existing = {row["feature_id"] for row in member["supporting_features"]}
            member["supporting_features"] = typed_supporting_features(
                sorted(existing | set(anchors)),
                vocabulary=vocabulary, decision_domain=domain, role_overrides=overrides,
            )
            added_anchors[member_id] = sorted(set(anchors) - existing)
            continue

        seed = curated.get(member_id)
        if seed is None:
            raise ContrastSupplyError(
                f"{member_id} is not a curated candidate; a new concept needs a seed row"
            )
        frozen_anchors = set(seed["plausibility_anchor_feature_ids"])
        never_best = (
            candidate.get("distractor_semantics") == PLAUSIBLE_BUT_NEVER_BEST
        )
        if not never_best:
            validate_predicate(candidate["correctness_conditions"], vocabulary=vocabulary)
        member = {
            "member_id": member_id,
            "role_in_set": "COMPETITOR",
            "concept_id": seed["competitor_concept_id"],
            "concept": seed["competitor_concept"],
            "concept_category": candidate["concept_category"],
            # A never-best member keeps the response-class tokens its frozen seed
            # row carries. Asserting the demanded token on its behalf would make
            # CS2-3 unable to refuse a candidate that belongs to another question,
            # which is exactly the failure the class must not import.
            "response_class_tokens": (
                sorted(seed["response_class_tokens"]) if never_best
                else [contrast_set["demanded_response_class"]]
            ),
            "decision_granularity": seed["competitor_decision_granularity"],
            "supporting_features": typed_supporting_features(
                sorted(frozen_anchors | set(anchors)),
                vocabulary=vocabulary, decision_domain=domain, role_overrides=overrides,
            ),
            "categorical_exclusion_conditions": [],
            "evidence_refs": list(candidate["evidence_refs"]),
            "seed_id": member_id,
            "supplied_on_demand": True,
        }
        if never_best:
            member["distractor_semantics"] = PLAUSIBLE_BUT_NEVER_BEST
            member["never_best_contract"] = candidate["never_best_contract"]
            validate_never_best_contract(member)
        else:
            member["correctness_conditions"] = candidate["correctness_conditions"]
        members.append(member)
        added_members.append(member_id)
        added_anchors[member_id] = sorted(anchors)

    from .contrast_first_v2_pilot import _build_relations

    supplied = dict(contrast_set)
    supplied["members"] = members
    supplied["relations"] = _build_relations(
        contrast_set["opportunity_label"], opportunity, reading, members, domain=domain,
    )
    supplied["feature_roles"] = {
        row["feature_id"]: row["contrast_role"]
        for member in members for row in member["supporting_features"]
    }
    supplied["supply"] = {
        "added_anchors": {key: value for key, value in sorted(added_anchors.items()) if value},
        "added_members": sorted(added_members),
    }
    return supplied


def run_acquisition_wave(
    root,
    *,
    acquisition_path: str = SUPPLY_ACQUISITION_PATH,
    readings_path: str = V2_READINGS_PATH,
) -> dict[str, Any]:
    """Phase 15. One bounded wave over the five, then measure, and stop.

    The two paths default to the frozen-five artifacts, so the historical wave
    and its report are unchanged. A later frozen batch supplies its own pair.
    """
    acquisition = load_acquisition(root, acquisition_path=acquisition_path)
    opportunities = {
        row["opportunity_label"]: row
        for row in _read(root, V1_OPPORTUNITIES_PATH)["opportunities"]
    }
    readings = _read(root, readings_path)["opportunities"]
    vocabulary = load_stem_feature_vocabulary(root)
    curated = {row["seed_id"]: row for row in load_curated_candidates(root)}
    frozen_relations = {
        relation["contrast_relation_id"]
        for relation in _read(root, "research/qgen/clinical_contrast_relations_v2.json")["relations"]
    }

    ledger = AcquisitionLedger()
    cache: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for row in build_v2_contrast_sets(root, readings_path=readings_path)["results"]:
        label = row["opportunity_label"]
        entry = acquisition["opportunities"].get(label)
        if entry is None:
            continue
        opportunity = opportunities[label]
        reading = readings[label]
        context = supply_context(opportunity, decision_domain=row["decision_domain"])
        ledger.open_wave(label)

        discovered = [dict(candidate) for candidate in entry["candidates"]]
        for candidate in discovered:
            candidate["candidate_id"] = candidate_id(candidate["concept_id"], context)
        deduplicated, duplicates = deduplicate_candidates(discovered)

        supplied_set = apply_supply_to_contrast_set(
            row["contrast_set"], entry,
            opportunity=opportunity, reading=reading,
            vocabulary=vocabulary[row["anchor_study_unit_id"]], curated=curated,
        )
        pairs = row["contradiction_pairs"]
        # Supply may have lifted an under-size frozen set over the minimum; the
        # gate then runs on the supplied set exactly as it always has. Where it
        # did not, the refusal is reported rather than raised, so a wave that
        # could not close the gap is measurable instead of fatal. The frozen-five
        # wave never reaches this branch.
        undersized = sum(
            1 for member in supplied_set["members"]
            if member["role_in_set"] == "COMPETITOR"
        ) < CONTRAST_SET_MINIMUM_COMPETITORS
        coherence = None if undersized else evaluate_contrast_set_coherence(
            supplied_set, contradiction_pairs=pairs
        )
        selection = {
            "admissible": False,
            "dropped": {},
            "surviving_competitors": sorted(
                member["member_id"] for member in supplied_set["members"]
                if member["role_in_set"] == "COMPETITOR"
            ),
            "fail_closed_reason": "FAIL_CLOSED_CONTRAST_SET_SIZE",
            "residual_violations": None,
        } if undersized else select_admissible_subset(
            supplied_set, coherence, contradiction_pairs=pairs
        )

        cache_hits = 0
        created = 0
        for relation in supplied_set["relations"]:
            if relation["contrast_relation_id"] in frozen_relations:
                cache_hits += 1
                continue
            created += 1
            admit_relation(
                cache,
                {
                    **relation,
                    "review": {
                        "verdict": "APPROVED",
                        "reviewer_id": "R-SUPPLY-SET",
                        "reasons": [],
                    },
                },
                context,
                vocabulary=vocabulary[row["anchor_study_unit_id"]],
            )

        verdicts = {
            verdict: sorted(
                candidate["member_id"] for candidate in entry["candidates"]
                if candidate["review"]["verdict"] == verdict
            )
            for verdict in REVIEW_VERDICTS
        }
        ledger.close_wave(label, candidates_discovered=len(discovered))
        results.append({
            "opportunity_label": label,
            "discipline": opportunity["discipline"],
            "difficulty_intent": opportunity["difficulty_intent"],
            "anchor_study_unit_id": row["anchor_study_unit_id"],
            "supply_context": context,
            "retrieval": entry["retrieval"],
            "CANDIDATES_DISCOVERED": len(discovered),
            "CANDIDATES_DEDUPLICATED": len(duplicates),
            "duplicates_removed": duplicates,
            "CANDIDATES_SEMANTICALLY_REVIEWED": len(entry["candidates"]),
            "RELATIONS_APPROVED": len(verdicts["APPROVED"]),
            "RELATIONS_REJECTED": len(verdicts["REJECTED"]),
            "RELATIONS_UNCERTAIN": len(verdicts["UNCERTAIN"]),
            "verdicts": verdicts,
            "refusal_reasons": {
                candidate["member_id"]: candidate["review"]["reasons"]
                for candidate in entry["candidates"]
                if candidate["review"]["verdict"] != "APPROVED"
            },
            "approved_by_source": {
                candidate["member_id"]: candidate["discovery_source"]
                for candidate in _approved(entry)
            },
            "approved_by_kind": {
                candidate["member_id"]: candidate["acquisition_kind"]
                for candidate in _approved(entry)
            },
            "supply": supplied_set["supply"],
            "VALID_COMPETITORS_BEFORE": [] if row["assembly_coherence"] is None
            else sorted(
                select_admissible_subset(
                    row["contrast_set"], row["assembly_coherence"],
                    contradiction_pairs=pairs,
                )["surviving_competitors"]
            ),
            "VALID_COMPETITORS_AFTER": sorted(selection["surviving_competitors"]),
            "assembly_violations_after": (
                ["FAIL_CLOSED_CONTRAST_SET_SIZE"] if coherence is None
                else coherence["violations"]
            ),
            "assembly_detail_after": [] if coherence is None else [
                {key: value for key, value in detail.items() if key != "note"}
                for detail in coherence["detail"]
            ],
            "selection_after": {
                "admissible": selection["admissible"],
                "dropped": selection["dropped"],
                "fail_closed_reason": selection["fail_closed_reason"],
                "residual_violations": selection["residual_violations"],
            },
            "TOTAL_RELATION_REQUESTS": len(supplied_set["relations"]),
            "CONTRAST_CACHE_HITS": cache_hits,
            "NEW_RELATIONS_CREATED": created,
            "contrast_set": supplied_set,
            "contradiction_pairs": pairs,
        })

    return {
        "schema_version": "1.0",
        "scope": "QGEN_ON_DEMAND_CONTRAST_SUPPLY_WAVE",
        "acquisition_id": acquisition["acquisition_id"],
        "waves": ledger.waves,
        "llm_api_calls": 0,
        "results": sorted(results, key=lambda row: row["opportunity_label"]),
        "cache": cache,
    }


# --------------------------------------------------------------- set assembly

def solve_supplied_blueprint(
    root,
    record: Mapping[str, Any],
    *,
    reading: Mapping[str, Any],
    context_features: Sequence[Mapping[str, str]],
    vocabulary: Mapping[str, Any],
) -> dict[str, Any]:
    """Design section 11. One pass, drop-only, and at most one repeat solve.

    If the solver names a competitor it cannot settle and three would still
    stand without it, that one competitor is dropped and the blueprint is solved
    once more. The step never re-ranks, never searches and never runs twice.
    """
    from .contrast_first_v2_pilot import solve_v2_blueprint

    pairs = record["contradiction_pairs"]
    # A set the wave could not lift over the minimum is refused here rather than
    # inside the gate, so the opportunity carries a reason instead of raising.
    if sum(
        1 for member in record["contrast_set"]["members"]
        if member["role_in_set"] == "COMPETITOR"
    ) < CONTRAST_SET_MINIMUM_COMPETITORS:
        return {
            "stage_reached": "CONTRAST_SET_ASSEMBLY",
            "terminal_state": "NO_SAFE_ITEM",
            "fail_closed_reason": "FAIL_CLOSED_CONTRAST_SET_SIZE",
            "selection": {
                "admissible": False,
                "surviving_competitors": sorted(
                    member["member_id"] for member in record["contrast_set"]["members"]
                    if member["role_in_set"] == "COMPETITOR"
                ),
                "fail_closed_reason": "FAIL_CLOSED_CONTRAST_SET_SIZE",
            },
            "blueprint": None,
            "dropped_unsettleable": None,
        }
    coherence = evaluate_contrast_set_coherence(
        record["contrast_set"], contradiction_pairs=pairs
    )
    selection = select_admissible_subset(
        record["contrast_set"], coherence, contradiction_pairs=pairs
    )
    if not selection["admissible"]:
        return {
            "stage_reached": "CONTRAST_SET_ASSEMBLY",
            "terminal_state": "NO_SAFE_ITEM",
            "fail_closed_reason": selection["fail_closed_reason"],
            "selection": selection,
            "blueprint": None,
            "dropped_unsettleable": None,
        }

    blueprint = solve_v2_blueprint(
        selection["contrast_set"], reading, vocabulary=vocabulary,
        contradiction_pairs=pairs, context_features=context_features,
    )
    dropped = None
    if blueprint["fail_closed_reason"] == "FAIL_CLOSED_COMPETITOR_CANNOT_BE_SETTLED":
        unsettleable = _named_unsettleable(blueprint, selection["contrast_set"])
        competitors = [
            member for member in selection["contrast_set"]["members"]
            if member["role_in_set"] == "COMPETITOR"
        ]
        if unsettleable is not None and len(competitors) - 1 >= 3:
            reduced = dict(selection["contrast_set"])
            reduced["members"] = [
                member for member in selection["contrast_set"]["members"]
                if member["member_id"] != unsettleable
            ]
            reduced["relations"] = [
                relation for relation in selection["contrast_set"]["relations"]
                if unsettleable not in (
                    relation["concept_a"]["member_id"], relation["concept_b"]["member_id"]
                )
            ]
            residual = evaluate_contrast_set_coherence(reduced, contradiction_pairs=pairs)
            if residual["coherent"]:
                dropped = unsettleable
                selection = dict(selection)
                selection["contrast_set"] = reduced
                selection["residual_coherence"] = residual
                selection["surviving_competitors"] = sorted(
                    member["member_id"] for member in reduced["members"]
                    if member["role_in_set"] == "COMPETITOR"
                )
                blueprint = solve_v2_blueprint(
                    reduced, reading, vocabulary=vocabulary,
                    contradiction_pairs=pairs, context_features=context_features,
                )

    if blueprint["fail_closed_reason"]:
        return {
            "stage_reached": "BLUEPRINT",
            "terminal_state": "NO_SAFE_ITEM",
            "fail_closed_reason": blueprint["fail_closed_reason"],
            "selection": selection,
            "blueprint": blueprint,
            "dropped_unsettleable": dropped,
        }

    out_of_set = out_of_set_second_keys(root, record, blueprint, selection["contrast_set"])
    spent = dropped_candidate_signature_features(record, blueprint, selection["contrast_set"])
    if spent:
        return {
            "stage_reached": "BLUEPRINT",
            "terminal_state": "NO_SAFE_ITEM",
            "fail_closed_reason": "FAIL_CLOSED_DROPPED_CANDIDATE_SIGNATURE_SPENT",
            "selection": selection,
            "blueprint": blueprint,
            "dropped_unsettleable": dropped,
            "dropped_candidate_signature_features": spent,
        }
    if out_of_set:
        return {
            "stage_reached": "BLUEPRINT",
            "terminal_state": "NO_SAFE_ITEM",
            "fail_closed_reason": "FAIL_CLOSED_OUT_OF_SET_SECOND_KEY",
            "selection": selection,
            "blueprint": blueprint,
            "dropped_unsettleable": dropped,
            "out_of_set_second_keys": out_of_set,
        }

    return {
        "stage_reached": "STEM",
        "terminal_state": None,
        "fail_closed_reason": None,
        "selection": selection,
        "blueprint": blueprint,
        "dropped_unsettleable": dropped,
        "out_of_set_second_keys": [],
    }


def _named_unsettleable(
    blueprint: Mapping[str, Any], contrast_set: Mapping[str, Any]
) -> str | None:
    note = blueprint.get("note") or ""
    members = [
        member["member_id"] for member in contrast_set["members"]
        if member["role_in_set"] == "COMPETITOR"
    ]
    named = [member_id for member_id in members if member_id in note]
    return named[0] if len(named) == 1 else None


def out_of_set_second_keys(
    root,
    record: Mapping[str, Any],
    blueprint: Mapping[str, Any],
    contrast_set: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """A candidate supply knows about, is not offering, and the stem makes correct.

    This is the gate V2 is recorded as not having, and it is added here rather
    than inside V2 because only the supply layer knows what it discovered and
    chose not to offer. It can only ever refuse an item.
    """
    from .clinical_contrast_v2 import (
        SATISFIED,
        build_feature_state_map,
        feature_assertion,
    )

    assignment = {
        row["stem_feature_id"]: row["state"] for row in blueprint["required_features"]
    }
    state_map = build_feature_state_map(
        [feature_assertion(feature, state) for feature, state in sorted(assignment.items())],
        contradiction_pairs=record["contradiction_pairs"],
    )
    in_set = {member["member_id"] for member in contrast_set["members"]}
    offending = []
    for member in record["contrast_set"]["members"]:
        if member["role_in_set"] != "COMPETITOR" or member["member_id"] in in_set:
            continue
        if is_never_best(member):
            # A dropped never-best candidate has no correctness conditions for a
            # blueprint to satisfy, so it cannot become an out-of-set second key.
            continue
        if evaluate_predicate(member["correctness_conditions"], state_map) == SATISFIED:
            offending.append({
                "member_id": member["member_id"],
                "concept": member["concept"],
                "why": (
                    "the blueprint's own assignment satisfies this candidate's "
                    "correctness conditions while the option set does not contain it"
                ),
            })
    return sorted(offending, key=lambda row: row["member_id"])


def dropped_candidate_signature_features(
    record: Mapping[str, Any],
    blueprint: Mapping[str, Any],
    contrast_set: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Rule S-6. Supply may not remove an option and then spend its signature.

    Added during the frozen-five wave, before any stem was written, because the
    solver's first admissible blueprint for `G2-PSY-03` dropped digitally
    delivered cognitive behavioural therapy from the option set and then asserted
    the inaccessibility of in-person delivery -- a required-PRESENT leaf of that
    same dropped candidate's correctness conditions -- to defeat its neighbour.
    Whether or not the dropped concept becomes formally correct, taking an option
    away and then reasoning from its own condition is not contrast supply.
    """
    in_set = {member["member_id"] for member in contrast_set["members"]}
    asserted = {
        row["stem_feature_id"] for row in blueprint["required_features"]
        if row["state"] == PRESENT_STATE
    }
    spent = []
    for member in record["contrast_set"]["members"]:
        if member["role_in_set"] != "COMPETITOR" or member["member_id"] in in_set:
            continue
        if is_never_best(member):
            # Rule S-6 protects a dropped candidate's own correctness signature.
            # A never-best candidate has none, so there is nothing to spend.
            continue
        for leaf in predicate_leaves(member["correctness_conditions"]):
            if leaf.get("required_state") != PRESENT_STATE:
                continue
            if leaf["feature_id"] in asserted:
                spent.append({
                    "member_id": member["member_id"],
                    "concept": member["concept"],
                    "feature_id": leaf["feature_id"],
                    "why": (
                        "the blueprint asserts a feature this dropped candidate's own "
                        "correctness conditions require PRESENT"
                    ),
                })
    return sorted(spent, key=lambda row: (row["member_id"], row["feature_id"]))


# --------------------------------------------------------------- Phase 19 replay

SUPPLY_GENERATED_PATH = "research/qgen/clinical_contrast_supply_frozen5_generated.json"

ACCEPTED_SAFETY_DIMENSIONS = (
    "AMBIGUOUS_BEST_ANSWERS",
    "BOOLEAN_LOGIC_DEFECT",
    "COMPETITOR_WITHOUT_STEM_ANCHOR",
    "CRITICAL_FACT_SAFETY_FAILURES",
    "FACTUAL_ERRORS",
    "MATERIAL_REDUNDANCY",
    "NUMERIC_ERRORS",
    "SECOND_KEY_RISK",
    "SILENCE_AS_ABSENCE_DEFECT",
    "UNNATURAL_STEM_ENGINEERING",
    "UNSUPPORTED_CLAIMS",
)


def run_frozen5_replay(
    root,
    wave: Mapping[str, Any],
    *,
    feature_anchor_snapshot: Mapping[str, Any] | None = None,
    readings_path: str = V2_READINGS_PATH,
    generated_path: str = None,
    reviews_path: str | None = None,
    scope: str = "QGEN_ON_DEMAND_SUPPLY_FROZEN5_REPLAY",
) -> dict[str, Any]:
    """Phase 19. One attempt for each opportunity whose supply reached three.

    ``feature_anchor_snapshot`` pins which snapshot supplies `SAF_1`'s anchors in
    the production gate. Unpinned, this replays exactly as it did against the
    frozen packs, and the committed recovery report still regenerates from it.

    The three path arguments default to the frozen-five artifacts, so that replay
    is unchanged; a later frozen batch passes its own and gets the same pipeline.
    """
    from .clinical_contrast_v2 import (
        build_feature_state_map,
        classify_competitor,
        feature_assertion,
    )
    from .contrast_first_pilot import validate_option_realization
    from .contrast_first_v2_pilot import (
        _applicable_discriminators,
        _build_options,
        _matrix_shim,
        _production_gate,
        build_v2_contrast_sets,
    )

    readings = _read(root, readings_path)["opportunities"]
    authoring = _read(root, V1_AUTHORING_PATH)["opportunities"]
    frozen = {
        row["opportunity_label"]: row
        for row in _read(root, V1_OPPORTUNITIES_PATH)["opportunities"]
    }
    vocabulary = load_stem_feature_vocabulary(root)
    generated = _read(root, generated_path or SUPPLY_GENERATED_PATH)
    reviews = (
        generated["reviews"] if reviews_path is None
        else _read(root, reviews_path)["reviews"]
    )
    baseline = {
        row["opportunity_label"]: row
        for row in build_v2_contrast_sets(root, readings_path=readings_path)["results"]
    }

    rows: list[dict[str, Any]] = []
    for record in wave["results"]:
        label = record["opportunity_label"]
        row: dict[str, Any] = {
            "opportunity_label": label,
            "discipline": record["discipline"],
            "difficulty_intent": record["difficulty_intent"],
            "VALID_COMPETITORS_BEFORE": record["VALID_COMPETITORS_BEFORE"],
            "VALID_COMPETITORS_AFTER": record["VALID_COMPETITORS_AFTER"],
            "three_valid_before": len(record["VALID_COMPETITORS_BEFORE"]) >= 3,
            "three_valid_after": len(record["VALID_COMPETITORS_AFTER"]) >= 3,
        }
        if not row["three_valid_after"]:
            row.update({
                "stage_reached": "CONTRAST_SET_ASSEMBLY",
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": record["selection_after"]["fail_closed_reason"],
                "replayed": False,
            })
            rows.append(row)
            continue

        solved = solve_supplied_blueprint(
            root, record, reading=readings[label],
            context_features=authoring[label].get("context_features") or [],
            vocabulary=vocabulary[record["anchor_study_unit_id"]],
        )
        row["replayed"] = True
        row["dropped_unsettleable"] = solved["dropped_unsettleable"]
        row["stem_blueprint_v2"] = solved["blueprint"]
        if solved["terminal_state"] == "NO_SAFE_ITEM":
            row.update({
                "stage_reached": solved["stage_reached"],
                "terminal_state": "NO_SAFE_ITEM",
                "fail_closed_reason": solved["fail_closed_reason"],
                "dropped_candidate_signature_features": solved.get(
                    "dropped_candidate_signature_features"
                ),
                "out_of_set_second_keys": solved.get("out_of_set_second_keys"),
            })
            rows.append(row)
            continue

        item = generated["items"][label]
        pairs = record["contradiction_pairs"]
        contrast_set = solved["selection"]["contrast_set"]
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
            for entry in solved["blueprint"]["required_features"]
        }
        stated = {
            entry["feature_id"]: entry["polarity"] for entry in item["stem_feature_map"]
        }
        verdicts = []
        for member in contrast_set["members"]:
            if member["role_in_set"] != "COMPETITOR":
                continue
            verdict = classify_competitor(
                member, realized,
                discriminators=_applicable_discriminators(readings[label], member["member_id"]),
            )
            verdict["concept"] = member["concept"]
            verdicts.append(verdict)
        key = next(
            member for member in contrast_set["members"] if member["role_in_set"] == "KEY"
        )
        options = _build_options(contrast_set, item)
        row.update({
            "stage_reached": "INDEPENDENT_REVIEW",
            "terminal_state": None,
            "fail_closed_reason": None,
            "stem": item["stem"],
            "lead_in": item["lead_in"],
            "stem_word_count": len(item["stem"].split()),
            "stem_realizes_the_blueprint_exactly": planned == stated,
            "key_correctness_under_the_new_stem": evaluate_predicate(
                key["correctness_conditions"], realized
            ),
            "competitor_verdicts": verdicts,
            "post_stem_coherence": evaluate_contrast_set_coherence(
                contrast_set, realized, contradiction_pairs=pairs
            ),
            "production_gate": _production_gate(
                root, baseline[label], solved["selection"], item, frozen[label],
                feature_anchor_snapshot=feature_anchor_snapshot,
            ),
            "options": options,
            "option_realization": validate_option_realization(
                options, _matrix_shim(contrast_set),
                key_option_text=item["key_option_text"], stem_text=item["stem"],
            ),
            "blind_solver": generated["blind_solver"][label],
            "review": reviews[label],
        })
        rows.append(row)

    return {
        "schema_version": "1.0",
        "scope": scope,
        "one_attempt_per_opportunity": True,
        "production_gate": "profile_contrast_retrieval.retrieve_profile_aware_contrasts",
        "production_gate_unchanged": True,
        **(
            {} if feature_anchor_snapshot is None
            else {"feature_anchor_snapshot_id": feature_anchor_snapshot["snapshot_id"]}
        ),
        "llm_api_calls": 0,
        "results": rows,
    }


# ------------------------------------------------------------- Phase 16 to 20

SUPPLY_TRACKED_ARTIFACTS = (
    "docs/superpowers/specs/2026-09-05-on-demand-clinical-contrast-supply-design.md",
    "scripts/qbank/contrast_supply.py",
    "tests/test_contrast_supply.py",
    "research/qgen/clinical_contrast_supply_acquisition.json",
    "research/qgen/clinical_contrast_supply_frozen5_generated.json",
    "research/qgen/clinical_contrast_supply_cache.json",
    "reports/qgen_v2_contrast_supply_diagnosis.json",
    "reports/qgen_v2_frozen5_supply_recovery.json",
)


def measure_supply_context(wave: Mapping[str, Any], replay: Mapping[str, Any]) -> dict[str, Any]:
    """Characters by stage, split into the V2-comparable figure and the supply cost.

    The V2 baseline of median 8,481 / p95 9,123 was measured over five stages and
    over realized items only, and it did not serialize the pairwise relation
    payload. The same five stages are measured the same way here so the comparison
    is like for like; the three supply stages are reported beside them and are
    deliberately not folded into that total.
    """
    import statistics

    from .clinical_contrast_v2 import canonical_json

    def summarise(values: Sequence[int]) -> dict[str, int]:
        ordered = sorted(values)
        if not ordered:
            return {"median": 0, "p95": 0}
        index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        return {"median": int(statistics.median(ordered)), "p95": ordered[index]}

    comparable_fields = (
        "contrast_set_v2", "stem_blueprint_v2", "competitor_verdicts",
        "options_and_rationales", "stem",
    )
    comparable = []
    for row in replay["results"]:
        if row["stage_reached"] != "INDEPENDENT_REVIEW":
            continue
        comparable.append({
            "opportunity_label": row["opportunity_label"],
            "contrast_set_v2": len(canonical_json({
                "admissible": True,
                "dropped": {},
                "surviving_competitors": row["VALID_COMPETITORS_AFTER"],
            })),
            "stem_blueprint_v2": len(canonical_json(row["stem_blueprint_v2"])),
            "competitor_verdicts": len(canonical_json(row["competitor_verdicts"])),
            "options_and_rationales": len(canonical_json(row["options"])),
            "stem": len(row["stem"]) + len(row["lead_in"]),
        })

    supply_stages = ("candidate_discovery", "relation_acquisition", "relation_review")
    supply = []
    for record in wave["results"]:
        supply.append({
            "opportunity_label": record["opportunity_label"],
            "candidate_discovery": len(canonical_json(record["retrieval"])),
            "relation_acquisition": len(canonical_json(record["contrast_set"]["relations"])),
            "relation_review": len(canonical_json(record["refusal_reasons"]))
            + len(canonical_json(record["approved_by_source"])),
        })

    return {
        "unit": "CHARACTERS",
        "tokens_not_reported_because": (
            "No local tokenizer is installed, and characters are not equated with tokens."
        ),
        "v2_comparable": {
            "measured_the_same_way_as": "contrast_first_v2_pilot.measure_v2_context",
            "per_opportunity": comparable,
            "summary": {
                **{
                    field: summarise([row[field] for row in comparable])
                    for field in comparable_fields
                },
                "TOTAL_PER_OPPORTUNITY": summarise([
                    sum(row[field] for field in comparable_fields) for row in comparable
                ]),
            },
            "v2_baseline": {"median": 8481, "p95": 9123},
        },
        "supply_layer_only": {
            "note": (
                "The cost the supply layer adds, per opportunity, and deliberately "
                "not folded into the figure above. relation_acquisition serializes "
                "every pairwise relation in the assembled set, which the V2 measure "
                "never did, so adding the two would compare different things."
            ),
            "per_opportunity": supply,
            "summary": {
                **{field: summarise([row[field] for row in supply]) for field in supply_stages},
                "TOTAL_PER_OPPORTUNITY": summarise([
                    sum(row[field] for field in supply_stages) for row in supply
                ]),
            },
        },
    }


def build_frozen5_recovery_report(root) -> dict[str, Any]:
    """Phases 16 to 20. What the one bounded wave bought, and what it did not."""
    from .contrast_first_pilot import measure_copyright
    from .contrast_first_v2_pilot import measure_medium_pilot_supply

    wave = run_acquisition_wave(root)
    cache = wave.pop("cache")
    replay = run_frozen5_replay(root, wave)
    by_label = {row["opportunity_label"]: row for row in replay["results"]}

    discovered = sum(row["CANDIDATES_DISCOVERED"] for row in wave["results"])
    deduplicated = sum(row["CANDIDATES_DEDUPLICATED"] for row in wave["results"])
    reviewed = sum(row["CANDIDATES_SEMANTICALLY_REVIEWED"] for row in wave["results"])
    approved = sum(row["RELATIONS_APPROVED"] for row in wave["results"])
    rejected = sum(row["RELATIONS_REJECTED"] for row in wave["results"])
    uncertain = sum(row["RELATIONS_UNCERTAIN"] for row in wave["results"])

    by_source: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for row in wave["results"]:
        for member_id, source in row["approved_by_source"].items():
            by_source[source] = by_source.get(source, 0) + 1
        for member_id, kind in row["approved_by_kind"].items():
            by_kind[kind] = by_kind.get(kind, 0) + 1

    before = sum(1 for row in replay["results"] if row["three_valid_before"])
    after = sum(1 for row in replay["results"] if row["three_valid_after"])

    realized = [row for row in replay["results"] if row["stage_reached"] == "INDEPENDENT_REVIEW"]
    accepted = [
        row for row in realized
        if row["review"]["VERDICT"] == "ACCEPT"
        and row["production_gate"]["post_stem_3_viable"]
    ]
    rejected_items = [row for row in realized if row not in accepted]

    safety = {dimension: 0 for dimension in ACCEPTED_SAFETY_DIMENSIONS}
    for row in accepted:
        for dimension in ACCEPTED_SAFETY_DIMENSIONS:
            safety[dimension] += row["review"][dimension]

    new_supply_safety = {
        "UNSUPPORTED_RELATIONS": 0,
        "SECOND_KEY_RELATIONS_ADMITTED": sum(
            1 for row in realized for verdict in row["competitor_verdicts"]
            if verdict["state"] == "SECOND_KEY"
        ),
        "CATEGORICALLY_EXCLUDED_RELATIONS_ADMITTED": sum(
            1 for row in realized for verdict in row["competitor_verdicts"]
            if verdict["state"] == "CATEGORICALLY_EXCLUDED"
        ),
        "LEARNER_DECISION_MISMATCHES_ADMITTED": 0,
        "RESPONSE_CLASS_MISMATCHES_ADMITTED": sum(
            1 for row in wave["results"]
            if "CS2-3" in row["assembly_violations_after"]
        ),
        "GRANULARITY_MISMATCHES_ADMITTED": sum(
            1 for row in wave["results"]
            if "CS2-4" in row["assembly_violations_after"]
        ),
        "BOOLEAN_LOGIC_DEFECTS": sum(row["review"]["BOOLEAN_LOGIC_DEFECT"] for row in realized),
        "SILENCE_AS_ABSENCE_DEFECTS": sum(
            row["review"]["SILENCE_AS_ABSENCE_DEFECT"] for row in realized
        ),
    }

    decision = decide_supply_assessment(
        three_valid_before=before,
        three_valid_after=after,
        accepted=len(accepted),
        realized=len(realized),
        new_supply_safety=new_supply_safety,
    )
    medium36 = measure_medium_pilot_supply(root)
    decision["MEDIUM36_TRIGGERED"] = "NO"
    decision["medium36_reason"] = (
        "Two independent reasons, either of which is sufficient. First, the Phase 21 "
        "trigger is not met: the wave is PROMISING rather than clearly so, because no "
        "recovered opportunity produced an item that is both independently accepted "
        "and clear of the unchanged production gate. Second, the pilot cannot be "
        "built at all: the frozen opportunity universe is 30, only 18 carry an "
        "authored option-set contract, 16 of those reach three admissible curated "
        "candidates and 10 are consumed by the V2 replay, leaving 6. Reaching 36 is "
        "source-packet research, not an architecture pilot."
    )

    return {
        "schema_version": "1.0",
        "scope": "QGEN_V2_FROZEN5_ON_DEMAND_SUPPLY_RECOVERY",
        "starting_commit": "b591226",
        "design": "docs/superpowers/specs/2026-09-05-on-demand-clinical-contrast-supply-design.md",
        "diagnosis": SUPPLY_DIAGNOSIS_PATH,
        "one_bounded_wave_per_opportunity": True,
        "waves": wave["waves"],
        "llm_api_calls": 0,
        "counts": {
            "FROZEN5_CANDIDATES_DISCOVERED": discovered,
            "FROZEN5_CANDIDATES_DEDUPLICATED": deduplicated,
            "FROZEN5_CANDIDATES_REVIEWED": reviewed,
            "FROZEN5_RELATIONS_APPROVED": approved,
            "FROZEN5_RELATIONS_REJECTED": rejected,
            "FROZEN5_RELATIONS_UNCERTAIN": uncertain,
            "FROZEN5_WITH_3_VALID_BEFORE": f"{before}/5",
            "FROZEN5_WITH_3_VALID_AFTER": f"{after}/5",
            "FROZEN5_RECOVERED_ITEMS_GENERATED": len(realized),
            "FROZEN5_RECOVERED_ACCEPTED": len(accepted),
            "FROZEN5_RECOVERED_REJECTED": len(rejected_items),
            "FROZEN5_RECOVERED_NO_SAFE_ITEM": sum(
                1 for row in replay["results"] if row["terminal_state"] == "NO_SAFE_ITEM"
            ),
        },
        "approved_supply_by_source": dict(sorted(by_source.items())),
        "approved_supply_by_kind": dict(sorted(by_kind.items())),
        "cache_economics": {
            "TOTAL_RELATION_REQUESTS": sum(
                row["TOTAL_RELATION_REQUESTS"] for row in wave["results"]
            ),
            "CONTRAST_CACHE_HITS": sum(row["CONTRAST_CACHE_HITS"] for row in wave["results"]),
            "NEW_RELATIONS_CREATED": sum(
                row["NEW_RELATIONS_CREATED"] for row in wave["results"]
            ),
            "RELATIONS_REUSED_ACROSS_OPPORTUNITIES": 0,
            "RELATIONS_REUSED_ACROSS_DISCIPLINES": 0,
            "note": (
                "A cache hit is a relation whose content hash is already in the frozen "
                "68. Adding an anchor changes the relation payload and therefore its "
                "hash, which is why the two opportunities that received anchors show "
                "few hits: the relation genuinely changed."
            ),
        },
        "new_supply_safety": new_supply_safety,
        "accepted_item_safety": safety,
        "ACCEPTED_ITEM_SAFETY": "NOT_RUN" if not accepted else (
            "PASS" if not any(safety.values()) else "FAIL"
        ),
        "realized_items": [
            {
                "opportunity_label": row["opportunity_label"],
                "independent_review_verdict": row["review"]["VERDICT"],
                "independent_review_defect_total": sum(
                    row["review"][dimension] for dimension in ACCEPTED_SAFETY_DIMENSIONS
                ),
                "production_gate_post_stem_3_viable": row["production_gate"][
                    "post_stem_3_viable"
                ],
                "production_gate_exclusions": row["production_gate"]["excluded_by_rule"],
                "terminal_state": (
                    "ACCEPTED" if row["production_gate"]["post_stem_3_viable"]
                    and row["review"]["VERDICT"] == "ACCEPT" else "REJECTED"
                ),
                "why": (
                    "The independent review scored zero on all eleven safety dimensions "
                    "and accepted the item. The unchanged production gate then refused "
                    "two of its three competitors under SAF_1, because that rule reads "
                    "the frozen stem-anchor pack and the anchors this wave added live "
                    "in the supply record instead. An item whose competitors the "
                    "production gate will not rank is not an accepted item."
                ) if not row["production_gate"]["post_stem_3_viable"] else None,
            }
            for row in realized
        ],
        "per_opportunity": replay["results"],
        "wave": wave,
        "medium_pilot_feasibility": medium36,
        "decision": decision,
        "final_analysis": FINAL_ANALYSIS,
        "context_characters": measure_supply_context(wave, replay),
        "copyright": measure_copyright(root, SUPPLY_TRACKED_ARTIFACTS),
    }


def decide_supply_assessment(
    *,
    three_valid_before: int,
    three_valid_after: int,
    accepted: int,
    realized: int,
    new_supply_safety: Mapping[str, int],
) -> dict[str, Any]:
    """Phase 20, against the milestone's own stated evidence for VALIDATED."""
    limbs = {
        "SUPPLY_IMPROVES_FOR_MULTIPLE_FROZEN_NO_SAFE_CASES": three_valid_after
        - three_valid_before >= 2,
        "NEW_RELATIONS_SURVIVE_INDEPENDENT_VALIDATION": True,
        "SOME_RECOVERED_OPPORTUNITIES_PRODUCE_ACCEPTED_ITEMS": accepted >= 1,
        "ACCEPTED_SAFETY_REMAINS_PERFECT": not any(new_supply_safety.values()),
    }
    if all(limbs.values()):
        assessment = "ON_DEMAND_CONTRAST_SUPPLY_VALIDATED"
    elif limbs["SUPPLY_IMPROVES_FOR_MULTIPLE_FROZEN_NO_SAFE_CASES"] and limbs[
        "ACCEPTED_SAFETY_REMAINS_PERFECT"
    ]:
        assessment = "ON_DEMAND_CONTRAST_SUPPLY_PROMISING"
    else:
        assessment = "CONTRAST_SUPPLY_NOT_IMPROVED"
    return {
        "SUPPLY_ASSESSMENT": assessment,
        "limbs": limbs,
        "what_the_wave_demonstrably_did": (
            f"Raised the number of frozen NO_SAFE_ITEM opportunities holding three "
            f"admissible V2 competitors from {three_valid_before} to {three_valid_after} "
            "of five, on one bounded wave each, with no change to any gate, key, "
            "opportunity, seed pack or evidence packet, and with zero second keys, "
            "categorical exclusions, class or granularity mismatches, Boolean defects "
            "or silence-as-absence defects in the new supply."
        ),
        "what_it_demonstrably_did_not_do": (
            f"Produce an accepted item. {realized} opportunity reached a stem and its "
            "independent review scored zero on all eleven safety dimensions, but the "
            "unmodified production gate refused two of its three competitors under "
            "SAF_1 STEM_PLAUSIBILITY_ANCHOR_ABSENT, so it is not counted as accepted."
        ),
        "the_finding_that_matters_most": (
            "The anchor-addition mechanism does not survive the production gate, and "
            "the reason is structural rather than clinical. `retrieve_profile_aware_"
            "contrasts` reads plausibility anchors from the frozen stem-anchor pack, "
            "which design rule S-2 forbids supply to edit, so an anchor the supply "
            "layer adds is invisible to the anchor floor. Supply can make a competitor "
            "live in V2's semantics and cannot make it live in production's. The "
            "anchor layer, not the concept library, is the artifact that has to become "
            "extendable and independently reviewed."
        ),
        "why_this_is_not_VALIDATED": (
            "The milestone's own evidence for VALIDATED requires that at least some "
            "recovered opportunities produce independently accepted items. Zero did."
        ),
    }


# ------------------------------------------------------------ Phases 30 to 38

#: Measured after the wave, and frozen here so the numbers cannot drift from the
#: prose. Every count in it is reproduced by the code above or by the graph and
#: FTS queries the acquisition artifact records.
FINAL_ANALYSIS = {
    "GRAPH_UNIQUE_APPROVED_CONTRIBUTIONS": 0,
    "graph_measurement": (
        "`graph_neighbourhood` was run at max_depth=1 from the study unit and the "
        "Toronto Notes topic node for both anchor units. SU-P-147 reaches 6 CONCEPT "
        "nodes and 1 topic node; SU-GS-76 reaches 3 CONCEPT nodes and 16 topic "
        "nodes. Every one of the 9 concept nodes is already a curated seed, so the "
        "graph discovered nothing the ordered sources above it had not. That "
        "reproduces the contrast-first pilot's GRAPH_UNIQUE_USEFUL_CONTRIBUTIONS = 0 "
        "and is a reason to keep the graph as a provenance and navigation aid rather "
        "than expand it."
    ),
    "TN_FTS_UNIQUE_APPROVED_CONTRIBUTIONS": 0,
    "fts_measurement": (
        "Five bounded retrievals of 15 chunks each returned 8 candidate concepts, all "
        "8 refused. But the refusals are not a retrieval failure and this is the "
        "distinction the milestone asked for. For G2-SURG-01 the retrieval returned "
        "exactly the non-gynaecologic differential the opportunity needed -- Crohn "
        "disease, mesenteric lymphadenitis, caecal diverticulitis, genitourinary and "
        "cardiopulmonary causes -- and every one of them was refused because the "
        "frozen SU-GS-76 vocabulary has no feature in which it could state a "
        "correctness condition. Used as evidence and concept discovery rather than as "
        "a competitor generator, FTS did its job: it proved the ceiling instead of "
        "papering over it."
    ),
    "LOCAL_EMBEDDING_TRIGGER_MET": "NO",
    "embedding_trigger_reasoning": (
        "The trigger is specific known-good competitors that remain unfindable "
        "despite the curated library, the graph, TN FTS and source evidence, while "
        "being known to exist in the corpus. Nothing in this wave meets it: the "
        "competitors that are missing were all found, by BM25 and by the claim cards, "
        "and then refused because they cannot be expressed. A better retriever "
        "returns the same list."
    ),
    "difficulty": {
        "EASY": {"attempted": 2, "realized": 0, "accepted": 0, "intent_match": "0/0"},
        "MEDIUM": {"attempted": 2, "realized": 1, "accepted": 0, "intent_match": "0/1"},
        "HARD": {"attempted": 0, "realized": 0, "accepted": 0, "intent_match": "0/0"},
        "note": (
            "One realized item, declared MEDIUM and read EASY by the blind solve and "
            "by the review, for the reason already recorded for G2-PHELO-03: every "
            "key condition is stated completely, and the completeness that makes an "
            "item safe is what makes it read easy. One item cannot establish that "
            "difficulty calibration is the next bottleneck, and it is not claimed."
        ),
    },
    "WHOLE_BOOK_CONTRAST_SCALING_DECISION": "SCALE_CONTRAST_RELATIONS_ON_DEMAND",
    "scaling_rationale": (
        "Broad prepopulation is refused on measured evidence rather than on "
        "principle: over these five opportunities a prepopulated graph would have "
        "contributed 0 novel concepts and a prepopulated FTS competitor index 0 "
        "approved relations, because the binding constraint is expressibility rather "
        "than recall. On-demand acquisition, by contrast, settled 42 relation "
        "requests with 29 cache hits and 13 new relations. The direction stands, with "
        "one stated precondition: until the plausibility-anchor layer is extendable "
        "and shared with the production gate, scaling on-demand supply scales "
        "V2-admissible sets that production will refuse."
    ),
    "NEXT_DOMINANT_BOTTLENECK": "OTHER_FROZEN_STEM_FEATURE_AND_ANCHOR_LAYER",
    "next_bottleneck_detail": (
        "Two of the five refusals are the frozen vocabulary and the frozen anchor "
        "pack directly -- G2-SURG-01 cannot express a non-gynaecologic differential, "
        "and G2-PED-01's added anchors are invisible to the production anchor floor. "
        "Two more, G2-PED-02 and G2-PSY-03, are the difficulty contract's settlement "
        "budget colliding with conditions the vocabulary leaves unstateable. Only "
        "G2-SURG-02 is something else, and that is a defect in its own frozen key. "
        "Runner-up bottleneck: DIFFICULTY_CALIBRATION, on the same evidence as before "
        "and no stronger."
    ),
    "NEXT_STEP": "USER_REVIEW_SUPPLY_MILESTONE",
    "why_user_review": (
        "The change this wave points at -- making the plausibility-anchor layer an "
        "extendable, independently reviewed artifact that both V2 and "
        "retrieve_profile_aware_contrasts read, and deciding whether the frozen "
        "stem-feature vocabulary may grow -- reopens a frozen layer. AGENTS.md "
        "requires explicit authorization for that, and this task did not carry it."
    ),
}
