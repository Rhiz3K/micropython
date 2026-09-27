# Selected macOS evidence, 2026-09-27

These records describe the second test board (`test-board-2`), a Pico 2 W,
using the native ARM macOS experimental build identified in [build.json](build.json),
plus the explicitly identified unmodified baseline for the later raw-REPL Wi-Fi
diagnostic.
They are separate from the original Linux test board and its earlier results.
See [the Mac result record](../../RESULTS-MAC-20260927.md).

The owner clarified that the display is physically connected. The timed-sleep
harness did not operate it. Earlier short/Wi-Fi runs lack reliable evidence of physical
disconnection; the completed 30-minute and 75-minute runs describe the assembly
with the display attached. These records do not establish bare-board operation,
display-driver behavior or current draw. A separate subsequent display test
is exported below.

## Export rules

- `uid` and `usb_serial` are replaced with `test-board-2`.
- Wi-Fi connection addresses and DNS/HTTP destinations are replaced with
  `<redacted-network>`; measured timings, status, RSSI and HTTP codes are retained.
- The two unittest logs replace the local host-mount path with
  `<redacted-local-path>`.
- JSON is reserialized without changing retained non-redacted values. Text uses LF.
- The later diagnostic metadata omits the private original long-sleep log and
  summary hashes; the exported long-sleep JSONL files have redacted identities.
- The selected baseline switch record omits the private snapshot hash and
  scratch-register dump, retaining revision, firmware hash and verification result.
- Full-flash backups, original application files, credentials, manifests and
  complete test configurations are not included. No firmware binary is included.

The eight completed test scenarios include the 30-minute and 75-minute runs
and contain their final PASS records. The original `wifi-ordinary.jsonl` and
`wifi-deep.jsonl` automatic-boot suites end in FAIL after the first reset; their
successful initial HTTP requests are not successful reconnect suites. Both
used the experimental firmware; that ordinary-reset run is not a baseline.

The later `wifi-restart-diagnostic-experimental/` and
`wifi-restart-diagnostic-baseline/` directories each contain events, summary and
metadata for a separate raw-REPL diagnostic with an ordinary `machine.reset()`
between probes and no deepsleep call. Both initial probes passed DHCP, DNS and
HTTP; both second probes failed with status -1 and no observed DHCP address.
The logs confirm actual reset/boot increments and cleanup. The selected
[baseline switch record](baseline-switch.json) identifies the baseline firmware
and filesystem-preservation result. This is a real baseline comparison for
that diagnostic, not a baseline rerun of the automatic-boot suites. Matching
failures do not establish their cause or exclude every possible regression.

The build metadata omits private artifact paths and the stale hardware status
from the build-time manifest. The report records subsequent hardware validation.
The completed [30-minute log](30min.jsonl) and [75-minute log](75min.jsonl) are
included. Their host intervals include boot, USB enumeration and record delivery;
they are not precise LPOSC calibration. This is a selected evidence set, not a
full private work-directory dump.

The [display events](display-test.jsonl) and [result](display-test-result.json)
record two full refreshes around one 5-second alarm boot, followed by verified
removal of the two temporary modules and a stopped REPL. Automatic checks are
PASS. The raw logs retain their original NOT_VERIFIED visual status; the
subsequent [owner confirmation](display-visual-confirmation.json) records PASS
for the readable phase-B text and right-hand rectangle. Phase B was host-invoked
after boot, so this is not an automatic application-startup integration test.
The [restoration result](restoration-result.json) confirms all 29 original file
hashes, restored original main filename, UTC RTC, cleared test backup words
and inactive Wi-Fi. The original app was left stopped on experimental firmware.
These exports omit original-file inventories and contents.
