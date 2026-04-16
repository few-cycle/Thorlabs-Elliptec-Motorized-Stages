# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-04-15

### Added

- Shared serial transport layer and protocol helpers in `ElliptecBus`.
- Shared architecture/mixins in `ElliptecBase` for discovery, status, motion, and unit conversion.
- Family-level bases for:
  - rotary stages (`ElliptecRotaryStages`)
  - linear stages (`ElliptecLinearStages`)
  - multi-position sliders (`ElliptecMultiPositionSlider`)
  - iris modules (`ElliptecMotorized_IRIS`)
- Device wrappers for:
  - Rotary: `ELL14`, `ELL16`, `ELL18`, `ELL21`
  - Linear: `ELL17`, `ELL20`
  - Slider: `ELL6`, `ELL6B`, `ELL9`, `ELL12`
  - Iris: `ELL15`, `ELL15Z`
- ELL16 bench validation CLI script: `ell16_bench_test.py`.
- Project documentation scaffold for Sphinx + Read the Docs:
  - `docs/` structure
  - API reference pages via autodoc
  - `.readthedocs.yaml`
  - `requirements-docs.txt`
- Public project metadata/documentation files:
  - `README.md`
  - `LICENSE` (Apache-2.0)

### Changed

- Refactored duplicated protocol/motion logic into reusable base layers.
- Standardized docstring style across core modules and family packages.
- Renamed iris package directory to import-safe name: `ElliptecMotorized_IRIS`.

### Notes

- This is the first documented public baseline for the project.
