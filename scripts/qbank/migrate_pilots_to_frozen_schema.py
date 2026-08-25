"""Phase 3C: migrate the Cardiology and ELOM pilot outputs to the frozen
shared schema (scope_schema_version 1.0), applying the six pilot findings:

A. freshness normalization (fresh_guideline_required /
   fresh_legal_verification_required -> freshness.{verification_required,
   verification_type})
B. explicit evidence_type (OBJECTIVE_REFERENCE / ROLE_LEVEL_REFERENCE) on
   every mcc_evidence entry
C. mcc_evidence hygiene: empty mcc_evidence enforced for
   SUPPORTING_KNOWLEDGE/SPECIALIST_DETAIL/REFERENCE_ONLY units (both pilots
   already followed this after the Cardiology weak-mapping review; this
   pass verifies it holds, it does not need to clear anything further)
D. jurisdiction remains optional (present only where set in the pilot data)
E. (procedural, not a data transform - see docs/scope/same_page_toc_merge_protocol.md)
F. target_questions/historical_absolute_estimate is dropped from the
   migrated crosswalk.json entries (it never feeds anything downstream);
   preserved verbatim in a separate *_migration_history.json file per
   chapter for audit purposes only.

Writes migrated output to research/scope/chapters/<code>/, leaving
research/scope/pilots/<name>/ untouched as historical record.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PILOTS_DIR = REPO / "research" / "scope" / "pilots"
CHAPTERS_DIR = REPO / "research" / "scope" / "chapters"

import sys
sys.path.insert(0, str(REPO / "scripts"))
from qbank.schema import validate_instance  # noqa: E402
from qbank.errors import SchemaValidationError  # noqa: E402

SCHEMA_VERSION = "1.0"


def migrate_study_unit(su: dict) -> dict:
    return {
        "scope_schema_version": SCHEMA_VERSION,
        "study_unit_id": su["study_unit_id"],
        "title": su["title"],
        "chapter_code": su["chapter_code"],
        "chapter_title": su["chapter_title"],
        "source_node_ids": su["source_node_ids"],
        "tn_page_range": su["tn_page_range"],
        "pdf_page_range": su["pdf_page_range"],
        "source_hierarchy_path": su["source_hierarchy_path"],
        "structural_rationale": su["structural_rationale"],
        "extraction_confidence": su["extraction_confidence"],
        "page_mapping_precision": su["page_mapping_precision"],
    }


def migrate_mcc_evidence(evidence_list: list) -> list:
    out = []
    for ev in evidence_list:
        evidence_type = "ROLE_LEVEL_REFERENCE" if ev.get("mcc_id") is None else "OBJECTIVE_REFERENCE"
        migrated = {
            "evidence_type": evidence_type,
            "mcc_id": ev["mcc_id"],
            "legacy_id": ev["legacy_id"],
            "objective_title": ev["objective_title"],
            "canmeds_role": ev["canmeds_role"],
            "official_source": ev["official_source"],
            "mapping_strength": ev["mapping_strength"],
            "mapping_rationale": ev["mapping_rationale"],
        }
        if ev.get("requires_scope_review"):
            migrated["requires_scope_review"] = True
        elif ev["mapping_strength"] == "WEAK":
            # Should not happen given pilot data already sets this, but
            # enforce rather than silently produce an invalid record.
            migrated["requires_scope_review"] = True
        out.append(migrated)
    return out


def migrate_freshness(entry: dict) -> dict:
    """Both pilots used a single boolean under a differently-named field:
    Cardiology fresh_guideline_required, ELOM fresh_legal_verification_required.
    Neither pilot recorded WHICH kind of freshness was needed beyond what's
    inferable from chapter context, so verification_type is inferred here
    from the source field name and jurisdiction presence - not invented,
    just reclassified from information the pilot data already implies."""
    required = bool(entry.get("fresh_guideline_required") or entry.get("fresh_legal_verification_required"))
    if not required:
        return {"verification_required": False}
    types = []
    if "fresh_guideline_required" in entry and entry["fresh_guideline_required"]:
        types.append("CLINICAL_GUIDELINE")
    if "fresh_legal_verification_required" in entry and entry["fresh_legal_verification_required"]:
        types.append("LEGAL_REGULATORY")
    if entry.get("jurisdiction", {}).get("scope") not in (None, "NOT_APPLICABLE"):
        if "LEGAL_REGULATORY" not in types:
            types.append("JURISDICTION")
    if not types:
        types = ["CLINICAL_GUIDELINE"]
    return {"verification_required": True, "verification_type": types}


def migrate_crosswalk_entry(entry: dict) -> tuple:
    """Returns (migrated_entry, historical_data_or_None)."""
    migrated = {
        "scope_schema_version": SCHEMA_VERSION,
        "study_unit_id": entry["study_unit_id"],
        "title": entry["title"],
        "classification": entry["classification"],
        "mcc_evidence": migrate_mcc_evidence(entry["mcc_evidence"]),
        "scope_depth": entry["scope_depth"],
        "testable_competencies": entry["testable_competencies"],
        "question_planning": {
            "coverage_weight": entry["question_planning"]["coverage_weight"],
            "minimum_question_coverage": entry["question_planning"]["minimum_question_coverage"],
            "preferred_item_forms": entry["question_planning"]["preferred_item_forms"],
        },
        "page_mapping_precision": entry["page_mapping_precision"],
        "clinical_source_organizations": entry["clinical_source_organizations"],
        "freshness": migrate_freshness(entry),
    }
    if entry.get("do_not_test"):
        migrated["do_not_test"] = entry["do_not_test"]
    if entry.get("jurisdiction"):
        migrated["jurisdiction"] = {
            "scope": entry["jurisdiction"]["scope"],
            "province_required_in_question": entry["jurisdiction"]["province_required_in_question"],
        }
    if entry.get("zero_question_reason"):
        migrated["zero_question_reason"] = entry["zero_question_reason"]
    if entry.get("cross_discipline_note"):
        migrated["cross_discipline_note"] = entry["cross_discipline_note"]
    if entry.get("uncertain_reason"):
        migrated["uncertain_reason"] = entry["uncertain_reason"]

    historical = entry.get("historical_absolute_estimate")
    return migrated, historical


def migrate_chapter(pilot_name: str, chapter_code: str):
    pilot_dir = PILOTS_DIR / pilot_name
    out_dir = CHAPTERS_DIR / chapter_code
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(pilot_dir / "study_units.json") as f:
        su_data = json.load(f)
    with open(pilot_dir / "crosswalk.json") as f:
        cw_data = json.load(f)

    migrated_units = [migrate_study_unit(u) for u in su_data["study_units"]]
    migrated_entries = []
    historical_by_unit = {}
    for e in cw_data["entries"]:
        migrated, historical = migrate_crosswalk_entry(e)
        migrated_entries.append(migrated)
        if historical:
            historical_by_unit[e["study_unit_id"]] = historical

    validation_errors = []
    for u in migrated_units:
        try:
            validate_instance(REPO, "study-unit", u)
        except SchemaValidationError as exc:
            validation_errors.append(f"study_unit {u['study_unit_id']}: {exc}")
    for e in migrated_entries:
        try:
            validate_instance(REPO, "crosswalk-entry", e)
        except SchemaValidationError as exc:
            validation_errors.append(f"crosswalk_entry {e['study_unit_id']}: {exc}")

    su_out = dict(su_data)
    su_out["scope_schema_version"] = SCHEMA_VERSION
    su_out["study_units"] = migrated_units
    su_out["migrated_from"] = f"research/scope/pilots/{pilot_name}/study_units.json"

    with open(out_dir / "study_units.json", "w") as f:
        json.dump(su_out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    cw_out = dict(cw_data)
    cw_out["scope_schema_version"] = SCHEMA_VERSION
    cw_out["entries"] = migrated_entries
    cw_out["migrated_from"] = f"research/scope/pilots/{pilot_name}/crosswalk.json"

    with open(out_dir / "crosswalk.json", "w") as f:
        json.dump(cw_out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if historical_by_unit:
        with open(out_dir / "migration_history.json", "w") as f:
            json.dump({
                "note": (
                    "Historical absolute target_questions estimates from "
                    "the Phase 3A/3B pilot, preserved here for audit only. "
                    "NOT used by question_planning.coverage_weight and NOT "
                    "read by any downstream manifest/production code."
                ),
                "by_study_unit": historical_by_unit,
            }, f, indent=2, ensure_ascii=False)
            f.write("\n")

    # copy audit/unresolved files through unchanged (they document process,
    # not schema-bound data)
    for fname in ["study_units_audit.json", "study_units_audit.md",
                  "crosswalk_audit.json", "crosswalk_audit.md",
                  "unresolved_mappings.json"]:
        src = pilot_dir / fname
        if src.exists():
            with open(src) as f:
                content = f.read()
            with open(out_dir / fname, "w") as f:
                f.write(content)

    return {
        "chapter_code": chapter_code,
        "study_units_migrated": len(migrated_units),
        "crosswalk_entries_migrated": len(migrated_entries),
        "validation_errors": validation_errors,
        "result": "PASS" if not validation_errors else "FAIL",
    }


def main():
    results = []
    results.append(migrate_chapter("cardiology", "C"))
    results.append(migrate_chapter("elom", "ELOM"))

    for r in results:
        print(f"\n=== {r['chapter_code']} ===")
        print(f"Study units migrated: {r['study_units_migrated']}")
        print(f"Crosswalk entries migrated: {r['crosswalk_entries_migrated']}")
        print(f"Validation errors: {len(r['validation_errors'])}")
        for e in r["validation_errors"][:10]:
            print(f"  - {e}")
        print(f"Result: {r['result']}")

    cardiology_result = next(r for r in results if r["chapter_code"] == "C")
    elom_result = next(r for r in results if r["chapter_code"] == "ELOM")
    print(f"\nCARDIOLOGY_MIGRATION = {cardiology_result['result']}")
    print(f"ELOM_MIGRATION = {elom_result['result']}")

    return results


if __name__ == "__main__":
    main()
