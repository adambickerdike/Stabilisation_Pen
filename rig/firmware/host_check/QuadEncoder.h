#pragma once
#include "Arduino_stub.h"
struct QuadEncoder { QuadEncoder(uint8_t, uint8_t, uint8_t, uint8_t) {} void setInitConfig() {} void init() {}
  int32_t read() { return 0; } void write(int32_t) {} };
