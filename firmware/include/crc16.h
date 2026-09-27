/*
 * crc16.h - CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection,
 * xorout 0x0000). Check value: "123456789" -> 0x29B1 (ICD s4.1).
 */
#ifndef PEN_CRC16_H
#define PEN_CRC16_H

#include <stddef.h>
#include <stdint.h>

#define CRC16_CCITT_INIT 0xFFFFu

uint16_t crc16_ccitt_update(uint16_t crc, const uint8_t *data, size_t len);

static inline uint16_t crc16_ccitt(const uint8_t *data, size_t len)
{
    return crc16_ccitt_update((uint16_t)CRC16_CCITT_INIT, data, len);
}

#endif /* PEN_CRC16_H */
