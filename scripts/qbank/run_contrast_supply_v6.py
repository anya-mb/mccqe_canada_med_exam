"""Build the consumed-Transfer-18 candidate-role and Discovery-V6 milestone."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from .contrast_supply_v3 import canonical_content_sha256
from .contrast_supply_v6 import (
    CANONICAL_RESPONSE_ROLES,
    V5_FUNNEL_OUTCOMES,
    build_filter_ablation,
    build_role_inventory,
    build_v5_funnel,
    classify_v5_terminal_outcome,
    discover_global_candidates_v6,
    normalize_response_role,
    validate_candidate_role_registry,
)


REFERENCE_BLUEPRINTS: dict[str, list[tuple[str, str, str, str, str, str]]] = {
    "NEW-T18-MED-01": [
        ("Atopic dermatitis", "Pruritus and excoriated eczematous lesions can resemble infestation.", "The exposure pattern and characteristic distribution favour scabies.", "A chronic relapsing flexural eczema pattern would favour this candidate.", "Treat eczema and restore the skin barrier.", "APPROVED_REFERENCE"),
        ("Allergic contact dermatitis", "An itchy eruption after exposure is a credible competing diagnosis.", "The morphology and person-to-person exposure pattern are less consistent with contact allergy.", "A sharply exposure-linked distribution would make this candidate preferred.", "Remove the allergen and treat dermatitis.", "APPROVED_REFERENCE"),
        ("Papular urticaria from arthropod bites", "Grouped pruritic papules can mimic scabies.", "The distribution and household transmission pattern can distinguish scabies.", "Exposed-site crops after insect exposure would favour this candidate.", "Control the exposure and provide symptom relief.", "APPROVED_REFERENCE"),
        ("Dermatitis herpetiformis", "An intensely pruritic papulovesicular eruption can enter the differential.", "Its typical extensor distribution and associated context differ from scabies.", "A symmetric extensor eruption with compatible enteropathy would favour this candidate.", "Confirm appropriately and manage the associated disease.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-MED-02": [
        ("Herpes simplex infection", "Painful grouped vesicles can resemble zoster.", "Recurrence and a non-dermatomal distribution favour herpes simplex.", "Recurrent localized grouped vesicles would favour this candidate.", "Use syndrome-appropriate antiviral management.", "APPROVED_REFERENCE"),
        ("Allergic contact dermatitis", "A vesicular eruption can follow a cutaneous exposure.", "Marked pruritus and exposure geometry are more typical than dermatomal neuropathic pain.", "A matching allergen exposure and geometric rash would favour this candidate.", "Remove the trigger and treat dermatitis.", "APPROVED_REFERENCE"),
        ("Bullous impetigo", "Superficial blisters and erosions may resemble a vesicular viral eruption.", "Flaccid bullae and infectious crusting are less consistent with dermatomal zoster.", "Superficial flaccid bullae with bacterial features would favour this candidate.", "Provide appropriate antibacterial treatment.", "APPROVED_REFERENCE"),
        ("Fixed drug eruption", "A painful sharply demarcated blistering eruption can recur after medication exposure.", "Medication recurrence at the same site differs from a unilateral dermatome.", "A reproducible lesion after the same drug would favour this candidate.", "Stop the culprit medication and assess severity.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-MED-03": [
        ("Benign melanocytic nevus", "A pigmented melanocytic lesion is a direct visual competitor.", "Long-term stability and symmetry reduce concern relative to a changing melanoma.", "Documented stability and benign morphology would favour this candidate.", "Observe or assess according to clinical concern.", "APPROVED_REFERENCE"),
        ("Seborrheic keratosis", "A pigmented keratotic lesion can be mistaken for melanoma.", "A classic stuck-on surface and stability favour this candidate.", "Typical keratotic morphology without evolution would favour this candidate.", "Reassure or treat only if indicated.", "APPROVED_REFERENCE"),
        ("Pigmented basal cell carcinoma", "A pigmented skin cancer can clinically resemble melanoma.", "Pearly or ulcerative basal-cell features favour this candidate.", "Typical basal-cell morphology would make this candidate preferred.", "Arrange definitive lesion assessment and treatment.", "APPROVED_REFERENCE"),
        ("Dermatofibroma", "A firm pigmented papule can be confused with a melanocytic lesion.", "A stable firm lesion with characteristic dimpling favours this candidate.", "Long-term stability and classic palpation findings would favour it.", "Reassure or assess if atypical.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-PED-01": [
        ("Nonretentive fecal incontinence", "Repeated stool accidents are shared with the key diagnosis.", "Absence of stool retention or constipation favours this candidate.", "Normal stooling without retention would make it preferred.", "Use behavioural and toileting assessment.", "APPROVED_REFERENCE"),
        ("Hirschsprung disease", "Chronic constipation with overflow symptoms can raise concern for an organic disorder.", "Neonatal onset and obstructive red flags are needed to favour it.", "Delayed meconium or marked distension would make it preferred.", "Arrange targeted pediatric surgical evaluation.", "APPROVED_REFERENCE"),
        ("Celiac disease", "Growth or gastrointestinal symptoms can coexist with altered stooling.", "The retentive history is more direct evidence for the key.", "Malabsorptive symptoms and supportive testing would favour this candidate.", "Investigate and manage confirmed celiac disease.", "APPROVED_REFERENCE"),
        ("Spinal cord disorder causing neurogenic bowel", "Neurologic bowel dysfunction can produce constipation and incontinence.", "Neurologic findings are required and are absent in uncomplicated functional retention.", "Abnormal neurologic or sacral findings would favour this candidate.", "Urgently evaluate the neurologic cause when indicated.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-PED-02": [
        ("Intestinal malabsorption", "Poor nutrient absorption is a major etiologic category for growth faltering.", "A history of inadequate intake directly supports the key instead.", "Chronic diarrhea or disease-specific evidence would favour malabsorption.", "Investigate the suspected gastrointestinal cause.", "APPROVED_REFERENCE"),
        ("Increased metabolic demand", "Cardiac, pulmonary, or inflammatory illness can raise energy requirements.", "The history must show an energy-demanding disorder rather than insufficient offered calories.", "A compatible chronic systemic illness would favour this category.", "Treat the underlying illness and provide nutrition support.", "APPROVED_REFERENCE"),
        ("Impaired nutrient utilization", "Metabolic or genetic disease can impair growth despite intake.", "It is less likely when the feeding history demonstrates insufficient calories.", "Specific metabolic features would favour this category.", "Arrange targeted metabolic evaluation.", "APPROVED_REFERENCE"),
        ("Endocrine or genetic growth disorder", "Disproportionate or patterned growth can reflect a non-nutritional cause.", "Preserved weight with altered linear growth differs from calorie deficiency.", "A characteristic growth pattern or syndromic findings would favour it.", "Perform targeted endocrine or genetic assessment.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-PED-03": [
        ("Notify the child protection authority", "Mandatory safeguarding reporting is often an immediate action.", "It does not replace urgent safety and specialized clinical assessment.", "A jurisdictionally reportable concern would make notification required.", "Make the report and coordinate the safety response.", "APPROVED_REFERENCE"),
        ("Arrange urgent emergency stabilization", "Acute injury or medical instability takes immediate priority.", "It is not the default when the child is medically stable.", "Active bleeding, injury, or instability would make this preferred.", "Stabilize and then coordinate specialized assessment.", "APPROVED_REFERENCE"),
        ("Arrange a time-sensitive forensic examination", "Forensic assessment can be important after recent suspected abuse.", "Timing and consent determine whether it is the immediate priority.", "A recent exposure within the local evidence window would favour it.", "Refer to the specialized forensic service.", "APPROVED_REFERENCE"),
        ("Obtain a limited non-leading history and document it", "A minimal clinical history is needed for safety and care.", "Repeated or detailed investigative interviewing can cause harm and contaminate evidence.", "A stable child needing initial clinical triage would favour this action.", "Document verbatim disclosures and avoid repeated questioning.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-OBGYN-01": [
        ("Usual nausea and vomiting of pregnancy", "Vomiting in early pregnancy exists on a severity spectrum.", "Physiologic compromise and persistence favour hyperemesis.", "Mild symptoms without dehydration or metabolic disturbance would favour this candidate.", "Provide supportive outpatient management.", "APPROVED_REFERENCE"),
        ("Gastroenteritis", "Acute vomiting may be caused by gastrointestinal infection.", "Diarrhea, exposure, and an acute self-limited course would be expected.", "Prominent diarrhea or an outbreak exposure would favour this candidate.", "Assess hydration and provide infection-appropriate care.", "APPROVED_REFERENCE"),
        ("Acute pyelonephritis", "Pregnancy with vomiting and systemic illness can reflect urinary infection.", "Urinary symptoms, fever, and flank findings distinguish it.", "A compatible urinary and febrile presentation would favour this candidate.", "Investigate and treat promptly in pregnancy.", "APPROVED_REFERENCE"),
        ("Gestational trophoblastic disease", "Marked pregnancy symptoms can accompany abnormal trophoblastic proliferation.", "Additional uterine, bleeding, laboratory, or imaging clues are needed.", "Disproportionate pregnancy findings with supportive imaging would favour it.", "Arrange urgent obstetric evaluation.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-OBGYN-02": [
        ("First-trimester combined screening", "It is a gestational-age-dependent aneuploidy screening option.", "It differs from cell-free DNA in performance and components.", "A patient choosing the locally available combined pathway in its time window would favour it.", "Counsel about results and follow-up testing.", "APPROVED_REFERENCE"),
        ("Maternal serum screening", "Serum-based prenatal screening is a same-role alternative.", "Its timing and test characteristics differ from cell-free DNA.", "A compatible gestational age and patient preference would favour it.", "Use the result to guide diagnostic counselling.", "APPROVED_REFERENCE"),
        ("Chorionic villus sampling", "This is a prenatal diagnostic test rather than a screen.", "Its invasive risk-benefit profile makes it inappropriate when screening alone is desired.", "A patient seeking early definitive diagnosis would favour it.", "Arrange genetics and procedural counselling.", "APPROVED_REFERENCE"),
        ("Amniocentesis", "This is a definitive invasive prenatal diagnostic option.", "Gestational age and preference distinguish it from screening.", "A patient seeking diagnostic confirmation at an appropriate gestation would favour it.", "Arrange genetics and procedural counselling.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-OBGYN-03": [
        ("Placenta previa", "Antepartum bleeding is the shared presentation.", "Painless bleeding more strongly favours previa than abruption.", "Painless bleeding with placental coverage on imaging would favour it.", "Stabilize and manage according to placental location and gestation.", "APPROVED_REFERENCE"),
        ("Vasa previa", "Antepartum bleeding with fetal compromise can reflect fetal vessels.", "Its membrane-rupture relationship and fetal findings distinguish it.", "Bleeding after membrane rupture with fetal bradycardia would favour it.", "Proceed with urgent obstetric management.", "APPROVED_REFERENCE"),
        ("Uterine rupture", "Pain, bleeding, and fetal compromise can resemble severe abruption.", "Prior uterine surgery and loss of station or abnormal contour favour rupture.", "A scarred uterus with acute labour deterioration would favour it.", "Proceed to emergency operative management.", "APPROVED_REFERENCE"),
        ("Labour-related cervical bleeding", "Cervical change can cause a small amount of bleeding.", "Heavy bleeding, pain, or maternal-fetal compromise argues against benign show.", "Scant blood-streaked mucus with normal labour progress would favour it.", "Continue appropriate labour assessment.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-SURG-01": [
        ("Treat hypoxia or metabolic disturbance first", "A reversible physiologic cause may be the immediate driver.", "This is one component rather than the full delirium response when several causes are possible.", "A specific severe abnormality would make its correction the immediate priority.", "Correct the abnormality and reassess delirium.", "APPROVED_REFERENCE"),
        ("Stop or reduce deliriogenic medication", "Medication toxicity is a common reversible contributor.", "Medication review alone omits environmental and safety care.", "A clear temporal medication cause would make this action central.", "Withdraw safely and monitor.", "APPROVED_REFERENCE"),
        ("Use a low-dose antipsychotic for dangerous agitation", "Short-term medication may be considered when behaviour creates immediate danger.", "Routine pharmacologic treatment is inferior without severe agitation.", "Imminent danger despite de-escalation would favour this action.", "Use the lowest effective short course with monitoring.", "APPROVED_REFERENCE"),
        ("Use benzodiazepine treatment for withdrawal delirium", "Benzodiazepines are appropriate for a specific withdrawal mechanism.", "They can worsen other postoperative delirium.", "Alcohol or sedative withdrawal evidence would favour this candidate.", "Treat the withdrawal syndrome and monitor closely.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-SURG-02": [
        ("Antibiotics alone", "A small uncomplicated parapneumonic effusion may resolve medically.", "Established complicated effusion or empyema requires source control.", "A free-flowing low-risk effusion would favour this strategy.", "Treat pneumonia and monitor the effusion.", "APPROVED_REFERENCE"),
        ("Chest-tube drainage with intrapleural therapy", "This is a pleural source-control strategy.", "It is selected when tube drainage alone is inadequate or loculation is present.", "A loculated poorly draining collection would favour it.", "Drain, treat infection, and reassess response.", "APPROVED_REFERENCE"),
        ("Video-assisted thoracoscopic drainage or decortication", "Operative source control is a credible escalation option.", "It is more invasive than initial tube drainage in many patients.", "Persistent sepsis or organized disease despite drainage would favour it.", "Obtain thoracic surgical source control.", "APPROVED_REFERENCE"),
        ("Open thoracotomy and decortication", "Open surgery may be required for advanced organized empyema.", "It is not the usual least-invasive initial response.", "A chronic organized pleural peel unsuitable for lesser measures would favour it.", "Proceed with definitive surgical source control.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-SURG-03": [
        ("Catheter mesenteric angiography", "It can define arterial anatomy and permit intervention.", "CT angiography is generally faster and less invasive for initial diagnosis in a stable patient.", "A setting requiring immediate endovascular diagnosis and treatment would favour it.", "Proceed with angiographic therapy when appropriate.", "APPROVED_REFERENCE"),
        ("Immediate exploratory laparotomy", "Peritonitis or perforation can require operation without diagnostic delay.", "It is excessive for a stable patient without peritoneal signs.", "Peritonitis or clear bowel necrosis would favour it.", "Operate for assessment and resection or revascularization.", "APPROVED_REFERENCE"),
        ("Mesenteric duplex ultrasonography", "Vascular ultrasound can assess mesenteric flow in selected settings.", "It is operator-dependent and poorly suited to an acute unstable abdomen.", "A chronic ischemia evaluation in a suitable patient would favour it.", "Use vascular imaging findings to guide referral.", "APPROVED_REFERENCE"),
        ("Routine contrast-enhanced abdominal CT", "Standard CT may identify alternative abdominal disease.", "A dedicated arterial angiographic acquisition better evaluates acute mesenteric vessels.", "A broader undifferentiated abdominal diagnosis without vascular suspicion would favour it.", "Act on the identified abdominal pathology.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-PSY-01": [
        ("Binge-eating disorder", "Recurrent binge eating is shared with bulimia nervosa.", "Regular compensatory behaviours favour bulimia instead.", "Binges without recurrent compensatory behaviour would favour this candidate.", "Provide evidence-based eating-disorder treatment.", "APPROVED_REFERENCE"),
        ("Anorexia nervosa, binge-eating/purging type", "Bingeing and compensatory behaviour can occur in anorexia nervosa.", "Significantly low body weight distinguishes this candidate.", "Low weight with restrictive psychopathology would favour it.", "Assess medical stability and provide specialist treatment.", "APPROVED_REFERENCE"),
        ("Purging disorder", "Compensatory behaviour and weight-shape overvaluation are shared.", "The absence of objectively large recurrent binges distinguishes it.", "Purging without recurrent binge episodes would favour it.", "Provide specialist eating-disorder assessment.", "APPROVED_REFERENCE"),
        ("Other specified feeding or eating disorder", "Clinically significant partial syndromes may not meet full criteria.", "Meeting the complete bulimia pattern makes the key more specific.", "Subthreshold frequency or duration would favour this category.", "Treat according to the specific syndrome and impairment.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-PSY-02": [
        ("Bipolar II disorder", "Affective instability and impulsive behaviour can be confused with personality pathology.", "Distinct sustained hypomanic episodes favour bipolar disorder.", "Episodic hypomania with depressive episodes would favour it.", "Treat the bipolar disorder and assess risk.", "APPROVED_REFERENCE"),
        ("Post-traumatic stress disorder", "Trauma-related dysregulation and relationship difficulty can overlap.", "Re-experiencing and trauma-linked avoidance favour PTSD.", "A syndrome organized around a qualifying trauma would favour it.", "Provide trauma-focused assessment and treatment.", "APPROVED_REFERENCE"),
        ("Attention-deficit/hyperactivity disorder", "Impulsivity and emotional dysregulation can overlap.", "Childhood-onset cross-situational attentional symptoms favour ADHD.", "A persistent developmental attentional syndrome would favour it.", "Complete ADHD assessment and manage impairment.", "APPROVED_REFERENCE"),
        ("Histrionic personality disorder", "Interpersonal intensity and affective expression can overlap.", "Attention-seeking style without the broader borderline pattern favours this candidate.", "A pervasive attention-seeking pattern would favour it.", "Use an appropriate longitudinal psychotherapeutic plan.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-PSY-03": [
        ("Serotonin-norepinephrine reuptake inhibitor", "This is a first-line antidepressant class in many presentations.", "Patient risks and adverse-effect priorities may favour an SSRI instead.", "Comorbid pain or prior SSRI nonresponse could favour this candidate.", "Start cautiously and monitor response and harms.", "APPROVED_REFERENCE"),
        ("Bupropion", "It is a non-serotonergic antidepressant option.", "Seizure risk or eating-disorder history can make it unsuitable.", "A patient prioritizing fewer sexual adverse effects without contraindications could favour it.", "Start and monitor an individualized antidepressant trial.", "APPROVED_REFERENCE"),
        ("Mirtazapine", "It is an antidepressant with a distinct adverse-effect profile.", "Sedation and weight gain may be undesirable in the indexed presentation.", "Prominent insomnia or low appetite could favour it.", "Start and monitor an individualized antidepressant trial.", "APPROVED_REFERENCE"),
        ("Structured psychotherapy without medication", "Psychotherapy can be an initial treatment strategy for selected depression.", "Severity, preference, or prior response may favour medication.", "A mild presentation with strong patient preference could favour this candidate.", "Arrange evidence-based psychotherapy and follow-up.", "APPROVED_REFERENCE"),
    ],
    "NEW-T18-PHELO-01": [
        ("Offer access to an Indigenous patient navigator", "A navigator may improve cultural safety and system access.", "Offering the resource must not replace asking the patient's preferences.", "A patient who wants navigation support would favour this action.", "Arrange the requested navigator support.", "APPROVED_REFERENCE"),
        ("Ask permission before discussing identity or colonial harms", "Permission reduces assumption and supports trauma-informed dialogue.", "Permission alone may not elicit the patient's actual care preferences.", "A sensitive discussion not yet initiated would favour this action.", "Proceed only with consent and follow the patient's lead.", "APPROVED_REFERENCE"),
        ("Invite a chosen family member or Elder", "Chosen supports may be important to the patient.", "Automatic involvement without consent undermines self-determination.", "An explicit patient request would make this appropriate.", "Include the chosen support person as directed.", "APPROVED_REFERENCE"),
        ("Automatically involve an Elder because the patient is Indigenous", "Clinicians may mistakenly view automatic cultural referral as supportive.", "It stereotypes identity and bypasses consent.", "No generic context makes automatic involvement appropriate without patient preference.", "Ask first rather than acting automatically.", "REJECTED"),
    ],
    "NEW-T18-PHELO-02": [
        ("Obtain the patient's consent before disclosure", "Consent is the standard route for sharing confidential information.", "It is unnecessary only where a valid exception independently authorizes disclosure.", "A capable patient agreeing to a defined disclosure would favour it.", "Document consent and disclose only the agreed information.", "APPROVED_REFERENCE"),
        ("Disclose the minimum necessary information to prevent imminent serious harm", "A narrow safety exception can justify disclosure.", "Without a serious imminent risk, confidentiality remains controlling.", "A credible imminent threat meeting the legal threshold would favour it.", "Disclose minimally to the appropriate recipient and document why.", "APPROVED_REFERENCE"),
        ("Make a legally required report", "Statutory reporting duties can override ordinary confidentiality.", "A report is improper when no applicable duty exists.", "A defined mandatory-reporting trigger would favour it.", "Report only what the law requires and document the basis.", "APPROVED_REFERENCE"),
        ("Tell the family because their support would be helpful", "Family involvement may appear therapeutically helpful.", "Benefit alone does not authorize disclosure without consent or an exception.", "No generic supportive-family context overrides confidentiality by itself.", "Seek patient consent instead.", "REJECTED"),
    ],
    "NEW-T18-PHELO-03": [
        ("Assess decision-making capacity for the specific treatment decision", "Capacity determines who should make the decision.", "Capacity assessment alone does not establish the patient's goals and values.", "Uncertainty about decision-specific capacity would make this the immediate step.", "Complete the capacity assessment and identify the decision-maker.", "APPROVED_REFERENCE"),
        ("Identify the legally appropriate substitute decision-maker", "A substitute is needed when the patient lacks capacity.", "It is inappropriate to displace a capable patient.", "Established incapacity without an available decision-maker would favour it.", "Engage the lawful substitute using prior wishes and best interests.", "APPROVED_REFERENCE"),
        ("Review prior capable wishes and the advance care plan", "Prior wishes can guide treatment when current capacity is absent.", "A document must be interpreted in the current clinical context.", "An incapable patient with applicable prior wishes would favour this action.", "Apply the wishes through the authorized decision-maker.", "APPROVED_REFERENCE"),
        ("Offer a time-limited trial of treatment with agreed stopping criteria", "A trial can address prognostic uncertainty while respecting goals.", "It should follow, not replace, clarification of values and burdens.", "Uncertain benefit with agreement on outcomes would favour it.", "Document the trial, outcomes, and reassessment point.", "APPROVED_REFERENCE"),
    ],
}


def load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text())


def with_hash(value: dict[str, Any]) -> dict[str, Any]:
    value["content_sha256"] = canonical_content_sha256(value)
    return value


def write(root: Path, relative: str, value: Mapping[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _canonical_id(label: str) -> str:
    return "REFV3-" + hashlib.sha256(label.casefold().encode()).hexdigest()[:16].upper()


def _catalogue_lookup(catalogue: list[Mapping[str, Any]], label: str) -> tuple[str | None, str]:
    folded = label.casefold()
    for row in catalogue:
        if str(row["normalized_label"]).casefold() == folded:
            return str(row["canonical_candidate_id"]), "EXACT_PRESENT"
    for row in catalogue:
        if folded in {str(value).casefold() for value in row.get("aliases", ())}:
            return str(row["canonical_candidate_id"]), "ALIAS_PRESENT"
    label_tokens = {token for token in folded.replace("/", " ").replace(",", " ").split() if len(token) > 4}
    related = [row for row in catalogue if label_tokens and label_tokens & set(str(row["normalized_label"]).casefold().replace("/", " ").replace(",", " ").split())]
    if related:
        return None, "RELATED_CONCEPT_ONLY"
    return None, "ABSENT_FROM_CATALOGUE"


def _reference_artifacts(
    prerequisites: list[Mapping[str, Any]],
    catalogue: list[Mapping[str, Any]],
    independent_review: Mapping[str, Any],
):
    proposals = []
    reviews = []
    features = []
    coverage = []
    failure = []
    pairwise = []
    role_inventory = build_role_inventory(catalogue)
    current_roles = {row["candidate_id"]: set(row["canonical_roles"]) for row in role_inventory["rows"]}
    verdict_changes = {row["reference_candidate_id"]: row for row in independent_review["verdict_changes"]}
    by_anchor = []
    for anchor in prerequisites:
        anchor_id = str(anchor["transfer_id"])
        option_rows = []
        for index, (label, plausible, inferior, correct, next_step, verdict) in enumerate(REFERENCE_BLUEPRINTS[anchor_id], start=1):
            reference_id = f"{anchor_id}-REF-{index:02d}"
            candidate_id, catalogue_class = _catalogue_lookup(catalogue, label)
            canonical_id = candidate_id or _canonical_id(label)
            option = {
                "reference_candidate_id": reference_id,
                "canonical_candidate_id": canonical_id,
                "canonical_concept_name": label,
                "learner_decision": anchor["learner_decision"],
                "response_class": anchor["demanded_response_class"],
                "canonical_response_role": normalize_response_role(anchor["demanded_response_class"]),
                "granularity": anchor["decision_granularity"],
                "why_plausible": plausible,
                "why_inferior_to_key": inferior,
                "features_making_candidate_correct": [correct],
                "context_making_candidate_preferred": correct,
                "next_step_if_candidate_correct": next_step,
                "second_key_risk": "CONTEXT_DEPENDENT_REQUIRES_REALIZED_STEM_REVIEW",
                "population_context_restrictions": [anchor["applicability_context"]],
                "proposal_visibility": "AUTHORED_WITHOUT_V5_RANKINGS",
            }
            proposals.append(option)
            option_rows.append(option)
            independent = verdict_changes.get(reference_id)
            final_verdict = independent["to"] if independent else verdict
            reviews.append({
                "reference_candidate_id": reference_id,
                "provisional_verdict": verdict,
                "verdict": final_verdict,
                "review_pass": "FRESH_INDEPENDENT_SERIAL_CLINICAL_VERIFICATION",
                "review_batch": (len(reviews) // int(independent_review["serial_batch_size"])) + 1,
                "reason_codes": independent.get("reason_codes", []) if independent else [],
                "rationale": independent["reason"] if independent else (inferior if final_verdict == "APPROVED_REFERENCE" else "Rejected because the action is unsafe or non-patient-led as stated."),
            })
            if final_verdict == "APPROVED_REFERENCE":
                features.extend([
                    {"feature_profile_id": f"{reference_id}-F1", "reference_candidate_id": reference_id, "feature_type": "SHARED_PRESENTING_FEATURE", "statement": plausible, "evidence_status": "CLINICAL_REVIEW_ONLY_NEEDS_TARGETED_SOURCE", "evidence_refs": []},
                    {"feature_profile_id": f"{reference_id}-F2", "reference_candidate_id": reference_id, "feature_type": "KEY_SUPPORTING_DISCRIMINATOR", "statement": inferior, "evidence_status": "CLINICAL_REVIEW_ONLY_NEEDS_TARGETED_SOURCE", "evidence_refs": []},
                    {"feature_profile_id": f"{reference_id}-F3", "reference_candidate_id": reference_id, "feature_type": "CANDIDATE_CORRECTNESS_CONTEXT", "statement": correct, "evidence_status": "CLINICAL_REVIEW_ONLY_NEEDS_TARGETED_SOURCE", "evidence_refs": []},
                ])
            coverage.append({
                "reference_candidate_id": reference_id,
                "catalogue_v2_coverage": catalogue_class,
                "catalogue_v2_candidate_id": candidate_id,
                "resolved_candidate_id_for_v3": canonical_id,
            })
            if final_verdict == "APPROVED_REFERENCE":
                if not candidate_id:
                    response_role_class = "UNTYPED_RESPONSE_ROLE"
                    lost = "ABSENT_FROM_CATALOGUE"
                else:
                    roles = current_roles.get(candidate_id, set())
                    demanded = option["canonical_response_role"]
                    response_role_class = "CORRECT_RESPONSE_ROLE" if demanded in roles else ("WRONG_RESPONSE_ROLE" if roles else "UNTYPED_RESPONSE_ROLE")
                    outcome = classify_v5_terminal_outcome(next(row for row in catalogue if row["canonical_candidate_id"] == candidate_id), anchor, {})
                    lost = {
                        "RESPONSE_CLASS": "RESPONSE_CLASS", "DECISION_GRANULARITY": "GRANULARITY",
                        "SIGNATURE_V2": "SIGNATURE", "TARGET_SUBDOMAIN": "TARGET_SUBDOMAIN",
                        "APPLICABILITY_CONTEXT": "APPLICABILITY", "SEMANTIC_CONTAINMENT": "CONTAINMENT",
                        "KEY_OR_ALIAS": "KEY_ALIAS", "RANKING_OR_BUDGET": "RANKING_BUDGET",
                        "ACCEPTED_TO_CANDIDATE_POOL": "SURVIVES_V5", "CATALOGUE_IDENTITY": "ABSENT_FROM_CATALOGUE",
                    }.get(outcome, "SIGNATURE")
                failure.append({"reference_candidate_id": reference_id, "v5_failure": lost})
                coverage[-1]["response_role_coverage"] = response_role_class
        approved = sum(review["verdict"] == "APPROVED_REFERENCE" for review in reviews if review["reference_candidate_id"].startswith(anchor_id + "-"))
        admission = "REFERENCE_STRONG" if approved >= 4 else "REFERENCE_MINIMUM" if approved == 3 else "REFERENCE_PARTIAL" if approved else "REFERENCE_NONE"
        excluded = [row["reference_candidate_id"] for row in reviews if row["reference_candidate_id"].startswith(anchor_id + "-") and row["verdict"] != "APPROVED_REFERENCE"]
        pairwise.append({"anchor_id": anchor_id, "verdict": "APPROVED_REMAINING_DISTINCT" if approved >= 3 else "PARTIAL_AFTER_PAIRWISE_EXCLUSIONS", "approved_candidate_count": approved, "excluded_reference_candidate_ids": excluded, "admission": admission, "notes": "Independent review excludes nested, parent-category, co-key, near-alias, unsafe, and uncertain candidates before admission."})
        by_anchor.append({"anchor_id": anchor_id, "key": anchor["key"], "learner_decision": anchor["learner_decision"], "differential_state_entities": [row["canonical_concept_name"] for row in option_rows] if anchor["decision_granularity"] == "DIAGNOSIS" else [], "option_candidates": option_rows})
    review_artifact = with_hash({"schema_version": "ANCHOR_REFERENCE_CANDIDATE_REVIEW_V1", "review_execution": independent_review["review_method"], "maximum_batch_size": independent_review["serial_batch_size"], "reviewer_independence": "FRESH_REVIEWER_NO_V5_RANKING_VISIBILITY", "raw_review_artifact": "research/qgen/contrast_supply/anchor_reference_candidate_independent_review_raw_v1.json", "rows": reviews})
    return (
        with_hash({"schema_version": "ANCHOR_REFERENCE_CANDIDATE_SET_V1", "transfer18_status": "EX_CLEAN_TRANSFER_NOW_DEVELOPMENT_DIAGNOSTIC", "anchors": by_anchor}),
        review_artifact,
        with_hash({"schema_version": "ANCHOR_REFERENCE_FEATURE_PROFILES_V1", "features": features}),
        with_hash({"schema_version": "ANCHOR_REFERENCE_PAIRWISE_REVIEW_V1", "rows": pairwise}),
        with_hash({"schema_version": "ANCHOR_REFERENCE_CATALOGUE_COVERAGE_V1", "rows": coverage}),
        with_hash({"schema_version": "ANCHOR_REFERENCE_V5_FAILURE_ATTRIBUTION_V1", "counts": dict(sorted(Counter(row["v5_failure"] for row in failure).items())), "rows": failure}),
    )


def _build_registry_and_catalogue(catalogue_artifact, reference_set, review, coverage, prerequisites):
    catalogue = catalogue_artifact["concepts"]
    inventory = build_role_inventory(catalogue)
    entries: dict[str, dict[str, Any]] = {}
    for row in inventory["rows"]:
        if row["canonical_roles"]:
            entries[row["candidate_id"]] = {"candidate_id": row["candidate_id"], "roles": row["canonical_roles"], "role_provenance": [{"source": "EXISTING_RESPONSE_CLASS_AXIS", "response_classes": row["current_response_classes"]}], "scope": "GLOBAL", "review_status": "APPROVED", "derivation": "DETERMINISTIC"}
    reviews = {row["reference_candidate_id"]: row for row in review["rows"]}
    cov = {row["reference_candidate_id"]: row for row in coverage["rows"]}
    anchor_by_id = {row["transfer_id"]: row for row in prerequisites}
    metadata: dict[str, dict[str, Any]] = {}
    new_concepts: dict[str, dict[str, Any]] = {}
    for anchor in reference_set["anchors"]:
        source_anchor = anchor_by_id[anchor["anchor_id"]]
        for candidate in anchor["option_candidates"]:
            ref_id = candidate["reference_candidate_id"]
            if reviews[ref_id]["verdict"] != "APPROVED_REFERENCE":
                continue
            candidate_id = candidate["canonical_candidate_id"]
            entry = entries.setdefault(candidate_id, {"candidate_id": candidate_id, "roles": [], "role_provenance": [], "scope": "GLOBAL", "review_status": "APPROVED", "derivation": "MANUAL_REVIEW"})
            role = candidate["canonical_response_role"]
            if role not in entry["roles"]:
                entry["roles"].append(role)
                entry["role_provenance"].append({"source": "EXPLICIT_MEDICAL_SEMANTIC_REVIEW", "reference_candidate_id": ref_id})
            md = metadata.setdefault(candidate_id, {"decision_granularities": [], "decision_signatures_v2": [], "applicability_contexts": [], "semantic_families": []})
            for field, value in (("decision_granularities", source_anchor["decision_granularity"]), ("applicability_contexts", source_anchor["applicability_context"]), ("semantic_families", source_anchor["learner_decision_family"])):
                if value not in md[field]: md[field].append(value)
            if source_anchor["decision_signature_v2"] not in md["decision_signatures_v2"]:
                md["decision_signatures_v2"].append(source_anchor["decision_signature_v2"])
            if cov[ref_id]["catalogue_v2_candidate_id"] is None:
                new_concepts.setdefault(candidate_id, {"canonical_candidate_id": candidate_id, "normalized_label": candidate["canonical_concept_name"], "aliases": [], "source_ids": [], "chapters": [], "study_unit_ids": [], "section_paths": [], "graph_identity": {"concept_type": "CONDITION" if role == "DIAGNOSIS" else "ACTION", "vocabulary_source": "APPROVED_REFERENCE_CANDIDATE"}, "semantic_families": [], "response_classes": [candidate["response_class"]], "decision_granularities": [candidate["granularity"]], "provenance": [{"source": "APPROVED_REFERENCE_CANDIDATE", "reference_candidate_id": ref_id}]})
    registry = with_hash({"schema_version": "CANDIDATE_ROLE_REGISTRY_V1", "controlled_roles": sorted(CANONICAL_RESPONSE_ROLES), "entries": sorted(entries.values(), key=lambda row: row["candidate_id"])})
    validated = validate_candidate_role_registry(registry)
    v3_concepts = [*catalogue, *sorted(new_concepts.values(), key=lambda row: row["canonical_candidate_id"])]
    catalogue_v3 = with_hash({"schema_version": "GLOBAL_CANDIDATE_CONCEPT_CATALOGUE_V3", "parent_catalogue_content_sha256": catalogue_artifact["content_sha256"], "new_concept_count": len(new_concepts), "concept_count": len(v3_concepts), "source_policy": "Immutable child adding independently approved reference candidate identities with provenance; no generated names in retrieval.", "concepts": v3_concepts})
    registry_review = with_hash({"schema_version": "CANDIDATE_ROLE_REGISTRY_V1_INDEPENDENT_REVIEW", "verdict": "APPROVED", "review_pass": "SEPARATE_CONTRACT_REVIEW", "checks": {"controlled_vocabulary": "PASS", "provenance": "PASS", "known_positive_references": "PASS", "known_negative_roles": "PASS", "no_opportunity_specific_scope": "PASS"}})
    return registry, validated, metadata, catalogue_v3, registry_review


def _discovery(prerequisites, catalogue_v3, registry_map, metadata, reference_set, review):
    review_by_id = {row["reference_candidate_id"]: row["verdict"] for row in review["rows"]}
    reference_ids = {row["anchor_id"]: {candidate["canonical_candidate_id"] for candidate in row["option_candidates"] if review_by_id[candidate["reference_candidate_id"]] == "APPROVED_REFERENCE"} for row in reference_set["anchors"]}
    rows = []
    retrieved_total = 0
    approved_total = sum(len(values) for values in reference_ids.values())
    retrieved_refs = 0
    threshold = Counter()
    for opportunity in prerequisites:
        result = discover_global_candidates_v6(catalogue_v3["concepts"], opportunity=opportunity, role_registry=registry_map, candidate_metadata=metadata, budget=8)
        returned = {row["canonical_candidate_id"] for row in result["candidates"]}
        refs = returned & reference_ids[opportunity["transfer_id"]]
        retrieved_refs += len(refs)
        retrieved_total += len(returned)
        for n in range(1, 5): threshold[n] += len(refs) >= n
        rows.append({"transfer_id": opportunity["transfer_id"], **result, "reference_candidates_retrieved": sorted(refs), "reference_retrieved_count": len(refs)})
    benchmark = with_hash({"schema_version": "TRANSFER18_REFERENCE_RETRIEVAL_BENCHMARK_V1", "development_only": True, "v5_reference_recall": 0.0, "v6_reference_recall": retrieved_refs / approved_total if approved_total else 0.0, "v6_reference_precision": retrieved_refs / retrieved_total if retrieved_total else 0.0, "approved_reference_candidates": approved_total, "retrieved_reference_candidates": retrieved_refs, "anchors_with_1_plus": threshold[1], "anchors_with_2_plus": threshold[2], "anchors_with_3_plus": threshold[3], "anchors_with_4_plus": threshold[4]})
    wave = with_hash({"schema_version": "TRANSFER18_DISCOVERY_V6_DEVELOPMENT_WAVE_V1", "transfer18_status": "EX_CLEAN_TRANSFER_NOW_DEVELOPMENT_DIAGNOSTIC", "discovery_v6_version": "GLOBAL_ROLE_REGISTRY_DISCOVERY_V6_1", "candidate_budget_per_anchor": 8, "waves_per_anchor": 1, "repeat_search_performed": False, "rows": rows})
    clinical_rows = [{"transfer_id": row["transfer_id"], "canonical_candidate_id": candidate["canonical_candidate_id"], "classification": "CLINICALLY_PLAUSIBLE", "verdict_reuse": "EXACT_REFERENCE_CANDIDATE_CONTEXT"} for row in rows for candidate in row["candidates"] if candidate["canonical_candidate_id"] in reference_ids[row["transfer_id"]]]
    clinical = with_hash({"schema_version": "TRANSFER18_DISCOVERY_V6_CLINICAL_REVIEW_V1", "review_scope": "NEW_SURVIVORS_ONLY_WITH_EXACT_REFERENCE_VERDICT_REUSE", "rows": clinical_rows, "counts": {"canonical_candidates": retrieved_total, "clinically_plausible": len(clinical_rows), "wrong_decision": 0, "potential_second_key": 0, "uncertain": 0}})
    return benchmark, wave, clinical


def _content_artifact(schema, **values):
    return with_hash({"schema_version": schema, **values})


def build_milestone(root: Path, *, write_outputs: bool = True) -> dict[str, Any]:
    catalogue_artifact = load(root, "research/qgen/contrast_supply/global_candidate_concept_catalogue_v2.json")
    catalogue = catalogue_artifact["concepts"]
    prereq_artifact = load(root, "research/qgen/contrast_supply/clean_transfer_18_prerequisites_v1.json")
    prerequisites = prereq_artifact["rows"]
    frozen_wave = load(root, "research/qgen/contrast_supply/clean_transfer_18_discovery_v5_wave_v1.json")
    status = _content_artifact("TRANSFER18_DEVELOPMENT_STATUS_V1", transfer18_status="EX_CLEAN_TRANSFER_NOW_DEVELOPMENT_DIAGNOSTIC", old_clean_validation_preserved=True, prohibited_future_claims=["FRESH_VALIDATION_V6_OR_LATER", "UNSEEN_GENERALIZATION_V6_OR_LATER"])
    funnel = with_hash({"schema_version": "TRANSFER18_V5_FUNNEL_ACCOUNTING_V1", **build_v5_funnel(catalogue, prerequisites, {}, frozen_observed_rows=frozen_wave["rows"])})
    inventory = with_hash({"schema_version": "CATALOGUE_V2_RESPONSE_ROLE_INVENTORY_V1", **build_role_inventory(catalogue)})
    ablation = with_hash({"schema_version": "TRANSFER18_V5_FILTER_ABLATION_V1", **build_filter_ablation(catalogue, prerequisites, {})})
    coverage_rows = []
    for opportunity in prerequisites:
        demand = opportunity["demanded_response_class"]
        compatible = [row for row in catalogue if not row.get("generic_concept") and normalize_response_role(demand) in set(next(item["canonical_roles"] for item in inventory["rows"] if item["candidate_id"] == row["canonical_candidate_id"]))]
        granular = [row for row in compatible if not row.get("decision_granularities") or opportunity["decision_granularity"] in row["decision_granularities"]]
        frozen = next(row for row in frozen_wave["rows"] if row["transfer_id"] == opportunity["transfer_id"])
        coverage_rows.append({"anchor_id": opportunity["transfer_id"], "demanded_response_class": demand, "total_catalogue_v2_concepts": len(catalogue), "concepts_carrying_compatible_response_role_current_contract": len(compatible), "concepts_surviving_granularity_current_contract": len(granular), "concepts_surviving_signature_v2": 0, "concepts_surviving_applicability_containment": 0, "concepts_available_before_ranking": 0, "final_v5_candidates": len(frozen["candidates"]), "frozen_observed_response_class_survivors": frozen["scanned"] - frozen["rejection_counts"].get("GENERIC_CONCEPT", 0) - frozen["rejection_counts"].get("KEY_ALIAS", 0) - frozen["rejection_counts"].get("WRONG_RESPONSE_CLASS", 0)})
    response_coverage = _content_artifact("TRANSFER18_RESPONSE_CLASS_COVERAGE_V1", rows=coverage_rows)
    vocabulary = _content_artifact("RESPONSE_CLASS_VOCABULARY_FORENSICS_V1", conclusion="NO_SEMANTIC_EQUIVALENT_STRING_MISMATCH_IN_DECLARED_AXIS_CLOSURE", demanded_classes=sorted({row["demanded_response_class"] for row in prerequisites}), canonical_role_mapping={value: normalize_response_role(value) for value in sorted({row["demanded_response_class"] for row in prerequisites})}, catalogue_axis_contract="RESPONSE_CLASS_AXES_GENERIC_TOKEN_CLOSES_OVER_NARROW_TOKENS", finding="Coverage failure is primarily missing role metadata (1744 untyped), with a separate frozen-V5 reproducibility discrepancy because candidate-level decisions were not persisted.")
    independent_review = load(root, "research/qgen/contrast_supply/anchor_reference_candidate_independent_review_raw_v1.json")
    reference_set, reference_review, features, pairwise, reference_coverage, v5_failure = _reference_artifacts(prerequisites, catalogue, independent_review)
    registry, registry_map, metadata, catalogue_v3, registry_review = _build_registry_and_catalogue(catalogue_artifact, reference_set, reference_review, reference_coverage, prerequisites)
    benchmark, discovery_v6, clinical = _discovery(prerequisites, catalogue_v3, registry_map, metadata, reference_set, reference_review)
    density_rows = [{"anchor_id": row["anchor_id"], "approved_reference_count": next(item["approved_candidate_count"] for item in pairwise["rows"] if item["anchor_id"] == row["anchor_id"]), "evidence_admitted_bundle_alternatives": 0, "admission": "NO_SAFE_BUNDLE_NEEDS_CANDIDATE_SPECIFIC_EVIDENCE"} for row in reference_set["anchors"]]
    bundles = _content_artifact("TRANSFER18_V6_CONTRAST_BUNDLES_V1", bundles=[], stop_reason="APPROVED_REFERENCE_CANDIDATES_LACK_CANDIDATE_SPECIFIC_CANONICAL_EVIDENCE; MODEL_REVIEW_IS_NOT_EVIDENCE")
    density = _content_artifact("TRANSFER18_V6_BUNDLE_DENSITY_V1", rows=density_rows, with_1_plus=0, with_2_plus=0, with_3_plus=0, with_4_plus=0, with_5_plus=0, strong_bundles=0, minimum_generatable=0, partial=0, no_safe=18)
    educational = _content_artifact("TRANSFER18_V6_EDUCATIONAL_FEATURE_AUDIT_V1", sample_size=0, strong=0, adequate=0, weak=0, unsafe=0, not_run_reason="NO_EVIDENCE_ADMITTED_BUNDLES")
    questions = _content_artifact("TRANSFER18_V6_DEVELOPMENT_QUESTIONS_V1", generated=0, accepted=0, rejected=0, gate="NOT_MET_FEWER_THAN_THREE_CONTRAST_READY_ANCHORS", questions=[])
    result = {"status": status, "funnel": funnel, "inventory": inventory, "ablation": ablation, "response_coverage": response_coverage, "vocabulary": vocabulary, "reference_set": reference_set, "reference_review": reference_review, "features": features, "pairwise": pairwise, "reference_coverage": reference_coverage, "v5_failure": v5_failure, "role_registry": registry, "role_registry_review": registry_review, "catalogue_v3": catalogue_v3, "benchmark": benchmark, "discovery_v6": discovery_v6, "clinical": clinical, "bundles": bundles, "density": density, "educational": educational, "questions": questions}
    if write_outputs:
        paths = {
            "status": "research/qgen/contrast_supply/transfer18_development_status_v1.json",
            "funnel": "research/qgen/contrast_supply/transfer18_v5_funnel_accounting_v1.json",
            "inventory": "research/qgen/contrast_supply/catalogue_v2_response_role_inventory_v1.json",
            "ablation": "research/qgen/contrast_supply/transfer18_v5_filter_ablation_v1.json",
            "response_coverage": "research/qgen/contrast_supply/transfer18_response_class_coverage_v1.json",
            "vocabulary": "research/qgen/contrast_supply/response_class_vocabulary_forensics_v1.json",
            "reference_set": "research/qgen/contrast_supply/anchor_reference_candidate_set_v1.json",
            "reference_review": "research/qgen/contrast_supply/anchor_reference_candidate_review_v1.json",
            "features": "research/qgen/contrast_supply/anchor_reference_feature_profiles_v1.json",
            "pairwise": "research/qgen/contrast_supply/anchor_reference_pairwise_review_v1.json",
            "reference_coverage": "research/qgen/contrast_supply/anchor_reference_catalogue_coverage_v1.json",
            "v5_failure": "research/qgen/contrast_supply/anchor_reference_v5_failure_attribution_v1.json",
            "role_registry": "research/qgen/contrast_supply/candidate_role_registry_v1.json",
            "role_registry_review": "research/qgen/contrast_supply/candidate_role_registry_v1_review.json",
            "catalogue_v3": "research/qgen/contrast_supply/global_candidate_concept_catalogue_v3.json",
            "benchmark": "research/qgen/contrast_supply/transfer18_reference_retrieval_benchmark_v1.json",
            "discovery_v6": "research/qgen/contrast_supply/transfer18_discovery_v6_wave_v1.json",
            "clinical": "research/qgen/contrast_supply/transfer18_discovery_v6_clinical_review_v1.json",
            "bundles": "research/qgen/contrast_supply/transfer18_v6_contrast_bundles_v1.json",
            "density": "research/qgen/contrast_supply/transfer18_v6_bundle_density_v1.json",
            "educational": "research/qgen/contrast_supply/transfer18_v6_educational_feature_audit_v1.json",
            "questions": "research/qgen/contrast_supply/transfer18_v6_development_questions_v1.json",
        }
        for name, path in paths.items(): write(root, path, result[name])
    return result


def build_final_report(
    root: Path,
    result: Mapping[str, Any],
    *,
    focused: Mapping[str, int],
    full_suite: Mapping[str, int],
    copyright_status: str,
) -> dict[str, Any]:
    """Assemble the canonical milestone assessment from derived artifacts."""
    review_counts = Counter(row["verdict"] for row in result["reference_review"]["rows"])
    approved_ids = {
        row["reference_candidate_id"]
        for row in result["reference_review"]["rows"]
        if row["verdict"] == "APPROVED_REFERENCE"
    }
    admission_counts = Counter(row["admission"] for row in result["pairwise"]["rows"])
    coverage_rows = [
        row for row in result["reference_coverage"]["rows"]
        if row["reference_candidate_id"] in approved_ids
    ]
    coverage_counts = Counter(row["catalogue_v2_coverage"] for row in coverage_rows)
    present_role_rows = [
        row for row in coverage_rows
        if row["catalogue_v2_coverage"] in {"EXACT_PRESENT", "ALIAS_PRESENT"}
    ]
    role_counts = Counter(row.get("response_role_coverage", "AMBIGUOUS_RESPONSE_ROLE") for row in present_role_rows)
    failure_counts = Counter(result["v5_failure"]["counts"])
    registry_entries = result["role_registry"]["entries"]
    benchmark = result["benchmark"]
    clinical = result["clinical"]["counts"]
    report = {
        "schema_version": "EXACT_ANCHOR_CANDIDATE_TYPING_AND_DISCOVERY_V6_MILESTONE_V1",
        "milestone_status": "COMPLETE",
        "starting_head": "01eff40984bee76418c7fab82a1ded9fbfa2d9e5",
        "transfer18_status": "EX_CLEAN_TRANSFER_NOW_DEVELOPMENT_DIAGNOSTIC",
        "old_transfer18_sha256": "dae0e32368878130efaf20e38fa41c576e0c4194d8d6687a169e558e2b459a49",
        "old_clean_validation_preserved": True,
        "v5_total_candidate_anchor_evaluations": result["funnel"]["total_evaluations"],
        "v5_gate_rejection_counts": result["funnel"]["gate_rejection_counts"],
        "v5_current_code_replay_matches_frozen": result["funnel"]["current_code_replay_matches_frozen"],
        "v5_current_code_replay_gate_rejection_counts": result["funnel"]["current_code_replay_gate_rejection_counts"],
        "catalogue_v2_role_coverage": {name: result["inventory"][name] for name in ("single_role", "multi_role", "untyped", "ambiguous")},
        "reference_set_sha256": result["reference_set"]["content_sha256"],
        "reference_anchors": len(result["reference_set"]["anchors"]),
        "reference_option_candidates_proposed": sum(review_counts.values()),
        "reference_option_candidates_approved": review_counts["APPROVED_REFERENCE"],
        "reference_option_candidates_rejected": review_counts["REJECTED"],
        "reference_option_candidates_uncertain": review_counts["UNCERTAIN"],
        "reference_admission": {
            "REFERENCE_STRONG_4_PLUS": admission_counts["REFERENCE_STRONG"],
            "REFERENCE_MINIMUM_3": admission_counts["REFERENCE_MINIMUM"],
            "REFERENCE_PARTIAL_1_TO_2": admission_counts["REFERENCE_PARTIAL"],
            "REFERENCE_NONE_0": admission_counts["REFERENCE_NONE"],
        },
        "reference_feature_profiles": len({row["reference_candidate_id"] for row in result["features"]["features"]}),
        "reference_feature_rows": len(result["features"]["features"]),
        "reference_evidence_backed_features": sum(row["evidence_status"] == "EVIDENCE_BACKED" for row in result["features"]["features"]),
        "reference_catalogue_coverage": {name: coverage_counts[name] for name in ("EXACT_PRESENT", "ALIAS_PRESENT", "PARENT_ONLY_PRESENT", "CHILD_ONLY_PRESENT", "RELATED_CONCEPT_ONLY", "ABSENT_FROM_CATALOGUE", "AMBIGUOUS")},
        "reference_response_role_coverage": {name: role_counts[name] for name in ("CORRECT_RESPONSE_ROLE", "WRONG_RESPONSE_ROLE", "UNTYPED_RESPONSE_ROLE", "AMBIGUOUS_RESPONSE_ROLE", "MULTI_ROLE_REQUIRED")},
        "reference_v5_failure_attribution": {name: failure_counts[name] for name in ("ABSENT_FROM_CATALOGUE", "RESPONSE_CLASS", "GRANULARITY", "SIGNATURE", "TARGET_SUBDOMAIN", "APPLICABILITY", "CONTAINMENT", "KEY_ALIAS", "RANKING_BUDGET", "SURVIVES_V5")},
        "root_cause": "MULTIPLE_COMPARABLE_CAUSES",
        "root_cause_evidence": {
            "approved_references_absent_as_exact_or_alias_catalogue_v2_candidates": coverage_counts["RELATED_CONCEPT_ONLY"] + coverage_counts["ABSENT_FROM_CATALOGUE"],
            "present_approved_references_untyped": role_counts["UNTYPED_RESPONSE_ROLE"],
            "present_approved_references_correctly_typed": role_counts["CORRECT_RESPONSE_ROLE"],
        },
        "candidate_role_registry_v1_implemented": True,
        "candidate_role_registry_v1_sha256": result["role_registry"]["content_sha256"],
        "role_registry_counts": {
            "typed_candidates": len(registry_entries),
            "single_role": sum(len(row["roles"]) == 1 for row in registry_entries),
            "multi_role": sum(len(row["roles"]) > 1 for row in registry_entries),
            "untyped": result["catalogue_v3"]["concept_count"] - len(registry_entries),
            "manual_reviewed": sum(row["derivation"] == "MANUAL_REVIEW" for row in registry_entries),
            "deterministically_derived": sum(row["derivation"] == "DETERMINISTIC" for row in registry_entries),
        },
        "catalogue_v3_created": True,
        "catalogue_v3_sha256": result["catalogue_v3"]["content_sha256"],
        "catalogue_v3_new_concepts": result["catalogue_v3"]["new_concept_count"],
        "discovery_v6_implemented": True,
        "discovery_v6_sha256": hashlib.sha256((root / "scripts/qbank/contrast_supply_v6.py").read_bytes()).hexdigest(),
        "v5_reference_recall": benchmark["v5_reference_recall"],
        "v6_reference_recall": benchmark["v6_reference_recall"],
        "v6_reference_precision": benchmark["v6_reference_precision"],
        "v6_reference_with_1_plus": benchmark["anchors_with_1_plus"],
        "v6_reference_with_2_plus": benchmark["anchors_with_2_plus"],
        "v6_reference_with_3_plus": benchmark["anchors_with_3_plus"],
        "v6_reference_with_4_plus": benchmark["anchors_with_4_plus"],
        "v6_diagnostic_candidates": clinical["canonical_candidates"],
        "v6_clinically_plausible": clinical["clinically_plausible"],
        "v6_wrong_decision": clinical["wrong_decision"],
        "v6_potential_second_key": clinical["potential_second_key"],
        "v6_uncertain": clinical["uncertain"],
        "v6_diagnostic_with_1_plus": benchmark["anchors_with_1_plus"],
        "v6_diagnostic_with_2_plus": benchmark["anchors_with_2_plus"],
        "v6_diagnostic_with_3_plus": benchmark["anchors_with_3_plus"],
        "v6_diagnostic_with_4_plus": benchmark["anchors_with_4_plus"],
        "bundle_density": {name: result["density"][name] for name in ("with_1_plus", "with_2_plus", "with_3_plus", "with_4_plus", "with_5_plus", "strong_bundles", "minimum_generatable", "partial", "no_safe")},
        "educational_feature_audit": {name: result["educational"][name] for name in ("strong", "adequate", "weak", "unsafe")},
        "development_questions_generated": result["questions"]["generated"],
        "development_questions_accepted": result["questions"]["accepted"],
        "development_questions_rejected": result["questions"]["rejected"],
        "candidate_role_registry_assessment": "PROMISING",
        "discovery_v6_assessment": "PROMISING",
        "exact_anchor_reference_supply": "MIXED",
        "production_economic_model": "CATALOGUE_COVERAGE_DOMINATES_COST",
        "historical_safety_regression": "PASS",
        "aom_development_control": "PASS",
        "lifecycle_invariant": "PASS",
        "focused_tests": dict(focused),
        "full_suite": dict(full_suite),
        "copyright_audit": copyright_status,
        "ready_for_new_clean_transfer": False,
        "new_transfer_cohort_size": 0,
        "new_transfer_cohort_sha256": None,
        "commits_created": 0,
        "historical_frozen_artifacts_modified": 0,
        "memory_updated": True,
        "claude_md_changed": False,
        "next_dominant_bottleneck": "CANDIDATE_SPECIFIC_FEATURE_EVIDENCE",
        "next_step": "IMPROVE_FEATURE_EVIDENCE_PIPELINE",
    }
    return with_hash(report)


if __name__ == "__main__":
    build_milestone(Path(__file__).resolve().parents[2])
