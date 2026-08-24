# MCCQE Qbank Production Design

Date: 2026-08-24

## Purpose

Produce a source-grounded MCCQE study bank organized in Toronto Notes 2025 order, targeting approximately 1,000 QA-passed questions in each of Medicine, Pediatrics, Obstetrics and Gynecology, Surgery, Psychiatry, and PHELO. Build the complete workflow through private Toronto Notes ingestion, manifests, a Cardiology pilot, controlled corpus production, audits, production JSON, and a locally tested React/Firebase application.

The first 40-50 Cardiology questions are the pilot and count toward Medicine's target. Accuracy remains the release criterion: a discipline may finish below 1,000 if replacement items cannot pass every gate.

## Permanent Source Rules

Toronto Notes 2025 is the primary curriculum and study-anchor source. Every ordinary question must trace to a real Toronto Notes chapter, section, subsection, TN page range, and physical PDF page range. Questions must be constructed so a learner can study that Toronto Notes topic or subtopic and then practise the same concept in an original MCCQE-style clinical decision.

Toronto Notes is not automatically the current clinical authority. Current MCC Objectives define examination scope. Current authoritative Canadian guidance determines the clinical answer when it differs from Toronto Notes 2025. Such items carry `guideline_updated_since_tn2025: true` and record the current supporting evidence. Toronto Notes prose, cases, tables, diagrams, mnemonics, and questions are never copied into generated artifacts.

The private PDF and extracted text remain outside Git and all deployable assets. Public output contains mappings and references, never Toronto Notes text or absolute local paths.

## Delivery Strategy

Production uses hybrid chapter waves:

1. Ingest and index the entire private Toronto Notes PDF.
2. Build and validate all six discipline manifests.
3. Complete one 40-50-question Cardiology pilot end-to-end.
4. Audit the pilot and correct process-level defects before scale-out.
5. Process independent chapters across disciplines in controlled waves.
6. Audit and lock each chapter before its next wave is released.
7. Audit each completed discipline, then the global corpus.
8. Export only QA-passed or genuinely human-reviewed records.
9. Build and test the React/Firebase application against production JSON.
10. Stop before deployment unless the user separately authorizes it.

## Private Toronto Notes Ingestion

Deterministic ingestion writes only under ignored `derived/toronto-notes-2025/`:

- `book.json`: source identity, edition, page count, size, and SHA-256.
- `page_index.json`: one record per physical PDF page.
- `headings.json`: normalized heading candidates and page locators.
- `chapters/<code>/manifest.json`: chapter identity and ordered section boundaries.
- `chapters/<code>/pages/<printed-page>.json`: extracted private text, headings, printed page, PDF page, extraction method, quality metrics, and source hash.
- `renders/`: temporary page images for visual inspection of uncertain pages.

Embedded text extraction is attempted first with PyMuPDF. A page is flagged when text volume, character quality, printed-page detection, or heading continuity falls below configured thresholds. Flagged pages are rendered and inspected; OCR is used only when embedded text is genuinely inadequate. Chapter TOC pages and every inferred chapter boundary receive visual QA. Ingestion is idempotent and refuses a source whose integrity differs from `config/project.json`.

The index stores private source text for agent retrieval but never republishes it. Every downstream Toronto Notes mapping resolves through page-index records rather than manually invented page numbers.

## Manifest Production

The six manifest prompts remain authoritative for coverage and allocation. Each manifest preserves actual Toronto Notes order, records all meaningful sections/subsections and exact page mappings, maps current MCC Objectives, assigns priority and target mix, identifies current-source research needs, and allocates collision-free permanent IDs.

The planning target is approximately 1,000 questions per discipline. Manifest macro-batches contain 40-50 predetermined IDs for audit and reporting. Generation does not process a whole macro-batch in one context.

All six manifests must be schema-valid simultaneously before the Cardiology pilot begins. Validation requires exact discipline identities, target arithmetic, ordered and non-overlapping page ranges, unique batch and question IDs, valid chapter codes, target distributions, and current-source research flags.

## Small-Batch Codex-Native Research and Generation

Each 40-50-item macro-batch is subdivided deterministically into five-question generation micro-batches. A micro-batch is the maximum generation unit; an agent may produce fewer items when evidence is inadequate. Research packets may be shared only when all five items concern the same tightly bounded subtopic and each claim retains its own locator.

For each micro-batch:

1. A source researcher reads only the relevant indexed Toronto Notes pages and creates a paraphrased topic outline.
2. The researcher checks current MCC scope and browses authoritative sources, preferring MCC, federal Canadian sources, and Canadian specialty organizations.
3. The researcher writes claim-level source packets before any vignette exists.
4. A separate question writer creates original items from approved claims and predetermined IDs.
5. Deterministic validation rejects malformed records before they become candidates.

Python performs only queueing, retrieval, schema validation, storage, comparison, deduplication, reporting, and export. Codex-native agents perform research, synthesis, generation, and review. No Python worker calls OpenAI or another LLM API, no API key is required, and `API_AUTOMATED` remains disabled.

Default maximum concurrency is four independent tasks, but no more than two medical generation tasks run concurrently until the pilot demonstrates stable quality. Source or rate-limit pressure reduces concurrency automatically; it never relaxes validation.

## Independent Verification

Verification is item-scoped, not micro-batch-scoped.

For each candidate:

1. Build a blind packet containing no answer key, rationale, distractor rationales, or generator notes.
2. Dispatch an isolated blind verifier that independently reads the mapped Toronto Notes section, checks current sources, and chooses one answer.
3. Require confidence at least 0.85, `single_best_answer: true`, no defensible alternative, sufficient stem information, valid TN mapping, current-guideline support, and MCC-level appropriateness.
4. Quarantine every key mismatch without autocorrection.
5. Give a different rationale auditor the full candidate and claim packet only after blind agreement.
6. Require passes for key, rationale, every distractor, every material claim, references, Canadian context, ambiguity, TN mapping, and MCC scope.
7. Revisions return to candidate status and repeat blind verification from scratch. Two failed revisions lead to rejection or human review.

Agreement between Codex agents is not proof. A question fails closed whenever accessible authoritative evidence does not establish the answer.

## Duplicate, Risk, and Copyright Controls

Duplicate detection runs within the micro-batch, macro-batch, chapter, discipline, and global corpus using normalized hashes, lexical similarity, semantic candidate retrieval, repeated clinical-decision fingerprints, option-set similarity, and shared-vignette heuristics. Uncertain semantic matches are flagged, not silently deleted.

Numerical thresholds, doses, screening, vaccination, pregnancy, pediatrics, anticoagulation, legal rules, public-health reporting, and emergency treatment receive enhanced checks and human-review priority. Two authoritative sources are preferred for high-risk claims when practical.

Every candidate is checked for suspicious similarity to Toronto Notes source text and known project-visible examples. No Toronto Notes text is stored in public question rationales.

## Audit and Locking

The Cardiology pilot is audited before any scale-out. Its acceptance criteria are:

- 40-50 requested IDs, with every shortfall explained;
- all published items pass blind and full-rationale review;
- exact and semantic duplicate review complete;
- answer and difficulty distributions are plausible;
- Toronto Notes topic/subtopic traceability is complete;
- references support material claims;
- high-risk items are separately listed;
- a human-readable pilot report records defects and process changes.

Thereafter, each chapter is audited and assigned an immutable content version before its questions enter the discipline candidate set. Discipline audits cover coverage, MCC mappings, distributions, reference quality, freshness, duplicates, and rationale quality. The global audit repeats these checks across all six disciplines and generates JSON and Markdown reports.

## Production Dataset and Web Application

Production export is rebuilt transactionally from verified filesystem evidence. It includes only QA-passed questions or items with actual reviewer metadata. Candidates, blind packets, internal source packets, verifier reasoning, quarantine, rejected records, private QA notes, and Toronto Notes files/text are excluded.

The React application reads versioned JSON under `app/public/data/qbank/`. It provides discipline/chapter/subtopic navigation, question sessions, five-option answering, detailed rationales, Toronto Notes study anchors, reference links, progress state, filtering, and search. Content tests prove references render and that no non-production item or private artifact is reachable. Firebase Hosting configuration and local build/emulator checks are included; deployment requires a separate explicit instruction.

## Checkpoints and Documentation

Meaningful commits are required after:

- production design and implementation plan;
- ingestion/indexing implementation and validated private index;
- six manifests and queue generation;
- Cardiology source packets;
- Cardiology candidate generation;
- Cardiology blind/rationale verification and audit;
- every completed chapter;
- every discipline audit;
- global audit;
- production export;
- React/Firebase application completion.

The implementation plan is updated as tasks complete. `reports/milestones.md`, `reports/progress.json`, and `reports/progress.md` are regenerated from durable artifacts. Counts are never estimated or hard-coded.

## Failure Handling

Every job transition is atomic and preserves raw responses and failure evidence. Failures are classified as `TECHNICAL_FAILURE`, `SOURCE_FAILURE`, `MEDICAL_AMBIGUITY`, `REFERENCE_FAILURE`, `SCHEMA_FAILURE`, `DUPLICATE`, or `COPYRIGHT_SIMILARITY`. Technical retries are bounded. Substantive medical failures are not repeatedly regenerated without a new verified claim packet.

If web access, an authoritative source, PDF extraction quality, or Codex capacity is temporarily unavailable, the affected job remains blocked or failed and completed artifacts remain valid. The system never falls back silently to model memory.

## Completion Criteria

The program is complete when:

- the full private Toronto Notes index passes integrity and mapping QA;
- all six manifests and deterministic queues pass validation;
- the Cardiology pilot passes its chapter audit;
- each discipline has up to approximately 1,000 QA-passed items, with shortfalls explicitly reported;
- all chapter, discipline, and global audits pass;
- production counts are computed from verified artifacts;
- the React/Firebase application builds and passes content/security tests;
- no protected source or internal QA artifact is tracked or deployable;
- milestone and implementation documents match the filesystem evidence.

The project does not claim physician review unless a qualified human has actually reviewed the specific items.
