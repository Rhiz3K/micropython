#!/usr/bin/env python3
# The MIT License (MIT). Copyright (c) 2026 MicroPython contributors.
"""Offline tests of deadline handling, without executing the hardware suite."""

import ast
from pathlib import Path
import types
import unittest


HERE = Path(__file__).resolve().parent
TICKS_PERIOD = 1 << 30


class SimulatedReset(BaseException):
    pass


class FakeClock:
    def __init__(self, elapsed=0):
        self.elapsed = elapsed

    def ticks_ms(self):
        return self.elapsed % TICKS_PERIOD

    def ticks_add(self, ticks, duration):
        if not -TICKS_PERIOD // 2 < duration < TICKS_PERIOD // 2:
            raise ValueError("ticks interval out of range")
        return (ticks + duration) % TICKS_PERIOD

    def ticks_diff(self, end, start):
        return (end - start + TICKS_PERIOD // 2) % TICKS_PERIOD - TICKS_PERIOD // 2


class LightsleepResetTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.requests = []
        self.reset_times = []
        self.early_wakes = []
        self.sleep_error = None
        tree = ast.parse((HERE / "device.py").read_text())
        helper = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "lightsleep_reset"
        )
        namespace = {
            "time": self.clock,
            "machine": types.SimpleNamespace(lightsleep=self.lightsleep, reset=self.reset),
        }
        exec(
            compile(ast.Module(body=[helper], type_ignores=[]), "device.py", "exec"),
            namespace,
        )
        self.run = namespace["lightsleep_reset"]

    def lightsleep(self, duration):
        self.requests.append(duration)
        # Model the actual RP2 alarm limit, rather than accepting arbitrary waits.
        if duration >= (1 << 32) // 1000:
            raise ValueError("sleep too long")
        if self.sleep_error is not None:
            raise self.sleep_error
        elapsed = self.early_wakes.pop(0) if self.early_wakes else duration
        self.clock.elapsed += elapsed

    def reset(self):
        self.reset_times.append(self.clock.elapsed)
        raise SimulatedReset()

    def check_duration(self, duration):
        started = self.clock.elapsed
        with self.assertRaises(SimulatedReset):
            self.run(duration)
        self.assertEqual(self.reset_times, [started + duration])
        self.assertTrue(all(0 < requested <= 60000 for requested in self.requests))

    def test_zero_resets_without_sleeping(self):
        self.check_duration(0)
        self.assertEqual(self.requests, [])

    def test_one_millisecond(self):
        self.check_duration(1)

    def test_repeated_early_wakes_do_not_reset_early(self):
        self.early_wakes = [0, 1, 37, 120]
        self.check_duration(2500)
        self.assertGreater(len(self.requests), 1)

    def test_deadline_crosses_ticks_wrap(self):
        self.clock.elapsed = TICKS_PERIOD - 500
        self.early_wakes = [100, 450]
        self.check_duration(2500)

    def test_late_wake_does_not_start_another_sleep(self):
        self.early_wakes = [2700]
        with self.assertRaises(SimulatedReset):
            self.run(2500)
        self.assertEqual(self.reset_times, [2700])
        self.assertEqual(len(self.requests), 1)

    def test_seventy_five_minutes_exceeds_single_alarm_limit(self):
        self.check_duration(4500000)
        self.assertGreater(len(self.requests), 1)

    def test_duration_exceeds_ticks_half_period(self):
        self.check_duration(TICKS_PERIOD // 2 + 1)

    def test_exception_does_not_reset(self):
        self.sleep_error = OSError("sleep failed")
        with self.assertRaisesRegex(OSError, "sleep failed"):
            self.run(2500)
        self.assertEqual(self.reset_times, [])

    def test_keyboard_interrupt_does_not_reset(self):
        self.sleep_error = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run(2500)
        self.assertEqual(self.reset_times, [])


if __name__ == "__main__":
    unittest.main()
