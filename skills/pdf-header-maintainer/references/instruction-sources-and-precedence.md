# Instruction Sources and Precedence

## Purpose
Define the instruction stack used by this skill, combining project-local rules and
OpenAI Codex guidance.

## Project-Local Sources
Read and apply these files when they exist in the repository root:
- `docs/agent-rules/CORE_RULES.md` (base rules)
- `docs/agent-rules/AGENT_CODEX.md` (Codex-specific constraints)
- `docs/agent-rules/AGENT_CODING_GUIDELINES.md` (execution and architecture rules)
- `docs/agent-rules/CODE_CONVENTIONS.md` (naming, typing, structure conventions)

## Precedence Model
1. Runtime/platform instructions (system/developer constraints)
2. Repository-level operational instructions (`AGENTS.md` if present)
3. Project-local rule documents listed above
4. Task-specific docs (`ROADMAP.md`, `CLAUDE.md`, bug notes, step plans)

If two sources conflict, follow the higher-priority source and document the decision
in the change summary.

## OpenAI Docs Alignment
This skill follows official guidance from:
- AGENTS.md guide (repository instruction file and layering behavior)
  - https://developers.openai.com/codex/guides/agents-md
- Skills guide (trigger metadata, concise skill body, progressive disclosure)
  - https://developers.openai.com/codex/skills

## Practical Application Rules
- Load only the references needed for the current task.
- Keep `SKILL.md` concise; move details into `references/`.
- Preserve minimal diff discipline and external behavior unless explicitly requested.
- Keep type hints and validation integrity unless a requested change requires otherwise.
