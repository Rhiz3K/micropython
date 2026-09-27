# RP2350 timed deepsleep: macOS results, 2026-09-27

**Experimental. Complete application-cycle energy remains unmeasured.**
Subsequent USB current measurements of this assembly are recorded separately
in the [JT-UM120 power report](POWER-MAC-20260927.md), the later
[display pin optimization](POWER-OPT-MAC-20260927.md), and the
[GP25 comparison](POWER-GP25-MAC-20260927.md). The last report includes the
latest verified restoration; the functional tests below did not measure current.
These are results from a second Pico 2 W (RP2350 A2, ARM), identified as
`test-board-2` in the exported logs. The owner has clarified that the e-paper
display is physically connected. The timed-sleep harness did not initialize,
update or send a sleep command to the display. Physical disconnection during the earlier
short and Wi-Fi tests was not reliably documented; the previous assumption of
disconnection is withdrawn. The long-sleep runs describe the board with the
display attached, based on this owner clarification. These results must not
be described as verified bare-board tests or display-driver validation.
A separate subsequent display test is recorded below.
They do not replace [the earlier Linux results](RESULTS.md).

## Build

The native ARM64 macOS build and subsequent firmware readback verification
completed successfully. Board: `RPI_PICO2_W`, platform: `rp2350-arm-s`.
The existing flash filesystem was verified unchanged across firmware flashing;
board-specific backup and verification material remains private.

- Source: `9a8542bb242d04bcf20ddfb7b09b8047759bfa92`.
- Pico SDK: `98a542c1a62fb549ffb5d66a3e5892b06276b670` (2.3.0).
- Build picotool: `6f6458d792b93685a11423b244a585eaa99eafcf`.
- GCC: 14.3.1; host: macOS 27.2 ARM64, Python 3.14.7, pyserial 3.5.
- UF2: 1780224 bytes, SHA-256
  `33ccf3abf94a3a2a784c0d6d08f32d4d722cf9a89a7074331b33788c60cfbe60`.
- Firmware BIN: 889712 bytes, SHA-256
  `5b66bbba5981774e8066924bd005182fea7523e36dcf795e623863e3b55ba881`.

See [sanitized build metadata](evidence/mac-20260927/build.json).
These hashes identify this Mac build, not the historical Linux UF2.
Firmware identity and flashing details are linked by the private test procedure;
the timed-sleep JSONL records do not themselves contain a firmware hash or version.

## Completed checks

Each sleep scenario used a fresh installation, distinct run name and new log.
The three-cycle, 100-cycle, thread, DMA and lightsleep-before suites used 2500 ms
sleeps with the Wi-Fi test disabled. The physical-display limitation above
applies to these runs. Times below are host durations including
USB enumeration, boot exchange and the final reset, not measured sleep duration.

| Check | Result | Evidence and scope |
| --- | --- | --- |
| Initial three cycles | PASS | [Log](evidence/mac-20260927/three-cycles.jsonl); 3 deep wakes, 5 unique boots, 13.150 s |
| 100 short cycles | PASS | [Log](evidence/mac-20260927/100-cycles.jsonl); 100 deep wakes, 102 unique boots, 380.624 s |
| Active CPU1 / caller on CPU1 | PASS | [Log](evidence/mac-20260927/thread.jsonl); rejection checks, then 3 deep wakes after worker exit, 13.465 s |
| RAM-to-RAM DMA | PASS | [Log](evidence/mac-20260927/dma.jsonl); 3 deep wakes, 13.151 s; no claim about every peripheral/DMA combination |
| Lightsleep before deepsleep | PASS | [Log](evidence/mac-20260927/lightsleep-before.jsonl); 3 deep wakes, 13.927 s |
| Active watchdog | PASS | [Log](evidence/mac-20260927/watchdog.jsonl); phase 4, 2 boots, WDT_RESET (3), 0 deep wakes, 3.732 s |
| Single 30-minute sleep, display attached | PASS | [Log](evidence/mac-20260927/30min.jsonl); 1 deep wake, 3 unique boots, RTC +1800 s, 1817.843553 s total host time |
| Single 75-minute sleep, display attached | PASS | [Log](evidence/mac-20260927/75min.jsonl); 1 deep wake, 3 unique boots, RTC +4500 s, 4541.880027 s total host time |
| Idle timing | PASS | [Exact expected output](evidence/mac-20260927/idle-regression.log), in a clean reset context |
| RTC during sleep and lightsleep | PASS | [Exact expected output](evidence/mac-20260927/rtc-sleep-regression.log) |
| SLEEP_EN register preservation | PASS | [Log](evidence/mac-20260927/lightsleep-registers-regression.log); one unittest case |
| Lightsleep USB/frequency checks | PASS | [Exact expected output](evidence/mac-20260927/lightsleep-frequency-regression.log); explicit `import machine` before the stock script |
| Lightsleep from CPU1 | PASS | [Log](evidence/mac-20260927/lightsleep-thread-regression.log); three unittest cases |
| Invalid arguments, hard IRQ, clock/time regression | PASS | [Log](evidence/mac-20260927/deepsleep-arguments-irq-regression.log); eight PASS checks |

All 114 deep wakes in the seven completed timed-sleep suites report cause 4,
`HAD_SWCORE_PD` and alarm source `LAST_SWCORE_PWRUP=0x40`. Each suite finishes
with cause 3 after the intended ordinary reset and an exact completed-cycle
count. The device checks the file sentinel and POWMAN backup region 2 on every
boot. Watchdog scratch regions 0/1 were lost on all 114 deep wakes.

The 100-cycle log crosses seven minute boundaries and one day boundary. Its
RTC sleep deltas are 2 s for 32 cycles and 3 s for 68 cycles. The initial
three-cycle run and each of the three short variants cross one minute and one
day, with deltas `[2, 3, 3]` s. These values agree with the logged RTC snapshots;
whole-second readings are not oscillator calibration.

The 30-minute run requested 1800 s and recorded RTC +1800 s, crossing midnight.
The host interval from SLEEP to receipt of the wake record was 1816.114484 s;
the final ordinary-reset PASS arrived at 1817.843553 s from host start. The
16.114484 s difference between that host interval and the RTC delta includes
boot/USB recovery and record delivery, so it is not a direct measurement of
oscillator error or pure sleep duration. The configured RTC tolerance was 90 s.

The 75-minute run requested 4500 s and recorded RTC +4500 s, also crossing
midnight. Its host SLEEP-to-wake interval was 4540.153568 s and total host time
was 4541.880027 s, with an RTC tolerance of 225 s. Both long runs completed
exactly one deep wake and the final ordinary-reset check. The 40.153568 s
host-minus-RTC difference in this run likewise includes USB enumeration, boot
and record delivery. Neither host interval is a precise calibration of LPOSC.
The attached display was not driven by the harness and no current was measured.

The 100-cycle log contains 93 SLEEP lines but all 100 confirmed wake records;
the thread log similarly has two SLEEP lines and three confirmed deep wakes.
SLEEP output is not the acknowledged result and is not the cycle counter.

On this RP2 port `machine.reset()` uses the watchdog and also reports cause 3.
The watchdog scenario is interpreted using its phase and implemented checks;
its log does not separately record the EBUSY errno or raw watchdog reason.
Raw POWMAN flags can survive ordinary resets and must be read with the reset
cause and test phase. None of these records measures current or independently
probes every power domain.

## Wi-Fi remains unresolved

### Original automatic-boot reconnect suites

These two suites ran the Wi-Fi check automatically from the test `main.py`
on each boot. Both used the experimental firmware.

| Check | Result | Evidence |
| --- | --- | --- |
| Ordinary-reset reconnect, experimental firmware | FAIL | [Log](evidence/mac-20260927/wifi-ordinary.jsonl); boot 2, cause 3, completed 1, 37.835 s |
| Deep-wake reconnect, same experimental firmware | FAIL | [Log](evidence/mac-20260927/wifi-deep.jsonl); boot 2, cause 4, completed 1, 37.907 s |

Initial connection with a dynamically assigned IP, DNS lookup and HTTP 200
succeeded in both runs; DHCP packets were not captured. On the first return,
both timed out after 30000 ms waiting for Wi-Fi/DHCP readiness, with
`wlan.status() == -1`. Neither reached a second successful DNS/HTTP transaction.
The deep-wake record passed reset-cause, RTC and backup/sentinel checks before
the network failure; it is still a failed reconnect suite.

**Both runs used this same experimental firmware. The ordinary-reset comparison
is not an unmodified-firmware baseline.** The failure occurs after both reset
paths in this pair; these observations neither establish nor rule out a
regression relative to unmodified firmware.

In the pinned CYW43 driver, status -1 is `CYW43_LINK_FAIL`, produced by a failed
`SET_SSID` event. A maintained Wi-Fi link still waiting for an IP address would
report `CYW43_LINK_NOIP` (2), so the recorded final state is a connection failure,
not merely an IP-address wait on an established link. The original automatic-boot harness stores only
the status at the 30-second timeout, without transitions or the driver's
`event.reason`. An earlier brief association or IP assignment cannot be ruled
out. See the pinned driver [event handling](https://github.com/georgerobotics/cyw43-driver/blob/055d64274b014dd7b1c2fc94d26e8a18face7124/src/cyw43_ctrl.c#L373)
and [status definitions](https://github.com/georgerobotics/cyw43-driver/blob/055d64274b014dd7b1c2fc94d26e8a18face7124/src/cyw43.h#L98).

### Separate raw-REPL ordinary-reset diagnostic, including baseline

After both long sleeps passed, a separate bounded host script ran two probes
through raw REPL without a soft reset. It kept the completed 75-minute test's
`main.py` and configuration in place. Probe 1 explicitly called
`wlan.active(False)`, waited 500 ms, then activated and connected the interface.
After a successful DNS and HTTP check, the host issued one `machine.reset()`.
Probe 2 began after USB re-enumeration and connected without an explicit
inactive call beforehand. Neither probe invoked deepsleep. Connection attempts
had a 35-second deadline; socket operations used a 10-second timeout, with
90-second outer probe and 20-second reset worker bounds.

The same script SHA-256 is recorded for both firmware runs. The baseline was
actually flashed and tested: unmodified source `09f5bb4475`, runtime
`v1.30.0-preview.85.g09f5bb4475`, UF2 SHA-256
`6b5f157ff16ca2844f1578eb7173a2aa92317638cc5e007809639feb2f6597c3`.
The [selected switch record](evidence/mac-20260927/baseline-switch.json) reports
PASS and byte-for-byte filesystem preservation. Diagnostic identity records
confirm the expected revision before both probes and before the ordinary reset.

| Firmware | Probe 1 | Reset evidence | Probe 2 |
| --- | --- | --- | --- |
| Experimental `9a8542bb24` | PASS: connected with DHCP at 5.580 s; DNS and HTTP 200 | USB disconnect observed, boot 3 → 4 | FAIL: status -1 at 4.150 s, connect timeout; final result at 36.189 s |
| Unmodified baseline `09f5bb4475` | PASS: connected with DHCP at 4.474 s; DNS and HTTP 200 | USB disconnect observed, boot 6 → 7 | FAIL: status -1 at 4.150 s, connect timeout; final result at 36.094 s |

Times in this table are measured from each probe's start, including activation
and, for probe 1, the explicit 500 ms wait. Final-result times include cleanup;
they are not the configured connect timeout. See the
[experimental events](evidence/mac-20260927/wifi-restart-diagnostic-experimental/events.jsonl),
[summary](evidence/mac-20260927/wifi-restart-diagnostic-experimental/summary.json) and
[metadata](evidence/mac-20260927/wifi-restart-diagnostic-experimental/metadata.json),
and the [baseline events](evidence/mac-20260927/wifi-restart-diagnostic-baseline/events.jsonl),
[summary](evidence/mac-20260927/wifi-restart-diagnostic-baseline/summary.json) and
[metadata](evidence/mac-20260927/wifi-restart-diagnostic-baseline/metadata.json).

Observed probe-1 status changes were `0 → 1 → 2 → 3` on the experimental build
and `0 → 1 → 3` on baseline; the sampling did not capture an intermediate 2 in
the latter. Both set `has_dhcp4=true`. Probe 2 showed `0 → 1 → -1` on both;
all its recorded states had `isconnected=false` and `has_dhcp4=false`. No second
DNS or HTTP check ran. These were completed network failures, not host worker
timeouts. Both logs confirm radio deactivation and removal of the diagnostic's
own temporary configuration after probe 2.

This comparison reproduces the ordinary-reset failure on unmodified firmware
in the tested setup. It is not evidence of a failure exclusive to deepsleep,
does not establish the cause, and does not rule out every possible regression.
It also does not turn the earlier automatic-boot suites into baseline tests.
The diagnostic sampled state changes at approximately 100 ms intervals; it did
not record driver `event.reason`, association events or DHCP packets, so brief
unobserved transitions and the underlying network/driver cause remain open.

## Separate display test

The owner's older photograph identifies a Waveshare Pico-ePaper-2.9 B/W V2,
296×128; the owner confirmed that the display remained connected. Current
jumper positions are not inferred from that photograph. The test used the
[pinned Pico vendor driver](https://github.com/waveshareteam/Pico_ePaper_Code/blob/c9bcd84db5adf5f085353649a8a5c31492bc5fb8/python/Pico-ePaper-2.9.py),
with explicit SPI1 pins and bounded BUSY waits. Its full LUT matches the
[explicit V2 reference](https://github.com/waveshareteam/e-Paper/blob/e4bb8924d47c8ac88072cdddea5544e2f4314d92/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd2in9_V2.py).
The original application's driver was not changed.

**Automatic checks: PASS. Visible phase-B image: PASS, confirmed by the owner.** See the
[events](evidence/mac-20260927/display-test.jsonl) and
[result](evidence/mac-20260927/display-test-result.json). Phase A performed one
full refresh with `A: BEFORE 5s SLEEP`, then the vendor sleep sequence and
RST=0 before `machine.deepsleep(5000)`. USB removal and return were observed.
The fresh boot reported cause 4, alarm 64 and `HAD_SWCORE_PD`; the harness
counter advanced 9 → 10 while other POWMAN backup words stayed unchanged.
RTC advanced 7 s, including host reconnection delay.
Phase-B records were received together after that phase finished; their
`host_utc` values are receipt times, not precise timestamps of the wake.

The host then explicitly invoked phase B through raw REPL: reinitialize,
one full refresh with `B: AFTER ALARM BOOT` and a black rectangle on the right,
then panel sleep and RST=0. The main refresh BUSY intervals were 2496/2497 ms.
The two temporary modules were removed after verification, the complete file
inventory matched its pre-test state, and the host confirmed a stopped REPL.
The owner subsequently confirmed readable `B: AFTER ALARM BOOT` text and the
correct black rectangle on the right; see the separate
[visual confirmation](evidence/mac-20260927/display-visual-confirmation.json).
The original machine logs retain `NOT_VERIFIED`, their status at test completion.
BUSY/SPI success alone does not prove the image. This additional wake is separate from the 114 wakes
in the seven timed-sleep suites above.

Phase B was initiated by the host after boot, not automatically by an
application startup hook. This does not validate the original application's
display integration. RST=0 and a sleep command do not prove zero module
current; `SPI.deinit()` is a no-op in this RP2 implementation. This display
test did not measure current or energy; see the subsequent power report.

## Board state and file restoration after the functional tests

The experimental firmware was restored after baseline testing, with full-flash
backup and byte-for-byte filesystem verification. The final runtime is
`v1.30.0-preview.87.g9a8542bb24`. The
[restoration record](evidence/mac-20260927/restoration-result.json) reports
PASS: all 29 original files match their saved sizes and SHA-256 values, the
original `main.py` name is restored, and only verified test files were removed.
The temporary Wi-Fi configuration and display modules were already removed.
Private original files, file inventories and full-flash images are not exported.

RTC was set from host UTC and checked, including weekday. All accessible test
backup-register words were cleared; their original pre-test volatile contents
were unavailable and have not been restored. STA and AP are inactive, and the
board is stopped in friendly REPL. **The original application was not started.**
A subsequent reset/power cycle will start it. The local HTTP test endpoint and
host test processes were stopped. The complete original firmware/FS backup is
retained privately for intentional rollback.

The later power tests used a fresh backup after the owner's USB reconnect;
one data file had changed and its newer contents were preserved. Their
[restoration record](evidence/mac-20260927-power/restoration-result.json),
2026-09-27 13:46:06 UTC, again verifies all 29 files and the original main name.
At that restoration the board remained on experimental firmware, stopped in
friendly REPL with radio off and panel asleep. Subsequent physical reconnects
for the no-load check may have started the original application; its present
runtime was not verified.

Subsequent panel-pin and GP25 tests again backed up and restored all 29 files.
The latest [restoration](evidence/mac-20260927-gp25/restoration.json), at
16:37:40 UTC, verified all originals and removed six temporary files. The
application is stopped in friendly REPL with radio off, GP25 low and panel
asleep with its data pins released. This final REPL state is not deepsleep;
0.3708 mA is the separately measured sleep current. The next reset starts the
unchanged original application, which does not integrate the tested helpers.

## Remaining work

| Check | State |
| --- | --- |
| Visible phase-B display image | PASS; owner confirmed text and right-hand rectangle |
| Automatic startup integration of the original application | NOT RUN |
| USB current of the attached assembly, radio off / panel asleep | PASS; see [power report](POWER-MAC-20260927.md) |
| No-load reference | Valid 15s window: 0.05541 mA; full capture later ended with HID error, see power report |
| Bare-board current and complete-cycle A/B/C energy | NOT MEASURED |
| Wi-Fi failure root cause and successful reconnect | UNRESOLVED |

No upstream PR was created. See [export scope and redaction rules](evidence/mac-20260927/README.md).
