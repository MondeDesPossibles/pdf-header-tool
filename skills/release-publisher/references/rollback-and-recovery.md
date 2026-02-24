# Rollback and Recovery

## Failure before commit/tag
- Restore modified files from git index/worktree.
- Re-run dry-run with corrected inputs.

## Failure after commit, before tag push
- Revert or amend local commit according to team policy.
- Delete local tag if created prematurely.

## Failure after tag push
- Create a corrective commit.
- If policy allows: delete remote tag and recreate.
- If policy forbids deletion: publish corrective follow-up version.

## Always capture
- failing command
- exact error output
- current branch/tag state
- remediation applied
