# USB / Wi-Fi evidence — 2026-09-28

See the [Czech report](../../RESULTS-USB-WIFI-MAC-20260928.md) for scope,
firmware identities, deployment, reproduction and limitations.

This export contains completed, allowlisted cases from one Pico 2 W with its
e-paper display attached through the confirmed meter/hub supply path.
`manifest.json` records copied source hashes, redaction and derived counts:

- 114 controlled hardware reset/wake USB returns across three firmware variants;
  70 belong to the new `.usbq1` candidate. Radio boot cases are included once.
- Three additional lightsleep/soft-reset cases, counted separately.
- 54 successful DHCP/exact-HTTP-body transactions, three failed negative
  controls, one requested but unstarted cycle. One seed reused an existing link.
- 16 public-helper calls and nine application-function checks passed. These
  overlap the reset/network cases and must not be counted as extra boots.
- Both host-fixture failures remain visible; neither requested a hardware reset.
- Native C tests reproduce and fix the TinyUSB queue-full bug. This does not
  establish the cause of the earlier physical USB enumeration failures.
- Deployment verified 29 files: 28 original files unchanged, one intentionally
  patched `main.py`; the full application remains stopped in REPL.

`wifi_device.py.txt`, `radio_guard.py.txt` and `helper-source.py.txt` are exact
tested bytes, with matching PASS source hashes. Older cases may identify older
source hashes. The current public helper was formatted before the commit;
`commit-format-checks.json` verifies identical AST and six repeated offline
checks, while the exact hardware-tested copy remains unchanged. Original application source, credentials, flash images, file
inventories, raw backup words and network endpoint configuration are excluded.
Device identifiers, network addresses and private paths were redacted.

`usb-unit-tests/reset-queued-setup-test.patch` is an additional test-only patch
on top of the official queue fix; it was not compiled into the firmware.
The manifest's file table is the initial export snapshot. This README and
the added test reproduction artifacts are covered by `SHA256SUMS`, which
covers every file here except itself.

Verify from this directory with `shasum -a 256 -c SHA256SUMS`.
No new current measurement, display refresh, DNS/TLS transaction or BLE/AP
peer traffic was performed in this investigation.
