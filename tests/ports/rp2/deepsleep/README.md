# RP2350 timed deep-sleep hardware tests

These opt-in tests run outside the normal test runner. They replace `main.py`,
reset the board repeatedly, change its RTC and overwrite its backup registers.
They never flash firmware or measure power. Preserve the original firmware,
filesystem, RTC and backup-register data before installation, and verify that
BOOTSEL recovery is available.

The sibling `../rp2_deepsleep_args.py` runs under the normal test runner. It skips
RP2040, RISC-V and firmware without `DEEPSLEEP_RESET` before making any sleep
call. It checks invalid arguments and EBUSY in an actual hard Timer callback,
using a zero-duration call so a regressed IRQ guard can only take the ordinary
reset path. Correct behavior neither sleeps nor resets; a guard regression can
reset the board and fail the test transport. Positive-duration IRQ rejection is
covered by the opt-in suite instead. Neither test arms a watchdog for this check.

The device keeps progress in the eight POWMAN scratch words,
`machine.mem_backup(2)`, without writing flash per cycle. Each alarm boot checks
`DEEPSLEEP_RESET`, RTC progress, a filesystem sentinel and POWMAN retention.
Watchdog scratch retention is reported separately; SWCORE power-down can lose
those words. An ordinary reset at the end must clear `DEEPSLEEP_RESET`.

## Installation and observation

Use an identified, backed-up RP2350 board with a suitable `boot.py` that does not
activate peripherals needed by another application. Stop other serial clients.
The tests do not change `boot.py`, flash firmware or restore saved application
files automatically. Keep the manifest, backups, credentials and logs private.

The host requires CPython and `pyserial`; installation also uses this
repository's `tools/pyboard.py`:

```sh
python3 -m venv /tmp/rp2350-hwtest
/tmp/rp2350-hwtest/bin/pip install pyserial
T=tests/ports/rp2/deepsleep
/tmp/rp2350-hwtest/bin/python "$T/host.py" list
```

Create a manifest for the actual board and independently verified backups:

```json
{
  "authorized": true,
  "bootsel_recovery_confirmed": true,
  "usb_serial": "REPLACE",
  "unique_id": "REPLACE_WITH_machine.unique_id_HEX",
  "machine_contains": "Raspberry Pi Pico 2 W with RP2350",
  "firmware_backup": {"path": "original-firmware.bin", "sha256": "REPLACE"},
  "filesystem_backup": {"path": "original-filesystem.tar", "sha256": "REPLACE"}
}
```

Backup paths are relative to the manifest. The installer verifies the hashes,
selects the USB serial and checks `machine.unique_id()` and the board description
before writing. A hash alone does not establish that a backup belongs to the
board. A UF2 firmware image is not a filesystem backup.

Example `config.json`:

```json
{
  "run": "pico2w-arm-100",
  "cycles": 100,
  "sleep_ms": 2500,
  "expect_deep_cause": true
}
```

```sh
/tmp/rp2350-hwtest/bin/python "$T/host.py" install \
  --manifest private/manifest.json --config private/config.json --allow-write
/tmp/rp2350-hwtest/bin/python "$T/host.py" run \
  --manifest private/manifest.json --config private/config.json \
  --allow-run --log private/100-cycles.jsonl
```

An existing `main.py` requires `--replace-main`; its exact contents are saved next
to the manifest. This supplements the complete backup. `sleep_ms` must be an
integer in `0..2147483647`; zero and one require `expect_deep_cause: false` because
these request ordinary resets. Use a new run name and log for each independent
installation. The log is created exclusively and is never overwritten.

## Reset-spanning protocol

Protocol 2 repeats each READY and SLEEP record until the host acknowledges the
specific run name, boot number and status. The board stays awake while waiting;
a connected host is required. The observer selects the USB serial on reconnect
and checks the unique ID. It does not soft-reset the running test.

Pass the same `--config` to both commands. The host then requires the initial
READY, a successfully acknowledged SLEEP before each wake, consecutive boot and
cycle counts, exactly the configured number of cycles, and the final ordinary
reset. It rejects partial observations, skipped phases and stale acknowledgements.
Omitting `--config` allows legacy observation without complete-run checks.

Malformed or truncated records are logged without acknowledging them or extending
the per-boot timeout. FAIL remains fatal. A timeout or missing final PASS is an
incomplete or failed run. The device repeats a failure until Ctrl-C returns to
REPL. An interrupted, already consumed wake fails instead of being counted twice.

The first sleep sets RTC to `2026-09-25 23:59:58`, after all host waiting, to cross
midnight. Whole-second RTC observations do not establish oscillator accuracy.
For long sleeps, set and report `rtc_tolerance_s` and `host_tolerance_s`. The host
lower-bound check measures SLEEP acknowledgement to the next READY, including
boot, USB enumeration and network setup. Its default tolerance is the larger of
0.25 seconds and 10% of the requested sleep, a test threshold rather than an
accuracy claim. Boot overhead can mask an early wake. `--timeout` must exceed the
requested sleep plus boot and optional network setup.

## Optional scenarios

Use a separate installation, configuration and log for each scenario:

- `thread: true`: reject calls from CPU1 and from CPU0 while CPU1 is active with
  `OSError(EBUSY)`, then complete the timed cycles after the thread exits.
- `watchdog: true`: reject deep sleep while an active watchdog keeps counting,
  then require `WDT_RESET`. This scenario completes zero deep-sleep cycles.
- `watchdog: true, watchdog_after_reset: true`: additionally require a TIMER
  watchdog reset and cleared expired ENABLE bit, then complete the configured
  deep-sleep cycles without rearming the watchdog. It requires mode `deepsleep`,
  `sleep_ms >= 2` and `expect_deep_cause: true`.
- `dma: true`: leave a fixed-address RAM copy active until deep-sleep teardown.
  No peripheral pins or flash addresses are used.
- `lightsleep_before: true`: call `lightsleep(20)` before each deep sleep.
- A single 30- or 75-minute cycle: use `sleep_ms` of 1800000 or 4500000 with an
  appropriate per-boot timeout and explicit RTC/host tolerances.

For the first application boot after UF2 installation, stage a one-cycle 2500 ms
configuration with `install --no-reset`. This synchronizes the test files without
starting them or calling `machine.reset()`. Install the exact verified UF2 through
BOOTSEL while preserving the filesystem, then observe its first normal boot.
Do not issue Ctrl-D or another reset before that first deep sleep. Record the
firmware hash, READY cause and watchdog registers. A TIMER reason establishes
watchdog-timeout recovery; a different reason tests first-boot sleep only.
BOOTSEL can affect RTC continuity and is a separate transition. This scenario
does not test a live watchdog inherited from boot ROM.

Run `regressions.py` explicitly with `mpremote ... run` on a stopped suite. It
checks invalid duration arguments, hard-IRQ rejection and lightsleep clock/time
restoration. Its RP2350 and `DEEPSLEEP_RESET` guard prevents the negative-delay
calls from entering a very long sleep on baseline firmware. Test zero/one through
separate reset-spanning configurations. Test no-argument `machine.deepsleep()`
separately with external recovery arranged; no timed wake is promised.

## Radio and comparison profiles

`radio` optionally selects `never`, `sta`, `ap`, `ble`, `sta_ble` or `sta_ap` on
Pico 2 W. The suite rejects radio interfaces already active at boot. Each alarm
boot initializes the profile again and leaves it active for firmware teardown.
`never` avoids importing either radio module. BLE has no peer traffic; AP checks
its firmware link state but does not establish a client's association.

AP profiles require a private `ap` object with an SSID starting with
`rp2350-sleep-test` and a WPA2 password of 8–63 printable ASCII characters. They
configure WPA2-AES-PSK while inactive and never start an open/default AP. A `wifi`
transaction is allowed only with `sta` or `sta_ble` when `radio` is specified:

```json
"wifi": {
  "ssid": "TEST_AP",
  "password": "PRIVATE",
  "host": "test-server.example",
  "dns_host": "test-server.example",
  "port": 80,
  "path": "/health"
}
```

Use an operator-controlled HTTP endpoint returning 200. The suite tests DHCP,
DNS and HTTP, with a bounded connection timeout and no automatic retry. The
private configuration contains credentials and must be removed or restored
exactly after the run. Result records omit passwords but can contain identities,
network addresses and names; review them before sharing.

`mode: "sleep_reset"` calls `time.sleep_ms()` then resets.
`mode: "lightsleep_reset"` repeats lightsleep until bounded deadlines expire,
then resets. Each lightsleep request is at most 60000 ms, permitting long totals
beyond the RP2 timer's single-alarm limit and handling ticks wrap. Both comparison
modes require `expect_deep_cause: false`. The default `deepsleep` mode exercises
the implementation under test.

Functional PASS, raw POWMAN status and GPIO snapshots do not measure current or
prove every power domain's state. Startup may change GPIOs before Python runs.
Compare firmware using the same board, supply, peripheral and USB/debugger setup;
measure without USB data and with the debugger disconnected separately. Record
sleep current separately from energy over a full application cycle. The host
handshake adds variable awake waiting, and mounted USB can affect lightsleep.

## Offline checks and restoration

These CPython checks use simulated clocks, transport and device state, without
opening a serial device or running the hardware suite:

```sh
python3 -m unittest discover -s tests/ports/rp2/deepsleep -p 'test_*.py'
```

They test acknowledgement and reset sequencing, malformed/reconnected transport,
watchdog bookkeeping, and deadline handling under early wakes, ticks wrap and
long durations. They are not hardware evidence.

After testing, restore the exact saved application files, RTC and backup-register
contents, and restore firmware if required for the intended final state. Do not
indiscriminately remove files by prefix. Retain firmware/tool revisions, backup
hashes, logs and the actual PASS/FAIL/NOT RUN results separately from these tests.
