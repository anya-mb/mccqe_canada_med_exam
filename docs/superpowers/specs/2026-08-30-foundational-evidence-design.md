# Foundational Evidence Design

Date: 2026-08-30

## Scope

Add a separate, additive evidence layer for stable factual support. It does not change the frozen 6,086-question allocation, scope, MCC mapping, ownership, Toronto Notes mappings, source-packet populations, audits, manifests, or the generator in this phase.

`research/qgen/foundational_evidence_claim_cards.json` is the canonical foundational-evidence artifact. It contains only atomic claim cards with `verification_status: "VERIFIED_COMPLETE"`; a missing, incomplete, blocked, or uncited claim is not admitted. A card is one independently citable factual proposition, not a topic summary, a recommendation bundle, or model-memory completion.

## Artifact contract

The root records `schema_version`, `scope: "FOUNDATIONAL_EVIDENCE_CLAIM_CARDS"`, the fixed source-registry artifact path and SHA-256, `documents`, and `claim_cards`.

Each card has a deterministic `FNDCLM-*` ID; one concise `claim`; one or more scope references (`study_unit_id` and/or allocation address); one or more citation objects (`document_id`, `locator`); an explicit stable-factual use classification; and `verification_status: "VERIFIED_COMPLETE"`. Citation locators must identify the supporting passage, table, figure, or section. The validator rejects duplicate card IDs, duplicate normalized claims within the same scope reference, invalid references, unknown documents, empty locators, and non-atomic/multi-claim structures that the schema can detect mechanically.

`documents` is metadata only. A citation reuses an existing `SRDOC-*` record when its normalized HTTPS canonical URL is already in `research/qgen/source_document_registry.json`. A document with a URL absent from that registry is recorded once as `FNDOC-` plus the first 16 uppercase hexadecimal characters of SHA-256 of its canonical URL, with the same identity and provenance fields used by the source-document registry. `FNDOC-*` entries must not duplicate an `SRDOC-*` URL or another `FNDOC-*` URL. Neither document metadata nor cards contain Toronto Notes text, question text, recommendations that require current guidance, or uncited factual assertions.

## Authority boundaries

Toronto Notes remains `TOPIC_CONTEXT_ONLY`: frozen scope/navigation metadata is used to locate the applicable topic but never as claim evidence or current guidance. Its existing `tn_page_range` (printed pages) and `pdf_page_range` must remain available together and unchanged; no OCR, indexing, page mapping, or scope rewrite is part of this layer.

Current or guideline-sensitive statements remain exclusively in READY current Canadian source packets. Foundational cards supply cited stable factual support only. The future generator must fail closed if it lacks the required kind of support and must not fill factual gaps from model memory.

## Deterministic audit

`reports/foundational_evidence_audit.json` is rebuilt solely from the claim artifact, the source-document registry, and frozen scope identifiers. It records input paths and SHA-256 fingerprints, counts of cards/citations and `SRDOC-*`/`FNDOC-*` references, stable sorted IDs, duplicate/missing-reference counts, and `status: "PASS"` only when the artifact exactly matches a deterministic rebuild. A fingerprint or provenance mismatch fails closed.

## Phase boundaries

Phase A implements only the schema/model, deterministic validator, provenance/fingerprint audit, CLI validation/write path, and focused tests. It creates no researched claim cards and does not modify the pilot generator.

Phase B is deliberately deferred: research only the stable claims needed for the 10-question `QGEN-PHELO-011` retry, make its 10-slot concept plan, then modify that pilot generator to consume frozen scope plus Toronto Notes context, foundational cards, and READY current packets. No Phase B action is authorized by this design alone.

