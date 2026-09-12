from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DISCIPLINES = ("MED", "PED", "OBGYN", "SURG", "PSY", "PHELO")


def test_operational_roster_is_balanced_distinct_fresh_and_outcome_blind():
    """Catches imbalance, topic clustering, reuse, and generation-aware selection."""
    from scripts.qbank.fresh_operational_holdout_18 import select_holdout

    roster = select_holdout(ROOT)
    rows = roster["opportunities"]

    assert len(rows) == 18
    assert Counter(row["discipline"] for row in rows) == {
        discipline: 3 for discipline in DISCIPLINES
    }
    assert len({row["study_unit_id"] for row in rows}) == 18
    families = defaultdict(set)
    for row in rows:
        families[row["discipline"]].add(row["topic_family"])
    assert all(len(families[discipline]) == 3 for discipline in DISCIPLINES)
    forbidden = {"seed", "contrast", "distractor", "stem", "yield", "accepted"}
    assert not any(
        any(token in key.lower() for token in forbidden)
        for row in rows
        for key in row
    )
    assert roster["selection_uses_generation_outcomes"] is False
    assert roster["source_inventory_path"] == (
        "research/qgen/readiness/future_untouched_holdout_eligibility.json"
    )
    assert roster["content_sha256"]


def test_architecture_freeze_pins_v6_shared_code_and_historical_holdout_files():
    """Catches a partial freeze that could miss semantic or historical drift."""
    from scripts.qbank.fresh_operational_holdout_18 import (
        build_architecture_freeze,
        select_holdout,
    )

    freeze = build_architecture_freeze(ROOT, select_holdout(ROOT))
    pins = freeze["architecture_pins"]

    assert pins["research/qgen/onboarding/feature_anchor_snapshot_v6.json"]
    assert pins["scripts/qbank/generation_lifecycle.py"]
    assert pins["scripts/qbank/profile_contrast_retrieval.py"]
    assert pins["scripts/qbank/fresh_operational_holdout_18.py"]
    assert freeze["historical_artifact_pins"]
    assert all(
        not path.startswith("research/qgen/holdout/fresh_operational_holdout_18")
        for path in freeze["historical_artifact_pins"]
    )
    assert freeze["holdout_architecture_freeze_sha256"]


def test_freeze_verifier_detects_architecture_hash_drift():
    """Catches any executable change after the holdout architecture is frozen."""
    from scripts.qbank.fresh_operational_holdout_18 import (
        HoldoutIntegrityError,
        build_architecture_freeze,
        select_holdout,
        verify_freeze,
    )

    roster = select_holdout(ROOT)
    freeze = build_architecture_freeze(ROOT, roster)
    assert verify_freeze(ROOT, roster, freeze)["verdict"] == "PASS"

    changed = deepcopy(freeze)
    changed["architecture_pins"]["scripts/qbank/generation_lifecycle.py"] = "0" * 64
    with pytest.raises(HoldoutIntegrityError, match="ARCHITECTURE_HASH_DRIFT"):
        verify_freeze(ROOT, roster, changed)


def test_freeze_verifier_detects_roster_substitution():
    """Catches post-freeze replacement of even one selected opportunity."""
    from scripts.qbank.fresh_operational_holdout_18 import (
        HoldoutIntegrityError,
        build_architecture_freeze,
        select_holdout,
        verify_freeze,
    )

    roster = select_holdout(ROOT)
    freeze = build_architecture_freeze(ROOT, roster)
    changed = deepcopy(roster)
    changed["opportunities"][0]["study_unit_id"] = "SU-TAMPERED"

    with pytest.raises(HoldoutIntegrityError, match="ROSTER_HASH_DRIFT"):
        verify_freeze(ROOT, changed, freeze)
