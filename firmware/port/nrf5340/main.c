/*
 * main.c - nRF5340 application-core entry. COMPILE-TESTED ONLY.
 * Order: safe GPIO levels -> time base -> application -> sensors ->
 * PWM/SAADC/DPPI scheduler -> watchdog -> sleep; all control runs in the
 * SAADC (40 kHz) and EGU0 (2 kHz) interrupts.
 */
#include "board.h"
#include "hal.h"

int main(void)
{
    board_gpio_init();
    board_timebase_init();
    const bool wdt = hal_reset_was_watchdog();
    pen_app_init(&g_app, PEN_PROFILE_BALANCED, wdt);
    pen_app_set_sink(&g_app, board_log_sink, NULL, true);
    sensors_init();
    sched_init();
    board_wdt_init();
    static uint8_t chunk[256];
    for (;;) {
        __asm volatile("wfi");
        /* background: research-log drain to USB CDC (112 kB/s at 2 kHz); BLE,
         * flash capture and the user interface are not implemented */
        const uint32_t n = board_log_read(chunk, sizeof(chunk));
        if (n > 0u) {
            board_usb_cdc_write(chunk, n);
        }
    }
}
