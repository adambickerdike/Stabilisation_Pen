// Host-side check of rig_protocol.h against rig/protocol.py (built and run by rig/tests/test_firmware.py with g++).
// Prints the CRC check value and two framed payloads as hex; the test packs the same values in Python and compares.
#include <stdio.h>
#include "../rig_daq/rig_protocol.h"
int main() {
  printf("crc=0x%04X\n", crc16_ccitt((const uint8_t *)"123456789", 9));
  SamplePayload s = {};
  s.seq = 7; s.t_cyc = 123456789012ULL;
  for (int i = 0; i < 8; i++) s.adc[i] = -1000 * i + 5;
  for (int i = 0; i < 4; i++) s.enc[i] = 100000 * i - 3;
  s.cmd = -42; s.flags = 0x93; s.nadc = 8; s.rsv = 0;
  uint8_t buf[80];
  size_t n = rig_frame(buf, T_SAMPLE, &s, sizeof(s));
  for (size_t i = 0; i < n; i++) printf("%02x", buf[i]);
  printf("\n");
  EventPayload e = {}; e.seq = 3; e.t_cyc = 99; e.kind = EV_TEMP; e.value = 0x02000320;
  n = rig_frame(buf, T_EVENT, &e, sizeof(e));
  for (size_t i = 0; i < n; i++) printf("%02x", buf[i]);
  printf("\n");
  ImuPayload m = {}; m.seq = 1; m.t_cyc = 5; m.acc[0] = -2; m.gyr[2] = 300; m.temp = 25;
  n = rig_frame(buf, T_IMU, &m, sizeof(m));
  for (size_t i = 0; i < n; i++) printf("%02x", buf[i]);
  printf("\n");
  return 0;
}
