# Plan: Smoke test for nim-execute

## Context
Minimal end-to-end test: write a Python module with a constant, verify importable.

## Tasks

### Task 1: Create a tiny constants module
- **mode:** A
- **target:** smoke_out/constants.py
- **context_files:** []
- **verifier:** .venv/bin/python -c "import sys; sys.path.insert(0,'.'); import smoke_out.constants as c; assert c.GREETING == 'hello from nim'"
- **verifier_timeout_s:** 15
- **spec:**
  Create a Python module containing exactly one module-level constant:
  `GREETING = "hello from nim"`. Do not include any other code, no comments,
  no docstring. The file must contain only that single assignment.
