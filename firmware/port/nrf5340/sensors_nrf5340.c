/*
 * sensors_nrf5340.c - sensor front ends for the stage task.
 * Status: COMPILE-TESTED SKELETON. TMAG5170 frame format and CRC, the
 * LSM6DSV16X FIFO read and the optical modules are VERIFY / pending (the
 * optical sensor is not yet selected, EXP-S01).
 *
 * TMAG5170 (datasheet as recalled, VERIFY): 32-bit SPI frames, MSB first:
 *   byte0 = R/W (bit7, 1 = read) | register address (bits 6:0)
 *   byte1..2 = data (write) / don't care (read)
 *   byte3 = command bits (7:4) | CRC4 (3:0), CRC poly x^4 + x + 1, init 0xF,
 *           over the 28 bits preceding it.
 *   The response to frame n arrives in frame n (status + 16-bit data + CRC).
 *   X/Y/Z_CH_RESULT registers 0x09 / 0x0A / 0x0B (VERIFY).
 */
#include <string.h>

#include "board.h"
#include "hal.h"
#include "nrf5340_regs.h"

#define TMAG_REG_X 0x09u
#define TMAG_REG_Y 0x0Au
#define TMAG_REG_Z 0x0Bu

static volatile uint8_t s_spi_tx[4], s_spi_rx[4];

uint8_t tmag5170_crc4(uint32_t frame28);
uint8_t tmag5170_crc4(uint32_t frame28)
{
    uint8_t crc = 0xFu;
    for (int b = 27; b >= 0; b--) {
        const uint8_t in = (uint8_t)((frame28 >> b) & 1u);
        const uint8_t msb = (uint8_t)((crc >> 3) & 1u);
        crc = (uint8_t)((crc << 1) & 0xFu);
        if ((msb ^ in) != 0u) {
            crc ^= 0x3u;
        }
    }
    return crc;
}

static bool spim4_xfer32(uint8_t reg, uint16_t *data)
{
    const uint32_t f = ((uint32_t)(0x80u | reg) << 24);   /* read, data 0, command 0 */
    const uint8_t crc = tmag5170_crc4(f >> 4);
    s_spi_tx[0] = (uint8_t)(f >> 24);
    s_spi_tx[1] = 0u;
    s_spi_tx[2] = 0u;
    s_spi_tx[3] = crc;
    const uint32_t s = NRF_SPIM4_BASE;
    REG32(s + SPIM_TXD_PTR) = (uint32_t)(uintptr_t)s_spi_tx;
    REG32(s + SPIM_TXD_MAXCNT) = 4u;
    REG32(s + SPIM_RXD_PTR) = (uint32_t)(uintptr_t)s_spi_rx;
    REG32(s + SPIM_RXD_MAXCNT) = 4u;
    REG32(s + SPIM_EVENTS_END) = 0u;
    REG32(s + SPIM_TASKS_START) = 1u;
    for (uint32_t k = 0; k < 2000u; k++) {                  /* ~1 us at 32 Mbit/s (VERIFY) */
        if (REG32(s + SPIM_EVENTS_END) != 0u) {
            *data = (uint16_t)(((uint16_t)s_spi_rx[1] << 8) | s_spi_rx[2]);
            const uint32_t r = ((uint32_t)s_spi_rx[0] << 24) | ((uint32_t)s_spi_rx[1] << 16) |
                               ((uint32_t)s_spi_rx[2] << 8) | s_spi_rx[3];
            return tmag5170_crc4(r >> 4) == (uint8_t)(s_spi_rx[3] & 0xFu);
        }
    }
    return false;
}

void sensors_init(void)
{
    const uint32_t s = NRF_SPIM4_BASE;
    REG32(s + SPIM_PSEL_SCK) = PSEL(0u, PIN_SPIA_SCK);
    REG32(s + SPIM_PSEL_MOSI) = PSEL(0u, PIN_SPIA_MOSI);
    REG32(s + SPIM_PSEL_MISO) = PSEL(0u, PIN_SPIA_MISO);
    REG32(s + SPIM_PSEL_CSN) = PSEL(0u, PIN_HALL_CS_N);
    REG32(s + SPIM_FREQUENCY) = SPIM_FREQ_M8;              /* TMAG5170 max 10 MHz (VERIFY) */
    REG32(s + SPIM_CONFIG) = 0u;                            /* mode 0, MSB first (VERIFY TMAG5170 mode) */
    REG32(s + SPIM_ENABLE) = 7u;
    /* TMAG5170 configuration (continuous conversion, X/Y/Z, +/-25 mT, conversion
     * counter in the status) would be written here: VERIFY register map */
}

bool hal_hall_read(hal_hall_t *h)
{
    uint16_t x = 0, y = 0, z = 0;
    const bool ok = spim4_xfer32(TMAG_REG_X, &x) && spim4_xfer32(TMAG_REG_Y, &y) && spim4_xfer32(TMAG_REG_Z, &z);
    h->raw[0] = (int16_t)x;
    h->raw[1] = (int16_t)y;
    h->raw[2] = (int16_t)z;
    h->fresh = ok;   /* + conversion-counter advance check (VERIFY status bits) */
    return ok;
}

void sensors_read(pen_sensors_t *s)
{
    hal_hall_t h;
    (void)hal_hall_read(&h);
    memcpy(s->hall_raw, h.raw, sizeof(s->hall_raw));
    s->hall_fresh = h.fresh;
    /* IMU FIFO (LSM6DSV16X on SPIB) and the three optical modules: pending
     * driver work and sensor selection. Until then the optics report invalid,
     * so no correction can be commanded (estimators need valid optics). */
    s->imu_n = 0;
    s->imu_dt = 1.0f / 7680.0f;
    s->opt_valid = false;
    s->opt_valid_bits = 0;
    s->opt_surface_lost = true;
}

/* ---- log sink: single-producer ring for the (not yet written) USB CDC task ---- */
#define LOG_RING 8192u
static uint8_t s_ring[LOG_RING];
static volatile uint32_t s_head, s_tail, s_drops;

void board_log_sink(const uint8_t *rec, size_t len, void *ctx)
{
    (void)ctx;
    const uint32_t used = s_head - s_tail;
    if (used + len > LOG_RING) {
        s_drops++;
        return;
    }
    for (size_t k = 0; k < len; k++) {
        s_ring[(s_head + (uint32_t)k) % LOG_RING] = rec[k];
    }
    s_head += (uint32_t)len;
}

uint32_t board_log_read(uint8_t *dst, uint32_t max)
{
    uint32_t n = 0;
    while (n < max && s_tail != s_head) {
        dst[n++] = s_ring[s_tail % LOG_RING];
        s_tail++;
    }
    return n;
}

/* USB CDC transport: not implemented (VERIFY stack choice); weak so the
 * application can provide it */
__attribute__((weak)) void board_usb_cdc_write(const uint8_t *data, uint32_t n)
{
    (void)data;
    (void)n;
}
