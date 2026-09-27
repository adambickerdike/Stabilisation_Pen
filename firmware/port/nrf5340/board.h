/*
 * board.h - Rev A pin plan (electronics/gen/design_revA.py sheet_mcu) and
 * port-internal interfaces. Pin numbers are copied from the schematic
 * generator; peripheral routing and SAADC AIN mapping are VERIFY.
 */
#ifndef PEN_BOARD_H
#define PEN_BOARD_H

#include <stdbool.h>
#include <stdint.h>

#include "app.h"

/* port 0 */
#define PIN_ISNS_X_AIN 0         /* AIN0 / P0.04 */
#define PIN_ISNS_Y_AIN 1         /* AIN1 / P0.05 */
#define PIN_VBAT_AIN 2           /* AIN2 / P0.06 (VBAT/2) */
#define PIN_NTC_AIN 3            /* AIN3 / P0.07 */
#define PIN_VREF_AIN 4           /* AIN4 / P0.25 (VREF_ADC = 1.25 V) */
#define PIN_SPIA_SCK 8           /* P0.08 (SPIM4) */
#define PIN_SPIA_MOSI 9          /* P0.09 */
#define PIN_SPIA_MISO 10         /* P0.10 */
#define PIN_HALL_CS_N 11         /* P0.11 (SPIM4 hardware CSN) */
#define PIN_OPT1_CS_N 12         /* P0.12 */
#define PIN_IN1_X 19             /* P0.19 */
#define PIN_IN2_X 20             /* P0.20 */
#define PIN_IN1_Y 21             /* P0.21 */
#define PIN_IN2_Y 22             /* P0.22 */
#define PIN_DRV_SLEEP_N 23       /* P0.23 */
#define PIN_ACT_EN_REQ 24        /* P0.24 (R71 pull-down) */
#define PIN_OPT2_CS_N 29         /* P0.29 */
#define PIN_OPT3_CS_N 30         /* P0.30 */
/* port 1 */
#define PIN_IMU_CS_N 1           /* P1.01 */
#define PIN_SPIB_SCK 2           /* P1.02 */
#define PIN_SPIB_MOSI 3          /* P1.03 */
#define PIN_SPIB_MISO 4          /* P1.04 */
#define PIN_FAULT_N 7            /* P1.07 */
#define PIN_FAULT_CLR_N 12       /* P1.12 (R74 pull-up) */
#define PIN_HALL_ALERT_N 13      /* P1.13 */
#define PIN_CHG_DET 14           /* P1.14 */

/* scheduler.c */
extern pen_app_t g_app;
void sched_init(void);
void SAADC_IRQHandler(void);   /* 40 kHz current loop */
void EGU0_IRQHandler(void);    /* 2 kHz stage task */
/* hal_nrf5340.c */
void board_gpio_init(void);
void board_timebase_init(void);
void board_wdt_init(void);
void board_slow_adc_store(int16_t vbat_code, int16_t ntc_code);
/* sensors_nrf5340.c */
void sensors_init(void);
void sensors_read(pen_sensors_t *s);
/* log sink (ring buffer drained by the USB CDC task, not implemented) */
void board_log_sink(const uint8_t *rec, size_t len, void *ctx);
uint32_t board_log_read(uint8_t *dst, uint32_t max);
void board_usb_cdc_write(const uint8_t *data, uint32_t n);

#endif /* PEN_BOARD_H */
