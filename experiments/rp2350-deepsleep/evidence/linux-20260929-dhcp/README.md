# Linux DHCP follow-up: derived evidence, 2026-09-29

This directory contains explicitly allowlisted observations. Raw private captures remain outside the repository.
These are Wi-Fi reconnect diagnostics, not new deepsleep or power measurements.

Completed capture records: 19. Connection results: {'PASS': 11, 'FAIL': 3}.
Other result categories: {'CONNECTION_RESULT': 14, 'HELPER_LINK_DOWN_PRECONDITION': 3, 'HOST_CAPTURE_PRECONDITION': 1, 'HELPER_COLD_GP23_PRECONDITION': 1}. Pending captures: [].

| Capture | Category | Outcome | Connect elapsed ms | PM preset | Target DHCP frames |
| --- | --- | --- | ---: | --- | ---: |
| 1 | CONNECTION_RESULT | PASS | 3136 | not overridden in recorded event | unavailable |
| 2 | HELPER_LINK_DOWN_PRECONDITION | FAIL | N/A | not overridden in recorded event | unavailable |
| 3 | CONNECTION_RESULT | PASS | 3149 | not overridden in recorded event | 4 |
| 4 | HOST_CAPTURE_PRECONDITION | FAIL | N/A | not overridden in recorded event | unavailable |
| 5 | CONNECTION_RESULT | PASS | 3141 | not overridden in recorded event | 4 |
| 6 | CONNECTION_RESULT | PASS | 3341 | not overridden in recorded event | 4 |
| 7 | CONNECTION_RESULT | PASS | 5037 | not overridden in recorded event | 4 |
| 8 | HELPER_LINK_DOWN_PRECONDITION | FAIL | N/A | not overridden in recorded event | 0 |
| 9 | HELPER_COLD_GP23_PRECONDITION | FAIL | N/A | not overridden in recorded event | 0 |
| 10 | CONNECTION_RESULT | PASS | 32715 | not overridden in recorded event | 4 |
| 11 | CONNECTION_RESULT | PASS | 5044 | not overridden in recorded event | 4 |
| 12 | CONNECTION_RESULT | FAIL | 35002 | performance | 0 |
| 13 | CONNECTION_RESULT | PASS | 3261 | none | 4 |
| 14 | CONNECTION_RESULT | FAIL | 35099 | performance | 2 |
| 15 | CONNECTION_RESULT | FAIL | 35091 | none | 6 |
| 16 | CONNECTION_RESULT | PASS | 4833 | performance | 4 |
| 17 | CONNECTION_RESULT | PASS | 32899 | none | 4 |
| 18 | CONNECTION_RESULT | PASS | 3121 | performance | 4 |
| 19 | HELPER_LINK_DOWN_PRECONDITION | FAIL | N/A | not overridden in recorded event | 0 |

## Method and limits

- `events.jsonl` preserves host receive times and numeric telemetry while dropping IP addresses and source labels. XIDs have an additional unsigned 32-bit representation.
- `summary.json` includes parsed DHCP message order/times/checksum results, matching RAM XIDs, and allowlisted router registration observations. Registration presence/absence is distinct from DHCP success.
- The private generation script reconstructs saved RouterOS hex-wrapped ASCII packet dumps through the reviewed parser, expands repeated lines, verifies IP/UDP checksums and cross-checks the same frozen packet metadata.
- Empty frame exports are valid empty capture snapshots, not corrupt packet dumps. No checksum result is claimed for them. Capture 1 has no usable saved packet export.
- Capture 2/8/19 failed the helper link-down precondition, capture 9 failed the cold GPIO23 precondition, and capture 4 failed a host capture precondition. No completed DHCP attempt is inferred for those runs.
- Capture 10 eventually connected at 32715 ms after repeated driver BADAUTH-kind samples coexisted with netif LINK_UP. Its DORA span is 18 ms; the much longer connection delay is a separate quantity.
- Capture 15 failed after 35091 ms despite a router-side DISCOVER/OFFER/REQUEST/ACK/REQUEST/ACK sequence; an observed ACK does not establish client acceptance.
- Capture 12 ran for 35002 ms and failed, with zero target frames and intermittent router registrations. Packet absence alone cannot locate the loss.
- Capture 19 stopped in the helper before PM_NONE was configured; it is not a fourth PM_NONE attempt. Its shutdown samples show netif LINK_UP clearing while the driver reports BADAUTH, revealing an overly strict status==0 helper condition.
- The three cold-helper snapshots and three ordinary reset results are preserved independently. They are not physical power cycles.
- `elf-layout.json` reproduces safe GDB expressions/struct layout only. Never apply its addresses to a different ELF. Reads can straddle callbacks; DHCP request_timeout units are 500 ms.
- `source-hashes.json` identifies private source files by SHA-256 for controlled auditing. It does not make the raw captures public or independently prove observations.
- The historical private-parser result in `summary.json` describes 11 tests on saved private fixtures. The separately executed current public-tool suite has 18 PASS tests in [public-parser-tests.txt](public-parser-tests.txt). Neither is a fresh hardware test.
- No current or energy measurement was made. PM_NONE must not be presented as a proven fix from this small sequential series.

## Exact device probe fragments

`probe-pm-source.py.txt` and `probe-shutdown-observer.py.txt` are extracted by
Python AST/literal_eval from the executed private host script. They contain no
credentials or endpoint. This actual probe streamed records approximately once
per second (and on state changes); it did not buffer all records until the end.

Before evaluating hardcoded RAM reads, execute the mandatory exact-BIN guard
in `probe-bin-guard.py.txt` (889792 bytes at XIP base, SHA-256 shown in that file).
A different build must use layout regenerated from its matching ELF. The guard
is a derived standalone equivalent of the private host's incremental readback
check with an added exact model/platform check before any XIP memory read.
This standalone guard fragment was not executed as-is in the recorded run.

The probe also requires `machine`, `network`, `time`, `json`, the historical
radio helper and `_wifi_http` from the pre-existing
[wifi_device.py.txt](../mac-20260928-usb-wifi/wifi_device.py.txt) experiment script.
`probe-helper-instrumentation.py.txt` contains the exact four host-side source
transformations applied to that helper. Append/evaluate the shutdown observer,
set `_preset` to `performance` or `none`, then define the PM source and invoke
`_diag_connect` with privately supplied credentials, endpoint and run label.
Later helper fixes are distinct from the historical helper used for these runs.
The source emits private addresses at runtime; never publish its raw output.

`probe-shutdown-fix-source.py.txt` is the exact AST-extracted literal executed
after connection in the supplemental shutdown-fix1 run. It also requires the
mandatory model/BIN guard before its hardcoded `machine.mem32` read, the probe
definitions above and the final fixed helper. For this run use
[probe-helper-fixed-instrumentation.py.txt](probe-helper-fixed-instrumentation.py.txt),
the four exact assignments from the final-helper host script: its poll insertion
matches `if sta.status() <= 0`. The historical instrumentation matches `== 0`
and cannot supply equivalent poll observations for the final helper.
Its 10-second observation loop uses `_deadline` and `_bad`; no synthetic wait
or successful result is added.

## Subsequent helper fixes and cleanup

`helper-regressions.json` preserves the portable cold-boot regression before
(GPIO23 mux precondition FAIL), after the GPIO fix (PASS), and with the final
helper (PASS). It includes two additional ordinary resets, for five total.

`shutdown-fix1-events.jsonl` preserves one separate connection (DHCP/HTTP PASS
at 3221 ms), an actual BADAUTH-kind/link-up target state, then helper shutdown
with link-down/BADAUTH and verified low radio pins. The fixed helper accepts a
non-connected error status after link-down rather than requiring exactly zero.
Capture 19's old-helper failure remains unchanged. This fixes the shutdown
helper's false failure; it does not fix or prove the cause of DHCP instability.
No router packet capture was taken during this supplemental connection.

There were 15 actual connection results across both phases: 12 PASS, 3 FAIL.
The main capture table remains the original 14 connection results (11 PASS, 3 FAIL).
The explicit PM A/B subset contains seven configured attempts: four performance and three none.
The final state records firmware hash, 37 unchanged filesystem files, restored
backup regions, elapsed RTC verification, usable friendly REPL and low radio
pins. No flash write or firmware reflash was performed. Display operation and
panel sleep were not verified; these are not current measurements.
