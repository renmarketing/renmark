# Plan: Demo

## Context
This is a demo plan used by tests. The orchestrator should ignore prose.

## Tasks

### Task 1: Add a constant module
- **mode:** A
- **target:** src/constants.py
- **context_files:** []
- **verifier:** python -c "import src.constants; assert src.constants.PI == 3.14"
- **spec:**
  Create a Python module defining `PI = 3.14` and `E = 2.718`.

### Task 2: Wire constant into app
- **mode:** B
- **target:** src/app.py
- **context_files:** [src/app.py, src/constants.py]
- **model:** mistralai/codestral-22b-instruct-v0.1
- **verifier:** python -c "import src.app; assert src.app.greet() == 'hi pi=3.14'"
- **verifier_timeout_s:** 30
- **spec:**
  Add a `greet()` function that imports PI from constants and returns
  `f"hi pi={PI}"`.
