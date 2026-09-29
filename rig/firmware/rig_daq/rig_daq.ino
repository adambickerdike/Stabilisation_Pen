// rig_daq.ino -- DAQ-1 firmware for the study-M measurement rigs (R9-R14): one clock for every channel.
//
// Evidence status: PROPOSED DESIGN. NOT COMPILED OR RUN in this study (no Teensy toolchain in the container).
// Build: Arduino IDE >= 2.3.10 with Teensyduino 1.62 (MFR AMF-237), board "Teensy 4.1", USB Type "Serial",
// CPU 600 MHz. Library: QuadEncoder (file QuadEncoder.h, MFR AMF-238). First bring-up steps in
// docs/measurement_rig.md section 1.3 (loop-back tests before any rig is connected).
//
// What it does, in one interrupt per ADC conversion (ADS131M08 DRDY, 1/2/4/8 kSPS):
//   stamp the 64-bit cycle count -> read the ADS131M08 frame (8 channels, simultaneous) -> latch the four
//   hardware quadrature counters -> compute the disturbance command (multitone, sweep or hold) and run the
//   stage servo (R13) or the current setpoint (R12) -> camera trigger, strobe and coded sync pulse -> one
//   68-byte SAMPLE frame into a ring buffer that loop() drains to USB.
// Datasheet facts used (ADS131M08, SBAS950B, MFR AMF-222): SPI mode 1 (CPOL 0, CPHA 1); 24-bit words, a
// 10-word frame (response, 8 channels, CRC); commands NULL 0x0000, WREG 011a aaaa annn nnnn; MODE 0x02
// (reset 0x0510), CLOCK 0x03 (reset 0xFF0E, OSR[4:2], PWR[1:0]), GAIN1 0x04 / GAIN2 0x05 (3-bit PGA codes,
// 0 = 1 ... 7 = 128); SYNC/RESET low >= 2048 CLKIN periods resets; data rate f_CLKIN / (2 OSR).
// LSM6DSV16X registers from ST's lsm6dsv16x_reg.h (MFR OPT-92). MAX31856 and page-sensor register
// addresses marked UNVERIFIED were NOT checked against a data sheet in this study: verify before use.

#include <SPI.h>
#include <IntervalTimer.h>
#include "QuadEncoder.h"
#include "rig_protocol.h"

#define FW_VERSION "rig_daq 0.1 (study M, proposed)"

// ------------------------------------------------------------------------------------------ pins (doc 1.2)
const int PIN_ADC_CS = 10, PIN_ADC_DRDY = 9, PIN_ADC_SYNCRST = 6;           // SPI0: 11 MOSI, 12 MISO, 13 SCK
const int PIN_CAM = 24, PIN_STROBE = 25, PIN_SYNC_OUT = 28, PIN_DUT_IN = 29, PIN_MARKER = 32;
const int PIN_PWM_A = 22, PIN_PWM_B = 23;                                     // -> RC -> OPA548 current amps
const int PIN_IMU_CS = 38, PIN_PAGE_CS = 36, PIN_IMU_INT1 = 35, PIN_PAGE_MOTION = 34;   // SPI1: 26, 27, 39
const int PIN_TC_CS[4] = {0, 1, 14, 15};                                      // MAX31856 on SPI0

QuadEncoder enc1(1, 2, 3, 0), enc2(2, 4, 7, 0), enc3(3, 8, 30, 0), enc4(4, 31, 33, 0);

SPISettings adcSPI(16000000, MSBFIRST, SPI_MODE1);    // SCLK period >= 40 ns allowed; 16 MHz: 15 us per frame
SPISettings tcSPI(4000000, MSBFIRST, SPI_MODE1);      // MAX31856 (UNVERIFIED: mode 1 or 3, <= 5 MHz)
SPISettings imuSPI(8000000, MSBFIRST, SPI_MODE3);     // LSM6DSV16X
SPISettings pageSPI(2000000, MSBFIRST, SPI_MODE3);    // PMW3901-class page sensors (UNVERIFIED)

// ------------------------------------------------------------------------------------------ one clock
static volatile uint32_t cyc_hi = 0, cyc_last = 0;
static inline uint64_t now_cyc() {
  uint32_t primask;
  __asm__ volatile("mrs %0, primask" : "=r"(primask));
  __disable_irq();
  uint32_t c = ARM_DWT_CYCCNT;
  if (c < cyc_last) cyc_hi++;           // wraps every 7.2 s at 600 MHz; the DRDY ISR calls this >= 1000 times/s
  cyc_last = c;
  uint64_t t = ((uint64_t)cyc_hi << 32) | c;
  if (!primask) __enable_irq();
  return t;
}

// ------------------------------------------------------------------------------------------ ring buffer
static const uint32_t RB_SIZE = 1u << 17;             // 128 KiB: 1.7 s of SAMPLE frames at 4 kSPS
DMAMEM static uint8_t rb[RB_SIZE];
static volatile uint32_t rb_head = 0, rb_tail = 0, rb_dropped = 0;
static volatile bool overrun_flag = false;

static bool rb_push(const uint8_t *p, uint32_t n) {   // called with interrupts masked or from the ISR
  uint32_t h = rb_head, t = rb_tail;
  uint32_t used = (h - t) & (RB_SIZE - 1);
  if (RB_SIZE - 1 - used < n) { rb_dropped++; overrun_flag = true; return false; }
  for (uint32_t i = 0; i < n; i++) rb[(h + i) & (RB_SIZE - 1)] = p[i];
  __asm__ volatile("dmb" ::: "memory");
  rb_head = (h + n) & (RB_SIZE - 1);
  return true;
}

static void push_frame(uint8_t type, const void *payload, uint8_t len) {
  uint8_t buf[262];
  uint32_t n = rig_frame(buf, type, payload, len);
  uint32_t primask;
  __asm__ volatile("mrs %0, primask" : "=r"(primask));
  __disable_irq();
  rb_push(buf, n);
  if (!primask) __enable_irq();
}

static volatile uint32_t ev_seq = 0;
static volatile bool running = false;
static void push_event(uint8_t kind, uint32_t value, uint64_t t) {
  if (!running) return;                                   // edges keep happening; they are logged only while running
  EventPayload e = {};
  e.seq = ev_seq++;
  e.t_cyc = t;
  e.kind = kind;
  e.value = value;
  push_frame(T_EVENT, &e, sizeof(e));
}

static void push_text(const char *s, uint8_t type = T_TEXT) {
  size_t n = strlen(s);
  if (n > 255) n = 255;
  push_frame(type, s, (uint8_t)n);
}

// ------------------------------------------------------------------------------------------ ADS131M08
static const uint8_t ADC_WORDS = 10, ADC_WB = 3;      // 24-bit words
static uint8_t adc_gain_code[8] = {7, 7, 7, 7, 0, 0, 0, 0};   // 128 on the bridges, 1 elsewhere (doc 1.2)
static uint8_t adc_osr_code = 3;                               // 1024 -> 4 kSPS at 8.192 MHz
static volatile uint32_t adc_rate = 4000;

static void adc_frame(const uint16_t *cmd_words, uint8_t n_cmd, uint8_t *rx) {
  // one full frame: command words MSB-aligned in 24-bit words, zeros after; rx gets 30 bytes
  uint8_t tx[ADC_WORDS * ADC_WB] = {0};
  for (uint8_t i = 0; i < n_cmd && i < ADC_WORDS; i++) {
    tx[i * ADC_WB] = cmd_words[i] >> 8;
    tx[i * ADC_WB + 1] = cmd_words[i] & 0xFF;
  }
  SPI.beginTransaction(adcSPI);
  digitalWriteFast(PIN_ADC_CS, LOW);
  for (uint8_t i = 0; i < ADC_WORDS * ADC_WB; i++) rx[i] = SPI.transfer(tx[i]);
  digitalWriteFast(PIN_ADC_CS, HIGH);
  SPI.endTransaction();
}

static void adc_wreg(uint8_t addr, uint16_t value) {
  uint16_t w[2] = {(uint16_t)(0x6000 | ((uint16_t)addr << 7)), value};   // WREG, one register (nnn nnnn = 0)
  uint8_t rx[ADC_WORDS * ADC_WB];
  adc_frame(w, 2, rx);
  delayMicroseconds(20);
}

static uint16_t adc_rreg(uint8_t addr) {
  uint16_t w[1] = {(uint16_t)(0xA000 | ((uint16_t)addr << 7))};          // RREG, one register
  uint8_t rx[ADC_WORDS * ADC_WB];
  adc_frame(w, 1, rx);
  uint16_t z[1] = {0x0000};                                               // the reply comes in the next frame
  adc_frame(z, 1, rx);
  return ((uint16_t)rx[0] << 8) | rx[1];
}

static void adc_configure() {
  adc_wreg(0x02, 0x0110);                                   // MODE: 24-bit, SPI timeout on, clear RESET flag
  adc_wreg(0x03, (uint16_t)(0xFF00 | (adc_osr_code << 2) | 0x2));   // CLOCK: all channels, OSR, high resolution
  uint16_t g1 = 0, g2 = 0;
  for (int c = 0; c < 4; c++) g1 |= (uint16_t)(adc_gain_code[c] & 7) << (4 * c);
  for (int c = 0; c < 4; c++) g2 |= (uint16_t)(adc_gain_code[4 + c] & 7) << (4 * c);
  adc_wreg(0x04, g1);                                       // GAIN1 (channels 0-3)
  adc_wreg(0x05, g2);                                       // GAIN2 (channels 4-7)
  static const uint16_t osr_val[8] = {128, 256, 512, 1024, 2048, 4096, 8192, 16256};
  adc_rate = (uint32_t)(8192000UL / (2UL * osr_val[adc_osr_code]));
}

static void adc_reset() {
  digitalWriteFast(PIN_ADC_SYNCRST, LOW);
  delayMicroseconds(400);                                   // >= 2048 CLKIN periods (250 us at 8.192 MHz)
  digitalWriteFast(PIN_ADC_SYNCRST, HIGH);
  delayMicroseconds(50);                                    // >= t_REGACQ (5 us)
}

// ------------------------------------------------------------------------------------------ disturbance command
struct Tone { float f, amp, phase; };
static Tone tones[32];
static volatile uint8_t n_tones = 0;
static volatile bool sweep_on = false;
static float sweep_f0 = 1, sweep_f1 = 30, sweep_T = 10, sweep_amp = 0;
static volatile int32_t hold_counts = 0;
static volatile uint32_t wave_tick = 0;
static volatile bool wave_on = false;

static int32_t command_counts() {
  if (!wave_on) return hold_counts;
  double t = (double)wave_tick / (double)adc_rate;
  double x = 0;
  if (sweep_on) {                                             // exponential (log) sweep, restarts every T
    double tt = fmod(t, (double)sweep_T);
    double k = log((double)sweep_f1 / sweep_f0);
    double ph = 2 * M_PI * sweep_f0 * sweep_T / k * (exp(tt / sweep_T * k) - 1.0);
    x = sweep_amp * sin(ph);
  } else {
    for (uint8_t i = 0; i < n_tones; i++) x += tones[i].amp * sin(2 * M_PI * tones[i].f * t + tones[i].phase);
  }
  wave_tick++;
  return hold_counts + (int32_t)lround(x);
}

// servo (R13): current = KP e + KI int(e) + KD de + KFF a_cmd; e and a_cmd in encoder counts
static volatile bool dist_loop = false, current_loop = false;
static float KP = 0, KI = 0, KD = 0, KFF = 0, ILIM_A = 1.0f, ISCALE_A = 3.0f;   // ISCALE: amps at full PWM swing
static float integ = 0, e_last = 0;
static int32_t cmd_hist[3] = {0, 0, 0};
static volatile int32_t trip_err = 4000, trip_pos = 12000;      // counts (1 mm, 3 mm at 0.244 um/count)
static volatile float iset_A = 0;                                 // R12 current setpoint
static volatile bool governor = false;

static void write_current(int pin, float amps) {
  bool lim = false;
  if (amps > ILIM_A) { amps = ILIM_A; lim = true; }
  if (amps < -ILIM_A) { amps = -ILIM_A; lim = true; }
  governor = lim;
  int duty = 2048 + (int)lroundf(2047.0f * amps / ISCALE_A);     // mid-scale = 0 A (bipolar current amp)
  if (duty < 0) duty = 0;
  if (duty > 4095) duty = 4095;
  analogWrite(pin, duty);
}

// ------------------------------------------------------------------------------------------ camera, strobe, sync
static volatile uint32_t cam_div = 40, cam_count = 0, strobe_delay_us = 200, strobe_width_us = 30;
static volatile bool cam_on = false, cam_high = false, sync_on = true, sync_high = false;
static volatile uint32_t sync_tick = 0;
static volatile uint8_t sync_n = 0;
IntervalTimer strobeOn, strobeOff, syncFall;

static void strobe_off_cb() {
  digitalWriteFast(PIN_STROBE, LOW);
  strobeOff.end();
}
static void strobe_on_cb() {
  strobeOn.end();
  digitalWriteFast(PIN_STROBE, HIGH);
  push_event(EV_STROBE, cam_count, now_cyc());
  strobeOff.begin(strobe_off_cb, strobe_width_us);
}
static void sync_fall_cb() {
  syncFall.end();
  digitalWriteFast(PIN_SYNC_OUT, LOW);
  sync_high = false;
  push_event(EV_SYNC_OUT_FALL, sync_n, now_cyc());
  sync_n++;
}

// ------------------------------------------------------------------------------------------ thermocouples (MAX31856)
static volatile uint8_t tc_mask = 0, tc_next = 0;
static volatile uint32_t tc_div = 400, tc_count = 0;

static uint32_t tc_read_raw(int ch) {                      // UNVERIFIED: LTCBH 0x0C, LTCBM 0x0D, LTCBL 0x0E
  SPI.beginTransaction(tcSPI);
  digitalWriteFast(PIN_TC_CS[ch], LOW);
  SPI.transfer(0x0C);
  uint32_t b2 = SPI.transfer(0), b1 = SPI.transfer(0), b0 = SPI.transfer(0);
  digitalWriteFast(PIN_TC_CS[ch], HIGH);
  SPI.endTransaction();
  return (b2 << 16) | (b1 << 8) | b0;
}

static void tc_init(int ch) {                              // UNVERIFIED: CR0 0x00 (0x80 auto conversion), CR1 0x01 (type T = 0x07)
  SPI.beginTransaction(tcSPI);
  digitalWriteFast(PIN_TC_CS[ch], LOW);
  SPI.transfer(0x80 | 0x00);
  SPI.transfer(0x80);
  SPI.transfer(0x07);
  digitalWriteFast(PIN_TC_CS[ch], HIGH);
  SPI.endTransaction();
}

// ------------------------------------------------------------------------------------------ the DRDY interrupt
static volatile uint32_t sample_seq = 0;

static void drdy_isr() {
  uint64_t t = now_cyc();
  uint8_t rx[ADC_WORDS * ADC_WB];
  uint16_t nul[1] = {0x0000};
  adc_frame(nul, 1, rx);
  int32_t e0 = enc1.read(), e1 = enc2.read(), e2 = enc3.read(), e3 = enc4.read();

  SamplePayload s = {};                                     // the servo, camera and sync run whether or not we log
  s.seq = sample_seq++;
  s.t_cyc = t;
  uint8_t status_lo = rx[1];
  s.nadc = (uint8_t)__builtin_popcount(status_lo);           // STATUS DRDY bits of the eight channels
  for (int c = 0; c < 8; c++) {
    const uint8_t *w = &rx[(1 + c) * ADC_WB];
    int32_t v = ((int32_t)w[0] << 16) | ((int32_t)w[1] << 8) | w[2];
    if (v & 0x800000) v -= 0x1000000;
    s.adc[c] = v;
  }
  s.enc[0] = e0; s.enc[1] = e1; s.enc[2] = e2; s.enc[3] = e3;

  int32_t cmd = command_counts();
  s.cmd = cmd;
  uint16_t flags = 0;

  if (dist_loop) {                                            // R13 stage on encoder channel 3 (enc[2])
    if (abs(e2 - cmd) > trip_err || abs(e2) > trip_pos) {
      dist_loop = false;
      write_current(PIN_PWM_A, 0);
      push_text("TRIP: disturbance loop off (error or position limit)");
    } else {
      float e = (float)(cmd - e2);
      float dt = 1.0f / (float)adc_rate;
      integ += e * dt;
      float de = (e - e_last) / dt;
      e_last = e;
      cmd_hist[2] = cmd_hist[1]; cmd_hist[1] = cmd_hist[0]; cmd_hist[0] = cmd;
      float acc = (float)(cmd_hist[0] - 2 * cmd_hist[1] + cmd_hist[2]) / (dt * dt);
      write_current(PIN_PWM_A, KP * e + KI * integ + KD * de + KFF * acc);
      flags |= F_DIST_LOOP;
    }
  }
  if (current_loop) {                                         // R12 coupon current (amplifier closes the loop)
    write_current(PIN_PWM_B, iset_A);
    flags |= F_CURRENT_LOOP;
  }
  if (governor) flags |= F_GOVERNOR;

  if (cam_on) {
    if (cam_high) { digitalWriteFast(PIN_CAM, LOW); cam_high = false; }
    if (++cam_count % cam_div == 0) {
      digitalWriteFast(PIN_CAM, HIGH);                       // OV9281: frame on the rising edge, >= 2 us (MFR OPT-88)
      cam_high = true;
      uint64_t tc = now_cyc();
      push_event(EV_CAM_TRIGGER, cam_count / cam_div, tc);
      strobeOn.begin(strobe_on_cb, strobe_delay_us);
      flags |= F_CAM;
    }
  }
  if (sync_on && ++sync_tick >= adc_rate) {                  // coded sync: 1 ms + n * 0.25 ms, once per second
    sync_tick = 0;
    digitalWriteFast(PIN_SYNC_OUT, HIGH);
    sync_high = true;
    push_event(EV_SYNC_OUT_RISE, sync_n, now_cyc());
    syncFall.begin(sync_fall_cb, 1000 + 250 * (uint32_t)sync_n);
  }
  if (sync_high) flags |= F_SYNC;
  if (digitalReadFast(PIN_DUT_IN)) flags |= F_DUT;
  if (digitalReadFast(PIN_STROBE)) flags |= F_STROBE;
  if (overrun_flag) { flags |= F_OVERRUN; overrun_flag = false; }
  s.flags = flags;

  if (tc_mask && ++tc_count >= tc_div) {                     // one thermocouple per tc_div ticks, round robin
    tc_count = 0;
    for (int k = 0; k < 4; k++) {
      uint8_t ch = (tc_next + k) & 3;
      if (tc_mask & (1 << ch)) {
        uint32_t raw = tc_read_raw(ch);
        push_event(EV_TEMP, ((uint32_t)ch << 24) | (raw & 0xFFFFFF), now_cyc());
        tc_next = (ch + 1) & 3;
        break;
      }
    }
  }
  if (running) push_frame(T_SAMPLE, &s, sizeof(s));
}

// ------------------------------------------------------------------------------------------ edges from outside
static void dut_isr() {
  uint64_t t = now_cyc();
  push_event(digitalReadFast(PIN_DUT_IN) ? EV_DUT_RISE : EV_DUT_FALL, 0, t);
}
static void marker_isr() { push_event(EV_MARKER, 0xFFFFFFFF, now_cyc()); }

// ------------------------------------------------------------------------------------------ IMU (LSM6DSV16X, recording pen)
static volatile bool imu_on = false, spi1_busy = false, imu_pending = false;
static volatile uint64_t imu_pending_t = 0;
static volatile uint32_t imu_seq = 0;

static void imu_write(uint8_t reg, uint8_t v) {
  SPI1.beginTransaction(imuSPI);
  digitalWriteFast(PIN_IMU_CS, LOW);
  SPI1.transfer(reg & 0x7F);
  SPI1.transfer(v);
  digitalWriteFast(PIN_IMU_CS, HIGH);
  SPI1.endTransaction();
}
static uint8_t imu_read(uint8_t reg) {
  SPI1.beginTransaction(imuSPI);
  digitalWriteFast(PIN_IMU_CS, LOW);
  SPI1.transfer(reg | 0x80);
  uint8_t v = SPI1.transfer(0);
  digitalWriteFast(PIN_IMU_CS, HIGH);
  SPI1.endTransaction();
  return v;
}
static bool imu_init() {
  if (imu_read(0x0F) != 0x70) return false;               // WHO_AM_I = LSM6DSV16X_ID
  imu_write(0x12, 0x01);                                   // CTRL3: SW_RESET
  delay(10);
  imu_write(0x12, 0x44);                                   // CTRL3: BDU (bit 6) + IF_INC (bit 2)
  imu_write(0x15, 0x04);                                   // CTRL6: FS_G = 2000 dps
  imu_write(0x17, 0x03);                                   // CTRL8: FS_XL = 16 g
  imu_write(0x10, 0x0A);                                   // CTRL1: ODR_XL = 1.92 kHz, high-performance
  imu_write(0x11, 0x0A);                                   // CTRL2: ODR_G = 1.92 kHz, high-performance
  imu_write(0x0D, 0x02);                                   // INT1_CTRL: gyroscope data-ready on INT1
  return true;
}
static void imu_read_frame(uint64_t t) {
  uint8_t b[14];
  SPI1.beginTransaction(imuSPI);
  digitalWriteFast(PIN_IMU_CS, LOW);
  SPI1.transfer(0x20 | 0x80);                              // OUT_TEMP_L .. OUTZ_H_A (temp, gyro, accel)
  for (int i = 0; i < 14; i++) b[i] = SPI1.transfer(0);
  digitalWriteFast(PIN_IMU_CS, HIGH);
  SPI1.endTransaction();
  ImuPayload p = {};
  p.seq = imu_seq++;
  p.t_cyc = t;
  p.temp = (int16_t)(b[0] | (b[1] << 8));
  for (int i = 0; i < 3; i++) p.gyr[i] = (int16_t)(b[2 + 2 * i] | (b[3 + 2 * i] << 8));
  for (int i = 0; i < 3; i++) p.acc[i] = (int16_t)(b[8 + 2 * i] | (b[9 + 2 * i] << 8));
  push_frame(T_IMU, &p, sizeof(p));
}
static void imu_isr() {
  uint64_t t = now_cyc();                                  // the data-ready edge is the sample time
  if (!imu_on) return;
  if (spi1_busy) { imu_pending_t = t; imu_pending = true; return; }   // loop() owns SPI1: read it there
  imu_read_frame(t);
}

// ------------------------------------------------------------------------------------------ page sensor (polled in loop)
static volatile bool page_on = false;
static uint32_t page_seq = 0, page_period_us = 1000;
static elapsedMicros page_timer;

static uint8_t page_reg(uint8_t reg) {                   // UNVERIFIED PMW3901-class timing: address, wait, data
  SPI1.beginTransaction(pageSPI);
  digitalWriteFast(PIN_PAGE_CS, LOW);
  SPI1.transfer(reg & 0x7F);
  delayMicroseconds(50);
  uint8_t v = SPI1.transfer(0);
  digitalWriteFast(PIN_PAGE_CS, HIGH);
  SPI1.endTransaction();
  delayMicroseconds(1);
  return v;
}
static void page_poll() {                                // UNVERIFIED: MOTION 0x02, DX 0x03/0x04, DY 0x05/0x06, SQUAL 0x07
  spi1_busy = true;                                      // the IMU ISR defers to loop() meanwhile (no GPIO IRQ masking)
  uint64_t t = now_cyc();
  uint8_t motion = page_reg(0x02);
  int16_t dx = (int16_t)(page_reg(0x03) | (page_reg(0x04) << 8));
  int16_t dy = (int16_t)(page_reg(0x05) | (page_reg(0x06) << 8));
  uint8_t squal = page_reg(0x07);
  PagePayload p = {};
  p.seq = page_seq++;
  p.t_cyc = t;
  p.dx = dx;
  p.dy = dy;
  p.squal = squal;
  p.valid = (motion & 0x80) ? 1 : 0;
  push_frame(T_PAGE, &p, sizeof(p));
  spi1_busy = false;
  if (imu_pending) { imu_pending = false; imu_read_frame(imu_pending_t); }
}

// ------------------------------------------------------------------------------------------ host commands
static void send_config() {
  char s[255];
  snprintf(s, sizeof(s), "fw=%s;f_cpu=%lu;adc_rate=%lu;osr_code=%u;gain_codes=%u,%u,%u,%u,%u,%u,%u,%u;cam_div=%lu;"
           "strobe_delay_us=%lu;strobe_width_us=%lu;sync_w0_us=1000;sync_dw_us=250;tc_mask=%u",
           FW_VERSION, (unsigned long)F_CPU_ACTUAL, (unsigned long)adc_rate, adc_osr_code, adc_gain_code[0], adc_gain_code[1],
           adc_gain_code[2], adc_gain_code[3], adc_gain_code[4], adc_gain_code[5], adc_gain_code[6], adc_gain_code[7],
           (unsigned long)cam_div, (unsigned long)strobe_delay_us, (unsigned long)strobe_width_us, tc_mask);
  push_text(s, T_CONFIG);
  snprintf(s, sizeof(s), "servo=KP %.4g KI %.4g KD %.4g KFF %.4g ILIM %.3g ISCALE %.3g trip_err %ld trip_pos %ld;tones=%u;sweep=%d",
           KP, KI, KD, KFF, ILIM_A, ISCALE_A, (long)trip_err, (long)trip_pos, n_tones, sweep_on ? 1 : 0);
  push_text(s, T_CONFIG);
}

static void handle(char *line) {
  char *cmd = strtok(line, " \t\r\n");
  if (!cmd) return;
  char *a1 = strtok(NULL, " \t\r\n"), *a2 = strtok(NULL, " \t\r\n"), *a3 = strtok(NULL, " \t\r\n"), *a4 = strtok(NULL, " \t\r\n");
  String c(cmd);
  c.toUpperCase();
  noInterrupts();
  if (c == "START") { sample_seq = 0; running = true; }
  else if (c == "STOP") { running = false; }
  else if (c == "RATE" && a1) {                                   // 1000, 2000, 4000 or 8000 samples/s
    long r = atol(a1);
    adc_osr_code = r >= 8000 ? 2 : r >= 4000 ? 3 : r >= 2000 ? 4 : 5;
    interrupts(); adc_configure(); noInterrupts();
  }
  else if (c == "GAIN" && a1 && a2) { int ch = atoi(a1), g = atoi(a2); if (ch >= 0 && ch < 8) adc_gain_code[ch] = (uint8_t)(g & 7);
                                      interrupts(); adc_configure(); noInterrupts(); }
  else if (c == "MARK" && a1) { interrupts(); push_event(EV_MARKER, (uint32_t)atol(a1), now_cyc()); noInterrupts(); }
  else if (c == "CAM" && a1) { cam_div = max(1L, atol(a1)); if (a2) strobe_delay_us = atol(a2); if (a3) strobe_width_us = atol(a3); cam_on = true; }
  else if (c == "CAMOFF") { cam_on = false; }
  else if (c == "SYNC" && a1) { sync_on = atoi(a1) != 0; }
  else if (c == "TONES") { n_tones = 0; }
  else if (c == "TONE" && a1 && a2 && a3) { if (n_tones < 32) { tones[n_tones].f = atof(a1); tones[n_tones].amp = atof(a2);
                                             tones[n_tones].phase = a3 ? atof(a3) : 0; n_tones++; } }
  else if (c == "SWEEP" && a1 && a2 && a3 && a4) { sweep_f0 = atof(a1); sweep_f1 = atof(a2); sweep_T = atof(a3); sweep_amp = atof(a4); sweep_on = true; }
  else if (c == "WAVE" && a1) { wave_on = atoi(a1) != 0; wave_tick = 0; if (!wave_on) sweep_on = false; }
  else if (c == "HOLD" && a1) { hold_counts = atol(a1); }
  else if (c == "ZERO" && a1) { int k = atoi(a1); QuadEncoder *e[4] = {&enc1, &enc2, &enc3, &enc4};
                                if (k >= 1 && k <= 4) e[k - 1]->write(0); }
  else if (c == "SERVO" && a1 && a2 && a3 && a4) { KP = atof(a1); KI = atof(a2); KD = atof(a3); KFF = atof(a4); integ = 0; e_last = 0; }
  else if (c == "ILIM" && a1) { ILIM_A = atof(a1); if (a2) ISCALE_A = atof(a2); }
  else if (c == "TRIP" && a1 && a2) { trip_err = atol(a1); trip_pos = atol(a2); }
  else if (c == "DIST" && a1) { dist_loop = atoi(a1) != 0; integ = 0; if (!dist_loop) write_current(PIN_PWM_A, 0); }
  else if (c == "ISET" && a1) { iset_A = atof(a1); current_loop = true; }
  else if (c == "IOFF") { current_loop = false; write_current(PIN_PWM_B, 0); }
  else if (c == "TC" && a1) { tc_mask = (uint8_t)atoi(a1) & 0x0F; if (a2) tc_div = max(1L, atol(a2));
                              interrupts(); for (int k = 0; k < 4; k++) if (tc_mask & (1 << k)) tc_init(k); noInterrupts(); }
  else if (c == "IMU" && a1) { bool on = atoi(a1) != 0; interrupts(); bool ok = on ? imu_init() : true; noInterrupts();
                               imu_on = on && ok; if (on && !ok) { interrupts(); push_text("IMU: WHO_AM_I mismatch"); noInterrupts(); } }
  else if (c == "PAGE" && a1) { page_on = atoi(a1) != 0; if (a2) page_period_us = max(200L, atol(a2)); }
  else if (c == "CONFIG") { interrupts(); send_config(); noInterrupts(); }
  else if (c == "STATUS") { char s[120]; snprintf(s, sizeof(s), "status seq=%lu dropped=%lu running=%d dist=%d",
                            (unsigned long)sample_seq, (unsigned long)rb_dropped, running, dist_loop);
                            interrupts(); push_text(s); noInterrupts(); }
  else { interrupts(); push_text("unknown command"); noInterrupts(); }
  interrupts();
}

// ------------------------------------------------------------------------------------------ setup and loop
void setup() {
  Serial.begin(12000000);                                 // USB: the baud rate is ignored
  pinMode(PIN_ADC_CS, OUTPUT); digitalWriteFast(PIN_ADC_CS, HIGH);
  pinMode(PIN_ADC_SYNCRST, OUTPUT); digitalWriteFast(PIN_ADC_SYNCRST, HIGH);
  pinMode(PIN_ADC_DRDY, INPUT);
  for (int k = 0; k < 4; k++) { pinMode(PIN_TC_CS[k], OUTPUT); digitalWriteFast(PIN_TC_CS[k], HIGH); }
  pinMode(PIN_IMU_CS, OUTPUT); digitalWriteFast(PIN_IMU_CS, HIGH);
  pinMode(PIN_PAGE_CS, OUTPUT); digitalWriteFast(PIN_PAGE_CS, HIGH);
  pinMode(PIN_CAM, OUTPUT); pinMode(PIN_STROBE, OUTPUT); pinMode(PIN_SYNC_OUT, OUTPUT);
  digitalWriteFast(PIN_CAM, LOW); digitalWriteFast(PIN_STROBE, LOW); digitalWriteFast(PIN_SYNC_OUT, LOW);
  pinMode(PIN_DUT_IN, INPUT); pinMode(PIN_MARKER, INPUT_PULLUP);
  pinMode(PIN_IMU_INT1, INPUT); pinMode(PIN_PAGE_MOTION, INPUT);
  analogWriteResolution(12);
  analogWriteFrequency(PIN_PWM_A, 36621.09);              // 12-bit PWM at 600 MHz (PJRC table)
  analogWriteFrequency(PIN_PWM_B, 36621.09);
  analogWrite(PIN_PWM_A, 2048); analogWrite(PIN_PWM_B, 2048);   // 0 A

  enc1.setInitConfig(); enc1.init();
  enc2.setInitConfig(); enc2.init();
  enc3.setInitConfig(); enc3.init();
  enc4.setInitConfig(); enc4.init();

  SPI.begin();
  SPI1.begin();
  adc_reset();
  adc_configure();
  uint16_t clk = adc_rreg(0x03);

  SPI.usingInterrupt(digitalPinToInterrupt(PIN_ADC_DRDY));
  attachInterrupt(digitalPinToInterrupt(PIN_ADC_DRDY), drdy_isr, FALLING);
  attachInterrupt(digitalPinToInterrupt(PIN_DUT_IN), dut_isr, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_MARKER), marker_isr, FALLING);
  attachInterrupt(digitalPinToInterrupt(PIN_IMU_INT1), imu_isr, RISING);

  // self-test: CRC check value and the ADC's CLOCK register read back
  uint16_t crc = crc16_ccitt((const uint8_t *)"123456789", 9);
  char s[96];
  snprintf(s, sizeof(s), "boot %s crc_check=0x%04X (expect 0x29B1) adc_clock=0x%04X", FW_VERSION, crc, clk);
  push_text(s);
  send_config();
}

static char line[160];
static uint8_t line_n = 0;

void loop() {
  // drain the ring buffer to USB in chunks
  uint32_t h = rb_head, t = rb_tail;
  if (h != t) {
    uint32_t n = (h > t) ? (h - t) : (RB_SIZE - t);
    if (n > 2048) n = 2048;
    int avail = Serial.availableForWrite();
    if (avail > 0) {
      if ((uint32_t)avail < n) n = (uint32_t)avail;
      Serial.write(&rb[t], n);
      rb_tail = (t + n) & (RB_SIZE - 1);
    }
  }
  // host commands, one per line
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (line_n) { line[line_n] = 0; handle(line); line_n = 0; }
    } else if (line_n < sizeof(line) - 1) {
      line[line_n++] = ch;
    }
  }
  if (page_on && page_timer >= page_period_us) {
    page_timer -= page_period_us;
    page_poll();
  }
}
