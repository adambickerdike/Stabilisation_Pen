| quantity | tcn_s | tcn_m | ICD budget |
|---|---|---|---|
| MAC per inference (window, tree) | 16,688 | 31,296 | <= 35,000 |
| parameters | 5,942 | 10,966 |  |
| flash: int8 weights + int32 biases (x2) + structs | 7,376 B | 12,792 B | <= 32 kB |
| ARM -O2 object: code / rodata | 1,240 / 7,292 B | n/a |  |
| activation RAM (int8 window + ping-pong; + float window) | 640 B (1,152 B) | 832 B (1,344 B) | <= 8 kB |
| plain C: QEMU instructions per inference | 118,359 | ~221,966 (scaled) |  |
| plain C time @128 MHz (CPI 1.0 / 1.3 / 1.6) | 0.92 / 1.20 / 1.48 ms | ~2.25 ms (CPI 1.3) | <= 1 ms |
| CMSIS-NN time @128 MHz (0.5 / 0.15 MAC/cycle) | 0.28 / 0.89 ms | 0.51 / 1.65 ms | <= 1 ms |
| energy per inference @128 MHz (CMSIS central) | 6.5 uJ | 11.9 uJ |  |
| power at 250 Hz @128 MHz (CMSIS central) | 1.64 mW | 2.97 mW |  |
| streaming alternative: MAC per step / state RAM | 5,792 / 1,603 B | 10,760 / 2,075 B |  |
| naive dilated conv at all 64 positions | 319,280 MAC | 587,840 MAC |  |
