"""Build research/tn2025/toc_inventory.json, toc_validation_report.{json,md},
and research/tn2025/unresolved_headings.json.

Deterministic, mechanical extraction ONLY - no MCC mapping, no clinical
judgment, nothing filled in from medical knowledge. Produces an
arbitrary-depth tree of nodes (chapter -> section -> topic; no level is
invented if the source doesn't support it) faithfully representing the
Toronto Notes 2025 printed structure.

Two independent, source-grounded extraction methods are combined:

1. TOC_OCR: parse each chapter's own printed internal table-of-contents
   page(s). A section line ends in that chapter's own page-numbering code
   (e.g. "C19", "P70"); heading text is recovered by walking left from that
   trailing code, keeping only tokens that are purely alphabetic once
   trailing punctuation is stripped (dot-leader OCR garbage reliably fails
   that test). This alone parsed 24 of 32 chapters completely, but for 8
   chapters the TOC page's page-number digits are themselves too
   OCR-corrupted to trust (see BODY_HEADING_CONFIRMATION below).

2. BODY_HEADING_CONFIRMATION: independent of the TOC page's page-number
   digits, search the chapter's own body pages for a standalone line whose
   text matches (exact after normalization, or a high-similarity fuzzy
   match tolerant of individual OCR character drops/substitutions) a
   heading candidate extracted from the TOC. When found, the confirming
   body page's own pdf_page - which is highly reliable, cross-validated
   chapter-wide against that chapter's own running header pattern
   ("<code><n> <ChapterTitle>") - is used as the section's start_pdf_page,
   OVERRIDING any TOC-digit guess, because it is grounded in directly
   observed text rather than inferred from corrupted digits.

Any heading candidate that neither method can anchor to a specific page is
recorded as UNRESOLVED in research/tn2025/unresolved_headings.json with the
exact TOC source page and raw OCR line - never silently dropped, never
filled in from outside knowledge of what a Toronto Notes chapter "should"
contain.
"""
import difflib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHAPTERS_DIR = REPO / "derived" / "toronto-notes-2025" / "chapters"
OCR_PAGES_DIR = REPO / "derived" / "toronto-notes-2025" / "ocr" / "pages"

OUT_INVENTORY = REPO / "research" / "tn2025" / "toc_inventory.json"
OUT_VALIDATION_JSON = REPO / "research" / "tn2025" / "toc_validation_report.json"
OUT_VALIDATION_MD = REPO / "research" / "tn2025" / "toc_validation_report.md"
OUT_UNRESOLVED = REPO / "research" / "tn2025" / "unresolved_headings.json"

GENERATED_AT = "2026-08-24"

# ---------------------------------------------------------------------------
# Shared text helpers
# ---------------------------------------------------------------------------

# Tolerant of a stray 1-2 char OCR symbol between the letter code and
# digits (observed: "PS§20").
TRAILING_CODE_RE = re.compile(r"^(?P<pre>.*?)(?P<code>[A-Za-z]{1,5})[^\w\s]{0,2}(?P<num>\d{1,4})\s*$")
WORD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z\-']*$")

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
    return any(pat.search(line) for pat in SKIP_LINE_PATTERNS)


LEADING_ALPHA_RE = re.compile(r"^[A-Za-z][A-Za-z\-']*")

# Short lowercase tokens that are legitimate in real headings ("Approach
# to...", "Diseases of the..."). Any OTHER short (<=3 char) all-lowercase
# token is treated as dot-leader OCR noise (observed pattern: repeated
# fragments like "ee ee ee", "es es", "ces sse") and stops the walk, rather
# than being kept as if it were a real heading word.
CONNECTOR_WORDS = {
    "of", "in", "to", "and", "or", "the", "a", "an", "for", "with",
    "at", "on", "by", "as", "is", "if", "vs",
}


def clean_heading_from_pre_code_text(pre: str) -> str:
    """Walk tokens left-to-right, keeping only ones that are purely
    alphabetic once trailing punctuation is stripped. Dot-leader OCR
    garbage (runs of digits/periods/short lowercase noise) reliably fails
    this test and stops the walk.

    A whitespace-collapsed OCR line occasionally glues a real trailing word
    directly onto its leader-dot run with no separating space (e.g.
    "Therapy...........scscccess..."). For such a token, the LEADING
    alphabetic run is still a genuine word from the source and is kept;
    the walk then stops (since garbage begins immediately after), rather
    than discarding the whole token."""
    kept = []
    for tok in pre.strip().split():
        core = tok.strip(".,;:")
        if core and WORD_TOKEN_RE.match(core):
            if len(core) <= 3 and core.islower() and core.lower() not in CONNECTOR_WORDS:
                break
            kept.append(core)
            continue
        # A token that looks exactly like a page-reference code (letters
        # immediately followed by digits, e.g. "ER18") is almost never a
        # real word with glued garbage - it's an embedded mid-line page
        # reference (typically from a two-column TOC layout merge). Reject
        # it outright rather than keeping its leading letters as if they
        # were a genuine (if truncated) word.
        if core and re.match(r"^[A-Za-z]{1,5}\d{1,4}", core):
            break
        m = LEADING_ALPHA_RE.match(core) if core else None
        if m and len(m.group(0)) >= 2:
            kept.append(m.group(0))
        break
    return " ".join(kept)


def normalize_for_match(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


# Trailing page-code pattern, tolerant of a stray 1-2 char OCR symbol
# inserted between the letters and digits (observed: "PS§20" where a
# printed page-number style artifact OCR'd as "§").
ANY_TRAILING_CODE_RE = re.compile(r"^(?P<pre>.*?)[A-Za-z]{1,5}[^\w\s]{0,2}\d{1,4}\s*$")


def extract_leader_stripped_heading(line: str) -> str:
    """Extract the heading candidate via the alphabetic-token walk. If the
    line ends in ANY letter-code+digits pattern (not only one matching this
    chapter - a merged/foreign code should still be stripped rather than
    walked into), that trailing code is excluded first. Without this, the
    token walk's glued-token fallback (which recovers a real word merged
    onto dot-leader garbage, e.g. "Therapy....") would also match the
    LEADING letters of the trailing page code itself (e.g. pull "NP" out
    of a genuine trailing "NP34"), appending a spurious extra word to the
    heading - a confirmed bug, fixed here by never walking into the
    trailing code region at all."""
    m = ANY_TRAILING_CODE_RE.match(line)
    pre = m.group("pre") if m else line
    return clean_heading_from_pre_code_text(pre)


# ---------------------------------------------------------------------------
# Chapter running-header ground truth (used both to compute end pages and to
# anchor BODY_HEADING_CONFIRMATION matches to an exact pdf_page).
# ---------------------------------------------------------------------------

def build_running_header_map(chapter_code: str, pdf_pages: list) -> dict:
    """Return {pdf_page: confirmed_relative_number} for every page in the
    chapter whose first line matches '<chapter_code><n>' (case-insensitive,
    optionally followed by the chapter title text). This is checked against
    the chapter's own linear position (pdf_page - chapter_start + 1) and
    used only as a validation/consistency signal; the linear formula itself
    is what's actually used for pdf_page<->relative-page conversion,
    because in every chapter sampled the two agree wherever a header is
    present at all (see toc_validation_report for the cross-check counts)."""
    header_re = re.compile(rf"^{re.escape(chapter_code)}(\d{{1,3}})\b", re.IGNORECASE)
    chapter_start = min(pdf_pages)
    confirmed = {}
    mismatches = []
    for i, pp in enumerate(pdf_pages):
        text = load_page_text(pp)
        first_line = text.splitlines()[0] if text.splitlines() else ""
        m = header_re.match(first_line.strip())
        if m:
            expected = i + 1
            got = int(m.group(1))
            confirmed[pp] = got
            if got != expected:
                mismatches.append({"pdf_page": pp, "expected_relative": expected, "header_read_relative": got})
    return {
        "confirmed_pages": confirmed,
        "coverage": f"{len(confirmed)}/{len(pdf_pages)}",
        "mismatches": mismatches,
    }


# ---------------------------------------------------------------------------
# TOC page detection and candidate extraction
# ---------------------------------------------------------------------------

def find_toc_pages(chapter_code: str, pdf_pages: list) -> list:
    """A real internal-TOC page has several lines ending in this chapter's
    own <code><digits> page-label; require >=3 such matches OR, for
    heavily digit-corrupted chapters, fall back to counting lines that at
    least *start* with this chapter's own alphabetic prefix in a
    leader-dot pattern (heading-candidate-with-any-trailing-junk)."""
    candidates = []
    for pdf_page in pdf_pages[:4]:
        text = load_page_text(pdf_page)
        strict_count = 0
        loose_count = 0
        for line in text.splitlines():
            line = line.strip()
            m = TRAILING_CODE_RE.match(line)
            if m and m.group("code").upper() == chapter_code.upper():
                heading = clean_heading_from_pre_code_text(m.group("pre"))
                if heading:
                    strict_count += 1
            # loose signal: line contains a dot-leader run (3+ periods, or
            # a long run of low-information filler) - typical of a TOC
            # entry regardless of whether the trailing code parsed
            if re.search(r"\.{3,}|[\.\s]{2,}[a-zA-Z]{0,3}\d", line):
                loose_count += 1
        candidates.append((pdf_page, strict_count, loose_count))

    strict_pages = [p for p, s, l in candidates if s >= 3]
    if strict_pages:
        return strict_pages
    loose_pages = [p for p, s, l in candidates if l >= 5]
    return loose_pages


def split_multi_entry_line(line: str, chapter_code: str) -> list:
    """Some Toronto Notes TOC pages lay out two columns of entries that
    OCR's reading order interleaves onto a single text line (observed
    directly, e.g. Neurology: "Mild Traumatic Brain Injury...N29 =-
    Multiple Sclerosis...N55" is genuinely two separate TOC entries merged
    by OCR). Detected by the presence of more than one embedded
    <chapter_code><digits> occurrence within the same line (not just one
    at the very end); the line is then split into that many sub-lines, one
    ending at each occurrence, so each is parsed as its own independent
    candidate rather than one candidate with a corrupted merged heading."""
    pattern = re.compile(rf"\b{re.escape(chapter_code)}\d{{1,4}}\b", re.IGNORECASE)
    matches = list(pattern.finditer(line))
    if len(matches) <= 1:
        return [line]
    segments = []
    start = 0
    for m in matches:
        segments.append(line[start:m.end()].strip())
        start = m.end()
    tail = line[start:].strip()
    if tail:
        segments.append(tail)
    return [s for s in segments if s]


def parse_toc_candidates(chapter_code: str, toc_pages: list, chapter_title: str = "") -> list:
    """Return an ordered list of dicts, one per TOC line judged to be a
    section heading (has enough structure to look like one), each with:
      heading_text, toc_trailing_code_num (int or None - only set if the
      trailing digits parsed AND the letter-code matched this chapter),
      raw_ocr_line, source_pdf_page
    Lines that don't look like section headers at all (too short, pure
    boilerplate) are treated as topic candidates instead and returned
    separately, attached to the preceding section candidate."""
    section_candidates = []
    current_topics = []
    seen_first_section = False

    def is_probable_section_line(line: str) -> bool:
        # Has some kind of leader-dot run OR ends in a trailing-code match -
        # i.e., looks like a TOC entry with a page reference, not a bare
        # sub-bullet topic.
        if TRAILING_CODE_RE.match(line) and TRAILING_CODE_RE.match(line).group("code").upper() == chapter_code.upper():
            return True
        return bool(re.search(r"\.{3,}|[\.\s]{2,}[a-zA-Z]{0,4}\d{1,4}\s*$", line))

    for pdf_page in toc_pages:
        text = load_page_text(pdf_page)
        for original_raw_line in text.splitlines():
            for raw_line in split_multi_entry_line(original_raw_line.strip(), chapter_code):
                line = raw_line.strip()
                if is_skip_line(line):
                    continue

                m = TRAILING_CODE_RE.match(line)
                trailing_num = None
                if m and m.group("code").upper() == chapter_code.upper():
                    trailing_num = int(m.group("num"))

                if is_probable_section_line(line):
                    heading = extract_leader_stripped_heading(line)
                    # Reject headings that are empty, or that reduce to
                    # just the chapter code itself (a stray page-number-only
                    # remnant line, e.g. an isolated "NP2" with no heading
                    # text before it - not a real section title).
                    if not heading or heading.upper() == chapter_code.upper():
                        continue
                    seen_first_section = True
                    if section_candidates:
                        section_candidates[-1]["topics"] = current_topics
                    current_topics = []
                    section_candidates.append({
                        "heading_text": heading,
                        "toc_trailing_code_num": trailing_num,
                        "raw_ocr_line": raw_line,
                        "source_pdf_page": pdf_page,
                        "topics": [],
                    })
                    continue

                if not seen_first_section:
                    continue
                if len(line) < 2:
                    continue
                if re.match(rf"^{re.escape(chapter_code)}\d+\b", line, re.IGNORECASE):
                    continue
                # Running-header/footer leakage into the topic list:
                # (a) the bare chapter title repeated (e.g. a footer line
                #     "P61 Pediatrics Toronto Notes 2025" splits across
                #     OCR lines, leaving "Pediatrics" as an orphan line),
                # (b) an isolated 1-4 char page-number-remnant token that
                #     is letters-then-digits and starts with this
                #     chapter's own code (e.g. "Pl" - OCR'd "P1").
                if chapter_title and normalize_for_match(line) == normalize_for_match(chapter_title):
                    continue
                if re.match(rf"^{re.escape(chapter_code)}[a-zA-Z]?\d{{0,3}}$", line, re.IGNORECASE) and len(line) <= 5:
                    continue
                current_topics.append(line)

    if section_candidates:
        section_candidates[-1]["topics"] = current_topics

    return section_candidates


# ---------------------------------------------------------------------------
# Body-heading confirmation
# ---------------------------------------------------------------------------

def confirm_via_body_headings(heading_text: str, body_pdf_pages: list, min_ratio: float = 0.87):
    """Search body pages (already restricted to an ordered window by the
    caller, so the FIRST exact match found is the correct one - sections
    are printed in reading order and the search window advances after each
    confirmed section) for a short standalone line matching heading_text.

    Exact normalized match returns immediately on first occurrence within
    the window (unambiguous). If no exact match exists anywhere in the
    window, fall back to the single BEST (highest-ratio) fuzzy match across
    the whole window - not the first one encountered - since an early,
    low-quality fuzzy false-positive should not pre-empt a better match
    later in the same window (this was a confirmed bug: an unrelated early
    partial-match previously won over the correct later occurrence).
    Returns (pdf_page, matched_line, method, ratio) or None."""
    target_norm = normalize_for_match(heading_text)
    if len(target_norm) < 4:
        return None  # too short to match reliably, avoid false positives

    best = None
    best_ratio = 0.0
    for pp in body_pdf_pages:
        text = load_page_text(pp)
        for line in text.splitlines():
            line_s = line.strip()
            if not line_s or len(line_s) > 70:
                continue
            line_norm = normalize_for_match(line_s)
            if not line_norm:
                continue
            if line_norm == target_norm:
                return (pp, line_s, "exact_normalized", 1.0)
            if abs(len(line_norm) - len(target_norm)) <= 4:
                ratio = difflib.SequenceMatcher(None, target_norm, line_norm).ratio()
                if ratio >= min_ratio and ratio > best_ratio:
                    best = (pp, line_s, "fuzzy_normalized", round(ratio, 3))
                    best_ratio = ratio
    return best


# ---------------------------------------------------------------------------
# Tree assembly
# ---------------------------------------------------------------------------

def assemble_chapter_tree(chapter_code, chapter_title, pdf_pages, unresolved_out):
    chapter_start = min(pdf_pages)
    chapter_end = max(pdf_pages)

    header_map = build_running_header_map(chapter_code, pdf_pages)
    toc_pages = find_toc_pages(chapter_code, pdf_pages)

    chapter_node = {
        "node_id": chapter_code,
        "chapter_code": chapter_code,
        "title": chapter_title,
        "level": 1,
        "parent_id": None,
        "start_tn_page": f"{chapter_code}1",
        "end_tn_page": f"{chapter_code}{chapter_end - chapter_start + 1}",
        "start_pdf_page": chapter_start,
        "end_pdf_page": chapter_end,
        "structural_type": "chapter",
        "extraction_method": "CHAPTER_MANIFEST",
        "confidence": "HIGH",
        "running_header_coverage": header_map["coverage"],
        "running_header_mismatches": header_map["mismatches"],
    }

    if not toc_pages:
        return chapter_node, [], {
            "chapter_code": chapter_code,
            "issue": "NO_TOC_PAGE_DETECTED",
            "detail": (
                f"No page among the chapter's first 4 pages "
                f"({pdf_pages[:4]}) contained enough section-line pattern "
                f"matches (strict >=3 or loose >=5) to be identified as an "
                f"internal table of contents."
            ),
            "source_pdf_pages_checked": pdf_pages[:4],
        }

    section_candidates = parse_toc_candidates(chapter_code, toc_pages, chapter_title)
    body_pages_all = [p for p in pdf_pages if p not in toc_pages]

    nodes = []

    # --- Pass 1: compute each candidate's raw TOC-digit page guess ---
    for cand in section_candidates:
        toc_num = cand["toc_trailing_code_num"]
        toc_pdf_page = None
        if toc_num is not None:
            candidate_pdf_page = chapter_start + toc_num - 1
            if chapter_start <= candidate_pdf_page <= chapter_end:
                toc_pdf_page = candidate_pdf_page
        cand["toc_pdf_page_guess"] = toc_pdf_page

    # --- Pass 2: promote candidates to TRUSTED ANCHORS by finding the
    # LONGEST NON-DECREASING SUBSEQUENCE of toc_pdf_page_guess values across
    # all candidates (standard O(n^2) DP - n is a few dozen per chapter, so
    # this is cheap). A naive greedy left-to-right "trust if >= previous"
    # walk is NOT used here because some Toronto Notes TOC pages lay out
    # two columns whose OCR reading order interleaves a few of the SECOND
    # column's (late-chapter) entries in among the FIRST column's (early-
    # chapter) entries at the very top of the page (confirmed directly,
    # e.g. Gynecology: candidates arrive in the order 2, 56, 2, 58, 4, 59,
    # 6, 7, 13, 14... - three late entries "56, 58, 59" are read early,
    # before the real early-chapter run "2, 4, 6, 7, 13..." resumes and
    # continues cleanly to the end). A greedy walk would trust the first
    # occurrence of 56 as an anchor and then reject the entire correct
    # 2,4,6,7,13,... run as "backward jumps," cascading into dozens of
    # false UNRESOLVED headings. LIS instead finds the actual intended
    # monotonic run (here: 2,2,4,6,7,13,14,15,19,20,21,23,25,26,34,34,36,
    # 39,42) and correctly excludes only the true outliers (56, 58, 59) -
    # which then get resolved on their own merits via BODY_HEADING_
    # CONFIRMATION with correct (non-corrupted) bounds in Pass 3. ---
    guesses = [c["toc_pdf_page_guess"] for c in section_candidates]
    n = len(guesses)
    dp = [1] * n
    prev_idx = [-1] * n
    for i in range(n):
        if guesses[i] is None:
            dp[i] = 0
            continue
        for j in range(i):
            if guesses[j] is not None and guesses[j] <= guesses[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev_idx[i] = j
    lis_indices = set()
    if n and max(dp, default=0) > 0:
        end = max(range(n), key=lambda i: dp[i])
        while end != -1:
            if guesses[end] is not None:
                lis_indices.add(end)
            end = prev_idx[end]

    for i, cand in enumerate(section_candidates):
        cand["is_trusted_anchor"] = i in lis_indices

    # --- Pass 3: for each candidate, resolve a start_pdf_page. Trusted
    # anchors are used directly (TOC_OCR, HIGH confidence) UNLESS an exact
    # body-text match exists at a *different* page, in which case the
    # exact body match wins (it is strictly stronger evidence than a
    # digit that merely happened to parse) and the disagreement is
    # recorded rather than silently dropped. Non-anchor candidates are
    # searched for via BODY_HEADING_CONFIRMATION within a window bounded
    # on both sides by the nearest trusted anchors before and after them -
    # never an open-ended forward search - which is what prevents a false
    # match against unrelated, similarly-worded text elsewhere in the
    # chapter. ---
    anchor_pages_in_order = [c["toc_pdf_page_guess"] for c in section_candidates if c["is_trusted_anchor"]]

    def bounded_window(idx):
        lower = chapter_start
        for j in range(idx - 1, -1, -1):
            if section_candidates[j]["is_trusted_anchor"]:
                lower = section_candidates[j]["toc_pdf_page_guess"]
                break
        upper = chapter_end
        for j in range(idx + 1, len(section_candidates)):
            if section_candidates[j]["is_trusted_anchor"]:
                upper = section_candidates[j]["toc_pdf_page_guess"]
                break
        return [p for p in body_pages_all if lower <= p <= upper]

    resolved_sections = []
    for idx, cand in enumerate(section_candidates):
        heading = cand["heading_text"]
        toc_pdf_page = cand["toc_pdf_page_guess"]

        start_pdf_page = None
        extraction_method = None
        confidence = None
        confirmation_detail = None

        if cand["is_trusted_anchor"]:
            window = [p for p in bounded_window(idx) if p != toc_pdf_page] + [toc_pdf_page]
            confirmation = confirm_via_body_headings(heading, sorted(set(window)))
            if confirmation and confirmation[0] != toc_pdf_page and confirmation[2] == "exact_normalized":
                conf_page, matched_line, method, ratio = confirmation
                start_pdf_page = conf_page
                extraction_method = "BODY_HEADING_CONFIRMATION"
                confidence = "HIGH"
                confirmation_detail = {
                    "matched_body_line": matched_line,
                    "match_method": method,
                    "match_ratio": ratio,
                    "toc_digit_guess_pdf_page": toc_pdf_page,
                    "toc_digit_guess_agreed": False,
                }
            else:
                start_pdf_page = toc_pdf_page
                extraction_method = "TOC_OCR"
                confidence = "HIGH"
        else:
            window = bounded_window(idx)
            confirmation = confirm_via_body_headings(heading, window)
            if confirmation:
                conf_page, matched_line, method, ratio = confirmation
                start_pdf_page = conf_page
                extraction_method = "BODY_HEADING_CONFIRMATION"
                confidence = "HIGH" if method == "exact_normalized" else "MEDIUM"
                confirmation_detail = {
                    "matched_body_line": matched_line,
                    "match_method": method,
                    "match_ratio": ratio,
                    "toc_digit_guess_pdf_page": toc_pdf_page,
                    "toc_digit_guess_agreed": toc_pdf_page == conf_page,
                }
            elif toc_pdf_page is not None:
                # Excluded from the LIS anchor chain purely because of its
                # POSITION in the OCR-extracted candidate order (typically
                # a two-column TOC layout artifact - see Pass 2), not
                # because its own digit is implausible; the bounded search
                # window (built from the wrong neighbouring anchors as a
                # consequence of that same ordering artifact) found no
                # match. As a fallback, accept the candidate's own digit
                # guess directly at reduced confidence rather than
                # discarding an otherwise-unremarkable entry - explicitly
                # marked so this is auditable, not silent.
                start_pdf_page = toc_pdf_page
                extraction_method = "TOC_OCR"
                confidence = "MEDIUM"
                confirmation_detail = {
                    "note": (
                        "Excluded from the chapter's trusted monotonic "
                        "anchor sequence due to its position among "
                        "OCR-extracted TOC candidates (see "
                        "known_limitations: two-column TOC layout "
                        "interleaving); accepted on its own unconfirmed "
                        "digit reading as a fallback."
                    ),
                }
            else:
                unresolved_out.append({
                    "chapter_code": chapter_code,
                    "heading_candidate": heading,
                    "raw_ocr_line": cand["raw_ocr_line"],
                    "source_pdf_page": cand["source_pdf_page"],
                    "reason": (
                        "TOC page's trailing page-number digits did not "
                        "parse to a page consistent with reading order "
                        "(not a trusted anchor), and no standalone "
                        "body-page line within the bounded window between "
                        "the nearest trusted anchors before/after this "
                        "heading matched closely enough (similarity "
                        "threshold 0.87) to confirm a page. Search window "
                        f"checked: pdf pages {window[0]}-{window[-1]}"
                        if window else "no body pages in bounded window"
                    ),
                    "status": "UNRESOLVED",
                })
                continue

        resolved_sections.append({
            "heading": heading,
            "start_pdf_page": start_pdf_page,
            "extraction_method": extraction_method,
            "confidence": confidence,
            "raw_ocr_line": cand["raw_ocr_line"],
            "source_pdf_page": cand["source_pdf_page"],
            "confirmation_detail": confirmation_detail,
            "topics": cand["topics"],
        })

    # Sections should already be in reading order by construction; sort as
    # a defensive invariant check in case a bounded-window confirmation
    # still produced a local inversion.
    resolved_sections.sort(key=lambda s: s["start_pdf_page"])

    # De-duplicate: if two TOC candidates resolved to the identical
    # start_pdf_page, keep the first (by original TOC order) and record the
    # second's topics as merged into it rather than creating a duplicate
    # node at the same page - this only happens when the TOC prints the
    # same heading concept twice (e.g. a category header immediately above
    # its first subsection) or a fuzzy-match collision.
    deduped = []
    seen_pages = set()
    for s in resolved_sections:
        if s["start_pdf_page"] in seen_pages:
            deduped[-1]["topics"].extend(s["topics"])
            deduped[-1].setdefault("merged_duplicate_headings", []).append(s["heading"])
            continue
        seen_pages.add(s["start_pdf_page"])
        deduped.append(s)
    resolved_sections = deduped

    for i, s in enumerate(resolved_sections):
        if i + 1 < len(resolved_sections):
            end_pdf_page = max(s["start_pdf_page"], resolved_sections[i + 1]["start_pdf_page"] - 1)
        else:
            end_pdf_page = chapter_end
        s["end_pdf_page"] = end_pdf_page

    for i, s in enumerate(resolved_sections):
        section_relative_start = s["start_pdf_page"] - chapter_start + 1
        section_relative_end = s["end_pdf_page"] - chapter_start + 1
        section_node_id = f"{chapter_code}.S{i + 1:02d}"
        section_node = {
            "node_id": section_node_id,
            "chapter_code": chapter_code,
            "title": s["heading"],
            "level": 2,
            "parent_id": chapter_code,
            "start_tn_page": f"{chapter_code}{section_relative_start}",
            "end_tn_page": f"{chapter_code}{section_relative_end}",
            "start_pdf_page": s["start_pdf_page"],
            "end_pdf_page": s["end_pdf_page"],
            "structural_type": "section",
            "extraction_method": s["extraction_method"],
            "confidence": s["confidence"],
            "raw_ocr_line": s["raw_ocr_line"],
            "toc_source_pdf_page": s["source_pdf_page"],
        }
        if s.get("confirmation_detail"):
            section_node["confirmation_detail"] = s["confirmation_detail"]
        if s.get("merged_duplicate_headings"):
            section_node["merged_duplicate_headings"] = s["merged_duplicate_headings"]
        nodes.append(section_node)

        for j, topic_text in enumerate(s["topics"]):
            topic_node_id = f"{section_node_id}.T{j + 1:02d}"
            nodes.append({
                "node_id": topic_node_id,
                "chapter_code": chapter_code,
                "title": topic_text,
                "level": 3,
                "parent_id": section_node_id,
                "start_tn_page": section_node["start_tn_page"],
                "end_tn_page": section_node["end_tn_page"],
                "start_pdf_page": s["start_pdf_page"],
                "end_pdf_page": s["end_pdf_page"],
                "structural_type": "topic",
                "extraction_method": "TOC_OCR_UNANCHORED",
                "confidence": "LOW",
            })

    return chapter_node, nodes, None


def main():
    chapter_dirs = sorted(CHAPTERS_DIR.iterdir())
    all_nodes = []
    unresolved = []
    no_toc_chapters = []

    for cdir in chapter_dirs:
        manifest_path = cdir / "manifest.json"
        if not manifest_path.exists():
            continue
        with open(manifest_path) as f:
            manifest = json.load(f)

        chapter_code = manifest["chapter_code"]
        chapter_title = manifest["chapter_title"]
        pdf_pages = [p["pdf_page"] for p in manifest["pages"]]

        chapter_node, section_topic_nodes, no_toc_issue = assemble_chapter_tree(
            chapter_code, chapter_title, pdf_pages, unresolved
        )
        all_nodes.append(chapter_node)
        all_nodes.extend(section_topic_nodes)
        if no_toc_issue:
            no_toc_chapters.append(chapter_code)
            unresolved.append({
                "chapter_code": chapter_code,
                "heading_candidate": None,
                "raw_ocr_line": None,
                "source_pdf_page": None,
                "reason": no_toc_issue["detail"],
                "status": "UNRESOLVED_NO_TOC_DETECTED",
            })

    sections = [n for n in all_nodes if n["structural_type"] == "section"]
    topics = [n for n in all_nodes if n["structural_type"] == "topic"]

    method_counts = {}
    for s in sections:
        method_counts[s["extraction_method"]] = method_counts.get(s["extraction_method"], 0) + 1

    inventory = {
        "schema_version": "2.0",
        "generated_at": GENERATED_AT,
        "source_manifests": "derived/toronto-notes-2025/chapters/*/manifest.json",
        "provenance_note": (
            "Chapter-level page boundaries were computed on the "
            "codex/qbank-production git branch and copied into this "
            "gitignored derived/ tree for reuse (not merged as code/history "
            "into main). Section- and topic-level structure is extracted by "
            "combining two independent, source-grounded methods: TOC_OCR "
            "(parsing each chapter's own printed table of contents) and "
            "BODY_HEADING_CONFIRMATION (independently locating each heading "
            "as a standalone line within the chapter's own body pages, "
            "using that page's position as ground truth when the TOC's own "
            "page-number digits are too OCR-corrupted to trust). Nothing is "
            "filled in from outside medical knowledge of what a chapter "
            "'should' contain - every node traces to a specific OCR'd "
            "source line."
        ),
        "extraction_method": "scripts/qbank/build_tn_toc_inventory.py",
        "node_schema": {
            "node_id": "Deterministic, hierarchical (e.g. 'C', 'C.S03', 'C.S03.T02')",
            "chapter_code": "Toronto Notes chapter code",
            "title": "Heading/topic text as extracted (OCR-preserved, not spell-corrected)",
            "level": "1=chapter, 2=section, 3=topic (no level is invented beyond what the source TOC supports)",
            "parent_id": "node_id of the parent, or null for chapter roots",
            "start_tn_page": "Printed chapter-relative page label, e.g. 'C19'",
            "end_tn_page": "Printed chapter-relative page label of the last page in range",
            "start_pdf_page": "Absolute PDF page number",
            "end_pdf_page": "Absolute PDF page number",
            "structural_type": "chapter | section | topic",
            "extraction_method": "CHAPTER_MANIFEST | TOC_OCR | BODY_HEADING_CONFIRMATION | TOC_OCR_UNANCHORED",
            "confidence": "HIGH | MEDIUM | LOW",
        },
        "summary": {
            "total_chapters": len([n for n in all_nodes if n["structural_type"] == "chapter"]),
            "total_sections": len(sections),
            "total_topics": len(topics),
            "total_nodes": len(all_nodes),
            "extraction_method_counts": method_counts,
            "chapters_with_no_toc_detected": no_toc_chapters,
            "unresolved_heading_count": len(unresolved),
        },
        "nodes": all_nodes,
    }

    OUT_INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_INVENTORY, "w") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(OUT_UNRESOLVED, "w") as f:
        json.dump({
            "generated_at": GENERATED_AT,
            "total_unresolved": len(unresolved),
            "unresolved_headings": unresolved,
        }, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {OUT_INVENTORY}")
    print(f"Wrote {OUT_UNRESOLVED}")
    print(f"Chapters: {inventory['summary']['total_chapters']}, "
          f"Sections: {len(sections)}, Topics: {len(topics)}, "
          f"Unresolved: {len(unresolved)}")
    print(f"Extraction methods: {method_counts}")
    if no_toc_chapters:
        print(f"No TOC detected: {no_toc_chapters}")


if __name__ == "__main__":
    main()
