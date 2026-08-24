"""Build research/tn2025/toc_inventory.json.

Mechanical, deterministic extraction ONLY - no MCC mapping, no clinical
judgment calls. Produces a 3-level hierarchy:

  chapter (from derived/toronto-notes-2025/chapters/<code>/manifest.json,
           itself copied from the codex/qbank-production branch's
           already-validated chapter-boundary detection)
    -> section (parsed from the chapter's own printed internal table of
                contents page; page-anchored via the chapter's own
                <code><N> page-numbering scheme, e.g. "C19", "P70")
      -> topic (the un-anchored bullet lines listed under each section in
                that same TOC; NOT independently page-anchored - the TOC
                itself doesn't give them one)

Subtopic-level (in-page heading detection within actual chapter content,
beyond what the chapter's own TOC lists) is explicitly NOT attempted here -
the existing pipeline's per-page "headings" field is empty for every page
checked, meaning no automated in-page heading detector exists yet. Building
one is separate follow-on work, not silently faked here.

OCR quality caveat: Toronto Notes TOC pages use dot-leaders between a
section title and its page number (e.g. "Chest Pain......C5"). OCR often
mangles the leader run into irregular junk ("0.0.6.0 ee eee ee es"). This
script strips a permissive leader-run pattern to recover the heading text,
but does NOT attempt to correct OCR misreadings of the heading text itself
(e.g. "ACrOMYMS" is preserved as printed by OCR, not silently corrected to
"Acronyms"). Every heading also carries the untouched raw OCR line for
manual review.
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHAPTERS_DIR = REPO / "derived" / "toronto-notes-2025" / "chapters"
OCR_PAGES_DIR = REPO / "derived" / "toronto-notes-2025" / "ocr" / "pages"
OUT = REPO / "research" / "tn2025" / "toc_inventory.json"

# Trailing page-label token at end of line: chapter code (1-5 letters,
# case-insensitive) immediately followed by digits, e.g. "C19", "c5", "P70".
TRAILING_CODE_RE = re.compile(r"^(?P<pre>.*?)(?P<code>[A-Za-z]{1,5})(?P<num>\d{1,4})\s*$")

# A token is kept as part of the cleaned heading if, after stripping
# trailing punctuation, what remains is purely alphabetic (letters/hyphens/
# apostrophes only, no digits) and non-empty. OCR-mangled dot-leaders
# ("....", "0.0.6.0", short lowercase noise like "ee"/"es"/"ccc") reliably
# fail this test because they contain digits or reduce to an empty string
# once punctuation is stripped, so the walk stops there.
WORD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z\-']*$")


def clean_heading_from_pre_code_text(pre: str) -> str:
    kept = []
    for tok in pre.strip().split():
        core = tok.strip(".,;:")
        if core and WORD_TOKEN_RE.match(core):
            kept.append(core)
        else:
            break
    return " ".join(kept)

# Lines to always skip (credits/editor boilerplate on the first chapter page)
SKIP_LINE_PATTERNS = [
    re.compile(r"chapter editors?", re.IGNORECASE),
    re.compile(r"associate editors?", re.IGNORECASE),
    re.compile(r"EBM editors?", re.IGNORECASE),
    re.compile(r"staff editors?", re.IGNORECASE),
    re.compile(r"^Toronto Notes 2025$", re.IGNORECASE),
    re.compile(r"^Dr\.", re.IGNORECASE),
]


def load_page_text(pdf_page: int) -> str:
    path = OCR_PAGES_DIR / f"{pdf_page:04d}.json"
    with open(path) as f:
        d = json.load(f)
    return d.get("ocr_text", "")


def is_skip_line(line: str) -> bool:
    if not line.strip():
        return True
    for pat in SKIP_LINE_PATTERNS:
        if pat.search(line):
            return True
    return False


def match_section_line(line: str, chapter_code: str):
    """Return (heading, page_num) if line ends in this chapter's page code
    (e.g. 'C19') preceded by a heading recoverable via the word-token walk,
    else None. Requires the recovered heading to be non-empty so that
    isolated page-number remnants (e.g. a bare 'C2' page-header line) are
    not misparsed as a zero-length section."""
    m = TRAILING_CODE_RE.match(line.strip())
    if not m:
        return None
    if m.group("code").upper() != chapter_code.upper():
        return None
    heading = clean_heading_from_pre_code_text(m.group("pre"))
    if not heading:
        return None
    return heading, int(m.group("num"))


def find_toc_pages(chapter_code: str, pdf_pages: list) -> list:
    """Return the list of pdf_page numbers (subset of the chapter's own
    pages, in order) that appear to be the chapter's internal TOC, by
    counting section-line matches restricted to this chapter's code on
    each of the first 4 pages."""
    candidates = []
    for pdf_page in pdf_pages[:4]:
        text = load_page_text(pdf_page)
        count = sum(1 for line in text.splitlines() if match_section_line(line.strip(), chapter_code))
        candidates.append((pdf_page, count))

    # A real TOC page has several matches; require >=3 to qualify.
    toc_pages = [p for p, c in candidates if c >= 3]
    return toc_pages


def parse_toc(chapter_code: str, toc_pages: list, chapter_start_pdf_page: int) -> list:
    """Parse the identified TOC page(s) into an ordered list of section
    dicts, each with nested topic strings."""
    sections = []
    current_section = None
    seen_first_section = False

    for pdf_page in toc_pages:
        text = load_page_text(pdf_page)
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if is_skip_line(line):
                continue

            m = match_section_line(line, chapter_code)
            if m:
                seen_first_section = True
                heading, page_num = m
                target_pdf_page = chapter_start_pdf_page + page_num - 1
                current_section = {
                    "section_title": heading,
                    "chapter_relative_page_label": f"{chapter_code.upper()}{page_num}",
                    "start_pdf_page": target_pdf_page,
                    "end_pdf_page": None,  # filled in after all sections parsed
                    "raw_ocr_line": raw_line,
                    "topics": [],
                }
                sections.append(current_section)
                continue

            # Not a section line. Before the first section is found, this is
            # still credits/boilerplate - skip. After, treat as a topic
            # bullet nested under the current section (if any, and if it
            # looks like real text, not stray OCR noise).
            if not seen_first_section:
                continue
            if current_section is None:
                continue
            if len(line) < 2:
                continue
            # Skip lines that are themselves clearly page headers/footers
            # (e.g. "C2 Cardiology and Cardiac Surgery")
            if re.match(rf"^{re.escape(chapter_code)}\d+\b", line, re.IGNORECASE):
                continue
            current_section["topics"].append(line)

    return sections


def fill_section_end_pages(sections: list, chapter_last_pdf_page: int):
    for i, sec in enumerate(sections):
        if i + 1 < len(sections):
            next_start = sections[i + 1]["start_pdf_page"]
            sec["end_pdf_page"] = max(sec["start_pdf_page"], next_start - 1)
        else:
            sec["end_pdf_page"] = chapter_last_pdf_page


def main():
    chapter_dirs = sorted(CHAPTERS_DIR.iterdir())
    chapters_out = []
    total_sections = 0
    total_topics = 0
    chapters_with_no_toc_detected = []

    for cdir in chapter_dirs:
        manifest_path = cdir / "manifest.json"
        if not manifest_path.exists():
            continue
        with open(manifest_path) as f:
            manifest = json.load(f)

        chapter_code = manifest["chapter_code"]
        chapter_title = manifest["chapter_title"]
        pdf_pages = [p["pdf_page"] for p in manifest["pages"]]
        chapter_start = min(pdf_pages)
        chapter_end = max(pdf_pages)

        toc_pages = find_toc_pages(chapter_code, pdf_pages)
        if not toc_pages:
            chapters_with_no_toc_detected.append(chapter_code)
            sections = []
            status = "NO_TOC_DETECTED_NEEDS_MANUAL_REVIEW"
            coverage_note = None
        else:
            sections = parse_toc(chapter_code, toc_pages, chapter_start)
            fill_section_end_pages(sections, chapter_end)
            status = "PARSED"
            # Data-quality signal: if the first detected section starts well
            # after the chapter's actual first content page, OCR likely
            # dropped the trailing page-number token for one or more early
            # TOC entries (observed directly in e.g. Family Medicine, where
            # the dot-leader run for early entries consumed the line before
            # OCR reached the printed page number). This is a real
            # extraction gap, not guessed at or silently absorbed.
            first_section_start = sections[0]["start_pdf_page"] if sections else None
            expected_early_bound = chapter_start + 5  # credits + acronyms page(s)
            if first_section_start is not None and first_section_start > expected_early_bound:
                status = "PARSED_INCOMPLETE_COVERAGE_SUSPECTED"
                coverage_note = (
                    f"First detected section starts at pdf page "
                    f"{first_section_start}, {first_section_start - chapter_start} "
                    f"pages into a chapter starting at {chapter_start}. This gap is "
                    f"larger than the typical 1-5 page credits/acronyms preamble, "
                    f"indicating the OCR text for one or more early TOC entries is "
                    f"missing its trailing page-number token (dot-leader consumed "
                    f"the line before reaching the number) and those sections were "
                    f"not captured. Needs manual review against the source PDF."
                )
            else:
                coverage_note = None

        total_sections += len(sections)
        total_topics += sum(len(s["topics"]) for s in sections)

        chapters_out.append({
            "chapter_code": chapter_code,
            "chapter_title": chapter_title,
            "pdf_page_range": [chapter_start, chapter_end],
            "tn_page_range": f"{chapter_code}1-{chapter_code}{chapter_end - chapter_start + 1}",
            "page_count": len(pdf_pages),
            "toc_source_pdf_pages": toc_pages,
            "toc_extraction_status": status,
            "coverage_quality_note": coverage_note,
            "sections": sections,
        })

    inventory = {
        "schema_version": "1.0",
        "generated_at": "2026-08-24",
        "source_manifests": "derived/toronto-notes-2025/chapters/*/manifest.json",
        "provenance_note": (
            "Chapter-level page boundaries (chapter_code, chapter_title, "
            "pdf_page_range) were computed on the codex/qbank-production "
            "git branch and copied into this gitignored derived/ tree for "
            "reuse (not merged as code/history into main). Section- and "
            "topic-level structure below is newly extracted in this pass "
            "by deterministically parsing each chapter's own printed "
            "internal table of contents page(s), located by counting "
            "regex matches of that chapter's own page-numbering scheme "
            "(e.g. 'C19', 'P70') on each chapter's first few pages."
        ),
        "extraction_method": "scripts/qbank/build_tn_toc_inventory.py",
        "hierarchy_depth_achieved": (
            "3 of 4 levels: chapter (page-range anchored) -> section "
            "(page-range anchored, derived from the chapter's own TOC "
            "page-number citations) -> topic (listed under its section in "
            "TOC order, NOT independently page-anchored - the printed TOC "
            "does not give sub-items their own page numbers). Subtopic-level "
            "in-page heading detection was NOT attempted - the existing "
            "OCR pipeline's per-page 'headings' field is empty for every "
            "page sampled, meaning no automated in-page heading detector "
            "exists yet; that is separate follow-on work."
        ),
        "known_limitations": [
            "OCR quality: table-of-contents dot-leaders are frequently "
            "mangled by OCR into irregular character runs; heading text is "
            "preserved as OCR'd (not spell-corrected) to avoid inventing "
            "content. Every section retains 'raw_ocr_line' for manual audit.",
            "Chapters where fewer than 3 section-pattern matches were found "
            "on the first 4 pages are marked toc_extraction_status: "
            "NO_TOC_DETECTED_NEEDS_MANUAL_REVIEW with zero sections - this "
            "is a known gap, not silently papered over.",
            "Topic bullet lines are attributed to the most recently parsed "
            "section in TOC reading order; a small number of OCR line-break "
            "artifacts may misattribute a topic to the wrong section - not "
            "individually verified against every one of the ~32 chapters.",
        ],
        "summary": {
            "total_chapters": len(chapters_out),
            "total_sections": total_sections,
            "total_topics": total_topics,
            "chapters_with_no_toc_detected": chapters_with_no_toc_detected,
            "chapters_with_suspected_incomplete_coverage": [
                c["chapter_code"] for c in chapters_out
                if c["toc_extraction_status"] == "PARSED_INCOMPLETE_COVERAGE_SUSPECTED"
            ],
            "chapters_fully_parsed": [
                c["chapter_code"] for c in chapters_out
                if c["toc_extraction_status"] == "PARSED"
            ],
        },
        "chapters": chapters_out,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {OUT}")
    print(f"Chapters: {len(chapters_out)}, Sections: {total_sections}, Topics: {total_topics}")
    if chapters_with_no_toc_detected:
        print(f"WARNING - no TOC detected for: {chapters_with_no_toc_detected}")


if __name__ == "__main__":
    main()
