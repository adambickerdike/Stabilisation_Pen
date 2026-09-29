// rig_protocol.h -- binary frames from DAQ-1 (Teensy 4.1) to the host.
//
// PROPOSED DESIGN. Mirrors rig/protocol.py (the Python side is the reference; rig/tests check the sizes
// and the CRC check value). Little-endian, packed.
//
//   0xA5 0x5A | type u8 | len u8 | payload[len] | crc16 u16
//
// crc16 = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no final xor) over type, len and
// payload; check value for "123456789" is 0x29B1.
#pragma once
#include <stdint.h>
#include <stddef.h>

#define RIG_SYNC0 0xA5
#define RIG_SYNC1 0x5A

enum : uint8_t {
  T_SAMPLE = 0x01,   // one ADC conversion + encoder latch + command, per DRDY
  T_EVENT = 0x02,    // edges, markers, camera/strobe, temperatures
  T_TEXT = 0x03,     // ASCII status and errors
  T_CONFIG = 0x04,   // ASCII key=value;... (f_cpu, adc_rate, gains, channel use, firmware version)
  T_IMU = 0x05,      // LSM6DSV16X sample (recording pen)
  T_PAGE = 0x06,     // page sensor increments
};

enum : uint8_t {
  EV_SYNC_OUT_RISE = 1, EV_SYNC_OUT_FALL = 2, EV_DUT_RISE = 3, EV_DUT_FALL = 4, EV_CAM_TRIGGER = 5,
  EV_STROBE = 6, EV_MARKER = 7, EV_LIFT = 8, EV_OVERRUN = 9, EV_TEMP = 10,
};

// SAMPLE flags
enum : uint16_t {
  F_CAM = 1u << 0, F_SYNC = 1u << 1, F_DUT = 1u << 2, F_STROBE = 1u << 3, F_DIST_LOOP = 1u << 4,
  F_CURRENT_LOOP = 1u << 5, F_GOVERNOR = 1u << 6, F_OVERRUN = 1u << 7,
};

#pragma pack(push, 1)
struct SamplePayload {      // 68 bytes
  uint32_t seq;
  uint64_t t_cyc;
  int32_t adc[8];
  int32_t enc[4];
  int32_t cmd;
  uint16_t flags;
  uint8_t nadc;
  uint8_t rsv;
};
struct EventPayload {       // 20 bytes
  uint32_t seq;
  uint64_t t_cyc;
  uint8_t kind;
  uint8_t pad[3];
  uint32_t value;
};
struct ImuPayload {         // 28 bytes
  uint32_t seq;
  uint64_t t_cyc;
  int16_t acc[3];
  int16_t gyr[3];
  int16_t temp;
  uint16_t rsv;
};
struct PagePayload {        // 20 bytes
  uint32_t seq;
  uint64_t t_cyc;
  int16_t dx;
  int16_t dy;
  uint8_t squal;
  uint8_t valid;
  uint16_t rsv;
};
#pragma pack(pop)

static_assert(sizeof(SamplePayload) == 68, "SAMPLE payload must be 68 bytes (rig/protocol.py)");
static_assert(sizeof(EventPayload) == 20, "EVENT payload must be 20 bytes");
static_assert(sizeof(ImuPayload) == 28, "IMU payload must be 28 bytes");
static_assert(sizeof(PagePayload) == 20, "PAGE payload must be 20 bytes");

// CRC-16/CCITT-FALSE, bitwise (the ISR frames are short; 74 bytes per SAMPLE)
static inline uint16_t crc16_ccitt(const uint8_t *p, size_t n, uint16_t crc = 0xFFFF) {
  while (n--) {
    crc ^= (uint16_t)(*p++) << 8;
    for (int i = 0; i < 8; i++) crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  }
  return crc;
}

// Frame into dst (needs len + 6 bytes); returns the number of bytes written.
static inline size_t rig_frame(uint8_t *dst, uint8_t type, const void *payload, uint8_t len) {
  dst[0] = RIG_SYNC0;
  dst[1] = RIG_SYNC1;
  dst[2] = type;
  dst[3] = len;
  const uint8_t *s = (const uint8_t *)payload;
  for (uint8_t i = 0; i < len; i++) dst[4 + i] = s[i];
  uint16_t c = crc16_ccitt(dst + 2, (size_t)len + 2);
  dst[4 + len] = (uint8_t)(c & 0xFF);
  dst[5 + len] = (uint8_t)(c >> 8);
  return (size_t)len + 6;
}
