from copy import deepcopy
import hashlib
import json
from pathlib import Path

from qbank.source_packet_population import (
    build_source_packet_population_audit,
    build_source_packet_research_progress,
    validate_source_packet_population,
    validate_source_packet_research_wave,
)
from qbank.cli import _parser, main


REPO = Path(__file__).resolve().parents[1]


def _ready_population() -> dict:
    plan_path = REPO / "research/qgen/source_packet_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    batch = next(
        item for item in plan["research_batches"]
        if item["research_batch_id"] == "SRB-089"
    )
    packets_by_id = {
        packet["source_packet_id"]: packet for packet in plan["source_packets"]
    }
    populated_packets = []
    for index, packet_id in enumerate(batch["source_packet_ids"], start=1):
        packet = deepcopy(packets_by_id[packet_id])
        sources = []
        citations = []
        for family_index, source_family in enumerate(
            packet["source_family_targets"], start=1
        ):
            source_id = f"AUTH-SRB-089-{index:02d}-{family_index:02d}"
            citations.append(
                {"source_id": source_id, "locator": "Recommendation section"}
            )
            sources.append({
                "source_id": source_id,
                "title": f"Authoritative guidance {index}.{family_index}",
                "issuing_organization": "Canadian Authority",
                "source_family": source_family,
                "source_type": "CANADIAN_SPECIALTY_SOCIETY_GUIDANCE",
                "publication_date": "2025-01-01",
                "update_date": None,
                "guideline_version": "Version 1",
                "date_status": "AVAILABLE",
                "version_status": "AVAILABLE",
                "url": f"https://example.ca/guidance-{index}-{family_index}",
                "retrieval_date": "2026-08-28",
                "jurisdiction": "CANADA_NATIONAL",
                "is_canadian": True,
                "international_fallback": False,
                "currentness_status": "CURRENT",
                "currentness_notes": "Official issuer page checked for supersession.",
            })
        packet.update({
            "status": "SOURCE_PACKET_READY",
            "authoritative_sources": sources,
            "source_dates": ["2025-01-01"],
            "retrieval_dates": ["2026-08-28"],
            "guideline_versions": ["Version 1"],
            "supported_recommendations": [{
                "recommendation_id": f"{packet_id}-REC-01",
                "statement": "A concise recommendation required by this packet.",
                "evidence_requirement_types": packet["evidence_requirement_types"],
                "source_citations": citations,
                "intended_uses": packet["claim_traceability_contract"],
            }],
            "important_contraindications_or_exceptions": [],
            "disagreements_or_ambiguities": [],
            "source_citations": citations,
            "evidence_boundaries": [{
                "boundary_id": f"{packet_id}-BOUNDARY-01",
                "statement": "A cited boundary for later distractor explanations.",
                "source_citations": citations,
            }],
            "evidence_notes": ["Evidence was limited to the canonical requirement."],
            "international_fallbacks": [],
            "canadian_guidance_not_found": False,
            "disagreement_present": False,
            "unresolved_evidence_conflict": False,
            "jurisdiction_resolved": True,
            "verification_status": "VERIFIED_COMPLETE",
        })
        populated_packets.append(packet)
    return {
        "schema_version": "1.0",
        "scope": "MCCQE_CURRENT_CANADIAN_SOURCE_PACKET_PILOT",
        "plan_artifact": "research/qgen/source_packet_plan.json",
        "source_packet_plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "pilot_research_batch_id": "SRB-089",
        "population_date": "2026-08-28",
        "source_packets": populated_packets,
    }


def test_ready_pilot_is_plan_bound_and_audits_complete_evidence() -> None:
    population = _ready_population()
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "PASS"
    assert audit == {
        "schema_version": "1.0",
        "scope": "SOURCE_PACKET_PILOT_AUDIT",
        "PILOT_RESEARCH_BATCH_ID": "SRB-089",
        "PILOT_PACKETS_TOTAL": 10,
        "PILOT_PACKETS_READY": 10,
        "PILOT_PACKETS_BLOCKED": 0,
        "PILOT_PACKETS_INCOMPLETE": 0,
        "AUTHORITATIVE_SOURCES_TOTAL": 11,
        "CANADIAN_AUTHORITATIVE_SOURCES": 11,
        "INTERNATIONAL_FALLBACK_SOURCES": 0,
        "PACKETS_WITH_SOURCE_DISAGREEMENT": 0,
        "PACKETS_WITH_UNRESOLVED_CONFLICT": 0,
        "PACKETS_WITH_JURISDICTION_BLOCKER": 0,
        "EVIDENCE_REQUIREMENTS_TOTAL": 10,
        "EVIDENCE_REQUIREMENTS_SUPPORTED": 10,
        "UNSUPPORTED_EVIDENCE_REQUIREMENTS": 0,
        "NON_PILOT_PACKETS_CHANGED": 0,
    }


def test_validator_rejects_a_changed_canonical_demand_field() -> None:
    population = _ready_population()
    population["source_packets"][0]["covered_generation_job_ids"] = [
        "QGEN-OBGYN-001"
    ]
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("canonical planning field changed" in error for error in result.errors)


def test_ready_packet_requires_complete_source_identity_and_currentness_metadata() -> None:
    population = _ready_population()
    source = population["source_packets"][0]["authoritative_sources"][0]
    source["issuing_organization"] = ""
    source["currentness_notes"] = ""
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("source metadata is incomplete" in error for error in result.errors)


def test_ready_packet_rejects_uncited_claims_and_unknown_source_links() -> None:
    population = _ready_population()
    packet = population["source_packets"][0]
    packet["supported_recommendations"][0]["source_citations"] = []
    packet["evidence_boundaries"][0]["source_citations"][0]["source_id"] = (
        "UNKNOWN-SOURCE"
    )
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("important recommendation is uncited" in error for error in result.errors)
    assert any("citation references unknown source" in error for error in result.errors)


def test_ready_packet_requires_every_canonical_source_family_or_documented_fallback() -> None:
    population = _ready_population()
    packet = next(
        item for item in population["source_packets"]
        if item["source_packet_id"] == "SRC-OBGYN-074"
    )
    packet["authoritative_sources"] = packet["authoritative_sources"][:1]
    retained_source_id = packet["authoritative_sources"][0]["source_id"]
    for record in (
        packet["supported_recommendations"]
        + packet["evidence_boundaries"]
    ):
        record["source_citations"] = [
            citation for citation in record["source_citations"]
            if citation["source_id"] == retained_source_id
        ]
    packet["source_citations"] = [
        citation for citation in packet["source_citations"]
        if citation["source_id"] == retained_source_id
    ]
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("canonical source-family target is unsupported" in error for error in result.errors)


def test_documented_higher_priority_canadian_alternative_can_cover_family_target() -> None:
    population = _ready_population()
    packet = population["source_packets"][0]
    source = packet["authoritative_sources"][0]
    source["source_family"] = "PUBLIC_HEALTH_AGENCY_OF_CANADA"
    source["source_type"] = "CANADIAN_NATIONAL_GUIDELINE"
    packet["source_family_target_assessments"] = [{
        "source_family_target": packet["source_family_targets"][0],
        "status": "CANADIAN_ALTERNATIVE_USED",
        "source_ids": [source["source_id"]],
        "rationale": (
            "The current national guideline directly addresses the canonical evidence "
            "requirement; no current SOGC document with equivalent scope was found."
        ),
    }]
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "PASS"


def test_international_source_requires_explicit_canadian_gap_and_fallback_record() -> None:
    population = _ready_population()
    packet = population["source_packets"][0]
    source = packet["authoritative_sources"][0]
    source["source_family"] = "INTERNATIONAL_SPECIALTY_GUIDELINE"
    source["is_canadian"] = False
    source["international_fallback"] = True
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("international fallback is not documented" in error for error in result.errors)


def test_validator_rejects_unknown_population_status() -> None:
    population = _ready_population()
    population["source_packets"][0]["status"] = "RESEARCH_DONE"
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("population status is invalid" in error for error in result.errors)


def test_evidence_conflict_block_requires_an_explicit_unresolved_disagreement() -> None:
    population = _ready_population()
    packet = population["source_packets"][0]
    packet["status"] = "BLOCKED_EVIDENCE_CONFLICT"
    packet["verification_status"] = "BLOCKED_EVIDENCE_CONFLICT"
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("conflict block lacks unresolved disagreement" in error for error in result.errors)


def test_explicit_evidence_conflict_block_is_valid_and_audited() -> None:
    population = _ready_population()
    packet = population["source_packets"][0]
    packet.update({
        "status": "BLOCKED_EVIDENCE_CONFLICT",
        "verification_status": "BLOCKED_EVIDENCE_CONFLICT",
        "disagreement_present": True,
        "unresolved_evidence_conflict": True,
        "disagreements_or_ambiguities": [{
            "disagreement_id": "SRC-OBGYN-071-DIS-01",
            "summary": "Two authoritative recommendations materially differ.",
            "source_ids": [source["source_id"] for source in packet["authoritative_sources"]],
            "resolution_status": "UNRESOLVED",
            "canadian_mccqe_applicability": "Cannot be adjudicated safely.",
        }],
    })
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "PASS"
    assert audit["PILOT_PACKETS_READY"] == 9
    assert audit["PILOT_PACKETS_BLOCKED"] == 1
    assert audit["PACKETS_WITH_SOURCE_DISAGREEMENT"] == 1
    assert audit["PACKETS_WITH_UNRESOLVED_CONFLICT"] == 1


def test_disagreement_requires_known_source_links_and_consistent_resolution() -> None:
    population = _ready_population()
    packet = population["source_packets"][0]
    packet.update({
        "disagreement_present": True,
        "unresolved_evidence_conflict": False,
        "disagreements_or_ambiguities": [{
            "disagreement_id": "SRC-OBGYN-071-DIS-01",
            "summary": "Two recommendations differ.",
            "source_ids": ["UNKNOWN-SOURCE"],
            "resolution_status": "UNRESOLVED",
            "canadian_mccqe_applicability": "The conflict remains unresolved.",
        }],
    })
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("disagreement source linkage is invalid" in error for error in result.errors)
    assert any("disagreement resolution state is inconsistent" in error for error in result.errors)


def test_jurisdiction_block_is_rejected_when_canonical_packet_is_resolved() -> None:
    population = _ready_population()
    packet = population["source_packets"][0]
    packet.update({
        "status": "BLOCKED_JURISDICTION",
        "verification_status": "BLOCKED_JURISDICTION",
        "jurisdiction_resolved": False,
    })
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("canonical packet does not require jurisdiction resolution" in error for error in result.errors)


def test_populated_exception_must_have_claim_level_citation() -> None:
    population = _ready_population()
    population["source_packets"][0]["important_contraindications_or_exceptions"] = [{
        "exception_id": "SRC-OBGYN-071-EX-01",
        "statement": "An important threshold or contraindication.",
        "source_citations": [],
    }]
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("important exception is uncited" in error for error in result.errors)


def test_ready_packet_source_date_version_and_retrieval_rollups_must_match_sources() -> None:
    population = _ready_population()
    population["source_packets"][0]["retrieval_dates"] = []
    audit = build_source_packet_population_audit(REPO, population)

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "FAIL"
    assert any("source metadata rollups are incomplete" in error for error in result.errors)


def test_cli_exposes_pilot_population_validator() -> None:
    args = _parser().parse_args(["validate-source-packet-pilot"])

    assert args.command == "validate-source-packet-pilot"


def test_cli_exposes_current_research_wave_validator() -> None:
    args = _parser().parse_args(["validate-source-packet-wave", "SRB-001"])

    assert args.command == "validate-source-packet-wave"
    assert args.research_batch_id == "SRB-001"


def test_cli_reconciles_all_preceding_waves_for_a_later_wave(
    capsys: object,
) -> None:
    """A later wave must be validated against every prior population artifact."""
    result = main(["validate-source-packet-wave", "SRB-002"])

    captured = capsys.readouterr()

    assert result == 0
    assert "SOURCE_PACKET_WAVE_VALIDATION: PASS" in captured.out


def test_committed_srb_089_population_and_audit_validate() -> None:
    population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_089.json").read_text(
            encoding="utf-8"
        )
    )
    audit = json.loads(
        (REPO / "reports/source_packet_pilot_srb_089_audit.json").read_text(
            encoding="utf-8"
        )
    )

    result = validate_source_packet_population(REPO, population, audit)

    assert result.status == "PASS"
    assert audit["NON_PILOT_PACKETS_CHANGED"] == 0
    assert audit["UNSUPPORTED_EVIDENCE_REQUIREMENTS"] == 0


def test_committed_wave_is_plan_bound_and_progress_is_derived() -> None:
    pilot_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_089.json").read_text(
            encoding="utf-8"
        )
    )
    wave_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_001.json").read_text(
            encoding="utf-8"
        )
    )
    wave_audit = json.loads(
        (REPO / "reports/source_packet_wave_srb_001_audit.json").read_text(
            encoding="utf-8"
        )
    )
    latest_wave_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_002.json").read_text(
            encoding="utf-8"
        )
    )
    latest_wave_audit = json.loads(
        (REPO / "reports/source_packet_wave_srb_002_audit.json").read_text(
            encoding="utf-8"
        )
    )
    newest_wave_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_003.json").read_text(
            encoding="utf-8"
        )
    )
    newest_wave_audit = json.loads(
        (REPO / "reports/source_packet_wave_srb_003_audit.json").read_text(
            encoding="utf-8"
        )
    )
    fourth_wave_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_004.json").read_text(
            encoding="utf-8"
        )
    )
    fourth_wave_audit = json.loads(
        (REPO / "reports/source_packet_wave_srb_004_audit.json").read_text(
            encoding="utf-8"
        )
    )
    next_wave_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_005.json").read_text(
            encoding="utf-8"
        )
    )
    next_wave_audit = json.loads(
        (REPO / "reports/source_packet_wave_srb_005_audit.json").read_text(
            encoding="utf-8"
        )
    )
    sixth_wave_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_006.json").read_text(
            encoding="utf-8"
        )
    )
    sixth_wave_audit = json.loads(
        (REPO / "reports/source_packet_wave_srb_006_audit.json").read_text(
            encoding="utf-8"
        )
    )
    seventh_wave_population = json.loads(
        (REPO / "research/qgen/source_packet_population_srb_007.json").read_text(
            encoding="utf-8"
        )
    )
    seventh_wave_audit = json.loads(
        (REPO / "reports/source_packet_wave_srb_007_audit.json").read_text(
            encoding="utf-8"
        )
    )

    result = validate_source_packet_research_wave(
        REPO, wave_population, [pilot_population], wave_audit
    )
    latest_result = validate_source_packet_research_wave(
        REPO,
        latest_wave_population,
        [pilot_population, wave_population],
        latest_wave_audit,
    )
    newest_result = validate_source_packet_research_wave(
        REPO,
        newest_wave_population,
        [pilot_population, wave_population, latest_wave_population],
        newest_wave_audit,
    )
    fourth_result = validate_source_packet_research_wave(
        REPO,
        fourth_wave_population,
        [
            pilot_population,
            wave_population,
            latest_wave_population,
            newest_wave_population,
        ],
        fourth_wave_audit,
    )
    next_result = validate_source_packet_research_wave(
        REPO,
        next_wave_population,
        [
            pilot_population,
            wave_population,
            latest_wave_population,
            newest_wave_population,
            fourth_wave_population,
        ],
        next_wave_audit,
    )
    sixth_result = validate_source_packet_research_wave(
        REPO,
        sixth_wave_population,
        [
            pilot_population,
            wave_population,
            latest_wave_population,
            newest_wave_population,
            fourth_wave_population,
            next_wave_population,
        ],
        sixth_wave_audit,
    )
    seventh_result = validate_source_packet_research_wave(
        REPO,
        seventh_wave_population,
        [
            pilot_population,
            wave_population,
            latest_wave_population,
            newest_wave_population,
            fourth_wave_population,
            next_wave_population,
            sixth_wave_population,
        ],
        seventh_wave_audit,
    )
    progress = build_source_packet_research_progress(
        REPO,
        [
            pilot_population,
            wave_population,
            latest_wave_population,
            newest_wave_population,
                fourth_wave_population,
                next_wave_population,
                sixth_wave_population,
                seventh_wave_population,
        ],
    )
    committed_progress = json.loads(
        (REPO / "reports/source_packet_research_progress.json").read_text(
            encoding="utf-8"
        )
    )

    assert result.status == "PASS"
    assert latest_result.status == "PASS"
    assert newest_result.status == "PASS"
    assert fourth_result.status == "PASS"
    assert next_result.status == "PASS"
    assert sixth_result.status == "PASS"
    assert seventh_result.status == "PASS"
    assert progress["TOTAL_SOURCE_PACKETS"] == 1524
    assert progress["SOURCE_PACKETS_READY"] == 70
    assert progress["SOURCE_PACKETS_PENDING"] == 1454
    assert progress["RESEARCH_BATCHES_COMPLETE"] == 8
    assert progress["RESEARCH_BATCHES_PENDING"] == 151
    assert progress["PREVIOUS_READY_PACKETS_CHANGED"] == 0
    assert progress["NON_SELECTED_PACKETS_CHANGED"] == 0
    assert committed_progress == progress
