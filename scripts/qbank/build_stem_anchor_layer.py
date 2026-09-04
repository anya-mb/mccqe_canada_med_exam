"""Build the additive, frozen stem-plausibility-anchor layer over approved seeds.

The G2 root-cause diagnosis found that anchoring has a ceiling and no floor. The
only machine-readable link between a competitor and a realized stem is the seed's
correctness condition, and the only automated test over that link is the ADM-3
anti-second-key ceiling. Nothing requires a competitor to retain positive pull, so
a stem that keeps its key unique by negating every competitor is admissible by
construction.

The diagnosis also proved that the floor cannot be computed from the correctness
conditions themselves. Every competitor of accepted G2-SURG-02, G2-MED-05 and
G2-PHELO-01 has the same computed signature as every competitor of the flagship
anchorless rejection G2-MED-01: zero conditions satisfied, the rest contradicted.
A rule over `condition_predicates` therefore separates nothing, and a rule that
rejects a competitor whose conditions are all contradicted rejects all four
accepted controls. The missing datum is a second, different relation: which stem
features, when PRESENT, give a learner a positive reason to *consider* this
competitor, as opposed to the conditions under which it would be *correct*.

This module derives that relation for the already-approved seeds. It adds no
seed, changes no pack, and changes no enrichment. Derivation rules, applied
uniformly and recorded per anchor so the layer can be audited:

  R1  Every condition predicate with `required_polarity: PRESENT` is an anchor.
      If the condition holds the competitor would be correct, so a fortiori it is
      a reason to consider it. A predicate requiring ABSENT is not an anchor: an
      absence gives a candidate nothing to reason from.

  R2  A phrase in the seed's frozen `shared_features_with_key`,
      `why_plausible_for_this_decision` or `conditions_under_which_competitor_
      would_be_correct` contributes the canonical stem features it designates.
      Designation is semantic, not lexical, and one phrase may designate several
      features on the same axis.

  R3  A phrase that names only the option category, the decision point or the
      presenting complaint designates nothing. Generic topic membership is not a
      stem anchor: it is shared by the key and by every option in the set, so it
      cannot give a candidate a reason to prefer this competitor over the others.

  R4  A seed whose plausibility rests entirely on category membership carries an
      empty anchor set and is admissible against no stem. That is the intended
      fail-closed outcome, not a gap.

Anchors are stem-independent by construction: each is a property of the seed
against its target's canonical vocabulary, written without reference to any
realized stem, opportunity, item, key or option. The join to a particular stem is
done at retrieval time and only there.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import QbankError
from .paths import resolve_root_path

SCOPE = "QGEN_CONTRAST_SEED_STEM_ANCHORS"
SCHEMA_VERSION = "1.0"

VOCABULARY_RELATIVE_PATH = "research/qgen/safe_yield/g2_stem_feature_vocabulary.json"

PACK_ENRICHMENTS = (
    (
        "research/qgen/generalization/competitive_contrast_seed_pack_r4.json",
        "research/qgen/generalization/competitive_contrast_seed_pack_r4.enrichment.json",
        "research/qgen/generalization/competitive_contrast_seed_pack_r4.stem_anchors.json",
        "competitive_contrast_seed_pack_r4",
    ),
    (
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted.json",
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted.enrichment.json",
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_targeted.stem_anchors.json",
        "competitive_contrast_seed_pack_g2_targeted",
    ),
    (
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions.json",
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions.enrichment.json",
        "research/qgen/generalization/competitive_contrast_seed_pack_g2_extensions.stem_anchors.json",
        "competitive_contrast_seed_pack_g2_extensions",
    ),
)


class StemAnchorBuildError(QbankError):
    """The anchor layer cannot be derived from the frozen inputs."""


# Anchors contributed by R2 only. R1's required-PRESENT predicates are merged in
# by the builder, so a seed absent from this table carries exactly its own
# correctness conditions as anchors. `None` records a deliberate R3/R4 finding
# that the seed's prose designates no stem datum at all.
R2_ANCHORS: dict[str, dict[str, Any]] = {
    # ---------------- SU-C-21, Acute Coronary Syndrome ----------------
    "SEED-G2-MED-T01-PE": {
        "SF-C21-TROPONIN-RISE-OR-FALL": "shared_features_with_key names 'a presentation "
        "that can raise cardiac troponin', which designates the troponin datum.",
    },
    "SEED-G2-MED-T01-DISSECTION": {},
    "SEED-G2-MED-T01-PERICARDITIS": {},
    "SEED-G2-MED-T02-NITRATE": {
        "SF-C21-DIAGNOSTIC-ST-ELEVATION": "shared_features_with_key names 'an immediate "
        "bedside action in an acute infarct'; the infarct is what invites the action.",
        "SF-C21-TROPONIN-RISE-OR-FALL": "same phrase, other member of the infarct-evidence axis.",
    },
    "SEED-G2-MED-T02-DIURETIC": {
        "SF-C21-HYPOTENSION-RAISED-JVP-CLEAR-LUNGS": "why_plausible states that the raised "
        "jugular venous pressure 'is the finding that most often triggers a diuretic'.",
    },
    "SEED-G2-MED-T02-BETA-BLOCKER": {
        "SF-C21-DIAGNOSTIC-ST-ELEVATION": "shared_features_with_key names 'an early "
        "pharmacological step in the management of an acute infarct'.",
        "SF-C21-TROPONIN-RISE-OR-FALL": "same phrase, other member of the infarct-evidence axis.",
    },
    "SEED-G2-MED-T02-VASOPRESSOR": {
        "SF-C21-HYPOTENSION-RAISED-JVP-CLEAR-LUNGS": "why_plausible states 'the blood "
        "pressure here is low'; shared features name 'an action indicated for shock physiology'.",
    },
    "SEED-G2-MED-T03-PPCI-ONLY": {
        "SF-C21-DIAGNOSTIC-ST-ELEVATION": "shared_features_with_key names 'an action that "
        "treats the infarct now'; a reperfusion route is invited by the infarct itself.",
    },
    "SEED-G2-MED-T03-RESCUE-ONLY": {
        "SF-C21-DIAGNOSTIC-ST-ELEVATION": "shared_features_with_key names 'fibrinolysis given "
        "now at the referring centre'; the infarct is what makes reperfusion now the question.",
        "SF-C21-DEVICE-TIME-EXCEEDS-WINDOW": "same phrase: lysis at the referring centre is "
        "live only where device therapy is not reachable in time.",
    },
    "SEED-G2-MED-T03-DEFERRED-ANGIO": {
        "SF-C21-DIAGNOSTIC-ST-ELEVATION": "shared_features_with_key names 'fibrinolysis given now'.",
        "SF-C21-DEVICE-TIME-EXCEEDS-WINDOW": "same phrase: giving lysis now rather than "
        "transferring is designated by the geography constraint.",
    },
    "SEED-G2-MED-T04-ADMIT-NONINVASIVE": {
        "SF-C21-TROPONIN-RISE-OR-FALL": "why_plausible states 'candidates who know admission "
        "is needed often stop there'; the data that make admission needed are designated.",
        "SF-C21-DYNAMIC-ST-T-CHANGES": "same phrase, other member of the admission-indicating axis.",
        "SF-C21-NONDIAGNOSTIC-ECG": "conditions text names a 'diagnostically uncertain' "
        "presentation that non-invasive testing would settle.",
    },
    "SEED-G2-MED-T04-DISCHARGE-STRESS": {
        "SF-C21-NONDIAGNOSTIC-ECG": "why_plausible states 'her tracing has returned to normal'.",
        "SF-C21-INITIAL-TROPONIN-NOT-ELEVATED": "conditions text names a presentation "
        "'without a troponin rise and fall'.",
    },
    "SEED-G2-MED-T04-OBSERVE": {
        "SF-C21-NONDIAGNOSTIC-ECG": "why_plausible states observation is used 'where the "
        "diagnosis is uncertain'.",
        "SF-C21-SERIAL-TESTING-NOT-YET-DONE": "same phrase: deferring the decision is live "
        "while serial testing is outstanding.",
    },
    "SEED-G2-MED-T04-CLINIC": {
        "SF-C21-NONDIAGNOSTIC-ECG": "conditions text names 'a lower-risk presentation being "
        "worked up as an outpatient'.",
        "SF-C21-INITIAL-TROPONIN-NOT-ELEVATED": "same phrase, other member of the low-risk axis.",
    },
    # ---------------- SU-GS-76, Appendicitis ----------------
    "SEED-SURG-T01-PID": {
        "SF-GS76-FEMALE-REPRODUCTIVE-AGE": "shared_features_with_key names 'acute lower "
        "abdominal pain in a woman of reproductive age'.",
    },
    "SEED-SURG-T01-TORSION": {
        "SF-GS76-FEMALE-REPRODUCTIVE-AGE": "shared_features_with_key names 'a surgical "
        "emergency in a young woman'.",
    },
    "SEED-SURG-T01-TOA": {
        "SF-GS76-FEMALE-REPRODUCTIVE-AGE": "shared_features_with_key names 'fever with "
        "unilateral lower abdominal pain in a woman of reproductive age'.",
    },
    "SEED-SURG-T02-US": {
        "SF-GS76-INTERMEDIATE-CLINICAL-SUSPICION": "shared_features_with_key names imaging "
        "'to settle an intermediate suspicion'.",
        "SF-GS76-IMAGING-AVAILABLE-NOW": "why_plausible states the modality 'is widely available'.",
    },
    "SEED-SURG-T02-MRI": {
        "SF-GS76-INTERMEDIATE-CLINICAL-SUSPICION": "the seed offers a modality for the same "
        "imaging decision, which an intermediate suspicion is what opens.",
        "SF-GS76-IMAGING-AVAILABLE-NOW": "shared_features_with_key names 'cross-sectional "
        "imaging'; a modality is a live choice where cross-sectional imaging is available.",
    },
    "SEED-SURG-T02-KUB": {
        "SF-GS76-IMAGING-AVAILABLE-NOW": "shared_features_with_key names 'an initial imaging "
        "pathway for acute right-sided abdominal pain'.",
    },
    "SEED-SURG-T02-LAPAROSCOPY": {},
    "SEED-SURG-T02-OBSERVE": {
        "SF-GS76-INTERMEDIATE-CLINICAL-SUSPICION": "why_plausible states the algorithm 'ends "
        "in admission and observation for intermediate or low suspicion'.",
    },
    "SEED-SURG-T03-NONOP": {},
    "SEED-SURG-T03-DRAINAGE": {},
    "SEED-SURG-T03-INTERVAL": {},
    # ---------------- SU-OB-54, Mastitis ----------------
    "SEED-OB-T01-DUCTAL": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'a tender "
        "indurated breast segment' with 'mild overlying erythema'.",
    },
    "SEED-OB-T01-ENGORGEMENT": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'a painful "
        "swollen breast' with 'overlying erythema'.",
        "SF-OB54-SYSTEMIC-ILLNESS": "why_plausible states 'postpartum hot flashes can be "
        "mistaken for fever'.",
    },
    "SEED-OB-T01-ABSCESS": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'progressive "
        "induration and erythema of one breast segment'.",
        "SF-OB54-SYSTEMIC-ILLNESS": "shared_features_with_key names 'systemic illness'.",
    },
    "SEED-OB-T01-PHLEGMON": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'a firm "
        "tender mass-like region of an inflamed lactating breast'.",
    },
    "SEED-OB-T01-GALACTOCELE": {
        "SF-OB54-FIRM-MASS-WITHOUT-FLUCTUANCE": "shared_features_with_key names 'a firm mass "
        "in a lactating breast'.",
    },
    "SEED-OB-T01-SUBACUTE": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'breast pain "
        "with induration in a lactating patient'.",
    },
    "SEED-OB-T01-IBC": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'a red, "
        "swollen, firm breast'.",
    },
    "SEED-OB-T02-MILK-CULTURE": {},
    "SEED-OB-T02-MAMMOGRAPHY": {
        "SF-OB54-FIRM-MASS-WITHOUT-FLUCTUANCE": "shared_features_with_key names 'imaging of a "
        "persistent breast mass'.",
    },
    "SEED-OB-T02-CRP": {
        "SF-OB54-NO-IMPROVEMENT-AFTER-48H": "shared_features_with_key names 'a test ordered to "
        "decide whether the process is still active'; failure to settle is what raises it.",
    },
    "SEED-OB-T02-ASPIRATION": {
        "SF-OB54-FIRM-MASS-WITHOUT-FLUCTUANCE": "shared_features_with_key names 'a step taken "
        "on the same persistent mass'.",
        "SF-OB54-PERSISTENT-MASS-AFTER-INFLAMMATION-RESOLVED": "same phrase, other member of "
        "the persistent-mass axis.",
    },
    "SEED-OB-T03-EMPTY": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'removal of "
        "milk from an inflamed breast'.",
        "SF-OB54-HYPERLACTATION": "conditions text names overfeeding that 'perpetuates "
        "hyperlactation' as what the instruction acts on.",
    },
    "SEED-OB-T03-MASSAGE": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'a manual "
        "technique applied to the inflamed segment'.",
    },
    "SEED-OB-T03-DISCARD": {},
    "SEED-OB-T03-DANGLE": {
        "SF-OB54-UNILATERAL-SEGMENTAL-ERYTHEMA": "shared_features_with_key names 'an "
        "instruction addressed at the inflamed segment'.",
    },
    "SEED-OB-T03-SHIELD": {
        "SF-OB54-NEEDLE-LIKE-BURNING-PAIN-BLEBS": "why_plausible states 'pain with latch is "
        "part of this presentation'.",
    },
    # ---------------- SU-P-147, Bronchiolitis ----------------
    "SEED-PED-T01-PNEUMONIA": {},
    "SEED-PED-T01-ASTHMA": {},
    "SEED-PED-T01-FOREIGN-BODY": {},
    "SEED-PED-T02-CONTINUOUS": {
        "SF-P147-HYPOXEMIA": "why_plausible names 'the option a clinician worried about silent "
        "desaturation reaches for'.",
    },
    "SEED-PED-T02-CXR": {
        "SF-P147-FOCAL-ASYMMETRIC-FINDINGS": "conditions text names a film ordered 'where the "
        "diagnosis is unclear', which the focal-findings datum is.",
    },
    "SEED-PED-T02-VIRAL": {},
    "SEED-PED-T02-CBC": {},
    "SEED-PED-T03-HFNC": {
        "SF-P147-HYPOXEMIA": "shared_features_with_key names 'an intervention aimed directly "
        "at the saturation'.",
    },
    "SEED-PED-T03-EPINEPHRINE": {},
    "SEED-PED-T03-SUCTION": {},
    "SEED-PED-T03-FLUIDS": {
        "SF-P147-MODERATE-SEVERE-DISTRESS": "why_plausible states 'a tachypneic infant is "
        "exactly the one for whom this is considered'.",
    },
    "SEED-PED-T03-HYPERTONIC": None,
    "SEED-PED-T03-SALBUTAMOL": {
        "SF-P147-FIRST-WHEEZE": "why_plausible states 'Wheeze invites a bronchodilator'.",
    },
    # ---------------- SU-PH-07, Screening ----------------
    "SEED-PHELO-T01-LENGTH": {
        "SF-PH07-SURVIVAL-LONGER-IN-SCREENED": "shared_features_with_key names 'longer "
        "measured survival in screen-detected cases without a treatment effect'.",
        "SF-PH07-MORTALITY-UNCHANGED": "same phrase: 'without a treatment effect'.",
    },
    "SEED-PHELO-T01-OVERDIAGNOSIS": {
        "SF-PH07-SURVIVAL-LONGER-IN-SCREENED": "shared_features_with_key names 'an apparent "
        "survival benefit produced by the act of screening rather than by treatment'.",
        "SF-PH07-MORTALITY-UNCHANGED": "same phrase: 'rather than by treatment'.",
    },
    "SEED-PHELO-T01-HEALTHY-SCREENEE": {
        "SF-PH07-SURVIVAL-LONGER-IN-SCREENED": "shared_features_with_key names 'a comparison "
        "that makes screening look better than it is'.",
    },
    "SEED-G2-PHELO-T01-LEAD-TIME": {
        "SF-PH07-MORTALITY-UNCHANGED": "shared_features_with_key names 'an explanation that "
        "makes screening look more effective than it is'.",
    },
    "SEED-PHELO-T02-AUTHORITY": {},
    "SEED-PHELO-T02-REMINDER": {},
    "SEED-PHELO-T02-DETECTION-COUNT": {
        "SF-PH07-LETTER-STATES-RELATIVE-BENEFIT-ONLY": "why_plausible names 'the edit most "
        "likely to be proposed by someone who has been told to add numbers'.",
    },
    "SEED-PHELO-T02-SENSITIVITY": {
        "SF-PH07-AUTONOMY-IS-THE-STATED-OBJECTIVE": "shared_features_with_key names 'an edit "
        "framed as disclosure', which is the autonomy objective.",
    },
    "SEED-G2-PHELO-T02-VOLUNTARY": {
        "SF-PH07-AUTONOMY-IS-THE-STATED-OBJECTIVE": "shared_features_with_key names 'an edit "
        "whose declared purpose is to protect the autonomy of the reader'.",
    },
    "SEED-PHELO-T03-PILOT": {
        "SF-PH07-CONFIRMATORY-CAPACITY-ABSENT": "shared_features_with_key names 'a plan that "
        "takes the capacity constraint seriously'.",
    },
    "SEED-PHELO-T03-RAISE-CUTOFF": {
        "SF-PH07-CONFIRMATORY-CAPACITY-ABSENT": "shared_features_with_key names 'a programme "
        "decision that changes how many people enter the confirmatory pathway'.",
    },
    "SEED-PHELO-T03-EVALUATE": {},
    "SEED-PHELO-T03-ECONOMIC": {
        "SF-PH07-CONSTRAINT-IS-COST-OR-LOGISTICS": "why_plausible states 'the cost of "
        "screening a whole population is stated to be considerable'.",
    },
    # ---------------- SU-PS-12, Depressive Disorders ----------------
    "SEED-PSY-T01-PDD": {},
    "SEED-PSY-T01-BD2": {
        "SF-PS12-INTEREPISODE-RECOVERY": "shared_features_with_key names 'recurrent "
        "depressive episodes with interepisode function'.",
    },
    "SEED-PSY-T01-MEDICAL": {},
    "SEED-PSY-T01-ANEMIA": {},
    "SEED-PSY-T02-SAFETY-PLAN": {
        "SF-PS12-HIGH-IMMINENT-SUICIDE-RISK": "shared_features_with_key names 'an action "
        "taken to reduce imminent suicide risk'.",
    },
    "SEED-PSY-T02-RISK-SCALE": {
        "SF-PS12-HIGH-IMMINENT-SUICIDE-RISK": "shared_features_with_key names 'a step taken "
        "to settle the disposition of an at-risk patient'.",
    },
    "SEED-PSY-T02-START-MED": {},
    "SEED-G2-PSY-T02-CRISIS-TEAM": {
        "SF-PS12-HIGH-IMMINENT-SUICIDE-RISK": "shared_features_with_key names 'an intensive "
        "intervention chosen to keep the patient safe' including 'removing lethal means'.",
    },
    "SEED-PSY-T03-PSYCHOTHERAPY": {
        "SF-PS12-MODERATE-SEVERITY": "shared_features_with_key names 'a first-line acute "
        "treatment for the same moderate episode'.",
    },
    "SEED-PSY-T03-COMBINED": {},
    "SEED-PSY-T03-EXERCISE": {
        "SF-PS12-MODERATE-SEVERITY": "conditions text names it 'a second-line adjunct at "
        "moderate severity'.",
    },
    "SEED-PSY-T03-DIGITAL": {},
    "SEED-G2-PSY-T03-ECT": {
        "SF-PS12-SEVERE-WITHOUT-PSYCHOSIS": "shared_features_with_key names 'a first-choice "
        "acute treatment named in the same guideline for severe illness'.",
        "SF-PS12-PSYCHOTIC-FEATURES": "why_plausible states 'psychotic features sit at that end'.",
    },
    "SEED-G2-PSY-T03-AD-ALONE": {
        "SF-PS12-MODERATE-SEVERITY": "why_plausible names 'the default initial treatment for "
        "a depressive episode', which is the severity band at which medication is offered.",
        "SF-PS12-SEVERE-WITHOUT-PSYCHOSIS": "same phrase, other member of the severity axis "
        "at which an antidepressant is a live initial plan.",
    },
}


def _read(root: Path, relative: str) -> dict[str, Any]:
    return json.loads(resolve_root_path(root, relative).read_text())


def _vocabulary(root: Path) -> dict[str, set[str]]:
    document = _read(root, VOCABULARY_RELATIVE_PATH)
    return {
        anchor["anchor_study_unit_id"]: {
            feature["stem_feature_id"] for feature in anchor["features"]
        }
        for anchor in document["anchors"]
    }


def derive_pack_anchors(
    pack: dict[str, Any], enrichment: dict[str, Any], vocabulary: dict[str, set[str]]
) -> list[dict[str, Any]]:
    """Derive the anchor rows for one pack, in seed-id order."""
    predicates = {
        seed["seed_id"]: seed.get("condition_predicates", [])
        for seed in enrichment["seeds"]
    }
    rows: list[dict[str, Any]] = []
    for target in pack.get("targets", []):
        unit = target["anchor_study_unit_id"]
        allowed = vocabulary.get(unit)
        if allowed is None:
            raise StemAnchorBuildError(f"no canonical vocabulary for anchor unit {unit}")
        for seed in target.get("seeds", []):
            seed_id = seed["seed_id"]
            if seed_id not in predicates:
                continue  # a seed the independent reviewer rejected; unreachable by design
            if seed_id not in R2_ANCHORS:
                raise StemAnchorBuildError(f"seed {seed_id} has no recorded R2 derivation")
            anchors: dict[str, dict[str, str]] = {}
            for predicate in predicates[seed_id]:
                if predicate["required_polarity"] != "PRESENT":
                    continue
                anchors[predicate["stem_feature_id"]] = {
                    "stem_feature_id": predicate["stem_feature_id"],
                    "rule": "R1",
                    "derivation": "a correctness condition requiring this feature PRESENT.",
                }
            contributed = R2_ANCHORS[seed_id]
            for feature_id, derivation in sorted((contributed or {}).items()):
                if feature_id not in allowed:
                    raise StemAnchorBuildError(
                        f"seed {seed_id} anchors {feature_id}, which is not in the "
                        f"canonical vocabulary of {unit}"
                    )
                if feature_id in anchors:
                    continue
                anchors[feature_id] = {
                    "stem_feature_id": feature_id,
                    "rule": "R2",
                    "derivation": derivation,
                }
            for feature_id in anchors:
                if feature_id not in allowed:
                    raise StemAnchorBuildError(
                        f"seed {seed_id} anchors {feature_id}, outside {unit}"
                    )
            rows.append({
                "seed_id": seed_id,
                "anchor_study_unit_id": unit,
                "target_id": target["target_id"],
                "plausibility_anchors": [anchors[key] for key in sorted(anchors)],
                "no_anchor_finding": (
                    "R4: the seed's frozen prose designates no stem datum, so its "
                    "plausibility rests on category membership alone."
                    if contributed is None and not anchors
                    else None
                ),
            })
    return sorted(rows, key=lambda row: row["seed_id"])


def anchor_document_sha256(rows: list[dict[str, Any]]) -> str:
    """Hash the derived rows so the layer can be proved untouched."""
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_stem_anchor_layer(root: Path) -> list[dict[str, Any]]:
    """Write one frozen anchor artifact per seed pack and return their summaries."""
    root = Path(root).resolve()
    vocabulary = _vocabulary(root)
    written: list[dict[str, Any]] = []
    for pack_relative, enrichment_relative, output_relative, pack_id in PACK_ENRICHMENTS:
        pack = _read(root, pack_relative)
        enrichment = _read(root, enrichment_relative)
        rows = derive_pack_anchors(pack, enrichment, vocabulary)
        document = {
            "anchors_pack_id": f"{pack_id}_stem_anchors",
            "anchors_for_pack_id": pack_id,
            "authorship": (
                "Derived from each seed's own frozen shared_features_with_key, "
                "why_plausible_for_this_decision and correctness-condition text, joined to "
                "the frozen canonical stem-feature vocabulary of its target's anchor study "
                "unit. Anchors are stem-independent: no opportunity, scenario, stem, "
                "lead-in, key, option or G2 verdict is referenced by any derivation. The "
                "seed pack and its enrichment are unchanged."
            ),
            "derivation_rules": {
                "R1": "every correctness condition requiring a feature PRESENT is an anchor.",
                "R2": "a phrase in the seed's frozen prose contributes the canonical stem "
                "features it designates.",
                "R3": "a phrase naming only the option category, the decision point or the "
                "presenting complaint designates nothing.",
                "R4": "a seed whose plausibility rests entirely on category membership "
                "carries an empty anchor set and is admissible against no stem.",
            },
            "enriches_enrichment_relative_path": enrichment_relative,
            "frozen": True,
            "frozen_sha256": anchor_document_sha256(rows),
            "schema_version": SCHEMA_VERSION,
            "scope": SCOPE,
            "seeds": rows,
        }
        path = resolve_root_path(root, output_relative)
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
        written.append({
            "path": output_relative,
            "seeds": len(rows),
            "seeds_with_no_anchor": sum(
                1 for row in rows if not row["plausibility_anchors"]
            ),
            "frozen_sha256": document["frozen_sha256"],
        })
    return written


if __name__ == "__main__":  # pragma: no cover - operator entry point
    import sys

    for summary in build_stem_anchor_layer(Path(sys.argv[1] if len(sys.argv) > 1 else ".")):
        print(json.dumps(summary))
