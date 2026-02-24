---
name: pdf-header-maintainer
description: Maintain and evolve the PDF Header Tool repository with roadmap-aware scope control, safe refactors, release/update compatibility, and reproducible validation. Use when modifying `pdf_header.py`, `app/`, `build_dist.py`, `run_dev.sh`, `release.sh`, `ROADMAP.md`, or `CLAUDE.md`, and when preparing step/substep work, resolving git workflow issues, or validating auto-update/release behavior.
---

# PDF Header Maintainer

## Overview
- Align every change with `ROADMAP.md` and `CLAUDE.md` before editing.
- Keep scope strict to the requested step/substep; do not bundle unrelated refactors.
- Preserve release/update invariants so local tests and shipped patches remain compatible.

## Workflow
1. Ground in repository truth before proposing changes.
2. Map requested change to roadmap step/substep and list in-scope files.
3. Implement minimal edits with explicit compatibility checks.
4. Run validations that match risk level and touched modules.
5. Document technical deltas in project docs when architecture/flow changes.

## Execution Rules
- Read first: `ROADMAP.md`, `CLAUDE.md`, relevant modules under `app/`, and touched scripts.
- Apply instruction precedence from `references/instruction-sources-and-precedence.md`.
- Prefer targeted edits over broad rewrites.
- Preserve `release.sh` assumptions: `VERSION`, `BUILD_ID`, `CHANNEL` entries in `pdf_header.py` must remain machine-editable.
- Preserve bootstrap/update sequence: pending update application must happen before heavy imports.
- When moving code across modules, check import graph to avoid circular dependencies.
- For release/update-sensitive changes, verify patch contents include all moved source files.

## Validation Matrix
- Syntax/import baseline:
  - `python3 -m compileall pdf_header.py app`
  - import smoke in project venv for touched modules.
- Runtime smoke (GUI path):
  - `./run_dev.sh <env> <profile>` with explicit env/profile in report.
- Update/patch integrity when packaging code changes:
  - inspect patch zip contents and metadata consistency.
- Regression-focused checks:
  - run narrow tests/scenarios linked to touched logic (UI, font handling, rotated pages, update staging).

## Documentation Rules
- Update `CLAUDE.md` when architecture, module ownership, or operational workflows change.
- Update `ROADMAP.md` when a step/substep state or implementation reality changes.
- Keep additions concise, auditable, and clearly attributable.
- If project instructions evolve, keep `docs/agent-rules/AGENT_CODING_GUIDELINES.md`,
  `docs/agent-rules/AGENT_CODEX.md`, `docs/agent-rules/CODE_CONVENTIONS.md`, and
  `docs/agent-rules/CORE_RULES.md` aligned.

## Git Workflow Rules
- Keep commits scoped and readable.
- Do not revert unrelated user changes.
- When branch diverges from remote, rebase/merge intentionally and resolve conflicts with project conventions preserved.

## References
- Architecture and module ownership: `references/architecture-map.md`
- Release/update invariants and checks: `references/release-update-invariants.md`
- Step execution checklist: `references/step-execution-checklist.md`
- Instruction sources and precedence: `references/instruction-sources-and-precedence.md`
