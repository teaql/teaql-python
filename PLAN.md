# TeaQL Python Migration Plan

## 1. Goal
Migrate `teaql-rs` to `teaql-python`, maintaining 1:1 semantic and algorithmic parity. The resulting library must be able to support `robot-task-board` with identically matching logs and readable code.

## 2. Scope
* Compatibility: Python 3.10+ (No legacy Python support required).
* Test coverage: Migrate tests to match `teaql-rs` precisely.
* End-to-end validation: Generate and run `robot-task-board` in Python and verify that logs match the Rust version exactly.

## 3. Phases

### Phase 1: Core Foundation & Models (In Progress)
* [x] Scaffold project (`pyproject.toml`, pytest configuration).
* [x] Implement `Value` model (Enum/Variant parity).
* [ ] Implement core logic modules (`expr.py`, `query.py`, `record.py`).

### Phase 2: Code Generation Support in `teaql-code-gen`
* [x] Branch `2026-08-python-support-init-version` created.
* [x] Setup Python Generator Classes.
* [ ] Fix generator STG templates (Replace Go/Rust generation logic with Python).
* [ ] Test generation against `models/main.xml`.

### Phase 3: Runtime API & Database Integration
* [ ] Port execution runtime (Mocking and integration).
* [ ] Implement SQLite backing for Python (if required for e2e test parity).
* [ ] Map context `ServiceRuntimeFromEnv()` correctly.

### Phase 4: E2E Validation (Robot Task Board)
* [ ] Run `python-app-console` workspace generated from `models/main.xml`.
* [ ] Ensure output logs match `expected-log.txt`.
