"""Central fail-closed precondition for question stem generation.

The caller may assemble lifecycle context from any canonical artifact family,
but no generator callback is invoked until this module verifies every
load-bearing state and pin in one place.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


APPROVED = "INDEPENDENT_REVIEW_APPROVED"
LIFECYCLE_STATES = frozenset({
    "DRAFT",
    "PROPOSED",
    APPROVED,
    "INDEPENDENT_REVIEW_REJECTED",
    "INDEPENDENT_REVIEW_UNCERTAIN",
    "FROZEN",
    "INVALIDATED",
    "EVIDENCE_READY",
    "FEATURE_READY",
    "CONTRAST_READY",
    "BLUEPRINT_READY",
    "STEM_FROZEN",
    "FINAL_REVIEW_ACCEPTED",
    "FINAL_REVIEW_REJECTED",
})
ALLOWED_TRANSITIONS = frozenset({
    ("DRAFT", "PROPOSED"),
    ("PROPOSED", APPROVED),
    ("PROPOSED", "INDEPENDENT_REVIEW_REJECTED"),
    ("PROPOSED", "INDEPENDENT_REVIEW_UNCERTAIN"),
    (APPROVED, "FROZEN"),
    ("INDEPENDENT_REVIEW_REJECTED", "INVALIDATED"),
    ("INDEPENDENT_REVIEW_UNCERTAIN", "INVALIDATED"),
    ("EVIDENCE_READY", "FEATURE_READY"),
    ("FEATURE_READY", "CONTRAST_READY"),
    ("CONTRAST_READY", "BLUEPRINT_READY"),
    ("BLUEPRINT_READY", "STEM_FROZEN"),
    ("STEM_FROZEN", "FINAL_REVIEW_ACCEPTED"),
    ("STEM_FROZEN", "FINAL_REVIEW_REJECTED"),
})


class GenerationPreconditionError(ValueError):
    """A required upstream lifecycle state is not generation-ready."""


def validate_lifecycle_transition(current: str, target: str) -> str:
    """Reject lifecycle shortcuts, especially authoring-to-freeze bypasses."""
    if current not in LIFECYCLE_STATES or target not in LIFECYCLE_STATES:
        raise GenerationPreconditionError("INVALID_LIFECYCLE_STATE")
    if (current, target) not in ALLOWED_TRANSITIONS:
        raise GenerationPreconditionError(
            f"INVALID_LIFECYCLE_TRANSITION: {current} -> {target}"
        )
    return target


def _state_error(kind: str, state: Any) -> str:
    upper = str(state or "").upper()
    if "REJECTED" in upper:
        return f"REJECTED_{kind}"
    if "UNCERTAIN" in upper:
        return f"UNCERTAIN_{kind}"
    return f"UNAPPROVED_{kind}"


def _require_reviewed_pinned(value: dict[str, Any], kind: str) -> None:
    if value.get("state") != APPROVED:
        raise GenerationPreconditionError(_state_error(kind, value.get("state")))
    if value.get("frozen") is not True:
        raise GenerationPreconditionError(f"UNFROZEN_{kind}")
    digest = value.get("content_sha256")
    if not digest or value.get("pinned_sha256") != digest:
        raise GenerationPreconditionError(f"UNPINNED_{kind}")
    author = value.get("author_id")
    reviewer = value.get("reviewer_id")
    if not reviewer or not author or reviewer == author:
        raise GenerationPreconditionError(f"NONINDEPENDENT_{kind}_REVIEW")


def _require_pinned(value: dict[str, Any], kind: str) -> None:
    digest = value.get("content_sha256")
    if not digest or value.get("pinned_sha256") != digest:
        raise GenerationPreconditionError(f"UNPINNED_{kind}")


def assert_generation_ready(context: dict[str, Any]) -> dict[str, Any]:
    """Validate the complete generation boundary and return an audit receipt."""
    opportunity_id = context.get("opportunity_id")
    if not opportunity_id:
        raise GenerationPreconditionError("MISSING_OPPORTUNITY_ID")

    _require_reviewed_pinned(context.get("evidence") or {}, "EVIDENCE")
    _require_reviewed_pinned(context.get("feature_map") or {}, "FEATURE_MAP")
    profile = context.get("profile_snapshot") or {}
    if profile.get("state") != "FROZEN":
        raise GenerationPreconditionError("UNFROZEN_PROFILE_SNAPSHOT")
    _require_pinned(profile, "PROFILE_SNAPSHOT")

    key = context.get("key") or {}
    if key.get("state") != "FROZEN" or not key.get("concept_id"):
        raise GenerationPreconditionError("EXACTLY_ONE_FROZEN_KEY_REQUIRED")

    competitors = context.get("competitors") or []
    if len(competitors) < 3:
        raise GenerationPreconditionError("FEWER_THAN_THREE_APPROVED_COMPETITORS")
    seed_ids = [row.get("seed_id") for row in competitors]
    if any(not seed_id for seed_id in seed_ids) or len(seed_ids) != len(set(seed_ids)):
        raise GenerationPreconditionError("DUPLICATE_OR_MISSING_COMPETITOR")
    for competitor in competitors:
        if competitor.get("viable") is not True:
            raise GenerationPreconditionError("NONVIABLE_COMPETITOR")
        _require_reviewed_pinned(competitor.get("seed") or {}, "SEED")
        _require_reviewed_pinned(competitor.get("relation") or {}, "RELATION")
        anchor = competitor.get("anchor") or {}
        _require_reviewed_pinned(anchor, "ANCHOR")
        if anchor.get("supports_candidate") is not True:
            raise GenerationPreconditionError("BACKWARDS_ANCHOR")

    contrast = context.get("contrast_set") or {}
    if contrast.get("state") != "FROZEN":
        raise GenerationPreconditionError("UNFROZEN_CONTRAST_SET")
    _require_pinned(contrast, "CONTRAST_SET")
    if contrast.get("coherence") != "PASS":
        raise GenerationPreconditionError("CONTRAST_SET_COHERENCE_FAILURE")
    if contrast.get("second_key_risk") is not False:
        raise GenerationPreconditionError("SECOND_KEY_RISK")

    blueprint = context.get("blueprint") or {}
    if blueprint.get("state") != "BLUEPRINT_READY":
        raise GenerationPreconditionError("BLUEPRINT_NOT_READY")
    _require_pinned(blueprint, "BLUEPRINT")

    return {
        "opportunity_id": opportunity_id,
        "verdict": "PASS",
        "feature_ready": True,
        "seed_ready": True,
        "contrast_ready": True,
        "blueprint_ready": True,
        "approved_competitor_count": len(competitors),
        "selected_seed_ids": seed_ids,
    }


def execute_generation(
    context: dict[str, Any], generator: Callable[[], Any]
) -> dict[str, Any]:
    """Invoke ``generator`` only after the centralized precondition passes."""
    receipt = assert_generation_ready(context)
    return {"precondition": receipt, "generated": generator()}
