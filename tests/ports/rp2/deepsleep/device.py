# Install as main.py on an identified, backed-up test board. See README.md.
# The MIT License (MIT). Copyright (c) 2026 MicroPython contributors.
import binascii
import errno
import json
import machine
import os
import select
import sys
import time

MAGIC = 0x44535032
SENTINEL = b"RP2350 deepsleep filesystem sentinel\n"
PREFIX = "DEEPSLEEP_TEST "
# RP2 may omit EBUSY from the Python errno module; py/mperrno.h defines it as 16.
EBUSY = getattr(errno, "EBUSY", 16)
last_record = {}


def rtc_seconds():
    r = machine.RTC().datetime()
    return time.mktime((r[0], r[1], r[2], r[4], r[5], r[6], 0, 0))


def check(condition, description):
    if not condition:
        raise AssertionError(description)


def backup_pattern(region, index):
    return 0x23450000 + region * 256 + index


def emit(record):
    print(PREFIX + json.dumps(record))


def wait_for_host(record):
    # No reset/soft-reset by the host: each boot runs main.py independently.
    # Repeat until acknowledged so USB enumeration cannot lose the boot result.
    poll = select.poll()
    poll.register(sys.stdin, select.POLLIN)
    line = ""
    next_emit = time.ticks_ms()
    while True:
        if time.ticks_diff(time.ticks_ms(), next_emit) >= 0:
            emit(record)
            next_emit = time.ticks_add(time.ticks_ms(), 1000)
        for _, events in poll.poll(100):
            # HUP/error is not input. Read one available ASCII character so a
            # disconnect or partial host command cannot block the next report.
            if events & select.POLLIN:
                char = sys.stdin.read(1)
                if char == "\n":
                    if line.strip() == "GO " + record["run"]:
                        return
                    line = ""
                elif char != "\r":
                    line = (line + char)[-128:]


def wifi_test(config):
    import network
    import socket

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    timeout = config.get("connect_timeout_ms", 30000)
    check(0 < timeout <= 600000, "Wi-Fi timeout must be in 1..600000 ms")
    started = time.ticks_ms()
    wlan.connect(config["ssid"], config["password"])
    deadline = time.ticks_add(started, timeout)
    while not wlan.isconnected():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            raise AssertionError(
                "Wi-Fi/DHCP timeout after {} ms, status {}".format(timeout, wlan.status())
            )
        time.sleep_ms(100)
    connected_ms = time.ticks_diff(time.ticks_ms(), started)
    host = config["host"]
    address = socket.getaddrinfo(host, config.get("port", 80))[0][-1]
    dns_host = config.get("dns_host", host)
    dns_address = address if dns_host == host else socket.getaddrinfo(dns_host, 80)[0][-1]
    sock = socket.socket()
    try:
        sock.settimeout(10)
        sock.connect(address)
        request = "GET {} HTTP/1.0\r\nHost: {}\r\n\r\n".format(config.get("path", "/"), host)
        sock.write(request.encode())
        status = sock.readline()
        check(status.startswith(b"HTTP/") and b" 200 " in status, "HTTP status")
    finally:
        sock.close()
    # Leave WLAN active to test shutdown of CYW43, lwIP and their background work.
    result = {
        "address": wlan.ifconfig()[0],
        "connect_elapsed_ms": connected_ms,
        "status": wlan.status(),
        "dns_host": dns_host,
        "dns_address": str(dns_address),
        "http_address": str(address),
        "http": 200,
    }
    try:
        result["rssi"] = wlan.status("rssi")
    except (OSError, ValueError, TypeError):
        pass
    return result


def expect_busy():
    try:
        machine.deepsleep(2000)
    except OSError as exc:
        check(exc.args[0] == EBUSY, "expected EBUSY, got " + repr(exc))
    else:
        raise AssertionError("deepsleep accepted an unsafe caller")


def thread_test():
    import _thread

    shared = [False, False, None]

    def worker():
        try:
            expect_busy()  # Must also reject deepsleep called from CPU1.
        except Exception as exc:
            shared[2] = repr(exc)
        shared[0] = True
        while not shared[1]:
            time.sleep_ms(1)

    _thread.start_new_thread(worker, ())
    try:
        deadline = time.ticks_add(time.ticks_ms(), 5000)
        while not shared[0]:
            check(time.ticks_diff(deadline, time.ticks_ms()) > 0, "CPU1 did not respond")
            time.sleep_ms(1)
        check(shared[2] is None, "CPU1 rejection: " + str(shared[2]))
        expect_busy()  # CPU0 while CPU1 is still active.
    finally:
        shared[1] = True
        # Let the thread return through runtime cleanup even if a check failed.
        time.sleep_ms(100)


def sleep_with_dma(config):
    import rp2

    # A long fixed-address RAM copy stays active until deepsleep aborts it.
    # No peripheral pins, flash addresses, ring alignment or DMA IRQs are used.
    source = bytearray(b"test")
    destination = bytearray(4)
    dma = rp2.DMA()
    try:
        ctrl = dma.pack_ctrl(size=2, inc_read=False, inc_write=False)
        dma.config(read=source, write=destination, count=0x0FFFFFFF, ctrl=ctrl, trigger=True)
        check(dma.active(), "DMA not active before deepsleep")
        machine.deepsleep(config["sleep_ms"])
    finally:
        # Keep buffers referenced until DMA is stopped if the sleep call fails.
        dma.close()


def run():
    global last_record
    with open("deepsleep-config.json") as f:
        config = json.load(f)
    regions = machine.mem_backup(-1)
    check(len(regions) == 3 and len(regions[2]) == 8, "requires RP2350 backup regions")
    state = regions[2]
    # State: magic, completed, RTC before sleep, phase, reserved, boots,
    # reserved, sentinel. Only POWMAN scratch is persistent in the deep state.
    if state[0] != MAGIC:
        for i in range(len(state)):
            state[i] = 0
        state[0] = MAGIC
        state[7] = 0x13579BDF
    state[5] += 1
    record = {
        "run": config["run"],
        "uid": binascii.hexlify(machine.unique_id()).decode(),
        "boot": state[5],
        "completed": state[1],
        "cause": machine.reset_cause(),
        "rtc": machine.RTC().datetime(),
        # Read-only evidence from pico-sdk RP2350 hardware/regs/{addressmap,powman}.h.
        # Startup may already have consumed/cleared CHIP_RESET status flags.
        "powman_chip_reset": machine.mem32[0x40100000 + 0x2C],
        "powman_last_swcore_pwrup": machine.mem32[0x40100000 + 0xA0],
        "status": "READY",
    }
    last_record = record
    check(state[7] == 0x13579BDF, "POWMAN scratch sentinel")
    check(state[4] == 0 and state[6] == 0, "POWMAN scratch unused test words changed")
    with open("deepsleep-sentinel.bin", "rb") as f:
        check(f.read() == SENTINEL, "filesystem sentinel changed")
    phase = state[3]
    record["phase"] = phase
    check(phase != 6, "deepsleep accepted an active CPU1")
    if phase in (1, 4, 5):
        expected = machine.WDT_RESET if phase == 4 else getattr(machine, "DEEPSLEEP_RESET", -1)
        if phase == 5 or (phase == 1 and not config.get("expect_deep_cause", True)):
            check(record["cause"] != expected, "stale DEEPSLEEP_RESET after machine.reset")
        else:
            check(record["cause"] == expected, "unexpected reset cause")
        record["watchdog_scratch_retained"] = [
            all(value == backup_pattern(r, i) for i, value in enumerate(regions[r]))
            for r in (0, 1)
        ]
        if phase == 1:
            elapsed = rtc_seconds() - state[2]
            target = config["sleep_ms"] / 1000
            tolerance = config.get("rtc_tolerance_s", 3)
            lower = max(1 if target >= 1 else 0, target - tolerance)
            record["rtc_before_epoch_s"] = state[2]
            record["rtc_elapsed_s"] = elapsed
            record["crossed_minute"] = state[2] // 60 != rtc_seconds() // 60
            record["crossed_day"] = state[2] // 86400 != rtc_seconds() // 86400
            check(lower <= elapsed <= target + tolerance + 10, "RTC duration")
            state[1] += 1
            record["completed"] = state[1]
        if phase in (4, 5):
            record["status"] = "PASS"
            state[3] = 2
            wait_for_host(record)
            return
    elif phase == 2:
        record["status"] = "STOPPED"
        emit(record)
        return
    if config.get("wifi"):
        record["wifi"] = wifi_test(config["wifi"])
    wait_for_host(record)
    if state[1] >= config.get("cycles", 100):
        state[3] = 5
        machine.reset()  # Verify lifetime of the deep-wake indication.
    if config.get("thread"):
        state[3] = 6
        thread_test()
    if config.get("watchdog"):
        state[3] = 4
        machine.WDT(timeout=2000)
        expect_busy()
        # A rejected call must leave the watchdog running. Expect WDT_RESET.
        while True:
            pass
    for r in (0, 1):
        for i in range(len(regions[r])):
            regions[r][i] = backup_pattern(r, i)
    os.sync()
    if config.get("lightsleep_before"):
        machine.lightsleep(20)
    if state[1] == 0:
        # Set just before sleeping, after USB/Wi-Fi preparation, to ensure the
        # default first sleep crosses midnight rather than host waiting doing so.
        machine.RTC().datetime((2026, 9, 25, 4, 23, 59, 58, 0))
    state[2] = rtc_seconds()
    state[3] = 1
    emit({"run": config["run"], "status": "SLEEP", "completed": state[1]})
    mode = config.get("mode", "deepsleep")
    if mode == "sleep_reset":
        time.sleep_ms(config["sleep_ms"])
        machine.reset()
    elif mode == "lightsleep_reset":
        machine.lightsleep(config["sleep_ms"])
        machine.reset()
    else:
        check(mode == "deepsleep", "unknown comparison mode")
        if config.get("dma"):
            sleep_with_dma(config)
        else:
            machine.deepsleep(config["sleep_ms"])
    raise AssertionError("deepsleep returned")


try:
    run()
except Exception as exc:
    # Stop on failure, leave raw/friendly REPL recoverable, never write a log to flash.
    last_record.update({"status": "FAIL", "error": repr(exc)})
    sys.print_exception(exc)
    # A failure during boot can precede USB enumeration. Repeat it until an
    # operator interrupts with Ctrl-C; KeyboardInterrupt remains uncaught.
    while True:
        emit(last_record)
        time.sleep_ms(1000)
