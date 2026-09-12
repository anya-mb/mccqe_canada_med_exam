"""Sequentially authored bounded seed and one-attempt item specification.

Only the twelve opportunities below produced three safe competitors in the
single allowed discovery wave.  Omitting an opportunity here means its raw
candidates failed before semantic proposal; it is not an opportunity swap.
"""

from __future__ import annotations


def _seed(label, relation, anchor, correct_when, evidence):
    return {
        "candidate": label,
        "relation": relation,
        "anchor_feature_id": anchor,
        "conditions_under_which_candidate_would_be_correct": correct_when,
        "evidence_refs": evidence,
        "verdict": "APPROVED",
    }


def _item(oid, key, stem, lead_in, candidates, rationale, blind_answer, confidence="HIGH"):
    return {
        "opportunity_id": oid,
        "key": key,
        "stem": stem,
        "lead_in": lead_in,
        "candidates": candidates,
        "key_rationale": rationale,
        "blind_answer": blind_answer,
        "blind_confidence": confidence,
    }


READY_ITEM_SPECS = [
    _item("QH24-MED-A25", "Local anesthetic systemic toxicity",
          "A 38-year-old patient becomes dizzy and disoriented two minutes after an inadvertent high dose of local anesthetic during a regional block. The patient reports a metallic taste and numbness around the mouth.",
          "Which diagnosis best explains this presentation?",
          [_seed("Vasovagal reaction", "COUNTERFACTUAL_CORRECT", "SF-H24-A25-01", "Pallor, bradycardia, and hypotension after a needle stimulus without the characteristic neurologic prodrome.", ["H24-SEED-MED-LAST-DIFFERENTIAL-01"]),
           _seed("Panic-related hyperventilation", "COUNTERFACTUAL_CORRECT", "SF-H24-A25-03", "Prominent tachypnea and anxiety with paresthesias, without a toxic temporal dose relationship.", ["H24-SEED-MED-LAST-DIFFERENTIAL-01"]),
           _seed("Systemic epinephrine effect", "COUNTERFACTUAL_CORRECT", "SF-H24-A25-01", "Palpitations, tremor, and hypertension immediately after an epinephrine-containing injection without neurologic toxicity.", ["H24-SEED-MED-LAST-DIFFERENTIAL-01"])],
          "Symptoms beginning immediately after local-anesthetic exposure, especially metallic taste, circumoral numbness, and disorientation, support early systemic toxicity.",
          "Local anesthetic systemic toxicity"),
    _item("QH24-MED-C29", "Transthoracic echocardiography",
          "A 72-year-old patient has progressive exertional dyspnea and a newly recognized harsh systolic murmur. Blood pressure and oxygen saturation are stable.",
          "Which investigation is most appropriate to characterize the suspected valve lesion and its hemodynamic consequences?",
          [_seed("12-lead electrocardiography", "PLAUSIBLE_BUT_NEVER_BEST", "SF-H24-C29-02", "Useful for rhythm or chamber-strain assessment, but it does not define valve anatomy or lesion severity.", ["H24-SEED-MED-VALVE-TESTS-01"]),
           _seed("Chest radiography", "PLAUSIBLE_BUT_NEVER_BEST", "SF-H24-C29-02", "Useful for pulmonary congestion or gross cardiac silhouette, but it does not characterize valve severity.", ["H24-SEED-MED-VALVE-TESTS-01"]),
           _seed("B-type natriuretic peptide", "PLAUSIBLE_BUT_NEVER_BEST", "SF-H24-C29-02", "Can support heart-failure assessment, but it does not identify and grade the valve lesion.", ["SRC-MED-019-REC-01", "SRC-MED-023-REC-01"])],
          "Echocardiography directly identifies the affected valve, grades lesion severity, and evaluates ventricular and hemodynamic consequences.",
          "Transthoracic echocardiography"),

    _item("QH24-PED-P003", "Give the routine vaccines today",
          "An immunocompetent 18-month-old child is due for routine vaccines. The child has mild rhinorrhea and a temperature of 37.6°C, is drinking normally, and has no history of vaccine allergy.",
          "What is the most appropriate vaccination plan?",
          [_seed("Defer vaccination until a moderate or severe acute illness improves", "COUNTERFACTUAL_CORRECT", "SF-H24-P003-02", "Correct when acute illness is moderate or severe, rather than mild.", ["H24-PED-IMMUNIZATION-01"]),
           _seed("Withhold the implicated vaccine after confirmed anaphylaxis to a component", "COUNTERFACTUAL_CORRECT", "SF-H24-P003-01", "Correct when there is confirmed anaphylaxis to that vaccine or a constituent.", ["H24-PED-IMMUNIZATION-01"]),
           _seed("Delay live vaccines during substantial immunosuppression", "COUNTERFACTUAL_CORRECT", "SF-H24-P003-01", "Correct when the child has a clinically important immunocompromising condition or therapy.", ["H24-PED-IMMUNIZATION-01"])],
          "A mild illness, with or without a low fever, is not a reason to delay routine immunization in an otherwise eligible child.",
          "Give the routine vaccines today"),
    _item("QH24-PED-P055", "Begin oral rehydration solution",
          "A 3-year-old child has acute watery diarrhea and mildly dry mucous membranes. The child is alert, has normal perfusion, is not vomiting, and drinks eagerly.",
          "What is the most appropriate initial treatment?",
          [_seed("Give an intravenous isotonic-fluid bolus", "COUNTERFACTUAL_CORRECT", "SF-H24-P055-01", "Correct for shock, severe dehydration, or failure of safe enteral rehydration.", ["H24-PED-DEHYDRATION-01"]),
           _seed("Give ondansetron, then oral rehydration", "COUNTERFACTUAL_CORRECT", "SF-H24-P055-01", "Appropriate when vomiting prevents oral rehydration in an eligible child.", ["H24-PED-ONDANSETRON-01"]),
           _seed("Continue usual fluids without a structured rehydration plan", "COUNTERFACTUAL_CORRECT", "SF-H24-P055-01", "Reasonable when dehydration is absent; it is insufficient for established dehydration.", ["H24-PED-DEHYDRATION-01"])],
          "Mild dehydration with preserved perfusion and ability to drink is treated initially with oral rehydration solution.",
          "Begin oral rehydration solution"),

    _item("QH24-OBGYN-GY40", "Observation without active treatment",
          "A 39-year-old patient has a 2-cm uterine fibroid found incidentally. Menstrual bleeding is normal, hemoglobin is normal, there are no pressure symptoms, and the patient has no fertility concerns.",
          "What is the most appropriate management?",
          [_seed("Myomectomy", "COUNTERFACTUAL_CORRECT", "SF-H24-GY40-01", "Appropriate for selected symptomatic patients who want uterine or fertility preservation.", ["SRC-OBGYN-082-REC-01", "SRC-OBGYN-082-REC-02"]),
           _seed("Uterine artery embolization", "COUNTERFACTUAL_CORRECT", "SF-H24-GY40-01", "Appropriate for selected symptomatic patients desiring uterine preservation but not future fertility.", ["SRC-OBGYN-082-REC-02"]),
           _seed("Hysterectomy", "COUNTERFACTUAL_CORRECT", "SF-H24-GY40-01", "Definitive treatment for substantial symptoms when fertility and uterine preservation are not desired.", ["SRC-OBGYN-082-REC-02"])],
          "Asymptomatic fibroids generally require no treatment; intervention is selected for symptoms and patient goals.",
          "Observation without active treatment"),
    _item("QH24-OBGYN-OB11", "Administer Tdap now",
          "A healthy patient at 28 weeks' gestation presents for routine antenatal care. Routine vaccines were up to date before pregnancy, and there is no vaccine-specific contraindication.",
          "Which vaccination action is most appropriate at this visit?",
          [_seed("Administer measles-mumps-rubella vaccine now", "COUNTERFACTUAL_CORRECT", "SF-H24-OB11-02", "Appropriate when indicated outside pregnancy; it is a live vaccine and is contraindicated during pregnancy.", ["SRC-OBGYN-074-REC-02"]),
           _seed("Administer varicella vaccine now", "COUNTERFACTUAL_CORRECT", "SF-H24-OB11-02", "Appropriate for susceptible nonpregnant patients; it is a live vaccine and is contraindicated during pregnancy.", ["SRC-OBGYN-074-REC-02"]),
           _seed("Defer Tdap until after delivery because it was received previously", "COUNTERFACTUAL_CORRECT", "SF-H24-OB11-01", "Postpartum Tdap is used when it was missed in pregnancy, but prior history does not replace Tdap in each pregnancy.", ["SRC-OBGYN-074-REC-01"])],
          "Tdap is recommended during every pregnancy, ideally at 27–32 weeks, regardless of prior Tdap history.",
          "Administer Tdap now"),

    _item("QH24-SURG-GS73", "Watchful waiting with return precautions",
          "A 58-year-old man has a small, easily reducible inguinal hernia found on examination. It causes no pain or activity limitation, and there are no obstructive symptoms.",
          "What is the most appropriate management strategy?",
          [_seed("Elective open mesh repair", "COUNTERFACTUAL_CORRECT", "SF-H24-GS73-01", "Appropriate for a symptomatic elective inguinal hernia when operative treatment is chosen.", ["H24-SURG-HERNIA-01"]),
           _seed("Elective laparoscopic repair", "COUNTERFACTUAL_CORRECT", "SF-H24-GS73-01", "Appropriate for selected symptomatic patients or circumstances favouring a minimally invasive approach.", ["H24-SURG-HERNIA-01"]),
           _seed("Urgent operative repair", "COUNTERFACTUAL_CORRECT", "SF-H24-GS73-01", "Required for suspected strangulation, incarceration, or bowel obstruction.", ["H24-SURG-HERNIA-01"])],
          "Watchful waiting is a safe option for carefully selected patients with an asymptomatic or minimally symptomatic inguinal hernia.",
          "Watchful waiting with return precautions"),
    _item("QH24-SURG-OR57", "No ankle imaging is indicated now",
          "A 24-year-old patient has lateral ankle pain after an inversion injury. There is no tenderness at the posterior edge or tip of either malleolus, and the patient can walk four steps.",
          "What is the most appropriate imaging decision?",
          [_seed("Obtain plain ankle radiographs", "COUNTERFACTUAL_CORRECT", "SF-H24-OR57-01", "Correct when the Ottawa ankle rules are positive for malleolar tenderness or inability to bear weight.", ["H24-SURG-ANKLE-01"]),
           _seed("Obtain magnetic resonance imaging", "COUNTERFACTUAL_CORRECT", "SF-H24-OR57-01", "May be appropriate later for persistent symptoms or suspected occult or complex soft-tissue injury.", ["H24-SURG-ANKLE-ADVANCED-01"]),
           _seed("Obtain musculoskeletal ultrasonography", "COUNTERFACTUAL_CORRECT", "SF-H24-OR57-01", "May be appropriate for a focused tendon question, not routine initial assessment of this uncomplicated sprain.", ["H24-SURG-ANKLE-ADVANCED-01"])],
          "The Ottawa ankle rules are negative, so routine ankle radiography is not indicated; advanced imaging is also unnecessary initially.",
          "No ankle imaging is indicated now"),

    _item("QH24-PSY-PS04", "Maintain continuous observation and arrange emergency psychiatric assessment",
          "A 32-year-old patient says they intend to die tonight, describes a specific plan, has access to the means, and cannot agree to remain safe. No reliable support person is available.",
          "What is the most appropriate immediate disposition?",
          [_seed("Discharge with a written safety plan and follow-up within one week", "COUNTERFACTUAL_CORRECT", "SF-H24-PS04-01", "Appropriate only for substantially lower acute risk with a feasible collaborative safety plan and reliable follow-up.", ["H24-PSY-SUICIDE-01"]),
           _seed("Arrange urgent outpatient psychiatry within 48 hours", "COUNTERFACTUAL_CORRECT", "SF-H24-PS04-01", "Can fit elevated but non-imminent risk when immediate safety is secured outside hospital.", ["H24-PSY-SUICIDE-01"]),
           _seed("Ask family to supervise at home and remove lethal means", "COUNTERFACTUAL_CORRECT", "SF-H24-PS04-01", "May contribute to a lower-risk community plan when reliable supports exist, but it is insufficient here.", ["H24-PSY-SUICIDE-01"])],
          "Current intent, a specific plan, means access, and inability to maintain safety require a secure setting, continuous observation, and emergency assessment.",
          "Maintain continuous observation and arrange emergency psychiatric assessment"),
    _item("QH24-PSY-PS30", "Start buprenorphine/naloxone",
          "A patient with moderate-to-severe opioid use disorder requests maintenance treatment. They value a lower overdose risk and flexible take-home dosing, and there is no contraindication to buprenorphine initiation.",
          "Which medication is the preferred first-line choice?",
          [_seed("Methadone", "COUNTERFACTUAL_CORRECT", "SF-H24-PS30-02", "An evidence-based opioid agonist alternative when buprenorphine is unsuitable or ineffective, or patient factors favour methadone.", ["H24-PSY-OUD-01"]),
           _seed("Slow-release oral morphine", "COUNTERFACTUAL_CORRECT", "SF-H24-PS30-02", "An alternative when first-line opioid agonist treatments are contraindicated, unavailable, or ineffective.", ["H24-PSY-OUD-01"]),
           _seed("Extended-release naltrexone", "COUNTERFACTUAL_CORRECT", "SF-H24-PS30-02", "May suit a fully withdrawn patient who specifically prefers antagonist treatment and can start it safely.", ["H24-PSY-OUD-ALTERNATIVES-01"])],
          "Buprenorphine/naloxone is preferred first-line when appropriate and fits the stated priorities because of its safety and access advantages.",
          "Start buprenorphine/naloxone"),

    _item("QH24-PHELO-PH09", "The rates cannot be compared without the population denominators",
          "A report states that Region A recorded 600 new cases of a disease last year and Region B recorded 400. It gives no population sizes or person-time denominators.",
          "Which interpretation is most accurate?",
          [_seed("Region A necessarily had the higher incidence rate", "COUNTERFACTUAL_CORRECT", "SF-H24-PH09-01", "Correct only if the relevant population or person-time denominators and ascertainment were equivalent.", ["REC-SRC-PHELO-013-01"]),
           _seed("Region B necessarily had the lower disease prevalence", "COUNTERFACTUAL_CORRECT", "SF-H24-PH09-01", "A prevalence comparison would require defined populations and existing-case counts, not these new-case counts alone.", ["REC-SRC-PHELO-013-01"]),
           _seed("The two regions had equivalent risk because both reported counts", "COUNTERFACTUAL_CORRECT", "SF-H24-PH09-01", "Equivalence could be assessed only after comparable rate denominators and uncertainty were supplied.", ["REC-SRC-PHELO-013-01"])],
          "Counts alone do not establish rates; the defined population or person-time denominator is required.",
          "The rates cannot be compared without the population denominators"),
    _item("QH24-PHELO-PH14", "The populations have different baseline event risks",
          "The same therapy reduces event risk from 20% to 10% in Population A and from 2% to 1% in Population B. The relative risk reduction is 50% in both, but the number needed to treat is 10 in A and 100 in B.",
          "What best explains the different numbers needed to treat?",
          [_seed("The treatment has different relative effects", "COUNTERFACTUAL_CORRECT", "SF-H24-PH14-01", "Could explain different absolute effects if relative risk reductions differed, but they are explicitly identical here.", ["H24-PHELO-NNT-01"]),
           _seed("The studies used different diagnostic-test specificities", "COUNTERFACTUAL_CORRECT", "SF-H24-PH14-03", "Could alter observed event classification, but no measurement difference is described.", ["H24-PHELO-DIAGNOSTIC-TEST-01"]),
           _seed("The result is explained by randomization failure", "COUNTERFACTUAL_CORRECT", "SF-H24-PH14-03", "Confounding could distort an effect in a nonrandom comparison, but it is neither needed nor supported to explain the arithmetic shown.", ["H24-PHELO-NNT-01"])],
          "NNT is the reciprocal of absolute risk reduction. The same relative reduction creates a larger absolute reduction when baseline risk is higher.",
          "The populations have different baseline event risks"),
]
