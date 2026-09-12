"""Append-only vocabulary, independently bound to evidence and decision scope."""
from copy import deepcopy
import importlib
import importlib.util
import pytest
from qbank.errors import QbankError
from qbank.feature_anchor_registry import content_sha256, registry_hash


def api():
    assert importlib.util.find_spec('qbank.vocabulary_onboarding'), 'vocabulary onboarding missing'
    return importlib.import_module('qbank.vocabulary_onboarding')


def fixture():
    parent={'snapshot_id':'FEATURE_ANCHOR_SNAPSHOT_V3','features':[],
            'anchor_relations':[],'anchor_scope':[],'registry_hash':registry_hash([],[])}
    p={'proposal_id':'FP-X','feature_id':'SF-X','preferred_label':'Bulging tympanic membrane',
       'feature_type':'EXAMINATION_FINDING','identity_type':'FINDING','study_unit_id':'SU-NEW',
       'learner_decision_ids':['LD-NEW'],'evidence_refs':['CLM-X'],
       'classification':'NEW_CANONICAL_FEATURE','author_execution_id':'author'}
    c={'CLM-X':{'text':'A bulging membrane supports the diagnosis', 'source_verified':True,
                 'source_packet_id':'SRC-X'}}
    review={'subject_sha256':content_sha256(p),'verdict':'APPROVED',
            'reviewer_execution_id':'reviewer','author_execution_id':'author',
            'independent_context':True,'rationale':'Feature identity and evidence checked',
            'evidence_refs_checked':['CLM-X'],'claim_sha256':{'CLM-X':content_sha256(c['CLM-X'])}}
    return parent,p,review,c


def test_new_unit_can_enter_child_without_mutating_parent():
    parent,p,r,c=fixture(); frozen=deepcopy(parent)
    s=api().build_extended_snapshot(parent,[p],{'FP-X':r},c)
    assert parent==frozen
    assert s['parent_snapshot_id']=='FEATURE_ANCHOR_SNAPSHOT_V3'
    assert s['feature_count']==1
    assert api().snapshot_vocabulary(s,'SU-NEW','LD-NEW')['SF-X']['clinical_role']=='EXAMINATION_FINDING'
    assert api().snapshot_vocabulary(s,'SU-OTHER','LD-NEW')=={}
    assert api().snapshot_vocabulary(s,'SU-NEW','LD-OTHER')=={}


@pytest.mark.parametrize('verdict',['REJECTED','UNCERTAIN'])
def test_unapproved_rows_never_enter_snapshot(verdict):
    parent,p,r,c=fixture();r['verdict']=verdict
    s=api().build_extended_snapshot(parent,[p],{'FP-X':r},c)
    assert s['feature_count']==0


@pytest.mark.parametrize('change',['evidence','ambiguous','stale','identity','role','scope','missing_review'])
def test_bad_proposal_is_not_admissible(change):
    parent,p,r,c=fixture()
    if change=='evidence': p['evidence_refs']=[]
    if change=='ambiguous':p['classification']='AMBIGUOUS'
    if change=='identity':p['identity_type']='UNKNOWN'
    if change=='role':p['feature_type']='MAGICAL_ROLE'
    if change=='scope':p['learner_decision_ids']=[]
    if change!='stale':r['subject_sha256']=content_sha256(p)
    else:p['preferred_label']='Different feature'
    with pytest.raises(QbankError):api().build_extended_snapshot(parent,[p],{} if change=='missing_review' else {'FP-X':r},c)


def test_snapshot_is_deterministic_and_scope_is_hashed():
    parent,p,r,c=fixture();m=api()
    a=m.build_extended_snapshot(parent,[p],{'FP-X':r},c)
    assert a==m.build_extended_snapshot(parent,[p],{'FP-X':r},c)
    tampered=deepcopy(a);tampered['unit_bindings']['SU-NEW']['LD-OTHER']=['SF-X']
    with pytest.raises(QbankError):m.verify_snapshot(tampered,a['content_sha256'])


def test_unsafe_same_label_different_identity_is_not_merged():
    m=api();_,p,_,_=fixture()
    old={**p,'feature_id':'SF-OLD','identity_type':'DIAGNOSIS'}
    result=m.normalize_feature(p,[old])
    assert result['classification']=='RELATED_BUT_DISTINCT'
    assert result['canonical_feature_id'] is None


def test_normalized_existing_feature_keeps_identity():
    m=api();_,p,_,_=fixture();old={**p,'feature_id':'SF-OLD'}
    p['preferred_label']='BULGING  tympanic membrane'
    result=m.normalize_feature(p,[old])
    assert result['classification']=='NORMALIZED_EXISTING'
    assert result['canonical_feature_id']=='SF-OLD'


def test_duplicate_ids_are_refused():
    parent,p,r,c=fixture()
    with pytest.raises(QbankError):api().build_extended_snapshot(parent,[p,p],{'FP-X':r},c)


def anchor_fixture():
    parent,p,r,c=fixture()
    a={'extension_id':'AX','feature_id':'SF-X','target_concept_id':'CON-X','seed_id':'SEED-X',
       'anchor_study_unit_id':'SU-NEW','learner_decision':'LD-NEW','decision_granularity':'DIAGNOSIS',
       'required_state':'PRESENT','scope_opportunity_labels':['OPP-X'],'context':{},
       'evidence_refs':['CLM-X'],'response_class':['PLAUSIBLE_DIAGNOSTIC_ENTITY'],
       'author_execution_id':'anchor-author'}
    ar={**r,'author_execution_id':'anchor-author','subject_sha256':content_sha256(a)}
    return parent,p,r,c,a,ar


def test_approved_anchor_enters_new_snapshot():
    parent,p,r,c,a,ar=anchor_fixture()
    s=api().build_extended_snapshot(parent,[p],{'FP-X':r},c,anchor_proposals=[a],anchor_reviews={'AX':ar})
    assert s['anchor_relation_count']==1
    assert s['anchor_relations'][0]['scope_opportunity_labels']==['OPP-X']


@pytest.mark.parametrize('verdict',['REJECTED','UNCERTAIN'])
def test_rejected_or_uncertain_anchor_excluded(verdict):
    parent,p,r,c,a,ar=anchor_fixture();ar['verdict']=verdict
    s=api().build_extended_snapshot(parent,[p],{'FP-X':r},c,anchor_proposals=[a],anchor_reviews={'AX':ar})
    assert s['anchor_relation_count']==0


@pytest.mark.parametrize('key,value',[('required_state','ABSENT'),('scope_opportunity_labels',[]),('learner_decision','LD-OTHER')])
def test_anchor_state_and_decision_scope_fail_closed(key,value):
    parent,p,r,c,a,ar=anchor_fixture();a[key]=value;ar['subject_sha256']=content_sha256(a)
    with pytest.raises(QbankError):
        api().build_extended_snapshot(parent,[p],{'FP-X':r},c,anchor_proposals=[a],anchor_reviews={'AX':ar})


def test_parent_legacy_rows_are_preserved_without_granting_new_decision_scope():
    from pathlib import Path
    from qbank.feature_anchor_registry import load_snapshot
    parent=load_snapshot(Path(__file__).resolve().parents[1],'FEATURE_ANCHOR_SNAPSHOT_V3')
    s=api().build_extended_snapshot(parent,[],{}, {})
    assert {x['feature_id']:x for x in s['features']}=={x['feature_id']:x for x in parent['features']}
    assert {x['anchor_relation_id']:x for x in s['anchor_relations']}=={x['anchor_relation_id']:x for x in parent['anchor_relations']}
    assert api().snapshot_vocabulary(s,'SU-NEW','LD-NEW')=={}
