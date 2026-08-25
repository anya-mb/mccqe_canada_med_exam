# Scope chapter workflow (compact packets)

Reusable deterministic commands to reduce context use while scaling the
Toronto Notes -> MCC scope crosswalk chapter by chapter:

```
python -m scripts.qbank prepare-scope-chapter <CODE>
python -m scripts.qbank validate-scope-chapter <CODE>
python -m scripts.qbank search-mcc-objectives "<query>"
```

Both commands are local, deterministic, and use no LLM/model API.

## Per-chapter workflow

1. Read `reports/scope_scaling_progress.json` for `next_chapter`.
2. Run `prepare-scope-chapter <CODE>` -> writes `derived/scope_packets/<CODE>.json`
   (gitignored) and prints a size report.
3. Give Claude only that packet plus the frozen scope schema/methodology -
   not the full TOC inventory or objectives registry.
4. Claude derives study units and the MCC crosswalk (judgment work: this is
   never done by the preparation command).
5. Run `validate-scope-chapter <CODE>` -> writes
   `reports/chapter_validation/<CODE>.json` and prints PASS/FAIL plus
   warnings. Fix and re-run until it PASSes.
6. Semantically review only flagged/risky mappings (WEAK, UNCERTAIN,
   validator warnings) - the validator already covers everything
   machine-checkable.
7. Run the test suite (`pytest`).
8. Update `research/scope/review_queue.json` and
   `reports/scope_scaling_progress.json` (`completed_chapters`,
   `next_chapter`, `last_completed_commit`).
9. Commit the chapter.
10. Stop the session.

If the correct MCC objective is not in a packet's bounded candidate set
(`candidate_set_truncated: true`), use `search-mcc-objectives` to search the
full canonical registry rather than guessing or leaving evidence weak.
