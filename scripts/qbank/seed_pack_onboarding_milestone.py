"""Deterministic builders and metrics for the seed-pack onboarding milestone."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .feature_anchor_registry import content_sha256


DISCIPLINES = ("MED", "OBGYN", "PED", "PHELO", "PSY", "SURG")
ROUTE_A_IDS = frozenset({"LD-C35-01", "LD-PH11-01", "LD-PH12-01", "LD-OB53-02"})


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_development_12(
    frozen: dict[str, Any], *, excluded_route_a: set[str] | frozenset[str]
) -> list[dict[str, Any]]:
    """Select the preregistered first two eligible IDs per discipline."""
    rows = frozen.get("frozen_opportunities")
    if not isinstance(rows, list):
        raise ValueError("frozen opportunity artifact carries no frozen_opportunities")
    selected: list[dict[str, Any]] = []
    for discipline in DISCIPLINES:
        eligible = sorted(
            (
                row for row in rows
                if row.get("discipline") == discipline
                and row.get("learner_decision_id") not in excluded_route_a
            ),
            key=lambda row: row["learner_decision_id"],
        )
        if len(eligible) < 2:
            raise ValueError(f"fewer than two eligible opportunities for {discipline}")
        selected.extend(eligible[:2])
    return selected


def build_development_12_document(
    *, frozen: dict[str, Any], frozen_sha256: str, stem_feature_maps_sha256: str
) -> dict[str, Any]:
    selected = select_development_12(frozen, excluded_route_a=ROUTE_A_IDS)
    document = {
        "schema_version": "1.0",
        "scope": "QGEN_SEED_PACK_ONBOARDING_DEVELOPMENT_12",
        "classification": "DEVELOPMENT_REGRESSION_SET",
        "selection_rule": (
            "Exclude the four frozen Route-A opportunities, then sort by "
            "learner_decision_id within discipline and take the first two."
        ),
        "excluded_route_a_opportunity_ids": sorted(ROUTE_A_IDS),
        "frozen_opportunities_sha256": frozen_sha256,
        "frozen_stem_feature_maps_sha256": stem_feature_maps_sha256,
        "opportunities": selected,
        "counts_by_discipline": {
            discipline: sum(row["discipline"] == discipline for row in selected)
            for discipline in DISCIPLINES
        },
        "frozen": True,
    }
    document["content_sha256"] = content_sha256(document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    frozen_path = root / "research/qgen/onboarding/v2_frozen_pilot_opportunities.json"
    maps_path = root / "research/qgen/onboarding/v2_frozen_pilot_stem_feature_maps.json"
    frozen = json.loads(frozen_path.read_text())
    document = build_development_12_document(
        frozen=frozen,
        frozen_sha256=file_sha256(frozen_path),
        stem_feature_maps_sha256=file_sha256(maps_path),
    )
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
