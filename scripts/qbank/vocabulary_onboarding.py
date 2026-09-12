"""Reviewed new vocabulary as a separate append-only registry snapshot.

Legacy registry rows and hashes remain unchanged. New snapshots add a full
behavioral hash and explicit unit/decision bindings; they have no implicit loader.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Mapping

from .clinical_concepts import normalize_surface_form
from .errors import QbankError
from .feature_anchor_registry import (REGISTRY_FEATURE_STATES, content_sha256,
    registry_hash, supported_roles_for, _non_anchor_domains, _extension_relation)
from .onboarding_evidence import verify_review

SNAPSHOT_ID = 'FEATURE_ANCHOR_SNAPSHOT_V4'
SNAPSHOT_PATH = 'research/qgen/onboarding/feature_anchor_snapshot_v4.json'
IDENTITY_TYPES = frozenset(('SYMPTOM','DIAGNOSIS','FINDING','SYNDROME','SEVERITY',
    'TEST','TEST_RESULT','TREATMENT','INDICATION','RISK_FACTOR','PRESENTATION',
    'CONTEXT','PROPOSITION'))
CLASSIFICATIONS = frozenset(('EXISTING_CANONICAL','NORMALIZED_EXISTING',
    'NEW_CANONICAL_FEATURE','RELATED_BUT_DISTINCT','AMBIGUOUS','REJECTED'))


class VocabularyOnboardingError(QbankError):
    """An unreviewed, ambiguous or incorrectly scoped extension was attempted."""


def normalize_feature(proposal: Mapping, features: list[dict]) -> dict:
    label = normalize_surface_form(proposal['preferred_label'])
    same = [r for r in features if normalize_surface_form(r['preferred_label'])==label]
    compatible = [r for r in same if r.get('identity_type','PROPOSITION')==proposal['identity_type']
                  and r['feature_type']==proposal['feature_type']]
    if len(compatible)>1:
        classification, canonical = 'AMBIGUOUS', None
    elif compatible:
        match=compatible[0]
        classification = ('EXISTING_CANONICAL' if match['preferred_label']==proposal['preferred_label']
                          else 'NORMALIZED_EXISTING')
        canonical=match['feature_id']
    else:
        classification='RELATED_BUT_DISTINCT' if same else 'NEW_CANONICAL_FEATURE'
        canonical=None
    return {'classification':classification,'canonical_feature_id':canonical,
            'normalized_label':label,'related_feature_ids':sorted(r['feature_id'] for r in same)}


def _reviewed(proposal: dict, review: dict, catalog: dict) -> None:
    refs=proposal.get('evidence_refs')
    if not refs:
        raise VocabularyOnboardingError('new feature/anchor requires evidence')
    verify_review(proposal,review,required_refs=refs)
    for ref in refs:
        claim=catalog.get(ref)
        if not claim or not claim.get('source_verified'):
            raise VocabularyOnboardingError(f'unverified feature/anchor claim {ref}')
        if (review.get('claim_sha256') or {}).get(ref)!=content_sha256(claim):
            raise VocabularyOnboardingError(f'feature/anchor claim hash mismatch {ref}')


def verify_snapshot(snapshot: dict, expected_sha256: str) -> None:
    if not expected_sha256 or snapshot.get('content_sha256')!=expected_sha256:
        raise VocabularyOnboardingError('snapshot requires explicit expected content hash')
    body={k:v for k,v in snapshot.items() if k!='content_sha256'}
    if content_sha256(body)!=expected_sha256:
        raise VocabularyOnboardingError('snapshot content hash mismatch')
    if registry_hash(snapshot['features'],snapshot['anchor_relations'])!=snapshot['registry_hash']:
        raise VocabularyOnboardingError('snapshot registry hash mismatch')


def build_extended_snapshot(parent: dict, proposals: list[dict], reviews: dict,
                            catalog: dict, *, snapshot_id=SNAPSHOT_ID,
                            anchor_proposals=(), anchor_reviews=None) -> dict:
    if not snapshot_id or snapshot_id.upper() in {'LATEST','HEAD','CURRENT'} or snapshot_id==parent['snapshot_id']:
        raise VocabularyOnboardingError('new explicit snapshot identity required')
    if 'content_sha256' in parent:
        verify_snapshot(parent,parent['content_sha256'])
    elif registry_hash(parent['features'],parent['anchor_relations'])!=parent['registry_hash']:
        raise VocabularyOnboardingError('parent registry hash mismatch')
    features=deepcopy(parent['features']);relations=deepcopy(parent['anchor_relations'])
    scopes=deepcopy(parent.get('anchor_scope',[]))
    bindings=deepcopy(parent.get('unit_bindings',{}))
    seen_proposals=set();normalizations=[];excluded=[];approved=[]
    for p in sorted(proposals,key=lambda p:p['proposal_id']):
        pid=p['proposal_id']
        if pid in seen_proposals:raise VocabularyOnboardingError('duplicate proposal id')
        seen_proposals.add(pid)
        review=reviews.get(pid)
        if not review:raise VocabularyOnboardingError(f'missing independent review {pid}')
        if review.get('verdict') in {'REJECTED','UNCERTAIN'}:
            excluded.append({'proposal_id':pid,'verdict':review['verdict']});continue
        _reviewed(p,review,catalog)
        if (p.get('classification') not in CLASSIFICATIONS
                or p['classification'] in {'AMBIGUOUS','REJECTED'}):
            raise VocabularyOnboardingError('ambiguous or invalid feature classification')
        if p.get('identity_type') not in IDENTITY_TYPES:
            raise VocabularyOnboardingError('unknown feature identity type')
        if not p.get('study_unit_id') or not p.get('learner_decision_ids'):
            raise VocabularyOnboardingError('feature requires study-unit and decision scope')
        if not p.get('preferred_label') or not p.get('feature_id'):
            raise VocabularyOnboardingError('feature identity and label required')
        roles=supported_roles_for(p['feature_type'])
        if not roles:raise VocabularyOnboardingError('unknown clinical feature role')
        normalization=normalize_feature(p,features)
        if normalization['classification']=='AMBIGUOUS':
            raise VocabularyOnboardingError('ambiguous normalization')
        fid=normalization['canonical_feature_id']
        if fid:
            if p['classification'] not in {'EXISTING_CANONICAL','NORMALIZED_EXISTING'} or p['feature_id']!=fid:
                raise VocabularyOnboardingError('duplicate feature needs explicit reviewed reuse')
        else:
            fid=p['feature_id']
            if any(r['feature_id']==fid for r in features):
                raise VocabularyOnboardingError('feature id collision changes identity')
            if p['classification'] not in {'NEW_CANONICAL_FEATURE','RELATED_BUT_DISTINCT'}:
                raise VocabularyOnboardingError('declared reuse has no canonical identity')
            features.append({'feature_id':fid,'canonical_concept_id':fid,
                'preferred_label':p['preferred_label'],'feature_type':p['feature_type'],
                'identity_type':p['identity_type'],'allowed_states':list(REGISTRY_FEATURE_STATES),
                'supported_roles':roles,'non_anchor_in_decision_domains':_non_anchor_domains(roles),
                'provenance':{'kind':'INDEPENDENTLY_REVIEWED_ONBOARDING_EXTENSION',
                    'study_unit_id':p['study_unit_id'],'proposal_id':pid,
                    'proposal_sha256':content_sha256(p),'review_sha256':content_sha256(review),
                    'evidence_refs':sorted(p['evidence_refs'])},
                'verification_status':'EVIDENCE_VERIFIED','introduced_in_version':snapshot_id,
                'deprecated_in_version':None})
        for decision in sorted(set(p['learner_decision_ids'])):
            target=bindings.setdefault(p['study_unit_id'],{}).setdefault(decision,[])
            if fid not in target:target.append(fid);target.sort()
        normalizations.append({'proposal_id':pid,**normalization})
        approved.append(pid)
    for p in sorted(anchor_proposals,key=lambda p:p['extension_id']):
        eid=p['extension_id'];review=(anchor_reviews or {}).get(eid)
        if not review:raise VocabularyOnboardingError(f'missing anchor review {eid}')
        if review.get('verdict') in {'REJECTED','UNCERTAIN'}:
            excluded.append({'proposal_id':eid,'verdict':review['verdict']});continue
        _reviewed(p,review,catalog)
        if p.get('required_state')!='PRESENT' or not p.get('scope_opportunity_labels'):
            raise VocabularyOnboardingError('new anchors require PRESENT and explicit scope')
        decision_bindings=bindings.get(p.get('anchor_study_unit_id'),{})
        if p.get('feature_id') not in decision_bindings.get(p.get('learner_decision'),[]):
            raise VocabularyOnboardingError('anchor feature outside reviewed decision vocabulary')
        relation=_extension_relation(p,{r['feature_id']:r for r in features},introduced_in_version=snapshot_id)
        if any(r['anchor_relation_id']==relation['anchor_relation_id'] for r in relations):
            raise VocabularyOnboardingError('duplicate anchor identity')
        relation['review_sha256']=content_sha256(review)
        relations.append(relation)
        scope={'seed_id':p['seed_id'],'target_concept_id':p['target_concept_id'],
            'learner_decision':p['learner_decision'],'decision_granularity':p['decision_granularity'],
            'anchor_study_unit_id':p['anchor_study_unit_id'],'no_anchor_finding':False}
        previous=next((r for r in scopes if r['seed_id']==scope['seed_id']),None)
        if previous and any(previous.get(k)!=scope[k] for k in scope if k!='no_anchor_finding'):
            raise VocabularyOnboardingError('anchor seed identity mismatch')
        if not previous:scopes.append(scope)
        approved.append(eid)
    features.sort(key=lambda r:r['feature_id'])
    relations.sort(key=lambda r:r['anchor_relation_id'])
    scopes.sort(key=lambda r:r['seed_id'])
    snapshot={'schema_version':'2.0','snapshot_id':snapshot_id,
        'parent_snapshot_id':parent['snapshot_id'],'parent_registry_hash':parent['registry_hash'],
        'parent_content_sha256':parent.get('content_sha256',content_sha256(parent)),
        'features':features,'anchor_relations':relations,'anchor_scope':scopes,
        'unit_bindings':bindings,'feature_count':len(features),'anchor_relation_count':len(relations),
        'registry_hash':registry_hash(features,relations),'normalization_results':normalizations,
        'approved_proposal_ids':approved,'excluded_proposals':excluded,
        'legacy_inheritance_policy':'Parent rows preserved; new eligibility uses explicit unit/decision bindings',
        'proposal_input_sha256':content_sha256(sorted(proposals,key=lambda p:p['proposal_id'])),
        'review_input_sha256':content_sha256(reviews)}
    snapshot['content_sha256']=content_sha256(snapshot)
    return snapshot


def snapshot_vocabulary(snapshot: dict, unit_id: str, decision_id: str) -> dict:
    verify_snapshot(snapshot,snapshot.get('content_sha256'))
    ids=set(snapshot['unit_bindings'].get(unit_id,{}).get(decision_id,[]))
    return {r['feature_id']:{'stem_feature_id':r['feature_id'],
        'normalized_feature':r['preferred_label'],'clinical_role':r['feature_type']}
        for r in snapshot['features'] if r['feature_id'] in ids}
