# Version and Build Rules

## Version format
- Stable: `X.Y.Z` (or `X.Y.Z.W`)
- Beta: `X.Y.Z-beta.N`
- Beta bugfix after a published beta MUST increment `N` on the same base version
  (example: `0.4.7-beta.1` -> `0.4.7-beta.2`).
- Branch naming for beta bugfix MUST be `fix/vX.Y.Z-beta.N`
  (example: `fix/v0.4.7-beta.2`).

## Build format
- `build-YYYY.MM.DD.NN`
- Build id must match in:
  - `pdf_header.py` (`BUILD_ID`)
  - `build_dist.py` (`BUILD_ID`)
  - `lancer.bat` (`set "BUILD_ID=..."`, source du log de lancement Windows)

## Consistency constraints
- `version.txt` must match `pdf_header.py` `VERSION`.
- `pdf_header.py` `CHANNEL` must align with stable/beta mode.
- Inconsistency must fail release preflight.
