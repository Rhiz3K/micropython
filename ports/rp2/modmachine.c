/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2020-2023 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

// This file is never compiled standalone, it's included directly from
// extmod/modmachine.c via MICROPY_PY_MACHINE_INCLUDEFILE.

#include "py/mphal.h"
#include "py/mperrno.h"
#include "mp_usbd.h"
#include "modmachine.h"
#include "uart.h"
#include "rp2_flash.h"
#if MICROPY_HW_ENABLE_PSRAM
#include "hardware/psram.h"
#endif
#include "clocks_extra.h"
#include "hardware/pll.h"
#include "hardware/structs/rosc.h"
#if PICO_RP2040
#include "hardware/structs/psm.h"
#endif
#include "hardware/structs/scb.h"
#include "hardware/structs/syscfg.h"
#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "hardware/xosc.h"
#include "pico/bootrom.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"
#include "pico/runtime_init.h"
#if MICROPY_PY_NETWORK_CYW43
#include "lib/cyw43-driver/src/cyw43.h"
#endif
#if MICROPY_HW_ENABLE_POWMAN_DEEPSLEEP
#include "hardware/dma.h"
#include "hardware/powman.h"
#include "hardware/structs/nvic.h"
#include "hardware/structs/systick.h"
#include "pico/multicore.h"
#endif

#define RP2_RESET_PWRON (1)
#define RP2_RESET_WDT (3)
#define RP2_RESET_DEEPSLEEP (4)

#if MICROPY_HW_ENABLE_POWMAN_DEEPSLEEP
// SDK 2.3.0 lists source positions; the observed alarm record is 0x40, not 6.
#define RP2_POWMAN_ALARM_PWRUP_MASK (1u << 6)
#define RP2_DEEPSLEEP_GLOBALS \
    { MP_ROM_QSTR(MP_QSTR_DEEPSLEEP_RESET), MP_ROM_INT(RP2_RESET_DEEPSLEEP) },
static bool woke_from_deepsleep;
static void machine_deepsleep_prepare_wfi(void);

void machine_deepsleep_init(void) {
    if (watchdog_hw->reason) {
        machine_deepsleep_prepare_wfi();
    }
    // These are read-only hardware reset records, not software scratch markers.
    woke_from_deepsleep = !watchdog_hw->reason
        && (powman_hw->chip_reset & POWMAN_CHIP_RESET_HAD_SWCORE_PD_BITS)
        && (powman_hw->last_swcore_pwrup & RP2_POWMAN_ALARM_PWRUP_MASK);
    powman_disable_alarm_wakeup();
    powman_clear_alarm();
    // POWMAN survives SWCORE power-down. Restore normal awake debug behaviour.
    powman_set_debug_power_request_ignored(false);
    if (powman_timer_is_running()) {
        // Preserve the RTC value, restoring crystal accuracy while awake.
        powman_timer_set_1khz_tick_source_xosc();
    }
}
#else
#define RP2_DEEPSLEEP_GLOBALS
#endif

#define MICROPY_PY_MACHINE_EXTRA_GLOBALS \
    RP2_DEEPSLEEP_GLOBALS \
    { MP_ROM_QSTR(MP_QSTR_Pin),                 MP_ROM_PTR(&machine_pin_type) }, \
    { MP_ROM_QSTR(MP_QSTR_RTC),                 MP_ROM_PTR(&machine_rtc_type) }, \
    { MP_ROM_QSTR(MP_QSTR_Timer),               MP_ROM_PTR(&machine_timer_type) }, \
    \
    { MP_ROM_QSTR(MP_QSTR_PWRON_RESET),         MP_ROM_INT(RP2_RESET_PWRON) }, \
    { MP_ROM_QSTR(MP_QSTR_WDT_RESET),           MP_ROM_INT(RP2_RESET_WDT) }, \

static mp_obj_t mp_machine_unique_id(void) {
    pico_unique_board_id_t id;
    pico_get_unique_board_id(&id);
    return mp_obj_new_bytes(id.id, sizeof(id.id));
}

MP_NORETURN static void mp_machine_reset(void) {
    watchdog_reboot(0, SRAM_END, 0);
    for (;;) {
        __wfi();
    }
}

static mp_int_t mp_machine_reset_cause(void) {
    int reset_cause;
    if (watchdog_caused_reboot()) {
        reset_cause = RP2_RESET_WDT;
    #if MICROPY_HW_ENABLE_POWMAN_DEEPSLEEP
    } else if (woke_from_deepsleep) {
        reset_cause = RP2_RESET_DEEPSLEEP;
    #endif
    } else {
        reset_cause = RP2_RESET_PWRON;
    }
    return reset_cause;
}

MP_NORETURN void mp_machine_bootloader(size_t n_args, const mp_obj_t *args) {
    MICROPY_BOARD_ENTER_BOOTLOADER(n_args, args);
    rosc_hw->ctrl = ROSC_CTRL_ENABLE_VALUE_ENABLE << ROSC_CTRL_ENABLE_LSB;
    reset_usb_boot(0, 0);
    for (;;) {
    }
}

static mp_obj_t mp_machine_get_freq(void) {
    return MP_OBJ_NEW_SMALL_INT(mp_hal_get_cpu_freq());
}

static mp_obj_t frequency_overrides[2] = {};

static void mp_machine_set_freq(size_t n_args, const mp_obj_t *args) {
    mp_int_t freq = mp_obj_get_int(args[0]);

    // If necessary, increase the flash divider before increasing the clock speed
    const int old_freq = clock_get_hz(clk_sys);
    rp2_flash_set_timing_for_freq(MAX(freq, old_freq));

    if (!set_sys_clock_khz(freq / 1000, false)) {
        mp_raise_ValueError(MP_ERROR_TEXT("cannot change frequency"));
    }
    if (n_args > 1) {
        mp_int_t freq_peri = mp_obj_get_int(args[1]);
        if (freq_peri != (USB_CLK_KHZ * KHZ)) {
            if (freq_peri == freq) {
                clock_configure(clk_peri,
                    0,
                    CLOCKS_CLK_PERI_CTRL_AUXSRC_VALUE_CLKSRC_PLL_SYS,
                    freq,
                    freq);
            } else {
                mp_raise_ValueError(MP_ERROR_TEXT("peripheral freq must be 48_000_000 or the same as the MCU freq"));
            }
        }
    }

    // If clock speed was reduced, maybe we can reduce the flash divider
    if (freq < old_freq) {
        rp2_flash_set_timing_for_freq(freq);
    }

    #if MICROPY_HW_ENABLE_UART_REPL
    setup_default_uart();
    mp_uart_init();
    #endif
    #if MICROPY_HW_ENABLE_PSRAM
    // Re-tune the PSRAM QMI timing for the new system clock.
    if (psram_is_available()) {
        psram_configure_params(PICO_DEFAULT_PSRAM_MAX_FREQ, PICO_DEFAULT_PSRAM_MAX_SELECT, PICO_DEFAULT_PSRAM_MIN_DESELECT);
        psram_reinitialize();
    }
    #endif

    if (n_args > 0) {
        memcpy(frequency_overrides, args, MIN(n_args, 2) * sizeof(mp_obj_t));
    }
}

static void mp_machine_idle(void) {
    MICROPY_INTERNAL_WFE(1);
}

static void alarm_sleep_callback(uint alarm_id) {
}

// Set this to 1 to enable some debug of the interrupt that woke the device
#define DEBUG_LIGHTSLEEP 0

static void mp_machine_lightsleep(size_t n_args, const mp_obj_t *args) {
    mp_int_t delay_ms = 0;
    bool use_timer_alarm = false;

    if (n_args == 1) {
        delay_ms = mp_obj_get_int(args[0]);
        if (delay_ms <= 1) {
            // Sleep is too small, just use standard delay.
            mp_hal_delay_ms(delay_ms);
            return;
        }
        use_timer_alarm = delay_ms < (1ULL << 32) / 1000;
        if (use_timer_alarm) {
            // Use timer alarm to wake.
        } else {
            // TODO: Use RTC alarm to wake.
            mp_raise_ValueError(MP_ERROR_TEXT("sleep too long"));
        }
    }

    uint32_t my_interrupts = MICROPY_BEGIN_ATOMIC_SECTION();
    #if MICROPY_PY_NETWORK_CYW43
    if (cyw43_poll_is_pending()) {
        MICROPY_END_ATOMIC_SECTION(my_interrupts);
        return;
    }
    #endif

    #if MICROPY_PY_THREAD
    static bool in_lightsleep;
    if (in_lightsleep) {
        // The other CPU is also in machine.lightsleep()
        MICROPY_END_ATOMIC_SECTION(my_interrupts);
        return;
    }
    in_lightsleep = true;
    #endif

    #if MICROPY_HW_ENABLE_USBDEV
    // Only disable the USB clock if a USB host has not configured the device
    // or if going to DORMANT mode.
    bool disable_usb = !(tud_mounted() && n_args > 0);
    #else
    bool disable_usb = true;
    #endif
    if (disable_usb) {
        clock_stop(clk_usb);
    }

    bool watchdog_active = (watchdog_hw->ctrl & WATCHDOG_CTRL_ENABLE_BITS) != 0;

    clock_stop(clk_adc);
    #if PICO_RP2350
    clock_stop(clk_hstx);
    #endif

    // CLK_REF = XOSC
    clock_configure(clk_ref, CLOCKS_CLK_REF_CTRL_SRC_VALUE_XOSC_CLKSRC, 0, XOSC_HZ, XOSC_HZ);

    // CLK_SYS = CLK_REF
    clock_configure(clk_sys, CLOCKS_CLK_SYS_CTRL_SRC_VALUE_CLK_REF, 0, XOSC_HZ, XOSC_HZ);

    // CLK_RTC = XOSC / 256
    #if PICO_RP2040
    clock_configure(clk_rtc, 0, CLOCKS_CLK_RTC_CTRL_AUXSRC_VALUE_XOSC_CLKSRC, XOSC_HZ, XOSC_HZ / 256);
    #endif

    // CLK_PERI = CLK_SYS
    clock_configure(clk_peri, 0, CLOCKS_CLK_PERI_CTRL_AUXSRC_VALUE_CLK_SYS, XOSC_HZ, XOSC_HZ);

    // Disable PLLs.
    pll_deinit(pll_sys);
    if (disable_usb) {
        pll_deinit(pll_usb);
    }

    // Disable ROSC.
    #if PICO_RP2040
    if (watchdog_active) {
        // Configure Power-On State Machine to reset the ROSC on a watchdog timeout.
        psm_hw->wdsel |= PSM_WDSEL_ROSC_BITS;
    }
    #endif
    rosc_hw->ctrl = ROSC_CTRL_ENABLE_VALUE_DISABLE << ROSC_CTRL_ENABLE_LSB;

    #if DEBUG_LIGHTSLEEP
    #if PICO_RP2040
    uint32_t pending_intr = 0;
    #else
    uint32_t pending_intr[2] = { 0 };
    #endif
    #endif

    bool alarm_armed = false;
    if (n_args == 0) {
        #if MICROPY_PY_NETWORK_CYW43
        gpio_set_dormant_irq_enabled(CYW43_PIN_WL_HOST_WAKE, GPIO_IRQ_LEVEL_HIGH, true);
        #endif
        xosc_dormant();
    } else {
        uint32_t save_sleep_en0 = clocks_hw->sleep_en0;
        uint32_t save_sleep_en1 = clocks_hw->sleep_en1;
        if (use_timer_alarm) {
            // Use timer alarm to wake.
            #if PICO_RP2040
            clocks_hw->sleep_en0 = CLOCKS_SLEEP_EN0_CLK_RTC_RTC_BITS;
            clocks_hw->sleep_en1 = CLOCKS_SLEEP_EN1_CLK_SYS_TIMER_BITS;
            #elif PICO_RP2350
            clocks_hw->sleep_en0 = CLOCKS_SLEEP_EN0_CLK_REF_POWMAN_BITS | CLOCKS_SLEEP_EN0_CLK_SYS_POWMAN_BITS;
            uint32_t sleep_en1 = CLOCKS_SLEEP_EN1_CLK_REF_TICKS_BITS | CLOCKS_SLEEP_EN1_CLK_SYS_TIMER0_BITS;
            if (watchdog_active) {
                // clk_sys watchdog and clk_ref ticks must be enabled for the watchdog counter to decrement on RP2350.
                sleep_en1 |= CLOCKS_SLEEP_EN1_CLK_SYS_WATCHDOG_BITS;
            }
            clocks_hw->sleep_en1 = sleep_en1;
            #else
            #error Unknown processor
            #endif
            hardware_alarm_claim(MICROPY_HW_LIGHTSLEEP_ALARM_NUM);
            hardware_alarm_set_callback(MICROPY_HW_LIGHTSLEEP_ALARM_NUM, alarm_sleep_callback);
            if (hardware_alarm_set_target(MICROPY_HW_LIGHTSLEEP_ALARM_NUM, make_timeout_time_ms(delay_ms)) == PICO_OK) {
                alarm_armed = true;
            }
        } else {
            // TODO: Use RTC alarm to wake.
            clocks_hw->sleep_en0 = 0x0;
            clocks_hw->sleep_en1 = 0x0;
        }

        if (!disable_usb) {
            clocks_hw->sleep_en0 |= CLOCKS_SLEEP_EN0_CLK_SYS_PLL_USB_BITS;
            #if PICO_RP2040
            clocks_hw->sleep_en1 |= CLOCKS_SLEEP_EN1_CLK_USB_USBCTRL_BITS;
            #elif PICO_RP2350
            clocks_hw->sleep_en1 |= CLOCKS_SLEEP_EN1_CLK_USB_BITS;
            #else
            #error Unknown processor
            #endif
        }

        #if PICO_ARM
        // Configure SLEEPDEEP bits on Cortex-M CPUs.
        #if PICO_RP2040
        scb_hw->scr |= M0PLUS_SCR_SLEEPDEEP_BITS;
        #elif PICO_RP2350
        scb_hw->scr |= M33_SCR_SLEEPDEEP_BITS;
        #else
        #error Unknown processor
        #endif
        #endif

        // Go into low-power mode.
        if (alarm_armed) {
            __wfi();

            #if DEBUG_LIGHTSLEEP
            #if PICO_RP2040
            pending_intr = nvic_hw->ispr;
            #else
            pending_intr[0] = nvic_hw->ispr[0];
            pending_intr[1] = nvic_hw->ispr[1];
            #endif
            #endif
        }
        clocks_hw->sleep_en0 = save_sleep_en0;
        clocks_hw->sleep_en1 = save_sleep_en1;
    }

    // Enable ROSC.
    rosc_hw->ctrl = ROSC_CTRL_ENABLE_VALUE_ENABLE << ROSC_CTRL_ENABLE_LSB;
    #if PICO_RP2040
    if (watchdog_active) {
        // No longer need the Power-On State Machine to reset the ROSC on a watchdog timeout.
        psm_hw->wdsel &= ~PSM_WDSEL_ROSC_BITS;
    }
    #endif

    // Bring back all clocks.
    runtime_init_clocks_optional_usb(disable_usb);
    MICROPY_END_ATOMIC_SECTION(my_interrupts);

    // Re-sync mp_hal_time_ns() counter with aon timer.
    mp_hal_time_ns_set_from_rtc();

    // Note: This must be done after MICROPY_END_ATOMIC_SECTION
    if (use_timer_alarm) {
        if (alarm_armed) {
            hardware_alarm_cancel(MICROPY_HW_LIGHTSLEEP_ALARM_NUM);
        }
        hardware_alarm_set_callback(MICROPY_HW_LIGHTSLEEP_ALARM_NUM, NULL);
        hardware_alarm_unclaim(MICROPY_HW_LIGHTSLEEP_ALARM_NUM);

        #if DEBUG_LIGHTSLEEP
        // Check irq.h for the list of IRQ's
        // for rp2040 00000042: TIMER_IRQ_1 woke the device as expected
        //            00000020: USBCTRL_IRQ woke the device (probably early)
        // For rp2350 00000000:00000002: TIMER0_IRQ_1 woke the device as expected
        //            00000000:00004000: USBCTRL_IRQ woke the device (probably early)
        #if PICO_RP2040
        mp_printf(MP_PYTHON_PRINTER, "lightsleep: pending_intr=%08lx\n", pending_intr);
        #else
        mp_printf(MP_PYTHON_PRINTER, "lightsleep: pending_intr=%08lx:%08lx\n", pending_intr[1], pending_intr[0]);
        #endif
        #endif
    }

    #if MICROPY_PY_THREAD
    // Clearing the flag here is atomic, and we know we're the ones who set it
    // (higher up, inside the critical section)
    in_lightsleep = false;
    #endif

    if (frequency_overrides[0] != MP_OBJ_NULL) {
        mp_machine_set_freq(1 + (frequency_overrides[1] != NULL ? 1 : 0), frequency_overrides);
    }
}

#if MICROPY_HW_ENABLE_POWMAN_DEEPSLEEP
/*
 * Adapted from Raspberry Pi pico-sdk, commit
 * 98a542c1a62fb549ffb5d66a3e5892b06276b670,
 * src/rp2_common/pico_low_power/low_power.c:
 * runtime_init_rp2350_sleep_fix().
 *
 * Copyright (c) 2026 Raspberry Pi (Trading) Ltd.
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */
static void __no_inline_not_in_flash_func(machine_deepsleep_prepare_wfi)(void) {
    // As in the SDK's runtime_init_rp2350_sleep_fix, clear the post-ROM-reboot
    // sleep state with an immediately pending IRQ. The STR and WFI must share
    // one aligned instruction fetch in SRAM. PRIMASK prevents handler dispatch.
    uint32_t irq_state = save_and_disable_interrupts();
    uint32_t enabled[MP_ARRAY_SIZE(nvic_hw->icer)];
    for (uint i = 0; i < MP_ARRAY_SIZE(enabled); ++i) {
        enabled[i] = nvic_hw->iser[i];
        nvic_hw->icer[i] = UINT32_MAX;
    }
    uint32_t mask = 1u << (FIRST_USER_IRQ % 32);
    io_rw_32 *pending = &nvic_hw->ispr[FIRST_USER_IRQ / 32];
    nvic_hw->icpr[FIRST_USER_IRQ / 32] = mask;
    nvic_hw->iser[FIRST_USER_IRQ / 32] = mask;
    scb_hw->scr &= ~M33_SCR_SLEEPDEEP_BITS;
    __asm volatile (
        ".balign 4\n"
        "str %0, [%1]\n"
        "wfi\n"
        : : "l" (mask), "l" (pending) : "memory"
        );
    nvic_hw->icer[FIRST_USER_IRQ / 32] = mask;
    nvic_hw->icpr[FIRST_USER_IRQ / 32] = mask;
    for (uint i = 0; i < MP_ARRAY_SIZE(enabled); ++i) {
        nvic_hw->iser[i] = enabled[i];
    }
    restore_interrupts(irq_state);
}

MP_NORETURN static void machine_deepsleep_abort(void) {
    uint32_t state = powman_hw->state;
    if ((state & (POWMAN_STATE_CHANGING_BITS | POWMAN_STATE_REQ_BITS))
        == (POWMAN_STATE_CHANGING_BITS | POWMAN_STATE_REQ_BITS)) {
        // A transition can commit between the caller's check and this one.
        // Its wake alarm must remain armed.
        __dsb();
        for (;;) {
            __wfi();
        }
    }
    // Teardown cannot be undone. Cancel the request and take an ordinary reset;
    // reset_cause() must not claim that the switched core was powered down.
    // Keep the alarm armed until cancellation has completed: a transition that
    // is already underway must retain its wake source.
    powman_hw->state = POWMAN_PASSWORD_BITS; // Request P0.0 (all domains on).
    uint64_t deadline = time_us_64() + 100000;
    while (powman_hw->state & (POWMAN_STATE_WAITING_BITS | POWMAN_STATE_CHANGING_BITS | POWMAN_STATE_CURRENT_BITS)) {
        if (time_us_64() >= deadline) {
            // Never execute WFI with an unconfirmed cancellation.
            watchdog_reboot(0, SRAM_END, 0);
            for (;;) {
                tight_loop_contents();
            }
        }
    }
    powman_disable_alarm_wakeup();
    powman_clear_alarm();
    scb_hw->scr &= ~M33_SCR_SLEEPDEEP_BITS;
    mp_machine_reset();
}

MP_NORETURN static void machine_deepsleep_timed(mp_int_t delay_ms) {
    if (delay_ms < 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("negative sleep duration"));
    }
    // Do not kill another Python thread while it owns a lock or writes flash.
    if (get_core_num() != 0 || __get_current_exception()
        #if MICROPY_PY_THREAD
        || core1_entry != NULL
        #endif
        || (watchdog_hw->ctrl & WATCHDOG_CTRL_ENABLE_BITS)) {
        mp_raise_OSError(MP_EBUSY);
    }
    if (delay_ms <= 1) {
        mp_hal_delay_ms(delay_ms);
        mp_machine_reset();
    }
    uint64_t now = powman_timer_get_ms();
    if (!powman_timer_is_running() || now > UINT64_MAX - (uint32_t)delay_ms) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid sleep deadline"));
    }
    uint64_t deadline = now + (uint32_t)delay_ms;
    powman_power_state awake = powman_get_power_state();
    if (!powman_configure_wakeup_state(POWMAN_POWER_STATE_NONE, awake)) {
        mp_raise_OSError(MP_EINVAL);
    }

    // Flash operations on core0 are synchronous. Applications must flush/close
    // files before calling, as for machine.reset(); os.sync() cannot flush LFS
    // file objects. From here there is no return to the Python runtime.
    uint32_t irq_state = save_and_disable_interrupts();
    // A callback could have started a thread/watchdog since the initial check.
    if (
        #if MICROPY_PY_THREAD
        core1_entry != NULL ||
        #endif
        (watchdog_hw->ctrl & WATCHDOG_CTRL_ENABLE_BITS)) {
        restore_interrupts(irq_state);
        mp_raise_OSError(MP_EBUSY);
    }
    multicore_reset_core1();
    #if MICROPY_PY_NETWORK_CYW43
    cyw43_deinit(&cyw43_state);
    // Also cover an interface which has never been activated.
    gpio_init(CYW43_PIN_WL_REG_ON);
    gpio_disable_pulls(CYW43_PIN_WL_REG_ON);
    gpio_put(CYW43_PIN_WL_REG_ON, false);
    gpio_set_dir(CYW43_PIN_WL_REG_ON, GPIO_OUT);
    #if MICROPY_HW_CYW43_DEEPSLEEP_CS_LOW
    // Some boards also use wireless CS to enable the VSYS monitor path.
    // Drive it low only after the radio is fully powered off.
    gpio_init(CYW43_PIN_WL_CS);
    gpio_disable_pulls(CYW43_PIN_WL_CS);
    gpio_put(CYW43_PIN_WL_CS, false);
    gpio_set_dir(CYW43_PIN_WL_CS, GPIO_OUT);
    #endif
    #endif
    #if MICROPY_HW_ENABLE_USBDEV
    tud_disconnect();
    #endif

    // RP2350-E5: prevent every channel from restarting another before aborting
    // them together. Leave the peripheral clocks running until writes drain.
    for (uint i = 0; i < NUM_DMA_CHANNELS; ++i) {
        uint32_t ctrl = dma_hw->ch[i].ctrl_trig;
        ctrl &= ~(DMA_CH0_CTRL_TRIG_EN_BITS | DMA_CH0_CTRL_TRIG_CHAIN_TO_BITS);
        dma_hw->ch[i].al1_ctrl = ctrl | (i << DMA_CH0_CTRL_TRIG_CHAIN_TO_LSB);
    }
    dma_hw->abort = (1u << NUM_DMA_CHANNELS) - 1;
    uint64_t abort_deadline = time_us_64() + 100000;
    while (dma_hw->abort) {
        if (time_us_64() >= abort_deadline) {
            machine_deepsleep_abort();
        }
    }

    for (uint i = 0; i < MP_ARRAY_SIZE(nvic_hw->icer); ++i) {
        nvic_hw->icer[i] = UINT32_MAX;
        nvic_hw->icpr[i] = UINT32_MAX;
    }
    systick_hw->csr = 0;
    scb_hw->icsr = M33_ICSR_PENDSVCLR_BITS | M33_ICSR_PENDSTCLR_BITS;
    // A preceding lightsleep() may have left SLEEPDEEP set.
    scb_hw->scr &= ~M33_SCR_SLEEPDEEP_BITS;
    powman_disable_all_wakeups();
    powman_clear_alarm();
    powman_set_debug_power_request_ignored(true);
    powman_timer_set_1khz_tick_source_lposc();
    powman_set_bits(&powman_hw->vreg_ctrl, POWMAN_VREG_CTRL_UNLOCK_BITS);
    // Normal ROM flash boot, without reserving any machine.mem_backup words.
    for (uint i = 0; i < 4; ++i) {
        powman_hw->boot[i] = 0;
    }
    powman_enable_alarm_wakeup_at_ms(deadline);
    // If the deadline races entry, this pending IRQ makes WFI return even with
    // PRIMASK set. Its handler is never executed; the failure path resets.
    irq_set_enabled(POWMAN_IRQ_TIMER, true);
    int state_result = powman_set_power_state(POWMAN_POWER_STATE_NONE);
    // The SDK polls for WAITING, but the sequencer may already be CHANGING.
    // Do not cancel or disarm the alarm once the all-off transition has begun.
    uint32_t state = powman_hw->state;
    if ((state & (POWMAN_STATE_CHANGING_BITS | POWMAN_STATE_REQ_BITS))
        == (POWMAN_STATE_CHANGING_BITS | POWMAN_STATE_REQ_BITS)) {
        __dsb();
        for (;;) {
            __wfi();
        }
    }
    if (powman_timer_get_ms() >= deadline || state_result != PICO_OK) {
        machine_deepsleep_abort();
    }
    // POWMAN defers P1.7 until both processors sleep. No manual clock/XIP
    // shutdown is needed: instructions and stack remain accessible until WFI,
    // after which SWCORE, XIP cache and both SRAM domains lose power.
    while (powman_timer_get_ms() < deadline) {
        __dsb();
        __wfi();
    }
    machine_deepsleep_abort();
}
#endif

MP_NORETURN static void mp_machine_deepsleep(size_t n_args, const mp_obj_t *args) {
    #if MICROPY_HW_ENABLE_POWMAN_DEEPSLEEP
    if (n_args == 1) {
        machine_deepsleep_timed(mp_obj_get_int(args[0]));
    }
    #endif
    mp_machine_lightsleep(n_args, args);
    mp_machine_reset();
}
