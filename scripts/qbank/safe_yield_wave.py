"""Drive a bounded pool of question opportunities to terminal states.

This is the planning front end and reporting back end of the design wrapped
around the per-item gates. It has no target: an opportunity that ends in
``NO_SAFE_ITEM`` with a reason, or in ``REDUNDANT``, is a complete and correct
result for that opportunity, and the wave reports it alongside what was accepted
rather than as a shortfall.

Ordering is CORE first, so that the hard opportunities are attempted rather than
deferred. Nothing here re-runs an opportunity to improve a number.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .critical_fact_adjudication import adjudicate_evidence_packet
from .errors import QbankError
from .marginal_educational_value import assess_marginal_value
from .option_set_admissibility import (
    RESPONSE_CLASS_AXES,
    ARCHETYPE_RESPONSE_AXIS,
    adjudicate_option_set_admissibility,
    normalize_option_text,
    validate_role_blind_label_pool,
)
from .paths import resolve_root_path
from .profile_contrast_retrieval import (
    build_retrieval_index,
    load_seed_enrichment,
    retrieve_profile_aware_contrasts,
)
from .qgen_profiles import (
    DisciplineProfileError,
    load_discipline_profiles,
    resolve_option_set_contract,
)
from .question_opportunity import summarize_opportunities, transition_opportunity


class SafeYieldWaveError(QbankError):
    """A wave input is missing or inconsistent."""


PRIORITY_ORDER = {"CORE": 0, "IMPORTANT": 1, "SUPPORTING": 2, "NOT_IN_SCOPE": 3}

SEED_PROVENANCE_CLASSES = frozenset({"ORIGINAL_CURATED", "TARGETED_NEW"})

# The three criteria a retrieved competitor is judged against once the stem is
# realised. They are semantic rather than arithmetic, so the verdicts are
# authored and frozen; what the wave owns is applying them without exception and
# recomputing the selection rule they feed.
SEMANTIC_ADMISSIBILITY_CRITERIA = frozenset({
    "SA_1_DECISION_GRANULARITY_MATCH",
    "SA_2_STEM_ANCHOR_PRESENT",
    "SA_3_CONTEXTUALLY_PLAUSIBLE",
})

MINIMUM_SEMANTICALLY_ADMISSIBLE_COMPETITORS = 3

_FACT_REASON = {
    "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT": "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT",
    "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT": "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
}


def _read(root: Path, relative: str) -> dict[str, Any]:
    path = resolve_root_path(root, relative)
    if not path.is_file():
        raise SafeYieldWaveError(f"wave input is unavailable: {relative}")
    return json.loads(path.read_text())


def build_contrast_index(root: Path, library: dict[str, Any]) -> list[dict[str, Any]]:
    """Build one retrieval index over every declared curated pack.

    Packs are read side by side rather than merged on disk, so the curated
    82-seed pack stays byte-identical and a targeted incremental pack is additive.
    A pack without its own frozen enrichment is refused: unenriched seeds carry no
    correctness conditions, so admitting them would return retrieval to the
    generic similarity matching the design rules out.
    """
    root = Path(root).resolve()
    packs = list(library.get("seed_packs") or [])
    enrichments = list(library.get("enrichments") or [])
    if not packs:
        raise SafeYieldWaveError("a contrast library must declare at least one seed pack")
    if len(packs) != len(enrichments):
        raise SafeYieldWaveError(
            "every declared seed pack needs exactly one enrichment, in the same order"
        )
    # Which pack a competitor came from is a reported result, so the classes are
    # declared by the caller rather than inferred from a pack id or a filename.
    classes = list(library.get("provenance_classes") or ["ORIGINAL_CURATED"] * len(packs))
    if len(classes) != len(packs):
        raise SafeYieldWaveError(
            "every declared seed pack needs exactly one provenance class, in the same order"
        )
    unknown = sorted(set(classes) - SEED_PROVENANCE_CLASSES)
    if unknown:
        raise SafeYieldWaveError(f"unknown seed provenance class: {', '.join(unknown)}")
    index: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pack_relative, enrichment_relative, provenance in zip(packs, enrichments, classes):
        pack = _read(root, pack_relative)
        enrichment = load_seed_enrichment(root, enrichment_relative)
        for row in build_retrieval_index(pack, enrichment):
            if row["seed_id"] in seen:
                raise SafeYieldWaveError(f"seed appears in two packs: {row['seed_id']}")
            seen.add(row["seed_id"])
            index.append(dict(row, source_pack=pack_relative, provenance=provenance))
    return sorted(index, key=lambda row: row["seed_id"])


def unretrieved_distractors(
    options: list[dict[str, Any]], ranked_competitors: list[dict[str, Any]]
) -> list[str]:
    """Return distractor texts that profile-aware retrieval did not produce.

    The key is exempt by construction: a key that retrieval returned would be a
    second answer, and the retrieval stage already refuses such a seed.
    """
    retrieved = {row["normalized_competitor_text"] for row in ranked_competitors}
    return [
        str(option.get("text"))
        for option in options
        if option.get("role") == "DISTRACTOR"
        and normalize_option_text(option.get("text")) not in retrieved
    ]


def load_semantic_admissibility(root: Path, relative: str) -> dict[str, dict[str, Any]]:
    """Load the frozen per-opportunity semantic verdicts over retrieved competitors.

    The verdicts are authored, because whether a competitor answers the same
    question at the same grain is not an arithmetic property. Freezing them
    separately from the wave is what stops a generator that cannot raise three
    competitors from re-judging its way to three.
    """
    document = _read(root, relative)
    if not document.get("frozen"):
        raise SafeYieldWaveError("semantic-admissibility judgements must be frozen before use")
    rows = document.get("opportunities")
    if not isinstance(rows, list):
        raise SafeYieldWaveError("semantic-admissibility judgements carry no opportunities")
    judgements: dict[str, dict[str, Any]] = {}
    for row in rows:
        label = row.get("opportunity_label")
        if not isinstance(label, str) or not label:
            raise SafeYieldWaveError("a semantic-admissibility record needs an opportunity label")
        if label in judgements:
            raise SafeYieldWaveError(f"duplicate semantic-admissibility record: {label}")
        judgements[label] = row
    return judgements


def select_semantically_admissible(
    ranked_competitors: list[dict[str, Any]],
    judgement: dict[str, Any],
    *,
    minimum: int = MINIMUM_SEMANTICALLY_ADMISSIBLE_COMPETITORS,
) -> dict[str, Any]:
    """Apply the frozen verdicts to ranked retrieval output and select the set.

    Every retrieved competitor must be judged, in rank order, so that nothing is
    selected unseen and nothing is judged that retrieval never returned. The
    selection rule - the first three ranked competitors that pass all three
    criteria - is recomputed here and the declared selection is checked against
    it rather than trusted.
    """
    ranked_ids = [row["seed_id"] for row in ranked_competitors]
    judged = judgement.get("judged_competitors")
    if not isinstance(judged, list):
        raise SafeYieldWaveError("a semantic-admissibility record needs judged competitors")
    judged_ids = [row.get("seed_id") for row in judged]
    if judged_ids != ranked_ids:
        raise SafeYieldWaveError(
            "the judged competitors are not the retrieved competitors in rank order: "
            f"judged {judged_ids}, retrieved {ranked_ids}"
        )
    verdicts: dict[str, dict[str, Any]] = {}
    refused: dict[str, str] = {}
    for row in judged:
        verdict = row.get("verdict")
        criterion = row.get("failed_criterion")
        if verdict not in {"ADMITTED", "REFUSED"}:
            raise SafeYieldWaveError(f"unknown semantic verdict for {row.get('seed_id')}: {verdict}")
        if verdict == "ADMITTED" and criterion is not None:
            raise SafeYieldWaveError(
                f"an admitted competitor may not carry a failed criterion: {row.get('seed_id')}"
            )
        if verdict == "REFUSED":
            if criterion not in SEMANTIC_ADMISSIBILITY_CRITERIA:
                raise SafeYieldWaveError(
                    f"a refused competitor needs a known failed criterion: {row.get('seed_id')}"
                )
            refused[row["seed_id"]] = criterion
        verdicts[row["seed_id"]] = row
    survivors = [
        row for row in ranked_competitors if verdicts[row["seed_id"]]["verdict"] == "ADMITTED"
    ]
    selected = survivors[:minimum]
    declared = judgement.get("selected_seed_ids")
    if declared is not None and list(declared) != [row["seed_id"] for row in selected]:
        raise SafeYieldWaveError(
            f"the declared selection is not the first {minimum} admitted competitors in rank "
            f"order: declared {list(declared)}"
        )
    return {
        "verdicts": verdicts,
        "refused": refused,
        "survivors": survivors,
        "selected": selected,
        "sufficient": len(survivors) >= minimum,
    }


def competitor_predicates_from_retrieval(
    ranked_competitors: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Key each retrieved competitor's frozen correctness conditions by option text.

    This is what lets ADM-3 run over realised items. In G1 it could fire only on
    the positive controls, because no stage supplied predicates for a real one.
    """
    return {
        row["normalized_competitor_text"]: list(row.get("condition_predicates") or [])
        for row in ranked_competitors
    }


def run_safe_yield_wave(
    root: Path,
    *,
    opportunities_relative_path: str,
    plan_relative_path: str,
    items_relative_path: str,
    labels_relative_path: str,
    assignments_relative_path: str,
    contrast_library: dict[str, Any] | None = None,
    semantic_admissibility_relative_path: str | None = None,
) -> dict[str, Any]:
    """Drive every opportunity in a wave and return its result record.

    When ``contrast_library`` is supplied the wave runs profile-aware retrieval
    over the curated library between evidence and contrast readiness, judges every
    retrieved competitor against the frozen semantic criteria, refuses any
    opportunity that cannot raise three semantically admissible competitors, and
    refuses any item carrying a distractor the selection did not produce.

    The semantic judgements are required alongside the library rather than
    optional beside it. Retrieval keys on discipline, item archetype and
    option-set archetype and not on the learner decision, so without them a seed
    curated for one decision is realisable against another.
    """
    root = Path(root).resolve()
    opportunities = _read(root, opportunities_relative_path)["opportunities"]
    plan = {row["opportunity_label"]: row for row in _read(root, plan_relative_path)["plan"]}
    items = {row["opportunity_label"]: row for row in _read(root, items_relative_path)["items"]}
    label_pool = validate_role_blind_label_pool(_read(root, labels_relative_path))
    assignments = {
        row["opportunity_label"]: row
        for row in _read(root, assignments_relative_path)["assignments"]
    }
    probes = _read(root, plan_relative_path).get("admissibility_probes", [])
    profiles = load_discipline_profiles(root)
    contrast_index = build_contrast_index(root, contrast_library) if contrast_library else None
    judgements: dict[str, dict[str, Any]] | None = None
    if contrast_index is not None:
        if not semantic_admissibility_relative_path:
            raise SafeYieldWaveError(
                "a wave with a contrast library needs its frozen semantic-admissibility "
                "judgements: retrieval cannot refuse a competitor curated for another decision"
            )
        judgements = load_semantic_admissibility(root, semantic_admissibility_relative_path)
    elif semantic_admissibility_relative_path:
        raise SafeYieldWaveError(
            "semantic-admissibility judgements were supplied without a contrast library"
        )

    fact_cache: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}

    def facts(packet_relative: str, profile_id: str) -> dict[str, dict[str, Any]]:
        key = (packet_relative, profile_id)
        if key not in fact_cache:
            fact_cache[key] = adjudicate_evidence_packet(
                root,
                _read(root, packet_relative),
                profile_risk_classes=profiles[profile_id]["numeric_risk_classes"],
            )
        return fact_cache[key]

    ordered = sorted(
        opportunities,
        key=lambda row: (PRIORITY_ORDER[row["priority_class"]], row["wave_label"]),
    )

    accepted_tuples: dict[str, list[dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []
    novelty_verdict_stream: list[str] = []
    gate_verdicts: dict[str, list[str]] = {}

    for opportunity in ordered:
        label = opportunity["wave_label"]
        entry = plan.get(label)
        if entry is None:
            raise SafeYieldWaveError(f"no wave plan entry for {label}")
        profile = profiles[opportunity["discipline_profile_id"]]
        record: dict[str, Any] = {
            "wave_label": label,
            "opportunity_id": opportunity["opportunity_id"],
            "discipline": opportunity["discipline"],
            "priority_class": opportunity["priority_class"],
            "learner_decision_id": opportunity["learner_decision_id"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": opportunity["option_set_archetype"],
        }

        # Stage 1 and 4 - profile binding, and the archetype declaration itself.
        try:
            contract = resolve_option_set_contract(
                profile, opportunity["item_archetype"], opportunity["option_set_archetype"]
            )
        except DisciplineProfileError as error:
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM",
                reason="FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE",
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
                "detail": str(error),
            })
            results.append(record)
            continue

        # Marginal educational value, pre-generation, over structured tuples only.
        topic = opportunity["anchor_study_unit_id"]
        novelty = assess_marginal_value(entry["novelty_tuple"], accepted_tuples.get(topic, []))
        novelty_verdict_stream.append(novelty["verdict"])
        gate_verdicts.setdefault("MARGINAL_EDUCATIONAL_VALUE", []).append(
            "REDUNDANT" if novelty["verdict"] == "REDUNDANT" else "NOVEL"
        )
        record["novelty_verdict"] = novelty["verdict"]
        if novelty["verdict"] == "REDUNDANT":
            transition_opportunity(opportunity, "REDUNDANT", reason="FAIL_CLOSED_REDUNDANT")
            record.update({"state": opportunity["state"], "novelty_basis": novelty["basis"]})
            results.append(record)
            continue

        # Critical facts, at claim level, inherited by the item.
        records = facts(entry["evidence_packet"], opportunity["discipline_profile_id"])
        unusable = [
            records[claim_id]
            for claim_id in entry["planned_evidence_refs"]
            if claim_id in records and not records[claim_id]["usable_in_generation"]
        ]
        missing = [
            claim_id for claim_id in entry["planned_evidence_refs"] if claim_id not in records
        ]
        gate_verdicts.setdefault("CRITICAL_FACT_ADJUDICATION", []).append(
            "FAIL" if unusable or missing else "PASS"
        )
        if missing:
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM", reason="FAIL_CLOSED_INSUFFICIENT_EVIDENCE"
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
                "missing_claim_ids": missing,
            })
            results.append(record)
            continue
        if unusable:
            reason = next(
                (
                    row.get("fail_closed_reason")
                    for row in unusable
                    if row.get("fail_closed_reason") == "FAIL_CLOSED_ERRONEOUS_SOURCE_FACT"
                ),
                "FAIL_CLOSED_UNRESOLVED_CRITICAL_FACT",
            )
            transition_opportunity(opportunity, "NO_SAFE_ITEM", reason=_FACT_REASON[reason])
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
                "critical_fact_failures": [
                    {
                        "claim_id": row["claim_id"],
                        "fact_classes": row["fact_classes"],
                        "basis": row["adjudication_basis"],
                        "sanity_checks": [check["check"] for check in row["sanity_findings"]],
                    }
                    for row in unusable
                ],
            })
            results.append(record)
            continue

        transition_opportunity(
            opportunity, "EVIDENCE_READY",
            decisive_discriminator=entry["novelty_tuple"]["decisive_discriminator"],
        )

        assignment = assignments[label]
        competitor_predicates = None
        # The stem and its feature map are realised before any option exists, so the plan
        # carries them and retrieval runs against them. A wave without a contrast library
        # predates this stage and still reads the map from the item.
        plan_features = entry.get("stem_feature_map")
        if contrast_index is not None and plan_features is None:
            raise SafeYieldWaveError(
                f"{label}: a wave with a contrast library needs the plan's stem feature map"
            )

        # Profile-aware contrast retrieval. The stage runs against the realised
        # stem's feature map, so it answers whether an approved seed is a
        # competitor *for this stem* rather than for the abstract target it was
        # curated against.
        if contrast_index is not None:
            axis = ARCHETYPE_RESPONSE_AXIS[opportunity["option_set_archetype"]]
            retrieval = retrieve_profile_aware_contrasts(
                index=contrast_index,
                discipline_profile_id=opportunity["discipline_profile_id"],
                item_archetype=opportunity["item_archetype"],
                option_set_archetype=opportunity["option_set_archetype"],
                demanded_response_class=assignment["demanded_response_class"],
                token_implications=contract.get("token_implications", {}),
                generic_token=RESPONSE_CLASS_AXES[axis]["generic_token"],
                stem_feature_map={"features": plan_features},
                ranking_preference=profile["competitor_ranking_preference"],
            )
            gate_verdicts.setdefault("PROFILE_AWARE_CONTRAST_RETRIEVAL", []).append(
                "FAIL_CLOSED" if retrieval["fail_closed_reason"] else "SUFFICIENT"
            )
            # Provenance, persisted whatever the outcome. It has to be enough to
            # prove that a realised distractor came through this path: what was
            # asked, what came back, in what order, from which pack, what each
            # filter said about it, and which three were selected.
            record["retrieval"] = {
                "query": {
                    "discipline_profile_id": opportunity["discipline_profile_id"],
                    "item_archetype": opportunity["item_archetype"],
                    "option_set_archetype": opportunity["option_set_archetype"],
                    "demanded_response_class": assignment["demanded_response_class"],
                    "learner_decision_id": opportunity["learner_decision_id"],
                    "ranking_preference": list(profile["competitor_ranking_preference"]),
                    "stem_feature_ids": [
                        feature["feature_id"] for feature in plan_features
                    ],
                },
                "indexed_count": retrieval["indexed_count"],
                "admissible_count": retrieval["admissible_count"],
                "ranked_seed_ids": [row["seed_id"] for row in retrieval["ranked_competitors"]],
                "ranked_competitors": [
                    {
                        "rank": rank,
                        "seed_id": row["seed_id"],
                        "source_pack": row.get("source_pack"),
                        "provenance": row.get("provenance"),
                        "competitor_concept": row["competitor_concept"],
                        "competitor_concept_id": row["competitor_concept_id"],
                        "satisfied_conditions": row["satisfied_conditions"],
                        "total_conditions": row["total_conditions"],
                        "reviewed_strength": row["reviewed_strength"],
                    }
                    for rank, row in enumerate(retrieval["ranked_competitors"], start=1)
                ],
                "excluded": retrieval["excluded"],
                "fail_closed_reason": retrieval["fail_closed_reason"],
            }
            if retrieval["fail_closed_reason"]:
                transition_opportunity(
                    opportunity, "NO_SAFE_ITEM",
                    reason="FAIL_CLOSED_INSUFFICIENT_ADMISSIBLE_COMPETITORS",
                )
                record.update({
                    "state": opportunity["state"],
                    "fail_closed_reason": opportunity["fail_closed_reason"],
                    "reopens_on": opportunity["reopens_on"],
                })
                results.append(record)
                continue

            # Semantic contrast admissibility. Retrieval answers whether a seed
            # shares this profile, archetype and response class; it cannot answer
            # whether the competitor addresses this learner decision at the key's
            # grain, is anchored in the realised stem, or is selectable for this
            # patient. That is judged here, over the retrieved set only.
            judgement = judgements.get(label)
            if judgement is None:
                raise SafeYieldWaveError(
                    f"{label}: no semantic-admissibility judgement for a retrieved competitor set"
                )
            semantic = select_semantically_admissible(
                retrieval["ranked_competitors"], judgement
            )
            selected_rows = semantic["selected"]
            selected_ids = [row["seed_id"] for row in selected_rows]
            for candidate in record["retrieval"]["ranked_competitors"]:
                verdict = semantic["verdicts"][candidate["seed_id"]]
                candidate["semantic_verdict"] = verdict["verdict"]
                candidate["semantic_failed_criterion"] = verdict.get("failed_criterion")
            record["retrieval"].update({
                "semantically_admissible_count": len(semantic["survivors"]),
                "semantic_refusals": [
                    {"seed_id": seed_id, "failed_criterion": criterion}
                    for seed_id, criterion in sorted(semantic["refused"].items())
                ],
                "selected_competitor_seed_ids": selected_ids,
            })
            gate_verdicts.setdefault("SEMANTIC_CONTRAST_ADMISSIBILITY", []).append(
                "SUFFICIENT" if semantic["sufficient"] else "FAIL_CLOSED"
            )
            if not semantic["sufficient"]:
                # Fewer than three competitors survive judgement. Nothing tops the
                # set up from the refused ones and nothing re-judges to reach three.
                transition_opportunity(
                    opportunity, "NO_SAFE_ITEM",
                    reason="FAIL_CLOSED_INSUFFICIENT_SEMANTICALLY_ADMISSIBLE_COMPETITORS",
                )
                record.update({
                    "state": opportunity["state"],
                    "fail_closed_reason": opportunity["fail_closed_reason"],
                    "reopens_on": opportunity["reopens_on"],
                })
                results.append(record)
                continue
            competitor_predicates = competitor_predicates_from_retrieval(selected_rows)

        item = items.get(label)
        if item is None:
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM", reason="FAIL_CLOSED_UNINSTANTIABLE_REASONING"
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
            })
            results.append(record)
            continue
        if plan_features is not None and item["stem_feature_map"] != plan_features:
            raise SafeYieldWaveError(
                f"{label}: the item's stem feature map disagrees with the plan's, so retrieval "
                "and adjudication would not have run against the same stem"
            )
        stem_feature_map = {
            "features": plan_features if plan_features is not None else item["stem_feature_map"]
        }

        if contrast_index is not None:
            # An option the retrieval stage never produced was authored freehand,
            # which is the practice this stage exists to remove. It is a
            # construction error rather than a clinical outcome, so it is loud.
            unretrieved = unretrieved_distractors(item["options"], selected_rows)
            if unretrieved:
                raise SafeYieldWaveError(
                    f"{label}: distractors were not produced by retrieval: {unretrieved}"
                )

        transition_opportunity(opportunity, "CONTRAST_READY")
        transition_opportunity(opportunity, "GENERATABLE")

        admissibility = adjudicate_option_set_admissibility(
            option_set_archetype=opportunity["option_set_archetype"],
            contract=contract,
            demanded_response_class=assignment["demanded_response_class"],
            options=item["options"],
            label_pool=label_pool,
            stem_feature_map=stem_feature_map,
            competitor_condition_predicates=competitor_predicates,
            key_grounding_feature_ids=item.get("key_grounding_feature_ids"),
            enacted_action_signatures=entry.get("enacted_action_signatures", []),
        )
        for rule, verdict in admissibility["rule_verdicts"].items():
            gate_verdicts.setdefault(rule, []).append(verdict)
        record["admissibility"] = admissibility
        if admissibility["verdict"] != "ADMISSIBLE":
            transition_opportunity(
                opportunity, "NO_SAFE_ITEM",
                reason=admissibility["fail_closed_reason"]
                or "FAIL_CLOSED_INCOHERENT_OPTION_SET_ARCHETYPE",
            )
            record.update({
                "state": opportunity["state"],
                "fail_closed_reason": opportunity["fail_closed_reason"],
                "reopens_on": opportunity["reopens_on"],
            })
            results.append(record)
            continue

        # The item is realised and internally sound. Acceptance still waits on
        # fresh independent verification, which is recorded separately.
        record.update({
            "state": "GENERATABLE",
            "item_id": item["item_id"],
            "awaiting": "FRESH_INDEPENDENT_VERIFICATION",
        })
        accepted_tuples.setdefault(topic, []).append(
            dict(entry["novelty_tuple"], item_reference=item["item_id"])
        )
        results.append(record)

    # Positive controls. Each probe is an option set built to violate exactly one
    # admissibility rule. Probes never enter the opportunity pool and never count
    # toward yield; they exist so that a wave in which every real item passes can
    # still show that the rule family is live rather than inert.
    probe_results: list[dict[str, Any]] = []
    for probe in probes:
        profile = profiles[probe["discipline_profile_id"]]
        contract = resolve_option_set_contract(
            profile, probe["item_archetype"], probe["option_set_archetype"]
        )
        verdict = adjudicate_option_set_admissibility(
            option_set_archetype=probe["option_set_archetype"],
            contract=contract,
            demanded_response_class=probe["demanded_response_class"],
            options=probe["options"],
            label_pool=label_pool,
            stem_feature_map={"features": probe.get("stem_feature_map", [])},
            competitor_condition_predicates=probe.get("competitor_condition_predicates"),
            key_grounding_feature_ids=probe.get("key_grounding_feature_ids"),
            enacted_action_signatures=probe.get("enacted_action_signatures", []),
        )
        for rule, value in verdict["rule_verdicts"].items():
            gate_verdicts.setdefault(rule, []).append(value)
        probe_results.append({
            "probe_id": probe["probe_id"],
            "targets_rule": probe["targets_rule"],
            "rule_verdicts": verdict["rule_verdicts"],
            "fired": verdict["rule_verdicts"][probe["targets_rule"]] == "FAIL",
            "verdict": verdict["verdict"],
        })

    return {
        "schema_version": "1.0",
        "scope": "QGEN_SAFE_YIELD_WAVE_EXECUTION",
        "wave_id": _read(root, opportunities_relative_path)["wave_id"],
        "opportunities": opportunities,
        "results": results,
        "gate_verdicts": gate_verdicts,
        "novelty_verdict_stream": novelty_verdict_stream,
        "admissibility_probes": probe_results,
        "pre_verification_summary": summarize_opportunities(opportunities),
    }
