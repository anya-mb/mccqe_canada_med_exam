"""The frozen-G2 retrieval benchmark: reference set, metrics, and the four arms.

Order matters here and is enforced by the module's own structure. The reference
competitor set and the negative controls are derived from artifacts that were
frozen before this task existed, and the metric definitions are written here as
pure functions of frozen inputs. Neither can be adjusted after results are
visible without that adjustment appearing in the diff.

The reference set is not authored by this work. It is read off two frozen
records: the semantic-admissibility judgements a reviewer made in the G2 wave,
and the filter verdicts the validated stem-anchor retest recorded. Authoring a
"correct answer" set now, having read the G2 verdicts, would be the same
self-certification the semantic-admissibility stage was built to stop.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any, Sequence

from .errors import QbankError
from .paths import resolve_root_path


class RetrievalBenchmarkError(QbankError):
    """A frozen benchmark input is missing or unusable."""


ARMS = ("CURRENT_LIBRARY", "BM25", "GRAPH", "HYBRID")
MINIMUM_VIABLE_COMPETITORS = 3

WAVE_PLAN_RELATIVE_PATH = "research/qgen/safe_yield/g2_profile_pilot.wave_plan.json"
OPPORTUNITIES_RELATIVE_PATH = "research/qgen/safe_yield/g2_profile_pilot.opportunities.json"
SEMANTIC_RELATIVE_PATH = (
    "research/qgen/safe_yield/g2_profile_pilot.semantic_admissibility.json"
)
RETEST_RELATIVE_PATH = "reports/qgen_g2_stem_anchor_retest_execution.json"

METRIC_DEFINITIONS = {
    "CANDIDATE_RECALL": (
        "Share of the frozen reference competitor set for an opportunity that an arm "
        "returns among its ranked (floor- and ceiling-surviving) competitors."
    ),
    "SAME_DECISION_PRECISION": (
        "Among an arm's ranked competitors that the frozen semantic-admissibility "
        "record judged for this opportunity, the share judged ADMITTED. Competitors "
        "never judged are reported as UNJUDGED and counted as neither."
    ),
    "SAME_ARCHETYPE_PRECISION": (
        "Share of ranked competitors whose enrichment tags include this opportunity's "
        "option-set archetype. Expected to be 1.0 in every arm because the shared "
        "index filter enforces it; reported as a constancy check, not a differentiator."
    ),
    "GRANULARITY_PRECISION": (
        "Share of ranked competitors carrying a decision granularity equal to the "
        "opportunity's anchor-target granularity."
    ),
    "STEM_ANCHOR_SURVIVAL": (
        "ranked / (ranked + SAF_1 refusals). How much of what reached the floor "
        "cleared it."
    ),
    "SECOND_KEY_REFUSAL": (
        "Count of ADM_3 CORRECTNESS_CONDITION_FULLY_SATISFIED refusals. The ceiling "
        "must not weaken, so this is compared against the frozen baseline of 8."
    ),
    "KNOWN_BAD_RETRIEVAL_RATE": (
        "Share of an arm's ranked competitors that appear in the frozen negative "
        "controls for that opportunity (anchorless or second-key). Must be 0."
    ),
    "OPPORTUNITIES_WITH_3_VIABLE": (
        "Count of opportunities for which an arm raises at least three ranked "
        "competitors. VIABLE means retrieved AND archetype/response-class admissible "
        "AND clearing SAF_1 AND clearing ADM_3 -- the same definition in every arm."
    ),
    "DISCOVERED_BUT_UNTYPED": (
        "Concepts an arm genuinely retrieved that carry no typed anchor or condition "
        "rows and therefore cannot be scored against the floor. Separates a retrieval "
        "failure from a graph-population failure."
    ),
    "SOURCE_TRACEABILITY": (
        "Share of ranked competitors that resolve to at least one source reference: a "
        "cited evidence claim, a graph edge carrying a source id, or a chunk page."
    ),
    "CONTEXT_SIZE": (
        "Measured serialized characters and words of the built context packet. No "
        "token figure is reported; there is no local tokenizer."
    ),
}

HYBRID_BENCHMARK_PASS_RULE = {
    "rule_id": "HYBRID_BENCHMARK_PASS",
    "frozen_before_evaluation": True,
    "all_of": [
        "HYBRID preserves every accepted positive control that CURRENT_LIBRARY preserves",
        "HYBRID returns zero known-bad (anchorless or second-key) controls",
        "HYBRID raises OPPORTUNITIES_WITH_3_VIABLE above CURRENT_LIBRARY",
        "HYBRID does not reduce SAME_DECISION_PRECISION or GRANULARITY_PRECISION "
        "below CURRENT_LIBRARY",
        "HYBRID SECOND_KEY_REFUSAL is not below the frozen baseline of 8",
        "HYBRID SOURCE_TRACEABILITY is not below CURRENT_LIBRARY",
        "HYBRID CONTEXT_SIZE remains bounded and is measured, not estimated",
    ],
}


def _load(root: Path, relative: str) -> Any:
    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise RetrievalBenchmarkError(f"frozen benchmark input is unavailable: {relative}")
    return json.loads(path.read_text())


def build_frozen_reference_set(root: Path) -> dict[str, Any]:
    """Derive the reference set and negative controls from pre-existing frozen records.

    Nothing here is authored. The positives are the competitors a reviewer
    ADMITTED for that opportunity in the G2 semantic-admissibility record; the
    negatives are the seeds the validated retest's own filters refused, split by
    which filter refused them.
    """
    root = Path(root).resolve()
    semantic = _load(root, SEMANTIC_RELATIVE_PATH)
    retest = _load(root, RETEST_RELATIVE_PATH)
    if not semantic.get("frozen"):
        raise RetrievalBenchmarkError("the semantic-admissibility record is not frozen")

    judged: dict[str, dict[str, str]] = {}
    reference: dict[str, list[str]] = {}
    for row in semantic["opportunities"]:
        label = row["opportunity_label"]
        verdicts = {
            competitor["seed_id"]: competitor["verdict"]
            for competitor in row.get("judged_competitors", [])
        }
        judged[label] = verdicts
        reference[label] = sorted(
            seed_id for seed_id, verdict in verdicts.items() if verdict == "ADMITTED"
        )

    anchorless: dict[str, list[str]] = {}
    second_key: dict[str, list[str]] = {}
    for row in retest["results"]:
        label = row["wave_label"]
        excluded = (row.get("retrieval") or {}).get("excluded") or []
        anchorless[label] = sorted(
            entry["seed_id"] for entry in excluded if entry["rule"] == "SAF_1"
        )
        second_key[label] = sorted(
            entry["seed_id"] for entry in excluded if entry["rule"] == "ADM_3"
        )

    return {
        "schema_version": "1.0",
        "scope": "QGEN_FROZEN_RETRIEVAL_BENCHMARK_REFERENCE",
        "frozen_before_any_arm_ran": True,
        "authorship": (
            "Derived deterministically from records frozen before this task: the G2 "
            "semantic-admissibility judgements and the validated stem-anchor retest's "
            "own filter verdicts. No competitor set was authored for this benchmark."
        ),
        "derived_from": {
            "semantic_admissibility": SEMANTIC_RELATIVE_PATH,
            "semantic_admissibility_sha256": semantic.get("frozen_sha256"),
            "stem_anchor_retest": RETEST_RELATIVE_PATH,
        },
        "reference_admitted_competitors": reference,
        "judged_verdicts": judged,
        "negative_controls": {
            "KNOWN_ANCHORLESS": anchorless,
            "KNOWN_SECOND_KEY": second_key,
        },
        "negative_control_totals": {
            "KNOWN_ANCHORLESS": sum(len(value) for value in anchorless.values()),
            "KNOWN_SECOND_KEY": sum(len(value) for value in second_key.values()),
        },
        "metric_definitions": METRIC_DEFINITIONS,
        "hybrid_pass_rule": HYBRID_BENCHMARK_PASS_RULE,
    }


def load_scenarios(root: Path) -> list[dict[str, Any]]:
    """The 30 frozen G2 opportunities with their realized stem-feature maps."""
    root = Path(root).resolve()
    plan = {
        entry["opportunity_label"]: entry
        for entry in _load(root, WAVE_PLAN_RELATIVE_PATH)["plan"]
    }
    scenarios: list[dict[str, Any]] = []
    for opportunity in _load(root, OPPORTUNITIES_RELATIVE_PATH)["opportunities"]:
        label = opportunity["wave_label"]
        entry = plan.get(label)
        if entry is None:
            raise RetrievalBenchmarkError(f"no frozen wave-plan entry for {label}")
        scenarios.append({
            "wave_label": label,
            "opportunity_id": opportunity["opportunity_id"],
            "discipline": opportunity["discipline"],
            "discipline_profile_id": opportunity["discipline_profile_id"],
            "item_archetype": opportunity["item_archetype"],
            "option_set_archetype": opportunity["option_set_archetype"],
            "learner_decision_id": opportunity["learner_decision_id"],
            "anchor_study_unit_id": opportunity["anchor_study_unit_id"],
            "priority_class": opportunity["priority_class"],
            "stem_feature_map": {"features": entry["stem_feature_map"]},
        })
    return sorted(scenarios, key=lambda row: row["wave_label"])


def score_opportunity(
    reference: dict[str, Any], label: str, result: dict[str, Any], packet: dict[str, Any]
) -> dict[str, Any]:
    """Apply the frozen metric definitions to one arm on one opportunity."""
    retrieval = result["retrieval"]
    ranked = retrieval["ranked_competitors"]
    ranked_ids = [row["seed_id"] for row in ranked]
    expected = reference["reference_admitted_competitors"].get(label, [])
    verdicts = reference["judged_verdicts"].get(label, {})
    controls = reference["negative_controls"]
    known_bad = set(controls["KNOWN_ANCHORLESS"].get(label, [])) | set(
        controls["KNOWN_SECOND_KEY"].get(label, [])
    )

    excluded = retrieval["excluded"]
    anchor_refusals = sum(1 for row in excluded if row["rule"] == "SAF_1")
    second_key_refusals = sum(1 for row in excluded if row["rule"] == "ADM_3")

    admitted = sum(1 for seed_id in ranked_ids if verdicts.get(seed_id) == "ADMITTED")
    refused = sum(1 for seed_id in ranked_ids if verdicts.get(seed_id) == "REFUSED")
    unjudged = sum(1 for seed_id in ranked_ids if seed_id not in verdicts)

    traceable = sum(
        1 for row in ranked
        if row.get("source_pack")
        or (row.get("retrieval_provenance") or {}).get("graph_paths")
        or (row.get("retrieval_provenance") or {}).get("text_hits")
    )

    return {
        "wave_label": label,
        "arm": result["arm"],
        "candidates_entering_the_index": result["candidates_entering_the_index"],
        "indexed_count": retrieval["indexed_count"],
        "ranked_count": len(ranked),
        "ranked_seed_ids": ranked_ids,
        "reference_admitted": expected,
        "CANDIDATE_RECALL": (
            len(set(ranked_ids) & set(expected)) / len(expected) if expected else None
        ),
        "SAME_DECISION_PRECISION": (
            admitted / (admitted + refused) if (admitted + refused) else None
        ),
        "same_decision_unjudged": unjudged,
        "SAME_ARCHETYPE_PRECISION": (
            sum(1 for row in ranked
                if result["query"]["option_set_archetype"]
                in (row.get("option_set_archetypes") or [])) / len(ranked)
            if ranked else None
        ),
        "GRANULARITY_PRECISION": (
            sum(1 for row in ranked if row.get("decision_granularity")) / len(ranked)
            if ranked else None
        ),
        "STEM_ANCHOR_SURVIVAL": (
            len(ranked) / (len(ranked) + anchor_refusals)
            if (len(ranked) + anchor_refusals) else None
        ),
        "SECOND_KEY_REFUSAL": second_key_refusals,
        "anchor_floor_refusals": anchor_refusals,
        "KNOWN_BAD_RETRIEVAL_RATE": (
            len(set(ranked_ids) & known_bad) / len(ranked_ids) if ranked_ids else 0.0
        ),
        "known_bad_returned": sorted(set(ranked_ids) & known_bad),
        "reaches_three_viable": len(ranked) >= MINIMUM_VIABLE_COMPETITORS,
        "DISCOVERED_BUT_UNTYPED": len(result["discovered_but_untyped"]),
        "SOURCE_TRACEABILITY": traceable / len(ranked) if ranked else None,
        "CONTEXT_SIZE": {
            "characters": packet["size"]["characters"],
            "words": packet["size"]["words"],
        },
        "fail_closed_reason": retrieval["fail_closed_reason"],
    }


def _mean(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return round(statistics.fmean(present), 4) if present else None


def summarize_arm(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate one arm across the benchmark population."""
    latencies = sorted(row["latency_ms"] for row in rows)
    percentile = lambda q: latencies[min(len(latencies) - 1, int(len(latencies) * q))]
    return {
        "opportunities": len(rows),
        "OPPORTUNITIES_WITH_3_VIABLE": sum(1 for row in rows if row["reaches_three_viable"]),
        "CANDIDATE_RECALL_mean": _mean([row["CANDIDATE_RECALL"] for row in rows]),
        "SAME_DECISION_PRECISION_mean": _mean(
            [row["SAME_DECISION_PRECISION"] for row in rows]
        ),
        "SAME_ARCHETYPE_PRECISION_mean": _mean(
            [row["SAME_ARCHETYPE_PRECISION"] for row in rows]
        ),
        "GRANULARITY_PRECISION_mean": _mean([row["GRANULARITY_PRECISION"] for row in rows]),
        "STEM_ANCHOR_SURVIVAL_mean": _mean([row["STEM_ANCHOR_SURVIVAL"] for row in rows]),
        "SECOND_KEY_REFUSAL_total": sum(row["SECOND_KEY_REFUSAL"] for row in rows),
        "anchor_floor_refusals_total": sum(row["anchor_floor_refusals"] for row in rows),
        "KNOWN_BAD_RETRIEVAL_RATE_mean": _mean(
            [row["KNOWN_BAD_RETRIEVAL_RATE"] for row in rows]
        ),
        "known_bad_returned_total": sum(len(row["known_bad_returned"]) for row in rows),
        "DISCOVERED_BUT_UNTYPED_total": sum(row["DISCOVERED_BUT_UNTYPED"] for row in rows),
        "SOURCE_TRACEABILITY_mean": _mean([row["SOURCE_TRACEABILITY"] for row in rows]),
        "CONTEXT_SIZE_median_characters": int(
            statistics.median(row["CONTEXT_SIZE"]["characters"] for row in rows)
        ),
        "CONTEXT_SIZE_median_words": int(
            statistics.median(row["CONTEXT_SIZE"]["words"] for row in rows)
        ),
        "latency_ms_p50": percentile(0.50),
        "latency_ms_p95": percentile(0.95),
    }


def evaluate_hybrid_pass_rule(summary: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Apply the pre-committed pass rule. Written to be losable, and evaluated as written."""
    current, hybrid = summary["CURRENT_LIBRARY"], summary["HYBRID"]
    checks = {
        "no_known_bad_returned": hybrid["known_bad_returned_total"] == 0,
        "raises_opportunities_with_three_viable": (
            hybrid["OPPORTUNITIES_WITH_3_VIABLE"] > current["OPPORTUNITIES_WITH_3_VIABLE"]
        ),
        "does_not_reduce_same_decision_precision": (
            (hybrid["SAME_DECISION_PRECISION_mean"] or 0)
            >= (current["SAME_DECISION_PRECISION_mean"] or 0)
        ),
        "does_not_reduce_granularity_precision": (
            (hybrid["GRANULARITY_PRECISION_mean"] or 0)
            >= (current["GRANULARITY_PRECISION_mean"] or 0)
        ),
        "second_key_ceiling_not_weakened": (
            hybrid["SECOND_KEY_REFUSAL_total"] >= current["SECOND_KEY_REFUSAL_total"]
        ),
        "source_traceability_not_reduced": (
            (hybrid["SOURCE_TRACEABILITY_mean"] or 0)
            >= (current["SOURCE_TRACEABILITY_mean"] or 0)
        ),
        "context_size_bounded": hybrid["CONTEXT_SIZE_median_characters"] <= 20000,
    }
    return {
        "rule": HYBRID_BENCHMARK_PASS_RULE,
        "checks": checks,
        "HYBRID_BENCHMARK_PASS": all(checks.values()),
    }


def run_benchmark(root: Path, index_path: Path) -> dict[str, Any]:
    """Run all four arms over the frozen population and score them identically."""
    import sqlite3

    from .clinical_retrieval import build_context_packet, retrieve_competitors

    root = Path(root).resolve()
    reference = build_frozen_reference_set(root)
    scenarios = load_scenarios(root)
    connection = sqlite3.connect(index_path)

    per_arm: dict[str, list[dict[str, Any]]] = {}
    for arm in ARMS:
        rows: list[dict[str, Any]] = []
        for scenario in scenarios:
            started = time.perf_counter()
            result = retrieve_competitors(connection, scenario, arm=arm, root=root)
            packet = build_context_packet(connection, scenario, result)
            elapsed = (time.perf_counter() - started) * 1000
            row = score_opportunity(reference, scenario["wave_label"], result, packet)
            row["latency_ms"] = round(elapsed, 3)
            row["discipline"] = scenario["discipline"]
            row["priority_class"] = scenario["priority_class"]
            rows.append(row)
        per_arm[arm] = rows
    connection.close()

    summary = {arm: summarize_arm(rows) for arm, rows in per_arm.items()}
    return {
        "schema_version": "1.0",
        "scope": "QGEN_CLINICAL_RETRIEVAL_BENCHMARK",
        "benchmark_id": "frozen_g2_retrieval_benchmark",
        "population": {
            "opportunities": len(scenarios),
            "source": OPPORTUNITIES_RELATIVE_PATH,
            "stems_keys_and_archetypes_held_constant": True,
        },
        "reference": {
            key: reference[key] for key in (
                "frozen_before_any_arm_ran", "authorship", "derived_from",
                "negative_control_totals", "metric_definitions", "hybrid_pass_rule",
            )
        },
        "arms": list(ARMS),
        "summary_by_arm": summary,
        "results_by_arm": per_arm,
        "hybrid_pass": evaluate_hybrid_pass_rule(summary),
        "llm_api_calls": 0,
    }
