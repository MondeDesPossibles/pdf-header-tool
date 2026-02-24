# Step Execution Checklist

## Before Coding
- Identify requested roadmap step/substep.
- List in-scope files and explicit out-of-scope files.
- Read latest state of touched files.

## During Coding
- Keep diffs minimal and scoped.
- Avoid opportunistic cleanups unrelated to requested step.
- Watch for import cycles when moving code.

## After Coding
- Run syntax/import checks.
- Run risk-aligned runtime smoke.
- Verify logs for startup/apply/update events.
- Update docs (`ROADMAP.md`, `CLAUDE.md`) if architecture/process changed.

## Before Commit
- Ensure commit includes only intended files.
- Exclude local prompt/handoff artifacts unless explicitly requested.
- Confirm branch state and divergence before push.
