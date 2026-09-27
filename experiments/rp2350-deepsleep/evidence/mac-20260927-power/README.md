# JT-UM120 power evidence, second Pico 2 W, 2026-09-27

See the [measurement report](../../POWER-MAC-20260927.md) for scope, wiring,
results and limitations. All measurements include the attached e-paper module,
with Wi-Fi deinitialized and the panel asleep, at the assembly's USB input.

## Included evidence

- `measurement-plan.json`: final scope, firmware identity, private script hashes
  and completion status. `plan_recorded_utc` is the time the plan record was
  written during acquisition, not the start of acquisition.
- `short-analysis.json`: three 45-second runs of each of four modes, with
  independent raw-frame validation and 5–40-second analysis windows.
- `long-analysis.json`, `long-device-result.json`: one 300-second deepsleep,
  including early 5–40-second and late 235–295-second windows and wake checks.
- `device-events.jsonl`, `long-device-events.jsonl`: host/device events;
  the physical board UID is replaced with `test-board-2`.
- `*-trace-1s.csv`: one-second summaries of all acquisition samples, grouped
  by host receipt time. These summaries do not replace the full-resolution
  samples used for the analyses. Power is computed per sample as voltage ×
  current before averaging; cycle energy was not integrated.
- PNG/SVG plots: short comparison/timeline and the 300-second sleep timeline.
- `restoration-result.json`: all 29 original files verified against the fresh
  pre-measurement backup, original main restored, temporary test files removed,
  backup registers and UTC restored. The application is stopped in REPL.
  `/main.py` in `temporary_files_removed` denotes the temporary guard main;
  the original main was subsequently restored to that same path.
- `no-load-attempt.json`: optional reference capture failed because Pico USB
  removal was not observed before its deadline. No no-load reference was
  obtained in that first attempt. This is separate from the passing sleep tests.
- `no-load-reference.json`: the later capture obtained a valid fixed 15-second
  window after owner-confirmed Pico-only disconnection: 0.05541 mA mean.
  The complete capture later ended with a HID read error; its failed status
  is retained and its USB return timestamp is unavailable. The selected window
  ends 15.48 seconds before that error. No reference value was subtracted.
- `SHA256SUMS`: hashes of these exported files, excluding the checksum file itself.

## Interpretation and privacy

The current falls during the short windows in all modes; no steady-state
assumption is made. The late long-sleep result is a separate window from a
single longer run. A later no-load indication is recorded, but its physical
cause was not established and it is not a calibration. Current of individual
components and full Wi-Fi/display application-cycle energy remain unmeasured.

Four ordered samples share each frame's host receipt timestamp. CRC and receipt
continuity were checked, but device timestamps and exact dropped-sample counts
are unknown. No zero/outlier filtering or reference subtraction was performed.
Advertised resolution/accuracy are not an independent calibration.

Complete raw HID frames, samples, scripts, original file inventories and backups
remain in the private working directory. Hashes inside analysis/provenance JSON
refer to those original local artifacts; they are not hashes of redacted exports.
`SHA256SUMS` separately identifies the exported bytes. This export omits physical
device identifiers, original application contents, credentials, network
configuration and full-flash images. It is a selected evidence package, not a
self-contained reproduction of the private measurement setup.
