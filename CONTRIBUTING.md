# Contributing to AudioMason

Thank you for your interest in contributing to AudioMason.

## How to Propose Changes

All changes must be proposed through the project's defined workflow:
- Open or reference a GitHub issue.
- Use an **implementation chat with a formal handoff** for any change.
- Follow the requirements defined in the governance documents.

Direct, ad-hoc changes are not accepted.

## Governance and Rules

AudioMason is governed by authoritative documents located in:

```
docs/governance/
```

These documents define:
- Project rules and constraints
- Roles and responsibilities
- Implementation and verification requirements

All contributors **must** read and respect these documents.

## Coding Standards (High-Level)

- Keep changes minimal and scoped to the issue.
- Maintain clarity and readability.
- Follow existing project structure and conventions.
- Do not introduce new rules or policies outside the governance framework.

## Documentation and Changes

Documentation changes are subject to the same governance rules as code changes.
Implementation chats and handoffs are mandatory for all accepted changes.

## Dev tooling (ruff + mypy)

AudioMason uses **ruff** (lint + formatter) and **mypy** (type checking) as developer tooling.

### Install (developer environment)

Use the optional `dev` extra:

```bash
python -m pip install -U pip
pip install -e ".[test,dev]"
```

### Run locally

```bash
ruff check .
ruff format --check .
mypy src/audiomason
```

### Notes

- `mypy` is intentionally scoped to `src/audiomason` only.
- Clear caches if results look stale:

```bash
rm -rf .mypy_cache .ruff_cache
```
