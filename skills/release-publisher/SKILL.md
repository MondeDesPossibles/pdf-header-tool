---
name: release-publisher
description: Publish stable and beta releases for PDF Header Tool with strict version/build consistency checks, branch-safe git flow, runtime whitelist packaging, and rollback-ready procedures. Use when preparing or validating release operations involving `release.sh`, `build_dist.py`, tags, GitHub release assets, or patch metadata.
---

# Release Publisher

## Overview
- Execute release workflows with low-freedom, explicit checks, and reproducible outputs.
- Keep stable and beta channels consistent across versioning, tags, assets, and metadata.

## Workflow
1. Run preflight checks from `references/release-flow.md`.
2. Validate version/build invariants from `references/version-build-rules.md`.
3. Validate runtime whitelist/package scope from `references/packaging-whitelist.md`.
4. Run dry-run command path before any mutating release action.
5. Execute stable or beta flow and collect artifact evidence.
6. Apply rollback procedure immediately on failure (`references/rollback-and-recovery.md`).

## Guardrails
- Do not skip dry-run before mutation.
- Do not publish if version/build checks fail.
- Do not force push or delete tags unless explicit operator instruction.
- Do not include dev-only files in runtime packaging.
- Keep release scripts versioned and tracked in Git.

## Command Reference
- Stable dry-run: `./release.sh X.Y.Z --dry-run --list-package`
- Beta dry-run: `./release.sh X.Y.Z-beta.N --beta --dry-run --list-package`
- Stable release: `./release.sh X.Y.Z --list-package`
- Beta release: `./release.sh X.Y.Z-beta.N --beta --list-package`
- Package listing only: `python3 build_dist.py --list-files`

## References
- Flow and checks: `references/release-flow.md`
- Version/build policy: `references/version-build-rules.md`
- Runtime whitelist policy: `references/packaging-whitelist.md`
- Rollback and recovery: `references/rollback-and-recovery.md`
