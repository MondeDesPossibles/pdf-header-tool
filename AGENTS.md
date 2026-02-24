# AGENTS.md

Repository instruction entrypoint.

## Instruction Files
Use and maintain instruction files in `docs/agent-rules/`:
- `docs/agent-rules/CORE_RULES.md`
- `docs/agent-rules/AGENT_CODEX.md`
- `docs/agent-rules/AGENT_CODING_GUIDELINES.md`
- `docs/agent-rules/CODE_CONVENTIONS.md`

## Precedence
- Higher-level runtime/developer instructions take priority.
- Then apply this repository's rules from `docs/agent-rules/`.
- Then apply task-specific docs (`ROADMAP.md`, `CLAUDE.md`, etc.).

## Scope Discipline
- Keep changes minimal and scoped.
- Preserve external behavior unless explicitly requested.
- Update architecture/roadmap docs when structural changes are made.
