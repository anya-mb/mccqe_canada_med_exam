import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from qbank.errors import SourceValidationError
from qbank.source import scan_deploy_leaks, validate_source


def write_pdf(path: Path, title: str | None = "Synthetic Edition") -> None:
    """Write a tiny valid one-page PDF with a deterministic title."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>",
    ]
    if title is not None:
        objects.append(f"<< /Title ({title}) >>".encode())
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode())
        document.extend(body)
        document.extend(b"\nendobj\n")
    startxref = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    info = f" /Info {len(objects)} 0 R" if title is not None else ""
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R{info} >>\n"
        f"startxref\n{startxref}\n%%EOF\n".encode()
    )
    path.write_bytes(document)


@dataclass
class SourceRepo:
    root: Path
    config: dict
    expected_pages: int


@pytest.fixture
def source_repo(tmp_path) -> SourceRepo:
    pdf = tmp_path / "Toronto Notes.pdf"
    write_pdf(pdf)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return SourceRepo(
        root=tmp_path,
        config={
            "source": {
                "path": str(pdf),
                "expected_edition": "Synthetic Edition",
                "expected_pages": 1,
                "expected_size_bytes": pdf.stat().st_size,
                "expected_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            }
        },
        expected_pages=1,
    )


@pytest.fixture
def minimal_config():
    return {
        "source": {
            "path": "/does/not/exist.pdf",
            "expected_edition": "Synthetic Edition",
            "expected_pages": 1,
            "expected_size_bytes": 0,
            "expected_sha256": "0" * 64,
        }
    }


def test_source_validation_checks_hash_pages_and_git_exclusion(source_repo):
    """Catches a validator that returns success without checking the PDF."""
    report = validate_source(source_repo.root, source_repo.config)

    assert report.valid
    assert report.pages == source_repo.expected_pages


def test_missing_source_fails_closed(tmp_path, minimal_config):
    """Catches a validator that treats an unavailable source as valid."""
    with pytest.raises(SourceValidationError, match="missing"):
        validate_source(tmp_path, minimal_config)


def test_pdf_in_public_assets_is_a_leak(tmp_path):
    """Catches a deploy scan that overlooks PDFs under public assets."""
    leaked = tmp_path / "app/public/notes.pdf"
    leaked.parent.mkdir(parents=True)
    leaked.write_bytes(b"%PDF")

    assert scan_deploy_leaks(tmp_path) == [leaked]


def test_source_metadata_hash_and_page_mismatches_fail(source_repo):
    """Catches validators that omit any configured PDF integrity check."""
    for key, value in (
        ("expected_sha256", "0" * 64),
        ("expected_pages", 2),
    ):
        config = {"source": dict(source_repo.config["source"])}
        config["source"][key] = value
        with pytest.raises(SourceValidationError):
            validate_source(source_repo.root, config)


def test_missing_expected_size_fails_closed(source_repo):
    """Catches validators that permit a source without size integrity metadata."""
    config = {"source": dict(source_repo.config["source"])}
    del config["source"]["expected_size_bytes"]

    with pytest.raises(SourceValidationError, match="missing required"):
        validate_source(source_repo.root, config)


def test_git_tracking_check_fails_closed_when_supplied_root_is_not_a_repository(tmp_path):
    """Catches Git failures that are incorrectly treated as an untracked source."""
    pdf = tmp_path / "source.pdf"
    write_pdf(pdf)
    config = {
        "source": {
            "path": str(pdf),
            "expected_edition": "Synthetic Edition",
            "expected_pages": 1,
            "expected_size_bytes": pdf.stat().st_size,
            "expected_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        }
    }
    with pytest.raises(SourceValidationError, match="Git tracking"):
        validate_source(tmp_path, config)


def test_source_without_optional_pdf_title_uses_verified_size_metadata(tmp_path):
    """Catches treating absent optional PDF titles as an integrity failure."""
    pdf = tmp_path / "source.pdf"
    write_pdf(pdf, title=None)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    config = {
        "source": {
            "path": str(pdf),
            "expected_edition": "Synthetic Edition",
            "expected_pages": 1,
            "expected_size_bytes": pdf.stat().st_size,
            "expected_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        }
    }

    report = validate_source(tmp_path, config)

    assert report.valid
    assert report.edition == "Synthetic Edition"


def test_available_pdf_title_must_match_expected_edition(source_repo):
    """Catches expected_edition being required in config but never enforced."""
    config = {"source": dict(source_repo.config["source"])}
    config["source"]["expected_edition"] = "Different Synthetic Edition"

    with pytest.raises(SourceValidationError, match="edition"):
        validate_source(source_repo.root, config)


def test_tracked_pdf_and_source_in_deploy_root_fail(source_repo):
    """Catches source checks that permit tracked or deployable private PDFs."""
    pdf = Path(source_repo.config["source"]["path"])
    subprocess.run(["git", "add", pdf.name], cwd=source_repo.root, check=True)
    with pytest.raises(SourceValidationError, match="tracked"):
        validate_source(source_repo.root, source_repo.config)

    public_pdf = source_repo.root / "public" / "Toronto Notes.pdf"
    public_pdf.parent.mkdir()
    write_pdf(public_pdf)
    config = {"source": dict(source_repo.config["source"], path=str(public_pdf))}
    config["source"]["expected_sha256"] = hashlib.sha256(public_pdf.read_bytes()).hexdigest()
    with pytest.raises(SourceValidationError, match="deploy"):
        validate_source(source_repo.root, config)


def test_deploy_scan_finds_private_derived_artifacts(tmp_path):
    """Catches a deploy scan that only looks for PDF suffixes."""
    leaked = tmp_path / "dist" / "derived" / "pages.json"
    leaked.parent.mkdir(parents=True)
    leaked.write_text("private source extraction", encoding="utf-8")

    assert scan_deploy_leaks(tmp_path) == [leaked]


@pytest.mark.parametrize(
    "private_directory",
    [
        "batches",
        "candidates",
        "blind",
        "blind_verification",
        "quarantine",
        "rejected",
        "retired",
        "derived",
        "jobs",
        "manifests",
        "verifier",
        "verifier_reasoning",
        "qa",
        "qa_notes",
        "rationale_verification",
    ],
)
def test_deploy_scan_finds_every_private_lifecycle_artifact(tmp_path, private_directory):
    """Catches omission of any private lifecycle artifact from public assets."""
    leaked = tmp_path / "app" / "public" / private_directory / "artifact.json"
    leaked.parent.mkdir(parents=True)
    leaked.write_text("private", encoding="utf-8")

    assert scan_deploy_leaks(tmp_path) == [leaked]


@pytest.mark.parametrize("deploy_root", ["app/public", "public", "dist"])
def test_deploy_scan_discovers_every_deploy_root(tmp_path, deploy_root):
    """Catches deploy-root discovery limited to one public-assets convention."""
    leaked = tmp_path / deploy_root / "derived" / "artifact.json"
    leaked.parent.mkdir(parents=True)
    leaked.write_text("private", encoding="utf-8")

    assert scan_deploy_leaks(tmp_path) == [leaked]


@pytest.mark.parametrize("link_target_kind", ["file", "directory", "broken"])
def test_deploy_scan_rejects_every_symlink_without_following_it(
    tmp_path, link_target_kind
):
    """Catches symlinked deploy content that redirects leakage scans externally."""
    deploy = tmp_path / "app/public"
    deploy.mkdir(parents=True)
    external = tmp_path / "external"
    if link_target_kind == "file":
        external.write_text("external private data", encoding="utf-8")
    elif link_target_kind == "directory":
        external.mkdir()
        (external / "private.json").write_text("external private data", encoding="utf-8")
    link = deploy / "linked-artifact"
    target = external if link_target_kind != "broken" else tmp_path / "missing"
    link.symlink_to(target, target_is_directory=link_target_kind != "file")

    assert scan_deploy_leaks(tmp_path) == [link]


@pytest.mark.parametrize(
    "relative",
    [
        "verified/raw-question.json",
        "config/project.json",
        ".qbank-stage-deadbeef/staged.json",
        ".qbank-backup-deadbeef/old.json",
    ],
)
def test_deploy_scan_rejects_raw_private_and_export_work_artifacts(
    tmp_path, relative
):
    """Catches private raw data or recoverable export trees beneath assets."""
    leaked = tmp_path / "dist" / relative
    leaked.parent.mkdir(parents=True)
    leaked.write_text("private", encoding="utf-8")

    assert scan_deploy_leaks(tmp_path) == [leaked]


@pytest.mark.parametrize(
    "relative",
    [
        "verified",
        "config",
        ".qbank-stage-deadbeef",
        ".qbank-backup-deadbeef",
    ],
)
def test_deploy_scan_rejects_empty_private_and_export_work_directories(
    tmp_path, relative
):
    """Catches private deploy categories even before a file is written."""
    leaked = tmp_path / "dist" / relative
    leaked.mkdir(parents=True)

    assert scan_deploy_leaks(tmp_path) == [leaked]


def test_symlinked_deploy_root_is_itself_a_leak(tmp_path):
    """Catches app/public redirected to an external directory."""
    external = tmp_path / "external-public"
    external.mkdir()
    (tmp_path / "app").mkdir()
    link = tmp_path / "app/public"
    link.symlink_to(external, target_is_directory=True)

    assert scan_deploy_leaks(tmp_path) == [link]
