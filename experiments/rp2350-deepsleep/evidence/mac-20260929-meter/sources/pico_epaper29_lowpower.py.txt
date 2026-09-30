# SPDX-License-Identifier: MIT
"""Park the tested Pico 2 W + Waveshare Pico-ePaper-2.9 B/W V2 display bus.

Call only after refresh has completed and the panel's sleep sequence has
completed (the tested vendor sequence sends 0x10/0x01, waits two seconds,
then drives RST low). This function does not send that sleep command.

After this function, enter timed machine.deepsleep(). Do not call display
methods or read BUSY again before reinitializing all pins and SPI. Reusing
a display object's init() is insufficient if it does not restore pin modes.

This is specific to the pin mapping below and RP2350 register layout.
It neither alters USB/radio nor integrates the original application.
"""
import machine
import os


def park_after_sleep():
    """Leave RST low and release DC/CS/SCK/MOSI/BUSY, without input pulls."""
    if os.uname().machine != "Raspberry Pi Pico 2 W with RP2350":
        raise OSError("This display sleep helper requires Pico 2 W / RP2350")

    machine.Pin(12, machine.Pin.OUT, value=0)
    for gpio in (8, 9, 10, 11, 13):
        machine.Pin(gpio, machine.Pin.IN, pull=None)
    for gpio in range(8, 14):
        # RP2350 PADS_BANK0 atomic-clear alias: IE, PUE and PDE only.
        machine.mem32[0x4003B004 + 4 * gpio] = 0x4C

    # With input buffers disabled, Pin.value() cannot verify output levels.
    # Check the output latch/OE and pad controls instead.
    high_z_mask = sum(1 << gpio for gpio in (8, 9, 10, 11, 13))
    output_enable = machine.mem32[0xD0000030]
    output_latch = machine.mem32[0xD0000010]
    if (output_enable & high_z_mask
            or not output_enable & (1 << 12)
            or output_latch & (1 << 12)
            or any(machine.mem32[0x40038004 + 4 * gpio] & 0x4C
                   for gpio in range(8, 14))):
        raise OSError("Display sleep pin verification failed")
