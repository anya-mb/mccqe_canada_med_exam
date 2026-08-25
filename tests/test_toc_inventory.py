"""Deterministic validation tests for research/tn2025/toc_inventory.json
and research/tn2025/unresolved_headings.json.

These are structural/integrity tests only - they do not evaluate whether
any individual heading's text or page range is medically or editorially
"correct" (that would require re-reading the source PDF page by page for
every node, which is out of scope here). They verify the tree itself is
internally consistent, complete over all 32 chapters, and that every
extraction gap is accounted for rather than silently dropped.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO / "research" / "tn2025" / "toc_inventory.json"
UNRESOLVED_PATH = REPO / "research" / "tn2025" / "unresolved_headings.json"
CHAPTERS_DIR = REPO / "derived" / "toronto-notes-2025" / "chapters"

EXPECTED_CHAPTER_COUNT = 32


@pytest.fixture(scope="module")
def inventory():
    with open(INVENTORY_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def unresolved():
    with open(UNRESOLVED_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def nodes(inventory):
    return inventory["nodes"]


@pytest.fixture(scope="module")
def chapter_nodes(nodes):
    return [n for n in nodes if n["structural_type"] == "chapter"]


@pytest.fixture(scope="module")
def section_nodes(nodes):
    return [n for n in nodes if n["structural_type"] == "section"]


@pytest.fixture(scope="module")
def topic_nodes(nodes):
    return [n for n in nodes if n["structural_type"] == "topic"]


@pytest.fixture(scope="module")
def node_by_id(nodes):
    return {n["node_id"]: n for n in nodes}


@pytest.fixture(scope="module")
def expected_chapter_codes():
    return sorted(p.name for p in CHAPTERS_DIR.iterdir() if (p / "manifest.json").exists())


# ---------------------------------------------------------------------------
# Chapter coverage
# ---------------------------------------------------------------------------

class TestChapterCoverage:
    def test_exactly_32_chapters_expected_on_disk(self, expected_chapter_codes):
        assert len(expected_chapter_codes) == EXPECTED_CHAPTER_COUNT

    def test_inventory_has_exactly_32_chapter_nodes(self, chapter_nodes):
        assert len(chapter_nodes) == EXPECTED_CHAPTER_COUNT

    def test_all_disk_chapters_represented_in_inventory(self, chapter_nodes, expected_chapter_codes):
        inventory_codes = sorted(n["chapter_code"] for n in chapter_nodes)
        assert inventory_codes == expected_chapter_codes

    def test_every_chapter_has_at_least_one_section_or_explicit_no_toc_flag(
        self, chapter_nodes, section_nodes, inventory
    ):
        no_toc_chapters = set(inventory["summary"]["chapters_with_no_toc_detected"])
        section_chapter_codes = {n["chapter_code"] for n in section_nodes}
        for ch in chapter_nodes:
            code = ch["chapter_code"]
            has_sections = code in section_chapter_codes
            is_flagged_no_toc = code in no_toc_chapters
            assert has_sections or is_flagged_no_toc, (
                f"Chapter {code} has neither extracted sections nor an "
                f"explicit NO_TOC_DETECTED flag - a silent extraction gap."
            )


# ---------------------------------------------------------------------------
# Node ID integrity
# ---------------------------------------------------------------------------

class TestNodeIdIntegrity:
    def test_no_duplicate_node_ids(self, nodes):
        ids = [n["node_id"] for n in nodes]
        dupes = {i for i in ids if ids.count(i) > 1}
        assert not dupes, f"Duplicate node_ids found: {dupes}"

    def test_no_orphan_parent_ids(self, nodes, node_by_id):
        for n in nodes:
            if n["parent_id"] is None:
                assert n["level"] == 1, (
                    f"Node {n['node_id']} has parent_id=None but level={n['level']} "
                    f"(only chapter roots, level 1, may have no parent)"
                )
                continue
            assert n["parent_id"] in node_by_id, (
                f"Node {n['node_id']} references parent_id {n['parent_id']!r} "
                f"which does not exist in the inventory."
            )

    def test_chapter_roots_have_no_parent(self, chapter_nodes):
        for n in chapter_nodes:
            assert n["parent_id"] is None

    def test_sections_parent_is_their_own_chapter(self, section_nodes, node_by_id):
        for n in section_nodes:
            parent = node_by_id[n["parent_id"]]
            assert parent["structural_type"] == "chapter"
            assert parent["chapter_code"] == n["chapter_code"]

    def test_topics_parent_is_a_section_in_same_chapter(self, topic_nodes, node_by_id):
        for n in topic_nodes:
            parent = node_by_id[n["parent_id"]]
            assert parent["structural_type"] == "section"
            assert parent["chapter_code"] == n["chapter_code"]


# ---------------------------------------------------------------------------
# Hierarchy validity
# ---------------------------------------------------------------------------

class TestHierarchyValidity:
    def test_no_level_is_invented_beyond_source_support(self, nodes):
        # Only levels 1 (chapter), 2 (section), 3 (topic) exist - the task
        # explicitly forbids fabricating a 4th (subtopic) level not
        # supported by the source TOC extraction.
        levels = {n["level"] for n in nodes}
        assert levels <= {1, 2, 3}, f"Unexpected node levels found: {levels}"

    def test_level_matches_structural_type(self, nodes):
        expected = {"chapter": 1, "section": 2, "topic": 3}
        for n in nodes:
            assert n["level"] == expected[n["structural_type"]], (
                f"Node {n['node_id']} has structural_type={n['structural_type']!r} "
                f"but level={n['level']} (expected {expected[n['structural_type']]})"
            )

    def test_every_node_belongs_to_a_real_chapter(self, nodes, expected_chapter_codes):
        expected_set = set(expected_chapter_codes)
        for n in nodes:
            assert n["chapter_code"] in expected_set, (
                f"Node {n['node_id']} has chapter_code {n['chapter_code']!r} "
                f"which is not one of the 32 known chapters."
            )


# ---------------------------------------------------------------------------
# Page anchor validity
# ---------------------------------------------------------------------------

class TestPageAnchors:
    def test_start_pdf_page_le_end_pdf_page(self, nodes):
        violations = [
            n["node_id"] for n in nodes
            if n["start_pdf_page"] > n["end_pdf_page"]
        ]
        assert not violations, f"Nodes with start_pdf_page > end_pdf_page: {violations}"

    def test_node_page_range_within_chapter_boundaries(self, nodes, node_by_id):
        chapter_bounds = {
            n["chapter_code"]: (n["start_pdf_page"], n["end_pdf_page"])
            for n in nodes if n["structural_type"] == "chapter"
        }
        violations = []
        for n in nodes:
            lo, hi = chapter_bounds[n["chapter_code"]]
            if not (lo <= n["start_pdf_page"] <= hi and lo <= n["end_pdf_page"] <= hi):
                violations.append(
                    f"{n['node_id']}: [{n['start_pdf_page']}-{n['end_pdf_page']}] "
                    f"outside chapter {n['chapter_code']} bounds [{lo}-{hi}]"
                )
        assert not violations, "\n".join(violations)

    def test_sections_within_a_chapter_are_non_decreasing_by_start_page(self, section_nodes):
        by_chapter = {}
        for n in section_nodes:
            by_chapter.setdefault(n["chapter_code"], []).append(n)
        for code, secs in by_chapter.items():
            # Sections are stored in node list order; verify that order
            # itself, since node_id suffix (S01, S02...) is assigned in
            # that same construction order.
            ordered = sorted(secs, key=lambda s: s["node_id"])
            pages = [s["start_pdf_page"] for s in ordered]
            assert pages == sorted(pages), (
                f"Chapter {code}: section start pages not non-decreasing "
                f"in node_id order: {[(s['node_id'], s['start_pdf_page']) for s in ordered]}"
            )

    def test_topic_page_range_matches_its_parent_section(self, topic_nodes, node_by_id):
        for n in topic_nodes:
            parent = node_by_id[n["parent_id"]]
            assert n["start_pdf_page"] == parent["start_pdf_page"]
            assert n["end_pdf_page"] == parent["end_pdf_page"]


# ---------------------------------------------------------------------------
# Duplicate-extraction checks
# ---------------------------------------------------------------------------

class TestNoDuplicateExtraction:
    def test_no_duplicate_identical_title_under_same_parent(self, nodes):
        from collections import Counter
        by_parent = {}
        for n in nodes:
            if n["parent_id"] is None:
                continue
            by_parent.setdefault(n["parent_id"], []).append(n["title"])
        violations = []
        for parent_id, titles in by_parent.items():
            counts = Counter(titles)
            dupes = {t: c for t, c in counts.items() if c > 1}
            if dupes:
                violations.append(f"parent {parent_id}: {dupes}")
        assert not violations, (
            "Duplicate identical child titles under the same parent "
            "(unmerged repeated TOC line extraction):\n" + "\n".join(violations)
        )

    def test_no_duplicate_section_start_page_within_a_chapter(self, section_nodes):
        from collections import Counter
        by_chapter = {}
        for n in section_nodes:
            by_chapter.setdefault(n["chapter_code"], []).append(n["start_pdf_page"])
        violations = []
        for code, pages in by_chapter.items():
            counts = Counter(pages)
            dupes = {p: c for p, c in counts.items() if c > 1}
            if dupes:
                violations.append(f"{code}: {dupes}")
        assert not violations, (
            "Two distinct section nodes claim the identical start_pdf_page "
            "within the same chapter (should have been merged):\n"
            + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# Unresolved-heading completeness
# ---------------------------------------------------------------------------

class TestUnresolvedCompleteness:
    def test_unresolved_count_matches_summary(self, inventory, unresolved):
        assert inventory["summary"]["unresolved_heading_count"] == unresolved["total_unresolved"]
        assert unresolved["total_unresolved"] == len(unresolved["unresolved_headings"])

    def test_every_unresolved_entry_has_a_chapter_code_and_reason(self, unresolved):
        for entry in unresolved["unresolved_headings"]:
            assert entry.get("chapter_code"), f"Unresolved entry missing chapter_code: {entry}"
            assert entry.get("reason"), f"Unresolved entry missing reason: {entry}"
            assert entry.get("status") in ("UNRESOLVED", "UNRESOLVED_NO_TOC_DETECTED")

    def test_no_toc_detected_chapters_have_a_corresponding_unresolved_entry(
        self, inventory, unresolved
    ):
        no_toc_chapters = set(inventory["summary"]["chapters_with_no_toc_detected"])
        flagged_chapters = {
            e["chapter_code"] for e in unresolved["unresolved_headings"]
            if e["status"] == "UNRESOLVED_NO_TOC_DETECTED"
        }
        assert no_toc_chapters == flagged_chapters, (
            f"Mismatch between summary.chapters_with_no_toc_detected "
            f"({no_toc_chapters}) and unresolved entries flagged "
            f"UNRESOLVED_NO_TOC_DETECTED ({flagged_chapters})"
        )

    def test_unresolved_chapter_codes_are_real_chapters(self, unresolved, expected_chapter_codes):
        expected_set = set(expected_chapter_codes)
        for e in unresolved["unresolved_headings"]:
            assert e["chapter_code"] in expected_set


# ---------------------------------------------------------------------------
# Extraction method / confidence field integrity
# ---------------------------------------------------------------------------

class TestExtractionMetadata:
    VALID_METHODS = {
        "CHAPTER_MANIFEST", "TOC_OCR", "BODY_HEADING_CONFIRMATION",
        "TOC_OCR_UNANCHORED",
    }
    VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}

    def test_every_node_has_a_valid_extraction_method(self, nodes):
        for n in nodes:
            assert n["extraction_method"] in self.VALID_METHODS, (
                f"{n['node_id']} has unexpected extraction_method "
                f"{n['extraction_method']!r}"
            )

    def test_every_node_has_a_valid_confidence(self, nodes):
        for n in nodes:
            assert n["confidence"] in self.VALID_CONFIDENCE

    def test_sections_are_not_extraction_method_toc_ocr_unanchored(self, section_nodes):
        # TOC_OCR_UNANCHORED is reserved for topic nodes (which never get
        # independent page confirmation by design); a section must always
        # carry one of the three page-anchored methods.
        for n in section_nodes:
            assert n["extraction_method"] != "TOC_OCR_UNANCHORED"


# ---------------------------------------------------------------------------
# Titles are non-trivial (basic sanity, not a content-correctness check)
# ---------------------------------------------------------------------------

class TestTitleSanity:
    def test_no_empty_titles(self, nodes):
        empties = [n["node_id"] for n in nodes if not n["title"].strip()]
        assert not empties, f"Nodes with empty title: {empties}"

    def test_section_titles_do_not_end_with_their_own_chapter_code(self, section_nodes):
        violations = [
            n["node_id"] for n in section_nodes
            if n["title"].upper().endswith(" " + n["chapter_code"].upper())
            or n["title"].upper() == n["chapter_code"].upper()
        ]
        assert not violations, (
            f"Section titles ending in a stray copy of their own chapter "
            f"code (extraction artifact): {violations}"
        )
