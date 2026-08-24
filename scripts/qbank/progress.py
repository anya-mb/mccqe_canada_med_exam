"""Filesystem-derived JSON and Markdown progress reporting."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile

from .errors import QbankError, SchemaValidationError
from .jsonio import read_json, write_json_atomic
from .manifests import validate_manifest_set
from .schema import validate_instance


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_QUESTION_DIRECTORIES = ("candidates", "verified", "quarantine", "rejected", "retired")
_JOB_STATES = ("pending", "running", "completed", "failed")
_BLIND_PASSED = frozenset(
    {"BLIND_PASS", "MEDICAL_PASS", "QA_PASS", "HUMAN_REVIEWED", "PUBLISHED"}
)
_QA_PASSED = frozenset({"QA_PASS", "PUBLISHED"})
_PUBLICATION_ELIGIBLE = frozenset({"QA_PASS", "HUMAN_REVIEWED", "PUBLISHED"})


def _timestamp(now: datetime | None) -> str:
    value = datetime.now(timezone.utc) if now is None else now
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("progress clock must be a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_object(path: Path, kind: str) -> dict:
    try:
        value = read_json(path)
    except (OSError, QbankError) as exc:
        raise SchemaValidationError(f"unable to read {kind}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaValidationError(f"{kind} must be a JSON object: {path}")
    return value


def _json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def _manifests(root: Path) -> list[dict]:
    values = [_read_object(path, "manifest") for path in _json_files(root / "manifests")]
    validate_manifest_set(values)
    return values


def _validated_question(path: Path) -> dict:
    value = _read_object(path, "question")
    public_value = dict(value)
    public_value.pop("human_review", None)
    validate_instance(_REPOSITORY_ROOT, "question", public_value)
    return public_value


def _questions(root: Path) -> list[dict]:
    seen: dict[str, Path] = {}
    questions: list[dict] = []
    for directory_name in _QUESTION_DIRECTORIES:
        for path in _json_files(root / directory_name):
            question = _validated_question(path)
            identifier = question["id"]
            if identifier in seen:
                raise SchemaValidationError(
                    f"question {identifier!r} exists in multiple lifecycle files: "
                    f"{seen[identifier]} and {path}"
                )
            seen[identifier] = path
            questions.append(question)
    return sorted(questions, key=lambda question: question["id"])


def _jobs(root: Path) -> dict[str, int]:
    counts = {state: 0 for state in _JOB_STATES}
    seen: dict[str, Path] = {}
    for state in _JOB_STATES:
        for path in _json_files(root / "jobs" / state):
            job = _read_object(path, "job")
            validate_instance(_REPOSITORY_ROOT, "job", job)
            identifier = job["job_id"]
            if identifier in seen:
                raise SchemaValidationError(
                    f"job {identifier!r} exists in multiple queue files: "
                    f"{seen[identifier]} and {path}"
                )
            if job["status"] != state.upper():
                raise SchemaValidationError(
                    f"job {identifier!r} status disagrees with queue directory {state!r}"
                )
            seen[identifier] = path
            counts[state] += 1
    return counts


def _empty_breakdown() -> dict[str, int]:
    return {"planned": 0, "generated": 0, "blind_passed": 0, "qa_passed": 0}


def build_progress(root: Path, now: datetime | None = None) -> dict:
    """Build a schema-valid progress report exclusively from repository files."""
    root = Path(root)
    manifests = _manifests(root)
    questions = _questions(root)
    disciplines: defaultdict[str, dict[str, int]] = defaultdict(_empty_breakdown)
    chapters: defaultdict[str, dict[str, int]] = defaultdict(_empty_breakdown)

    planned = 0
    chapter_planned: defaultdict[str, int] = defaultdict(int)
    for manifest in manifests:
        discipline = manifest["discipline"]
        for batch in manifest["batches"]:
            count = len(batch["question_ids"])
            chapter = batch["chapter"]
            planned += count
            disciplines[discipline]["planned"] += count
            chapters[chapter]["planned"] += count
            chapter_planned[chapter] += count

    blind_passed = 0
    qa_passed = 0
    rejected = 0
    quarantined = 0
    human_reviewed = 0
    chapter_eligible: defaultdict[str, int] = defaultdict(int)
    for question in questions:
        discipline = question["discipline"]
        chapter = question["chapter"]
        status = question["status"]
        disciplines[discipline]["generated"] += 1
        chapters[chapter]["generated"] += 1
        if status in _BLIND_PASSED:
            blind_passed += 1
            disciplines[discipline]["blind_passed"] += 1
            chapters[chapter]["blind_passed"] += 1
        if status in _QA_PASSED:
            qa_passed += 1
            disciplines[discipline]["qa_passed"] += 1
            chapters[chapter]["qa_passed"] += 1
        if status == "REJECTED":
            rejected += 1
        if status == "QUARANTINE":
            quarantined += 1
        if status == "HUMAN_REVIEWED":
            human_reviewed += 1
        if status in _PUBLICATION_ELIGIBLE:
            chapter_eligible[chapter] += 1

    coverage_gaps = []
    for chapter in sorted(chapter_planned):
        gap = chapter_planned[chapter] - chapter_eligible[chapter]
        if gap > 0:
            noun = "question" if gap == 1 else "questions"
            coverage_gaps.append(f"{chapter}: {gap} {noun} remain")

    report = {
        "generated_at": _timestamp(now),
        "planned": planned,
        "generated": len(questions),
        "blind_passed": blind_passed,
        "qa_passed": qa_passed,
        "rejected": rejected,
        "quarantined": quarantined,
        "human_reviewed": human_reviewed,
        "disciplines": {key: disciplines[key] for key in sorted(disciplines)},
        "chapters": {key: chapters[key] for key in sorted(chapters)},
        "jobs": _jobs(root),
        "coverage_gaps": coverage_gaps,
    }
    validate_instance(_REPOSITORY_ROOT, "progress", report)
    return report


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _breakdown_table(label: str, values: dict[str, dict[str, int]]) -> list[str]:
    lines = [
        f"| {label} | Planned | Generated | Blind passed | QA passed |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, counts in values.items():
        lines.append(
            f"| {_markdown_cell(name)} | {counts['planned']} | {counts['generated']} | "
            f"{counts['blind_passed']} | {counts['qa_passed']} |"
        )
    return lines


def _markdown(report: dict) -> str:
    lines = [
        "# Qbank Progress",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        "## Totals",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Planned | {report['planned']} |",
        f"| Generated | {report['generated']} |",
        f"| Blind passed | {report['blind_passed']} |",
        f"| QA passed | {report['qa_passed']} |",
        f"| Human reviewed | {report['human_reviewed']} |",
        f"| Rejected | {report['rejected']} |",
        f"| Quarantined | {report['quarantined']} |",
        "",
        "## Disciplines",
        "",
        *_breakdown_table("Discipline", report["disciplines"]),
        "",
        "## Chapters",
        "",
        *_breakdown_table("Chapter", report["chapters"]),
        "",
        "## Jobs",
        "",
        "| State | Count |",
        "| --- | ---: |",
        f"| Pending | {report['jobs']['pending']} |",
        f"| Running | {report['jobs']['running']} |",
        f"| Completed | {report['jobs']['completed']} |",
        f"| Failed | {report['jobs']['failed']} |",
        "",
        "## Coverage gaps",
        "",
    ]
    lines.extend(
        (f"- {_markdown_cell(gap)}" for gap in report["coverage_gaps"])
        if report["coverage_gaps"]
        else ["- None"]
    )
    return "\n".join(lines) + "\n"


def _write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(value)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_progress(
    root: Path, now: datetime | None = None
) -> tuple[Path, Path]:
    """Regenerate deterministic JSON and Markdown reports from one snapshot."""
    root = Path(root)
    report = build_progress(root, now=now)
    json_path = root / "reports" / "progress.json"
    markdown_path = root / "reports" / "progress.md"
    write_json_atomic(json_path, report)
    _write_text_atomic(markdown_path, _markdown(report))
    return json_path, markdown_path
