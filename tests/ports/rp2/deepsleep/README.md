# RP2350 timed deepsleep hardware checks (opt-in)

These scripts are **prepared hardware tests, not evidence that tests passed**.
They are outside the normal test runner because they replace a board's `main.py`,
reset it repeatedly, change its RTC and overwrite all user backup registers.
They do not flash firmware, measure current or prove a power-domain transition.
Record actual results against exact firmware and SDK revisions separately.

`device.py` runs independently on each boot. It stores cycle progress in the
eight POWMAN scratch words (`machine.mem_backup(2)`), never in flash. A sentinel
file and the program/configuration are written only at installation. The device
temporarily owns these eight words as application test data; the firmware must
not reserve or overwrite any of them for wake markers or diagnostics.
The device repeats a JSON boot result until the host acknowledges it; USB re-enumeration
therefore cannot silently lose a successful cycle. The host never soft-resets a
running test. A test failure repeats its JSON result until Ctrl-C returns to REPL,
so failures before USB enumeration are also observable.

The suite requires the RP2350 `machine.mem_backup` regions and tests their
advertised layout. It observes, but does not require, retention of watchdog
scratch regions 0 and 1: a SWCORE power-down may lose those regions. The suite
requires POWMAN retention. On an unmodified baseline use `expect_deep_cause:
false`; on a patch use `true` to require `machine.DEEPSLEEP_RESET` for each timed
wake. After the requested cycles, an ordinary `machine.reset()` must clear this
cause. A fresh `main.py` invocation, successful USB exchange, file sentinel,
RTC observation and optional Wi-Fi transaction are checked after each wake.
Boot records also include read-only raw `POWMAN_CHIP_RESET` and
`POWMAN_LAST_SWCORE_PWRUP` values, using offsets from the pinned SDK's RP2350
register headers. Firmware startup may already have cleared reset flags; these
values must be interpreted with that firmware's reset-cause handling. They do
not independently prove the state of every power domain or its current draw.

## Identify, authorize and back up first

Do not infer permission from finding a connected serial port. Record the board
model, RP2350 stepping if available, ARM/RISC-V build, device unique ID, USB
serial number, firmware SHA-256 and revision, and the owner's permission.
Back up the current firmware and complete filesystem **before installing or
flashing anything**. Validate backup readability and checksums. Save any useful
backup-register data separately: these tests intentionally overwrite it.

BOOTSEL recovery must be available: hold BOOTSEL while connecting USB (or use
an appropriate documented reset procedure), identify that board's boot volume,
then copy a known-good firmware UF2 for that board. A UF2 firmware image alone
is not a filesystem backup. A separate filesystem restore may be needed.
Stop other serial clients and disconnect the debugger for power tests.

Example manifest (all values must describe the actual identified board):

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

Paths are relative to the manifest. The host verifies hashes, matches the USB
serial before opening a port, then checks the unique ID and board description
before installation. A matching serial is used on every reconnect, followed by
the unique ID reported by the freshly booted program. This does not establish
that a backup represents the board; that provenance is the operator's duty.
`list` only enumerates USB metadata; it does not open a serial port.

## Install once, then observe

Use a private directory for the manifest, backups, credentials and logs. Install
CPython `pyserial`; the installer uses this repository's `tools/pyboard.py`.

```sh
python3 -m venv /tmp/rp2350-hwtest
/tmp/rp2350-hwtest/bin/pip install pyserial
T=tests/ports/rp2/deepsleep
/tmp/rp2350-hwtest/bin/python "$T/host.py" list
```

Example `config.json`:

```json
{
  "run": "pico2w-arm-patch-100",
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

An existing `main.py` is refused unless `--replace-main` is also given; its exact
contents are saved next to the manifest. This supplements the full backup.
An existing `boot.py` still executes and may interfere with the test: inspect it
and arrange a suitable test filesystem rather than silently modifying it.
Install validates arguments before writing. Zero and 1 ms are accepted only
with `expect_deep_cause: false`, since they request ordinary immediate resets.
The first sleep sets RTC to 2026-09-25
23:59:58 so the series crosses both a minute and midnight. Inspect the logged
before/after RTC times; host-controlled waiting also advances RTC. Coarse
whole-second RTC checks do not measure oscillator accuracy. For long sleeps
set `rtc_tolerance_s` explicitly and report the host/RTC difference, rather
than assuming LPOSC has crystal accuracy.

The log is created exclusively, with no overwriting of an earlier run. A timeout
or missing final `PASS` is incomplete/failed, never a successful test. The
timeout is per boot; set it longer than the requested sleep plus boot and network
setup. A PASS means only the implemented checks passed; it is not a current or
power-domain measurement. The final normal reset leaves the suite stopped.

Pass the same private `--config` to `run` as to `install`. Before sending any
GO, the host then rejects a different run name or radio mode, and accepts final
PASS only with exactly the configured cycle count (zero for the watchdog
rejection case). The configuration and its credentials are not written to the
host log. Omitting this optional argument retains legacy observation behavior
without these expected-run checks.

## Scenarios and initially unexecuted results

Each independent run requires a distinct run name/configuration/log and a new
installation to reset its scratch state. Installation writes are per run, not
per cycle. Preserve the complete logs and firmware hashes.

| Scenario | Configuration / command | Initial result |
| --- | --- | --- |
| 100 short resets, RTC, file, POWMAN, USB, reset cause | Default above | NOT RUN |
| Watchdog scratch retention | Reported independently in each wake record | NOT RUN |
| Active CPU1 and caller on CPU1 | Add `"thread": true`; expects `OSError(EBUSY)` then successful deep sleep after CPU1 exits | NOT RUN |
| Active watchdog | `"watchdog": true, "cycles": 1`; rejection must leave watchdog running and reboot with `WDT_RESET` | NOT RUN |
| Active DMA | Add `"dma": true`; a fixed-address RAM copy must be stopped by deep-sleep teardown | NOT RUN |
| Lightsleep immediately before deep sleep | Add `"lightsleep_before": true`; calls `lightsleep(20)` before every deep sleep | NOT RUN |
| Wi-Fi, DHCP, DNS, HTTP, repeated reconnect | Add Wi-Fi configuration below | NOT RUN |
| 30 minutes | `"cycles": 1, "sleep_ms": 1800000`, `--timeout 1920` | NOT RUN |
| Beyond 72 minutes (75 minutes) | `"cycles": 1, "sleep_ms": 4500000`, `--timeout 4620` | NOT RUN |
| Negative/overflow arguments, hard IRQ rejection, lightsleep clock/time | Explicitly run `regressions.py` on a stopped suite | NOT RUN |
| Zero and 1 ms | Separate suite runs with `"sleep_ms": 0` / `1`, `"cycles": 1`, `"expect_deep_cause": false` | NOT RUN |
| No argument | Run separately with manual recovery; no timed wake is promised | NOT RUN |
| Existing lightsleep tests | Run repository `rp2_lightsleep*.py`, `rp2_machine_idle.py`, `machine_rtc_sleep.py` against both builds | NOT RUN |
| Measured sleep current and complete cycle energy | External instrumentation; see below | NOT RUN |

The CPU1/watchdog cases deliberately expect rejection in this initial patch.
They are not evidence of automatic shutdown of an active second Python thread
or continued watchdog protection during a deep sleep. A fresh boot caused by
an unexpectedly accepted CPU1 call is a failure, not a completed cycle.
The scripts compare `OSError` to errno 16 when `errno.EBUSY` is not exported by
the RP2 Python module; 16 is `MP_EBUSY` in `py/mperrno.h`.

Wi-Fi configuration uses an operator-approved, controlled HTTP endpoint that
returns `200`, to make DHCP/DNS/HTTP repeatable. Do not use a public site as a
load target. The network remains active when `deepsleep` is called.
Optional `dns_host` selects a separate DNS lookup name (default: `host`), so
HTTP can target a controlled local server by IP while still testing DNS.
The log records DNS and HTTP addresses separately, without Wi-Fi credentials.
`connect_timeout_ms` optionally changes the 30-second connection/DHCP timeout
(maximum ten minutes). A timeout reports `wlan.status()`; a successful connection
reports elapsed milliseconds, status and RSSI when supported. The test does not
retry a failed connection automatically.

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

Run `regressions.py` explicitly using `mpremote ... run`, then recheck the
device identity after any reset. It checks `ValueError` for `-1` and
`-2147483647`, integer conversion `OverflowError` at/below `-2147483648` and
at/above `2147483648`, and
`OSError(EBUSY)` from an actual hard Timer callback. Zero/1 ms use their own
reset-spanning suite configurations above. Test `machine.deepsleep()` last: it uses the
legacy non-timed path and needs an externally arranged wake or recovery.
The no-argument case is manual because it can hang until an external event.
`1 << 100` must fail integer conversion; the tool does not
start a multi-day sleep merely to test the maximum accepted duration.
The MPZ integer converter accepts magnitudes up to `2147483647`, so even the
signed 32-bit minimum fails conversion before duration validation. A strict
`expect_deep_cause: true` test can fail for a very short positive delay whose
deadline expires during teardown; that ordinary-reset outcome must be recorded
as such, not presented as a successful power-down.

## Comparison and power measurements

Use the same board, supply, Wi-Fi state, peripherals, flash contents, USB and
debugger arrangement for all measurements. Test Pico 2 separately from Pico 2 W;
do not infer chip current from a whole-board reading.

* A: `"mode": "sleep_reset", "expect_deep_cause": false` calls `time.sleep_ms`
  then resets to provide a comparable complete cycle.
* B: `"mode": "lightsleep_reset", "expect_deep_cause": false` calls lightsleep
  then reset; also run baseline firmware's `"mode": "deepsleep"` with the same
  expectation to record its actual existing behavior.
* C: `"mode": "deepsleep", "expect_deep_cause": true` runs the new implementation.

### Pico 2 W radio initialization across alarm boots

The optional `radio` field selects an isolated radio profile on Raspberry Pi
Pico 2 W. Start each profile as a separate run with a new log. Use a clean
`boot.py` that does not initialize a radio; an active STA/AP/BLE found during
preparation fails the test rather than being silently shut down. The final
ordinary reset still checks that `DEEPSLEEP_RESET` does not remain stale.

| `radio` | State left active when calling `deepsleep` | Initial result |
| --- | --- | --- |
| `never` | Neither network nor Bluetooth imported/initialized by this suite | NOT RUN |
| `sta` | STA driver, without association unless `wifi` is configured | NOT RUN |
| `ap` | Only the configured WPA2 test AP | NOT RUN |
| `ble` | Only `BLE.active(True)`, without advertising, scanning or a peer | NOT RUN |
| `sta_ble` | STA driver and BLE together | NOT RUN |
| `sta_ap` | STA driver and the configured WPA2 AP together | NOT RUN |

For example, run `never` for ten 2500ms cycles, then each isolated active
profile for five cycles before testing combinations:

```json
{
  "run": "pico2w-core-cs-low-sta-5",
  "cycles": 5,
  "sleep_ms": 2500,
  "expect_deep_cause": true,
  "radio": "sta"
}
```

After each alarm boot the suite initializes the requested profile again,
checks the STA/AP/BLE active flags, and leaves those interfaces active for
firmware teardown. It keeps the objects alive until sleep. There is no Python
radio deinit or GP25 preparation helper. `never` avoids importing either radio
module; it cannot establish whether an earlier `boot.py` activated hardware.
These checks exercise radio initialization APIs across resets. STA without a
Wi-Fi transaction checks the requested API state, not a working connection.
No peer traffic or preserved network/BLE connection is established by these
checks, and no BLE advertisement or scan is started.

AP modes require this additional object in the **private** configuration:

```json
"ap": {
  "ssid": "rp2350-sleep-test-example",
  "password": "REPLACE_IN_PRIVATE_CONFIG"
}
```

The SSID must start with `rp2350-sleep-test` and fit 32 UTF-8 bytes. Supply a
private WPA2 password of 8–63 printable ASCII characters. The host validates
these fields before writing to the board; the device validates again before
activation. Security is explicitly WPA2-AES-PSK (`0x00400004`, from the pinned
CYW43 driver), configured while the AP is inactive and checked after activation.
The suite also waits at most ten seconds for `ap.status() == 3`
(`CYW43_LINK_UP`), then requires it in subsequent radio records. On this port
that requires the firmware AP link event, an up netif and its IP, rather than
only the cached `active()` flag. It still does not test a client's association
or over-the-air password authentication.
No default/open AP is permitted. AP operation emits beacons, but no client is
needed or tested. SSID/password are not included in result records. The private
configuration on flash contains the credentials and must be restored/removed
as part of the operator's exact filesystem restoration.

Reuse the existing `wifi` object for DHCP/DNS/HTTP only with `radio: "sta"` or
`"sta_ble"`. Omitting `radio` retains the original Wi-Fi suite behavior. A failed
connection is still a failure; no retry is added. Without a successful Wi-Fi
transaction, `connection_proven` remains false even if a driver is active.

Radio runs record read-only GP23/25/29 register snapshots: `pins_at_boot` before
radio-module imports, `pins_after_radio` after initialization, and
`pins_before_sleep` in the SLEEP record. Fields contain GPIO control/status,
pad configuration, and SIO output/output-enable values. They are non-atomic
diagnostics, not assertions of a pin's sleep state. **ROM/runtime startup may
change GP25 before Python runs; a post-boot LOW or HIGH cannot prove the level
held during P1.7.** The suite does not write GP25, GP29 or display pins.

To evaluate automatic core preparation, compare old/new firmware using the
same radio profile and attached, separately prepared display. A separate
operator-controlled measurement may establish GP25 HIGH immediately before
entry; do not call the board LOW helper in that comparison. Use external
current/pin evidence during sleep and the reset-spanning functional results
together. A functional PASS here is not a measured current reduction. The
existing 0ms/1ms cases test ordinary reset boundaries and must not be counted
as successful P1.7 transitions.

Record supply voltage, supply entry point, current measurement point, instrument
and resolution/bandwidth, Wi-Fi state, attached peripherals, USB and debugger.
Record sleep current separately from the integral of voltage times current over
one complete cycle, including startup, DHCP/DNS/HTTP and awake waiting. The USB
host handshake introduces variable awake time; define and record equal cycle
boundaries/dwell times for a fair energy comparison. Do not treat these scripts
as an energy analyzer. Measure with USB disconnected as well where possible;
reconnect it to retrieve the repeated boot result after a single long sleep.
The script waits for the next GO, so it does not silently run unobserved cycles.

Correlate wake cause and the implementation's POWMAN state-transition evidence
with measurement. Neither lower current nor a successful WFI alone proves
that SWCORE/XIP/SRAM domains powered off. Repeat with debugger physically
disconnected: debug power requests can inhibit the intended state. Pin-level
logic/probe changes require a separate wiring review for the actual board.

After testing, restore the saved entry point/configuration and any backup data,
or restore the complete filesystem and original firmware. Do not indiscriminately
delete files matching a prefix. Retain the test log, tool versions, board identity,
backup hashes, firmware hashes, any scope traces and a PASS/FAIL/NOT RUN table.
