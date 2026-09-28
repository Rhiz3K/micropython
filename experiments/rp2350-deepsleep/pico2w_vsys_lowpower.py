# SPDX-License-Identifier: MIT
"""Pico 2 W: stop CYW43 and disable the VSYS monitor path.

Call only after all network/Bluetooth tasks, callbacks and other workers have
stopped, and explicitly deactivate Bluetooth before calling if it was used.
An active station is disconnected before its radio is powered off. The helper
waits up to 500 ms for the driver's link-down state; the disconnect call itself
also has a driver timeout. If a previously connected station does not report
link-down, the radio and monitor path are still turned off, then OSError is
raised. This verifies the local state, not receipt of a frame by the access point.

This function deinitializes both WLAN interfaces and verifies that
GP23/WL_REG_ON is driven low before driving GP25/wireless CS low. The latter
disables Pico 2 W's VSYS-to-ADC3 monitor path. It does not switch off VSYS or
the Pico's main supply, and does not change USB or display registers/pins.

Use this as a final preparation for timed machine.deepsleep(). Do not access
the wireless bus afterwards. Following the reset, normal driver setup must
reclaim its pins before wireless use. GPIO29/ADC3 cannot measure VSYS while
GP25 remains low: reading VSYS requires CS high, a correctly configured ADC,
and no simultaneous wireless SPI transaction. This helper does not restore
that state, retry a connection or guarantee reconnect to every access point.

Board reference: Raspberry Pi Pico 2 W schematic, revision 2, page 1:
https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf
"""

import machine
import network
import os
import time


def _require_sio_low_output(gpio):
    """Check mux, post-override drive, pad isolation/OD and SIO latch/OE."""
    control = machine.mem32[0x40028004 + 8 * gpio]
    status = machine.mem32[0x40028000 + 8 * gpio]
    pad = machine.mem32[0x40038004 + 4 * gpio]
    mask = 1 << gpio
    if (
        (control & 0x1F) != 5
        or (status & 0x2200) != 0x2000
        or pad & 0x180
        or not machine.mem32[0xD0000030] & mask
        or machine.mem32[0xD0000010] & mask
    ):
        raise OSError("Expected SIO output low on GPIO %d" % gpio)


def radio_off_and_disable_vsys_monitor():
    """Disconnect STA, power the radio off, then disable the VSYS monitor."""
    if os.uname().machine != "Raspberry Pi Pico 2 W with RP2350":
        raise OSError("This VSYS sleep helper requires Pico 2 W / RP2350")

    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    was_connected = sta.isconnected()
    link_down = not was_connected
    if sta.active():
        sta.disconnect()
        started = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), started) < 500:
            if sta.status() == 0 and not sta.isconnected():
                break
            time.sleep_ms(20)
        link_down = sta.status() == 0 and not sta.isconnected()
        sta.active(False)
    if ap.active():
        ap.active(False)
    # Calling active(False) on an already inactive interface can initialize
    # CYW43 just to send its shutdown command. Deinit itself is safe when idle.
    sta.deinit()
    if sta.active() or ap.active():
        raise OSError("Wireless interfaces are still active")
    _require_sio_low_output(23)

    machine.Pin(25, machine.Pin.OUT, pull=None, value=0)
    _require_sio_low_output(25)
    _require_sio_low_output(23)
    if was_connected and not link_down:
        raise OSError("Wi-Fi link-down was not confirmed before radio power-off")
