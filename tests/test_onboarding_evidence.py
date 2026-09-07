"""Adversarial tests for the new evidence boundary, independent of W1 replay."""
from copy import deepcopy
import pytest
from qbank import onboarding_evidence as e
from qbank.errors import QbankError


def inputs():
    address = {'allocation_address_id':'SU-X','study_unit_id':'SU-X','discipline':'MED',
               'mcc_objective_ids':['1'],'generation_policy':'GENERATE_WHEN_STRONG_AND_NON_REDUNDANT'}
    support = {'allocation_address_id':'SU-X','study_unit_id':'SU-X','discipline':'MED',
               'mcc_objective_ids':['1'],'learner_decision_id':'LD-X','statement':'Choose investigation',
               'clinical_target':'target','population':'adults','jurisdiction':'Canada',
               'limitations':['Defined narrow decision only'],'source_packet_ids':['SRC-X'],
               'claim_ids':['CLM-X'],'alignment_state':'ALIGNED_COMPLETE',
               'alignment_rationale':'The claim supports this narrow decision.',
               'author_execution_id':'author','decision_contract':'NEXT_INVESTIGATION',
               'decision_granularity':'DIAGNOSTIC_TEST','option_set_archetype':'INVESTIGATION_SET',
               'response_class':'DIAGNOSTIC_TEST','context':{},'mapping_provenance':'explicit decision review'}
    catalog = {'CLM-X':{'source_packet_id':'SRC-X','text':'Use test for target',
                         'source_verified':True,'artifact':'fixture','artifact_sha256':'a'}}
    review = {'subject_sha256':e.subject_hash(support),'verdict':'APPROVED',
              'reviewer_execution_id':'separate-reviewer','author_execution_id':'author',
              'independent_context':True,'rationale':'Claim and scope checked',
              'evidence_refs_checked':['CLM-X'],
              'claim_sha256':{k:e.subject_hash(v) for k,v in catalog.items()}}
    return support,review,{'SU-X':address},catalog


def test_packet_ready_does_not_imply_address_ready():
    s,r,a,c=inputs()
    assert e.initial_address_state(a['SU-X'], ['SRC-X'], c)=='NOT_ASSESSED'


def test_reviewed_narrow_support_is_ready_without_promoting_address():
    s,r,a,c=inputs()
    assert e.validate_decision_support(s,r,a,c)=='EVIDENCE_READY'
    assert e.initial_address_state(a['SU-X'], ['SRC-X'], c)=='NOT_ASSESSED'


@pytest.mark.parametrize('state',['ALIGNED_PARTIAL','MISALIGNED','NOT_ASSESSED','EVIDENCE_MISSING','OUT_OF_SCOPE'])
def test_noncomplete_decision_refused(state):
    s,r,a,c=inputs();s['alignment_state']=state;r['subject_sha256']=e.subject_hash(s)
    with pytest.raises(QbankError,match='ALIGNED_COMPLETE'): e.validate_decision_support(s,r,a,c)


@pytest.mark.parametrize('mutation', ['claim','packet','address','mcc','unit','unverified','no_refs','self_review','uncertain','stale'])
def test_invalid_provenance_fails_closed(mutation):
    s,r,a,c=inputs()
    if mutation=='claim': s['claim_ids']=['CLM-UNKNOWN']
    if mutation=='packet': s['source_packet_ids']=['SRC-OTHER']
    if mutation=='address': s['allocation_address_id']='SU-OTHER'
    if mutation=='mcc': s['mcc_objective_ids']=['invented']
    if mutation=='unit': s['study_unit_id']='SU-OTHER'
    if mutation=='unverified': c['CLM-X']['source_verified']=False
    if mutation=='no_refs': s['claim_ids']=[]
    if mutation=='self_review': r['reviewer_execution_id']='author'
    if mutation=='uncertain': r['verdict']='UNCERTAIN'
    if mutation!='stale': r['subject_sha256']=e.subject_hash(s)
    else: s['population']='children'
    with pytest.raises(QbankError): e.validate_decision_support(s,r,a,c)


def test_zero_scope_precedes_researched_claims():
    s,r,a,c=inputs();a['SU-X']['generation_policy']='NEVER'
    assert e.initial_address_state(a['SU-X'],['SRC-X'],c)=='OUT_OF_SCOPE'
    with pytest.raises(QbankError): e.validate_decision_support(s,r,a,c)


def test_review_must_check_every_required_claim():
    s,r,a,c=inputs();r['evidence_refs_checked']=[]
    with pytest.raises(QbankError): e.validate_decision_support(s,r,a,c)


def test_changed_claim_text_invalidates_its_review():
    s,r,a,c=inputs()
    r['claim_sha256']={k:e.subject_hash(v) for k,v in c.items()}
    c['CLM-X']['text']='Different recommendation'
    with pytest.raises(QbankError,match='claim.*hash'): e.validate_decision_support(s,r,a,c)
