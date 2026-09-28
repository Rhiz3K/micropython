#!/usr/bin/env python3
# The MIT License (MIT). Copyright (c) 2026 MicroPython contributors.
"""Install/observe the opt-in RP2350 reset-spanning test. Never flashes firmware."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PREFIX = b"DEEPSLEEP_TEST "
RADIO_MODES = ("never", "sta", "ap", "ble", "sta_ble", "sta_ap")


def validate_radio_config(config):
    mode = config.get("radio")
    if mode is None:
        if "ap" in config:
            raise ValueError("ap configuration requires radio=ap or sta_ap")
        return
    if mode not in RADIO_MODES:
        raise ValueError("unknown radio test mode")
    if "wifi" in config and mode not in ("sta", "sta_ble"):
        raise ValueError("wifi transaction requires radio=sta or sta_ble")
    if mode in ("ap", "sta_ap"):
        ap = config.get("ap")
        if not isinstance(ap, dict):
            raise ValueError("AP test requires private ap configuration")
        ssid = ap.get("ssid")
        if not isinstance(ssid, str) or not ssid.startswith("rp2350-sleep-test"):
            raise ValueError("AP SSID must start with rp2350-sleep-test")
        if not 1 <= len(ssid.encode()) <= 32:
            raise ValueError("AP SSID must fit 32 bytes")
        password = ap.get("password")
        if not isinstance(password, str) or not 8 <= len(password) <= 63:
            raise ValueError("AP password must contain 8..63 printable ASCII characters")
        if any(not 32 <= ord(char) <= 126 for char in password):
            raise ValueError("AP password must contain 8..63 printable ASCII characters")
    elif "ap" in config:
        raise ValueError("ap configuration requires radio=ap or sta_ap")


def ports():
    from serial.tools import list_ports

    return list(list_ports.comports())


def validate_expected_record(record, config):
    if config is None:
        return
    if record.get("run") != config["run"]:
        raise ValueError("record does not belong to the expected run")
    if config.get("radio") is not None and record.get("radio_mode") != config["radio"]:
        raise ValueError("record radio mode does not match configuration")
    if record.get("status") == "PASS":
        expected = 0 if config.get("watchdog") else config.get("cycles", 100)
        if type(record.get("completed")) is not int or record["completed"] != expected:
            raise ValueError("PASS completed count does not match configuration")


def load_manifest(path):
    data = json.loads(path.read_text())
    if not data.get("authorized") or not data.get("bootsel_recovery_confirmed"):
        raise ValueError("manifest must attest authorization and BOOTSEL recovery")
    for key in ("usb_serial", "unique_id", "machine_contains"):
        if not data.get(key):
            raise ValueError("missing identity field: " + key)
    for key in ("firmware_backup", "filesystem_backup"):
        backup = data[key]
        source = (path.parent / backup["path"]).resolve()
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != backup["sha256"]:
            raise ValueError("backup checksum mismatch: " + str(source))
    return data


def port_for(manifest):
    found = [p for p in ports() if p.serial_number == manifest["usb_serial"]]
    if len(found) > 1:
        raise ValueError("USB serial is not unique")
    return found[0].device if found else None


def install(args, manifest):
    if not args.allow_write:
        raise ValueError("installation requires --allow-write")
    config = json.loads(args.config.read_text())
    if not isinstance(config["sleep_ms"], int) or not 0 <= config["sleep_ms"] <= 2147483647:
        raise ValueError("suite needs sleep_ms in 0..2147483647")
    if config["sleep_ms"] <= 1 and config.get("expect_deep_cause", True):
        raise ValueError("zero/1ms only request ordinary resets: set expect_deep_cause=false")
    if not config.get("run") or config.get("cycles", 100) < 1:
        raise ValueError("config requires a run name and positive cycle count")
    validate_radio_config(config)
    sys.path.insert(0, str(HERE.parents[3] / "tools"))
    from pyboard import Pyboard

    port = port_for(manifest)
    if port is None:
        raise ValueError("authorized device is not connected")
    board = Pyboard(port)
    try:
        board.enter_raw_repl(soft_reset=False)
        identity = json.loads(
            board.exec_(
                "import machine, binascii, json, sys, os; "
                "print(json.dumps({'uid':binascii.hexlify(machine.unique_id()).decode(),"
                "'machine':sys.implementation._machine}))"
            )
        )
        if identity["uid"].lower() != manifest["unique_id"].lower():
            raise ValueError("machine.unique_id mismatch")
        if manifest["machine_contains"] not in identity["machine"]:
            raise ValueError("board/architecture description mismatch: " + identity["machine"])
        if (
            config.get("radio") is not None
            and identity["machine"] != "Raspberry Pi Pico 2 W with RP2350"
        ):
            raise ValueError("radio/pin scenarios require Raspberry Pi Pico 2 W with RP2350")
        existing = json.loads(board.exec_("print(json.dumps(os.listdir()))"))
        if "main.py" in existing and not args.replace_main:
            raise ValueError("main.py exists; backed-up replacement requires --replace-main")
        if any(name.startswith("deepsleep-") for name in existing) and not args.replace_main:
            raise ValueError("test files exist; use a new backup and --replace-main")
        # The manifest attests a full backup; also retain the exact overwritten entry point.
        if "main.py" in existing:
            destination = args.manifest.parent / (config["run"] + "-main-before-install.py")
            if destination.exists():
                raise ValueError("refusing to overwrite " + str(destination))
            board.fs_get("main.py", str(destination))
        board.fs_put(str(HERE / "device.py"), "main.py")
        board.exec_(
            "with open('deepsleep-config.json','w') as f: f.write(%r)\n"
            "with open('deepsleep-sentinel.bin','wb') as f: f.write(%r)\n"
            "os.sync()\nmachine.mem_backup(2)[0] = 0\n"
            % (json.dumps(config), b"RP2350 deepsleep filesystem sentinel\n")
        )
        board.use_raw_paste = False
        # Allow the host to receive the command ACK and close CDC before reset.
        board.exec_raw_no_follow("import time; time.sleep_ms(150); machine.reset()")
    finally:
        board.close()
    print("Installed once. Start 'run'; per-cycle progress uses POWMAN scratch only.")


def observe(args, manifest):
    import serial

    if not args.allow_run:
        raise ValueError("sleep/reset execution requires --allow-run")
    expected = None
    if args.config is not None:
        expected = json.loads(args.config.read_text())
        if (
            not expected.get("run")
            or type(expected.get("cycles", 100)) is not int
            or expected.get("cycles", 100) < 1
        ):
            raise ValueError("expected config requires a run name and positive cycle count")
        validate_radio_config(expected)
    seen = set()
    started = time.monotonic()
    last_progress = started
    connection = None
    buffer = b""
    with args.log.open("x", buffering=1) as log:
        log.write(
            json.dumps({"host_start": time.time(), "usb_serial": manifest["usb_serial"]}) + "\n"
        )
        try:
            while time.monotonic() - last_progress < args.timeout:
                try:
                    if connection is None:
                        port = port_for(manifest)
                        if port is None:
                            time.sleep(0.2)
                            continue
                        connection = serial.Serial(port, 115200, timeout=0.2, exclusive=True)
                        buffer = b""
                        # Establish host presence after DTR/enumeration. This
                        # also terminates a partial line from an earlier client.
                        connection.write(b"\nHELLO\n")
                        connection.flush()
                    buffer += connection.read(connection.in_waiting or 1)
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        index = line.find(PREFIX)
                        if index < 0:
                            continue
                        record = json.loads(line[index + len(PREFIX) :])
                        record["host_elapsed_s"] = time.monotonic() - started
                        try:
                            validate_expected_record(record, expected)
                        except ValueError:
                            log.write(json.dumps(record) + "\n")
                            raise
                        status = record.get("status")
                        if status in ("FAIL", "STOPPED"):
                            log.write(json.dumps(record) + "\n")
                            raise RuntimeError(str(record))
                        if status == "SLEEP":
                            log.write(json.dumps(record) + "\n")
                            continue
                        if record.get("uid", "").lower() != manifest["unique_id"].lower():
                            raise ValueError("reconnected target identity mismatch")
                        key = (record["run"], record["boot"])
                        if key not in seen:
                            seen.add(key)
                            last_progress = time.monotonic()
                            log.write(json.dumps(record) + "\n")
                            print(json.dumps(record), flush=True)
                        connection.write(("GO " + record["run"] + "\n").encode())
                        connection.flush()
                        if status == "PASS":
                            return
                    if len(buffer) > 65536:
                        raise RuntimeError("unbounded non-test serial output")
                    if port_for(manifest) is None:
                        connection.close()
                        connection = None
                except (OSError, serial.SerialException):
                    if connection is not None:
                        connection.close()
                        connection = None
                    time.sleep(0.2)
            raise TimeoutError("No boot progress within timeout; log is incomplete, not PASS")
        finally:
            if connection is not None:
                connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="enumerate USB metadata without opening devices")
    for name in ("install", "run"):
        command = sub.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        if name == "install":
            command.add_argument("--config", type=Path, required=True)
            command.add_argument("--allow-write", action="store_true")
            command.add_argument("--replace-main", action="store_true")
        else:
            command.add_argument(
                "--config",
                type=Path,
                help="same private config as install; verify run, radio and final count",
            )
            command.add_argument("--allow-run", action="store_true")
            command.add_argument("--log", type=Path, required=True)
            command.add_argument(
                "--timeout", type=float, default=90, help="per-boot timeout, seconds"
            )
    args = parser.parse_args()
    if args.command == "list":
        for port in ports():
            print(
                json.dumps(
                    {
                        "port": port.device,
                        "usb_serial": port.serial_number,
                        "vid": port.vid,
                        "pid": port.pid,
                        "description": port.description,
                    }
                )
            )
        return
    manifest = load_manifest(args.manifest.resolve())
    if args.command == "install":
        install(args, manifest)
    else:
        observe(args, manifest)


if __name__ == "__main__":
    main()
