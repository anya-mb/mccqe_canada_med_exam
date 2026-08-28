from pathlib import Path

from qbank.allocation_discipline_routing import (
    load_allocation_discipline_routing,
    preflight_allocation_disciplines,
    validate_allocation_discipline_routing,
)
from qbank.cli import main


REPO = Path(__file__).resolve().parents[1]


def test_medical_imaging_exceptional_routing_resolves_every_eligible_address():
    routing = load_allocation_discipline_routing(REPO)
    result = validate_allocation_discipline_routing(REPO, routing)
    preflight = preflight_allocation_disciplines(REPO, routing)

    assert result.status == "PASS"
    assert result.summary == {
        "routing_candidates": 26,
        "routed_med": 18,
        "routed_surg": 8,
        "deferred_routing": 0,
        "high_confidence": 9,
        "moderate_confidence": 17,
        "low_confidence": 0,
    }
    assert preflight.total_allocation_addresses == 1507
    assert preflight.eligible_allocation_addresses == 1175
    assert preflight.suppressed_allocation_addresses == 31
    assert preflight.zero_scope_allocation_addresses == 301
    assert preflight.medical_imaging_ambiguous_addresses == 26
    assert preflight.unassigned_eligible_addresses == 0
    assert preflight.multi_assigned_eligible_addresses == 0


def test_routing_validation_command_reports_a_clean_dry_run(capsys):
    assert main(["--root", str(REPO), "validate-allocation-discipline-routing"]) == 0

    assert "ALLOCATION_DISCIPLINE_ROUTING_VALIDATION: PASS" in capsys.readouterr().out
