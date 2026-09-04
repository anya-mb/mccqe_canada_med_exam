"""G0: replay the pre-publication admissibility stage over a frozen cohort.

This is the falsification test for the whole design. The new stage is run over a
frozen set of already-independently-reviewed items and must separate the ones the
reviewer failed from the ones the reviewer passed, using general rules only.

Nothing in this module knows an item id, a discipline's clinical content, or which
items the reviewer failed. It reads a frozen staged artifact, binds each item to
its discipline profile, adjudicates the critical facts its claims carry, and
adjudicates its option set from a role-blind label pool. The comparison with the
independent verdicts happens afterwards, in the report.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .critical_fact_adjudication import adjudicate_evidence_packet
from .errors import QbankError
from .option_set_admissibility import (
    RESPONSE_CLASS_AXES,
    adjudicate_option_set_admissibility,
    validate_role_blind_label_pool,
)
from .paths import resolve_root_path
from .qgen_profiles import load_discipline_profiles, resolve_option_set_contract


class G0ReplayError(QbankError):
    """A replay input is missing or inconsistent."""


_CLAIM_ID = re.compile(r"CLM-[A-Z0-9-]+")


def _read(root: Path, relative: str) -> dict[str, Any]:
    path = resolve_root_path(root, relative)
    if not path.is_file():
        raise G0ReplayError(f"replay input is unavailable: {relative}")
    return json.loads(path.read_text())


def _scenario_key(lead_in: str, stem: str) -> str:
    return hashlib.sha256((lead_in + "\n" + stem).encode("utf-8")).hexdigest()


def _key_grounding_feature_ids(item: dict[str, Any]) -> set[str]:
    """Feature ids the item's own frozen record shows the key's reasoning rests on.

    A stem feature that grounds the key is doing clinical work, so it cannot also
    be a clause planted only to switch a competitor off.
    """
    feature_ids = {
        feature["feature_id"]
        for feature in item.get("stem_feature_map", {}).get("features", [])
        if isinstance(feature, dict) and isinstance(feature.get("feature_id"), str)
    }
    grounded: set[str] = set()
    serialized = json.dumps(item.get("numeric_derivation_validation", {}))
    for feature_id in feature_ids:
        if f'"{feature_id}"' in serialized:
            grounded.add(feature_id)
    for feature in item.get("stem_feature_map", {}).get("features", []):
        for parent in feature.get("derived_from") or []:
            grounded.add(parent)
    return grounded


def _competitor_predicates(item: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Join each realized competitor to the stem features that defeat its condition.

    The defeating-feature list is a frozen field of the artifact under replay, not
    something this code or the profile authors, which is what makes ADM-3's input
    one the judging party did not write.
    """
    by_contrast: dict[str, list[str]] = {}
    for proof in item.get("contextual_competitor_proof", {}).get("proofs", []):
        contrast_id = proof.get("contrast_id")
        if isinstance(contrast_id, str):
            by_contrast[contrast_id] = list(proof.get("defeating_stem_feature_ids") or [])
    from .option_set_admissibility import normalize_option_text

    predicates: dict[str, list[dict[str, Any]]] = {}
    for option in item.get("assembly", {}).get("options", []):
        contrast_id = option.get("contrast_id")
        if contrast_id is None:
            continue
        normalized = normalize_option_text(option.get("text"))
        predicates[normalized] = [
            {"stem_feature_id": feature_id, "defeated": True}
            for feature_id in by_contrast.get(contrast_id, [])
        ]
    return predicates


def replay_item(
    *,
    item: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    assignment: dict[str, Any],
    label_pool: dict[str, dict[str, Any]],
    fact_records_by_profile: dict[str, dict[str, dict[str, Any]]],
    enacted_signatures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Replay one frozen item through critical-fact and option-set adjudication."""
    profile_id = assignment["discipline_profile_id"]
    profile = profiles[profile_id]
    contract = resolve_option_set_contract(
        profile, assignment["item_archetype"], assignment["option_set_archetype"]
    )

    cited = sorted(set(_CLAIM_ID.findall(json.dumps(item))))
    records = fact_records_by_profile[profile_id]
    unusable = [
        records[claim_id]
        for claim_id in cited
        if claim_id in records and not records[claim_id]["usable_in_generation"]
    ]

    admissibility = adjudicate_option_set_admissibility(
        option_set_archetype=assignment["option_set_archetype"],
        contract=contract,
        demanded_response_class=assignment["demanded_response_class"],
        options=item["assembly"]["options"],
        label_pool=label_pool,
        stem_feature_map=item.get("stem_feature_map", {}),
        competitor_condition_predicates=_competitor_predicates(item),
        key_grounding_feature_ids=sorted(_key_grounding_feature_ids(item)),
        enacted_action_signatures=[
            signature
            for signature in enacted_signatures
            if signature.get("enactor") == "PATIENT_PERFORMED"
        ],
    )

    rejected_by: list[str] = []
    if unusable:
        rejected_by.append("CRITICAL_FACT_ADJUDICATION")
    if admissibility["verdict"] != "ADMISSIBLE":
        rejected_by.extend(
            rule for rule, verdict in admissibility["rule_verdicts"].items() if verdict == "FAIL"
        )
        if admissibility["fail_closed_reason"]:
            rejected_by.append(admissibility["fail_closed_reason"])

    return {
        "item_id": item["item_id"],
        "discipline_profile_id": profile_id,
        "item_archetype": assignment["item_archetype"],
        "option_set_archetype": assignment["option_set_archetype"],
        "demanded_response_class": assignment["demanded_response_class"],
        "critical_fact_failures": [
            {
                "claim_id": record["claim_id"],
                "fact_classes": record["fact_classes"],
                "basis": record["adjudication_basis"],
                "sanity_checks": [row["check"] for row in record["sanity_findings"]],
                "fail_closed_reason": record.get("fail_closed_reason"),
            }
            for record in unusable
        ],
        "admissibility": admissibility,
        "replay_verdict": "REJECTED" if rejected_by else "ACCEPTED",
        "rejected_by": sorted(set(rejected_by)),
    }


def run_g0_replay(
    root: Path,
    *,
    staged_relative_path: str,
    evidence_relative_path: str,
    labels_relative_path: str,
    assignments_relative_path: str,
    enacted_relative_path: str,
    independent_verification_relative_path: str,
) -> dict[str, Any]:
    """Run the whole replay and compare it with the frozen independent verdicts."""
    root = Path(root).resolve()
    staged = _read(root, staged_relative_path)
    evidence = _read(root, evidence_relative_path)
    labels = validate_role_blind_label_pool(_read(root, labels_relative_path))
    assignments_doc = _read(root, assignments_relative_path)
    enacted = _read(root, enacted_relative_path)["signatures"]
    verification = _read(root, independent_verification_relative_path)

    profiles = load_discipline_profiles(root)
    fact_records_by_profile = {
        profile_id: adjudicate_evidence_packet(
            root, evidence, profile_risk_classes=profile["numeric_risk_classes"]
        )
        for profile_id, profile in profiles.items()
    }
    assignments = {
        row["scenario_sha256"]: row for row in assignments_doc["assignments"]
    }

    independent = {
        row["item_id"]: ("PASS" if not row.get("defects") else "FAIL")
        for row in verification["ordered_item_verdicts"]
    }

    results: list[dict[str, Any]] = []
    for item in staged["items"]:
        key = _scenario_key(item["assembly"]["lead_in"], item["assembly"]["stem"])
        assignment = assignments.get(key)
        if assignment is None:
            raise G0ReplayError(
                f"no demanded response class is assigned for item {item['item_id']}"
            )
        result = replay_item(
            item=item,
            profiles=profiles,
            assignment=assignment,
            label_pool=labels,
            fact_records_by_profile=fact_records_by_profile,
            enacted_signatures=enacted,
        )
        result["independent_verdict"] = independent.get(item["item_id"])
        result["agreement"] = (
            "AGREE"
            if (result["replay_verdict"] == "REJECTED") == (result["independent_verdict"] == "FAIL")
            else "DISAGREE"
        )
        results.append(result)

    failed_items = [row for row in results if row["independent_verdict"] == "FAIL"]
    passed_items = [row for row in results if row["independent_verdict"] == "PASS"]
    failed_rejected = sum(1 for row in failed_items if row["replay_verdict"] == "REJECTED")
    passed_accepted = sum(1 for row in passed_items if row["replay_verdict"] == "ACCEPTED")

    rule_verdicts: dict[str, list[str]] = {}
    for row in results:
        for rule, verdict in row["admissibility"]["rule_verdicts"].items():
            rule_verdicts.setdefault(rule, []).append(verdict)
        rule_verdicts.setdefault("CRITICAL_FACT_ADJUDICATION", []).append(
            "FAIL" if row["critical_fact_failures"] else "PASS"
        )

    return {
        "schema_version": "1.0",
        "scope": "QGEN_G0_FROZEN_REPLAY",
        "cohort": staged.get("pilot_id"),
        "items_replayed": len(results),
        "failed_items_total": len(failed_items),
        "passed_items_total": len(passed_items),
        "failed_items_rejected": failed_rejected,
        "passed_items_accepted": passed_accepted,
        "false_acceptances": sorted(
            row["item_id"]
            for row in failed_items
            if row["replay_verdict"] == "ACCEPTED"
        ),
        "false_rejections": sorted(
            row["item_id"]
            for row in passed_items
            if row["replay_verdict"] == "REJECTED"
        ),
        "rule_verdict_values": {
            rule: sorted(set(values)) for rule, values in sorted(rule_verdicts.items())
        },
        "result": "PASS"
        if failed_rejected == len(failed_items) and passed_accepted == len(passed_items)
        else "FAIL",
        "items": sorted(results, key=lambda row: row["item_id"]),
    }
