# RP2350 timed deepsleep: recorded results

Updated 2026-09-27. **Experimental; the original Linux tests did not measure
sleep current or cycle energy.** This document records those Pico 2 W tests;
they do not by themselves validate another board/display assembly.
No upstream PR has been submitted.

For subsequent native macOS testing on a second Pico 2 W, see the separate
[2026-09-27 Mac results](RESULTS-MAC-20260927.md). The historical matrix below
remains scoped to the original Linux test board and its dated observations.
USB current of the second board with its attached display was subsequently
measured in the [JT-UM120 power report](POWER-MAC-20260927.md). A subsequent
[display pin optimization](POWER-OPT-MAC-20260927.md) reduced measured deep-sleep
USB current from about 3.82 to 0.60 mA with the display still attached.
A further [GP25 comparison](POWER-GP25-MAC-20260927.md) measured 0.5983 versus
0.3708 mA over matching late windows of two 300 s sleeps, another 38.0%
reduction. Alarm wake, display refresh and driver reinitialization passed;
a supplied photograph also confirmed the new phase-B image. Wi-Fi association
was not tested by that driver check. The original application was restored
without integrating either helper.
Complete application-cycle energy remains unmeasured.

## Source and artifacts

- Original upstream base: `09f5bb447504a058376c62fe991b3613531837e6`.
- Firmware and tests commit: `3fc3f9431d9ccc571b4fb0c27bd860d5709ab683`.
- Pico SDK: `98a542c1a62fb549ffb5d66a3e5892b06276b670` (2.3.0).
- Picotool used by the build: `6f6458d792b93685a11423b244a585eaa99eafcf`.
- Tested Linux toolchain: Arm GNU 14.3.rel1 / GCC 14.3.1, CMake 4.4.3,
  Make 4.3. See [build environment](evidence/builds/environment.txt).
- Original tested Pico 2 W UF2 SHA-256:
  `a10041bf6b02177f37eb1d396bff023e9261802d59bcc8874749e8f458b2f9bb`.
- First 889736 flash bytes at `0x10000000` matched the build's firmware.bin:
  `3de9dd1b96c6740d51be949f199664723b21963eadb42470ebf8bb1c7eb90759`.

The tested code was subsequently committed. The two patches beside this file
are byte-identical to the corresponding source changes in that commit.
The build/version metadata of a new build from a commit may differ from the
original dirty-tree build, even with identical functional source. Do not claim
the historical UF2 hash for a new native macOS build.

`reproduce.sh` preserves the historical Linux x86_64 recipe: build the exact
unmodified base first, apply firmware.patch, then build the three targets. A
complete clean run passed all five builds and reproduced the tested W UF2
byte for byte. The script never accesses hardware. No firmware binaries or
private flash backups are committed here.

## Test matrix

These are observations from 2026-09-25 unless dated otherwise. The test README's
initial NOT RUN table is a scenario template, not this result record.

| Check | Result | Scope/evidence |
| --- | --- | --- |
| Baseline Pico 2 W and Pico/RP2040 builds | PASS | [Build logs](evidence/builds/) |
| Patched Pico 2 W, Pico 2 ARM, Pico/RP2040 builds | PASS | [Build logs](evidence/builds/); only W tested physically |
| Full clean Linux reproduction | PASS | Five builds; tested W UF2 byte-identical |
| 100 x 2500 ms deep sleep | PASS | [Complete JSON log](evidence/patch-final-100.jsonl); 100 alarm wakes, final ordinary reset |
| New program, USB, deep reset cause and marker lifetime | PASS | All 100 deep wakes cause 4; final ordinary reset cause 3 |
| RTC continuity | PASS | Seven minute crossings, one day crossing; not oscillator calibration |
| File sentinel and POWMAN backup region 2 | PASS | Retained across the 100-cycle suite; no per-cycle flash writes |
| Watchdog-backed regions 0/1 | Observed LOST | Expected P1.7 limitation, not successful retention |
| Active CPU1 / call from CPU1 | PASS | EBUSY; three sleeps after worker exits |
| Active watchdog | PASS | EBUSY; watchdog remains running and expires |
| RAM-to-RAM DMA and lightsleep-before-deepsleep | PASS | Three cycles per scenario; not every peripheral/DMA combination |
| 0 and 1 ms | PASS | Ordinary reset, not power-down |
| 20 ms | PASS | Three deep wakes |
| 2 ms strict deep-wake expectation | FAIL | Ordinary-reset fallback; P1.7 not guaranteed for expired deadlines |
| Negative/overflow arguments and hard IRQ rejection | PASS | [Regression log](evidence/final-regressions-fixed.log) |
| Existing RTC/lightsleep frequency, register, thread checks | PASS | Stock frequency test required explicit `import machine` |
| idle timing | FAIL initially; PASS after reset | Passed baseline and patch in clean context; earlier failure not isolated |
| Wi-Fi/DHCP/DNS/HTTP reconnect suite | FAIL | [Patched log](evidence/patch-final-wifi.jsonl): three post-wake transactions passed, later timeout |
| Baseline Wi-Fi control | FAIL | [Baseline log](evidence/baseline-wifi-ordinary-5.jsonl): first connection timed out before sleep |
| Patched Wi-Fi retry, 60 s timeout | FAIL | [Retry log](evidence/patch-final-wifi-repeat-5.jsonl): first connection timed out before sleep |
| Final 10 s smoke after baseline comparison | PASS | Timed alarm wake, RTC +10 s, final ordinary reset |
| Runtime Wi-Fi trace diagnostic, September 26 | FAIL | REPL stopped responding after `trace=7`; no usable packet trace retained |
| Remote recovery, September 26 | FAIL | USB reset and 5/30 s hub cycles did not restore enumeration |
| 30-minute and 75-minute sleeps | NOT RUN | Configurations prepared in test README |
| Maximum-duration sleep / 64-bit overflow fault injection | NOT RUN | Code review and integer rejection do not establish these cases |
| No-argument sleep, external RUN/brownout/debug reset | NOT RUN | Requires independently arranged recovery |
| Physical Pico 2, RP2040 and new Pico 2 WH/display | NOT RUN | Do not transfer results from the original board |
| RISC-V build and hardware | NOT RUN | New path gated off; no compatibility claim |
| Native macOS build | NOT RUN | Commands in handover are a new-host procedure |
| Sleep current, A/B/C comparison, cycle energy | NOT RUN | No current meter was connected |

The 100-cycle host duration was 377.72 s including boot, USB exchange and the
final reset. The records contain `HAD_SWCORE_PD` and alarm wake source
`LAST_SWCORE_PWRUP=0x40`. This supports switched-core power-down and wake.
Turning off SRAM/XIP is inferred from the requested P1.7 state and hardware
documentation; each domain was not independently probed during sleep.
Neither register records nor successful wake cycles measure energy savings.

## Evidence export and open failures

The four JSON logs are exports of original records with `uid`/`usb_serial`
replaced by `test-board-1` and network destinations replaced by
`<redacted-network>`. Timing, outcomes and hardware values are unchanged.
The build environment's hostname is redacted. Exported text logs use LF line
endings and omit trailing whitespace; values are otherwise unchanged. This is a selected evidence set; the
larger local review bundle retains additional failed attempts and test logs.

Wi-Fi failure is not established as a patch regression: the baseline also
failed before sleeping. Read-only router diagnosis found older unsuccessful
DHCP offers for the candidate MAC, but the mapping still needs confirmation
against the active WLAN MAC. No router configuration was changed. Capture a
new DHCP transaction on a controlled AP to distinguish association, OFFER,
REQUEST and ACK failure. Network inventories and credentials are not published.

The later USB trace hang was a runtime diagnostic, with no firmware rewrite.
After a host USB reset, enumeration failed with descriptor timeout -110 and
address error -62. The hub reported off/on on both logical USB peer ports, but
physical loss of VBUS was not measured. The owner confirmed USB-only wiring.
The last verified state of the original board is unresponsive, awaiting a
physical unplug/replug. Do not infer a recovered REPL from September 25 logs.

## Primary references

- [RP2350 datasheet and errata](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf).
- [Pico 2 W schematic](https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf).
- [Pinned POWMAN implementation](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2_common/hardware_powman/powman.c).
- [Pinned low-power implementation](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2_common/pico_low_power/low_power.c).
- [Related upstream issue](https://github.com/micropython/micropython/issues/15623).
