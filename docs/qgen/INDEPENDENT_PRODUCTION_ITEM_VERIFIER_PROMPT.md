# Independent Production Item Verifier V1

Use this prompt only in a **new Codex session that did not author the item**. The authoring session may not mark its own item `FINAL_VERIFIED`. Session identifiers establish provenance only; they are not medical evidence.

Provide the new session with:

- one or more `PRODUCTION_ITEM_VERIFICATION_PACKAGE_V1` JSON paths;
- the repository path containing the relevant Toronto Notes source material;
- access to the current Canadian-source research and the original authoritative source documents.

Do not provide author-session conclusions, prior verifier verdicts, or adjudication outcomes before Stage 1.

## Non-negotiable rules

- Do not generate or rewrite a question during verification.
- Do not reveal private chain-of-thought. Return concise conclusions, defect descriptions, and direct source traces only.
- Do not trust author citations merely because they exist. Open and inspect the cited source and locator.
- Do not rely solely on author-created summaries when actual Toronto Notes or current authoritative guidance is available.
- Do not reproduce substantial Toronto Notes prose.
- Fail closed when a source cannot be found, a decision-changing conflict is unresolved, or the package hash does not validate.
- Freeze Stage 1 before opening any key, rationale, evidence, or author-confidence field.

## Stage 1 — blind solve

Have a coordinator produce the strict blind projection. It may contain only:

- item ID;
- stem;
- lead-in;
- answer choices.

Without inspecting any other package field, return:

- chosen best answer;
- confidence (`LOW`, `MODERATE`, or `HIGH`);
- possible second key, or `null`;
- ambiguity assessment;
- missing-information assessment;
- MCCQE realism (`PASS`, `FAIL`, or `UNCERTAIN`).

Freeze and hash this verdict. Do not revise it after Stage 2 begins.

## Stage 2 — evidence and rationale audit

Only after Stage 1 is frozen, reveal the author key, rationales, evidence package, Toronto Notes references, and current-guidance references.

Extract every rationale claim and classify it as exactly one of:

- `VERIFIED`
- `SUPPORTED_WITH_SCOPE_LIMITATION`
- `UNSUPPORTED`
- `CONTRADICTED`
- `OUTDATED`
- `SOURCE_NOT_FOUND`
- `OVERSTATED`
- `NOT_LOAD_BEARING`

For each load-bearing claim, record a direct source trace. A trace is mandatory for thresholds, ages, timing, screening intervals, drug choices and doses, contraindications, legal obligations, pregnancy recommendations, emergency actions, diagnostic criteria, and any other fact that can change the best answer.

Explicitly check for invented recommendations, fabricated or non-entailing citations, wrong age/timing/dose/interval, wrong legal duty, wrong pregnancy recommendation, unsupported absolute wording, invented symptom/sign associations, incorrect first-line claims, incorrect contraindications, and false absence inferences.

### Toronto Notes classification

Inspect the actual relevant material where available and assign one:

- `TN_CONSISTENT`
- `TN_MORE_GENERAL`
- `TN_MORE_DETAILED`
- `TN_DIFFERENT_SCOPE`
- `CURRENT_GUIDANCE_UPDATES_TN`
- `MATERIAL_TN_CONTRADICTION`
- `TN_SOURCE_NOT_FOUND`

### Current Canadian guidance

Prefer, as relevant, CPS, SOGC, Health Canada, PHAC, CTFPHC, CANMAT, CMPA, provincial Colleges, and Canadian specialty societies. Use major current international guidance only when appropriate Canadian guidance is unavailable. Record the organization, title, URL or repository locator, publication/update date or version, retrieval date, and the precise section supporting the claim.

If Toronto Notes and current Canadian guidance differ, assign one:

- `CURRENT_GUIDANCE_CLARIFIES_TN`
- `CURRENT_GUIDANCE_UPDATES_TN`
- `MATERIAL_CONFLICT`
- `UNCERTAIN`

For current management, authoritative current Canadian guidance normally controls. A conflict that could change the best answer requires rejection or revision; never choose silently.

### Answer and rationale validity

Require all of the following for acceptance:

- the blind answer equals the author key;
- exactly one best answer and no possible second key;
- at least three genuinely plausible but inferior distractors;
- all options use the same response class and compatible granularity;
- the rationale explains why the key fits, which evidence discriminates, why each distractor is plausible yet inferior here, what would make each distractor correct, and the conditional next action where meaningful.

## Final verdict

Return exactly one:

- `VERIFIED_ACCEPT`
- `REJECT_WRONG_KEY`
- `REJECT_SECOND_KEY`
- `REJECT_AMBIGUOUS`
- `REJECT_UNSUPPORTED_RATIONALE`
- `REJECT_HALLUCINATION`
- `REJECT_CANADIAN_GUIDELINE_CONFLICT`
- `REJECT_TORONTO_NOTES_CONFLICT`
- `REJECT_OUTDATED_GUIDANCE`
- `REJECT_WEAK_DISTRACTORS`
- `NEEDS_SOURCE_UPDATE`
- `NEEDS_HUMAN_ADJUDICATION`

Only `VERIFIED_ACCEPT` may enter the final production bank. Write the Stage-1 and Stage-2 hashes and verified source versions/dates to `PRODUCTION_ITEM_VERIFICATION_LEDGER_V1`. Freeze the verified-content hash. Any change to stem, lead-in, options, key, rationale, or load-bearing evidence/source bindings requires a new independent verification.

## Disagreement

If the author and verifier disagree, create a compact packet containing the item, both verdicts, and relevant source evidence. Send only that packet to a third session distinct from both author and verifier. The adjudicator must return exactly one of `AUTHOR_CORRECT`, `VERIFIER_CORRECT`, `BOTH_INCOMPLETE`, `ITEM_AMBIGUOUS`, `SOURCE_CONFLICT`, or `REJECT`.
