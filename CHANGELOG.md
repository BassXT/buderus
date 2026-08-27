# Changelog

## 0.2.0 - 2026-08-27

### Added

- Add cumulative electricity consumption, produced heat, and environmental energy sensors from the PointT energy-monitoring resources.

### Fixed

- Add the reported `cooling`, `heating_auto`, `heating_manual_off`,
  `manual_on_eco`, and `manual_on_high` enum values with English and German
  translations. Fixes #7, #9, and #19.
- Report enum values that are not declared in a sensor description as unknown and
  log them once instead of raising a `ValueError` on every coordinator update.
  Prevents recurrences of #5, #7, #9, and #19.
- Add the missing state translations for heating circuit switch programs A and B.
- Log the underlying SingleKey or gateway validation error during initial setup so
  the generic setup error can be diagnosed without logging the submitted redirect
  URL or authorization code. Helps investigate #6.

## 0.1.3 - 2026-07-15

### Fixed

- Add `off` as a valid heating circuit operation mode and include translations. Fixes #2 via #4.
- Add `cooling_manual_on` as a valid heating circuit overall status via #3.
- Add `summer_idle` as a valid heating circuit overall status. Fixes part of #5.
- Add `auto` as a valid DHW overall status. Fixes part of #5.

## 0.1.2 - 2026-05-25

### Fixed

- Correct DHW Eco and Eco+ labels.
