# Draft for human review — not submitted

Suggested title: `rp2: Add timed RP2350 power-down deepsleep.`

This experimental patch has completed 100 timed sleep/wake cycles on one
Pico 2 W. Current and cycle energy have not been measured, so this is not a
claim of verified power savings or production readiness. See RESULTS.md for
the full PASS/FAIL/NOT RUN matrix, including incomplete Wi-Fi validation.

### Summary

On RP2350, `machine.deepsleep(ms)` currently calls `lightsleep(ms)` and then
resets, keeping the switched power domains supplied during sleep. This patch
adds a timed POWMAN path for the ARM variants of RPI_PICO2 and RPI_PICO2_W.
It requests P1.7, with switched core, XIP cache and both SRAM domains off;
the AON timer runs from LPOSC and requests an ordinary ROM boot at its alarm.
Python execution starts again from boot.py/main.py. RTC time and the 32-byte
POWMAN backup region survive independently of the Python heap.

The path stops CYW43, disconnects USB, drains DMA using the RP2350-E5 abort
sequence, and prevents IRQ callbacks from restarting work during teardown.
It includes the pinned SDK's SRAM WFI preparation sequence, with its original
BSD attribution. Hardware reset/wake records identify DEEPSLEEP_RESET without
claiming a scratch register. Alarm wake is disabled on the subsequent boot.
A rejected or cancelled transition takes an ordinary reset instead of reporting
a successful deep wake. Once POWMAN reports a committed transition, its alarm
is kept armed even if the SDK's WAITING-only poll returned a timeout.

Existing lightsleep behavior, RP2040 behavior, no-argument deepsleep and
RP2350 RISC-V remain unchanged. The patch builds on the already merged RTC
and frequency fixes in #19694, #19712 and #19582; it does not reimplement them.
Related discussion: #15623. No SDK or shared-port dependency is changed.

### Testing

Base: `09f5bb447504a058376c62fe991b3613531837e6`.
Pico SDK: `98a542c1a62fb549ffb5d66a3e5892b06276b670` (2.3.0).
Tools: Arm GNU Toolchain 14.3.rel1 / GCC 14.3.1, CMake 4.4.3, GNU Make 4.3.
`reproduce.sh` builds unmodified RPI_PICO2_W and RPI_PICO first, applies the
firmware patch, then builds RPI_PICO2_W, RPI_PICO2 and RPI_PICO. It writes
per-build logs, source revisions, size reports and artifact checksums.
The baseline builds and all three patched ARM board builds passed. On
RPI_PICO2_W the ELF text/data total increases by 1,616 bytes; BSS is unchanged.
The complete clean-clone reproduction passed all five builds; its Pico 2 W
UF2 is byte-identical to the hardware-tested image.

A Pico 2 W was identified and its original flash backed up before testing.
The final candidate passed 100 consecutive `deepsleep(2500)` cycles, followed
by an ordinary reset. The restart-aware harness records fresh boots, USB
reconnection, `DEEPSLEEP_RESET` on all 100 timer wakes, and the existing
ordinary-reset cause after the final reset. Each timer wake records both
`HAD_SWCORE_PD` and the AON alarm wake source. RTC continuity passed across
a day boundary and seven minute boundaries. POWMAN backup data and a file
sentinel survived; watchdog scratch regions did not, as documented. The
harness does not write flash on every cycle. Evidence is retained in
`patch-final-100.jsonl`; elapsed host time was approximately 378 seconds,
including reboot, USB reconnection and the final reset.

Final RPI_PICO2_W UF2 SHA256:
`a10041bf6b02177f37eb1d396bff023e9261802d59bcc8874749e8f458b2f9bb`.

The first experimental candidate disconnected USB and failed to return before
the host timeout. That attempt remains FAIL in the retained history. Subsequent
diagnosis exposed an already committed POWMAN transition while the SDK reported
a timeout; cancelling it caused premature wake. The final path preserves the
alarm and completes the committed transition.

Additional hardware checks passed for active CPU1/caller-on-CPU1 rejection,
active watchdog rejection with subsequent watchdog expiry, active RAM DMA,
lightsleep-before-deepsleep, zero/1 ms ordinary resets, three 20 ms deep wakes,
negative/overflow arguments, and hard-IRQ rejection. Existing RTC/lightsleep
register/thread/frequency tests passed; rp2_lightsleep.py required an explicit
pre-import of machine because the existing test omits it. The idle timing test
failed in the earlier active-test context, then passed after a clean reset on
both patched firmware and baseline. The strict 2 ms deep-wake check failed:
it took the documented ordinary-reset fallback, without false deep attribution.

Wi-Fi validation is **not a full PASS**: DHCP/DNS/HTTP succeeded after three
deep wakes, then a reconnect timed out. A baseline control also timed out at
its initial connection before any sleep, with WLAN status 2 (no IP). A patched
retry with a 60-second limit failed in the same pre-sleep state. This does not
establish a deepsleep regression, but reliable network recovery remains
unverified and needs investigation on a controlled network.

The 30-minute/75-minute sleeps, no-argument dormant, external-reset fault
injection, power/current/energy measurements, independent observation of every
power domain, physical Pico 2 comparison and RISC-V build/hardware validation
have not been performed. The implementation remains experimental.

### Trade-offs and Alternatives

This initial version rejects an active watchdog, active Python worker on
core1, calls on core1, and IRQ-context calls with EBUSY. Applications must
stop workers and flush/close files before reset-like deepsleep. The initial
positive argument range is at most 2147483647 milliseconds. Negative values
are rejected; the existing integer converter raises OverflowError when the
magnitude exceeds 2147483647, including INT_MIN.
Zero and one millisecond use the existing delay/reset semantics, and intervals
that expire during teardown can complete as an ordinary reset.

USB and network sessions are lost and must be established again. LPOSC sleep
timekeeping has different accuracy from XOSC. Only `machine.mem_backup(2)`
survives P1.7; watchdog-backed regions 0 and 1 reset with switched-core power.
That retention change is documented explicitly.

The high-level SDK pico_low_power Pstate path uses POWMAN scratch[6] and [7]
for state and a callback pointer, conflicting with MicroPython's public
backup-memory layout. Using hardware_powman directly avoids that collision.
GPIO wake, other boards, RISC-V power-down and active-watchdog integration
remain follow-up work. Broader hardware validation and measured board current
and cycle energy are required before treating this as production-ready.

### Generative AI

Generative AI tools were used to prepare the implementation, tests and review
materials. Human validation of the code and description is still required
before submission; the submitting contributor must take responsibility for
review and maintenance. This draft does not assert that such review has
already happened.

### Follow-up before submission (2026-09-26)

During runtime CYW43 trace diagnostics (`trace=7`), USB REPL became
unresponsive. Subsequent host USB reset and hub power-cycle requests did not
restore enumeration. No firmware was changed during that diagnostic. Actual
VBUS removal was not measured and a physical power cycle remains outstanding
on the original board. This observation does not identify a root cause or
prove a deepsleep regression. Prefer router-side DHCP capture for the next
network experiment. See HANDOVER.cs.md for the continuation plan.
