# Architecture Map

## Current Structure
- Entry point: `pdf_header.py`
- App package: `app/`
- UI modules: `app/ui/`
- Services: `app/services/`
- Update system: `app/update.py`
- Build/packaging: `build_dist.py`
- Dev/runtime scripts: `run_dev.sh`, `release.sh`

## Ownership Guidance
- `pdf_header.py`: startup orchestration, version/build/channel constants, app launch flow.
- `app/runtime.py`: bootstrap checks, logger setup, exception hook, runtime metadata.
- `app/ui/main_window.py`: app lifecycle, preview/render/apply orchestration.
- `app/ui/sidebar.py`: sidebar construction and option callbacks.
- `app/ui/file_panel.py`: right panel list/cards/counters.
- `app/services/*`: pure/near-pure domain logic for fonts/layout/pdf insertion.
- `app/update.py`: update check/download/staging/apply flow (avoid non-blocking regressions).

## Coupling Hotspots
- Startup ordering across `pdf_header.py`, `app/runtime.py`, `app/update.py`.
- Logger/profile behavior spanning runtime and UI modules.
- Font/layout/pdf service contracts used by `PDFHeaderApp`.
- Patch packaging expectations in `build_dist.py` consumed by update logic.
