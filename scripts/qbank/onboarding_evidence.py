"""Evidence readiness is a reviewed address/decision relation, never packet status."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import QbankError
from .feature_anchor_registry import content_sha256

STATES = ('NOT_ASSESSED', 'ALIGNED_COMPLETE', 'ALIGNED_PARTIAL', 'MISALIGNED',
          'EVIDENCE_MISSING', 'OUT_OF_SCOPE')


class OnboardingEvidenceError(QbankError):
    """Unresolved evidence or provenance at the new onboarding boundary."""


def subject_hash(subject: dict) -> str:
    return content_sha256(subject)


def verify_review(subject: dict, review: dict, *, required_refs=()) -> None:
    """Check review consistency. Actual independence is execution provenance.

    This does not infer medical entailment from a hash or two identity strings.
    Canonical review artifacts must originate in a separately executed review.
    """
    if review.get('verdict') != 'APPROVED':
        raise OnboardingEvidenceError('independent review is not APPROVED')
    if review.get('subject_sha256') != subject_hash(subject):
        raise OnboardingEvidenceError('stale or mismatched review subject hash')
    author = subject.get('author_execution_id')
    reviewer = review.get('reviewer_execution_id')
    if (not author or not reviewer or author == reviewer
            or review.get('author_execution_id') != author
            or review.get('independent_context') is not True
            or not review.get('rationale')):
        raise OnboardingEvidenceError('separate independent review provenance required')
    if not set(required_refs) <= set(review.get('evidence_refs_checked') or []):
        raise OnboardingEvidenceError('review has not checked every load-bearing claim')


def initial_address_state(address: dict, packets: list[str], catalog: dict) -> str:
    if address.get('generation_policy') == 'NEVER':
        return 'OUT_OF_SCOPE'
    verified = {c['source_packet_id'] for c in catalog.values() if c['source_verified']}
    return 'NOT_ASSESSED' if set(packets) & verified else 'EVIDENCE_MISSING'


def validate_decision_support(support: dict, review: dict, addresses: dict,
                              catalog: dict) -> str:
    if support.get('alignment_state') != 'ALIGNED_COMPLETE':
        raise OnboardingEvidenceError('decision evidence must be ALIGNED_COMPLETE')
    required = ('allocation_address_id', 'study_unit_id', 'discipline',
                'mcc_objective_ids', 'learner_decision_id', 'statement',
                'clinical_target', 'population', 'jurisdiction', 'limitations',
                'source_packet_ids', 'claim_ids', 'alignment_rationale',
                'mapping_provenance')
    for key in required:
        if not support.get(key):
            raise OnboardingEvidenceError(f'decision support missing {key}')
    address = addresses.get(support['allocation_address_id'])
    if not address or address.get('generation_policy') == 'NEVER':
        raise OnboardingEvidenceError('unknown or out-of-scope allocation address')
    for key in ('study_unit_id', 'discipline'):
        if support[key] != address[key]:
            raise OnboardingEvidenceError(f'canonical {key} mismatch')
    if not set(support['mcc_objective_ids']) <= set(address['mcc_objective_ids']):
        raise OnboardingEvidenceError('MCC scope mismatch')
    refs = support['claim_ids']
    if len(refs) != len(set(refs)):
        raise OnboardingEvidenceError('duplicate claim ids')
    actual_packets = set()
    for ref in refs:
        claim = catalog.get(ref)
        if not claim or not claim.get('source_verified') or not claim.get('text'):
            raise OnboardingEvidenceError(f'claim missing or unverified: {ref}')
        if (review.get('claim_sha256') or {}).get(ref) != subject_hash(claim):
            raise OnboardingEvidenceError(f'claim content hash mismatch: {ref}')
        actual_packets.add(claim['source_packet_id'])
    if actual_packets != set(support['source_packet_ids']):
        raise OnboardingEvidenceError('address-specific claim/packet mapping mismatch')
    verify_review(support, review, required_refs=refs)
    return 'EVIDENCE_READY'


def load_claim_catalog(root: Path) -> dict[str, dict[str, Any]]:
    """Import frozen packet claims without giving any address a readiness state."""
    result = {}
    for path in sorted((root / 'research/qgen').glob('source_packet_population_srb_*.json')):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        for packet in json.loads(path.read_text())['source_packets']:
            for key, id_key in (('supported_recommendations','recommendation_id'),
                                ('important_contraindications_or_exceptions','exception_id')):
                for claim in packet.get(key) or []:
                    row = {'source_packet_id':packet['source_packet_id'],
                           'text':claim['statement'],
                           'source_verified':packet['status']=='SOURCE_PACKET_READY'
                               and packet.get('verification_status')=='VERIFIED_COMPLETE',
                           'source_citations':claim.get('source_citations',[]),
                           'artifact':path.relative_to(root).as_posix(),
                           'artifact_sha256':sha}
                    if claim[id_key] in result:
                        raise OnboardingEvidenceError(f'duplicate canonical claim: {claim[id_key]}')
                    result[claim[id_key]] = row
    return result
