# Same-Page TOC Merge Protocol

**Frozen at Phase 3C** as shared methodology, generalized from the Cardiology
pilot (1 merge: Acronyms + Basic Anatomy Review) and the ELOM pilot (3
merges/misattributions, including one that reattributed 12 nodes from a
"References" section to their true source — a legal-framework disclaimer
printed on the chapter's own TOC page).

## Why this happens

`toc_inventory.json`'s extraction model flattens the source into 3 levels
(chapter → section → topic). When two or more printed Toronto Notes
headings share an identical printed page label (a common layout pattern —
a short section, or a category header immediately followed by its first
subsection, both landing on the same physical page), the extraction
pipeline's same-start-page deduplication logic merges them into ONE TOC
node, keeping the first heading's title and folding the second (and any
further) heading's topic children under it. This is documented behavior of
the TOC inventory, not a bug to fix there — it is a real ambiguity in what
a flat section-level node actually represents, and study-unit derivation is
where it must be resolved.

## Detection signal

A section node is a merge candidate if:
- its `merged_duplicate_headings` field (set by the TOC builder) is
  non-empty, **or**
- its topic children's content is thematically inconsistent with the
  section's own title (e.g., topics about anatomy attached to a section
  titled "Acronyms"), **or**
- unclaimed trailing text on the chapter's own TOC page got attributed to
  the wrong (usually last-parsed) section as spurious "topic" lines.

## Resolution procedure (mandatory order)

1. **Inspect raw OCR** of the chapter's own TOC page (the page(s) identified
   by `toc_inventory.json`'s `toc_source_pdf_pages` for that chapter).
   Read every printed heading and its page label directly — this is the
   ground truth for what headings actually exist and what page they claim.
2. **Inspect the normalized/clean-OCR page text** as a cross-check if the
   raw OCR is ambiguous (rare — the two extractions are usually identical
   for TOC pages).
3. **Locate body headings independently.** If a suspected genuine heading's
   true page is unclear from the TOC alone, search the chapter's body pages
   for that heading appearing as a standalone line (same technique
   `BODY_HEADING_CONFIRMATION` uses in the TOC extraction itself) — the
   confirming page is ground truth, overriding a guessed TOC digit.
4. **Use body-heading confirmation where available** to assign each
   resolved sub-heading its own `start_pdf_page` for the study unit's
   `pdf_page_range`, rather than defaulting every split unit to the whole
   merged node's page span when a tighter bound is directly evidenced.
5. **Preserve raw provenance.** Every resolved study unit's
   `structural_rationale` must state explicitly which merge it resolves,
   which raw TOC nodes it draws from, and how the split was determined
   (e.g. "verified against raw OCR page 21"). Never state a resolution
   without citing the source page checked.
6. **Never infer a split heading from medical/domain knowledge.** If the
   printed heading text is genuinely ambiguous or illegible even after
   steps 1–4, do not guess a plausible-sounding heading. Two safe fallbacks
   exist: (a) keep the merged node as one study unit with the ambiguity
   documented in `structural_rationale`, or (b) treat the disputed portion
   as its own study unit sourced from the same node with a note that its
   title is provisional pending source clarification.
7. **Unresolved ambiguity must remain explicitly unresolved.** Do not force
   a resolution to avoid a review-queue entry. Add the ambiguity to
   `research/scope/review_queue.json` with `issue_type: "structural_ambiguity"`
   rather than silently picking one interpretation.

## What NOT to do

- Do not hard-code a fix keyed to a specific chapter's name or node ID
  inside shared code — resolutions belong in that chapter's own
  `study_units.json` `structural_rationale` fields, produced by applying
  this general procedure, not by a chapter-specific `if chapter_code == "X"`
  branch in shared tooling. (A chapter-specific note IS expected and
  correct *within that chapter's own generation script/data* — what's
  disallowed is baking chapter-specific logic into the shared TOC
  extraction or crosswalk-building code paths that every chapter uses.)
- Do not silently absorb a misattributed node's content into whichever
  section happens to be "current" during extraction without checking
  whether it actually belongs there (this is exactly the ELOM
  References-disclaimer case: 12 nodes were extraction-time-attached to
  the wrong section and would have become spurious "reference bibliography
  sub-topics" if not checked against the raw source).

## Worked examples

- **Cardiology `C.S01`** ("ACrOMYMS", merges Acronyms + Basic Anatomy
  Review, both at page C2): split into `SU-C-01` (Acronyms, the section
  node itself) and `SU-C-02` (Cardiac Anatomy Review, the two topic
  children) — see `research/scope/chapters/C/study_units.json`.
- **ELOM `ELOM.S01`** (merges three headings: Acronyms, a bare category
  header "Ethical Issues in Health Care", and "The Canadian Healthcare
  System", all at page ELOM2): split into `SU-ELOM-01` through
  `SU-ELOM-06`.
- **ELOM `ELOM.S04`** (12 nodes extracted as "References" topic children
  are actually a disclaimer paragraph printed on the chapter's TOC page,
  confirmed by searching all ELOM body pages for the exact text and finding
  it only on page 21): reattributed to `SU-ELOM-25` — see
  `research/scope/chapters/ELOM/study_units.json` for the full
  `structural_rationale`.
