"""Build canonical research/mcc/objectives_registry.json from official MCC sources.

Data provenance:
- Medical Expert role: official MCC Objectives Online Web Service
  (https://mcc.ca/wp-json/mcc/medical-expert/en/?type=json&content=true),
  documented at https://mcc.ca/wp-content/uploads/Exams-objectives-web-service-documentation.pdf
- Six non-Medical-Expert roles (Collaborator, Communicator, Health Advocate,
  Leader/Manager, Professional, Scholar): official static role pages at
  https://mcc.ca/objectives/<role>/ (no web-service endpoint documented or
  available for these roles as of 2026-08-24 - confirmed via HTTP 404 on the
  same URL pattern used for medical-expert).

The web-service "id" field for Medical Expert objectives has been verified
(4/4 manual spot-checks: Headache=39, Limp in children=20, Abnormal lipids=51,
Vascular injury=109-15) to be IDENTICAL to the "Legacy ID" displayed on each
individual official objective page. No separate "current ID" system was found;
mcc_id and legacy_id are therefore the same value for Medical Expert records.
"""
import html
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "research" / "mcc" / "raw_retrieval"
OUT = REPO / "research" / "mcc" / "objectives_registry.json"

RETRIEVED_AT = "2026-08-24"


def strip_html_to_text(fragment: str) -> str:
    """Deterministically convert a WP block HTML fragment to plain text,
    preserving list nesting with '-' bullets and numbered sub-items."""
    if not fragment:
        return ""
    s = fragment
    # Normalize block-level tags to newlines before stripping
    s = re.sub(r"<li[^>]*>", "\n- ", s)
    s = re.sub(r"</li>", "", s)
    s = re.sub(r"<(p|h[1-6]|/p|/h[1-6])[^>]*>", "\n", s)
    s = re.sub(r"<(ol|ul|/ol|/ul)[^>]*>", "\n", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    # Strip remaining tags (links etc.) but keep their text content
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def parse_medical_expert_content(raw_html: str) -> dict:
    """Split official content HTML into named sections by its own
    <h2 class="wp-block-heading"> markers. Section names are official MCC
    section headings verbatim (Rationale, Causal Conditions, Key Objectives,
    Enabling Objectives) - do not rename or reinterpret them."""
    if not raw_html:
        return {"raw_html": "", "sections": {}}

    heading_pattern = re.compile(
        r'<h2 class="wp-block-heading">(.*?)</h2>', re.DOTALL
    )
    matches = list(heading_pattern.finditer(raw_html))
    sections = {}
    sections_normalized = {}
    for i, m in enumerate(matches):
        heading_raw = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_html)
        body_html = raw_html[start:end]
        text = strip_html_to_text(body_html)
        sections[heading_raw] = text
        # normalize: lowercase, strip trailing 's' for simple pluralization,
        # so "Key Objective"/"Key Objectives" and "Causal conditions"/
        # "Causal Conditions" map to the same canonical key
        norm = heading_raw.lower().rstrip("s")
        sections_normalized[norm] = text

    return {"raw_html": raw_html, "sections": sections, "sections_normalized": sections_normalized}


def normalize_title_for_url_match(title: str) -> str:
    return title.strip().lower()


def load_medical_expert() -> list:
    with open(RAW / "medical-expert_web_service_response.json") as f:
        objectives = json.load(f)
    with open(RAW / "medical-expert_page_links.json") as f:
        links_data = json.load(f)

    title_to_url = {}
    for link in links_data["links"]:
        if "#" in link["href"]:
            continue
        title_to_url[normalize_title_for_url_match(link["text"])] = link["href"]

    records = []
    unmatched_urls = []
    for obj in objectives:
        title_key = normalize_title_for_url_match(obj["title"])
        official_url = title_to_url.get(title_key)
        if official_url is None:
            unmatched_urls.append(obj["title"])

        parsed = parse_medical_expert_content(obj.get("content", ""))
        group = obj.get("group") or {}
        group_id = group.get("id") or None
        group_title = group.get("title") or None

        record = {
            "mcc_id": obj["id"],
            "legacy_id": obj["id"],
            "legacy_id_verification": "OFFICIAL_CONFIRMED",
            "legacy_id_verification_note": (
                "Web-service 'id' field confirmed identical to page-displayed "
                "'Legacy ID' via manual spot-check against official objective "
                "pages (n=4: id 39, 20, 51, 109-15). No separate current-ID "
                "system was found on official MCC pages for Medical Expert."
            ),
            "title": obj["title"],
            "role": "Medical Expert",
            "role_code": obj.get("role", "expert"),
            "language": obj.get("language", "en"),
            "version": obj.get("version"),
            "group": {
                "id": group_id,
                "title": group_title,
            },
            "medical_expert_category": (
                "Population health and its determinants" if group_id == "Group-78" else
                "Ethics, legal, and organizational aspects of medicine" if group_id == "Group-121" else
                "Clinical presentation/diagnosis"
            ),
            "official_url": official_url,
            "content": {
                "rationale": parsed["sections_normalized"].get("rationale"),
                "causal_conditions": parsed["sections_normalized"].get("causal condition"),
                "key_objectives": parsed["sections_normalized"].get("key objective"),
                "enabling_objectives": parsed["sections_normalized"].get("enabling objective"),
                "other_sections": {
                    k: v for k, v in parsed["sections"].items()
                    if k.lower().rstrip("s") not in (
                        "rationale", "causal condition", "key objective", "enabling objective"
                    )
                },
                "section_headings_found_raw": sorted(parsed["sections"].keys()),
            },
            "provenance": {
                "web_service_url": "https://mcc.ca/wp-json/mcc/medical-expert/en/?type=json&content=true",
                "page_url": official_url,
                "retrieved_at": RETRIEVED_AT,
                "legacy_id_source": official_url,
            },
            "verification_status": "OFFICIAL_CONFIRMED" if official_url else "URL_UNMATCHED_TITLE_MISMATCH",
        }
        records.append(record)

    return records, unmatched_urls


# Non-Medical-Expert roles: no documented/available web-service endpoint.
# Content captured verbatim from official static role pages via browser
# retrieval on 2026-08-24. These roles are represented by MCC as broad
# cross-disciplinary competency statements, NOT as per-presentation records
# with Legacy IDs - preserving the actual official MCC structure rather than
# forcing a Medical-Expert-shaped schema onto them, per task instructions.

NON_EXPERT_ROLES = {
    "Collaborator": {
        "official_url": "https://mcc.ca/objectives/collaborator/",
        "description": "As Collaborators, physicians work in partnership with others to achieve optimal patient care.",
        "source_attribution": "Royal College of Physicians and Surgeons of Canada",
        "objective_groups": [
            {
                "group_title": "Collaborate effectively within the health care system",
                "enabling_objectives": [
                    "Work effectively within the health care system, both in an institutional environment and in the community",
                    "Explain how the organization, policies, and financing of the health care system impact collaborative patient care",
                    "Discuss the role of, and work collaboratively with, community and social service agencies (e.g., schools, municipalities and non-governmental organizations) and local, provincial and national agencies/governments as appropriate to address the concerns at a population level.",
                    "Participate effectively in and with health organizations, ranging from individual clinical practices to provincial organizations, exerting a positive influence on clinical practice and policy-making.",
                    "Discuss the roles and services provided by government, social agencies, or community organizations in providing services to special populations.",
                ],
            },
            {
                "group_title": "Consult effectively with physicians and other health care professionals to provide care for individuals, communities, and populations",
                "enabling_objectives": [
                    "Explain how personal values, biases, and professional limitations impact the consultation process",
                    "Recognize that the clinical situation requires expertise beyond one's own, and determine the urgency",
                    "Identify an individual or service with the required skill or expertise",
                    "Communicate well in writing and/or orally with the consultant",
                    "Ensure that the consultation takes place at an appropriate time and place",
                    "Ensure that the consultant's oral or written report is received",
                    "Carry out recommendations as appropriate and/or ensure that transfer of care takes place",
                    "Act responsibly and expeditiously when other health professionals request assistance",
                ],
            },
            {
                "group_title": "Participate effectively on health care teams",
                "enabling_objectives": [
                    "Explain the scope of practice and demonstrate respect for the expertise of each member of the team",
                    "Describe and adapt to differences in team organization and function",
                    "Agree on and implement team members' responsibilities and roles, including leadership",
                    "Implement protocols to ensure effective communication and accountabilities among team members, especially at times of patient care transition",
                    "Demonstrate respect for team members without bias (e.g., bias related to gender, ethnicity, cultural background or health care role)",
                    "Include the patient and family as part of the care team with the goal of appropriate degrees of shared decision-making",
                    "Share patient information appropriately, while respecting confidentiality",
                    "Contribute to intra- and inter-disciplinary teams related to institutional or other activities (e.g., quality assurance, educational committees)",
                ],
            },
            {
                "group_title": "Manage conflict effectively",
                "enabling_objectives": [
                    "Recognize and prevent tensions that may lead to conflict",
                    "Use strategies to deal with conflict through negotiation and collaboration, while respecting the views and positions of others",
                    "Seek help and advice when necessary, recognizing personal limitations in conflict resolution",
                ],
            },
        ],
    },
    "Communicator": {
        "official_url": "https://mcc.ca/objectives/communicator/",
        "description": "As communicators, physicians effectively facilitate the patient-physician relationship and the dynamic exchanges that occur before, during, and after medical encounters.",
        "source_attribution": "Adapted from “CanMEDS 2015 Physician Competency Framework” by the Royal College of Physicians and Surgeons of Canada, 2015.",
        "objective_groups": [
            {
                "group_title": "Appropriately develop and maintain ethical relationships, rapport, and trust with patients, families, and communities",
                "enabling_objectives": [
                    "Initiate an interview with the patient by greeting with respect, attending to comfort and to the need for an interpreter if applicable, orienting to the interview, and consulting with the patient to establish the reason for the visit",
                    "Use appropriate nonverbal communication (positioning, posture, facial expression)",
                    "Tailor the interview to the clinical context (emergency department, clinic)",
                    "Seek consent from competent patients before involving family members",
                    "When appropriate, facilitate collaboration among families and patients, while maintaining patient wishes as the priority, ensuring confidentiality, and respecting patient autonomy",
                    "Determine an appropriate substitute decision-maker, as required, and document appropriately",
                ],
            },
            {
                "group_title": "Accurately elicit relevant information and perspectives from patients and families, colleagues, and other professionals",
                "enabling_objectives": [
                    "Elicit patient information through active listening and the appropriate use of open and closed questions, as well as using clear language appropriate to the patient's understanding",
                    "Appropriately use interviewing skills such as clarifying, bridging, and summarizing",
                    "Gather information about the patient's concerns, beliefs, expectations, and illness experience",
                    "Receive relevant information from other sources such as the patient's family, caregivers, and other professionals and, with the patient's permission, seek out additional information",
                ],
            },
            {
                "group_title": "Accurately convey relevant information and explanations to patients, families, and communities",
                "enabling_objectives": [
                    "Recognize how one's own values/beliefs may bias how one approaches communication with patients and families",
                    "Disclose to the patient personal values or beliefs that may limit professional involvement",
                    "Respect patients' rights to be given complete and truthful information",
                    "Identify the personal and cultural context of the patient, and the manner in which it may influence the patient's choices",
                    "Provide information using clear language appropriate to the patient's understanding, checking for understanding, and clarifying if necessary",
                    "Adhere to requirements for obtaining informed consent",
                ],
            },
            {
                "group_title": "Effectively communicate in challenging situations (delivering bad news, addressing anger, confusion, medical error, misunderstanding, and media interviews)",
                "enabling_objectives": [
                    "Disclose error and adverse events in a prompt and truthful manner",
                ],
            },
            {
                "group_title": "Develop a shared plan of care with patients, their families, and other professionals",
                "enabling_objectives": [
                    "Establish a common understanding and negotiate agreement concerning diagnosis, management, and follow-up",
                    "Communicate clearly and effectively the reasons for referral and the consultant's responsibilities for patient care",
                ],
            },
            {
                "group_title": "Effectively convey oral and written information associated with a medical encounter",
                "enabling_objectives": [
                    "Effectively present information about clinical encounters and management plans to patients and their families",
                    "Maintain comprehensive, legible, and up-to-date medical records, forms, and reports, and retain those as required",
                    "Allow patients access to their medical records and disclose to others only with the patient's consent or with appropriate legal authority (to family members, physicians or other health care providers, and to third parties)",
                    "Write prescriptions correctly and legibly",
                    "Adhere to legal requirements for writing narcotic prescriptions",
                    "Communicate effectively with third parties other than health professionals",
                    "Disclose patient information only when legally permitted",
                    "Transmit information to third parties (insurance companies, government agencies) truthfully and in a timely manner",
                    "Adhere to the ethical and legal requirements of confidentiality in all professional communication",
                    "Maintain confidentiality of medical records.",
                    "Know the exceptions to confidentiality and when it must or may be breached (e.g., duty to warn or report, child abuse, notifiable diseases)",
                    "Recognize the duty to inform patients about mandatory disclosures",
                    "Mitigate the risk of breaches to confidentiality posed by electronic communication (e.g., use of encryption, use of virtual private networks, verification of demographic information)",
                    "Avoid inappropriate use of social media",
                ],
            },
        ],
    },
    "Health Advocate": {
        "official_url": "https://mcc.ca/objectives/health-advocate/",
        "description": "Through advocacy, physicians play an important role in disease prevention and in protecting and promoting the health of patients, communities, and populations.",
        "source_attribution": None,
        "contextual_considerations": {
            "determinants_of_health": {
                "social_and_economic_factors": [
                    "Income", "Social status", "Education and literacy",
                    "Social support networks", "Oppression and discrimination (e.g., racism, sexism)",
                ],
                "environmental_and_physical_factors": [
                    "Employment and working conditions", "Food security", "Housing", "Access to health care",
                ],
                "personal_factors": [
                    "Health practices and coping skills", "Childhood experiences",
                    "Gender identity", "Biological and genetic endowment",
                ],
                "government_policies": [],
            }
        },
        "key_objectives": [
            "Given a patient, community, or population with health inequities, the candidate will identify the social and structural factors that are affecting health",
            "Describe the impact of these factors",
            "Suggest interventions to address these issues through advocacy",
        ],
        "objective_groups": [
            {
                "group_title": "Given a patient, community, or population with health inequities, the candidate will",
                "enabling_objectives": [
                    "Support and collaborate with the patient, community, or population affected",
                    "Identify and describe how factors in working, living, and community environments impact health, including personal, physical, and socioeconomic risk factors for health",
                    "potential conflicts between advocacy for equitable access to resources and ethical, medicolegal, and professional issues (e.g., stewardship of limited resources, economic constraints, commercialization of health care and scientific advances)",
                    "examples of government legislation, public and corporate policies, and trends that inequitably affect health locally, nationally, and/or globally",
                    "common barriers to health for equity-deserving populations, including health care access (e.g., people with disabilities, people who are marginalized, people who are underserved)",
                    "barriers to pharmaceutical access (e.g., special authorization requirements, manufacturing shortages, limited availability)",
                    "Describe ways to advocate for patients, communities, and populations, within the context of available resources, to overcome barriers for optimal health care (e.g., working with a partner, other health care workers, or community organizations).",
                ],
            }
        ],
    },
    "Leader/Manager": {
        "official_url": "https://mcc.ca/objectives/leader-manager/",
        "description": "As leaders and managers, physicians are integral participants in health care organizations. They organize and manage personal and professional practices, and contribute to the delivery of high-quality health care through clinical, administrative, and other activities.",
        "source_attribution": "Royal College of Physicians and Surgeons of Canada",
        "note": "The 2015 CanMEDs role revisions were changed by the Royal College from Manager to Leader, reducing the number and broadening the scope of the objectives to include an emphasis on quality assurance and patient safety. In order to be effective and actionable in terms of both personal and professional activities, the MCC has retained the Manager objectives, while adding objectives on quality assurance and patient safety.",
        "objective_groups": [
            {
                "group_title": "Effectively manage practice and career",
                "enabling_objectives": [
                    "Be able to fulfill, both as resident and in subsequent practice, the obligations and responsibilities of patient care including finances and human resources, where relevant.",
                    "Abide by the regulatory requirements governing medical office practice (maintenance of patient records, guidelines concerning prescriptions, especially narcotics)",
                    "Demonstrate leadership on health care teams and contribute to high-quality patient care by enhancing patient safety.",
                    "Avoid conflicts of interest by maintaining ethical relations with the industry, suppliers and other medically relevant groups.",
                    "Employ information technology as appropriate for patient care and practice management.",
                    "Utilize strategies to balance their professional and personal lives and access available support services if professional competence is compromised.",
                    "Adopt strategies for self-improvement and maintenance of competence.",
                    "Set priorities and manage time effectively in both their professional and personal lives.",
                ],
            },
            {
                "group_title": "Allocate health care resources effectively",
                "enabling_objectives": [
                    "Utilize all health resources (e.g. human, diagnostic, therapeutic) prudently and economically.",
                    "Utilize all health resources equitably and without bias or discrimination.",
                    "Manage limited health resources in an ethical and informed manner, while balancing individual and societal needs.",
                ],
            },
            {
                "group_title": "Participate appropriately in the health care system",
                "enabling_objectives": [
                    "Know the fundamental principles of the Canada Health Act",
                    "Describe the structure, function and financing of the Canadian health care system at the federal, provincial/territorial and local levels.",
                    "Describe the roles of physicians in developing and supporting the health care system (including health and prevention, advocacy groups, regulatory bodies, professional associations).",
                    "Contribute to the delivery of high-quality health care services by advocating for and participating in quality improvement.",
                    "Contribute to the delivery of high-quality health care services by promoting and practicing a culture of patient safety.",
                ],
            },
        ],
    },
    "Professional": {
        "official_url": "https://mcc.ca/objectives/professional/",
        "description": "Physicians play a unique societal role as professionals, requiring a mastery of knowledge, skills and behaviours dedicated to the health of individuals, communities, and society.",
        "source_attribution": "Adapted from “CanMEDS 2015 Physician Competency Framework” by the Royal College of Physicians and Surgeons of Canada, 2015.",
        "objective_groups": [
            {
                "group_title": "Accountability to patients and their families",
                "enabling_objectives": [
                    "Provide care that meets or exceeds expected standards of competence",
                    "Ensure continuity of care",
                    "Maintain patient confidentiality",
                    "Describe and implement current ethical and legal aspects of patient care",
                    "Recognise and manage conflicts of interest",
                    "Exhibit professional behaviours in the use of technology-enabled communication",
                    "Describe the organization of practice",
                ],
            },
            {
                "group_title": "Accountability to physician health and well-being for provision of optimal patient care",
                "enabling_objectives": [
                    "Maintain competence",
                    "Evaluate personal professional competence",
                    "Recognise personal limitations of competence",
                    "Pursue ongoing personal education to maintain competence",
                    "Manage influences on personal well-being that may affect professional performance",
                    "Manage personal and professional demands to ensure sustainable practice",
                    "Promote a culture that recognises, responds to, and supports colleagues in need",
                ],
            },
            {
                "group_title": "Accountability to the profession",
                "enabling_objectives": [
                    "Abide by the profession's rules, regulations, and ethical codes",
                    "Assume responsibility for one's own actions and model high standards of professional behaviour at all times",
                    "Recognise and respond to unprofessional and unethical behaviours in physicians and other health professional colleagues",
                    "Participate in peer assessment, teaching, and standard setting",
                    "Maintain confidentiality of professional documents (e.g., test materials, student evaluations)",
                ],
            },
            {
                "group_title": "Accountability to society",
                "enabling_objectives": [
                    "Respond to societal expectations of physicians",
                    "Demonstrate a commitment to patient safety and quality improvement",
                ],
            },
            {
                "group_title": "Integrity",
                "enabling_objectives": [
                    "Behave according to the highest standards of integrity, including ethical conduct, honesty, compassion, and dedication to the welfare of patients and society",
                    "Observe appropriate and/or legal boundaries in relationships with patients and health professionals",
                    "Avoid abuse of privilege",
                ],
            },
            {
                "group_title": "Altruism",
                "enabling_objectives": [
                    "Put the needs of others before one's own as the foundation of professional behaviour",
                    "Serve, when necessary, beyond normal duty or expectations, keeping in mind essential personal/professional balance",
                ],
            },
        ],
    },
    "Scholar": {
        "official_url": "https://mcc.ca/objectives/scholar/",
        "description": "As Scholars, physicians demonstrate a lifelong commitment to reflective learning, as well as to the dissemination, application, and translation of medical knowledge.",
        "source_attribution": "Royal College of Physicians and Surgeons of Canada",
        "objective_groups": [
            {
                "group_title": "Develop a plan for personal continued education",
                "enabling_objectives": [
                    "Describe the principles of maintaining competence",
                    "Use self-awareness in assessing competence, including reflection on personal practice",
                    "Evaluate personal learning outcomes (seek feedback from teachers, other health professionals, and other sources)",
                    "Document the personal learning process",
                ],
            },
            {
                "group_title": "Apply principles of research and information management to learning and practice",
                "enabling_objectives": [
                    "Describe the principles of evidence-based medicine",
                    "Retrieve information from appropriate sources",
                    "Evaluate information resources in order to select the best source for the information needed.",
                    "Formulate a specific question in order to guide the design of the information search.",
                    "Search the literature efficiently for evidence in order to answer a research or clinical question.",
                    "Assess the quality of information, using principles of critical appraisal: its relevance and importance, the appropriateness of its methodology, its conformity to ethical standards",
                    "Integrate retrieved information into clinical practice",
                    "Accept complexity, uncertainty, and ambiguity as part of medical practice",
                    "Apply the principles of screening and be able to evaluate the utility of a proposed screening intervention, including being able to discuss the potential for lead-time bias and length-prevalence bias and measurement issues (validity, sensitivity, specificity, positive predictive value, negative predictive value, bias, confounding, error, reliability)",
                ],
            },
            {
                "group_title": "Facilitate the learning of others as part of professional responsibility (patients, health professionals, society)",
                "enabling_objectives": [
                    "Disseminate new information as it becomes available",
                ],
            },
        ],
    },
}


def build_non_expert_records() -> list:
    records = []
    for role_name, data in NON_EXPERT_ROLES.items():
        record = {
            "mcc_id": None,
            "legacy_id": None,
            "legacy_id_verification": "NOT_APPLICABLE",
            "legacy_id_verification_note": (
                "This role has no documented web-service endpoint and no "
                "individual objective pages with Legacy IDs. MCC represents "
                "this role as a single broad competency statement, not as "
                "discrete presentation-level objectives. Structure preserved "
                "as officially published rather than forced into the "
                "Medical-Expert per-presentation shape."
            ),
            "title": role_name,
            "role": role_name,
            "role_code": role_name.lower().replace("/", "-").replace(" ", "-"),
            "language": "en",
            "version": None,
            "group": {"id": None, "title": None},
            "medical_expert_category": None,
            "official_url": data["official_url"],
            "content": {
                "description": data.get("description"),
                "source_attribution": data.get("source_attribution"),
                "note": data.get("note"),
                "key_objectives": data.get("key_objectives"),
                "contextual_considerations": data.get("contextual_considerations"),
                "objective_groups": data.get("objective_groups", []),
            },
            "applies_across_disciplines": True,
            "provenance": {
                "web_service_url": None,
                "web_service_attempt_result": (
                    "HTTP 404 rest_no_route at "
                    f"https://mcc.ca/wp-json/mcc/{role_name.lower().replace('/', '-').replace(' ', '-')}/en/"
                    "?type=json&content=true (attempted 2026-08-24; no "
                    "documented endpoint exists for this role per official "
                    "technical documentation, which covers medical-expert only)"
                ),
                "page_url": data["official_url"],
                "retrieved_at": RETRIEVED_AT,
                "legacy_id_source": None,
            },
            "verification_status": "OFFICIAL_CONFIRMED",
        }
        records.append(record)
    return records


def main():
    medical_expert_records, unmatched = load_medical_expert()
    non_expert_records = build_non_expert_records()

    all_records = medical_expert_records + non_expert_records

    role_counts = {}
    for r in all_records:
        role_counts[r["role"]] = role_counts.get(r["role"], 0) + 1

    registry = {
        "schema_version": "1.0",
        "retrieved_at": RETRIEVED_AT,
        "sources": [
            {
                "type": "web_service_json",
                "role": "Medical Expert",
                "url": "https://mcc.ca/wp-json/mcc/medical-expert/en/?type=json&content=true",
                "documentation_url": "https://mcc.ca/wp-content/uploads/Exams-objectives-web-service-documentation.pdf",
                "documentation_title": "Objectives Online Web Service (Medical Council of Canada Objectives Online Web Service User Guide)",
                "http_status": 200,
                "retrieved_at": RETRIEVED_AT,
                "record_count": len(medical_expert_records),
            },
            {
                "type": "static_page_scrape",
                "role": "Collaborator, Communicator, Health Advocate, Leader/Manager, Professional, Scholar",
                "url_pattern": "https://mcc.ca/objectives/<role-slug>/",
                "note": (
                    "No JSON/XML web-service endpoint exists for these six "
                    "roles. Confirmed via HTTP 404 (rest_no_route) when "
                    "attempting the same URL pattern used successfully for "
                    "medical-expert, e.g. "
                    "https://mcc.ca/wp-json/mcc/collaborator/en/?type=json&content=true "
                    "-> 404. The official technical documentation PDF "
                    "(2 pages) exclusively describes medical-expert endpoints."
                ),
                "http_status_of_attempted_api": 404,
                "retrieved_at": RETRIEVED_AT,
                "record_count": len(non_expert_records),
            },
        ],
        "roles": [
            "Medical Expert",
            "Collaborator",
            "Communicator",
            "Health Advocate",
            "Leader/Manager",
            "Professional",
            "Scholar",
        ],
        "role_counts": role_counts,
        "total_records": len(all_records),
        "structural_note": (
            "Medical Expert is represented as 192 discrete presentation/"
            "diagnosis, population-health, and ethics/legal/organizational "
            "objectives, each with an official Legacy ID, version, and URL. "
            "The six non-Medical-Expert roles are each represented as ONE "
            "record containing the role's full official competency "
            "statement structure (objective groups and enabling objectives), "
            "because MCC does not publish per-presentation IDs for these "
            "roles. This preserves actual official MCC structure rather "
            "than manufacturing a uniform shape. Per MCC Study Smarter "
            "guidance, all six non-Medical-Expert roles apply across all "
            "six qbank disciplines (applies_across_disciplines: true) and "
            "must not be force-assigned to a single discipline."
        ),
        "unmatched_url_titles": unmatched,
        "objectives": all_records,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")

    print(f"Wrote {len(all_records)} objective records to {OUT}")
    print(f"Role counts: {json.dumps(role_counts, indent=2)}")
    if unmatched:
        print(f"WARNING: {len(unmatched)} unmatched URLs: {unmatched}")


if __name__ == "__main__":
    main()
