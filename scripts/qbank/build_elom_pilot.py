"""Build the ELOM (chapter ELOM) pilot: study units + MCC crosswalk.

Phase 3B pilot. Validates the curriculum-crosswalk methodology on a
fundamentally different domain (ethical/legal/organizational, largely
non-Medical-Expert) after calibrating the model on Cardiology. No
question generation.

Structural finding (verified directly against raw OCR page 21, the
chapter's own TOC page - not invented): three of ELOM's four TOC_OCR
sections are themselves MERGES of multiple printed Toronto Notes headings
that happen to share a page label, exactly the same artifact seen in
Cardiology's ACrOMYMS/Basic-Anatomy-Review merge:
  - ELOM.S01 ("AcromymsS") actually merges THREE headings: "Acronyms",
    "Ethical Issues in Health Care" (a bare category header with no
    content of its own), and "The Canadian Healthcare System" (with 6
    real topic children).
  - ELOM.S03 ("Clinical Informatics and Ethical Considerations") merges
    TWO headings: itself (2 topics) and "Indigenous Health" (5 topics
    after resolving one more OCR line-wrap).
  - ELOM.S04 ("References") node's 13 "topic" children are NOT sub-items
    of the bibliography at all - they are a disclaimer/framework
    paragraph (the CLEO citation + the "three main types of law" note)
    that is printed on the CHAPTER'S OWN TOC PAGE (pdf page 21) after the
    "References...ELOM32" line, and one stray OCR-corrupted page-footer
    fragment. Verified by searching all ELOM body pages for this exact
    text: it appears ONLY on page 21, not anywhere in the actual
    bibliography (pdf pages 52-54).
Resolved by direct source inspection, not invented. See each unit's
structural_rationale for the specific resolution.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO / "research" / "tn2025" / "toc_inventory.json"
REGISTRY_PATH = REPO / "research" / "mcc" / "objectives_registry.json"

OUT_DIR = REPO / "research" / "scope" / "pilots" / "elom"

CHAPTER_CODE = "ELOM"
GENERATED_AT = "2026-08-24"

ORGANIZATIONAL_HEADER_NODES = {
    "ELOM": "Chapter root container - represented by all study units below.",
    "ELOM.S02": (
        "'Ethical and Legal Issues in Canadian Medicine' - a pure section "
        "umbrella (verified against raw page-21 TOC text: this heading has "
        "no content of its own beyond its 12 topic children, each a "
        "distinct testable ethical/legal issue and kept as its own study "
        "unit per the task's explicit instruction not to collapse "
        "distinct legal/professional decisions)."
    ),
}

EXCLUDED_ARTIFACT_NODES = {
    "ELOM.S04.T13": (
        "Raw OCR text: 'ELOMI1 Ethical, Legal, and Organizational Medicine "
        "Toronto Notes 2025'. Verified against the source: this is a "
        "corrupted copy of the chapter's own running footer from page 21 "
        "itself ('ELOM1 Ethical, Legal, and Organizational Medicine "
        "Toronto Notes 2025', with '1' misread as 'I1'), not a genuine "
        "content line. Explicitly excluded as a parsing artifact, not "
        "silently dropped - tracked here with its full raw text so the "
        "exclusion is auditable."
    ),
}


def load_inventory_nodes():
    with open(INVENTORY_PATH) as f:
        inv = json.load(f)
    return [n for n in inv["nodes"] if n["chapter_code"] == CHAPTER_CODE]


def node_lookup(nodes):
    return {n["node_id"]: n for n in nodes}


# ---------------------------------------------------------------------------
# STUDY UNIT DEFINITIONS
# ---------------------------------------------------------------------------

STUDY_UNITS = [
    {
        "study_unit_id": "SU-ELOM-01",
        "title": "Acronyms (Chapter Glossary)",
        "source_node_ids": ["ELOM.S01"],
        "structural_rationale": (
            "Toronto Notes' chapter-opening acronym glossary. Reference "
            "material only. NOTE: this node's raw title 'AcromymsS' and "
            "page range (ELOM2-ELOM8) actually represent THREE merged "
            "printed headings sharing page ELOM2 (verified against raw "
            "OCR page 21): 'Acronyms', 'Ethical Issues in Health Care' "
            "(a bare category header with zero content of its own - the "
            "raw TOC shows no topics listed directly under it before "
            "'The Canadian Healthcare System' begins), and 'The Canadian "
            "Healthcare System'. This unit represents ONLY the Acronyms "
            "portion; the Canadian Healthcare System content is "
            "separately represented in SU-ELOM-02 through SU-ELOM-06 via "
            "this same node's topic children. 'Ethical Issues in Health "
            "Care' itself is accounted for as an organizational header "
            "with no independent content (see organizational_header_nodes "
            "in study_units.json), analogous to Cardiology's 'CARDIAC "
            "DISEASE'."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-02",
        "title": "Canadian Healthcare System: Structure, Funding, and Delivery",
        "source_node_ids": ["ELOM.S01.T01", "ELOM.S01.T05"],
        "structural_rationale": (
            "'Overview of Canadian Healthcare System' and 'Healthcare "
            "Expenditure and Delivery in Canada' combined: the first "
            "introduces what the system is, the second how it is funded "
            "and delivered - one coherent system-overview unit rather "
            "than an isolated background fact and a separate funding "
            "fact."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-03",
        "title": "Legal Foundation of Canadian Healthcare",
        "source_node_ids": ["ELOM.S01.T02"],
        "structural_rationale": (
            "Kept separate from the general system-overview unit because "
            "it addresses a genuinely distinct testable competency: the "
            "constitutional/jurisdictional division of authority over "
            "healthcare between federal and provincial/territorial "
            "governments, which directly grounds the jurisdiction model "
            "(see crosswalk jurisdiction field) applied across this "
            "chapter's legal units."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-04",
        "title": "History of the Canadian Healthcare System and Crown-Indigenous Relations",
        "source_node_ids": ["ELOM.S01.T03", "ELOM.S01.T04"],
        "structural_rationale": (
            "'History of the Canadian Healthcare System and Crown-"
            "Indigenous' / 'Relations Pursuant to Healthcare' are one "
            "topic split into two TOC lines by an OCR line-wrap artifact "
            "(the full heading is 'History of the Canadian Healthcare "
            "System and Crown-Indigenous Relations Pursuant to "
            "Healthcare') - both nodes grouped into this one unit."
        ),
        "extraction_confidence": "MEDIUM",
    },
    {
        "study_unit_id": "SU-ELOM-05",
        "title": "Physician Licensure and Certification",
        "source_node_ids": ["ELOM.S01.T06"],
        "structural_rationale": "Distinct, independently testable professional/regulatory process, kept separate from the general system overview.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-06",
        "title": "Role of Professional Associations",
        "source_node_ids": ["ELOM.S01.T07"],
        "structural_rationale": "Distinct organizational topic (CMA, provincial colleges, specialty societies) with its own testable competency (knowing which body does what).",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-07",
        "title": "Introduction to the Principles of Ethics",
        "source_node_ids": ["ELOM.S02.T01"],
        "structural_rationale": (
            "Foundational ethical framework (autonomy, beneficence, non-"
            "maleficence, justice) underlying all subsequent ethics "
            "topics in this section - kept as its own small foundational "
            "unit rather than folded silently into every downstream unit, "
            "since it has substantive content of its own."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-08",
        "title": "Confidentiality",
        "source_node_ids": ["ELOM.S02.T02"],
        "structural_rationale": "Distinct, independently testable professional/legal duty.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-09",
        "title": "Consent and Capacity",
        "source_node_ids": ["ELOM.S02.T03"],
        "structural_rationale": (
            "Kept as ONE unit matching Toronto Notes' own combined "
            "heading - consent and capacity are clinically and legally "
            "inseparable (capacity assessment is the gateway to valid "
            "consent), not artificially split into two units the source "
            "itself doesn't split."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-10",
        "title": "Negligence",
        "source_node_ids": ["ELOM.S02.T04"],
        "structural_rationale": "Distinct, independently testable medico-legal issue.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-11",
        "title": "Truth-Telling",
        "source_node_ids": ["ELOM.S02.T05"],
        "structural_rationale": "Distinct communication/professional duty.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-12",
        "title": "Reproductive Technologies",
        "source_node_ids": ["ELOM.S02.T06"],
        "structural_rationale": "Distinct ethical/legal domain (IVF, surrogacy, related consent issues), kept separate rather than folded into general consent.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-13",
        "title": "End-of-Life Care",
        "source_node_ids": ["ELOM.S02.T07"],
        "structural_rationale": "Distinct, high-currency topic (goals of care, MAID) with its own dedicated MCC objective (Dying patients).",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-14",
        "title": "Physician Competence and Professional Conduct",
        "source_node_ids": ["ELOM.S02.T08"],
        "structural_rationale": "Distinct professional-duty/discipline topic.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-15",
        "title": "Research Ethics",
        "source_node_ids": ["ELOM.S02.T09"],
        "structural_rationale": "Distinct domain (REB approval, research consent, Tri-Council Policy Statement), kept separate from clinical consent/ethics.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-16",
        "title": "Physician-Industry Relations",
        "source_node_ids": ["ELOM.S02.T10"],
        "structural_rationale": "Distinct conflict-of-interest topic.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-17",
        "title": "Resource Allocation",
        "source_node_ids": ["ELOM.S02.T11"],
        "structural_rationale": "Distinct distributive-justice/triage topic.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-18",
        "title": "Conscientious Objection",
        "source_node_ids": ["ELOM.S02.T12"],
        "structural_rationale": "Distinct, currently topical issue (referral obligations re: MAID, reproductive services), kept separate rather than folded into general professionalism.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-19",
        "title": "Clinical Informatics and Digital Health Ethics",
        "source_node_ids": ["ELOM.S03", "ELOM.S03.T01", "ELOM.S03.T02"],
        "structural_rationale": (
            "'Key Terms' and 'Overview of Digital Health Technologies' "
            "combined: Key Terms is a short glossary preamble to the "
            "substantive digital-health content, not an independent "
            "testable unit on its own. This unit also carries the "
            "section-level node ELOM.S03 itself, since that node's own "
            "printed title/page-anchor represents 'Clinical Informatics "
            "and Ethical Considerations' (the FIRST of its two merged "
            "headings - see SU-ELOM-20..23 for resolution of the second, "
            "'Indigenous Health', which shares the same page label)."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-20",
        "title": "History and Impact of Colonialism, and the Movement Towards Reconciliation",
        "source_node_ids": ["ELOM.S03.T03", "ELOM.S03.T04"],
        "structural_rationale": (
            "'Overview of the History and Impact of Colonialism' and "
            "'Movement Towards Reconciliation' combined: Toronto Notes "
            "places them as an immediately adjacent historical-narrative "
            "pair (colonialism's harms, then the current reconciliation "
            "response), and both represent historical/contextual "
            "literacy rather than two independent clinical decisions - "
            "matching the consolidation principle for closely related "
            "material, not two clinically distinct competencies."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-21",
        "title": "Indigenous Health Disparities and Comorbidities",
        "source_node_ids": ["ELOM.S03.T05", "ELOM.S03.T06"],
        "structural_rationale": (
            "'Indigenous Disproportionate Over-Representation of "
            "Biological,' / 'Psychological, and Social Co-Morbicities' "
            "[sic, OCR] are one topic split into two TOC lines by an OCR "
            "line-wrap artifact (the full heading is 'Indigenous "
            "Disproportionate Over-Representation of Biological, "
            "Psychological, and Social Co-Morbidities') - both nodes "
            "grouped into this one unit. Kept as its own distinct unit "
            "(not folded into the colonialism/reconciliation unit) "
            "because it addresses a distinct, directly clinically-"
            "relevant competency: recognizing structural determinants of "
            "elevated disease burden, not historical narrative."
        ),
        "extraction_confidence": "MEDIUM",
    },
    {
        "study_unit_id": "SU-ELOM-22",
        "title": "Indigenous Health Coverage and Jurisdictions",
        "source_node_ids": ["ELOM.S03.T07"],
        "structural_rationale": "Distinct system-navigation topic (NIHB, jurisdictional gaps such as Jordan's Principle) with real testable decision content.",
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-23",
        "title": "Resources in Indigenous Health",
        "source_node_ids": ["ELOM.S03.T08"],
        "structural_rationale": (
            "Verified against the raw References bibliography (pdf pages "
            "53-54): 'Resources in Indigenous Health' is literally one of "
            "the bibliography's own subsection headers there. This TOC-"
            "listed topic is a pointer to that resource list, not "
            "independent testable content - treated as reference "
            "material."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-24",
        "title": "References / Bibliography",
        "source_node_ids": ["ELOM.S04"],
        "structural_rationale": (
            "The chapter's actual bibliography (pdf pages 52-54, "
            "confirmed by direct inspection - citation lists under "
            "'Bioethics', 'Governing Organizations', 'Healthcare "
            "Delivery', 'Important Acts/Charters', 'Law', 'Research "
            "Ethics', 'Indigenous Health, History, and Laws', 'Resources "
            "in Indigenous Health'). This unit represents ONLY the "
            "section-level node's own bibliography content; its "
            "extracted 'topic' children (T01-T13) are NOT genuine "
            "sub-items of the bibliography - see SU-ELOM-25 and "
            "EXCLUDED_ARTIFACT_NODES."
        ),
        "extraction_confidence": "HIGH",
    },
    {
        "study_unit_id": "SU-ELOM-25",
        "title": "Canadian Legal System Framework (Criminal/Civil/Administrative Law)",
        "source_node_ids": [
            "ELOM.S04.T01", "ELOM.S04.T02", "ELOM.S04.T03",
            "ELOM.S04.T04", "ELOM.S04.T05", "ELOM.S04.T06",
            "ELOM.S04.T07", "ELOM.S04.T08", "ELOM.S04.T09",
            "ELOM.S04.T10", "ELOM.S04.T11", "ELOM.S04.T12",
        ],
        "structural_rationale": (
            "VERIFIED SOURCE AMBIGUITY, RESOLVED BY DIRECT INSPECTION "
            "(not invented): these 12 nodes were extracted as 'topic' "
            "children of the References section (ELOM.S04) because they "
            "are unclaimed text following the last TOC section line, but "
            "searching all ELOM body pages confirms this text appears "
            "ONLY on page 21 (the chapter's own TOC/title page), "
            "immediately after 'References...ELOM32' in the printed TOC, "
            "and NOT anywhere within the actual bibliography (pdf 52-54). "
            "It is a general framing/disclaimer note explaining that (a) "
            "the official MCC CLEO objectives document "
            "(mcc.ca/wp-content/uploads/CLEO.pdf) covers this material in "
            "more depth, and (b) a single act can trigger criminal, "
            "civil, AND administrative consequences, with criminal law "
            "nationwide but civil/administrative law varying by province/"
            "territory. This is substantive, testable content in its own "
            "right (the criminal/civil/administrative framework and the "
            "jurisdiction-varies-by-province principle) - reattributed "
            "here as its own unit rather than left buried as spurious "
            "'topics' of the bibliography. A 13th extracted node "
            "(ELOM.S04.T13) is a genuine OCR artifact (corrupted running "
            "footer text) and is explicitly excluded, not included here - "
            "see EXCLUDED_ARTIFACT_NODES."
        ),
        "extraction_confidence": "MEDIUM",
    },
]


def enrich_study_units(units, nodes_by_id):
    for u in units:
        pdf_starts, pdf_ends, tn_starts, tn_ends, paths, levels = [], [], [], [], [], []
        for nid in u["source_node_ids"]:
            n = nodes_by_id[nid]
            pdf_starts.append(n["start_pdf_page"])
            pdf_ends.append(n["end_pdf_page"])
            tn_starts.append(n["start_tn_page"])
            tn_ends.append(n["end_tn_page"])
            paths.append(f"{nid} ({n['title']})")
            levels.append(n["level"])
        u["tn_page_range"] = f"{min(tn_starts, key=lambda x: int(''.join(c for c in x if c.isdigit())))}-{max(tn_ends, key=lambda x: int(''.join(c for c in x if c.isdigit())))}"
        u["pdf_page_range"] = [min(pdf_starts), max(pdf_ends)]
        u["chapter_code"] = CHAPTER_CODE
        u["chapter_title"] = "Ethical, Legal, and Organizational Medicine"
        u["source_hierarchy_path"] = paths
        u["page_mapping_precision"] = "EXACT_SECTION" if 2 in levels else "SECTION_INHERITED"
    return units


def derive_coverage_weight(minimum_coverage_hint, classification):
    if classification in ("REFERENCE_ONLY",):
        return 1
    return minimum_coverage_hint


# ---------------------------------------------------------------------------
# CROSSWALK: MCC mapping per study unit.
#
# MCC evidence verified directly against research/mcc/objectives_registry.json
# by loading each cited objective's/role's actual content. ELOM maps heavily
# to non-Medical-Expert role-level objectives (Collaborator, Leader/Manager,
# Professional, Scholar) - confirmed these exist and contain directly
# relevant enabling-objective text before citing them, exactly as done for
# Medical Expert objectives in the Cardiology pilot. No objective invented.
# ---------------------------------------------------------------------------

def obj_ref(mcc_id, title, role="Medical Expert", strength="STRONG", rationale="", requires_scope_review=False):
    ref = {
        "mcc_id": mcc_id,
        "legacy_id": mcc_id,
        "objective_title": title,
        "canmeds_role": role,
        "official_source": "research/mcc/objectives_registry.json (retrieved from official MCC Objectives Online Web Service)",
        "mapping_strength": strength,
        "mapping_rationale": rationale,
    }
    if requires_scope_review:
        ref["requires_scope_review"] = True
    return ref


def role_ref(role, group_title, strength="STRONG", rationale="", requires_scope_review=False):
    """Non-Medical-Expert roles have no per-objective mcc_id/legacy_id (see
    objectives_registry.json structural_note: MCC represents these roles as
    a single role-level competency statement, not discrete objectives).
    mcc_id/legacy_id are explicitly null rather than fabricated."""
    ref = {
        "mcc_id": None,
        "legacy_id": None,
        "objective_title": f"{role} - {group_title}",
        "canmeds_role": role,
        "official_source": "research/mcc/objectives_registry.json (role-level record; no per-objective ID exists for this role)",
        "mapping_strength": strength,
        "mapping_rationale": rationale,
    }
    if requires_scope_review:
        ref["requires_scope_review"] = True
    return ref


NA_JURISDICTION = {"scope": "NOT_APPLICABLE", "province_required_in_question": False, "fresh_legal_verification_required": False}

CROSSWALK = {
    "SU-ELOM-01": {
        "classification": "REFERENCE_ONLY", "mcc_evidence": [],
        "scope_depth": "OUT_OF_SCOPE_DETAIL", "testable_competencies": {},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 0, "preferred_item_forms": [],
        "zero_question_reason": "Pure glossary/reference content.",
        "clinical_source_organizations": [], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-02": {
        "classification": "COMPONENT",
        "mcc_evidence": [obj_ref("78-1", "Concepts of health and its determinants", strength="MODERATE",
            rationale="Objective covers 'concepts of health, wellness, illness, disease' and 'determinants of health'; system-level structure/funding/delivery is adjacent but not identical to this objective's own focus on individual-level health concepts.")],
        "scope_depth": "RECOGNIZE",
        "testable_competencies": {"system_navigation": "Describe the basic structure, funding model (public single-payer for medically necessary services), and delivery mechanisms of the Canadian healthcare system."},
        "jurisdiction": {"scope": "CANADA_WIDE_PROFESSIONAL_PRINCIPLE", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 2, "preferred_item_forms": ["SYSTEM_ORGANIZATIONAL_DECISION"],
        "clinical_source_organizations": ["Health Canada", "Government of Canada / Department of Justice"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-03": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("121-5", "Legal system", strength="STRONG",
            rationale="Objective's rationale explicitly states: 'Knowledge of the legal system in Canada allows the physician to provide care to patients in the context of federal, provincial or territorial, and local laws and regulations.' Directly matches this unit's content.")],
        "scope_depth": "RECOGNIZE_AND_ACT",
        "testable_competencies": {"legal_professional_action": "Identify which level of government/legal authority (federal vs. provincial/territorial) governs a given healthcare legal question."},
        "jurisdiction": {"scope": "FEDERAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 3, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION", "SYSTEM_ORGANIZATIONAL_DECISION"],
        "clinical_source_organizations": ["Government of Canada / Department of Justice", "provincial/territorial legislation"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-04": {
        "classification": "COMPONENT",
        "mcc_evidence": [
            obj_ref("78-9", "Indigenous health", strength="MODERATE", rationale="Objective's rationale explicitly requires responding to TRC Calls to Action; historical context is foundational but this unit itself is historical/contextual literacy rather than the objective's own clinical-encounter focus."),
            obj_ref("127", "Providing anti-oppressive health care", strength="MODERATE", rationale="Objective explicitly names colonialism and the TRC Calls to Action as foundational context for anti-oppressive care."),
        ],
        "scope_depth": "CONTEXT_ONLY",
        "testable_competencies": {"ethical_reasoning": "Articulate how the history of the Canadian healthcare system and Crown-Indigenous relations informs current health inequities."},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 2, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION"],
        "clinical_source_organizations": ["authoritative Indigenous-health sources", "Truth and Reconciliation Commission of Canada"], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-05": {
        "classification": "COMPONENT",
        "mcc_evidence": [role_ref("Leader/Manager", "Effectively manage practice and career", strength="MODERATE",
            rationale="Group's enabling text: 'Abide by the regulatory requirements governing medical office practice' - generically covers regulatory compliance but does not explicitly name licensure/certification processes.")],
        "scope_depth": "RECOGNIZE",
        "testable_competencies": {"system_navigation": "Recognize the role of the LMCC and provincial/territorial medical regulatory authorities in physician licensure."},
        "jurisdiction": {"scope": "PROVINCIAL_TERRITORIAL", "province_required_in_question": True, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 2, "preferred_item_forms": ["SYSTEM_ORGANIZATIONAL_DECISION"],
        "clinical_source_organizations": ["provincial/territorial Colleges/regulators", "MCC"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-06": {
        "classification": "DIRECT",
        "mcc_evidence": [role_ref("Leader/Manager", "Participate appropriately in the health care system", strength="STRONG",
            rationale="Group's enabling text explicitly names 'professional associations' as one of the bodies whose role the candidate must describe: 'Describe the roles of physicians in developing and supporting the health care system (including health and prevention, advocacy groups, regulatory bodies, professional associations).'")],
        "scope_depth": "RECOGNIZE",
        "testable_competencies": {"system_navigation": "Identify the distinct roles of the CMA, provincial medical associations, and specialty societies."},
        "jurisdiction": {"scope": "CANADA_WIDE_PROFESSIONAL_PRINCIPLE", "province_required_in_question": False, "fresh_legal_verification_required": False},
        "minimum_question_coverage": 2, "preferred_item_forms": ["SYSTEM_ORGANIZATIONAL_DECISION"],
        "clinical_source_organizations": ["CMA"], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-07": {
        "classification": "SUPPORTING_KNOWLEDGE", "mcc_evidence": [],
        "scope_depth": "CONTEXT_ONLY",
        "testable_competencies": {"ethical_reasoning": "Apply the four principles of biomedical ethics (autonomy, beneficence, non-maleficence, justice) to frame a clinical ethics question."},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 1, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION"],
        "clinical_source_organizations": [], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-08": {
        "classification": "DIRECT",
        "mcc_evidence": [role_ref("Communicator", "Effectively convey oral and written information associated with a medical encounter", strength="STRONG",
            rationale="Group's enabling text explicitly covers confidentiality: 'Adhere to the ethical and legal requirements of confidentiality in all professional communication', 'Maintain confidentiality of medical records', 'Know the exceptions to confidentiality and when it must or may be breached (e.g., duty to warn or report, child abuse, notifiable diseases)'.")],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {
            "legal_professional_action": "Maintain patient confidentiality and recognize the recognized exceptions (duty to warn, mandatory reporting).",
            "communication": "Disclose information only with appropriate consent or legal authority.",
        },
        "jurisdiction": {"scope": "PROVINCIAL_TERRITORIAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 5, "preferred_item_forms": ["CONFIDENTIALITY_DECISION"],
        "clinical_source_organizations": ["provincial/territorial legislation", "CMPA"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-09": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("121-1", "Consent", strength="STRONG",
            rationale="Objective's key_objectives text explicitly names capacity: 'taking into account issues related to decision-making capacity, information sharing, the form of consent, limitations, and exceptions to the requirement of consent.'")],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {
            "assessment": "Assess decision-making capacity for a specific decision.",
            "legal_professional_action": "Determine the appropriate consent process, including for incapable patients (substitute decision-maker).",
        },
        "jurisdiction": {"scope": "PROVINCIAL_TERRITORIAL", "province_required_in_question": True, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 8, "preferred_item_forms": ["CONSENT_CAPACITY_DECISION"],
        "clinical_source_organizations": ["provincial/territorial legislation (e.g., health care consent acts)", "CMPA"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-10": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("121-3", "Negligence", strength="STRONG",
            rationale="Direct title and content match: objective covers standard of care, harm, and appropriate action when negligence is reported or suspected.")],
        "scope_depth": "RECOGNIZE_AND_ACT",
        "testable_competencies": {"legal_professional_action": "Recognize a potential negligence/standard-of-care concern and determine appropriate next steps."},
        "jurisdiction": {"scope": "PROVINCIAL_TERRITORIAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 4, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION", "PROFESSIONAL_RESPONSE"],
        "clinical_source_organizations": ["CMPA", "provincial/territorial Colleges/regulators"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-11": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("121-2", "Truth telling", strength="STRONG",
            rationale="Direct title and content match: 'the candidate must honestly and accurately convey relevant information and explanations to patients, their families and other members of the health care team.'")],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {"communication": "Honestly and accurately disclose information, including medical error, to patients and families."},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 4, "preferred_item_forms": ["COMMUNICATION_RESPONSE"],
        "clinical_source_organizations": ["CMPA"], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-12": {
        "classification": "COMPONENT",
        "mcc_evidence": [obj_ref("121-1", "Consent", strength="WEAK",
            rationale="Reproductive technology use requires the same general consent framework this objective covers, but assisted human reproduction is not itself named in the objective's content.", requires_scope_review=True)],
        "scope_depth": "RECOGNIZE",
        "testable_competencies": {"ethical_reasoning": "Apply informed consent principles to reproductive technology decisions (e.g., IVF, surrogacy, gamete donation)."},
        "jurisdiction": {"scope": "FEDERAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 2, "preferred_item_forms": ["CONSENT_CAPACITY_DECISION"],
        "clinical_source_organizations": ["Government of Canada / Department of Justice (Assisted Human Reproduction Act)", "SOGC"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-13": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("25", "Dying patients", strength="STRONG",
            rationale="Objective's key_objectives text explicitly requires: 'The candidate must know the provisions in Canadian law on medical assistance in dying (MAID), be prepared to discuss them with patients, and respond appropriately to such requests.'")],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {
            "assessment": "Develop a goals-of-care plan for a dying patient.",
            "legal_professional_action": "Know the provisions of Canadian MAID law and respond appropriately to a MAID request.",
            "communication": "Discuss end-of-life options with patients and families.",
        },
        "jurisdiction": {"scope": "FEDERAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 6, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION", "COMMUNICATION_RESPONSE"],
        "clinical_source_organizations": ["Government of Canada / Department of Justice (Criminal Code MAID provisions)", "Health Canada", "CMPA"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-14": {
        "classification": "DIRECT",
        "mcc_evidence": [role_ref("Professional", "Accountability to the profession", strength="STRONG",
            rationale="Group's enabling text directly covers this unit's content: 'Abide by the profession's rules, regulations, and ethical codes', 'Recognise and respond to unprofessional and unethical behaviours in physicians and other health professional colleagues', 'Participate in peer assessment, teaching, and standard setting'.")],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {"legal_professional_action": "Recognize unprofessional conduct and determine an appropriate response, including reporting obligations."},
        "jurisdiction": {"scope": "PROVINCIAL_TERRITORIAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 5, "preferred_item_forms": ["PROFESSIONAL_RESPONSE"],
        "clinical_source_organizations": ["provincial/territorial Colleges/regulators"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-15": {
        "classification": "COMPONENT",
        "mcc_evidence": [role_ref("Scholar", "Apply principles of research and information management to learning and practice", strength="WEAK",
            rationale="Group's enabling text covers evaluating information quality including 'conformity to ethical standards', but this is about appraising existing research, not conducting ethically-approved research (REB approval, research consent) - a genuine but indirect link.", requires_scope_review=True)],
        "scope_depth": "RECOGNIZE",
        "testable_competencies": {"ethical_reasoning": "Recognize the requirement for research ethics board approval and informed consent in human research."},
        "jurisdiction": {"scope": "CANADA_WIDE_PROFESSIONAL_PRINCIPLE", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 2, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION"],
        "clinical_source_organizations": ["Government of Canada (Tri-Council Policy Statement)"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-16": {
        "classification": "DIRECT",
        "mcc_evidence": [role_ref("Leader/Manager", "Effectively manage practice and career", strength="STRONG",
            rationale="Group's enabling text directly names this: 'Avoid conflicts of interest by maintaining ethical relations with the industry, suppliers and other medically relevant groups.'")],
        "scope_depth": "RECOGNIZE_AND_ACT",
        "testable_competencies": {"legal_professional_action": "Recognize and appropriately manage conflicts of interest arising from industry relationships."},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 3, "preferred_item_forms": ["PROFESSIONAL_RESPONSE"],
        "clinical_source_organizations": ["CMA"], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-17": {
        "classification": "DIRECT",
        "mcc_evidence": [role_ref("Leader/Manager", "Allocate health care resources effectively", strength="STRONG",
            rationale="Exact title match with the group's own name: 'Allocate health care resources effectively', covering utilizing resources 'prudently and economically', 'equitably and without bias', and 'in an ethical and informed manner, while balancing individual and societal needs.'")],
        "scope_depth": "RECOGNIZE_AND_ACT",
        "testable_competencies": {"ethical_reasoning": "Apply principles of equitable and ethical resource allocation in a scenario of scarcity."},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 3, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION"],
        "clinical_source_organizations": [], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-18": {
        "classification": "UNCERTAIN", "mcc_evidence": [],
        "scope_depth": "RECOGNIZE",
        "testable_competencies": {"ethical_reasoning": "Balance a physician's own conscientious objection with the duty to provide timely patient access/effective referral."},
        "jurisdiction": {"scope": "PROVINCIAL_TERRITORIAL", "province_required_in_question": True, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 1, "preferred_item_forms": ["PROFESSIONAL_RESPONSE"],
        "clinical_source_organizations": ["provincial/territorial Colleges/regulators"], "fresh_legal_verification_required": True,
        "uncertain_reason": "No MCC objective (Medical Expert or role-level) was found that explicitly or substantially addresses conscientious objection. Professional role's 'Integrity' group covers general ethical conduct but does not name this topic. Flagged UNCERTAIN rather than force-mapped to a weakly-related objective.",
    },
    "SU-ELOM-19": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("126", "Clinical informatics", strength="STRONG",
            rationale="Direct title match. Objective's rationale explicitly covers 'electronic health records [EHRs], virtual care, and advanced analytics [e.g., artificial intelligence and machine learning]'.")],
        "scope_depth": "RECOGNIZE_AND_ACT",
        "testable_competencies": {
            "system_navigation": "Use health information systems safely, recognizing their limitations.",
            "ethical_reasoning": "Recognize ethical considerations in digital health technology use (e.g., AI-assisted decision-making, EHR privacy).",
        },
        "jurisdiction": {"scope": "CANADA_WIDE_PROFESSIONAL_PRINCIPLE", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 3, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION", "SYSTEM_ORGANIZATIONAL_DECISION"],
        "clinical_source_organizations": ["Health Canada", "provincial/territorial privacy legislation"], "fresh_legal_verification_required": True,
    },
    "SU-ELOM-20": {
        "classification": "COMPONENT",
        "mcc_evidence": [
            obj_ref("127", "Providing anti-oppressive health care", strength="STRONG", rationale="Objective's rationale explicitly names colonialism and 'responding to the calls to action from the Truth and Reconciliation Commission of Canada' as foundational."),
            obj_ref("78-9", "Indigenous health", strength="STRONG", rationale="Objective's rationale explicitly requires responding to 'the Calls to Action of the Truth and Reconciliation Commission' and understanding 'root causes of the inequitable health care and health outcomes experienced by Indigenous Peoples'."),
        ],
        "scope_depth": "RECOGNIZE_AND_ACT",
        "testable_competencies": {"ethical_reasoning": "Articulate how colonialism's historical impact and the TRC's Calls to Action inform current clinical and system-level practice."},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 3, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION"],
        "clinical_source_organizations": ["authoritative Indigenous-health sources", "Truth and Reconciliation Commission of Canada"], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-21": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("78-9", "Indigenous health", strength="STRONG",
            rationale="Objective's key_objectives text explicitly requires demonstrating 'an awareness of the root causes of the inequitable health care and health outcomes experienced by Indigenous Peoples' and applying 'population health principles in understanding and advocating for Indigenous Peoples' health'.")],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {
            "health_advocacy": "Recognize structural/social determinants driving disproportionate disease burden in Indigenous populations.",
            "ethical_reasoning": "Provide anti-racist, culturally safe, trauma-informed care.",
        },
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 5, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION", "MOST_APPROPRIATE_ACTION"],
        "clinical_source_organizations": ["authoritative Indigenous-health sources", "PHAC"], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-22": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("78-9", "Indigenous health", strength="STRONG",
            rationale="Objective's key_objectives text explicitly requires the candidate to 'articulate the inherent Indigenous and Treaty Rights (e.g., Medicine Chest Clause) relevant to the health of Indigenous Peoples' and apply population health principles at 'institutional' and 'societal' levels - directly covers coverage/jurisdiction content.")],
        "scope_depth": "RECOGNIZE_AND_ACT",
        "testable_competencies": {"system_navigation": "Navigate jurisdictional health coverage gaps affecting Indigenous patients (e.g., Jordan's Principle, NIHB)."},
        "jurisdiction": {"scope": "FEDERAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 3, "preferred_item_forms": ["SYSTEM_ORGANIZATIONAL_DECISION"],
        "clinical_source_organizations": ["Government of Canada / Indigenous Services Canada", "authoritative Indigenous-health sources"], "fresh_legal_verification_required": True,
        "cross_discipline_note": "Shares strong conceptual overlap with PHELO's population-health/jurisdiction content and with Pediatrics (Jordan's Principle specifically concerns children); Toronto Notes places the core content here in ELOM.",
    },
    "SU-ELOM-23": {
        "classification": "REFERENCE_ONLY", "mcc_evidence": [],
        "scope_depth": "OUT_OF_SCOPE_DETAIL", "testable_competencies": {},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 0, "preferred_item_forms": [],
        "zero_question_reason": "Pointer to a resource list, not independent testable content.",
        "clinical_source_organizations": [], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-24": {
        "classification": "REFERENCE_ONLY", "mcc_evidence": [],
        "scope_depth": "OUT_OF_SCOPE_DETAIL", "testable_competencies": {},
        "jurisdiction": NA_JURISDICTION,
        "minimum_question_coverage": 0, "preferred_item_forms": [],
        "zero_question_reason": "Chapter bibliography, no independent content.",
        "clinical_source_organizations": [], "fresh_legal_verification_required": False,
    },
    "SU-ELOM-25": {
        "classification": "DIRECT",
        "mcc_evidence": [obj_ref("121-5", "Legal system", strength="STRONG",
            rationale="Objective's rationale explicitly covers 'federal, provincial or territorial, and local laws and regulations' - directly matches this unit's criminal/civil/administrative and jurisdiction-varies-by-province framework.")],
        "scope_depth": "CORE_ACTION",
        "testable_competencies": {
            "legal_professional_action": "Distinguish criminal, civil, and administrative legal consequences of a given act, and recognize that criminal law is national while civil/administrative law varies by province/territory.",
        },
        "jurisdiction": {"scope": "FEDERAL", "province_required_in_question": False, "fresh_legal_verification_required": True},
        "minimum_question_coverage": 4, "preferred_item_forms": ["ETHICAL_LEGAL_ACTION"],
        "clinical_source_organizations": ["Government of Canada / Department of Justice", "provincial/territorial legislation", "CMPA"], "fresh_legal_verification_required": True,
    },
}


def build_crosswalk(units):
    entries = []
    unresolved = []
    for u in units:
        cw = CROSSWALK.get(u["study_unit_id"])
        if cw is None:
            unresolved.append({"study_unit_id": u["study_unit_id"], "title": u["title"], "reason": "No crosswalk entry defined."})
            continue
        coverage_weight = derive_coverage_weight(
            {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 8: 5}.get(cw["minimum_question_coverage"], 3),
            cw["classification"],
        )
        entry = {
            "study_unit_id": u["study_unit_id"],
            "title": u["title"],
            "classification": cw["classification"],
            "mcc_evidence": cw["mcc_evidence"],
            "scope_depth": cw["scope_depth"],
            "testable_competencies": cw["testable_competencies"],
            "jurisdiction": cw["jurisdiction"],
            "question_planning": {
                "coverage_weight": coverage_weight,
                "minimum_question_coverage": cw["minimum_question_coverage"],
                "preferred_item_forms": cw["preferred_item_forms"],
            },
            "page_mapping_precision": u["page_mapping_precision"],
            "clinical_source_organizations": cw["clinical_source_organizations"],
            "fresh_legal_verification_required": cw["fresh_legal_verification_required"],
        }
        if "zero_question_reason" in cw:
            entry["zero_question_reason"] = cw["zero_question_reason"]
        if "cross_discipline_note" in cw:
            entry["cross_discipline_note"] = cw["cross_discipline_note"]
        if cw["classification"] == "UNCERTAIN":
            unresolved.append({"study_unit_id": u["study_unit_id"], "title": u["title"], "reason": cw.get("uncertain_reason", "Insufficient evidence.")})
        entries.append(entry)
    return entries, unresolved


def main():
    nodes = load_inventory_nodes()
    nodes_by_id = node_lookup(nodes)
    units = enrich_study_units(STUDY_UNITS, nodes_by_id)

    all_node_ids = set(nodes_by_id.keys())
    assigned = set()
    for u in units:
        assigned.update(u["source_node_ids"])
    organizational = set(ORGANIZATIONAL_HEADER_NODES.keys())
    excluded_artifacts = set(EXCLUDED_ARTIFACT_NODES.keys())
    unassigned = all_node_ids - assigned - organizational - excluded_artifacts
    double_assigned = {}
    seen = {}
    for u in units:
        for nid in u["source_node_ids"]:
            seen.setdefault(nid, []).append(u["study_unit_id"])
    for nid, us in seen.items():
        if len(us) > 1:
            double_assigned[nid] = us

    accounted = assigned | organizational | excluded_artifacts

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "study_units.json", "w") as f:
        json.dump({
            "schema_version": "1.0",
            "generated_at": GENERATED_AT,
            "chapter_code": CHAPTER_CODE,
            "chapter_title": "Ethical, Legal, and Organizational Medicine",
            "source_toc_inventory": "research/tn2025/toc_inventory.json",
            "methodology_note": (
                "Study units derived from Toronto Notes SOURCE STRUCTURE, "
                "with THREE same-page TOC merges resolved by direct "
                "inspection of the raw OCR source (pdf page 21) rather than "
                "invented or guessed - see each affected unit's "
                "structural_rationale for the specific resolution."
            ),
            "total_study_units": len(units),
            "organizational_header_nodes": ORGANIZATIONAL_HEADER_NODES,
            "excluded_artifact_nodes": EXCLUDED_ARTIFACT_NODES,
            "study_units": units,
        }, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote study_units.json: {len(units)} units")
    print(f"Total chapter nodes: {len(all_node_ids)}")
    print(f"Assigned: {len(assigned)}, Organizational: {len(organizational)}, "
          f"Excluded artifacts: {len(excluded_artifacts)}")
    print(f"Unassigned (should be empty): {unassigned}")
    print(f"Double-assigned (should be empty): {double_assigned}")
    print(f"Total accounted: {len(accounted)} / {len(all_node_ids)}")

    audit = {
        "generated_at": GENERATED_AT,
        "chapter_code": CHAPTER_CODE,
        "raw_toc_nodes": len(nodes),
        "raw_leaf_nodes": len([n for n in nodes if n["structural_type"] == "topic"]) + len([
            n for n in nodes if n["structural_type"] == "section"
            and not any(t["parent_id"] == n["node_id"] for t in nodes if t["structural_type"] == "topic")
        ]),
        "derived_study_units": len(units),
        "unassigned_source_nodes": sorted(unassigned),
        "unassigned_source_node_count": len(unassigned),
        "double_assigned_source_nodes": double_assigned,
        "organizational_header_nodes_accounted_for": len(organizational),
        "excluded_artifact_nodes_accounted_for": len(excluded_artifacts),
        "excluded_artifact_details": EXCLUDED_ARTIFACT_NODES,
        "coverage_check": {
            "total_nodes": len(all_node_ids),
            "assigned_to_a_study_unit": len(assigned),
            "accounted_as_organizational_header": len(organizational),
            "accounted_as_excluded_artifact": len(excluded_artifacts),
            "total_accounted": len(accounted),
            "fully_accounted": accounted == all_node_ids,
        },
        "source_ambiguities_resolved": [
            "ELOM.S01 merge (Acronyms + Ethical Issues in Health Care + "
            "Canadian Healthcare System, all sharing page ELOM2) - resolved "
            "by direct inspection of raw OCR page 21, split into SU-ELOM-01"
            " through SU-ELOM-06.",
            "ELOM.S03 merge (Clinical Informatics and Ethical "
            "Considerations + Indigenous Health, both sharing page "
            "ELOM25) - resolved by direct inspection of raw OCR page 21, "
            "split into SU-ELOM-19 through SU-ELOM-23.",
            "ELOM.S04 'References' topic-children misattribution (12 "
            "genuine content nodes about the Canadian legal framework, "
            "actually printed on the chapter's TOC page 21, not the "
            "bibliography pages 52-54, misattributed as bibliography "
            "sub-topics by the TOC parser) - resolved by direct text "
            "search confirming this content's true source location, "
            "reattributed to SU-ELOM-25. One further node (T13) confirmed "
            "as a genuine OCR artifact and explicitly excluded.",
        ],
        "no_source_node_silently_dropped": len(unassigned) == 0,
        "page_traceability_valid": all(
            u["pdf_page_range"][0] >= 21 and u["pdf_page_range"][1] <= 54
            for u in units
        ),
        "result": "PASS" if (
            len(unassigned) == 0 and len(double_assigned) == 0
            and accounted == all_node_ids
        ) else "FAIL",
    }

    with open(OUT_DIR / "study_units_audit.json", "w") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
        f.write("\n")

    md_lines = [
        "# ELOM Study-Unit Consolidation Audit",
        "",
        f"**Generated:** {GENERATED_AT}",
        f"**Result:** {'✅ PASS' if audit['result'] == 'PASS' else '❌ FAIL'}",
        "",
        "## Coverage",
        "",
        f"- Raw TOC nodes: {audit['raw_toc_nodes']}",
        f"- Raw leaf nodes: {audit['raw_leaf_nodes']}",
        f"- Derived study units: {audit['derived_study_units']}",
        f"- Unassigned source nodes: {len(unassigned)}",
        f"- Double-assigned source nodes: {len(double_assigned)}",
        f"- Organizational header nodes (not units, not dropped): {len(organizational)}",
        f"- Excluded OCR-artifact nodes (not units, not dropped, explicitly documented): {len(excluded_artifacts)}",
        f"- **Total accounted:** {len(accounted)} / {len(all_node_ids)} ({'fully accounted' if accounted == all_node_ids else 'GAP'})",
        "",
        "## Source Ambiguities Found and Resolved",
        "",
        "Unlike Cardiology (one same-page merge), ELOM's TOC page contains THREE separate same-page-merge/misattribution artifacts, each resolved by directly reading the raw OCR source rather than guessed:",
        "",
    ]
    for note in audit["source_ambiguities_resolved"]:
        md_lines.append(f"- {note}")
    md_lines.extend([
        "",
        "## Excluded Artifact Nodes",
        "",
    ])
    for nid, reason in EXCLUDED_ARTIFACT_NODES.items():
        md_lines.append(f"**{nid}:** {reason}")
        md_lines.append("")
    md_lines.extend([
        "## Page Traceability",
        "",
        f"All {len(units)} study units' pdf_page_range falls within the chapter's own bounds (21-54): "
        f"{'✅ valid' if audit['page_traceability_valid'] else '❌ INVALID'}",
        "",
        "## Summary",
        "",
        f"Raw TOC nodes: {audit['raw_toc_nodes']}",
        f"Raw leaf nodes: {audit['raw_leaf_nodes']}",
        f"Derived study units: {audit['derived_study_units']}",
        f"Unassigned source nodes: {len(unassigned)}",
        "",
        f"**Study-unit derivation: {audit['result']}**",
        "",
    ])
    with open(OUT_DIR / "study_units_audit.md", "w") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"\nStudy-unit derivation result: {audit['result']}")

    # =========================================================================
    # CROSSWALK
    # =========================================================================
    crosswalk_entries, unresolved_mappings = build_crosswalk(units)

    with open(OUT_DIR / "crosswalk.json", "w") as f:
        json.dump({
            "schema_version": "1.0",
            "generated_at": GENERATED_AT,
            "chapter_code": CHAPTER_CODE,
            "source_authority": {
                "primary": "research/mcc/objectives_registry.json",
                "supporting": [
                    "research/mcc/study_smarter_discipline_mapping.json",
                    "research/mcc/blueprint.json",
                ],
                "methodology": "research/raw/broad_scope_memo_corrected_2026-08-24.md",
            },
            "total_study_units": len(units),
            "entries": crosswalk_entries,
        }, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(OUT_DIR / "unresolved_mappings.json", "w") as f:
        json.dump({
            "generated_at": GENERATED_AT,
            "total_unresolved": len(unresolved_mappings),
            "unresolved_mappings": unresolved_mappings,
        }, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nWrote crosswalk.json: {len(crosswalk_entries)} entries")
    print(f"Wrote unresolved_mappings.json: {len(unresolved_mappings)} unresolved")

    from collections import Counter
    classif_counts = Counter(e["classification"] for e in crosswalk_entries)
    confidence_counts = Counter(u["extraction_confidence"] for u in units)

    all_obj_ids = set()
    weak_mappings = []
    for e in crosswalk_entries:
        for m in e["mcc_evidence"]:
            if m["mcc_id"] is not None:
                all_obj_ids.add(m["mcc_id"])
            if m["mapping_strength"] == "WEAK":
                weak_mappings.append({"study_unit_id": e["study_unit_id"], "mcc_id": m["mcc_id"], "role": m["canmeds_role"]})

    with open(REGISTRY_PATH) as f:
        reg = json.load(f)
    valid_ids = {o["mcc_id"] for o in reg["objectives"] if o["role"] == "Medical Expert" and o["mcc_id"]}
    invalid_ids = all_obj_ids - valid_ids

    jurisdiction_sensitive = [
        e["study_unit_id"] for e in crosswalk_entries
        if e["jurisdiction"]["scope"] not in ("NOT_APPLICABLE",)
    ]
    fresh_legal_verification_units = [e["study_unit_id"] for e in crosswalk_entries if e["fresh_legal_verification_required"]]

    zero_q_units = [e for e in crosswalk_entries if e["question_planning"]["minimum_question_coverage"] == 0]
    zero_q_no_reason = [e for e in zero_q_units if "zero_question_reason" not in e]

    crosswalk_audit = {
        "generated_at": GENERATED_AT,
        "chapter_code": CHAPTER_CODE,
        "study_units_total": len(units),
        "classification_counts": dict(classif_counts),
        "confidence_counts": {
            "HIGH": sum(1 for u in units if u["extraction_confidence"] == "HIGH"),
            "MEDIUM": sum(1 for u in units if u["extraction_confidence"] == "MEDIUM"),
            "LOW": sum(1 for u in units if u["extraction_confidence"] == "LOW"),
        },
        "weak_mappings": weak_mappings,
        "weak_mapping_count": len(weak_mappings),
        "jurisdiction_sensitive_units": jurisdiction_sensitive,
        "jurisdiction_sensitive_unit_count": len(jurisdiction_sensitive),
        "units_requiring_future_legal_verification": fresh_legal_verification_units,
        "units_requiring_future_legal_verification_count": len(fresh_legal_verification_units),
        "mcc_objective_ids_used": sorted(all_obj_ids),
        "mcc_objective_id_count": len(all_obj_ids),
        "invalid_objective_ids": sorted(invalid_ids),
        "invalid_objective_id_count": len(invalid_ids),
        "units_with_zero_planned_questions": len(zero_q_units),
        "zero_question_units_missing_reason": len(zero_q_no_reason),
        "unresolved_mappings_count": len(unresolved_mappings),
        "gate_result": "PASS" if (
            len(invalid_ids) == 0 and len(zero_q_no_reason) == 0
        ) else "FAIL",
    }

    with open(OUT_DIR / "crosswalk_audit.json", "w") as f:
        json.dump(crosswalk_audit, f, indent=2, ensure_ascii=False)
        f.write("\n")

    md = []
    md.append("# ELOM MCC Crosswalk Audit")
    md.append("")
    md.append(f"**Generated:** {GENERATED_AT}")
    md.append(f"**Result:** {'✅ PASS' if crosswalk_audit['gate_result']=='PASS' else '❌ FAIL'}")
    md.append("")
    md.append(f"**Study units total:** {len(units)}")
    md.append("")
    md.append("## Classification Breakdown")
    md.append("")
    for cls in ["DIRECT", "COMPONENT", "CROSS_DISCIPLINE", "SUPPORTING_KNOWLEDGE", "SPECIALIST_DETAIL", "REFERENCE_ONLY", "UNCERTAIN"]:
        md.append(f"- {cls}: {classif_counts.get(cls, 0)}")
    md.append("")
    md.append("## Extraction Confidence")
    md.append("")
    md.append(f"- HIGH: {crosswalk_audit['confidence_counts']['HIGH']}")
    md.append(f"- MEDIUM: {crosswalk_audit['confidence_counts']['MEDIUM']}")
    md.append(f"- LOW: {crosswalk_audit['confidence_counts']['LOW']}")
    md.append("")
    md.append("## Jurisdiction Model")
    md.append("")
    md.append(f"- Jurisdiction-sensitive units (scope != NOT_APPLICABLE): {len(jurisdiction_sensitive)}")
    md.append(f"- Units requiring future legal verification: {len(fresh_legal_verification_units)}")
    md.append("")
    md.append("## MCC Objective ID Usage")
    md.append("")
    md.append(f"- MCC Objective IDs used: {len(all_obj_ids)} — {sorted(all_obj_ids)}")
    md.append(f"- Invalid Objective IDs: {len(invalid_ids)} {'✅' if not invalid_ids else '❌ ' + str(invalid_ids)}")
    md.append(f"- WEAK mappings: {len(weak_mappings)}")
    md.append("")
    md.append("## Zero-Question Units")
    md.append("")
    md.append(f"Units with 0 minimum_question_coverage: {len(zero_q_units)}")
    md.append(f"Missing explicit reason: {len(zero_q_no_reason)} {'✅' if not zero_q_no_reason else '❌'}")
    md.append("")
    md.append("## Unresolved Mappings")
    md.append("")
    md.append(f"{len(unresolved_mappings)}")
    for u in unresolved_mappings:
        md.append(f"- {u['study_unit_id']}: {u['title']} — {u['reason']}")
    md.append("")

    with open(OUT_DIR / "crosswalk_audit.md", "w") as f:
        f.write("\n".join(md) + "\n")

    print(f"\nCrosswalk audit result: {crosswalk_audit['gate_result']}")
    print(f"Classification counts: {dict(classif_counts)}")
    print(f"Jurisdiction-sensitive units: {len(jurisdiction_sensitive)}")
    print(f"Units requiring future legal verification: {len(fresh_legal_verification_units)}")
    print(f"Invalid objective IDs: {len(invalid_ids)}")
    print(f"WEAK mappings: {len(weak_mappings)}")
    print(f"Unresolved: {len(unresolved_mappings)}")

    return units, crosswalk_entries, crosswalk_audit


if __name__ == "__main__":
    main()
