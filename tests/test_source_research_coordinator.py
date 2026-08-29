from copy import deepcopy
import json
from pathlib import Path

from qbank.source_research_coordinator import validate_disjoint_worker_ownership


REPO = Path(__file__).resolve().parents[1]


def _population(batch_id: str) -> dict:
    stem = batch_id.lower().replace("-", "_")
    return json.loads(
        (REPO / f"research/qgen/source_packet_population_{stem}.json").read_text(
            encoding="utf-8"
        )
    )


def test_disjoint_ownership_rejects_duplicate_pending_packet_or_integrated_batch() -> None:
    integrated = _population("SRB-001")
    duplicate = deepcopy(_population("SRB-002"))
    duplicate["source_packets"][0]["source_packet_id"] = integrated["source_packets"][0][
        "source_packet_id"
    ]

    result = validate_disjoint_worker_ownership(
        REPO, ["SRB-001", "SRB-001"], [integrated, duplicate]
    )

    assert result.status == "FAIL"
    assert any("duplicate pending batch" in error for error in result.errors)
    assert any("already integrated batch" in error for error in result.errors)
    assert any("not pairwise disjoint" in error for error in result.errors)
