import json
from pathlib import Path

import pymupdf
import pytest

from qbank.searchable_pdf import (
    build_searchable_pdf,
    clean_ocr_text,
    load_ocr_pages,
)


def write_pdf(path: Path, page_count: int = 2) -> None:
    document = pymupdf.open()
    for _ in range(page_count):
        document.new_page(width=200, height=200)
    document.save(path)
    document.close()


def write_ocr_page(directory: Path, page: int, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{page:04d}.json").write_text(
        json.dumps({"pdf_page": page, "ocr_text": text}), encoding="utf-8"
    )


def test_clean_ocr_text_preserves_middle_searchable_words():
    text = "alpha\n\nbeta   gamma\n\n e e e e \n punctuation—here"

    cleaned = clean_ocr_text(text)

    assert cleaned == "alpha beta gamma punctuation—here"
    assert "beta gamma" in cleaned


def test_load_ocr_pages_requires_one_record_per_pdf_page(tmp_path):
    ocr_dir = tmp_path / "ocr" / "pages"
    write_ocr_page(ocr_dir, 1, "first")

    with pytest.raises(ValueError, match="missing OCR pages: 2"):
        load_ocr_pages(ocr_dir, page_count=2)


def test_build_searchable_pdf_writes_clean_text_and_searchable_invisible_layer(tmp_path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "searchable.pdf"
    clean_dir = tmp_path / "clean-ocr"
    write_pdf(source)
    ocr_dir = tmp_path / "ocr" / "pages"
    write_ocr_page(ocr_dir, 1, "first\n\npage has needle in the middle")
    write_ocr_page(ocr_dir, 2, "second page")

    result = build_searchable_pdf(source, ocr_dir, output, clean_dir)

    assert result.page_count == 2
    assert (clean_dir / "0001.txt").read_text(encoding="utf-8") == (
        "first page has needle in the middle\n"
    )
    document = pymupdf.open(output)
    assert "needle" in document[0].get_text().lower()
    assert "page has needle" in document[0].get_text().lower()
    assert document[0].get_text("words")
    document.close()
