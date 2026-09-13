from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.qbank.registry_v3_canonicalization import (
    ADJUDICATION_TIERS,
    DESTRUCTIVE_RELATIONS,
    RELATION_EFFECT,
    RELATION_RANK,
    RELATIONS,
    atomic_signature,
    build_adjudication_queue,
    build_benchmark_adjudication_queue,
    build_candidate_recall_audit,
    build_input_manifest,
    build_v3_contract,
    candidate_tier,
    content_sha256,
    decision_tokens,
    exact_duplicate_invariants,
    load_frozen_gold_relations,
    mine_benchmark_candidates,
    mine_registry_candidates,
    pair_id,
    resolve_exact_duplicates,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return build_input_manifest(ROOT)


@pytest.fixture(scope="module")
def pool() -> dict:
    return mine_registry_candidates(ROOT)


@pytest.fixture(scope="module")
def frozen() -> dict:
    return load_frozen_gold_relations(ROOT)


# --------------------------------------------------------------------------
# Frozen inputs (Phase 2 / Phase 28)
# --------------------------------------------------------------------------


def test_input_manifest_pins_immutable_registry_v2(manifest: dict) -> None:
    registry_v2 = manifest["inputs"]["registry_v2"]
    assert registry_v2["rows"] == 2001
    assert registry_v2["mutable"] is False
    assert manifest["registry_v2_is_immutable_input"] is True
    assert sum(registry_v2["discipline_counts"].values()) == registry_v2["rows"]


def test_input_manifest_hashes_match_files_on_disk(manifest: dict) -> None:
    for entry in manifest["inputs"].values():
        payload = json.loads((ROOT / entry["path"]).read_text())
        assert payload["content_sha256"] == entry["content_sha256"]


def test_artifacts_carry_self_consistent_content_hashes(manifest: dict, pool: dict, frozen: dict) -> None:
    for artifact in (manifest, pool, frozen, build_v3_contract()):
        assert artifact["content_sha256"] == content_sha256(artifact)


# --------------------------------------------------------------------------
# Contract (Phase 3 / Phase 4)
# --------------------------------------------------------------------------


def test_contract_defines_an_effect_for_every_relation() -> None:
    contract = build_v3_contract()
    assert set(contract["relation_effect"]) == set(RELATIONS)
    assert RELATION_EFFECT["DUPLICATE"] == "COLLAPSE_TO_ONE_CANONICAL_DECISION"
    assert RELATION_EFFECT["EQUIVALENT"] == "COLLAPSE_TO_ONE_CANONICAL_DECISION"
    assert RELATION_EFFECT["VARIANT_OF_SAME_DECISION"] == "ATTACH_AS_VARIANT_NOT_COVERAGE_UNIT"
    assert RELATION_EFFECT["NEAR_DUPLICATE"] == "RETAIN_SEPARATE_WITH_REVIEW_FLAG"
    assert RELATION_EFFECT["RELATED_BUT_DISTINCT"] == "KEEP_SEPARATE"
    assert RELATION_EFFECT["UNCERTAIN"].startswith("FAIL_CLOSED")


def test_near_duplicate_never_merges_automatically() -> None:
    assert "NEAR_DUPLICATE" not in DESTRUCTIVE_RELATIONS
    assert "MERGE" not in RELATION_EFFECT["NEAR_DUPLICATE"]
    assert "COLLAPSE" not in RELATION_EFFECT["NEAR_DUPLICATE"]


def test_uncertain_and_unrelated_rank_below_every_binding_relation() -> None:
    assert RELATION_RANK["UNCERTAIN"] == 0
    assert RELATION_RANK["UNRELATED"] == 0
    assert RELATION_RANK["DUPLICATE"] == max(RELATION_RANK.values())


# --------------------------------------------------------------------------
# Deterministic primitives
# --------------------------------------------------------------------------


def test_pair_id_is_order_independent_and_not_positional() -> None:
    assert pair_id("QOP-V2-A", "QOP-V2-B") == pair_id("QOP-V2-B", "QOP-V2-A")
    assert pair_id("QOP-V2-A", "QOP-V2-B") != pair_id("QOP-V2-A", "QOP-V2-C")


def test_atomic_signature_drops_non_material_state() -> None:
    row = {
        "study_unit_id": "SU-X-1",
        "response_class": "DIAGNOSIS",
        "action_lemma": "recognize",
        "clinical_object": "Acute Coronary Syndrome",
        "key_concept_or_action": "ignored when clinical_object present",
        "clinical_stage": "NA",
        "population_context": "NA",
    }
    signature = atomic_signature(row)
    assert signature["decision_operator"] == "diagnose"
    assert signature["decision_object"] == "acute coronary syndrome"
    assert signature["material_state"] is None
    assert signature["material_population"] is None


def test_decision_tokens_drop_generic_scaffolding_words() -> None:
    tokens = decision_tokens({"learner_decision": "Apply differential reasoning for the vignette evidence."})
    assert "differential" in tokens
    assert not tokens & {"apply", "reasoning", "the", "vignette", "evidence"}


# --------------------------------------------------------------------------
# Candidate discovery (Phase 5)
# --------------------------------------------------------------------------


def test_candidate_pool_is_bounded_far_below_all_pairs(pool: dict) -> None:
    assert pool["candidate_pairs"] < pool["total_possible_pairs"] / 50
    assert pool["queued_pairs"] < pool["candidate_pairs"] / 10
    assert set(pool["tier_counts"]) <= set(
        tier for tier in pool["tier_counts"]
    )


def test_only_high_impact_tiers_are_queued(pool: dict) -> None:
    for candidate in pool["candidates"]:
        assert candidate["queued_for_adjudication"] == (candidate["tier"] in ADJUDICATION_TIERS)


def test_candidate_pool_assigns_no_semantic_label(pool: dict) -> None:
    for candidate in pool["candidates"][:200]:
        assert "relation" not in candidate
    assert "NO_SEMANTIC_LABEL_ASSIGNMENT" in pool["selection_policy"]


def test_candidate_pair_ids_are_unique_and_symmetric(pool: dict) -> None:
    ids = [candidate["pair_id"] for candidate in pool["candidates"]]
    assert len(ids) == len(set(ids))
    for candidate in pool["candidates"][:50]:
        assert candidate["pair_id"] == pair_id(candidate["b_opportunity_id"], candidate["a_opportunity_id"])


def test_candidate_tier_requires_shared_scope_for_high_tiers() -> None:
    left = {
        "study_unit_id": "SU-A-1",
        "clinical_topic": "Topic A",
        "response_class": "DIAGNOSIS",
        "opportunity_family": "DIAGNOSIS",
        "action_lemma": "recognize",
        "clinical_object": "thing",
        "key_concept_or_action": "thing",
        "clinical_stage": "NA",
        "population_context": "NA",
    }
    right = dict(left, study_unit_id="SU-B-2", clinical_topic="Topic B")
    assert candidate_tier(left, dict(left), set(), set()) == "T1_EXACT_SIGNATURE_NEIGHBOUR"
    assert candidate_tier(left, right, set(), set()) == "T7_REMOTE"


# --------------------------------------------------------------------------
# Exact duplicate fast path (Phase 11)
# --------------------------------------------------------------------------


def test_exact_duplicate_resolution_is_invariant_identity_only() -> None:
    resolution = resolve_exact_duplicates(ROOT)
    assert resolution["policy"] == "DETERMINISTIC_ONLY_ON_FULL_INVARIANT_IDENTITY_NEVER_FUZZY"
    assert resolution["rows_examined"] == 2001
    for group in resolution["groups"]:
        assert len(group["opportunity_ids"]) > 1
        assert group["review_method"] == "DETERMINISTIC_EXACT_INVARIANT_IDENTITY"


def test_exact_duplicate_invariants_separate_differing_rows() -> None:
    base = {
        "study_unit_id": "SU-X-1",
        "response_class": "DIAGNOSIS",
        "action_lemma": "recognize",
        "clinical_object": "sepsis",
        "key_concept_or_action": "sepsis",
        "clinical_stage": "NA",
        "population_context": "NA",
        "opportunity_fingerprint": "FP-1",
    }
    other = dict(base, opportunity_fingerprint="FP-2")
    assert exact_duplicate_invariants(base) != exact_duplicate_invariants(other)


# --------------------------------------------------------------------------
# Frozen semantic reuse
# --------------------------------------------------------------------------


def test_frozen_gold_reuse_is_verbatim_and_resolves_every_row(frozen: dict) -> None:
    assert frozen["unresolved_gold_rows"] == 0
    assert frozen["reuse_policy"].startswith("VERBATIM_LABEL_REUSE")
    assert frozen["registry_pair_count"] > 0
    for row in frozen["registry_pairs"]:
        assert row["relation"] in RELATIONS
        assert row["review_method"] == "FROZEN_DOUBLE_REVIEWED_GOLD"
        assert row["a_opportunity_id"] < row["b_opportunity_id"]


# --------------------------------------------------------------------------
# Recall audit (Phase 6)
# --------------------------------------------------------------------------


def test_candidate_retrieval_recalls_every_known_collapsing_relation() -> None:
    audit = build_candidate_recall_audit(ROOT)
    assert audit["diagnostic_only"] is True
    assert audit["semantic_labels_tuned"] is False
    assert audit["collapsing_relation_queued"]["recall"] == 1.0
    assert audit["containment_relation_retrieval"]["recall"] == 1.0
    assert audit["candidate_retrieval_sufficient"] is True


def test_candidate_retrieval_does_not_drag_in_known_unrelated_pairs() -> None:
    audit = build_candidate_recall_audit(ROOT)
    assert audit["unrelated_correctly_excluded"] == audit["unrelated_total"]


# --------------------------------------------------------------------------
# Adjudication queues (Phase 7 / Phase 8 / Phase 17)
# --------------------------------------------------------------------------


def test_registry_queue_hides_labels_quotas_and_matcher_predictions() -> None:
    queue = build_adjudication_queue(ROOT)
    assert queue["pending_semantic_reviews"] > 0
    for row in queue["pending"][:100]:
        assert row["review_fields"]["relation"] is None
        assert "matcher" not in json.dumps(row).lower()
        assert "prediction" not in json.dumps(row).lower()
        assert row["tier"] in ADJUDICATION_TIERS


def test_registry_queue_never_repeats_a_frozen_judgment() -> None:
    queue = build_adjudication_queue(ROOT)
    frozen_ids = {row["pair_id"] for row in load_frozen_gold_relations(ROOT)["registry_pairs"]}
    assert not {row["pair_id"] for row in queue["pending"]} & frozen_ids
    assert queue["already_resolved_by_frozen_gold"] == len(set(queue["reused_pair_ids"]))


def test_registry_queue_is_priority_ordered() -> None:
    queue = build_adjudication_queue(ROOT)
    order = [ADJUDICATION_TIERS.index(row["tier"]) for row in queue["pending"]]
    assert order == sorted(order)


def test_benchmark_candidate_retrieval_covers_every_benchmark_row() -> None:
    pool = mine_benchmark_candidates(ROOT)
    assert pool["benchmark_rows"] == 145
    assert pool["benchmark_rows_without_candidates"] == []
    assert pool["benchmark_rows_with_candidates"] == pool["benchmark_rows"]


def test_benchmark_queue_permits_many_to_many() -> None:
    queue = build_benchmark_adjudication_queue(ROOT)
    assert "MANY_TO_MANY_PERMITTED" in queue["queue_policy"]
    counts: dict[str, int] = {}
    for row in queue["pending"]:
        counts[row["benchmark_opportunity_id"]] = counts.get(row["benchmark_opportunity_id"], 0) + 1
    assert max(counts.values()) > 1


# --------------------------------------------------------------------------
# Deterministic atomicity screen
# --------------------------------------------------------------------------


def test_generic_category_wrapper_can_never_be_a_canonical_decision() -> None:
    from scripts.qbank.registry_v3_canonicalization import classify_atomicity_form

    verdict = classify_atomicity_form({"learner_decision": "Apply diagnosis reasoning for Sinusitis."})
    assert verdict["atomicity_form"] == "GENERIC_CATEGORY_WRAPPER"
    assert verdict["can_be_canonical_decision"] is False


def test_named_phrase_wrapper_is_not_presumed_atomic() -> None:
    from scripts.qbank.registry_v3_canonicalization import classify_atomicity_form

    verdict = classify_atomicity_form(
        {"learner_decision": "Apply antithyroid drug reasoning for Graves' Disease."}
    )
    assert verdict["atomicity_form"] == "NAMED_PHRASE_WRAPPER"
    assert verdict["can_be_canonical_decision"] is False


def test_concrete_decision_statement_is_the_only_canonical_form() -> None:
    from scripts.qbank.registry_v3_canonicalization import classify_atomicity_form

    verdict = classify_atomicity_form(
        {"learner_decision": "Select antithyroid drugs for first-line management."}
    )
    assert verdict["atomicity_form"] == "CONCRETE_DECISION_STATEMENT"
    assert verdict["can_be_canonical_decision"] is True


def test_atomicity_screen_covers_every_source_row() -> None:
    from scripts.qbank.registry_v3_canonicalization import build_atomicity_screen

    screen = build_atomicity_screen(ROOT)
    assert screen["rows_examined"] == 2001
    assert sum(screen["form_counts"].values()) == 2001


# --------------------------------------------------------------------------
# Destructive-decision safety (Phase 10)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def resolved() -> dict:
    from scripts.qbank.registry_v3_canonicalization import resolve_registry_relations

    return resolve_registry_relations(ROOT)


def test_no_destructive_relation_binds_on_a_single_review(resolved: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import DESTRUCTIVE_RELATIONS

    for row in resolved["resolved"]:
        if row["relation"] in DESTRUCTIVE_RELATIONS:
            assert row["review_method"] != "SINGLE_HIGH_SEMANTIC_ADJUDICATION"
            assert len(row["reviewer_lineage"]) >= 2


def test_second_review_packet_withholds_the_primary_label() -> None:
    from scripts.qbank.registry_v3_canonicalization import build_destructive_second_review_packet

    packet = build_destructive_second_review_packet(ROOT)
    for row in packet["packet"]:
        # the reviewer gets empty fields to fill, never a prior verdict
        assert row["review_fields"] == {"relation": None, "justification": None}
        assert set(row) == {
            "pair_id",
            "tier",
            "discipline",
            "opportunity_a",
            "opportunity_b",
            "directionality",
            "review_fields",
        }
    payload = json.dumps(packet["packet"])
    assert '"justification": null' in payload
    assert payload.count('"justification"') == len(packet["packet"])


def test_disagreements_are_third_adjudicated_not_defaulted(resolved: dict) -> None:
    assert resolved["third_adjudicated"] > 0
    third = [
        row
        for row in resolved["resolved"]
        if row["review_method"] == "THIRD_ADJUDICATOR_RESOLVED_REVIEWER_DISAGREEMENT"
    ]
    assert all(len(row["reviewer_lineage"]) == 3 for row in third)


# --------------------------------------------------------------------------
# Relation graph and canonicalization (Phase 12 / 13)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def graph() -> dict:
    from scripts.qbank.registry_v3_canonicalization import build_relation_graph

    return build_relation_graph(ROOT)


@pytest.fixture(scope="module")
def registry() -> dict:
    from scripts.qbank.registry_v3_canonicalization import build_registry_v3

    return build_registry_v3(ROOT)


def test_relation_graph_is_append_only_over_source_ids(graph: dict) -> None:
    assert graph["append_only"] is True
    assert graph["nodes"] == 2001
    for edge in graph["edge_list"]:
        assert edge["a_opportunity_id"].startswith("QOP-V2-")
        assert edge["b_opportunity_id"].startswith("QOP-V2-")
        assert edge["effect"] == RELATION_EFFECT[edge["relation"]]


def test_monotonicity_invariant_holds(graph: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import validate_monotonicity

    assert validate_monotonicity(graph, graph)["monotonicity"] == "PASS"


def test_monotonicity_invariant_detects_a_downgrade(graph: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import validate_monotonicity

    downgraded = dict(graph)
    downgraded["edge_list"] = [
        dict(edge, relation="UNRELATED") if edge["relation"] == "EQUIVALENT" else edge
        for edge in graph["edge_list"]
    ]
    assert validate_monotonicity(downgraded, graph)["monotonicity"] == "FAIL"


def test_only_duplicate_and_equivalent_collapse_rows() -> None:
    from scripts.qbank.registry_v3_canonicalization import RELATION_EFFECT

    collapsing = {r for r, e in RELATION_EFFECT.items() if e == "COLLAPSE_TO_ONE_CANONICAL_DECISION"}
    assert collapsing == {"DUPLICATE", "EQUIVALENT"}


# --------------------------------------------------------------------------
# Registry V3 (Phase 14 / 15 / 25)
# --------------------------------------------------------------------------


def test_registry_v3_validates(registry: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import validate_registry_v3

    validate_registry_v3(registry)


def test_registry_v3_ids_are_stable_and_content_derived(registry: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import canonical_opportunity_id

    for row in registry["opportunities"]:
        assert row["opportunity_id"] == canonical_opportunity_id(row["source_v2_opportunity_ids"])
        assert row["opportunity_id"] == canonical_opportunity_id(
            list(reversed(row["source_v2_opportunity_ids"]))
        )


def test_registry_v3_preserves_lineage_for_every_source_row(registry: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import build_lineage

    lineage = build_lineage(ROOT)
    assert lineage["every_v2_row_mapped"] is True
    assert len({row["source_v2_opportunity_id"] for row in lineage["lineage"]}) == 2001


def test_duplicate_and_equivalent_collapse_reduces_row_count(registry: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import build_canonical_components

    components = build_canonical_components(ROOT)
    assert registry["canonical_rows"] < registry["registry_v2_rows"]
    assert (
        components["canonical_components"] + components["source_rows_collapsed"]
        + components["source_rows_demoted_to_variant"]
        == registry["registry_v2_rows"]
    )


def test_related_but_distinct_rows_stay_separate(graph: dict, registry: dict) -> None:
    by_source = {
        source: row["opportunity_id"]
        for row in registry["opportunities"]
        for source in row["source_v2_opportunity_ids"]
    }
    for edge in graph["edge_list"]:
        if edge["relation"] in {"RELATED_BUT_DISTINCT", "UNRELATED", "NEAR_DUPLICATE"}:
            left, right = by_source.get(edge["a_opportunity_id"]), by_source.get(edge["b_opportunity_id"])
            if left and right:
                assert left != right, edge["pair_id"]


def test_containment_direction_is_recorded_both_ways(graph: dict, registry: dict) -> None:
    broader = [e for e in graph["edge_list"] if e["relation"] == "REGISTRY_BROADER_CONTAINS_BENCHMARK"]
    assert broader
    for edge in broader:
        assert edge["direction"] == "A_CONTAINS_B"
    narrower = [e for e in graph["edge_list"] if e["relation"] == "REGISTRY_NARROWER_THAN_BENCHMARK"]
    assert narrower
    for edge in narrower:
        assert edge["direction"] == "B_CONTAINS_A"


def test_unresolved_relations_fail_closed(registry: dict) -> None:
    flagged = [row for row in registry["opportunities"] if row["unresolved_relation_flags"]]
    assert flagged
    for row in flagged:
        assert row["lifecycle_state"] != "PRODUCTION_ELIGIBLE"


def test_production_eligible_rows_carry_generation_metadata(registry: dict) -> None:
    eligible = [row for row in registry["opportunities"] if row["lifecycle_state"] == "PRODUCTION_ELIGIBLE"]
    assert eligible
    for row in eligible:
        assert row["atomicity_form"] == "CONCRETE_DECISION_STATEMENT"
        for field in (
            "discipline",
            "study_unit_id",
            "clinical_topic",
            "opportunity_family",
            "response_class",
            "learner_decision",
            "supported_difficulty_levels",
            "MCC_physician_activity",
        ):
            assert row.get(field), (row["opportunity_id"], field)


# --------------------------------------------------------------------------
# Variants (Phase 16)
# --------------------------------------------------------------------------


def test_variants_never_count_toward_curriculum_coverage() -> None:
    from scripts.qbank.registry_v3_canonicalization import build_variant_registry

    variants = build_variant_registry(ROOT)
    assert variants["variants_counted_toward_coverage"] == 0
    for row in variants["variants"]:
        assert row["counts_toward_curriculum_coverage"] is False


def test_variant_sources_are_not_also_canonical_rows(registry: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import build_variant_registry

    variant_sources = {row["source_v2_opportunity_id"] for row in build_variant_registry(ROOT)["variants"]}
    canonical_sources = {
        source for row in registry["opportunities"] for source in row["source_v2_opportunity_ids"]
    }
    assert not variant_sources & canonical_sources


# --------------------------------------------------------------------------
# Benchmark mapping and coverage (Phase 17 / 18)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def coverage() -> dict:
    from scripts.qbank.registry_v3_canonicalization import build_coverage_report

    return build_coverage_report(ROOT)


def test_benchmark_mapping_is_many_to_many() -> None:
    from scripts.qbank.registry_v3_canonicalization import build_benchmark_mapping

    mapping = build_benchmark_mapping(ROOT)
    assert mapping["benchmark_rows_with_multiple_registry_matches"] > 0
    assert mapping["registry_rows_with_multiple_benchmark_matches"] > 0
    assert "NO_FORCED_ONE_TO_ONE" in mapping["cardinality_policy"]


def test_coverage_metrics_are_separated_not_collapsed(coverage: dict) -> None:
    metrics = coverage["metrics"]
    for key in (
        "atomic_equivalent_recall",
        "atomic_equivalent_precision",
        "curriculum_decision_coverage",
        "missing_benchmark_decisions",
        "registry_only_decisions",
        "atomization_deficit",
        "variant_capture",
        "duplicate_rate",
        "over_split_rate",
        "uncertain_rate",
    ):
        assert key in metrics
        assert key in coverage["definitions"] or isinstance(metrics[key], (int, float))


def test_coverage_metrics_are_internally_coherent(coverage: dict) -> None:
    metrics = coverage["metrics"]
    assert 0.0 <= metrics["curriculum_decision_coverage"] <= 1.0
    assert metrics["atomic_equivalent_recall"] <= metrics["curriculum_decision_coverage"]
    assert metrics["missing_benchmark_decisions"] <= coverage["benchmark_rows"]
    assert metrics["registry_only_decisions"] <= coverage["registry_v3_canonical_rows"]


def test_atomization_deficit_counts_heading_only_coverage(coverage: dict) -> None:
    assert coverage["metrics"]["atomization_deficit"] == len(
        coverage["atomization_deficit_benchmark_opportunity_ids"]
    )


# --------------------------------------------------------------------------
# Gap admission, review queue, pilot manifest (Phase 20 / 30 / 32)
# --------------------------------------------------------------------------


def test_only_confirmed_atomic_true_omissions_are_admitted() -> None:
    from scripts.qbank.registry_v3_canonicalization import admit_new_opportunities

    admitted = admit_new_opportunities(ROOT)
    assert admitted["admitted_count"] <= admitted["disposition_counts"]["TRUE_REGISTRY_OMISSION"]
    for row in admitted["admitted"]:
        assert row["registry_v2_miss_reason"] == "TRUE_REGISTRY_OMISSION"
        assert row["lifecycle_state"] == "NEEDS_SOURCE_RESEARCH"
        assert row["admitted_from_benchmark_opportunity_id"].startswith("NBO-")


def test_review_queue_keeps_unresolved_work_visible(registry: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import build_review_queue

    queue = build_review_queue(ROOT)
    assert queue["registry_rows_queued"] == registry["canonical_rows"] - registry["lifecycle_counts"][
        "PRODUCTION_ELIGIBLE"
    ]
    assert queue["benchmark_gaps_queued"] > 0


def test_pilot_manifest_selects_only_production_eligible_rows(registry: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import build_pilot_manifest

    manifest = build_pilot_manifest(ROOT)
    eligible = {
        row["opportunity_id"]
        for row in registry["opportunities"]
        if row["lifecycle_state"] == "PRODUCTION_ELIGIBLE"
    }
    assert 20 <= manifest["selected"] <= 50
    assert {row["opportunity_id"] for row in manifest["manifest"]} <= eligible
    assert manifest["questions_generated_in_this_milestone"] == 0


def test_pilot_manifest_is_deterministic_and_broad() -> None:
    from scripts.qbank.registry_v3_canonicalization import build_pilot_manifest

    first, second = build_pilot_manifest(ROOT), build_pilot_manifest(ROOT)
    assert first["content_sha256"] == second["content_sha256"]
    assert len(first["discipline_counts"]) == 6
    assert len(first["family_counts"]) >= 8
    assert len(first["response_class_counts"]) >= 4


# --------------------------------------------------------------------------
# Rebuild, preservation, copyright, acceptance gate
# --------------------------------------------------------------------------


def test_deterministic_rebuild_reproduces_every_on_disk_hash() -> None:
    from scripts.qbank.registry_v3_canonicalization import verify_deterministic_rebuild

    rebuild = verify_deterministic_rebuild(ROOT)
    assert rebuild["deterministic_rebuild"] == "PASS"
    assert rebuild["self_hashes_valid"] == rebuild["artifacts"]


def test_registry_v1_and_v2_are_untouched_by_v3(manifest: dict) -> None:
    from scripts.qbank.registry_v3_canonicalization import (
        BENCHMARK_PATH,
        REGISTRY_V1_PATH,
        REGISTRY_V2_PATH,
        file_sha256,
    )

    for path in (REGISTRY_V1_PATH, REGISTRY_V2_PATH, BENCHMARK_PATH):
        assert (ROOT / path).exists()
    assert file_sha256(ROOT / REGISTRY_V2_PATH) == manifest["inputs"]["registry_v2"]["file_sha256"]
    assert file_sha256(ROOT / REGISTRY_V1_PATH) == manifest["inputs"]["registry_v1"]["file_sha256"]


def test_copyright_audit_passes_and_drops_source_prose() -> None:
    from scripts.qbank.registry_v3_canonicalization import build_copyright_audit

    audit = build_copyright_audit(ROOT)
    assert audit["copyright_audit"] == "PASS"
    assert audit["source_prose_fields_carried_into_v3"] == []
    assert audit["longest_canonical_text_words"] < 80


def test_acceptance_gate_passes_every_check() -> None:
    from scripts.qbank.registry_v3_canonicalization import build_acceptance_gate

    gate = build_acceptance_gate(ROOT)
    assert gate["failed_checks"] == []
    assert gate["registry_v3_frozen_for_production_use"] is True
