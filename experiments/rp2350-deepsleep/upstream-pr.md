# Draft for human review — not submitted

Suggested title: `rp2: Add timed RP2350 deep sleep and Pico 2 W sleep preparation.`

On RP2350, `machine.deepsleep(ms)` currently calls `lightsleep(ms)` and then
resets, keeping the switched power domains supplied. This patch implements
timed P1.7 power-down for ARM Pico 2 and Pico 2 W, followed by a normal ROM
boot when the always-on timer expires. It also disables Pico 2 W's VSYS
monitor path after shutting down its radio, so that path does not continue
consuming current during deep sleep.

**Experimental; not ready for submission. No upstream PR was submitted.**
The combined firmware completed 120 alarm wakes and a direct firmware
comparison confirmed the GP25 current reduction. The subsequent
[USB/Wi-Fi investigation](RESULTS-USB-WIFI-MAC-20260928.md) reproduced and fixed
a pinned TinyUSB SETUP-queue bug with upstream commit `a0249ada`, then verified
70 controlled USB returns on the new firmware. The earlier intermittent
enumeration failures were not reproduced in today's control firmware, so the
causal link to that bug remains unproven.

Explicit Wi-Fi disconnect and a bounded wait for local link-down before radio
power-off allowed repeated DHCP/HTTP after reset, deep sleep and the original
application's lightsleep/soft-reset path. This is application preparation,
not a change to the core deepsleep deadline or a guarantee for every AP.
The patched original application and new firmware are installed; 28 other
original files were verified unchanged and the application was stopped in REPL
on the **Mac test board on 28 September**.
Complete application-cycle energy and the full production application flow
remain unverified. The [previous report](RESULTS-EXTENDED-MAC-20260927.md)
retains all original failures and the earlier rollback evidence.

The **29 September Linux follow-up** used a different Pico 2 W, a B/W/R V4
panel and a MikroTik network. Its [initial tests](RESULTS-LINUX-20260929.md)
passed six controlled alarm wakes but also found two DHCP timeouts. The
[subsequent packet/RAM diagnostics](RESULTS-DHCP-LINUX-20260929.md) found three
more timeouts in 15 connections, with no sleep between the PM comparison
attempts. PM_NONE did not eliminate the failure. Router registrations and
driver state indicate unstable Wi-Fi association/authentication, but the event
reason is unresolved. No new current or cycle-energy measurement was made.
Two hardware-verified fixes to the experimental Python preparation helper
handle a never-initialized GP23 mux and an already-down link retaining BADAUTH.
They do not modify this core patch, resolve Wi-Fi authentication, or install
an application change on that board. The Linux firmware and all 37 files were
left unchanged by this diagnostic follow-up.

### Implementation

For timed sleeps longer than 1 ms, POWMAN switches off SWCORE, XIP cache and
both SRAM domains. Its timer runs from LPOSC; execution restarts at
`boot.py`/`main.py` after the alarm. RTC time and all eight words of the existing
POWMAN backup region survive. Hardware reset/wake records identify
`machine.DEEPSLEEP_RESET` without reserving any user scratch words.

The path stops CYW43, disconnects USB, aborts DMA using the RP2350-E5 sequence,
and prevents interrupt callbacks from restarting work during teardown. It
includes the pinned SDK's SRAM WFI preparation sequence with its BSD
attribution. A rejected or cancelled transition causes an ordinary reset;
once POWMAN has committed the transition, its wake alarm remains armed.
Subsequent startup clears the alarm and restores the RTC's XOSC tick source.

Pico 2 W opts into `MICROPY_HW_CYW43_DEEPSLEEP_CS_LOW`; its default is disabled
for other boards. Only after `cyw43_deinit()` and explicit WL_REG_ON LOW does
the timed-sleep path configure `CYW43_PIN_WL_CS` (GP25) as a LOW output without
pulls. On Pico 2 W this also disables the VSYS-to-ADC monitor path. The normal
wireless driver reclaims CS on initialization after wake. This does not alter
`WLAN.active(False)` or add display-specific GPIO handling.

The implementation uses existing SDK power-management facilities and existing
MicroPython RTC/backup-memory APIs. It does not reimplement the already merged
RTC/frequency fixes. The combined core patch changes no SDK or shared-port
dependency. The separately tested USB integration additionally applies
`tinyusb-ep0-queue.patch` inside the pinned TinyUSB submodule; it is not included
in `combined-upstream.patch`, and the submodule gitlink remains unchanged. RP2040,
no-argument deepsleep, lightsleep and RP2350 RISC-V behavior are unchanged.

### Validation

Base: `09f5bb447504a058376c62fe991b3613531837e6`.
Pico SDK: `98a542c1a62fb549ffb5d66a3e5892b06276b670` (2.3.0).
Build picotool: `6f6458d792b93685a11423b244a585eaa99eafcf`.
The current native macOS builds used GCC 14.3.1, CMake 4.4.3 and GNU Make 3.81.

| Check | Current evidence |
| --- | --- |
| Combined firmware: Pico 2 W ARM, Pico 2 ARM, Pico RP2040 builds | PASS; fresh separate builds, zero compiler warnings, matching core-source hashes before/after and across builds |
| Original timed implementation: 100 consecutive 2500 ms sleeps | PASS on the Mac test Pico 2 W; 100 alarm boots and the final ordinary-reset check |
| Original timed implementation: 30- and 75-minute sleeps | PASS on that Pico 2 W with the display attached; RTC advanced 1800/4500 s and each run completed its alarm boot and final reset |
| Original timed implementation: CPU1/IRQ/WDT rejection, RAM DMA, lightsleep-before-deepsleep, RTC and lightsleep regressions | PASS within the scenarios documented in the Mac report |
| Combined firmware: 100 sleeps with radio never activated by the suite | PASS; 100 confirmed deep wakes |
| Combined firmware: STA 10, AP retry 5 and BLE 5 sleeps | PASS; 20 confirmed deep wakes; API/driver checks do not prove peer traffic |
| Combined firmware: first AP attempt | FAIL before first READY/sleep; a subsequent five-cycle AP attempt passed |
| Combined firmware: STA+BLE attempt | FAIL during initial bootstrap; no USB/READY within 90 s and no completed sleep |
| Combined firmware: direct 300-second current comparison | PASS; 0.60048 to 0.371783 mA at the USB input, with GP25 HIGH on entry and no Python GP25 preparation |
| Separate Wi-Fi diagnostics: cold, ordinary-reset and deep-sleep boots | PASS for three HTTP transactions, with explicit radio deinitialization before and after each probe |
| Explicit Wi-Fi preparation and reconnect | PASS in the new report: 3 combined-control deep cycles, 5 normal + 5 deep cycles on usbq1 with the public helper, and 2 normal + 3 deep + 3 lightsleep/soft-reset cycles with the application function; power-off-only negative controls still fail |
| usbq1 integration: controlled USB returns | PASS 70/70; 30 normal resets, 25 STA+BLE starts, 10 public-helper cycles and 5 application-function cycles; three soft resets are counted separately |
| TinyUSB native C regression | Baseline targeted FAIL 1/1; patched targeted PASS 1/1, full usbd PASS 7/7, added reset/queued-SETUP ordering check PASS 8/8 |
| Combined firmware: remaining STA+AP, CPU1/IRQ/WDT/DMA, lightsleep and short-duration suites | NOT RUN |
| Combined firmware: regression scripts | NOT RUN; the initial runner failed during an ordinary reset before executing a test |
| Combined firmware: second 300-second run with new display A/B refresh | NOT RUN |
| Physical non-W Pico 2 validation | NOT RUN |
| Current RISC-V compile regression | SKIPPED; a suitable local compiler was unavailable; no RISC-V hardware validation |

The earlier combined integration build is `764de396cf` plus the working-tree GP25
change, with runtime version `v1.30.0-preview.88.g764de396cf.dirty`.
Its Pico 2 W UF2 SHA256 is
`c5c308066fc70ecf91d94709d6e5515ff15756d892834417aadd85d685b62f2b`.
Build logs, artifact checksums and the exact core diff are retained with the
build matrix; the extended report identifies the tested combined image and
the harness version used for each run.
Earlier firmware hashes and results remain separately identified in the
[Mac functional report](RESULTS-MAC-20260927.md) and
[historical Linux report](RESULTS.md).

The earlier Mac functional report contains 114 confirmed deep wakes across
seven completed suites, with reset cause 4, `HAD_SWCORE_PD` and the AON alarm
source.
POWMAN backup data and a file sentinel survived; watchdog scratch regions did
not. The display was attached, so these are not verified bare-board tests.
RTC snapshots and host receipt times do not calibrate LPOSC or independently
measure every power domain.

The expanded reset-spanning harness provides profiles for radio never
activated by the suite, STA, secured AP, BLE, STA+BLE and STA+AP. The completed
combined-firmware runs recorded 100 + 10 + 5 + 5 = 120 deep wakes for never,
STA, AP retry and BLE respectively. It leaves the selected interfaces active
for firmware teardown and does not call the GP25 Python helper.
Read-only pin snapshots provide diagnostics, not proof of the pin level during
P1.7. Driver/API initialization is distinct from a successful Wi-Fi transaction,
AP client traffic or BLE peer communication. The failed AP and STA+BLE
bootstrap attempts are retained alongside the completed suites; neither
reached its first sleep. No new physical post-wake display image was verified
for this combined firmware.

### Measured motivation and integration boundaries

USB input current was measured on a Pico 2 W / RP2350 A2 with a Waveshare
Pico-ePaper-2.9 B/W V2 attached, using a JT-UM120. A matched 300-second
old-core/new-core comparison measured late-window means of 0.60048 mA and
0.371783 mA respectively: a reduction of about 0.22870 mA (38.1%). Both runs
entered with GP25 HIGH; the new C path performed the LOW preparation without
a Python GP25 helper. The display was prepared separately in both runs.
This validates the automatic core preparation on this assembly; the planned
second new-core run and new display A/B refresh were not performed.

In the [completed GP25 experiment](POWER-GP25-MAC-20260927.md), matched 300-second
sleeps on the same earlier firmware and separately prepared display measured
0.5983 mA with GP25 HIGH and 0.3708 mA with GP25 LOW, a 0.2276 mA reduction.
The LOW preparation in that experiment was an independently verified Python
helper. A preceding HIGH/LOW/HIGH comparison also reproduced the change.
These earlier results remain separate from the direct firmware comparison
above.

The [display pin experiment](POWER-OPT-MAC-20260927.md) separately reduced this
assembly's sleep current from about 3.82 to 0.60 mA by preparing the panel's
signal pins. Panel sleep/Hi-Z handling remains application integration and is
not part of the core PR. Neither are supply rewiring, operation through VSYS
without VBUS, or external power switches. The core does not switch off the
board's main supply, external flash or display power.

The readings describe the USB input of this assembly, not RP2350-only current
or a guaranteed current for other boards. The meter has 10 microampere
resolution and was not independently calibrated; no no-load offset was
subtracted. Measurement windows, raw-frame checks and limitations are in the
linked power reports. Complete energy including boot, Wi-Fi and display
refresh remains unmeasured.

### Remaining limitations and design choices

Wi-Fi recovery without explicit application preparation remains unsupported.
The earlier Mac tests reproduced
ordinary-reset reconnect failure on both unmodified `09f5bb4475` and the earlier experimental
firmware after an initially successful connection/DNS/HTTP transaction.
This does not establish a deepsleep regression. See the
[controlled baseline comparison](RESULTS-MAC-20260927.md#wi-fi-remains-unresolved).
Three probes on 27 September, spanning cold/ordinary-reset/deep-sleep boots,
passed with explicit
radio deinitialization before and after each probe. They do not establish
repeated reconnect with an active Wi-Fi interface handed directly to deep
sleep. On 28 September, power-off-only negative controls reproduced the failure
both without a reset and across ordinary reset/deep sleep. Graceful disconnect
and confirmation of local link-down before power-off passed the subsequent
repeated reconnect tests. The public helper and the deployed application now
use that preparation; the core deepsleep implementation itself does not wait
for Wi-Fi disassociation. The [new report](RESULTS-USB-WIFI-MAC-20260928.md)
separates actual DHCP/HTTP transactions from radio activation and preserves
the limits of the AP-specific tests.

The 27 September combined-firmware session also lost USB after an ordinary reset with no
radio initialization. A 150 ms delay before the host-requested reset passed
three subsequent control resets, but the later STA+BLE bootstrap still failed
with that delay. The initial AP failure therefore cannot be attributed
specifically to AP or timed deep sleep, and the host delay is not a demonstrated
general fix. Testing that day stopped before the remaining profiles,
regression scripts and final display/current repeat. The 28 September
investigation fixed a separately reproduced TinyUSB queue bug and verified
70 candidate USB returns, but did not establish that bug as the cause of the
historical enumeration failures. Those unrun profiles and the new full
display/current cycle remain gaps.

Active watchdogs, active Python workers on core1, calls from core1 and hard-IRQ
calls are rejected with `EBUSY` before teardown. Applications must stop workers
and flush/close files before sleeping. Only `machine.mem_backup(2)` survives
P1.7; the Python heap, peripherals and watchdog-backed regions 0/1 do not.
USB and network sessions must be established again after boot.

Negative durations are rejected. The integer conversion limits magnitude to
2147483647 ms, including rejection of INT_MIN. Zero and 1 ms take an ordinary
reset; a deadline that expires during teardown can also take that documented
fallback. LPOSC timekeeping differs from XOSC accuracy.

The SDK's high-level Pstate helper uses POWMAN scratch[6] and [7], which would
conflict with MicroPython's public backup region. Direct `hardware_powman`
use preserves that contract. GPIO wake, other board opt-ins, RISC-V power-down
and active-watchdog integration remain outside this patch. No-argument dormant,
external-reset fault injection, broader silicon/board coverage and independent
power-domain observation remain validation gaps. Hardware evidence is limited
to one Pico 2 W; the plain Pico 2 and RP2040 checks are builds, not live tests
of this combined candidate. The unresolved bootstrap/reset failures and
unperformed tests prevent a production-ready or submission-ready claim.
Maintainer and human review are still required.

### Generative AI

Generative AI tools were used to prepare the implementation, tests and review
materials. Human validation of the code and description is still required
before submission; the submitting contributor must take responsibility for
review and maintenance. This draft does not assert that such review has
already happened.
