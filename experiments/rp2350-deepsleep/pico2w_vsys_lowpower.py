# SPDX-License-Identifier: MIT
"""Pico 2 W: stop CYW43 and disable the VSYS monitor path.

Call only after all network/Bluetooth tasks, callbacks and other workers have
stopped. This function deinitializes both WLAN interfaces and verifies that
GP23/WL_REG_ON is driven low before driving GP25/wireless CS low. The latter
disables Pico 2 W's VSYS-to-ADC3 monitor path. It does not switch off VSYS or
the Pico's main supply, and does not change USB or display registers/pins.

Use this as a final preparation for timed machine.deepsleep(). Do not access
the wireless bus afterwards. Following the reset, normal driver setup must
reclaim its pins before wireless use. GPIO29/ADC3 cannot measure VSYS while
GP25 remains low: reading VSYS requires CS high, a correctly configured ADC,
and no simultaneous wireless SPI transaction. This helper does not restore
that state or validate Wi-Fi reconnect after wake.

Board reference: Raspberry Pi Pico 2 W schematic, revision 2, page 1:
https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf
"""
import machine
import network
import os


def _require_sio_low_output(gpio):
    """Check mux, post-override drive, pad isolation/OD and SIO latch/OE."""
    control = machine.mem32[0x40028004 + 8 * gpio]
    status = machine.mem32[0x40028000 + 8 * gpio]
    pad = machine.mem32[0x40038004 + 4 * gpio]
    mask = 1 << gpio
    if ((control & 0x1f) != 5
            or (status & 0x2200) != 0x2000
            or pad & 0x180
            or not machine.mem32[0xd0000030] & mask
            or machine.mem32[0xd0000010] & mask):
        raise OSError("Expected SIO output low on GPIO %d" % gpio)


def radio_off_and_disable_vsys_monitor():
    """Verify the radio is off, then hold its CS/VSYS-monitor enable low."""
    if os.uname().machine != "Raspberry Pi Pico 2 W with RP2350":
        raise OSError("This VSYS sleep helper requires Pico 2 W / RP2350")

    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    sta.active(False)
    ap.active(False)
    sta.deinit()
    if sta.active() or ap.active():
        raise OSError("Wireless interfaces are still active")
    _require_sio_low_output(23)

    machine.Pin(25, machine.Pin.OUT, pull=None, value=0)
    _require_sio_low_output(25)
    _require_sio_low_output(23)
