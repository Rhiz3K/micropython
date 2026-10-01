#!/usr/bin/env python3
# The MIT License (MIT). Copyright (c) 2026 MicroPython contributors.
"""Offline harness checks only: no serial device, firmware, or sleep is exercised."""

import ast
import binascii
from contextlib import ExitStack
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("deepsleep_host", HERE / "host.py")
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)
CONFIG = {"run": "synthetic", "cycles": 1, "sleep_ms": 2500}
MANIFEST = {"usb_serial": "synthetic", "unique_id": "0123"}


def record(status="READY", boot=1, completed=0, phase=0, **extra):
    result = {
        "protocol": 2,
        "run": "synthetic",
        "uid": "0123",
        "status": status,
        "boot": boot,
        "completed": completed,
        "phase": phase,
    }
    result.update(extra)
    return result


def frame(value):
    return host.PREFIX + json.dumps(value).encode() + b"\n"


class ProtocolTests(unittest.TestCase):
    def test_malformed_records(self):
        for payload in (b'{"status":', b"\xff", b"[]", b"null", b'{"status":"OTHER"}'):
            with self.subTest(payload=payload), self.assertRaises((ValueError, UnicodeError)):
                host.parse_record(host.PREFIX + payload)
        self.assertIsNone(host.parse_record(b"normal REPL output"))
        self.assertEqual(host.parse_record(b">>> " + frame(record())), record())

    def test_acknowledgement_scoped_to_boot_and_status(self):
        self.assertEqual(host.acknowledgement(record()), "GO synthetic 1 READY\n")
        self.assertEqual(host.acknowledgement(record("SLEEP")), "GO synthetic 1 SLEEP\n")
        self.assertEqual(host.acknowledgement(record(boot=2)), "GO synthetic 2 READY\n")

    def start_sleep(self, config=CONFIG):
        progress = host.RunProgress(config)
        progress.check(record(), 0)
        sleep = record("SLEEP", sleep_ms=config["sleep_ms"])
        progress.check(sleep, 0.1)
        progress.acknowledged(sleep, 0.2)
        return progress

    def test_complete_run_and_timing(self):
        progress = self.start_sleep()
        wake = record(boot=2, completed=1, phase=1)
        progress.check(wake, 3)
        self.assertAlmostEqual(wake["host_cycle_elapsed_s"], 2.8)
        progress.check(wake, 3.1)  # repeated READY is idempotent
        progress.check(record("PASS", boot=3, completed=1, phase=5), 4)

    def test_duplicate_sleep_keeps_first_successful_ack_time(self):
        progress = self.start_sleep()
        sleep = record("SLEEP", sleep_ms=2500)
        progress.check(sleep, 2)
        progress.acknowledged(sleep, 2)
        self.assertEqual(progress.sleep_started, 0.2)

    def test_early_wake_rejected(self):
        progress = self.start_sleep()
        with self.assertRaisesRegex(ValueError, "duration lower bound"):
            progress.check(record(boot=2, completed=1, phase=1), 1)

    def test_pass_without_complete_observation_rejected(self):
        for records in (
            [record("PASS", boot=3, completed=1, phase=5)],
            [record(), record("PASS", boot=3, completed=1, phase=5)],
            [record(boot=2, completed=1, phase=1)],
            [record(), record(boot=2, completed=1, phase=1)],
        ):
            with self.subTest(records=records), self.assertRaises(ValueError):
                progress = host.RunProgress(CONFIG)
                for value in records:
                    progress.check(value, 3)

    def test_unacknowledged_sleep_and_skipped_boot_rejected(self):
        for acknowledged, boot in ((False, 2), (True, 3)):
            progress = host.RunProgress(CONFIG)
            progress.check(record(), 0)
            sleep = record("SLEEP", sleep_ms=2500)
            progress.check(sleep, 0.1)
            if acknowledged:
                progress.acknowledged(sleep, 0.2)
            with self.assertRaisesRegex(ValueError, "acknowledged sleep"):
                progress.check(record(boot=boot, completed=1, phase=1), 4)

    def test_wrong_identity_run_count_and_legacy_protocol(self):
        with self.assertRaises(ValueError):
            host.validate_expected_record(record(run="other"), CONFIG)
        with self.assertRaises(ValueError):
            host.validate_expected_record(record("PASS", completed=2), CONFIG)
        legacy = record()
        del legacy["protocol"]
        with self.assertRaisesRegex(ValueError, "reinstall"):
            host.RunProgress(CONFIG).check(legacy, 0)

    def test_watchdog_sequence(self):
        progress = host.RunProgress(dict(CONFIG, watchdog=True))
        progress.check(record(), 0)
        progress.check(record("PASS", boot=2, phase=4), 2.5)
        with self.assertRaises(ValueError):
            progress.check(record("PASS", boot=2, phase=8), 2.5)

    def test_watchdog_after_reset_sequence(self):
        config = dict(CONFIG, watchdog=True, watchdog_after_reset=True)
        progress = host.RunProgress(config)
        progress.check(record(watchdog_after_reset=True), 0)
        timeout = record(
            boot=2, phase=4, watchdog_after_reset=True, watchdog_reason=1, watchdog_ctrl=0
        )
        progress.check(timeout, 2.1)
        progress.check(timeout, 2.2)  # Repeated timeout READY is idempotent.
        sleep = record("SLEEP", boot=2, sleep_ms=2500, watchdog_after_reset=True)
        progress.check(sleep, 2.3)
        progress.acknowledged(sleep, 2.4)
        wake = record(boot=3, completed=1, phase=1, watchdog_after_reset=True)
        progress.check(wake, 5.1)
        final = record("PASS", boot=4, completed=1, phase=5, watchdog_after_reset=True)
        host.validate_expected_record(final, config)
        progress.check(final, 5.2)

    def test_watchdog_after_reset_cannot_skip_timeout_or_deep_sleep(self):
        config = dict(CONFIG, watchdog=True, watchdog_after_reset=True)
        progress = host.RunProgress(config)
        progress.check(record(), 0)
        with self.assertRaises(ValueError):
            progress.check(record("SLEEP", sleep_ms=2500), 0.1)
        with self.assertRaises(ValueError):
            progress.check(record(boot=2, completed=1, phase=1), 3)
        progress.check(record(boot=2, phase=4, watchdog_reason=1, watchdog_ctrl=0), 2)
        with self.assertRaises(ValueError):
            progress.check(record("PASS", boot=3, completed=1, phase=5), 3)
        with self.assertRaises(ValueError):
            progress.check(record(boot=3, completed=1, phase=1), 5)
        with self.assertRaises(ValueError):
            host.validate_expected_record(
                record("PASS", boot=2, phase=4, watchdog_after_reset=True), config
            )
        with self.assertRaisesRegex(ValueError, "scenario marker"):
            host.validate_expected_record(record(), config)

    def test_watchdog_after_reset_requires_actual_inactive_timeout(self):
        config = dict(CONFIG, watchdog=True, watchdog_after_reset=True)
        for extra in (
            {"watchdog_reason": 2},
            {"watchdog_reason": None},
            {"watchdog_ctrl": 1 << 30},
            {"watchdog_ctrl": None},
            {"boot": 3},
            {"completed": 1},
        ):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                progress = host.RunProgress(config)
                progress.check(record(), 0)
                timeout = record(boot=2, phase=4, watchdog_reason=1, watchdog_ctrl=0)
                timeout.update(extra)
                progress.check(timeout, 2)

    def test_watchdog_after_reset_config_restrictions(self):
        config = dict(CONFIG, watchdog=True, watchdog_after_reset=True)
        host.validate_watchdog_config(config)
        host.validate_watchdog_config(dict(CONFIG, watchdog=True))
        for extra in (
            {"watchdog": False},
            {"watchdog_after_reset": "true"},
            {"mode": "lightsleep_reset"},
            {"expect_deep_cause": False},
            {"sleep_ms": 1},
            {"cycles": 0},
            {"cycles": -1},
            {"cycles": 1.5},
            {"cycles": True},
        ):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                host.validate_watchdog_config(dict(config, **extra))

    def test_zero_duration(self):
        progress = self.start_sleep(dict(CONFIG, sleep_ms=0))
        progress.check(record(boot=2, completed=1, phase=1), 0.2)


class FakeClock:
    now = 0.0

    def monotonic(self):
        return self.now

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeSerial:
    in_waiting = 0

    def __init__(self, events, clock):
        self.events = iter(events)
        self.clock = clock
        self.writes = []
        self.closed = False

    def read(self, _):
        self.clock.sleep(0.2)
        event = next(self.events, b"")
        if isinstance(event, Exception):
            raise event
        if isinstance(event, tuple):
            delay, event = event
            self.clock.sleep(delay)
        return event

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        pass

    def close(self):
        self.closed = True


class ObserveTests(unittest.TestCase):
    def observe(self, sessions, error=None, config=CONFIG):
        clock = FakeClock()
        connections = [FakeSerial(events, clock) for events in sessions]
        pending = iter(connections)
        serial = types.SimpleNamespace(
            Serial=lambda *a, **kw: next(pending), SerialException=OSError
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text(json.dumps(config))
            args = types.SimpleNamespace(
                allow_run=True,
                config=root / "config.json",
                log=root / "log.jsonl",
                timeout=8,
            )
            with ExitStack() as stack:
                stack.enter_context(patch.dict(sys.modules, {"serial": serial}))
                stack.enter_context(patch.object(host, "time", clock))
                stack.enter_context(
                    patch.object(host, "port_for", return_value="synthetic-no-device")
                )
                stack.enter_context(patch("sys.stdout", new_callable=io.StringIO))
                if error is None:
                    host.observe(args, MANIFEST)
                else:
                    with self.assertRaises(error):
                        host.observe(args, MANIFEST)
            records = [json.loads(line) for line in args.log.read_text().splitlines()]
        self.assertTrue(all(connection.closed for connection in connections))
        return records, connections

    def test_malformed_and_truncated_usb_reconnect_then_complete(self):
        records, connections = self.observe(
            [
                [
                    host.PREFIX + b'{"status":\n',
                    frame(record()),
                    frame(record("SLEEP", sleep_ms=2500)),
                    host.PREFIX + b'{"sta',
                    OSError("USB gone"),
                ],
                [
                    (2.5, frame(record(boot=2, completed=1, phase=1))),
                    frame(record("PASS", boot=3, completed=1, phase=5)),
                ],
            ]
        )
        self.assertEqual(
            [r["host_event"] for r in records if "host_event" in r],
            ["malformed_record", "truncated_record_on_disconnect"],
        )
        self.assertEqual(records[-1]["status"], "PASS")
        self.assertEqual(
            connections[0].writes,
            [b"\nHELLO\n", b"GO synthetic 1 READY\n", b"GO synthetic 1 SLEEP\n"],
        )

    def test_watchdog_after_reset_reconnect_and_complete(self):
        config = dict(CONFIG, watchdog=True, watchdog_after_reset=True)
        records, connections = self.observe(
            [
                [frame(record(watchdog_after_reset=True)), OSError("WDT reset")],
                [
                    frame(
                        record(
                            boot=2,
                            phase=4,
                            watchdog_after_reset=True,
                            watchdog_reason=1,
                            watchdog_ctrl=0,
                        )
                    ),
                    frame(record("SLEEP", boot=2, sleep_ms=2500, watchdog_after_reset=True)),
                    OSError("deep sleep"),
                ],
                [
                    (2.5, frame(record(boot=3, completed=1, phase=1, watchdog_after_reset=True))),
                    frame(record("PASS", boot=4, completed=1, phase=5, watchdog_after_reset=True)),
                ],
            ],
            config=config,
        )
        self.assertEqual(records[-1]["completed"], 1)
        self.assertEqual(records[-1]["phase"], 5)
        self.assertIn(b"GO synthetic 2 READY\n", connections[1].writes)
        self.assertIn(b"GO synthetic 2 SLEEP\n", connections[1].writes)

    def test_repeated_bad_json_cannot_extend_timeout_or_pass(self):
        records, connections = self.observe(
            [[host.PREFIX + b'{"status":"PASS"\n'] * 100], TimeoutError
        )
        self.assertTrue(all(r.get("status") != "PASS" for r in records))
        self.assertEqual(connections[0].writes, [b"\nHELLO\n"])
        self.assertLess(len(records), 100)

    def test_wrong_uid_never_acknowledged(self):
        _, connections = self.observe([[frame(record(uid="other"))]], ValueError)
        self.assertEqual(connections[0].writes, [b"\nHELLO\n"])

    def test_device_fail_remains_failure(self):
        records, _ = self.observe([[frame(record("FAIL", error="synthetic"))]], RuntimeError)
        self.assertEqual(records[-1]["status"], "FAIL")


class InstallTests(unittest.TestCase):
    def test_invalid_sleep_duration_is_rejected_before_device_access(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            args = types.SimpleNamespace(allow_write=True, config=config_path)
            for duration in (True, -1, 2147483648, 2.5):
                config_path.write_text(json.dumps(dict(CONFIG, sleep_ms=duration)))
                with self.subTest(duration=duration), self.assertRaisesRegex(
                    ValueError, "sleep_ms in"
                ):
                    host.install(args, MANIFEST)

    def test_staged_install_never_resets_or_starts_main(self):
        for no_reset in (True, False):
            commands = []
            writes = []
            board = types.SimpleNamespace(
                enter_raw_repl=lambda **kwargs: self.assertFalse(kwargs["soft_reset"]),
                fs_put=lambda source, destination: writes.append(destination),
                exec_raw_no_follow=commands.append,
                close=lambda: None,
            )

            def execute(command):
                commands.append(command)
                if "unique_id" in command:
                    return json.dumps({"uid": "0123", "machine": "RP2350"}).encode()
                if "os.listdir" in command:
                    return b"[]"
                return b""

            board.exec_ = execute
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "config.json").write_text(json.dumps(CONFIG))
                args = types.SimpleNamespace(
                    allow_write=True,
                    config=root / "config.json",
                    manifest=root / "manifest.json",
                    replace_main=False,
                    no_reset=no_reset,
                )
                with patch.dict(
                    sys.modules, {"pyboard": types.SimpleNamespace(Pyboard=lambda _: board)}
                ), patch.object(host, "port_for", return_value="synthetic-no-device"), patch(
                    "sys.stdout", new_callable=io.StringIO
                ):
                    host.install(args, dict(MANIFEST, machine_contains="RP2350"))
            with self.subTest(no_reset=no_reset):
                self.assertEqual(writes, ["main.py"])
                self.assertTrue(any("machine.mem_backup(2)[0] = 0" in cmd for cmd in commands))
                self.assertEqual(any("machine.reset()" in cmd for cmd in commands), not no_reset)
                self.assertFalse(any("exec(open" in cmd for cmd in commands))


class SimulatedReset(BaseException):
    pass


class DeviceStateTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((HERE / "device.py").read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.config = dict(CONFIG)
        self.state = [0x44535032, 0, 100, 0, 0, 1, 0, 0x13579BDF]
        self.machine = types.SimpleNamespace(
            mem_backup=lambda _: [[0] * 8, [0] * 8, self.state],
            unique_id=lambda: b"\x01\x23",
            reset_cause=lambda: 4,
            RTC=lambda: types.SimpleNamespace(datetime=lambda: (2026, 9, 26, 5, 0, 0, 1, 0)),
            mem32={0x4010002C: 0, 0x401000A0: 64, 0x400D8000: 0, 0x400D8008: 1},
            DEEPSLEEP_RESET=4,
            WDT_RESET=3,
            WDT=lambda **kwargs: None,
        )
        self.namespace = {
            "machine": self.machine,
            "json": json,
            "binascii": binascii,
            "MAGIC": self.state[0],
            "SENTINEL": b"sentinel",
            "EBUSY": 16,
            "WATCHDOG_CTRL": 0x400D8000,
            "WATCHDOG_REASON": 0x400D8008,
            "WATCHDOG_ENABLE": 1 << 30,
            "WATCHDOG_REASON_TIMER": 1,
            "open": lambda name, *a: (
                io.StringIO(json.dumps(self.config))
                if name.endswith(".json")
                else io.BytesIO(b"sentinel")
            ),
        }
        exec(
            compile(ast.Module(body=functions, type_ignores=[]), "device.py", "exec"),
            self.namespace,
        )
        self.namespace["rtc_seconds"] = lambda: 103
        self.namespace["wait_for_host"] = lambda _: None

    def test_wake_consumed_before_reporting_and_soft_reset_not_double_counted(self):
        self.state[3] = 1
        self.namespace["wait_for_host"] = lambda _: (_ for _ in ()).throw(SimulatedReset())
        with self.assertRaises(SimulatedReset):
            self.namespace["run"]()
        self.assertEqual((self.state[1], self.state[3]), (1, 7))
        with self.assertRaisesRegex(AssertionError, "already consumed"):
            self.namespace["run"]()
        self.assertEqual(self.state[1], 1)

    def test_watchdog_cannot_pass_before_busy_was_confirmed(self):
        self.config["watchdog"] = True
        self.machine.deepsleep = lambda _: (_ for _ in ()).throw(SimulatedReset())
        with self.assertRaises(SimulatedReset):
            self.namespace["run"]()
        self.assertEqual(self.state[3], 8)
        self.machine.reset_cause = lambda: 3
        with self.assertRaisesRegex(AssertionError, "before deepsleep rejection"):
            self.namespace["run"]()

    def test_confirmed_watchdog_phase_accepts_watchdog_reset(self):
        self.state[3] = 4
        self.machine.reset_cause = lambda: 3
        emitted = []
        self.namespace["wait_for_host"] = emitted.append
        self.namespace["run"]()
        self.assertEqual(emitted[0]["status"], "PASS")
        self.assertEqual(self.state[3], 2)

    def test_watchdog_after_reset_runs_deep_sleep_without_rearming(self):
        self.config.update(watchdog=True, watchdog_after_reset=True)
        self.state[3] = 4
        self.machine.reset_cause = lambda: 3
        self.machine.WDT = lambda **kwargs: self.fail("watchdog rearmed after its timeout")
        self.namespace["os"] = types.SimpleNamespace(sync=lambda: None)
        self.machine.RTC = lambda: types.SimpleNamespace(datetime=lambda *args: None)
        self.machine.deepsleep = lambda _: (_ for _ in ()).throw(SimulatedReset())
        emitted = []
        self.namespace["wait_for_host"] = lambda value: emitted.append(dict(value))
        with self.assertRaises(SimulatedReset):
            self.namespace["run"]()
        self.assertEqual(
            [(r["status"], r.get("phase")) for r in emitted], [("READY", 4), ("SLEEP", None)]
        )
        self.assertEqual((self.state[1], self.state[3]), (0, 1))
        self.machine.reset_cause = lambda: 4
        self.namespace["rtc_seconds"] = lambda: 106
        self.machine.reset = lambda: (_ for _ in ()).throw(SimulatedReset())
        with self.assertRaises(SimulatedReset):
            self.namespace["run"]()
        self.assertEqual((self.state[1], self.state[3]), (1, 5))
        self.machine.reset_cause = lambda: 3
        self.namespace["run"]()
        self.assertEqual(
            (emitted[-1]["status"], emitted[-1]["completed"], emitted[-1]["phase"]), ("PASS", 1, 5)
        )

    def test_watchdog_after_reset_consumed_before_host_wait(self):
        self.config.update(watchdog=True, watchdog_after_reset=True)
        self.state[3] = 4
        self.machine.reset_cause = lambda: 3
        self.namespace["wait_for_host"] = lambda _: (_ for _ in ()).throw(SimulatedReset())
        with self.assertRaises(SimulatedReset):
            self.namespace["run"]()
        self.assertEqual((self.state[1], self.state[3]), (0, 9))
        with self.assertRaisesRegex(AssertionError, "consumed watchdog"):
            self.namespace["run"]()

    def test_watchdog_after_reset_rejects_running_or_non_timeout_watchdog(self):
        self.config.update(watchdog=True, watchdog_after_reset=True)
        self.state[3] = 4
        self.machine.reset_cause = lambda: 3
        for ctrl, reason, error in ((1 << 30, 1, "still enabled"), (0, 2, "timeout required")):
            self.machine.mem32[0x400D8000] = ctrl
            self.machine.mem32[0x400D8008] = reason
            with self.subTest(ctrl=ctrl, reason=reason), self.assertRaisesRegex(
                AssertionError, error
            ):
                self.namespace["run"]()
            self.assertEqual((self.state[1], self.state[3]), (0, 4))

    def test_watchdog_pass_phase_written_only_after_busy(self):
        class ResetAtArming(list):
            def __setitem__(self, key, value):
                super().__setitem__(key, value)
                if key == 3 and value == 4:
                    raise SimulatedReset()

        self.config["watchdog"] = True
        self.state = ResetAtArming(self.state)
        busy_phases = []

        def busy(_):
            busy_phases.append(self.state[3])
            raise OSError(16)

        self.machine.deepsleep = busy
        with self.assertRaises(SimulatedReset):
            self.namespace["run"]()
        self.assertEqual(busy_phases, [8])
        self.assertEqual(self.state[3], 4)

    def test_stale_or_wrong_status_ack_cannot_release_device(self):
        incoming = io.StringIO(
            "GO synthetic\nGO synthetic 0 READY\nGO synthetic 1 SLEEP\nGO synthetic 1 READY\n"
        )
        self.namespace.update(
            {
                "select": types.SimpleNamespace(
                    POLLIN=1,
                    poll=lambda: types.SimpleNamespace(
                        register=lambda *a: None, poll=lambda _: [(0, 1)]
                    ),
                ),
                "sys": types.SimpleNamespace(stdin=incoming),
                "time": types.SimpleNamespace(
                    ticks_ms=lambda: 0, ticks_diff=lambda a, b: a - b, ticks_add=lambda a, b: a + b
                ),
                "emit": lambda _: None,
            }
        )
        # Restore the actual function overridden by setUp.
        tree = ast.parse((HERE / "device.py").read_text())
        function = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "wait_for_host"
        )
        exec(
            compile(ast.Module(body=[function], type_ignores=[]), "device.py", "exec"),
            self.namespace,
        )
        self.namespace["wait_for_host"](record())
        self.assertEqual(incoming.read(), "")

    def test_sleep_phase_and_rtc_seed_follow_sleep_ack(self):
        self.namespace["os"] = types.SimpleNamespace(sync=lambda: None)
        rtc_writes = []
        self.machine.RTC = lambda: types.SimpleNamespace(
            datetime=lambda *args: rtc_writes.extend(args) if args else ()
        )

        def wait(value):
            if value["status"] == "SLEEP":
                self.assertEqual(self.state[3], 0)
                self.assertEqual(rtc_writes, [])

        self.namespace["wait_for_host"] = wait
        self.machine.deepsleep = lambda _: (_ for _ in ()).throw(SimulatedReset())
        with self.assertRaises(SimulatedReset):
            self.namespace["run"]()
        self.assertEqual(self.state[3], 1)
        self.assertEqual(rtc_writes, [(2026, 9, 25, 4, 23, 59, 58, 0)])

    def test_regression_guard_rejects_baseline_before_any_sleep(self):
        tree = ast.parse((HERE / "regressions.py").read_text())
        guard = next(node for node in tree.body if isinstance(node, ast.If))
        code = compile(ast.Module(body=[guard], type_ignores=[]), "regressions.py", "exec")
        for platform, model, capability, accepted in (
            ("rp2", "Raspberry Pi Pico 2 W with RP2350", False, False),
            ("rp2", "Raspberry Pi Pico with RP2040", True, False),
            ("esp32", "RP2350", True, False),
            ("rp2", "Raspberry Pi Pico 2 W with RP2350", True, True),
        ):
            machine = types.SimpleNamespace()
            if capability:
                machine.DEEPSLEEP_RESET = 4
            namespace = {
                "machine": machine,
                "sys": types.SimpleNamespace(
                    platform=platform, implementation=types.SimpleNamespace(_machine=model)
                ),
            }
            with self.subTest(platform=platform, model=model, capability=capability):
                if accepted:
                    exec(code, namespace)
                else:
                    with self.assertRaises(RuntimeError):
                        exec(code, namespace)


if __name__ == "__main__":
    unittest.main()
