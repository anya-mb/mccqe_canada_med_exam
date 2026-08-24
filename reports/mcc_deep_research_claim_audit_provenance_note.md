# Provenance Verification of the Audited Deep Research Memo

**Date:** 2026-08-24
**Supersedes:** Nothing in `reports/mcc_deep_research_claim_audit.md` is retracted or edited by
this note. This is an additional provenance finding required before trusting that audit's
"0 incorrect claims" conclusion at face value.

---

## What was checked

Per instruction, before relying on `reports/mcc_deep_research_claim_audit.md`, the exact
identity of the file it audited was verified.

| Field | Value |
|---|---|
| Path | `research/raw/MCC_ONLY_DEEP_RESEARCH_MEMO.md` |
| SHA-256 | `ca8bb3686d8169a6cffba299cd5d16bbedde8e46ba4a26db14ecd6d8e07d3e45` |
| Filesystem mtime | 2026-08-24 14:40:48 |
| Git history | Added in exactly one commit: `f76fa36` ("feat: build canonical MCC evidence layer (Phase 1)"), the same commit that first published the Phase 1 evidence artifacts. No earlier commit touches this path. |

## Classification

The file's own first line reads:

> `# CORRECTED MCCQE EVIDENCE SUMMARY — VERIFIED 2026-08-24`

and its body explicitly instructs (lines 39–42):

> "Do NOT claim: one-third are pilot questions; one-third of each section is pilot; exactly 10
> pilot questions occur in each section."

This means the file already contains the correction for the exact error the task instructions
warn about (the "one-third of each section is pilot" misconception). It is therefore **classification
B — "the corrected MCC evidence memo"** in the task's own A/B/C scheme, not **A — "the original raw
Deep Research memo"**.

## Why this matters, and why it does not invalidate the prior audit

The task states: *"If the audit claims '0 incorrect claims' AND it audited the original
uncorrected memo: the audit itself is invalid and must be regenerated."*

Since the audited file is confirmed to be version B, not version A, that trigger condition is not
met. The prior audit's "0 incorrect claims found" conclusion is an accurate description of the
document it actually examined — the corrected memo does not contain the one-third-pilot error
because it was already written with that error removed.

## The real gap: no true original was ever preserved

Git history shows this repository never held a separate, uncorrected "version A" file at any
point — only the already-corrected version B was ever committed. The file was present,
untracked, in the working directory before this session's Phase 1 work began, and was first
captured into git as part of a broad `git add research/` in commit `f76fa36`. Its content was not
authored by this session; only its retrieval into the audit process was.

Practical consequence: `reports/mcc_deep_research_claim_audit.md` cannot be read as "independent
proof the original Deep Research output was error-free," because the original, error-containing
version was never available to audit — it was superseded/corrected before ever reaching disk in
this repository. The audit is valid as a check of version B against official MCC sources, and
that check is what the Phase 1 evidence artifacts (`current_exam_profile.json`, `blueprint.json`,
etc.) are actually built from — not from any unverified "version A" claims.

## Action taken

- No prior report was edited or deleted.
- This note is filed alongside the original audit as the required provenance record.
- The distinction between "audited document was already corrected" and "audited document was
  independently verified from scratch against official sources" is preserved: every fact in
  `research/mcc/*.json` was separately confirmed against live `mcc.ca` pages/PDFs during Phase 1
  and Phase 2, not simply carried over from the memo's claims.
