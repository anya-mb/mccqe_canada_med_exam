"""Fail-closed compositional profiles without mutating historical profiles."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def api():
    assert importlib.util.find_spec('qbank.qgen_profiles_v2'), 'Profile V2 is not implemented'
    return importlib.import_module('qbank.qgen_profiles_v2')


def support(**changes):
    row = dict(discipline='MED', decision_contract='DIAGNOSIS',
               decision_granularity='DIAGNOSIS', option_set_archetype='DIAGNOSIS_SET',
               response_class='PLAUSIBLE_DIAGNOSTIC_ENTITY', context={
                   'pregnancy_postpartum_relevant': False, 'operative_relevant': False,
                   'capacity_relevant': False, 'risk_relevant': False,
                   'legal_duty_relevant': False})
    row.update(changes)
    return row


def resolve(row):
    return api().resolve_profile(row, api().build_profile_snapshot())


def test_diagnosis_contract_returns_existing_engine_axis_and_explicit_pins():
    result = resolve(support())
    assert result['response_class_axis'] == 'cardinal_syndrome_capability'
    assert result['decision_domain'] == 'PATIENT_CLINICAL'
    assert result['profile_snapshot_id'] == 'QGEN_PROFILE_SNAPSHOT_V2'
    assert len(result['profile_snapshot_sha256']) == 64
    assert result['evidence_readiness'] == 'NOT_ASSESSED'
    assert result['token_implications']['AIRFLOW_OBSTRUCTION'] == ['PLAUSIBLE_DIAGNOSTIC_ENTITY']


@pytest.mark.parametrize('changes', [
    {'decision_contract': 'ALLOW_ANYTHING'}, {'decision_granularity': 'SINGLE_NEXT_ACTION'},
    {'response_class': 'COMMUNICATION_ACTION'}, {'option_set_archetype': 'NEXT_ACTION_SET'},
    {'discipline': 'UNKNOWN'}, {'decision_domain': 'POPULATION_PROGRAMME'},
    {'context': {}}, {'context': {'pregnancy_postpartum_relevant': 'false'}},
])
def test_wrong_class_domain_granularity_or_missing_context_fails(changes):
    module = api()
    with pytest.raises(module.ProfileV2Error):
        resolve(support(**changes))


@pytest.mark.parametrize('unit', ['SU-PM-06', 'SU-PM-10'])
@pytest.mark.parametrize('discipline', ['MED', 'PHELO'])
def test_palliative_legal_action_uses_shared_legal_contract(unit, discipline):
    row = support(study_unit_id=unit, discipline=discipline,
                  decision_contract='ETHICAL_LEGAL_ACTION', decision_granularity='LEGAL_DUTY',
                  option_set_archetype='LEGAL_ACTION_SET', response_class='TREATING_CLINICIAN_DUTY')
    row['context'].update(legal_duty_relevant=True, jurisdiction='Ontario')
    assert resolve(row)['response_class_axis'] == 'duty_holder_class'
    del row['context']['jurisdiction']
    with pytest.raises(api().ProfileV2Error):
        resolve(row)


@pytest.mark.parametrize('unit,contract,granularity,archetype,response', [
    ('SU-GY-03', 'NEXT_INVESTIGATION', 'DIAGNOSTIC_TEST', 'INVESTIGATION_SET', 'STRUCTURAL'),
    ('SU-GY-04', 'INITIAL_MANAGEMENT', 'MANAGEMENT_STRATEGY', 'MANAGEMENT_STRATEGY_SET',
     'MANAGEMENT_STRATEGY_FOR_PRESENTATION'),
    ('SU-GY-10', 'MEDICATION_SELECTION', 'SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', 'PHARMACOLOGIC_ACTION'),
])
def test_gynecology_does_not_require_irrelevant_gestational_context(unit, contract, granularity, archetype, response):
    row = support(study_unit_id=unit, discipline='OBGYN', decision_contract=contract,
                  decision_granularity=granularity, option_set_archetype=archetype, response_class=response)
    assert resolve(row)['structural_status'] == 'PROFILE_EXPRESSIBLE'
    row['context']['pregnancy_postpartum_relevant'] = True
    with pytest.raises(api().ProfileV2Error):
        resolve(row)
    row['context']['gestational_age_or_postpartum_day'] = 'Postpartum day 4'
    assert resolve(row)['structural_status'] == 'PROFILE_EXPRESSIBLE'


@pytest.mark.parametrize('discipline,flag,field', [
    ('PED', None, 'age'), ('SURG', 'operative_relevant', 'operative_context'),
    ('PSY', 'capacity_relevant', 'capacity_context'), ('PSY', 'risk_relevant', 'risk_context'),
])
def test_conditional_overlay_context_is_required(discipline, flag, field):
    row = support(discipline=discipline)
    if flag:
        row['context'][flag] = True
    with pytest.raises(api().ProfileV2Error):
        resolve(row)
    row['context'][field] = 'Explicit context in the reviewed decision'
    assert resolve(row)['structural_status'] == 'PROFILE_EXPRESSIBLE'


def test_legal_and_emergency_cannot_opt_out_of_intrinsic_context():
    for contract, granularity, archetype, response in [
        ('ETHICAL_LEGAL_ACTION', 'LEGAL_DUTY', 'LEGAL_ACTION_SET', 'LEGAL_DUTY_ACTION'),
        ('EMERGENCY_STABILIZATION', 'SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', 'LOW_FLOW_SUPPORT'),
    ]:
        with pytest.raises(api().ProfileV2Error):
            resolve(support(decision_contract=contract, decision_granularity=granularity,
                            option_set_archetype=archetype, response_class=response))


def test_epidemiologic_and_programme_granularities_remain_expressible():
    row = support(discipline='PHELO', decision_contract='INTERPRETATION',
                  decision_granularity='EPIDEMIOLOGIC_EXPLANATION',
                  option_set_archetype='STATISTICAL_INTERPRETATION_SET',
                  response_class='CONFOUNDING')
    assert resolve(row)['decision_domain'] == 'EVIDENCE_INTERPRETATION'
    row.update(decision_contract='PROFESSIONAL_ORGANIZATIONAL_ACTION',
               decision_granularity='PROGRAMME_ACTION', option_set_archetype='MANAGEMENT_STRATEGY_SET',
               response_class='PROGRAMME_ACTION')
    assert resolve(row)['decision_domain'] == 'POPULATION_PROGRAMME'


def test_snapshot_rebuild_and_load_are_explicit_and_content_verified(tmp_path):
    module = api()
    snapshot = module.build_profile_snapshot()
    path = tmp_path / module.SNAPSHOT_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(snapshot))
    loaded = module.load_profile_snapshot(tmp_path, snapshot['snapshot_id'], snapshot['content_sha256'])
    assert loaded == snapshot
    for snapshot_id, sha in [('latest', snapshot['content_sha256']),
                             (snapshot['snapshot_id'], '0' * 64)]:
        with pytest.raises(module.ProfileV2Error):
            module.load_profile_snapshot(tmp_path, snapshot_id, sha)
    snapshot['overlays']['PED']['always_required'] = []
    path.write_text(json.dumps(snapshot))
    with pytest.raises(module.ProfileV2Error):
        module.load_profile_snapshot(tmp_path, loaded['snapshot_id'], loaded['content_sha256'])


def test_tampered_in_memory_snapshot_is_refused():
    snapshot = api().build_profile_snapshot()
    snapshot['overlays']['PED']['always_required'] = []
    with pytest.raises(api().ProfileV2Error):
        api().resolve_profile(support(), snapshot)


def test_published_artifact_rebuilds_byte_identically():
    snapshot = api().build_profile_snapshot()
    assert (ROOT / api().SNAPSHOT_PATH).read_text() == json.dumps(snapshot, indent=2, sort_keys=True) + '\n'


@pytest.mark.parametrize('label,contract,granularity,discipline,axis,parity', [
    ('G2-MED-04', 'INITIAL_MANAGEMENT', 'SINGLE_NEXT_ACTION', 'MED',
     'next_action_class', ['organ_system']),
    ('G2-PED-01', 'DIAGNOSIS', 'DIAGNOSIS', 'PED',
     'cardinal_syndrome_capability', ['age_appropriateness']),
])
def test_historical_accepted_control_maps_without_losing_response_or_parity(label, contract, granularity, discipline, axis, parity):
    path = ROOT / 'research/qgen/safe_yield/g2_profile_pilot.scenarios.json'
    before = path.read_bytes()
    scenario = next(row for row in json.loads(before)['scenarios'] if row['opportunity_label'] == label)
    row = support(discipline=discipline, decision_contract=contract, decision_granularity=granularity,
                  option_set_archetype=scenario['option_set_archetype'],
                  response_class=scenario['demanded_response_class'])
    if discipline == 'PED':
        row['context']['age'] = 'Infant age must be explicit'
    result = resolve(row)
    assert result['response_class_axis'] == axis
    assert result['nominal_parity_axes'] == parity
    assert result['demanded_response_class'] == scenario['demanded_response_class']
    assert path.read_bytes() == before


def test_conditional_gyne_parity_keeps_nonpregnancy_category_and_inflammatory_axis():
    result = resolve(support(discipline='OBGYN'))
    assert result['nominal_parity_axes'] == ['inflammatory_state', 'gestational_applicability']


def test_rehashed_weakened_catalog_and_nonstrings_are_rejected():
    from qbank.feature_anchor_registry import content_sha256
    snapshot = api().build_profile_snapshot()
    snapshot['overlays']['PED']['always_required'] = []
    del snapshot['content_sha256']
    snapshot['content_sha256'] = content_sha256(snapshot)
    with pytest.raises(api().ProfileV2Error):
        api().resolve_profile(support(), snapshot)
    for field in ['discipline', 'decision_contract', 'option_set_archetype', 'response_class']:
        with pytest.raises(api().ProfileV2Error):
            resolve(support(**{field: []}))


@pytest.mark.parametrize('contract,granularity,archetype,response', [
    ('SCREENING_PREVENTION', 'DIAGNOSTIC_TEST', 'INVESTIGATION_SET', 'DIAGNOSTIC_ADVANCEMENT'),
    ('COMMUNICATION', 'SINGLE_NEXT_ACTION', 'NEXT_ACTION_SET', 'COMMUNICATION_ACTION'),
    ('ETHICAL_LEGAL_ACTION', 'ETHICAL_ACTION', 'ETHICAL_ACTION_SET', 'AUTONOMY'),
])
def test_remaining_shared_contracts_have_coherent_pairs(contract, granularity, archetype, response):
    assert resolve(support(decision_contract=contract, decision_granularity=granularity,
                           option_set_archetype=archetype, response_class=response))['structural_status'] == 'PROFILE_EXPRESSIBLE'
