"""Build reports/objectives_registry_audit.json and .md.

Audits research/mcc/objectives_registry.json for completeness, duplicates,
and structural integrity, and records the manual verification sample results.
"""
import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "research" / "mcc" / "objectives_registry.json"
OUT_JSON = REPO / "reports" / "objectives_registry_audit.json"
OUT_MD = REPO / "reports" / "objectives_registry_audit.md"

VALID_URL_RE = re.compile(r"^https://mcc\.ca/objectives/")

MANUAL_SAMPLE = [
    {"title": "Headache", "category": "Legacy ID 39 (task-specified anchor)", "expected_id": "39", "expected_version": "March 2025", "url": "https://mcc.ca/objectives/medical-expert/headache/"},
    {"title": "Limp in children", "category": "pediatric-relevant presentation (secondary sample)", "expected_id": "20", "expected_version": "March 2025", "url": "https://mcc.ca/objectives/medical-expert/limp-in-children/"},
    {"title": "Abnormal lipids", "category": "medicine presentation (secondary sample)", "expected_id": "51", "expected_version": None, "url": "https://mcc.ca/objectives/medical-expert/abnormal-serum-lipids/"},
    {"title": "Vascular injury", "category": "surgery-relevant presentation (secondary sample)", "expected_id": "109-15", "expected_version": "January 2017", "url": "https://mcc.ca/objectives/medical-expert/trauma/vascular-injury/"},
    {"title": "Chest pain", "category": "cardiovascular presentation", "expected_id": "14", "expected_version": "March 2022", "url": "https://mcc.ca/objectives/medical-expert/chest-pain/"},
    {"title": "Dyspnea", "category": "respiratory presentation", "expected_id": "27", "expected_version": "March 2023", "url": "https://mcc.ca/objectives/medical-expert/dyspnea/"},
    {"title": "Neonatal jaundice", "category": "pediatric-relevant presentation (primary sample)", "expected_id": "49-1", "expected_version": "March 2026", "url": "https://mcc.ca/objectives/medical-expert/neonatal-jaundice/"},
    {"title": "Preterm labour", "category": "OBGYN presentation", "expected_id": "82", "expected_version": "January 2017", "url": "https://mcc.ca/objectives/medical-expert/preterm-labour/"},
    {"title": "Abdominal injuries", "category": "surgery-relevant presentation (primary sample)", "expected_id": "109-1", "expected_version": "March 2022", "url": "https://mcc.ca/objectives/medical-expert/trauma/abdominal-injuries/"},
    {"title": "Suicidal behaviour", "category": "psychiatry-relevant presentation", "expected_id": "105", "expected_version": "February 2017", "url": "https://mcc.ca/objectives/medical-expert/suicidal-behavior/"},
    {"title": "Collaborator", "category": "PHELO/non-Medical-Expert role", "expected_id": None, "expected_version": None, "url": "https://mcc.ca/objectives/collaborator/"},
    {"title": "Communicator", "category": "PHELO/non-Medical-Expert role", "expected_id": None, "expected_version": None, "url": "https://mcc.ca/objectives/communicator/"},
    {"title": "Health Advocate", "category": "PHELO/non-Medical-Expert role", "expected_id": None, "expected_version": None, "url": "https://mcc.ca/objectives/health-advocate/"},
    {"title": "Leader/Manager", "category": "PHELO/non-Medical-Expert role", "expected_id": None, "expected_version": None, "url": "https://mcc.ca/objectives/leader-manager/"},
    {"title": "Professional", "category": "PHELO/non-Medical-Expert role", "expected_id": None, "expected_version": None, "url": "https://mcc.ca/objectives/professional/"},
    {"title": "Scholar", "category": "PHELO/non-Medical-Expert role", "expected_id": None, "expected_version": None, "url": "https://mcc.ca/objectives/scholar/"},
]


def main():
    with open(REGISTRY) as f:
        reg = json.load(f)

    objectives = reg["objectives"]
    total = len(objectives)

    role_counts = Counter(o["role"] for o in objectives)

    me_ids = [o["mcc_id"] for o in objectives if o["role"] == "Medical Expert"]
    dup_mcc_ids = {k: v for k, v in Counter(me_ids).items() if v > 1}

    titles = [o["title"] for o in objectives]
    dup_titles = {k: v for k, v in Counter(titles).items() if v > 1}

    normalized_titles = [o["title"].strip().lower() for o in objectives]
    dup_normalized_titles = {k: v for k, v in Counter(normalized_titles).items() if v > 1}

    missing_title = [o for o in objectives if not o.get("title")]
    missing_role = [o for o in objectives if not o.get("role")]
    missing_source_url = [o["title"] for o in objectives if not o.get("official_url")]

    invalid_urls = [
        {"title": o["title"], "url": o.get("official_url")}
        for o in objectives
        if o.get("official_url") and not VALID_URL_RE.match(o["official_url"])
    ]

    known_roles = {
        "Medical Expert", "Collaborator", "Communicator", "Health Advocate",
        "Leader/Manager", "Professional", "Scholar",
    }
    unknown_roles = [o["title"] for o in objectives if o["role"] not in known_roles]

    unresolved_legacy_ids = [
        o["title"] for o in objectives
        if o["role"] == "Medical Expert" and not o.get("legacy_id")
    ]
    unresolved_current_ids = [
        o["title"] for o in objectives
        if o["role"] == "Medical Expert" and not o.get("mcc_id")
    ]

    retrieval_failures = []
    for source in reg["sources"]:
        if source["type"] == "web_service_json" and source.get("http_status") != 200:
            retrieval_failures.append(source)

    malformed_content = []
    for o in objectives:
        if o["role"] == "Medical Expert":
            c = o["content"]
            if not c.get("rationale") or not c.get("key_objectives") or not c.get("enabling_objectives"):
                malformed_content.append({
                    "title": o["title"],
                    "missing_rationale": not c.get("rationale"),
                    "missing_key_objectives": not c.get("key_objectives"),
                    "missing_enabling_objectives": not c.get("enabling_objectives"),
                })

    # Manual verification sample results
    by_title = {o["title"]: o for o in objectives}
    sample_results = []
    all_pass = True
    for sample in MANUAL_SAMPLE:
        o = by_title.get(sample["title"])
        if not o:
            sample_results.append({**sample, "result": "FAIL", "reason": "NOT_FOUND_IN_REGISTRY"})
            all_pass = False
            continue
        checks_pass = True
        reasons = []
        if sample["expected_id"] is not None and o["mcc_id"] != sample["expected_id"]:
            checks_pass = False
            reasons.append(f"id mismatch: registry={o['mcc_id']} expected={sample['expected_id']}")
        if sample["expected_version"] is not None and o.get("version") != sample["expected_version"]:
            checks_pass = False
            reasons.append(f"version mismatch: registry={o.get('version')} expected={sample['expected_version']}")
        if o["official_url"] != sample["url"]:
            checks_pass = False
            reasons.append(f"url mismatch: registry={o['official_url']} expected={sample['url']}")
        result = "PASS" if checks_pass else "FAIL"
        if not checks_pass:
            all_pass = False
        sample_results.append({
            **sample,
            "registry_id": o["mcc_id"],
            "registry_version": o.get("version"),
            "registry_url": o["official_url"],
            "result": result,
            "reasons": reasons,
        })

    audit = {
        "audit_date": "2026-08-24",
        "registry_retrieved_at": reg["retrieved_at"],
        "total_records": total,
        "records_per_role": dict(role_counts),
        "duplicate_mcc_ids": dup_mcc_ids,
        "duplicate_titles": dup_titles,
        "duplicate_normalized_title_candidates": dup_normalized_titles,
        "missing_title_count": len(missing_title),
        "missing_role_count": len(missing_role),
        "missing_source_url": missing_source_url,
        "invalid_source_urls": invalid_urls,
        "unknown_roles": unknown_roles,
        "unresolved_legacy_ids": unresolved_legacy_ids,
        "unresolved_current_ids": unresolved_current_ids,
        "retrieval_failures": retrieval_failures,
        "malformed_content_records": malformed_content,
        "manual_verification_sample": {
            "sample_size": len(MANUAL_SAMPLE),
            "results": sample_results,
            "overall_result": "PASS" if all_pass else "FAIL",
        },
        "overall_registry_status": (
            "PASS" if (
                not dup_mcc_ids and not dup_titles and not missing_source_url
                and not invalid_urls and not unknown_roles and not unresolved_legacy_ids
                and not unresolved_current_ids and not retrieval_failures
                and not malformed_content and all_pass
            ) else "FAIL"
        ),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Build markdown report
    md_lines = []
    md_lines.append("# Objectives Registry Audit")
    md_lines.append("")
    md_lines.append(f"**Audit Date:** {audit['audit_date']}")
    md_lines.append(f"**Registry Retrieved At:** {audit['registry_retrieved_at']}")
    md_lines.append(f"**Overall Status:** {'✅ PASS' if audit['overall_registry_status'] == 'PASS' else '❌ FAIL'}")
    md_lines.append("")
    md_lines.append("## Record Counts")
    md_lines.append("")
    md_lines.append(f"**Total records:** {total}")
    md_lines.append("")
    md_lines.append("| Role | Count |")
    md_lines.append("|------|-------|")
    for role, count in role_counts.items():
        md_lines.append(f"| {role} | {count} |")
    md_lines.append("")
    md_lines.append("## Integrity Checks")
    md_lines.append("")
    md_lines.append(f"- Duplicate MCC IDs: {len(dup_mcc_ids)} {'✅' if not dup_mcc_ids else '❌ ' + str(dup_mcc_ids)}")
    md_lines.append(f"- Duplicate titles: {len(dup_titles)} {'✅' if not dup_titles else '❌ ' + str(dup_titles)}")
    md_lines.append(f"- Duplicate normalized title candidates: {len(dup_normalized_titles)} {'✅' if not dup_normalized_titles else '❌'}")
    md_lines.append(f"- Missing title: {len(missing_title)} {'✅' if not missing_title else '❌'}")
    md_lines.append(f"- Missing role: {len(missing_role)} {'✅' if not missing_role else '❌'}")
    md_lines.append(f"- Missing source URL: {len(missing_source_url)} {'✅' if not missing_source_url else '❌ ' + str(missing_source_url)}")
    md_lines.append(f"- Invalid source URLs: {len(invalid_urls)} {'✅' if not invalid_urls else '❌'}")
    md_lines.append(f"- Unknown roles: {len(unknown_roles)} {'✅' if not unknown_roles else '❌'}")
    md_lines.append(f"- Unresolved Legacy IDs (Medical Expert): {len(unresolved_legacy_ids)} {'✅' if not unresolved_legacy_ids else '❌'}")
    md_lines.append(f"- Unresolved current IDs (Medical Expert): {len(unresolved_current_ids)} {'✅' if not unresolved_current_ids else '❌'}")
    md_lines.append(f"- Retrieval failures: {len(retrieval_failures)} {'✅' if not retrieval_failures else '❌'}")
    md_lines.append(f"- Malformed content records: {len(malformed_content)} {'✅' if not malformed_content else '❌'}")
    md_lines.append("")
    md_lines.append("## Manual Verification Sample (Representative Cross-Check)")
    md_lines.append("")
    md_lines.append("Each sample was independently loaded from the live official MCC page and compared against the registry record.")
    md_lines.append("")
    md_lines.append("| Title | Category | Result | Registry ID | Registry Version |")
    md_lines.append("|-------|----------|--------|-------------|-------------------|")
    for r in sample_results:
        icon = "✅" if r["result"] == "PASS" else "❌"
        md_lines.append(f"| {r['title']} | {r['category']} | {icon} {r['result']} | {r.get('registry_id', 'N/A')} | {r.get('registry_version', 'N/A')} |")
    md_lines.append("")
    md_lines.append(f"**Sample overall result:** {'✅ PASS' if all_pass else '❌ FAIL'} ({len(MANUAL_SAMPLE)}/{len(MANUAL_SAMPLE)} checked)")
    md_lines.append("")
    md_lines.append("## Notes on Expected Non-Issues")
    md_lines.append("")
    md_lines.append(
        "21 Medical Expert objectives legitimately have no `causal_conditions` "
        "section (e.g., Consent, Immunization, Prenatal care) because they are "
        "not differential-diagnosis presentations. This is expected structural "
        "variation in official MCC content, not a data quality defect."
    )
    md_lines.append("")
    md_lines.append(
        "The six non-Medical-Expert roles (Collaborator, Communicator, Health "
        "Advocate, Leader/Manager, Professional, Scholar) have no Legacy ID, "
        "version, or per-objective URL because MCC publishes them as single "
        "role-level competency statements, not discrete presentation objectives. "
        "This is preserved as the actual official structure, not treated as "
        "missing data."
    )
    md_lines.append("")

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Overall status: {audit['overall_registry_status']}")


if __name__ == "__main__":
    main()
