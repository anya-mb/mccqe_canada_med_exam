"""Deterministic local index over the Toronto Notes corpus.

The corpus is a legally obtained local study source. It is indexed here for
retrieval only: the database lives under the gitignored ``derived/`` tree, it is
rebuilt from canonical local artifacts rather than committed, and no module in
this package emits corpus prose into a tracked file.

Nothing here is a generic fixed-token RAG chunker. Toronto Notes is heavily
structured -- a running header, blank-line separated blocks, short title-case
headings above bulleted clinical lists -- and that structure is what makes a
chunk a retrieval unit rather than a slice. Chunks are page-bounded and
heading-bounded by construction, because a chunk that spans two topics cannot
answer "which study unit does this belong to", which is the only question
retrieval actually asks of it.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

from .errors import QbankError
from .paths import resolve_root_path


class TnIndexError(QbankError):
    """The corpus, a canonical structural artifact, or the index is unusable."""


DOCUMENT_ID = "TN2025"
INDEX_RELATIVE_PATH = "derived/tn_index/tn_index.sqlite3"
BUILD_MANIFEST_RELATIVE_PATH = "research/tn2025/tn_index_build_manifest.json"

CORPUS_RELATIVE_PATH = "derived/toronto-notes-2025"
PAGE_INDEX_RELATIVE_PATH = f"{CORPUS_RELATIVE_PATH}/ocr/page_index.json"
TOC_RELATIVE_PATH = "research/tn2025/toc_inventory.json"
SCOPE_RELATIVE_PATH = "research/scope/master_scope_crosswalk.json"

# A chunk is a retrieval unit. Large enough to carry a clinical statement with its
# qualifiers, small enough that a BM25 hit localizes to one topic rather than one page.
MAX_CHUNK_CHARS = 1800
MIN_CHUNK_CHARS = 40

# Chosen deliberately, and recorded in the build manifest rather than left implicit.
# porter folds -itis/-osis/-aemia morphology, which medical recall needs; it also
# over-stems some drug names, which is an accepted and stated trade-off because the
# graph and the anchor floor -- not BM25 -- carry admissibility.
FTS_TOKENIZER = "porter unicode61 remove_diacritics 2"

BULLET_CHARACTERS = "+•«»=*■□▪-–—·"
_RUNNING_HEADER_LEADING = re.compile(r"^([A-Z]{1,4}\d{1,3})\s+(\S.*)$")
_RUNNING_HEADER_TRAILING = re.compile(r"^(\S.*?)\s+([A-Z]{1,4}\d{1,3})$")
_WHITESPACE = re.compile(r"\s+")
_SEARCH_STRIPPABLE = re.compile(r"[^0-9a-z%./:-]+")


# --------------------------------------------------------------------- blocks


def _strip_bullet(line: str) -> str:
    return line.lstrip(BULLET_CHARACTERS + " \t")


def classify_block(text: str) -> dict[str, Any]:
    """Classify one blank-line-delimited block of OCR text.

    The classes exist to answer three retrieval questions and no others: does this
    block start a new topic (HEADING), is it clinical content (LIST/PARAGRAPH), or
    is it a figure artifact that would only pollute the term index (NOISE).
    """
    stripped = text.strip()
    if not stripped:
        return {"kind": "NOISE", "reason": "EMPTY"}

    lines = [line for line in stripped.split("\n") if line.strip()]
    letters = sum(character.isalpha() for character in stripped)
    words = stripped.split()

    # Figure scaffolding: arrows, rules, single glyphs, table pipes.
    if letters < 3 or len(stripped) < 4:
        return {"kind": "NOISE", "reason": "TOO_SHORT"}
    if letters / max(len(stripped), 1) < 0.45:
        return {"kind": "NOISE", "reason": "LOW_ALPHABETIC_RATIO"}

    bulleted = sum(
        1 for line in lines if line.lstrip().startswith(tuple(BULLET_CHARACTERS))
    )
    if bulleted and bulleted >= max(1, len(lines) // 2):
        return {"kind": "LIST", "reason": "BULLETED", "bulleted_lines": bulleted}

    if (
        len(lines) == 1
        and len(words) <= 8
        and not stripped.endswith((".", ",", ";", ":"))
        and stripped[0].isupper()
        and not stripped.lstrip().startswith(tuple(BULLET_CHARACTERS))
    ):
        return {"kind": "HEADING", "reason": "SHORT_TITLE_LINE"}

    return {"kind": "PARAGRAPH", "reason": "PROSE"}


def split_page_blocks(ocr_text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Split a page into classified blocks, returning the running header separately.

    The running header carries the printed Toronto Notes page label (``C30``), which
    is the citable page reference, so it is extracted rather than merely discarded.
    """
    lines = ocr_text.split("\n")
    header: dict[str, Any] = {"tn_page_label": None, "running_header_text": None}
    body_start = 0
    for index, line in enumerate(lines[:3]):
        candidate = line.strip()
        if not candidate:
            continue
        leading = _RUNNING_HEADER_LEADING.match(candidate)
        trailing = _RUNNING_HEADER_TRAILING.match(candidate)
        match = leading or trailing
        if match and len(candidate) < 90:
            header = {
                "tn_page_label": match.group(1) if leading else match.group(2),
                "running_header_text": candidate,
            }
            body_start = index + 1
        break

    blocks: list[dict[str, Any]] = []
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        text = "\n".join(current).strip()
        current.clear()
        if not text:
            return
        # Toronto Notes prints a section heading directly above its bulleted list
        # with no blank line between them, so a heading is routinely the first line
        # of a content block. Peeling it off is what makes headings usable as chunk
        # boundaries at all; without it every heading is swallowed by its own list.
        lines = text.split("\n")
        if len(lines) > 1 and classify_block(lines[0])["kind"] == "HEADING":
            head = lines[0].strip()
            blocks.append({"text": head, **classify_block(head)})
            text = "\n".join(lines[1:]).strip()
            if not text:
                return
        blocks.append({"text": text, **classify_block(text)})

    for line in lines[body_start:]:
        if line.strip():
            current.append(line)
        else:
            flush()
    flush()
    return blocks, header


def normalize_for_search(text: str) -> str:
    """Normalize a block for the term index.

    Numerals, decimals, percentages and ratios survive because clinical thresholds
    are exactly what a stem asserts; bullets, case and OCR whitespace do not.
    """
    lowered = "\n".join(_strip_bullet(line) for line in text.lower().split("\n"))
    replaced = _SEARCH_STRIPPABLE.sub(" ", lowered)
    return _WHITESPACE.sub(" ", replaced).strip()


# --------------------------------------------------------------------- chunks


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_page(
    page_document: dict[str, Any],
    *,
    document_id: str,
    chapter_code: str | None,
    tn_node_id: str | None,
    section_path: str | None,
) -> list[dict[str, Any]]:
    """Chunk one OCR page into page- and heading-bounded retrieval units."""
    pdf_page = page_document["pdf_page"]
    blocks, header = split_page_blocks(page_document.get("ocr_text") or "")

    chunks: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    subheading: str | None = None
    pending_subheading: str | None = None

    def emit() -> None:
        nonlocal pending
        if not pending:
            return
        text = "\n".join(block["text"] for block in pending).strip()
        if len(text) < MIN_CHUNK_CHARS:
            pending = []
            return
        ordinal = len(chunks)
        text_sha256 = _sha256(text)
        identity = f"{document_id}|{pdf_page}|{ordinal}|{text_sha256}"
        chunks.append({
            "chunk_id": "TNC-" + _sha256(identity)[:24],
            "document_id": document_id,
            "chapter_code": chapter_code,
            "tn_node_id": tn_node_id,
            "section_path": section_path,
            "subheading": pending_subheading,
            "pdf_page": pdf_page,
            "tn_page_label": header["tn_page_label"],
            "ordinal": ordinal,
            "block_kinds": ",".join(sorted({block["kind"] for block in pending})),
            "text": text,
            "text_sha256": text_sha256,
            "char_count": len(text),
            "normalized_text_for_search": normalize_for_search(text),
        })
        pending = []

    for block in blocks:
        if block["kind"] == "NOISE":
            continue
        if block["kind"] == "HEADING":
            emit()
            subheading = block["text"].strip()
            pending_subheading = subheading
            continue
        prospective = sum(len(item["text"]) + 1 for item in pending) + len(block["text"])
        if pending and prospective > MAX_CHUNK_CHARS:
            emit()
            pending_subheading = subheading
        if not pending:
            pending_subheading = subheading
        pending.append(block)

    emit()

    # A block longer than the bound on its own is split on line boundaries rather
    # than silently exceeding it; OCR occasionally emits a whole column as one block.
    bounded: list[dict[str, Any]] = []
    for chunk in chunks:
        if chunk["char_count"] <= MAX_CHUNK_CHARS:
            bounded.append(chunk)
            continue
        for piece in _split_oversized(chunk["text"]):
            ordinal = len(bounded)
            text_sha256 = _sha256(piece)
            identity = f"{document_id}|{pdf_page}|{ordinal}|{text_sha256}"
            bounded.append({
                **chunk,
                "chunk_id": "TNC-" + _sha256(identity)[:24],
                "ordinal": ordinal,
                "text": piece,
                "text_sha256": text_sha256,
                "char_count": len(piece),
                "normalized_text_for_search": normalize_for_search(piece),
            })
    for ordinal, chunk in enumerate(bounded):
        chunk["ordinal"] = ordinal
    return bounded


def _split_oversized(text: str) -> list[str]:
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.split("\n"):
        if current and size + len(line) + 1 > MAX_CHUNK_CHARS:
            pieces.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        pieces.append("\n".join(current))
    return [piece for piece in pieces if piece.strip()]


# ---------------------------------------------------------------- page joins


def _load(root: Path, relative: str) -> Any:
    path = resolve_root_path(Path(root).resolve(), relative)
    if not path.is_file():
        raise TnIndexError(f"canonical artifact is unavailable: {relative}")
    return json.loads(path.read_text())


def resolve_page_nodes(root: Path) -> dict[int, dict[str, Any]]:
    """Resolve every PDF page to the deepest TOC node whose range contains it.

    Ties are broken deterministically: deepest level first, then the latest start
    page, then node id. Several topics share a printed page in this corpus, so a
    tie-break that is not stated is a tie-break that is not reproducible.
    """
    toc = _load(root, TOC_RELATIVE_PATH)
    titles = {node["node_id"]: node.get("title") for node in toc["nodes"]}
    parents = {node["node_id"]: node.get("parent_id") for node in toc["nodes"]}

    by_page: dict[int, list[dict[str, Any]]] = {}
    for node in toc["nodes"]:
        start, end = node.get("start_pdf_page"), node.get("end_pdf_page")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        for page in range(start, end + 1):
            by_page.setdefault(page, []).append(node)

    page_index = _load(root, PAGE_INDEX_RELATIVE_PATH)
    resolution: dict[int, dict[str, Any]] = {}
    for page in page_index["pages"]:
        pdf_page = page["pdf_page"]
        candidates = by_page.get(pdf_page, [])
        if not candidates:
            resolution[pdf_page] = {
                "tn_node_id": None, "chapter_code": None, "section_path": None
            }
            continue
        best = sorted(
            candidates,
            key=lambda node: (
                -int(node.get("level") or 0),
                -int(node.get("start_pdf_page") or 0),
                node["node_id"],
            ),
        )[0]
        path: list[str] = []
        cursor: str | None = best["node_id"]
        seen: set[str] = set()
        while cursor and cursor not in seen:
            seen.add(cursor)
            title = titles.get(cursor)
            if title:
                path.append(title)
            cursor = parents.get(cursor)
        resolution[pdf_page] = {
            "tn_node_id": best["node_id"],
            "chapter_code": best.get("chapter_code"),
            "section_path": " > ".join(reversed(path)),
        }
    return resolution


def _resolve_page_study_units(root: Path) -> dict[int, list[str]]:
    crosswalk = _load(root, SCOPE_RELATIVE_PATH)
    by_page: dict[int, list[str]] = {}
    for entry in crosswalk["entries"]:
        span = entry.get("pdf_page_range")
        if not (isinstance(span, list) and len(span) == 2):
            continue
        start, end = span
        if not (isinstance(start, int) and isinstance(end, int)):
            continue
        for page in range(start, end + 1):
            by_page.setdefault(page, []).append(entry["study_unit_id"])
    return {page: sorted(set(units)) for page, units in by_page.items()}


# --------------------------------------------------------------------- schema


SCHEMA = """
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    authority_role TEXT NOT NULL
);
CREATE TABLE pages (
    pdf_page INTEGER PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    tn_page_label TEXT,
    canonical_text_sha256 TEXT NOT NULL,
    ocr_quality_flags TEXT NOT NULL
);
CREATE TABLE chapters (
    chapter_code TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    chapter_title TEXT NOT NULL,
    start_pdf_page INTEGER NOT NULL,
    end_pdf_page INTEGER NOT NULL
);
CREATE TABLE sections (
    tn_node_id TEXT PRIMARY KEY,
    chapter_code TEXT,
    parent_id TEXT,
    level INTEGER,
    title TEXT NOT NULL,
    structural_type TEXT,
    start_pdf_page INTEGER,
    end_pdf_page INTEGER,
    confidence TEXT
);
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    chapter_code TEXT,
    tn_node_id TEXT,
    section_path TEXT,
    subheading TEXT,
    pdf_page INTEGER NOT NULL REFERENCES pages(pdf_page),
    tn_page_label TEXT,
    ordinal INTEGER NOT NULL,
    block_kinds TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    char_count INTEGER NOT NULL
);
CREATE INDEX chunks_by_page ON chunks(pdf_page, ordinal);
CREATE INDEX chunks_by_node ON chunks(tn_node_id);
CREATE TABLE chunk_text (
    chunk_id TEXT PRIMARY KEY REFERENCES chunks(chunk_id),
    text TEXT NOT NULL,
    normalized_text_for_search TEXT NOT NULL
);
CREATE TABLE study_units (
    study_unit_id TEXT PRIMARY KEY,
    chapter_code TEXT,
    study_unit_title TEXT NOT NULL,
    classification TEXT,
    scope_depth TEXT,
    tn_page_range TEXT,
    start_pdf_page INTEGER,
    end_pdf_page INTEGER
);
CREATE TABLE chunk_study_units (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
    study_unit_id TEXT NOT NULL REFERENCES study_units(study_unit_id),
    PRIMARY KEY (chunk_id, study_unit_id)
);
CREATE INDEX chunk_study_units_by_unit ON chunk_study_units(study_unit_id);
CREATE TABLE mcc_objectives (
    mcc_objective_id TEXT PRIMARY KEY,
    title TEXT
);
CREATE TABLE study_unit_objectives (
    study_unit_id TEXT NOT NULL REFERENCES study_units(study_unit_id),
    mcc_objective_id TEXT NOT NULL,
    PRIMARY KEY (study_unit_id, mcc_objective_id)
);
CREATE TABLE build_manifest (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

FTS_SCHEMA = f"""
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    normalized_text_for_search,
    content='',
    tokenize='{FTS_TOKENIZER}'
);
"""


def open_index(path: Path) -> sqlite3.Connection:
    """Open an existing index read-only-ish, failing closed if it is not one."""
    path = Path(path)
    if not path.is_file():
        raise TnIndexError(f"index has not been built: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = None
    try:
        connection.execute("SELECT count(*) FROM chunks").fetchone()
    except sqlite3.Error as exc:
        raise TnIndexError(f"index is unusable: {exc}") from exc
    return connection


def build_tn_index(
    root: Path, index_path: Path, *, page_limit: int | None = None
) -> dict[str, Any]:
    """Build the whole deterministic index from canonical local artifacts.

    Deterministic throughout: no model reads a page, no ordering depends on
    filesystem iteration order, and a rebuild reproduces every chunk id.
    """
    started = time.monotonic()
    root = Path(root).resolve()
    corpus = resolve_root_path(root, CORPUS_RELATIVE_PATH)
    if not corpus.is_dir():
        raise TnIndexError(f"Toronto Notes corpus is unavailable: {CORPUS_RELATIVE_PATH}")

    page_index = _load(root, PAGE_INDEX_RELATIVE_PATH)
    toc = _load(root, TOC_RELATIVE_PATH)
    crosswalk = _load(root, SCOPE_RELATIVE_PATH)
    node_resolution = resolve_page_nodes(root)
    page_study_units = _resolve_page_study_units(root)

    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        index_path.unlink()
    connection = sqlite3.connect(index_path)
    connection.executescript(SCHEMA)
    connection.executescript(FTS_SCHEMA)

    connection.execute(
        "INSERT INTO documents VALUES (?,?,?,?,?)",
        (DOCUMENT_ID, "Toronto Notes 2025", page_index["source_sha256"],
         page_index["page_count"], "TOPIC_DISCOVERY_SOURCE"),
    )

    chapters_directory = corpus / "chapters"
    for manifest_path in sorted(chapters_directory.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        pdf_pages = [page["pdf_page"] for page in manifest["pages"]]
        connection.execute(
            "INSERT INTO chapters VALUES (?,?,?,?,?)",
            (manifest["chapter_code"], DOCUMENT_ID, manifest["chapter_title"],
             min(pdf_pages), max(pdf_pages)),
        )

    connection.executemany(
        "INSERT INTO sections VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (node["node_id"], node.get("chapter_code"), node.get("parent_id"),
             node.get("level"), node.get("title") or "", node.get("structural_type"),
             node.get("start_pdf_page"), node.get("end_pdf_page"), node.get("confidence"))
            for node in sorted(toc["nodes"], key=lambda item: item["node_id"])
        ],
    )

    objectives: dict[str, str | None] = {}
    unit_objectives: set[tuple[str, str]] = set()
    for entry in sorted(crosswalk["entries"], key=lambda item: item["study_unit_id"]):
        span = entry.get("pdf_page_range") or [None, None]
        connection.execute(
            "INSERT INTO study_units VALUES (?,?,?,?,?,?,?,?)",
            (entry["study_unit_id"], entry.get("chapter_code"),
             entry.get("study_unit_title") or entry.get("title") or "",
             entry.get("classification"), entry.get("scope_depth"),
             entry.get("tn_page_range"),
             span[0] if isinstance(span, list) and len(span) == 2 else None,
             span[1] if isinstance(span, list) and len(span) == 2 else None),
        )
        for evidence in entry.get("mcc_evidence") or []:
            objective_id = evidence.get("mcc_id")
            if isinstance(objective_id, str) and objective_id:
                objectives.setdefault(objective_id, evidence.get("objective_title"))
                unit_objectives.add((entry["study_unit_id"], objective_id))
    connection.executemany(
        "INSERT INTO mcc_objectives VALUES (?,?)",
        [(objective_id, objectives[objective_id]) for objective_id in sorted(objectives)],
    )
    connection.executemany(
        "INSERT INTO study_unit_objectives VALUES (?,?)", sorted(unit_objectives)
    )

    pages = sorted(page_index["pages"], key=lambda page: page["pdf_page"])
    if page_limit is not None:
        pages = pages[:page_limit]

    total_chunks = 0
    for page in pages:
        pdf_page = page["pdf_page"]
        document = json.loads((corpus / "ocr" / page["page_path"]).read_text())
        node = node_resolution.get(pdf_page) or {}
        chunks = chunk_page(
            document,
            document_id=DOCUMENT_ID,
            chapter_code=node.get("chapter_code"),
            tn_node_id=node.get("tn_node_id"),
            section_path=node.get("section_path"),
        )
        label = chunks[0]["tn_page_label"] if chunks else None
        connection.execute(
            "INSERT INTO pages VALUES (?,?,?,?,?)",
            (pdf_page, DOCUMENT_ID, label, page["canonical_text_sha256"],
             ",".join(page.get("ocr_quality_flags") or [])),
        )
        units = page_study_units.get(pdf_page, [])
        for chunk in chunks:
            connection.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (chunk["chunk_id"], chunk["document_id"], chunk["chapter_code"],
                 chunk["tn_node_id"], chunk["section_path"], chunk["subheading"],
                 chunk["pdf_page"], chunk["tn_page_label"], chunk["ordinal"],
                 chunk["block_kinds"], chunk["text_sha256"], chunk["char_count"]),
            )
            rowid = connection.execute(
                "SELECT rowid FROM chunks WHERE chunk_id = ?", (chunk["chunk_id"],)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO chunk_text VALUES (?,?,?)",
                (chunk["chunk_id"], chunk["text"], chunk["normalized_text_for_search"]),
            )
            connection.execute(
                "INSERT INTO chunks_fts(rowid, normalized_text_for_search) VALUES (?,?)",
                (rowid, chunk["normalized_text_for_search"]),
            )
            for unit in units:
                connection.execute(
                    "INSERT OR IGNORE INTO chunk_study_units VALUES (?,?)",
                    (chunk["chunk_id"], unit),
                )
            total_chunks += 1

    elapsed = time.monotonic() - started
    manifest = {
        "document_id": DOCUMENT_ID,
        "source_sha256": page_index["source_sha256"],
        "pages_indexed": str(len(pages)),
        "chunks_indexed": str(total_chunks),
        "max_chunk_chars": str(MAX_CHUNK_CHARS),
        "fts_tokenizer": FTS_TOKENIZER,
        "build_seconds": f"{elapsed:.3f}",
    }
    connection.executemany(
        "INSERT INTO build_manifest VALUES (?,?)", sorted(manifest.items())
    )
    connection.commit()
    connection.close()
    manifest["index_bytes"] = str(index_path.stat().st_size)
    return manifest


def write_index_build_manifest(root: Path, index_path: Path) -> dict[str, Any]:
    """Write the small tracked manifest describing a built index.

    Counts, hashes, tokenizer settings and size distributions only. No Toronto
    Notes prose reaches this file, which is what makes it committable while the
    database it describes stays under the gitignored derived/ tree.
    """
    import statistics

    from .jsonio import write_json_atomic

    connection = open_index(index_path)
    manifest = dict(connection.execute("SELECT key, value FROM build_manifest"))
    sizes = sorted(row[0] for row in connection.execute("SELECT char_count FROM chunks"))
    scalar = lambda sql: connection.execute(sql).fetchone()[0]
    document = {
        "schema_version": "1.0",
        "scope": "TN_DETERMINISTIC_INDEX_BUILD_MANIFEST",
        "document_id": manifest["document_id"],
        "source_sha256": manifest["source_sha256"],
        "authority_role": "TOPIC_DISCOVERY_SOURCE",
        "index_relative_path": INDEX_RELATIVE_PATH,
        "index_is_a_tracked_artifact": False,
        "rebuild_command": "qbank build-tn-index",
        "fts_tokenizer": manifest["fts_tokenizer"],
        "tokenizer_rationale": (
            "porter folds -itis/-osis/-aemia morphology, which medical recall needs; "
            "remove_diacritics 2 folds OCR diacritic noise. porter over-stems some drug "
            "names, which is accepted because admissibility is carried by the anchor "
            "floor and the graph, never by BM25 rank."
        ),
        "max_chunk_chars": int(manifest["max_chunk_chars"]),
        "counts": {
            "pages_indexed": int(manifest["pages_indexed"]),
            "chunks_indexed": int(manifest["chunks_indexed"]),
            "chapters": scalar("SELECT count(*) FROM chapters"),
            "sections": scalar("SELECT count(*) FROM sections"),
            "study_units": scalar("SELECT count(*) FROM study_units"),
            "mcc_objectives": scalar("SELECT count(*) FROM mcc_objectives"),
            "study_unit_objective_links": scalar("SELECT count(*) FROM study_unit_objectives"),
            "chunk_study_unit_links": scalar("SELECT count(*) FROM chunk_study_units"),
            "pages_without_chunks": scalar(
                "SELECT count(*) FROM pages p WHERE NOT EXISTS "
                "(SELECT 1 FROM chunks c WHERE c.pdf_page = p.pdf_page)"
            ),
        },
        "chunk_size_chars": {
            "median": int(statistics.median(sizes)),
            "p95": sizes[int(len(sizes) * 0.95)],
            "max": max(sizes),
            "min": min(sizes),
        },
        "build_seconds": float(manifest["build_seconds"]),
        "index_bytes": index_path.stat().st_size,
    }
    connection.close()
    write_json_atomic(resolve_root_path(Path(root).resolve(), BUILD_MANIFEST_RELATIVE_PATH), document)
    return document
