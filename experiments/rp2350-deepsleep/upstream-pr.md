# Draft for human review — not submitted

Suggested title: `rp2: Add timed RP2350 deep sleep and Pico 2 W sleep preparation.`

Timed `machine.deepsleep(ms)` currently uses lightsleep followed by reset.
This patch requests RP2350 P1.7: SWCORE, both SRAM domains and the XIP cache
lose power. The always-on POWMAN timer runs from LPOSC and its alarm restores
power for a normal ROM boot and a new `boot.py`/`main.py` run.

**Experimental; not ready for upstream submission. No PR has been submitted.**
Board opt-in enables the new timed path only for ARM `RPI_PICO2` and
`RPI_PICO2_W`. RP2040, RP2350 RISC-V, lightsleep and no-argument deepsleep
retain their existing paths. RISC-V compilation now passes for Pico 2/Pico 2 W;
RISC-V runtime and P1.7 support have not been verified.

## Implementation and API behavior

- RTC time and all eight POWMAN backup words (`machine.mem_backup(2)`) survive.
  Python heap, peripherals and watchdog-backed backup regions 0/1 do not.
  `DEEPSLEEP_RESET` requires the hardware reset/wake records and ALARM latch.
  Startup consumes that latch, preventing a later core-only reset from reusing
  retained POWMAN history, and restores XOSC RTC ticking. No scratch words are reserved.
- Calls from core1 or an interrupt, an active Python worker on core1, and an
  enabled watchdog raise `EBUSY` before teardown. The code repeats the worker
  and watchdog checks with interrupts disabled before resetting idle core1.
  Watchdog refusal is a limitation of this candidate, not a hardware requirement;
  accepting it needs timeout/transition race tests.
- Teardown stops CYW43, disconnects USB and aborts DMA using the RP2350-E5
  sequence. Wi-Fi disassociation is kept separate: a 500 ms outer wait would
  not bound the driver call itself. Applications must flush and close buffered files first.
  The pinned SDK's SRAM sleep preparation is included with BSD attribution;
  POWMAN removes the switched domains only after the processors enter sleep.
- Rejected, cancelled or expired transitions after teardown take an ordinary reset.
  Once a transition is committed, its wake alarm remains armed. Startup restores
  debugger power-request handling after the temporary sleep-entry override.
- Pico 2 W additionally opts into driving radio CS/GP25 LOW after radio power-off,
  disabling its VSYS monitor path. Other boards default to no CS override.
  GP23/WL_REG_ON is explicitly LOW with no pulls, including a never-used radio;
  normal full CYW43 deinitialization already clears its pulls. Display GPIO and
  supply wiring remain application responsibilities.
- Negative durations and values outside the port's signed integer range are
  rejected; 0/1 ms take an ordinary reset. Alarm addition is checked for overflow.
  LPOSC does not provide XOSC accuracy. No new Python API is introduced.

The merged RTC/frequency fixes are reused, not reimplemented. Direct
`hardware_powman` calls avoid the high-level SDK helper's scratch[6:7] use,
which conflicts with MicroPython's public backup memory.

## Reproduction and current validation

Upstream base: `09f5bb447504a058376c62fe991b3613531837e6`.
Pico SDK: `98a542c1a62fb549ffb5d66a3e5892b06276b670` (2.3.0).
Final reviewed source: `2445a04bfa2f426e8390b2efaa6450910734e430`.
Runtime: `v1.30.0-preview.99.g2445a04bfa.dirty`; Pico 2 W UF2 SHA-256:
`b6eb010e46925f196002de0b9fd865da5107e9a9d8b49c3853577d7108ce53f2`.

The [review report](RESULTS-REVIEW-20260929.md) records exact commands, versions,
artifacts and evidence, keeping the first `5f4f0fde9` validation separate from
the final alarm-lifetime fix. [Build instructions](HANDOVER.cs.md) require
[TinyUSB preparation](prepare-tinyusb.sh), which verifies and applies the exact
stored upstream SETUP-queue fix. The pinned gitlink is unchanged; a clone alone
does not reproduce the tested integration. That fix is outside `combined-upstream.patch`.

| 29 September review check | Result |
| --- | --- |
| Fresh Pico 2 W ARM, Pico 2 ARM and Pico RP2040 builds | PASS: zero compiler warnings |
| Documentation with warnings treated as errors | PASS |
| Offline reset-spanning harness / isolated TinyUSB preparation tests | PASS: 21 / 10 |
| Linux Pico 2 W, 3 × 2500 ms alarm cycles, attached B/W/R V4 panel | PASS |
| CPU1 `EBUSY`, RAM DMA, lightsleep-before, RTC midnight, USB, file and POWMAN records | PASS in that bounded suite |
| Five alarm wakes: 3 in the suite, 1 reset probe, 1 rearm cycle | PASS: alarm cause 4; final ordinary reset cause 3 |
| Software AIRCR SYSRESETREQ after alarm wake, with retained POWMAN history | PASS: cause 1, then 8-second watchdog recovery cause 3 |
| Active watchdog refusal followed by an actual watchdog reset | PASS: `EBUSY`, then `WDT_RESET` |
| Current/energy measurement, 100 cycles, 30/75 minutes, new Wi-Fi repetitions | NOT RUN on this revision |
| RISC-V builds: clean base and candidate × Pico 2/Pico 2 W | PASS: 4 builds, legacy lightsleep/reset path retained |
| LPOSC OTP read on the Linux Pico 2 W, installed `2445a04bf` | PASS: 33045 Hz; configured divider matches |
| Current patch generator, isolated Git fixtures | PASS: 10 tests; repository Ruff/format checks |
| Physical SWD debugger, non-W Pico 2, RP2040 and RISC-V runtime | NOT RUN |

The [follow-up report](FOLLOWUP-REVIEW-20260929.md) records RISC-V commands,
SHA-256 hashes, the read-only OTP check and the source-backed design decisions.
Current [patch snapshots](tools/README.md) are generated from committed HEAD
and checked for staleness; they are not a clean upstream commit series.

Protocol 2 waits for host acknowledgements and checks each observed boot before
accepting a completed cycle. ACK-SLEEP-to-READY timing includes boot/USB, not
just the powered-down interval. This reset-spanning harness remains an opt-in
experiment, not an upstream multitest.
POWMAN records support SWCORE power-down and alarm wake; they are not independent
measurements of every domain, board current or complete-cycle energy.

## Earlier evidence and remaining work

The [Mac functional report](RESULTS-MAC-20260927.md) and
[combined-candidate report](RESULTS-EXTENDED-MAC-20260927.md) identify their exact
older firmware and cover 100-cycle/long sleeps and measured GP25 current reduction.
Those measurements concern USB input to a specific board/display assembly,
not chip-only current or this review's firmware. Complete-cycle energy remains
unmeasured. [USB/Wi-Fi results](RESULTS-USB-WIFI-MAC-20260928.md) retain the earlier
USB failures and the limits of attributing them to the reproduced TinyUSB bug.
[Linux DHCP diagnostics](RESULTS-DHCP-LINUX-20260929.md) retain association failures;
PM_NONE did not eliminate them. Explicit application Wi-Fi preparation helped
tested cases, but this core path does not guarantee reconnect for every AP.

USB and network sessions must be re-established after boot. GPIO wake, active
watchdog support, other board opt-ins, RISC-V power-down and independent domain
measurements remain outside the patch. Broader fault-injection and radio tests,
a maintainer-ready clean branch and contributor sign-off are still outstanding.
Suggested review split: attributed SDK sleep workaround; timed power-down core
and API documentation; Pico 2 W GP25 preparation. The separate TinyUSB integration
and experimental harness need their own review. Further cleanup is deferred.

Primary sources: [RP2350 datasheet/errata](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf),
[Pico 2 W schematic](https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf),
[pinned POWMAN](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2_common/hardware_powman/powman.c),
[pinned sleep preparation](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2_common/pico_low_power/low_power.c),
[A2 ROM alarm handling](https://github.com/raspberrypi/pico-bootrom-rp2350/blob/fd6104450fa8f55c11c0c9b54dbc69a27537130f/src/main/arm/varm_boot_path.c#L596) (ALARM also preserved in reviewed A3/A4 ROM sources),
and [MicroPython issue #15623](https://github.com/micropython/micropython/issues/15623).

Generative AI assisted implementation, tests and review materials. Human review
and responsibility for the contribution remain required before any submission;
this draft neither claims that review is complete nor adds a sign-off.
