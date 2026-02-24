# Release Flow (Stable/Beta)

## Preflight
- Ensure clean working tree.
- Ensure current branch is correct for release.
- Ensure local branch is not behind remote.
- Run package listing to review runtime + patch file set.

## Dry-run first
- Stable: `./release.sh X.Y.Z --dry-run --list-package`
- Beta: `./release.sh X.Y.Z-beta.N --beta --dry-run --list-package`
- Confirm output summary: branch, channel, version, build id.

## Mutation path
- Update constants and `version.txt`.
- Validate syntax and consistency checks.
- Create commit and tag.
- Push branch and tag.
- Build assets via `build_dist.py`.
- Upload assets to GitHub Release if `gh` is available.

## Postflight evidence
- Record tag, branch, channel.
- Record artifact names and sizes.
- Record `metadata.json` and patch sha256.
