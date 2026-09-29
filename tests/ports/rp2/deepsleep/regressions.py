# Run explicitly via mpremote, with the installed sleep suite stopped.
# The MIT License (MIT). Copyright (c) 2026 MicroPython contributors.
import errno
import machine
import micropython
import sys
import time

# Baseline RP2 deepsleep(-1) converts to an unsigned delay (about 49 days).
# This patch exports DEEPSLEEP_RESET only when its POWMAN implementation is
# enabled. Check both port/chip and capability before any destructive call.
if not (
    sys.platform == "rp2"
    and "RP2350" in getattr(sys.implementation, "_machine", "")
    and hasattr(machine, "DEEPSLEEP_RESET")
):
    raise RuntimeError("requires RP2350 firmware with POWMAN DEEPSLEEP_RESET support")

# RP2 may omit EBUSY from the Python errno module; py/mperrno.h defines it as 16.
EBUSY = getattr(errno, "EBUSY", 16)


def expect_exception(value, types):
    try:
        machine.deepsleep(value)
    except types:
        print("PASS argument", value)
    else:
        raise AssertionError("argument accepted: " + str(value))


expect_exception(-1, ValueError)
expect_exception(-((1 << 31) - 1), ValueError)
expect_exception(-(1 << 31), OverflowError)
expect_exception(-(1 << 31) - 1, OverflowError)
expect_exception(1 << 31, OverflowError)
expect_exception(1 << 100, OverflowError)


def test_hard_irq():
    micropython.alloc_emergency_exception_buf(100)
    result = [0]

    def callback(_):
        try:
            machine.deepsleep(2000)
        except OSError as exc:
            result[0] = exc.args[0]
        except Exception:
            result[0] = -1
        else:
            result[0] = -2

    timer = machine.Timer()
    try:
        timer.init(mode=machine.Timer.ONE_SHOT, period=10, callback=callback, hard=True)
        deadline = time.ticks_add(time.ticks_ms(), 2000)
        while result[0] == 0 and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            time.sleep_ms(1)
        assert result[0] == EBUSY, result[0]
        print("PASS hard IRQ rejected with EBUSY")
    finally:
        timer.deinit()


test_hard_irq()

original = machine.freq()
try:
    machine.freq(100_000_000)
    rtc_before = time.time()
    for duration in (0, 1, 250, 1500):
        target = time.ticks_add(time.ticks_ms(), duration)
        machine.lightsleep(duration)
        # Interrupts may end lightsleep early; this is permitted by its API.
        while True:
            remaining = time.ticks_diff(target, time.ticks_ms())
            if remaining <= 0:
                break
            machine.lightsleep(remaining)
        assert machine.freq() == 100_000_000
    assert time.time() >= rtc_before + 1
    print("PASS lightsleep clock restoration and time progress")
finally:
    machine.freq(original)
