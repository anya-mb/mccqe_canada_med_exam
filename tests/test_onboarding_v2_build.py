"""V4 snapshot and Phase 7/8 revalidation reproduce byte-identically from frozen inputs."""
import json
from pathlib import Path

import pytest

from qbank import onboarding_v2_build as ob

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / 'research/qgen/onboarding' / name).read_text())


@pytest.fixture(scope='module')
def artifacts():
    return {
        'new_discipline': load('v2_new_discipline_evidence.json'),
        'existing': load('v2_existing_decision_proposals.json'),
        'blocked': load('v2_profile_blocked_decision_proposals.json'),
        'review': load('v2_independent_review_raw.json'),
        'committed_v4': load('feature_anchor_snapshot_v4.json'),
        'phase7_report': load('v2_phase7_phase8_revalidation.json'),
    }


def test_v4_snapshot_rebuilds_byte_identically(artifacts):
    rebuilt = ob.build_snapshot_v4(ROOT, artifacts['new_discipline'], artifacts['existing'],
                                    artifacts['blocked'], artifacts['review'])
    assert rebuilt == artifacts['committed_v4']


def test_v4_only_approved_rows_entered(artifacts):
    v4 = artifacts['committed_v4']
    assert v4['feature_count'] == 144
    assert len(v4['approved_proposal_ids']) == 42
    excluded_ids = {row['proposal_id'] for row in v4['excluded_proposals']}
    assert excluded_ids == {
        'FP-ONB2-P146-PERSISTENT-ASYMMETRY',
        'FP-ONB2-P146-REDUCED-AIR-ENTRY',
        'FP-ONB2-P146-INCOMPLETE-RESPONSE',
    }


def test_original_26_revalidation_matches_committed_report(artifacts):
    from qbank.feature_anchor_registry import content_sha256

    final_alloc = json.loads((ROOT / 'research/scope/final_question_allocation.json').read_text())
    canonical_addresses = {a['allocation_address_id']: a for a in final_alloc['allocation_addresses']}
    results = ob.revalidate_supports(ROOT, artifacts['existing']['supports'], artifacts['review'],
                                      canonical_addresses)
    valid = sum(1 for r in results if r['outcome'] == 'VALID')
    blocked = sum(1 for r in results if r['outcome'] == 'EVIDENCE_BLOCKED')
    assert len(results) == 26
    assert valid == 24
    assert blocked == 2
    assert {r['learner_decision_id'] for r in results if r['outcome'] == 'EVIDENCE_BLOCKED'} == {
        'LD-D23-01', 'LD-PH11-02'}
    report = artifacts['phase7_report']
    assert report['original_26_revalidation']['valid_count'] == valid
    assert report['review_input_sha256'] == content_sha256(artifacts['review'])


def test_previously_profile_blocked_six_now_evidence_ready(artifacts):
    final_alloc = json.loads((ROOT / 'research/scope/final_question_allocation.json').read_text())
    canonical_addresses = {a['allocation_address_id']: a for a in final_alloc['allocation_addresses']}
    results = ob.revalidate_supports(ROOT, artifacts['blocked']['supports'], artifacts['review'],
                                      canonical_addresses)
    assert len(results) == 6
    assert all(r['outcome'] == 'VALID' for r in results)
