# Milestone 1: Qbank foundation handoff

## Checkpoint

Branch: `codex/qbank-foundation`  
HEAD: `b81f83eca5f972aa0483fabf56b5c05d5765f730` (`fix: preserve manifest sources across CLI jobs`)

The foundation is deterministic, fail-closed, and configured for `CODEX_NATIVE` research. No questions were generated, verified, or published. The empty filesystem is the source of truth: `reports/progress.json` records planned `0`, generated `0`, blind passed `0`, QA passed `0`, human reviewed `0`, rejected `0`, quarantined `0`; all discipline/chapter breakdowns and all queue states are empty/zero; and coverage gaps are empty because no manifests are planned yet.

## Exact foundation branch commits

The branch history from the foundation scaffold through this handoff is:

```text
1118daa9d7b52af097ba82571805eb9f73daefed chore: scaffold qbank production pipeline
7f53865c31a8cad4e1b6bcd4855b6e71087315f4 feat: add deterministic config and JSON storage
dd0d7e52b3cac65b2c0b3e24a7d5a4e57b4bed9a fix: reject non-finite JSON numbers
9dcfc1dbb885dae8cafd045838dc9daa7abcc6b6 feat: define canonical qbank schemas
5e477e5327d058ac7ee8c94c80c8933f73bec635 fix: tighten canonical schema validation
d32504d462b83e27db809698368dd18f9a0404d9 feat: enforce Toronto Notes source integrity
0367a608d012a69818d9ce49ca54ca828b958e4c fix: close source validation leak checks
10a8e417aa4f9896937e043ab6a24e452310e2ca feat: enforce qbank lifecycle transitions
f10cd7933c2317c476bad2ddc7e4e6dab61f87ba feat: generate deterministic qbank job queues
68d1c415a7857e679851eb8608e2d3d191046dc2 fix: validate timestamp-free pending jobs
801d95e88eafa7a47ba57340c5eb794cd63244c test: validate stored running jobs
8c403cab6d274b1d44eec12d2ba40f3c59a3a9b8 feat: add isolated blind verification gate
981a6675b304c8f262e5b99d892cc15008a402d7 fix: enforce blind confidence floor
6487ca71ba4d5645b8afd0651917d39f3c90c05c feat: normalize references and flag medical risk
c8f2f80425ec57127fa3a1b038433de6a4d40340 fix: harden reference IDs and risk flags
b3d978be6d61d683c127bffce842b5f1e841aa75 fix: constrain numerical threshold symbols
305f5edcc7ff73304b46d87d1f6a5f216c50ac84 feat: build progress reports and safe production data
2cafda122f60c0f776c82d9af77680f8ccca14ac fix: validate progress lifecycle evidence
e10bf62acdbfdccc88b92a78fc5ef85b22368c20 feat: complete deterministic qbank foundation
b81f83eca5f972aa0483fabf56b5c05d5765f730 fix: preserve manifest sources across CLI jobs
```

## Source validation

The private local source is Toronto Notes 2025, 41st Edition. `qbank validate-source` and `qbank validate-project` both validated:

- pages: `1,595`
- size: `444,206,901` bytes
- SHA-256: `9cafb5f2064335c8e4ee00abf446ab78d12b469802aa134fb84effcef3704288`
- source remains outside Git and deployable assets

## Implemented controls

The milestone provides portable policy/configuration, canonical Draft 2020-12 schemas, atomic JSON I/O, source metadata/hash/page/deploy-leak validation, deterministic manifest and job validation, lifecycle transition enforcement, answer-key-free blind packets with confidence gates, reference normalization and risk flags, filesystem-derived progress, and production export restricted to QA-passed or documented human-reviewed items. Python is deterministic orchestration only: no OpenAI or other model API calls, no API key, and no external model billing. `API_AUTOMATED` is disabled.

## Verification evidence

The installed repository environment ran the full suite with `.venv/bin/pytest -q`: **385 passed in 4.66s**. `qbank validate-project` returned `PROJECT_VALID`, `CONFIG_VALID`, `PROMPTS_VALID: 9`, `SCHEMAS_VALID: 11`, `DEPLOY_EXCLUSION_VALID`, and `SOURCE_VALID: 1595 pages`; it explicitly reported `GENERATION_BLOCKED` because zero manifests exist. `git diff --check` returned success, and the tracked-file leakage scan found no PDF, `derived/`, or source-derived deploy artifact.

## Next authorized milestone

The next and only authorized milestone is **private Toronto Notes ingestion**: establish embedded-text extraction quality, deterministic page/heading mapping, and visual QA for uncertain pages under ignored private `derived/` storage. No Cardiology medical-content generation, question generation, or publication is authorized until that ingestion checkpoint is complete and separately verified.
