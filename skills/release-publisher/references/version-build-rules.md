# Version and Build Rules

## Version format
- Stable: `X.Y.Z` (or `X.Y.Z.W`)
- Beta: `X.Y.Z-beta.N`

## Build format
- `build-YYYY.MM.DD.NN`
- Build id must match in:
  - `pdf_header.py` (`BUILD_ID`)
  - `build_dist.py` (`BUILD_ID`)

## Consistency constraints
- `version.txt` must match `pdf_header.py` `VERSION`.
- `pdf_header.py` `CHANNEL` must align with stable/beta mode.
- Inconsistency must fail release preflight.
