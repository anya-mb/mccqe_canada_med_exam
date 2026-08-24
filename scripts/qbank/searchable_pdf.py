"""Build a PDF with an invisible OCR text layer for full-text search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import unicodedata

import pymupdf


_REPEATED_SINGLE_LETTER = re.compile(r"\b([a-z])(?:\s+\1){2,}\b", re.IGNORECASE)
_MAX_TEXTBOX_CHARS = 1800


def clean_ocr_text(text: str) -> str:
    """Normalize OCR noise without removing useful searchable text."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\u00a0", " ")
    normalized = _REPEATED_SINGLE_LETTER.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def load_ocr_pages(ocr_pages_dir: Path, page_count: int) -> dict[int, str]:
    """Load and clean exactly one OCR JSON record for every PDF page."""
    records: dict[int, str] = {}
    for path in sorted(ocr_pages_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid OCR JSON: {path}") from exc
        page_number = record.get("pdf_page")
        if not isinstance(page_number, int) or not 1 <= page_number <= page_count:
            raise ValueError(f"invalid pdf_page in OCR JSON: {path}")
        if page_number in records:
            raise ValueError(f"duplicate OCR page: {page_number}")
        raw_text = record.get("ocr_text", record.get("text", ""))
        if not isinstance(raw_text, str):
            raise ValueError(f"OCR text is not a string: {path}")
        records[page_number] = clean_ocr_text(raw_text)

    missing = sorted(set(range(1, page_count + 1)) - records.keys())
    if missing:
        raise ValueError("missing OCR pages: " + ", ".join(map(str, missing[:10])))
    return records


def _chunks(text: str, limit: int = _MAX_TEXTBOX_CHARS) -> list[str]:
    """Split text at whitespace so each invisible text object stays manageable."""
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _insert_searchable_text(page: pymupdf.Page, text: str) -> None:
    """Insert tiny white text for broad PDF-viewer search compatibility."""
    if not text:
        return
    for chunk in _chunks(text):
        page.insert_textbox(
            page.rect,
            chunk,
            fontname="helv",
            fontsize=0.5,
            lineheight=0.5,
            color=(1, 1, 1),
            overlay=True,
        )


def build_searchable_pdf(
    source_pdf: Path,
    ocr_pages_dir: Path,
    output_pdf: Path,
    clean_ocr_dir: Path,
) -> argparse.Namespace:
    """Create *output_pdf* and one clean UTF-8 text file per page."""
    if output_pdf.exists():
        raise FileExistsError(f"output already exists: {output_pdf}")
    document = pymupdf.open(source_pdf)
    try:
        pages = load_ocr_pages(ocr_pages_dir, document.page_count)
        clean_ocr_dir.mkdir(parents=True, exist_ok=True)
        for page_number, text in pages.items():
            (clean_ocr_dir / f"{page_number:04d}.txt").write_text(
                text + "\n" if text else "", encoding="utf-8"
            )
            _insert_searchable_text(document[page_number - 1], text)
        document.save(output_pdf, garbage=4, deflate=True)
        return argparse.Namespace(page_count=document.page_count)
    finally:
        document.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--ocr-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clean-ocr-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    clean_dir = args.clean_ocr_dir or args.ocr_dir.parent.parent / "clean-ocr"
    result = build_searchable_pdf(args.pdf, args.ocr_dir, args.output, clean_dir)
    print(f"SEARCHABLE_PDF_CREATED: {args.output} ({result.page_count} pages)")
    print(f"CLEAN_OCR_CREATED: {clean_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
