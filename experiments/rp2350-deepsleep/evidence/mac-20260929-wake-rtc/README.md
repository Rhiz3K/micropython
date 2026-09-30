# RP2350 wake/RTC and power evidence — 2026-09-29

The adjacent report explains the fixture and limits. All six attempts are retained: two PASS and four FAIL. The corrected deep experiment requires retention of POWMAN region 2; all three original regions were restored afterwards.

`restoration-deep2.json` is the actual final restoration. `restoration.json` is an earlier intermediate restoration.

`SHA256SUMS` verifies the 54 sanitized exported files. `figures/SHA256SUMS` verifies the final plot, CSV and provenance. `BUNDLE-SHA256SUMS` verifies every file in this repository bundle except itself.

Raw HID frames, device/application files, identities and credentials remain private. Exported raw hashes were declared by the analyzers; complete CRC/sample and numerical replays were independently verified locally. The figure compares two actual cycles per profile; it does not provide an upstream result, a confidence interval or an absolute meter calibration.
