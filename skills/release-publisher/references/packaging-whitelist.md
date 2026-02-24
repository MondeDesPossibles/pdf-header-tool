# Packaging Whitelist

## Runtime (full zip)
Required baseline:
- `pdf_header.py`
- `version.txt`
- `lancer.bat`
- `app/**/*.py`
- Embedded Python runtime and `site-packages` produced by `build_dist.py`

## Patch (auto-update)
Required baseline:
- `pdf_header.py`
- `version.txt`
- `app/**/*.py`

## Exclusions
Do not include dev-only sources in runtime payload selection logic:
- `.github/`
- roadmap/internal docs
- dev helper prompts/handoffs
- non-runtime scripts
