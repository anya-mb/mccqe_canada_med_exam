"""The deterministic Toronto Notes index: schema, chunking and reproducibility.

The corpus is a legally obtained local study source. It may be indexed locally for
retrieval, and it may never become a tracked repository artifact, so these tests
assert both that the index is complete and that it stays under derived/.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from qbank.tn_index import (
    INDEX_RELATIVE_PATH,
    MAX_CHUNK_CHARS,
    TnIndexError,
    build_tn_index,
    chunk_page,
    classify_block,
    normalize_for_search,
    open_index,
    resolve_page_nodes,
    split_page_blocks,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "derived/toronto-notes-2025"
PAGES = CORPUS / "ocr/pages"

pytestmark = pytest.mark.skipif(
    not PAGES.is_dir(), reason="local Toronto Notes corpus is not present"
)


def page_document(pdf_page):
    return json.loads((PAGES / f"{pdf_page:04d}.json").read_text())


# ---------------------------------------------------------------- block layer


def test_running_header_is_dropped_and_its_page_label_is_kept():
    blocks, header = split_page_blocks(page_document(120)["ocr_text"])
    assert header["tn_page_label"] == "C30"
    assert header["running_header_text"].endswith("Cardiology and Cardiac Surgery")
    assert all("Cardiology and Cardiac Surgery" not in b["text"] for b in blocks[:1])


def test_a_short_titlecase_line_is_a_heading_and_a_sentence_is_not():
    assert classify_block("Ischemic Heart Disease")["kind"] == "HEADING"
    assert classify_block("Epidemiology")["kind"] == "HEADING"
    assert (
        classify_block(
            "most common cause of cardiovascular morbidity and mortality"
        )["kind"]
        != "HEADING"
    )


def test_bulleted_blocks_classify_as_list_and_figure_artifacts_as_noise():
    assert classify_block("+ refer to the guideline\n« optimal medical therapy")["kind"] == "LIST"
    for artifact in ("¥", "M", "| | | |", "y"):
        assert classify_block(artifact)["kind"] == "NOISE", artifact


def test_normalization_folds_case_bullets_and_whitespace_but_keeps_numerals():
    normalized = normalize_for_search("+  Troponin  RISE of 0.05 ng/mL\n« M:F=2:1")
    assert "troponin" in normalized
    assert "0.05" in normalized
    assert "2:1" in normalized or "2 1" in normalized
    assert "+" not in normalized and "«" not in normalized
    assert "  " not in normalized


# ---------------------------------------------------------------- chunk layer


def test_chunks_are_page_bounded_size_bounded_and_carry_provenance():
    chunks = chunk_page(page_document(120), document_id="TN2025", chapter_code="C",
                        tn_node_id="C.S06.T01", section_path="C > Ischemic Heart Disease")
    assert chunks
    for chunk in chunks:
        assert chunk["pdf_page"] == 120
        assert chunk["char_count"] <= MAX_CHUNK_CHARS
        assert chunk["chunk_id"].startswith("TNC-")
        assert chunk["text_sha256"] and chunk["document_id"] == "TN2025"
        assert chunk["chapter_code"] == "C"
        assert chunk["tn_page_label"] == "C30"


def test_chunk_ids_are_deterministic_across_rebuilds():
    first = chunk_page(page_document(120), document_id="TN2025", chapter_code="C",
                       tn_node_id="C.S06.T01", section_path="C")
    second = chunk_page(page_document(120), document_id="TN2025", chapter_code="C",
                        tn_node_id="C.S06.T01", section_path="C")
    assert [c["chunk_id"] for c in first] == [c["chunk_id"] for c in second]


def test_a_heading_starts_a_new_chunk():
    chunks = chunk_page(page_document(120), document_id="TN2025", chapter_code="C",
                        tn_node_id="C.S06.T01", section_path="C")
    subheadings = [c["subheading"] for c in chunks if c["subheading"]]
    assert "Epidemiology" in subheadings


def test_noise_only_blocks_do_not_become_chunks():
    chunks = chunk_page(page_document(120), document_id="TN2025", chapter_code="C",
                        tn_node_id="C.S06.T01", section_path="C")
    for chunk in chunks:
        assert chunk["text"].strip() not in {"¥", "M", "y", "| | | |"}


# ---------------------------------------------------------------- page joins


def test_every_page_resolves_to_the_deepest_toc_node_that_contains_it():
    resolution = resolve_page_nodes(ROOT)
    assert len(resolution) == 1595
    node = resolution[120]
    assert node["chapter_code"] == "C"
    assert node["tn_node_id"].startswith("C")
    assert node["section_path"].startswith("Cardiology")


# ---------------------------------------------------------------- index build


@pytest.fixture(scope="module")
def index_path(tmp_path_factory):
    target = tmp_path_factory.mktemp("tnindex") / "tn_index.sqlite3"
    build_tn_index(ROOT, target)
    return target


def test_the_index_covers_every_ocr_page_with_its_canonical_hash(index_path):
    connection = open_index(index_path)
    pages = json.loads((CORPUS / "ocr/page_index.json").read_text())
    indexed = dict(connection.execute("SELECT pdf_page, canonical_text_sha256 FROM pages"))
    assert len(indexed) == pages["page_count"] == 1595
    for page in pages["pages"]:
        assert indexed[page["pdf_page"]] == page["canonical_text_sha256"]


def test_structural_tables_match_the_canonical_source_artifacts(index_path):
    connection = open_index(index_path)
    count = lambda table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    assert count("chapters") == 32
    assert count("sections") == 2019
    assert count("study_units") == 1487
    assert count("chunks") > 5000


def test_fts_is_queryable_and_returns_the_owning_study_unit(index_path):
    connection = open_index(index_path)
    rows = list(connection.execute(
        "SELECT c.chunk_id, c.chapter_code, bm25(chunks_fts) AS score "
        "FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "
        "WHERE chunks_fts MATCH ? ORDER BY score LIMIT 5",
        ("bronchiolitis",),
    ))
    assert rows
    assert any(row[1] == "P" for row in rows)


def test_no_chunk_text_is_written_outside_the_gitignored_derived_tree():
    assert INDEX_RELATIVE_PATH.startswith("derived/")
    assert "derived/" in (ROOT / ".gitignore").read_text()


def test_building_twice_produces_identical_chunk_ids(tmp_path):
    first, second = tmp_path / "a.sqlite3", tmp_path / "b.sqlite3"
    build_tn_index(ROOT, first, page_limit=40)
    build_tn_index(ROOT, second, page_limit=40)
    ids = lambda p: [r[0] for r in open_index(p).execute(
        "SELECT chunk_id FROM chunks ORDER BY pdf_page, ordinal")]
    assert ids(first) == ids(second)
    assert ids(first)


def test_a_missing_corpus_fails_closed(tmp_path):
    with pytest.raises(TnIndexError):
        build_tn_index(tmp_path, tmp_path / "x.sqlite3")


def test_mcc_objectives_and_their_study_unit_links_are_indexed(index_path):
    connection = open_index(index_path)
    objectives = connection.execute("SELECT count(*) FROM mcc_objectives").fetchone()[0]
    links = connection.execute("SELECT count(*) FROM study_unit_objectives").fetchone()[0]
    assert objectives > 100
    assert links > objectives
    titled = connection.execute(
        "SELECT count(*) FROM mcc_objectives WHERE title IS NOT NULL"
    ).fetchone()[0]
    assert titled == objectives


def test_the_only_pages_without_chunks_are_the_quality_flagged_ones(index_path):
    connection = open_index(index_path)
    empty = list(connection.execute(
        "SELECT pdf_page, ocr_quality_flags FROM pages p "
        "WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.pdf_page = p.pdf_page)"
    ))
    assert len(empty) == 2
    for _, flags in empty:
        assert flags, "a page with no chunks must carry an OCR quality flag"


def test_the_tracked_build_manifest_carries_counts_and_no_corpus_prose(index_path, tmp_path):
    from qbank.tn_index import BUILD_MANIFEST_RELATIVE_PATH, write_index_build_manifest

    document = write_index_build_manifest(ROOT, index_path)
    assert document["counts"]["pages_indexed"] == 1595
    assert document["index_is_a_tracked_artifact"] is False
    assert document["authority_role"] == "TOPIC_DISCOVERY_SOURCE"
    serialized = json.dumps(document)
    # The manifest describes the corpus; it must not contain any of it. Every long
    # token in it should be a hash, an identifier or one of its own field values.
    assert "Ischemic Heart Disease" not in serialized
    assert (ROOT / BUILD_MANIFEST_RELATIVE_PATH).is_file()
