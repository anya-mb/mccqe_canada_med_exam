# MCCQE Qbank Pipeline

Deterministic, fail-closed filesystem foundation for a source-grounded MCCQE question bank. The project uses active Codex-native work for medical reasoning and Python only for deterministic orchestration, validation, and data management.

Toronto Notes is private and is used solely as a study-anchor source. It is not committed, exported, or treated as final clinical authority. Current MCC Objectives and authoritative Canadian guidance govern scope and answers.

## Setup

Install the development environment with `uv sync --extra dev`. The committed configuration is in `config/project.json`; copy `config/project.local.example.json` to the ignored `config/project.local.json` and set the local Toronto Notes PDF path.

The lifecycle directories contain only validated JSON artifacts. Production exports are written to `app/public/data/qbank/` and must contain only `QA_PASS` items or documented `HUMAN_REVIEWED` items.
