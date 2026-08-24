"""Cross-manifest validation for deterministic qbank allocation."""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re

from .errors import SchemaValidationError
from .schema import validate_instance


_QUESTION_ID = re.compile(r"^(?P<prefix>.+-)(?P<number>[0-9]+)$")


@dataclass(frozen=True)
class ManifestSummary:
    """Counts derived from a validated set of discipline manifests."""

    manifest_count: int
    batch_count: int
    target_questions: int
    question_count: int


@dataclass(frozen=True)
class ManifestDocument:
    """A validated manifest value paired with its repository-relative path."""

    relative_path: str
    value: dict


def _fail(message: str) -> None:
    raise SchemaValidationError(f"manifest set validation failed: {message}")


def _claim(identifier: str, kind: str, owner: str, seen: dict[str, str]) -> None:
    first_owner = seen.get(identifier)
    if first_owner is not None:
        _fail(
            f"duplicate {kind} ID {identifier!r}; used by {first_owner} and {owner}"
        )
    seen[identifier] = owner


def _validate_contiguous_ids(batch_id: str, question_ids: list[str]) -> None:
    parsed = [_QUESTION_ID.fullmatch(question_id) for question_id in question_ids]
    if any(match is None for match in parsed):
        _fail(f"batch {batch_id!r} must allocate contiguous question IDs")

    matches = [match for match in parsed if match is not None]
    prefix = matches[0].group("prefix")
    width = len(matches[0].group("number"))
    first = int(matches[0].group("number"))
    expected = [
        f"{prefix}{number:0{width}d}"
        for number in range(first, first + len(matches))
    ]
    if question_ids != expected:
        _fail(f"batch {batch_id!r} must allocate contiguous question IDs")


def _validate_manifest_totals(manifest: dict) -> None:
    manifest_id = manifest["manifest_id"]
    target = manifest["target_questions"]
    section_total = sum(section["target_questions"] for section in manifest["sections"])
    batch_total = sum(batch["target_questions"] for batch in manifest["batches"])

    if section_total != target:
        _fail(
            f"manifest {manifest_id!r} target {target} disagrees with "
            f"section target total {section_total}"
        )
    if batch_total != target:
        _fail(
            f"manifest {manifest_id!r} target {target} disagrees with "
            f"batch target total {batch_total}"
        )

    section_targets: dict[str, int] = {}
    for section in manifest["sections"]:
        chapter = section["chapter"]
        if chapter in section_targets:
            _fail(f"manifest {manifest_id!r} has duplicate section chapter {chapter!r}")
        section_targets[chapter] = section["target_questions"]

    batch_targets: defaultdict[str, int] = defaultdict(int)
    for batch in manifest["batches"]:
        batch_targets[batch["chapter"]] += batch["target_questions"]

    if section_targets != dict(batch_targets):
        _fail(
            f"manifest {manifest_id!r} section/batch target totals disagree: "
            f"sections={section_targets!r}, batches={dict(batch_targets)!r}"
        )


def validate_manifest_set(root: Path, manifests: list[dict]) -> ManifestSummary:
    """Validate schemas, mappings, totals, allocation, and global identifiers."""
    if not isinstance(manifests, list):
        _fail("manifests must be a list")

    for manifest in manifests:
        validate_instance(root, "manifest", manifest)

    manifest_ids: dict[str, str] = {}
    batch_ids: dict[str, str] = {}
    question_ids: dict[str, str] = {}
    batch_count = 0
    question_count = 0
    target_questions = 0

    for manifest in manifests:
        manifest_id = manifest["manifest_id"]
        _claim(manifest_id, "manifest", manifest_id, manifest_ids)
        _validate_manifest_totals(manifest)
        target_questions += manifest["target_questions"]

        for batch in manifest["batches"]:
            batch_id = batch["batch_id"]
            owner = f"manifest {manifest_id!r} batch {batch_id!r}"
            _claim(batch_id, "batch", owner, batch_ids)
            batch_count += 1

            target = batch["target_questions"]
            if not 40 <= target <= 60:
                _fail(
                    f"batch {batch_id!r} target_questions must be between 40 and 60"
                )
            if target != len(batch["question_ids"]):
                _fail(
                    f"batch {batch_id!r} target/question ID count mismatch: "
                    f"target={target}, IDs={len(batch['question_ids'])}"
                )

            mapping = batch["toronto_notes"]
            if mapping["chapter"] != batch["chapter"]:
                _fail(f"batch {batch_id!r} Toronto Notes chapter mapping disagrees")
            if mapping["section"] != batch["section"]:
                _fail(f"batch {batch_id!r} Toronto Notes section mapping disagrees")

            for question_id in batch["question_ids"]:
                _claim(question_id, "question", owner, question_ids)
            _validate_contiguous_ids(batch_id, batch["question_ids"])
            question_count += len(batch["question_ids"])

    if target_questions != question_count:
        _fail(
            f"target/question ID total mismatch: target={target_questions}, "
            f"IDs={question_count}"
        )

    return ManifestSummary(
        manifest_count=len(manifests),
        batch_count=batch_count,
        target_questions=target_questions,
        question_count=question_count,
    )
