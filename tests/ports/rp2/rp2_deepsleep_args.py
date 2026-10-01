# Test argument validation and hard-IRQ rejection without entering deep sleep.
import sys

try:
    import machine
except ImportError:
    print("SKIP")
    raise SystemExit

# Baseline deepsleep(-1) can request about 49 days of sleep. Require the
# ARM RP2350 implementation before making any call, including invalid ones.
model = getattr(sys.implementation, "_machine", "")
if not (
    sys.platform == "rp2"
    and "RP2350" in model
    and "RISCV" not in model
    and hasattr(machine, "DEEPSLEEP_RESET")
):
    print("SKIP")
    raise SystemExit


def check_exception(value, exception):
    try:
        machine.deepsleep(value)
    except exception:
        print(exception.__name__)
    else:
        raise AssertionError("invalid sleep duration accepted")


check_exception(-1, ValueError)
check_exception(-((1 << 31) - 1), ValueError)
check_exception(-(1 << 31), OverflowError)
check_exception(-(1 << 31) - 1, OverflowError)
check_exception(1 << 31, OverflowError)
check_exception(1 << 100, OverflowError)

import errno
import micropython
import time

EBUSY = getattr(errno, "EBUSY", 16)
micropython.alloc_emergency_exception_buf(100)
result = [0]


def callback(_):
    try:
        # The IRQ guard precedes the zero-duration ordinary-reset path. If that
        # guard regresses this may reset the board and fail the test transport,
        # but it cannot enter the timed power-down state. Positive durations are
        # covered separately by the opt-in reset-spanning hardware suite.
        machine.deepsleep(0)
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
    print("hard IRQ EBUSY")
finally:
    timer.deinit()
