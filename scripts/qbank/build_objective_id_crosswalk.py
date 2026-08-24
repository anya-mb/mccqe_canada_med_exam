"""Build research/mcc/objective_id_crosswalk.json.

Reconciles the web-service 'id' field against the official page-displayed
'Legacy ID' field for Medical Expert objectives.

Finding (documented, not assumed): manual spot-check of 4 objectives
(Headache/39, Limp in children/20, Abnormal lipids/51, Vascular injury/109-15)
showed the web-service id IS the Legacy ID verbatim in every case, with no
separate 'current ID' exposed anywhere on the official site. Since the web
service is the only bulk source of these identifiers and there is no second,
independent ID system to reconcile against, this crosswalk documents that
finding as CONFIRMED_BY_SAMPLE rather than fabricating a distinct id system.

Non-Medical-Expert roles have no Legacy ID system at all (see
objectives_registry.json structural_note) and are excluded from this
crosswalk as NOT_APPLICABLE.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "research" / "mcc" / "objectives_registry.json"
OUT = REPO / "research" / "mcc" / "objective_id_crosswalk.json"

MANUALLY_VERIFIED_SAMPLE = {
    "39": {"title": "Headache", "page_legacy_id": "39", "checked_url": "https://mcc.ca/objectives/medical-expert/headache/"},
    "20": {"title": "Limp in children", "page_legacy_id": "20", "checked_url": "https://mcc.ca/objectives/medical-expert/limp-in-children/"},
    "51": {"title": "Abnormal lipids", "page_legacy_id": "51", "checked_url": "https://mcc.ca/objectives/medical-expert/abnormal-serum-lipids/"},
    "109-15": {"title": "Vascular injury", "page_legacy_id": "109-15", "checked_url": "https://mcc.ca/objectives/medical-expert/trauma/vascular-injury/"},
}


def main():
    with open(REGISTRY) as f:
        registry = json.load(f)

    entries = []
    for obj in registry["objectives"]:
        if obj["role"] != "Medical Expert":
            entries.append({
                "mcc_id": None,
                "legacy_id": None,
                "title": obj["title"],
                "role": obj["role"],
                "match_method": "not_applicable_role_level_record",
                "status": "NOT_APPLICABLE",
                "note": "Non-Medical-Expert role; no per-objective Legacy ID system exists on official MCC site.",
            })
            continue

        mcc_id = obj["mcc_id"]
        is_manually_verified = mcc_id in MANUALLY_VERIFIED_SAMPLE

        entries.append({
            "mcc_id": mcc_id,
            "legacy_id": obj["legacy_id"],
            "title": obj["title"],
            "role": obj["role"],
            "official_url": obj["official_url"],
            "match_method": (
                "manually_verified_official_page" if is_manually_verified
                else "web_service_id_equals_legacy_id_by_documented_pattern"
            ),
            "status": "CONFIRMED" if is_manually_verified else "CONFIRMED_BY_SAMPLE_PATTERN",
            "note": (
                "Directly confirmed by loading the official objective page and "
                "reading its displayed 'Legacy ID' field."
                if is_manually_verified else
                "Not individually page-checked. Inferred to equal the Legacy ID "
                "based on 4/4 manually verified samples showing the web-service "
                "id field is identical to the official page's Legacy ID field, "
                "with no exceptions found and no alternate ID system published "
                "by MCC. This is a documented pattern inference, not a fuzzy "
                "title match — flag for individual re-verification if this "
                "objective's Legacy ID is load-bearing for a specific "
                "crosswalk decision."
            ),
        })

    crosswalk = {
        "schema_version": "1.0",
        "generated_at": "2026-08-24",
        "source_registry": "research/mcc/objectives_registry.json",
        "methodology": {
            "summary": (
                "The official MCC Objectives Online Web Service exposes only "
                "one identifier field ('id') for Medical Expert objectives. "
                "The official individual objective pages (mcc.ca/objectives/"
                "medical-expert/<slug>/) separately display a field labeled "
                "'Legacy ID'. This crosswalk establishes whether these two "
                "values are the same identifier."
            ),
            "manually_verified_sample": MANUALLY_VERIFIED_SAMPLE,
            "manually_verified_sample_size": len(MANUALLY_VERIFIED_SAMPLE),
            "manually_verified_match_rate": "4/4 (100%)",
            "conclusion": (
                "CONFIRMED: web-service 'id' == official page 'Legacy ID' for "
                "every sampled Medical Expert objective. No distinct 'current "
                "ID' system was found anywhere on the official MCC site. "
                "Records not in the manual sample are marked "
                "CONFIRMED_BY_SAMPLE_PATTERN rather than CONFIRMED to keep the "
                "distinction between directly-observed and pattern-inferred "
                "auditable."
            ),
            "non_expert_roles": (
                "Collaborator, Communicator, Health Advocate, Leader/Manager, "
                "Professional, and Scholar have no Legacy ID system at all; "
                "entries for these roles are marked NOT_APPLICABLE."
            ),
        },
        "status_counts": {},
        "entries": entries,
    }

    from collections import Counter
    crosswalk["status_counts"] = dict(Counter(e["status"] for e in entries))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(crosswalk, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(entries)} crosswalk entries to {OUT}")
    print(json.dumps(crosswalk["status_counts"], indent=2))


if __name__ == "__main__":
    main()
