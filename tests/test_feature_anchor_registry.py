"""The versioned feature/anchor registry, and the contract it reconciles.

The milestone this belongs to exists because `SAF_1` and the V2 supply layer read
two different statements of the same relation. These tests hold the repaired
contract in place: the baseline snapshot must reproduce the frozen packs exactly,
extensions must be append-only and independently approved before they are
visible, and no consumer may resolve a snapshot implicitly.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.qbank.clinical_contrast_v2 import (
    ANCHOR_CLASSES,
    CONTRAST_ROLES,
    FEATURE_STATES,
    discriminative_class,
)
from scripts.qbank.feature_anchor_registry import (
    ADMISSIBLE_REVIEW_VERDICTS,
    BASELINE_SNAPSHOT_ID,
    EXTENDED_SNAPSHOT_ID,
    EXTENSIONS_PATH,
    REGISTRY_FEATURE_STATES,
    SEED_PACK_BASES,
    SNAPSHOTS_PATH,
    FeatureAnchorRegistryError,
    anchor_feature_ids,
    anchor_relation_id,
    approved_extensions,
    build_reconciliation,
    build_snapshot,
    build_snapshot_store,
    load_extensions,
    load_snapshot,
    registry_hash,
    registry_state,
    snapshot_anchor_index,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def baseline():
    return load_snapshot(ROOT, BASELINE_SNAPSHOT_ID)


@pytest.fixture(scope="module")
def extended():
    return load_snapshot(ROOT, EXTENDED_SNAPSHOT_ID)


# ------------------------------------------------- baseline import fidelity


def _frozen_pack_anchors() -> dict[str, list[str]]:
    resolved: dict[str, list[str]] = {}
    for base in SEED_PACK_BASES:
        document = json.loads((ROOT / f"{base}.stem_anchors.json").read_text())
        for row in document["seeds"]:
            resolved[row["seed_id"]] = sorted({
                anchor["stem_feature_id"] for anchor in row["plausibility_anchors"]
            })
    return resolved


def test_baseline_snapshot_reproduces_every_frozen_anchor_row(baseline):
    """The binding regression: set equality per seed, not merely equal counts."""
    frozen = _frozen_pack_anchors()
    registry = snapshot_anchor_index(baseline)
    assert set(registry) == set(frozen)
    mismatched = {
        seed_id: (frozen[seed_id], registry[seed_id])
        for seed_id in frozen
        if frozen[seed_id] != registry[seed_id]
    }
    assert mismatched == {}


def test_baseline_keeps_the_one_deliberately_anchorless_seed(baseline):
    """R4 of the frozen derivation: a seed resting on category membership alone."""
    registry = snapshot_anchor_index(baseline)
    assert registry["SEED-PED-T03-HYPERTONIC"] == []


def test_baseline_counts(baseline):
    assert baseline["feature_count"] == 102
    assert baseline["anchor_relation_count"] == 153
    assert baseline["extension_diff"]["ANCHOR_RELATIONS_ADDED"] == 0


def test_historical_frozen_artifacts_are_untouched():
    """No pack, enrichment or anchor layer may be appended to."""
    for base in SEED_PACK_BASES:
        anchors = json.loads((ROOT / f"{base}.stem_anchors.json").read_text())
        assert anchors["frozen"] is True
        enrichment = json.loads((ROOT / f"{base}.enrichment.json").read_text())
        assert enrichment["frozen"] is True


# ------------------------------------------------------------- identity


def test_feature_ids_are_the_frozen_ids_and_are_stable(baseline):
    vocabulary = json.loads(
        (ROOT / "research/qgen/safe_yield/g2_stem_feature_vocabulary.json").read_text()
    )
    frozen = {
        feature["stem_feature_id"]
        for unit in vocabulary["anchors"]
        for feature in unit["features"]
    }
    assert {row["feature_id"] for row in baseline["features"]} == frozen
    for row in baseline["features"]:
        assert row["canonical_concept_id"] == row["feature_id"]


def test_anchor_relation_ids_are_stable_across_rebuilds():
    first = build_snapshot(ROOT, snapshot_id=BASELINE_SNAPSHOT_ID)
    second = build_snapshot(ROOT, snapshot_id=BASELINE_SNAPSHOT_ID)
    assert [row["anchor_relation_id"] for row in first["anchor_relations"]] == [
        row["anchor_relation_id"] for row in second["anchor_relations"]
    ]
    assert first["registry_hash"] == second["registry_hash"]


def test_anchor_relation_id_ignores_evidence_and_role():
    """Restating why a relation holds must not move the relation's identity."""
    identity = {
        "feature_id": "SF-P147-MODERATE-SEVERE-DISTRESS",
        "target_concept_id": "CONCEPT-X",
        "learner_decision": "QGEN-GEN-PED-T01",
        "decision_granularity": "SINGLE_DIAGNOSIS",
        "required_state": "PRESENT",
    }
    baseline_id = anchor_relation_id(identity)
    assert anchor_relation_id({
        **identity, "evidence_refs": ["CLM-A"], "declared_anchor_role": "POSITIVE_SUPPORT",
    }) == baseline_id
    assert anchor_relation_id({**identity, "learner_decision": "QGEN-GEN-PED-T02"}) != baseline_id


def test_an_anchor_relation_without_an_identity_is_refused():
    with pytest.raises(FeatureAnchorRegistryError):
        anchor_relation_id({"feature_id": "SF-X"})


def test_a_feature_is_not_an_anchor_relation(baseline):
    """Registration is not entitlement, which is the whole point of two tables."""
    registered = {row["feature_id"] for row in baseline["features"]}
    anchoring = {row["feature_id"] for row in baseline["anchor_relations"]}
    assert anchoring < registered
    assert len(registered - anchoring) == 15

    # A registered feature anchors nothing for a decision no relation names.
    assert anchor_feature_ids(
        baseline,
        target_concept_id="CONCEPT-R4-SU-OT-56-FOREIGN-BODY",
        learner_decision="QGEN-GEN-PSY-T03",
    ) == []


def test_generic_context_features_anchor_only_where_a_relation_says_so(baseline):
    """`imaging is available now` must not become a universal anchor."""
    relations = [
        row for row in baseline["anchor_relations"]
        if row["feature_id"] == "SF-GS76-IMAGING-AVAILABLE-NOW"
    ]
    # It anchors three competitors, all under the one learner decision a relation
    # was asserted for, and it reaches no other decision merely by being registered.
    assert {row["learner_decision"] for row in relations} == {"QGEN-GEN-SURG-T02"}
    # And the registry can now say what the frozen packs could not: it is a
    # SYSTEM_CONSTRAINT, so it types to RESOURCE_AVAILABILITY and carries
    # plausibility in no decision domain at all.
    for row in relations:
        assert row["non_anchor_in_decision_domains"] == [
            "EVIDENCE_INTERPRETATION", "PATIENT_CLINICAL", "POPULATION_PROGRAMME"
        ]
        assert set(row["anchor_role_by_decision_domain"].values()) == {
            "RESOURCE_AVAILABILITY"
        }


# ------------------------------------------------------- states and roles


def test_allowed_states_are_v2s_four_and_nothing_else(baseline):
    assert set(REGISTRY_FEATURE_STATES) == set(FEATURE_STATES)
    for row in baseline["features"]:
        assert row["allowed_states"] == list(REGISTRY_FEATURE_STATES)


def test_unknown_is_never_absent_at_the_registry_boundary(baseline):
    """The shared boundary this milestone creates must not collapse the two."""
    state_map = {"SF-P147-VIRAL-PRODROME": {"state": "PRESENT"}}
    assert registry_state(baseline, state_map, "SF-P147-VIRAL-PRODROME") == "PRESENT"
    assert registry_state(baseline, state_map, "SF-P147-FAILING-TO-IMPROVE") == "UNKNOWN"
    assert registry_state(baseline, state_map, "SF-P147-FAILING-TO-IMPROVE") != "ABSENT"
    assert registry_state(
        baseline, {"SF-P147-FAILING-TO-IMPROVE": {"state": "ABSENT"}},
        "SF-P147-FAILING-TO-IMPROVE",
    ) == "ABSENT"


def test_an_unregistered_feature_is_refused_rather_than_resolved(baseline):
    with pytest.raises(FeatureAnchorRegistryError):
        registry_state(baseline, {}, "SF-NOT-A-FEATURE")


def test_supported_roles_come_from_the_canonical_v2_mapping(baseline):
    for row in baseline["features"]:
        for role in row["supported_roles"].values():
            assert role in CONTRAST_ROLES


def test_the_registry_reports_untyped_anchors_without_enforcing_them(baseline):
    """Measured, not enforced: enforcing it would change historical verdicts."""
    outside = [
        row for row in baseline["anchor_relations"]
        if "PATIENT_CLINICAL" in row["non_anchor_in_decision_domains"]
    ]
    assert outside, "the diagnosed anchor-quality defect must still be visible"
    for row in outside:
        assert row["verification_status"] == "FROZEN_CANONICAL"


# ------------------------------------------------------------ extensions


def test_every_proposed_extension_is_classified_and_reviewed():
    document = load_extensions(ROOT)
    assert len(document["extensions"]) == 15
    for extension in document["extensions"]:
        assert extension["classification"] in {
            "FEATURE_ALREADY_EXISTS", "NEW_FEATURE_REQUIRED",
            "ANCHOR_RELATION_ONLY", "INVALID_EXTENSION",
        }
        assert extension["registry_review"]["verdict"] in {
            "APPROVED", "REJECTED", "UNCERTAIN"
        }


def test_only_approved_extensions_enter_the_new_snapshot(extended):
    document = load_extensions(ROOT)
    approved = {row["extension_id"] for row in approved_extensions(document)}
    assert len(approved) == 4
    assert set(extended["extension_diff"]["extension_ids"]) == approved
    assert extended["extension_diff"]["ANCHOR_RELATIONS_ADDED"] == 4
    assert extended["extension_diff"]["FEATURES_ADDED"] == 0


def test_a_rejected_extension_never_reaches_a_snapshot():
    document = load_extensions(ROOT)
    rejected = [
        row for row in document["extensions"]
        if row["registry_review"]["verdict"] == "REJECTED"
    ]
    assert len(rejected) == 11
    with pytest.raises(FeatureAnchorRegistryError):
        build_snapshot(ROOT, snapshot_id="TEST", extensions=[rejected[0]])


def test_an_uncertain_extension_fails_closed():
    """UNCERTAIN is named separately and is refused exactly as REJECTED is."""
    document = load_extensions(ROOT)
    approved = copy.deepcopy(approved_extensions(document)[0])
    approved["registry_review"]["verdict"] = "UNCERTAIN"
    assert "UNCERTAIN" not in ADMISSIBLE_REVIEW_VERDICTS
    with pytest.raises(FeatureAnchorRegistryError):
        build_snapshot(ROOT, snapshot_id="TEST", extensions=[approved])


def test_an_approved_extension_needs_evidence():
    document = load_extensions(ROOT)
    stripped = copy.deepcopy(approved_extensions(document)[0])
    stripped["evidence_refs"] = []
    with pytest.raises(FeatureAnchorRegistryError, match="model memory is not evidence"):
        build_snapshot(ROOT, snapshot_id="TEST", extensions=[stripped])


def test_an_approved_extension_must_satisfy_every_minimality_criterion():
    document = load_extensions(ROOT)
    for criterion in (
        "clinically_meaningful", "mcc_level_relevant",
        "needed_for_a_validated_contrast_relation", "not_a_duplicate", "correctly_typed",
    ):
        weakened = copy.deepcopy(approved_extensions(document)[0])
        weakened["registry_review"][criterion] = False
        with pytest.raises(FeatureAnchorRegistryError, match="minimality"):
            build_snapshot(ROOT, snapshot_id="TEST", extensions=[weakened])


def test_a_new_feature_may_not_be_approved_by_this_registry():
    """The frozen vocabulary is not grown here, and the guard is a rule not a habit."""
    document = load_extensions(ROOT)
    smuggled = copy.deepcopy(approved_extensions(document)[0])
    smuggled["classification"] = "NEW_FEATURE_REQUIRED"
    with pytest.raises(FeatureAnchorRegistryError, match="frozen"):
        build_snapshot(ROOT, snapshot_id="TEST", extensions=[smuggled])


def test_extensions_are_append_only(baseline, extended):
    """Every baseline relation survives, byte for byte, into the extended snapshot."""
    before = {row["anchor_relation_id"]: row for row in baseline["anchor_relations"]}
    after = {row["anchor_relation_id"]: row for row in extended["anchor_relations"]}
    assert set(before) < set(after)
    for relation_id, row in before.items():
        assert after[relation_id] == row
    assert extended["features"] == baseline["features"]


def test_a_duplicate_anchor_relation_is_refused_rather_than_appended():
    document = load_extensions(ROOT)
    duplicate = copy.deepcopy(approved_extensions(document)[0])
    duplicate["feature_id"] = "SF-P147-ABRUPT-ONSET-NO-PRODROME"
    duplicate["target_concept_id"] = "CONCEPT-R4-SU-OT-56-FOREIGN-BODY"
    duplicate["learner_decision"] = "QGEN-GEN-PED-T01"
    duplicate["decision_granularity"] = "SINGLE_DIAGNOSIS"
    with pytest.raises(FeatureAnchorRegistryError, match="duplicate"):
        build_snapshot(ROOT, snapshot_id="TEST", extensions=[duplicate])


def test_approved_extensions_carry_a_role_inside_the_anchor_classes(extended):
    added = {
        row["anchor_relation_id"]
        for row in extended["extension_diff"]["added_anchor_relations"]
    }
    for relation in extended["anchor_relations"]:
        if relation["anchor_relation_id"] not in added:
            continue
        role = relation["declared_anchor_role"] or relation[
            "anchor_role_by_decision_domain"
        ]["PATIENT_CLINICAL"]
        assert discriminative_class(role) in ANCHOR_CLASSES


# ------------------------------------------------------------- snapshots


def test_a_snapshot_must_be_pinned_and_there_is_no_latest():
    for pin in ("", None, "latest", "LATEST", "current", "HEAD"):
        with pytest.raises(FeatureAnchorRegistryError):
            load_snapshot(ROOT, pin)
    with pytest.raises(FeatureAnchorRegistryError):
        load_snapshot(ROOT, "FEATURE_ANCHOR_SNAPSHOT_V99")


def test_snapshot_hash_is_deterministic_and_covers_the_rows(baseline, extended):
    assert baseline["registry_hash"] == registry_hash(
        baseline["features"], baseline["anchor_relations"]
    )
    assert extended["registry_hash"] != baseline["registry_hash"]
    tampered = copy.deepcopy(baseline)
    tampered["anchor_relations"][0]["feature_id"] = "SF-P147-VIRAL-PRODROME"
    assert registry_hash(
        tampered["features"], tampered["anchor_relations"]
    ) != baseline["registry_hash"]


def test_the_tracked_snapshot_store_rebuilds_identically():
    rebuilt = build_snapshot_store(ROOT)
    tracked = json.loads((ROOT / SNAPSHOTS_PATH).read_text())
    assert rebuilt == tracked


def test_a_snapshot_records_the_inputs_it_was_built_from(baseline):
    built = baseline["built_from"]
    assert built["vocabulary_sha256"]
    assert len(built["stem_anchor_packs"]) == 3
    assert all(entry["sha256"] for entry in built["stem_anchor_packs"])


def test_the_reconciliation_report_still_names_the_defect():
    report = build_reconciliation(ROOT)
    assert report["supply_invisibility"]["APPROVED_ANCHOR_ADDITIONS"] == 4
    assert report["supply_invisibility"]["VISIBLE_TO_SAF1_TODAY"] == 0
    assert report["production_code_changed"] is False


def test_the_extensions_artifact_records_the_concept_id_mismatch_it_reconciles():
    """Three of four approved extensions carry a supply-minted concept id."""
    document = load_extensions(ROOT)
    mismatched = [
        row for row in approved_extensions(document)
        if row["concept_id_reconciliation"] == "REGISTERED_ID_DIFFERS_FROM_SUPPLY_DECLARED_ID"
    ]
    assert len(mismatched) == 3
