"""Explicit compositional profiles for new onboarding callers only.

This module establishes structural expressibility, never evidence readiness.
Before eligibility the caller MUST pass this exact support object, including
context flags, to onboarding_evidence.validate_decision_support with its bound
independent review. Context strings describe the eligible population or the
context that a later blueprint must establish; they are not patient observations.
The returned requirements must still be enforced against the realized item.
Historical profile files and loaders are deliberately not consulted or modified.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .errors import QbankError
from .feature_anchor_registry import content_sha256
from .option_set_admissibility import ARCHETYPE_RESPONSE_AXIS, RESPONSE_CLASS_AXES

SNAPSHOT_PATH = 'research/qgen/onboarding/profile_snapshot_v2.json'
SNAPSHOT_ID = 'QGEN_PROFILE_SNAPSHOT_V2'
PROFILE_SCHEMA = 'PROFILE_SCHEMA_V2'
DISCIPLINE_IDS = dict(MED='MEDICINE', PED='PEDIATRICS', OBGYN='OBGYN',
                      SURG='SURGERY', PSY='PSYCHIATRY', PHELO='PHELO')
CONTEXT_FIELDS = {
    'pregnancy_postpartum_relevant': 'gestational_age_or_postpartum_day',
    'operative_relevant': 'operative_context',
    'capacity_relevant': 'capacity_context',
    'risk_relevant': 'risk_context',
    'legal_duty_relevant': 'jurisdiction',
}

# Preserve the historical comparison axes wherever their archetype existed.
# These are discipline/context rules, never named clinical entities or units.
PARITY_OVERLAYS = {
    'MED': {'DIAGNOSIS_SET': ['organ_system'], 'INVESTIGATION_SET': ['organ_system'],
            'NEXT_ACTION_SET': ['organ_system'], 'MANAGEMENT_STRATEGY_SET': ['drug_class']},
    'PED': {name: ['age_appropriateness'] for name in (
        'DIAGNOSIS_SET', 'INVESTIGATION_SET', 'NEXT_ACTION_SET', 'MANAGEMENT_STRATEGY_SET')},
    'OBGYN': {'DIAGNOSIS_SET': ['inflammatory_state', 'gestational_applicability'],
              'INVESTIGATION_SET': ['gestational_applicability'],
              'NEXT_ACTION_SET': ['gestational_applicability'],
              'MANAGEMENT_STRATEGY_SET': ['gestational_applicability']},
    'SURG': {'DIAGNOSIS_SET': ['organ_system'], 'INVESTIGATION_SET': ['organ_system'],
             'NEXT_ACTION_SET': ['organ_system'], 'MANAGEMENT_STRATEGY_SET': ['organ_system'],
             'DISPOSITION_SET': ['care_setting']},
    'PSY': {'DISPOSITION_SET': ['care_setting'], 'MANAGEMENT_STRATEGY_SET': ['care_setting'],
            'NEXT_ACTION_SET': ['care_setting']},
    'PHELO': {},
}


class ProfileV2Error(QbankError):
    """A profile pin, decision pair or conditional context is unusable."""


def _pair(granularity: str, archetype: str, *, domain='PATIENT_CLINICAL',
          tokens=None, flags=()) -> dict[str, Any]:
    axis = ARCHETYPE_RESPONSE_AXIS[archetype]
    definition = RESPONSE_CLASS_AXES[axis]
    return {
        'decision_granularity': granularity, 'option_set_archetype': archetype,
        'response_class_axis': axis, 'decision_domain': domain,
        'response_classes': sorted(tokens if tokens is not None else
                                   set(definition['tokens']) | {definition['generic_token']}),
        'required_context_flags': list(flags),
    }


def build_profile_snapshot() -> dict[str, Any]:
    """Build the closed ten-contract catalog deterministically, without I/O."""
    next_actions = [
        'NEXT_ACTION_FOR_CURRENT_CARE', 'OBSERVATION', 'MINIMAL_SUPPORT',
        'LOW_FLOW_SUPPORT', 'HIGH_FLOW_SUPPORT', 'ESCALATION_TO_CRITICAL_CARE',
        'DIAGNOSTIC_ORDER', 'MONITORING_ORDER', 'PHARMACOLOGIC_ACTION',
        'PROCEDURAL_INTERVENTION', 'DISPOSITION_ACTION', 'PATIENT_INSTRUCTION',
    ]
    contracts = {
        'DIAGNOSIS': [_pair('DIAGNOSIS', 'DIAGNOSIS_SET')],
        'NEXT_INVESTIGATION': [_pair('DIAGNOSTIC_TEST', 'INVESTIGATION_SET')],
        'INITIAL_MANAGEMENT': [
            _pair('SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', tokens=next_actions),
            _pair('MANAGEMENT_STRATEGY', 'MANAGEMENT_STRATEGY_SET',
                  tokens=set(RESPONSE_CLASS_AXES['management_capability']['tokens'])
                  - {'PROGRAMME_ACTION'} | {'MANAGEMENT_STRATEGY_FOR_PRESENTATION'}),
            _pair('DISPOSITION', 'DISPOSITION_SET', flags=['risk_relevant']),
        ],
        'EMERGENCY_STABILIZATION': [
            _pair('SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', tokens=[
                'LOW_FLOW_SUPPORT', 'HIGH_FLOW_SUPPORT', 'ESCALATION_TO_CRITICAL_CARE',
                'PHARMACOLOGIC_ACTION', 'PROCEDURAL_INTERVENTION',
                'NEXT_ACTION_FOR_CURRENT_CARE'], flags=['risk_relevant']),
            _pair('DISPOSITION', 'DISPOSITION_SET', flags=['risk_relevant']),
        ],
        'SCREENING_PREVENTION': [
            _pair('DIAGNOSTIC_TEST', 'INVESTIGATION_SET'),
            _pair('SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', tokens=[
                'DIAGNOSTIC_ORDER', 'MONITORING_ORDER', 'PHARMACOLOGIC_ACTION',
                'PATIENT_INSTRUCTION', 'NEXT_ACTION_FOR_CURRENT_CARE']),
            _pair('PROGRAMME_ACTION', 'MANAGEMENT_STRATEGY_SET',
                  domain='POPULATION_PROGRAMME', tokens=['PROGRAMME_ACTION']),
        ],
        'MEDICATION_SELECTION': [
            _pair('SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', tokens=['PHARMACOLOGIC_ACTION']),
            _pair('MANAGEMENT_STRATEGY', 'MANAGEMENT_STRATEGY_SET', tokens=[
                'PHARMACOLOGIC_ONLY', 'PHARMACOLOGIC_TREATMENT']),
        ],
        'INTERPRETATION': [
            _pair('EPIDEMIOLOGIC_EXPLANATION', 'STATISTICAL_INTERPRETATION_SET',
                  domain='EVIDENCE_INTERPRETATION'),
            _pair('DIAGNOSIS', 'DIAGNOSIS_SET'),
        ],
        'ETHICAL_LEGAL_ACTION': [
            _pair('ETHICAL_ACTION', 'ETHICAL_ACTION_SET'),
            _pair('LEGAL_DUTY', 'LEGAL_ACTION_SET', flags=['legal_duty_relevant']),
        ],
        'COMMUNICATION': [
            _pair('SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', tokens=[
                'COMMUNICATION_ACTION', 'PATIENT_INSTRUCTION']),
            _pair('ETHICAL_ACTION', 'ETHICAL_ACTION_SET', tokens=[
                'AUTONOMY', 'CONFIDENTIALITY', 'ETHICAL_ACTION']),
        ],
        'PROFESSIONAL_ORGANIZATIONAL_ACTION': [
            _pair('PROGRAMME_ACTION', 'MANAGEMENT_STRATEGY_SET',
                  domain='POPULATION_PROGRAMME', tokens=['PROGRAMME_ACTION']),
            _pair('LEGAL_DUTY', 'LEGAL_ACTION_SET', flags=['legal_duty_relevant']),
            _pair('ETHICAL_ACTION', 'ETHICAL_ACTION_SET'),
        ],
    }
    snapshot = {
        'schema_version': PROFILE_SCHEMA, 'snapshot_id': SNAPSHOT_ID,
        'scope': 'QGEN_COMPOSITIONAL_PROFILE_SNAPSHOT',
        'common_core': [
            'SINGLE_BEST_ANSWER', 'POSITIVE_ANCHORING', 'DECISION_SCOPED_EVIDENCE',
            'FOUR_STATE_SEMANTICS', 'PAIRWISE_COHERENCE', 'OPTION_PARITY',
            'INDEPENDENT_FINAL_REVIEW',
        ],
        'context_flag_fields': dict(CONTEXT_FIELDS),
        'context_interpretation': 'REVIEWED_ELIGIBILITY_REQUIREMENTS_NOT_STEM_OBSERVATIONS',
        'overlays': {
            discipline: {'discipline_profile_id': profile,
                         'always_required': ['age'] if discipline == 'PED' else [],
                         'nominal_parity_by_archetype': deepcopy(PARITY_OVERLAYS[discipline])}
            for discipline, profile in DISCIPLINE_IDS.items()
        },
        'decision_contracts': contracts,
        'competitor_ranking_preference': [
            'NEAREST_UNSATISFIED_CORRECTNESS_CONDITION', 'SHARED_FEATURE_COUNT',
            'REVIEWED_SEED_STRENGTH',
        ],
        'option_set_contracts': {
            archetype: {
                'option_set_archetype': archetype, 'response_class_axis': axis,
                'token_implications': {
                    token: [RESPONSE_CLASS_AXES[axis]['generic_token']]
                    for token in sorted(RESPONSE_CLASS_AXES[axis]['tokens'])
                },
                'nominal_parity_axes': [],
            }
            for archetype, axis in sorted(ARCHETYPE_RESPONSE_AXIS.items())
        },
        'study_unit_specific_exceptions': [],
        'evidence_readiness': 'NOT_ASSESSED',
    }
    snapshot['content_sha256'] = content_sha256(snapshot)
    return snapshot


def _validate_snapshot(snapshot: dict) -> None:
    if not isinstance(snapshot, dict):
        raise ProfileV2Error('loaded explicit profile snapshot required')
    if snapshot.get('snapshot_id') != SNAPSHOT_ID or snapshot.get('schema_version') != PROFILE_SCHEMA:
        raise ProfileV2Error('unknown profile snapshot or schema; no implicit latest')
    content = {key: value for key, value in snapshot.items() if key != 'content_sha256'}
    if content_sha256(content) != snapshot.get('content_sha256'):
        raise ProfileV2Error('profile snapshot content hash mismatch')
    # This version is a closed catalog. A rehashed arbitrary pairing or weakened
    # overlay is a new contract version, not another admissible V2 snapshot.
    if snapshot != build_profile_snapshot():
        raise ProfileV2Error('profile snapshot differs from the closed V2 contract')


def load_profile_snapshot(root: Path, snapshot_id: str, expected_sha256: str) -> dict:
    """Load the explicit V2 artifact and compare every field with its expected pin."""
    if snapshot_id != SNAPSHOT_ID or not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ProfileV2Error('explicit profile snapshot id and expected SHA256 required')
    try:
        snapshot = json.loads((Path(root) / SNAPSHOT_PATH).read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileV2Error(f'profile snapshot unavailable: {error}') from error
    _validate_snapshot(snapshot)
    if snapshot['content_sha256'] != expected_sha256:
        raise ProfileV2Error('profile snapshot does not match the expected pin')
    return snapshot


def resolve_profile(support: dict, snapshot: dict) -> dict:
    """Resolve structure only; evidence validation of the exact support is separate.

    Do not use PROFILE_EXPRESSIBLE as permission to generate. The caller must
    validate_decision_support(support, review, addresses, catalog) and carry the
    returned support_sha256 into its frozen opportunity and downstream stages.
    """
    _validate_snapshot(snapshot)
    if not isinstance(support, dict):
        raise ProfileV2Error('decision support must be an object')
    for field in ('discipline', 'decision_contract', 'decision_granularity',
                  'option_set_archetype', 'response_class'):
        if not isinstance(support.get(field), str) or not support[field]:
            raise ProfileV2Error(f'nonempty decision contract string required: {field}')
    overlay = snapshot['overlays'].get(support.get('discipline'))
    candidates = snapshot['decision_contracts'].get(support.get('decision_contract'))
    if overlay is None or candidates is None:
        raise ProfileV2Error('unknown discipline or decision contract')
    pairs = [pair for pair in candidates
             if pair['decision_granularity'] == support.get('decision_granularity')
             and pair['option_set_archetype'] == support.get('option_set_archetype')
             and support.get('response_class') in pair['response_classes']
             and support.get('decision_domain', pair['decision_domain']) == pair['decision_domain']]
    if len(pairs) != 1:
        raise ProfileV2Error('unsupported decision/granularity/archetype/response-class/domain pairing')
    pair = pairs[0]
    context = support.get('context')
    if not isinstance(context, dict):
        raise ProfileV2Error('reviewed context flags required')
    for flag in snapshot['context_flag_fields']:
        if type(context.get(flag)) is not bool:
            raise ProfileV2Error(f'explicit boolean context flag required: {flag}')
    for flag in pair['required_context_flags']:
        if context[flag] is not True:
            raise ProfileV2Error(f'this decision requires context flag {flag}')
    required = sorted(set(overlay['always_required']) | {
        field for flag, field in snapshot['context_flag_fields'].items() if context[flag]
    })
    for field in required:
        if not isinstance(context.get(field), str) or not context[field].strip():
            raise ProfileV2Error(f'reviewed context requirement missing: {field}')
    contract = deepcopy(snapshot['option_set_contracts'][pair['option_set_archetype']])
    contract['nominal_parity_axes'] = list(
        overlay['nominal_parity_by_archetype'].get(pair['option_set_archetype'], []))
    return {
        **contract, 'discipline_profile_id': overlay['discipline_profile_id'],
        'decision_contract': support['decision_contract'],
        'decision_granularity': pair['decision_granularity'],
        'decision_domain': pair['decision_domain'], 'response_class': support['response_class'],
        'demanded_response_class': support['response_class'],
        'profile_schema': snapshot['schema_version'],
        'profile_snapshot_id': snapshot['snapshot_id'],
        'profile_snapshot_sha256': snapshot['content_sha256'],
        'support_sha256': content_sha256(support),
        'scenario_requirements': required,
        'context_requirements': {field: context[field] for field in required},
        'competitor_ranking_preference': list(snapshot['competitor_ranking_preference']),
        'common_core': list(snapshot['common_core']),
        'structural_status': 'PROFILE_EXPRESSIBLE', 'evidence_readiness': 'NOT_ASSESSED',
    }
