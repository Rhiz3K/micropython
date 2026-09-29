# SPDX-License-Identifier: MIT
"""Opt-in hardware regression for the Pico 2 W helper's fresh-boot GP23 mux.

Use only an identified, backed-up Pico 2 W after a fresh hardware boot with
safe boot.py/main.py. Neither WLAN interface nor Bluetooth may have been
activated since that boot. Stop all network/Bluetooth callbacks, timers and
other workers first. The probe checks inactive interfaces and the expected
GP23 NULL mux, but cannot prove that boot history or worker precondition.

Run from the repository root, replacing PORT with the identified serial port:

    mpremote connect PORT resume \\
        run experiments/rp2350-deepsleep/pico2w_vsys_lowpower.py + \\
        run experiments/rp2350-deepsleep/pico2w_vsys_lowpower_regression.py

Both local files execute in RAM. The first defines the helper in the existing
REPL globals; the second invokes it once. `resume` prevents a configured
automatic soft reset. Entering raw REPL can interrupt the current program, so
inspect autostart and arrange a stopped application beforehand. Use one serial
client and an external process timeout; this probe cannot recover a hung USB
transport. Record the exact firmware/helper revisions and source hashes on the
host. No reset, flash write, network join or display operation is requested.

Alternatively, run this file alone if pico2w_vsys_lowpower is importable, or
import this probe and call run_probe(helper_callable). A test result is the
JSON object following `PICO2W_VSYS_REGRESSION `, not the host's exit status.
READY precedes the helper call; PASS/FAIL/NOT_READY is the final result.
Missing final output is incomplete. NOT_READY means this run does not exercise
the fresh-boot regression, e.g. GP23 already has SIO mux. Do not force registers
to simulate a fresh boot. An unchanged helper is expected to FAIL on GP23;
the fix should PASS with both GP23 and GP25 driven low and radios still inactive.

The probe intentionally avoids firmware-specific addresses such as cyw43_poll.
It leaves the radio and VSYS monitor disabled after PASS. Before subsequent
wireless use, normal driver initialization must reclaim its pins. It neither
measures current nor verifies AP receipt of disassociation or a Wi-Fi reconnect.
"""

import json
import os

import machine


def _probe_pins():
    # RP2350 SDK hardware/regs: IO_BANK0, PADS_BANK0, SIO GPIO_OUT/GPIO_OE.
    # Read only after checking the exact supported board description.
    out = machine.mem32[0xD0000010]
    oe = machine.mem32[0xD0000030]
    return {
        str(pin): {
            "ctrl": machine.mem32[0x40028004 + 8 * pin],
            "status": machine.mem32[0x40028000 + 8 * pin],
            "pad": machine.mem32[0x40038004 + 4 * pin],
            "sio_out": bool(out & (1 << pin)),
            "sio_oe": bool(oe & (1 << pin)),
        }
        for pin in (23, 25)
    }


def _probe_low(pin):
    # Check the pad-facing signal too: a low latch alone is insufficient.
    return (
        pin["ctrl"] & 0x1F == 5
        and pin["status"] & 0x2200 == 0x2000
        and pin["pad"] & 0x180 == 0
        and pin["sio_oe"]
        and not pin["sio_out"]
    )


def _probe_radios(sta, ap, ble):
    return {"sta_active": sta.active(), "ap_active": ap.active(), "ble_active": ble.active()}


def _probe_emit(record):
    print("PICO2W_VSYS_REGRESSION " + json.dumps(record))


def run_probe(helper=None):
    record = {
        "test": "pico2w-vsys-fresh-boot-mux",
        "status": "NOT_READY",
        "stage": "preconditions",
        "fresh_boot_and_stopped_workers_are_operator_preconditions": True,
        "helper_called": False,
    }
    try:
        uname = os.uname()
        record["model"] = uname.machine
        record["version"] = uname.version
        if uname.machine != "Raspberry Pi Pico 2 W with RP2350":
            raise ValueError("requires Pico 2 W / RP2350")

        import bluetooth
        import network

        # Construct/query only. Inactive BLE() does not activate the controller.
        sta = network.WLAN(network.STA_IF)
        ap = network.WLAN(network.AP_IF)
        ble = bluetooth.BLE()
        record["before_radio"] = _probe_radios(sta, ap, ble)
        record["before_pins"] = _probe_pins()
        record["reset_cause"] = machine.reset_cause()
        if any(record["before_radio"].values()):
            raise ValueError("radio already active; no helper call made")
        gp23 = record["before_pins"]["23"]
        if gp23["ctrl"] & 0x1F != 31 or not gp23["sio_oe"] or gp23["sio_out"]:
            raise ValueError("expected fresh-boot GP23 NULL mux, OE set, latch low")

        if helper is None:
            import pico2w_vsys_lowpower

            helper = pico2w_vsys_lowpower.radio_off_and_disable_vsys_monitor
            record["helper_source"] = "imported_module"
        else:
            record["helper_source"] = "provided_callable"
        if not callable(helper):
            raise TypeError("helper must be callable")

        record["status"] = "READY"
        _probe_emit(record)
        record["stage"] = "helper"
        record["helper_called"] = True
        try:
            helper()
        finally:
            # Retain the actual failure-state evidence when the old helper raises.
            record["after_pins"] = _probe_pins()
            record["after_radio"] = _probe_radios(sta, ap, ble)
        record["stage"] = "postconditions"
        if any(record["after_radio"].values()):
            raise AssertionError("radio active after helper")
        if not all(_probe_low(pin) for pin in record["after_pins"].values()):
            raise AssertionError("GP23 and GP25 must drive SIO low with pads enabled")
        record["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001 - report unexpected hardware errors as failed evidence.
        record["status"] = "FAIL" if record["helper_called"] else "NOT_READY"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
    _probe_emit(record)
    return record


if __name__ == "__main__":
    run_probe(globals().get("radio_off_and_disable_vsys_monitor"))
