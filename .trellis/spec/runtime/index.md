# trellis-runtime Package Guidelines

> Conventions for the fork-local `trellis-runtime/` Python package.

---

## Overview

`trellis-runtime/` packages the upstream `.trellis` Python scripts and hooks for global install via `uvx`. Its `src/` tree is vendored code — this package defines how it is synced, versioned, released, and dispatched.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Package Conventions](./package-conventions.md) | Upstream sync mapping, versioning/release tagging, `main()` entry contract, verification commands | Done |

---

## Pre-Development Checklist

Before touching `trellis-runtime/`:

- Editing vendored files under `src/` → don't; run `scripts/sync_upstream.sh` instead → [package-conventions.md](./package-conventions.md)
- After merging an upstream release → re-run sync, then bump version to the upstream version → [package-conventions.md "Versioning & Release"](./package-conventions.md)
- Adding a CLI or hook entry point → [package-conventions.md "Entry Contract"](./package-conventions.md)
- Verifying the package → [package-conventions.md "Verification"](./package-conventions.md)

---

**Language**: Prose in Chinese, identifiers/keywords/commands in English (matches [cli/backend/trellis-dependencies.md](../cli/backend/trellis-dependencies.md)).
