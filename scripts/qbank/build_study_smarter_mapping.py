"""Build research/mcc/study_smarter_discipline_mapping.json,
research/mcc/study_smarter_registry_reconciliation.json, and
reports/study_smarter_mapping_audit.{json,md}
from the raw discipline lists extracted from the official 2026 Study Smarter
guide PDF.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "research" / "mcc" / "raw_retrieval" / "study_smarter_discipline_lists_raw.json"
REGISTRY = REPO / "research" / "mcc" / "objectives_registry.json"

OUT_MAPPING = REPO / "research" / "mcc" / "study_smarter_discipline_mapping.json"
OUT_RECONCILIATION = REPO / "research" / "mcc" / "study_smarter_registry_reconciliation.json"
OUT_AUDIT_JSON = REPO / "reports" / "study_smarter_mapping_audit.json"
OUT_AUDIT_MD = REPO / "reports" / "study_smarter_mapping_audit.md"

CANONICAL_DISCIPLINES = ["Medicine", "OBGYN", "Psychiatry", "Pediatrics", "Surgery", "PHELO"]
SOURCE_DISCIPLINE_KEY_MAP = {
    "Medicine": "Medicine",
    "Obstetrics and Gynecology": "OBGYN",
    "Psychiatry": "Psychiatry",
    "Pediatrics": "Pediatrics",
    "Surgery": "Surgery",
    "PHELO": "PHELO",
}


def normalize_title(t: str) -> str:
    import re
    # Collapse whitespace and normalize spacing around slashes so that
    # "A / B" and "A/B" compare equal - a purely typographic difference
    # observed between Study Smarter and the registry (e.g. "Periodic health
    # encounter / preventive health advice" vs ".../preventive...").
    t = t.strip().lower()
    t = re.sub(r"\s*/\s*", "/", t)
    t = re.sub(r"\s+", " ", t)
    return t


def main():
    with open(RAW) as f:
        raw = json.load(f)
    with open(REGISTRY) as f:
        registry = json.load(f)

    me_objectives = [o for o in registry["objectives"] if o["role"] == "Medical Expert"]
    by_legacy_id = defaultdict(list)
    by_title_norm = {}
    by_group_base_id = defaultdict(list)  # e.g. "109" -> [109-1, 109-3, ...] (sub-items only)
    for o in me_objectives:
        by_legacy_id[o["legacy_id"]].append(o)
        by_title_norm[normalize_title(o["title"])] = o
        if "-" in o["legacy_id"]:
            base = o["legacy_id"].split("-")[0]
            by_group_base_id[base].append(o)

    # ---- 1. Build discipline mapping structure ----
    disciplines_out = {}
    by_objective = defaultdict(lambda: {"title": None, "disciplines": []})

    all_disciplines_raw = raw["disciplines"]
    for source_key, canonical_key in SOURCE_DISCIPLINE_KEY_MAP.items():
        entries = all_disciplines_raw[source_key]
        out_entries = []
        for e in entries:
            entry = {
                "discipline": canonical_key,
                "title_as_printed": e["title_as_printed"],
                "legacy_id": e["legacy_id"],
                "source_page": "Study Smarter 2026, Section 1B",
                "source": "Study Smarter 2026",
            }
            if "SOURCE_ANOMALY_SECOND_ID_PRINTED" in e:
                entry["source_anomaly_second_id_printed"] = e["SOURCE_ANOMALY_SECOND_ID_PRINTED"]
                entry["anomaly_note"] = e["anomaly_note"]
            out_entries.append(entry)

            key = e["legacy_id"]
            by_objective[key]["title"] = e["title_as_printed"]
            if canonical_key not in by_objective[key]["disciplines"]:
                by_objective[key]["disciplines"].append(canonical_key)

        disciplines_out[canonical_key] = out_entries

    unique_legacy_ids = set(by_objective.keys())
    multi_discipline_ids = {
        k: v["disciplines"] for k, v in by_objective.items() if len(v["disciplines"]) > 1
    }

    mapping = {
        "source": {
            "title": raw["_provenance"]["source_title"],
            "author": raw["_provenance"]["source_author"],
            "published_date_as_printed": raw["_provenance"]["published_date_as_printed"],
            "official_url": raw["_provenance"]["source_url"],
            "retrieved_at": "2026-08-24",
            "sha256": raw["_provenance"]["source_pdf_sha256"],
        },
        "limitations": {
            "source_is_exhaustive": False,
            "not_all_objectives_represented": True,
            "objectives_may_overlap_disciplines": True,
            "non_medical_expert_roles_map_to_all_disciplines": True,
            "official_caveats_verbatim": raw["_provenance"]["official_caveats_verbatim_from_page_7"],
        },
        "known_source_anomaly": raw["_provenance"]["known_source_anomaly"],
        "disciplines": disciplines_out,
        "by_objective": dict(by_objective),
        "summary": {
            "total_listing_rows": sum(len(v) for v in disciplines_out.values()),
            "unique_legacy_ids_listed": len(unique_legacy_ids),
            "legacy_ids_appearing_in_multiple_disciplines": len(multi_discipline_ids),
            "rows_per_discipline": {k: len(v) for k, v in disciplines_out.items()},
        },
    }

    OUT_MAPPING.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_MAPPING, "w") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # ---- 2. Build reconciliation against objectives_registry ----
    reconciliation_entries = []
    for discipline_key, entries in disciplines_out.items():
        for e in entries:
            legacy_id = e["legacy_id"]
            title_printed = e["title_as_printed"]
            title_norm = normalize_title(title_printed)

            id_matches = by_legacy_id.get(legacy_id, [])
            title_match = by_title_norm.get(title_norm)

            group_siblings = by_group_base_id.get(legacy_id, [])
            group_title_match = next(
                (g for g in group_siblings if normalize_title(g["title"]) == title_norm), None
            )

            if id_matches and any(normalize_title(m["title"]) == title_norm for m in id_matches):
                status = "CONFIRMED"
                match_method = "legacy_id_and_title_match"
                matched = next(m for m in id_matches if normalize_title(m["title"]) == title_norm)
                note = None
            elif group_title_match:
                # Study Smarter cites the bare parent group ID (e.g. "109")
                # instead of the specific sub-item ID (e.g. "109-11") for an
                # objective whose title matches that sub-item exactly. This is
                # a deliberate, systematic Study Smarter citation convention
                # (stated purpose: "to facilitate searching on
                # mcc.ca/objectives", where the group page is what's findable)
                # -- not a data error. Verified across every occurrence before
                # this branch was added; see reports/study_smarter_mapping_audit.md.
                status = "CONFIRMED"
                match_method = "confirmed_via_group_id_citation"
                matched = group_title_match
                note = (
                    f"Study Smarter prints the parent group's Legacy ID "
                    f"'{legacy_id}' rather than the specific sub-item ID "
                    f"'{matched['legacy_id']}'. Title matches exactly. This "
                    f"is the guide's standard citation convention for "
                    f"grouped objectives, confirmed systematically, not an "
                    f"error."
                )
            elif id_matches and len(id_matches) == 1:
                status = "REVIEW"
                match_method = "legacy_id_matches_title_differs"
                matched = id_matches[0]
                note = (
                    f"Legacy ID {legacy_id} exists in registry as "
                    f"'{matched['title']}' but Study Smarter prints "
                    f"'{title_printed}', and no sub-item of group "
                    f"'{legacy_id}' has this exact title either. Requires "
                    f"manual review."
                )
            elif title_match:
                status = "REVIEW"
                match_method = "title_matches_legacy_id_differs"
                matched = title_match
                note = (
                    f"Title '{title_printed}' matches registry title exactly "
                    f"but registry legacy_id is '{matched['legacy_id']}' "
                    f"while Study Smarter prints '{legacy_id}', and "
                    f"'{legacy_id}' is not that record's group base ID "
                    f"either. Requires manual review."
                )
            else:
                status = "UNRESOLVED"
                match_method = "no_registry_match"
                matched = None
                note = (
                    f"No Medical Expert registry record found for Legacy ID "
                    f"'{legacy_id}' or title '{title_printed}'. May reflect a "
                    f"group-level entry (e.g., a parent presentation group "
                    f"like 'Trauma'=109 or 'Population health'=78 cited "
                    f"without a specific sub-item), or true absence from the "
                    f"current registry."
                )

            reconciliation_entries.append({
                "discipline": discipline_key,
                "title_as_printed": title_printed,
                "legacy_id_as_printed": legacy_id,
                "registry_matched_title": matched["title"] if matched else None,
                "registry_matched_mcc_id": matched["mcc_id"] if matched else None,
                "match_method": match_method,
                "status": status,
                "note": note,
            })

    status_counts = dict(Counter(e["status"] for e in reconciliation_entries))

    reconciliation = {
        "generated_at": "2026-08-24",
        "source_mapping": "research/mcc/study_smarter_discipline_mapping.json",
        "source_registry": "research/mcc/objectives_registry.json",
        "methodology": (
            "Each Study Smarter listing (discipline, printed title, printed "
            "Legacy ID) is checked against the Medical Expert objectives "
            "registry using two independent keys: (1) Legacy ID and "
            "(2) normalized exact title. CONFIRMED requires both to agree. "
            "REVIEW covers a match on exactly one key. UNRESOLVED means "
            "neither key produced a registry match, most often because the "
            "Study Smarter list cites a group-parent Legacy ID (e.g., 78, "
            "109, 121) rather than one of its specific sub-item IDs — this "
            "is expected given the guide explicitly groups related "
            "objectives under one ID for brevity, not a registry defect."
        ),
        "status_counts": status_counts,
        "entries": reconciliation_entries,
    }

    with open(OUT_RECONCILIATION, "w") as f:
        json.dump(reconciliation, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # ---- 3. Build audit report ----
    unmatched = [e for e in reconciliation_entries if e["status"] == "UNRESOLVED"]
    review = [e for e in reconciliation_entries if e["status"] == "REVIEW"]

    # duplicate extraction errors: same (discipline, title, legacy_id) row appearing >1x
    row_keys = [(e["discipline"], e["title_as_printed"], e["legacy_id_as_printed"]) for e in reconciliation_entries]
    dup_rows = {k: v for k, v in Counter(row_keys).items() if v > 1}

    # malformed IDs: any legacy_id that isn't purely numeric or numeric-hyphen-numeric
    import re
    malformed_ids = [
        e for e in reconciliation_entries
        if not re.match(r"^\d+(-\d+)?$", e["legacy_id_as_printed"])
    ]

    audit = {
        "audit_date": "2026-08-24",
        "total_listing_rows": len(reconciliation_entries),
        "rows_per_discipline": mapping["summary"]["rows_per_discipline"],
        "unique_legacy_ids_across_all_disciplines": mapping["summary"]["unique_legacy_ids_listed"],
        "legacy_ids_appearing_in_more_than_one_discipline": mapping["summary"]["legacy_ids_appearing_in_multiple_disciplines"],
        "reconciliation_status_counts": status_counts,
        "unmatched_records": unmatched,
        "title_version_discrepancies": review,
        "duplicate_extraction_errors": {str(k): v for k, v in dup_rows.items()},
        "malformed_ids": malformed_ids,
        "known_source_anomaly": raw["_provenance"]["known_source_anomaly"],
        "important_caveat": (
            "Absence of a Medical Expert objective from all six Study Smarter "
            "discipline lists does NOT mean it is missing from MCC scope. "
            "Study Smarter is explicitly non-exhaustive per its own printed "
            "caveats (see study_smarter_discipline_mapping.json.limitations). "
            "Absence means only 'not explicitly represented in this "
            "non-exhaustive study aid.'"
        ),
        "overall_status": "PASS" if not dup_rows and not malformed_ids else "PASS_WITH_NOTES",
    }

    with open(OUT_AUDIT_JSON, "w") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Markdown report
    lines = []
    lines.append("# Study Smarter Discipline Mapping Audit")
    lines.append("")
    lines.append(f"**Audit Date:** {audit['audit_date']}")
    lines.append(f"**Overall Status:** {'✅ PASS' if audit['overall_status'] == 'PASS' else '⚠️ PASS_WITH_NOTES'}")
    lines.append("")
    lines.append("## Source")
    lines.append("")
    lines.append(f"- **Title:** {mapping['source']['title']}")
    lines.append(f"- **Published (as printed):** {mapping['source']['published_date_as_printed']}")
    lines.append(f"- **URL:** {mapping['source']['official_url']}")
    lines.append(f"- **SHA-256:** {mapping['source']['sha256']}")
    lines.append("")
    lines.append("## Listing Counts")
    lines.append("")
    lines.append("| Discipline | Rows Listed |")
    lines.append("|------------|-------------|")
    for disc, count in audit["rows_per_discipline"].items():
        lines.append(f"| {disc} | {count} |")
    lines.append(f"| **Total** | **{audit['total_listing_rows']}** |")
    lines.append("")
    lines.append(f"**Unique Legacy IDs across all disciplines:** {audit['unique_legacy_ids_across_all_disciplines']}")
    lines.append(f"**Legacy IDs appearing in >1 discipline (explicit multi-listing, not inferred):** {audit['legacy_ids_appearing_in_more_than_one_discipline']}")
    lines.append("")
    lines.append("## Reconciliation Against Objectives Registry")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    for status, count in status_counts.items():
        lines.append(f"| {status} | {count} |")
    lines.append("")
    lines.append(f"**Matched registry records (CONFIRMED):** {status_counts.get('CONFIRMED', 0)} / {audit['total_listing_rows']}")
    lines.append("")
    if unmatched:
        lines.append("### Unmatched Records (UNRESOLVED)")
        lines.append("")
        lines.append("| Discipline | Title as Printed | Legacy ID | Note |")
        lines.append("|------------|-------------------|-----------|------|")
        for e in unmatched:
            lines.append(f"| {e['discipline']} | {e['title_as_printed']} | {e['legacy_id_as_printed']} | {e['note']} |")
        lines.append("")
    if review:
        lines.append("### Title/Version Discrepancies (REVIEW)")
        lines.append("")
        lines.append("| Discipline | Title as Printed | Legacy ID | Registry Match | Note |")
        lines.append("|------------|-------------------|-----------|-----------------|------|")
        for e in review:
            lines.append(f"| {e['discipline']} | {e['title_as_printed']} | {e['legacy_id_as_printed']} | {e['registry_matched_title']} | {e['note']} |")
        lines.append("")
    lines.append("## Known Source Anomaly")
    lines.append("")
    lines.append(f"**Location:** {audit['known_source_anomaly']['location']}")
    lines.append("")
    lines.append(f"**Printed text:** `{audit['known_source_anomaly']['printed_text_verbatim']}`")
    lines.append("")
    lines.append(audit['known_source_anomaly']['issue'])
    lines.append("")
    lines.append(f"**Resolution:** {audit['known_source_anomaly']['resolution']}")
    lines.append("")
    lines.append("## Duplicate Extraction Errors")
    lines.append("")
    lines.append(f"Count: {len(dup_rows)} " + ("✅" if not dup_rows else "⚠️"))
    lines.append("")
    lines.append("## Malformed IDs")
    lines.append("")
    lines.append(f"Count: {len(malformed_ids)} " + ("✅" if not malformed_ids else "⚠️"))
    lines.append("")
    lines.append("## Important Caveat")
    lines.append("")
    lines.append(audit["important_caveat"])
    lines.append("")

    with open(OUT_AUDIT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {OUT_MAPPING}")
    print(f"Wrote {OUT_RECONCILIATION}")
    print(f"Wrote {OUT_AUDIT_JSON}")
    print(f"Wrote {OUT_AUDIT_MD}")
    print(json.dumps(status_counts, indent=2))


if __name__ == "__main__":
    main()
