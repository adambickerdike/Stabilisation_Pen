// Minimal stubs of the Teensyduino API, used ONLY to syntax-check rig_daq.ino on a PC with g++
// (rig/tests/test_firmware.py). They do nothing; this is not a build and proves nothing about timing.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string>
#include <algorithm>
#define DMAMEM
#define F_CPU_ACTUAL 600000000UL
#define LOW 0
#define HIGH 1
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define RISING 3
#define FALLING 2
#define CHANGE 4
#define MSBFIRST 1
#define SPI_MODE1 0x04
#define SPI_MODE3 0x0C
static volatile uint32_t ARM_DWT_CYCCNT;
inline void __disable_irq() {}
inline void __enable_irq() {}
#define __asm__(...)
inline void noInterrupts() {}
inline void interrupts() {}
inline void pinMode(int, int) {}
inline void digitalWriteFast(int, int) {}
inline int digitalReadFast(int) { return 0; }
inline void analogWrite(int, int) {}
inline void analogWriteResolution(int) {}
inline void analogWriteFrequency(int, float) {}
inline void delayMicroseconds(uint32_t) {}
inline void delay(uint32_t) {}
inline int digitalPinToInterrupt(int p) { return p; }
inline void attachInterrupt(int, void (*)(), int) {}
using std::max;
inline long max(long a, long b) { return a > b ? a : b; }
struct SPISettings { SPISettings(uint32_t, int, int) {} };
struct SPIClass { void begin() {} void beginTransaction(const SPISettings&) {} void endTransaction() {}
  uint8_t transfer(uint8_t) { return 0; } void usingInterrupt(int) {} };
static SPIClass SPI, SPI1;
struct IntervalTimer { bool begin(void (*)(), uint32_t) { return true; } void end() {} };
struct elapsedMicros { uint32_t v = 0; operator uint32_t() const { return v; } elapsedMicros& operator-=(uint32_t d) { v -= d; return *this; } };
struct SerialClass { void begin(uint32_t) {} int available() { return 0; } int read() { return -1; }
  int availableForWrite() { return 64; } size_t write(const uint8_t*, size_t n) { return n; } };
static SerialClass Serial;
class String { std::string s; public: String(const char* c) : s(c) {} void toUpperCase() { for (auto& ch : s) ch = toupper(ch); }
  bool operator==(const char* o) const { return s == o; } };
