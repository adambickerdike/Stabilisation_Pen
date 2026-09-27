/*
 * hal.h - abstract hardware interface of the Rev A research pen.
 *
 * The control core (core/) never touches registers; the application layer
 * (core/app.c) and the safety sequencer use only these functions.
 * Implementations: port/host/hal_host.c (unit tests, with a behavioural model
 * of the over-current latch) and port/nrf5340/hal_nrf5340.c (register level,
 * compile-tested only, VERIFY).
 * Pin names follow electronics/gen/design_revA.py sheet_mcu().
 */
#ifndef PEN_HAL_H
#define PEN_HAL_H

#include <stdbool.h>
#include <stdint.h>

#include "current_loop.h"

/* ---- actuator power path ---- */
void hal_act_en_req(bool on);       /* ACT_EN_REQ (P0.24): VMOT = REQ & FAULT_N & NOCHG */
void hal_drv_sleep_n(bool awake);   /* DRV_SLEEP_N (P0.23), both DRV8212P */
bool hal_fault_n(void);             /* FAULT_N (P1.07): false = over-current latch set */
void hal_fault_clr_pulse(void);     /* FAULT_CLR_N (P1.12): low >= 1 us, then high */
bool hal_chg_det(void);             /* CHG_DET (P1.14): VBUS present */

/* ---- bridges: IN1_X P0.19, IN2_X P0.20, IN1_Y P0.21, IN2_Y P0.22 ---- */
void hal_bridge_set(const bridge_cmd_t cmd[2]);  /* takes effect at the next PWM period */

/* ---- slow analogue channels (converted by the port) ---- */
float hal_vbat_volts(void);         /* AIN2 VBAT_SENSE x 2 */
float hal_ntc_ratio(void);          /* AIN3 NTC_COIL / supply, 0..1 */

/* ---- digital sensors (read at the start of each 2 kHz tick) ---- */
typedef struct {
    int16_t raw[3];      /* TMAG5170 X, Y, Z result codes */
    bool fresh;          /* new conversion + frame CRC OK */
} hal_hall_t;
bool hal_hall_read(hal_hall_t *h);

/* ---- system ---- */
void hal_watchdog_kick(void);
bool hal_reset_was_watchdog(void);
uint32_t hal_time_us(void);
/* short critical section around ISR/task shared accumulators */
uint32_t hal_irq_save(void);
void hal_irq_restore(uint32_t state);

#endif /* PEN_HAL_H */
