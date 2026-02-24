# Release & Update Invariants

## Must Keep Stable
- `release.sh` edits `pdf_header.py` constants via `sed`.
- `version.txt` must match release intent.
- `build_dist.py` must package patch files needed by moved code (`app/**/*.py` when modularized).
- `metadata.json` patch name/hash/size must match generated patch zip.

## Startup/Update Ordering
- Apply pending update before heavy imports/UI startup.
- Keep update checks non-blocking at runtime.

## Validation Checks
- Confirm constants in `pdf_header.py` remain present and editable.
- Confirm patch zip includes newly introduced modules.
- Confirm metadata points to existing patch zip with matching sha256.
- Smoke startup through `run_dev.sh` and inspect logs.
