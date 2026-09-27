/*
 * crc16.c - CRC-16/CCITT-FALSE, bitwise (small code, ~8 cycles/bit on M33;
 * the 2 kHz research frame is 54 bytes). Host KAT: tests/test_log.c.
 */
#include "crc16.h"

uint16_t crc16_ccitt_update(uint16_t crc, const uint8_t *data, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        crc = (uint16_t)(crc ^ (uint16_t)((uint16_t)data[i] << 8));
        for (int b = 0; b < 8; b++) {
            if ((crc & 0x8000u) != 0u) {
                crc = (uint16_t)((uint16_t)(crc << 1) ^ 0x1021u);
            } else {
                crc = (uint16_t)(crc << 1);
            }
        }
    }
    return crc;
}
