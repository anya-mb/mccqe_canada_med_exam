# Task 8 report: reference registry and high-risk classification

Status: complete

Commit: `6487ca7 feat: normalize references and flag medical risk`

Implemented:

- canonical reference registry merging with normalized HTTPS URL, organization,
  title, date, deterministic organization-slug/SHA-256 IDs, claim/locator
  merging, and fail-closed metadata or ID collisions;
- deterministic, enum-ordered high-risk classification using curated structured
  fields and conservative clinical text markers;
- a schema-valid empty `references/registry.json` and synthetic regression
  tests for normalization, collisions, all risk flags, and generic-word false
  positives.

Verification:

- `PYTHONPATH=scripts python -m pytest -q tests/test_references.py tests/test_risk.py` — 16 passed
- `PYTHONPATH=scripts python -m pytest -q` — 339 passed
- `validate_instance(Path('.'), 'reference-registry', read_json(Path('references/registry.json')))` — passed
- staged diff whitespace check — passed

Concern:

`uv run` cannot run in this desktop sandbox because its Rust system-configuration
dependency panics while opening the platform configuration store. The same test
suite was run with the project source path explicitly configured instead.

## Review round 1

Addressed:

- stable-ID organization slugs now derive from the casefolded canonical
  organization identity, so Unicode/casefold equivalents cannot receive
  different IDs;
- numerical threshold detection now recognizes comparative symbols and forms,
  while ordinary measurements and ages remain unflagged without a decision
  marker;
- public-health reporting recognizes authority/action order in both directions,
  including medical-officer-of-health wording, without treating an authority
  mention alone as reporting.

TDD evidence:

- RED: `PYTHONPATH=scripts python -m pytest -q tests/test_references.py tests/test_risk.py` — 5 failed, 21 passed (Unicode slug, two comparative threshold forms, and two public-health reporting forms).
- GREEN: `PYTHONPATH=scripts python -m pytest -q tests/test_references.py tests/test_risk.py` — 26 passed.
- Full: `PYTHONPATH=scripts python -m pytest -q` — 349 passed.

## Review round 2

Symbol comparisons, including bare equality, now require a clinical decision
context in the same sentence. Explicit threshold/cutoff and verbal-comparison
markers remain supported. This preserves treatment-triggered BP and creatinine
comparisons while rejecting ordinary sample-size, baseline-measurement, and
statistical equality statements.

TDD evidence:

- RED: `PYTHONPATH=scripts python -m pytest -q tests/test_risk.py` — 3 failed, 19 passed (ordinary equality false positives).
- GREEN: `PYTHONPATH=scripts python -m pytest -q tests/test_risk.py` — 22 passed.
- Full: `PYTHONPATH=scripts python -m pytest -q` — 352 passed.
