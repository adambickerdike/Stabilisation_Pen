# EML — Embedded ML stream: search log and critical synthesis

Stream: EML (embedded machine learning on the pen MCU). Ledger: `../ledger/EML_embedded_ml.csv` (rows EML-01 to EML-30).
All retrieval on 2026-09-26. Numbers marked **[calc]** are this stream's own calculations, not published values.

## 1. Search log

All entries dated 2026-09-26. "curl" means a direct HTTP fetch of the exact URL (raw GitHub files, arXiv PDFs, vendor pages); "WebFetch" means the page was fetched and queried. Outcomes note failures honestly.

| # | Tool | Exact query or URL | Outcome |
|---|---|---|---|
| 1 | WebSearch | `nRF5340 product specification application core 128 MHz SAADC PWM current consumption` | Found PS v1.1–v1.5 mirrors and Nordic product page |
| 2 | WebSearch | `CMSIS-NN release notes latest version 2026` | Pointed to CMSIS-NN releases, ExecuTorch PR updating to v8.0.0 |
| 3 | WebFetch | https://github.com/ARM-software/CMSIS-NN/releases | Release list (years in summary inconsistent; Keil page used for dates) |
| 4 | WebFetch | https://github.com/pytorch/executorch/pull/22719 | ExecuTorch PR "Update CMSIS-NN to v8.0.0", merged 14 Sep 2026 |
| 5 | curl | https://api.github.com/repos/ARM-software/CMSIS-NN/releases?per_page=10 | Blocked (GitHub API not enabled for session) |
| 6 | GitHub MCP list_releases | ARM-software/CMSIS-NN | Denied (repository not configured for session; not added) |
| 7 | curl | https://raw.githubusercontent.com/ARM-software/CMSIS-NN/main/README.md | OK (operator table, licence, ISA paths) |
| 8 | curl | https://raw.githubusercontent.com/ARM-software/CMSIS-NN/main/ARM.CMSIS-NN.pdsc | OK (no release list on main) |
| 9 | WebFetch | https://www.keil.arm.com/packs/cmsis-nn-arm/versions/ | 8.0.0 = 21 Aug 2026; 7.0.0 = 27 Nov 2024; 6.0.0 = 3 Jun 2024 |
| 10 | WebFetch | https://arm-software.github.io/CMSIS-NN/latest/index.html | No version string or benchmarks on page |
| 11 | WebFetch (x2) | https://github.com/ARM-software/CMSIS-NN/releases/tag/v8.0.0 | Notes of v8.0.0; date shown as "21 Aug" |
| 12 | curl | https://raw.githubusercontent.com/ARM-software/CMSIS-NN/main/Include/arm_nnfunctions.h | OK (V.19.1.0, 27 Mar 2026) |
| 13 | curl | https://raw.githubusercontent.com/ARM-software/CMSIS-NN/main/Source/ConvolutionFunctions/arm_convolve_wrapper_s8.c | OK |
| 14 | curl | https://raw.githubusercontent.com/ARM-software/CMSIS-NN/main/Include/arm_nnsupportfunctions.h ; .../Source/ConvolutionFunctions/arm_convolve_s8.c | OK |
| 15 | curl | https://raw.githubusercontent.com/tensorflow/tflite-micro/main/README.md ; .../LICENSE | OK (Apache-2.0) |
| 16 | WebFetch | https://developers.google.com/edge/litert/microcontrollers/get_started | OK (last updated 2026-05-28) |
| 17 | WebFetch | https://ai.google.dev/edge/litert/models/quantization_spec | 301 redirect |
| 18 | WebFetch | https://developers.google.com/edge/litert/models/quantization_spec | OK |
| 19 | curl | https://raw.githubusercontent.com/tensorflow/tflite-micro/main/tensorflow/lite/micro/micro_mutable_op_resolver.h | OK |
| 20 | curl | https://raw.githubusercontent.com/tensorflow/tflite-micro/main/tensorflow/lite/micro/kernels/cmsis_nn/conv.cc | OK |
| 21 | curl | https://raw.githubusercontent.com/tensorflow/tflite-micro/main/tensorflow/lite/micro/docs/memory_management.md | OK |
| 22 | curl | .../tensorflow/lite/micro/kernels/var_handle.cc ; read_variable.cc ; assign_variable.cc ; call_once.cc ; .../micro/micro_resource_variable.h | OK |
| 23 | curl | https://www.tme.eu/Document/3e794294564952202d03e12371eb0e0e/NRF5340-CLAA-R7-DTE.pdf | 403 (Cloudflare) |
| 24 | WebSearch | `nRF5340_PS pdf docs-be.nordicsemi.com product specification` | Pointed to Nordic infocenter/docs |
| 25 | WebFetch | https://docs.nordicsemi.com/bundle/ps_nrf5340/page/keyfeatures_html5.html | 301 to /r/bundle/ |
| 26 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/keyfeatures_html5.html | OK |
| 27 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/about.html | No version on page |
| 28 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/chapters/rev_history/rev_history.html | v1.6, Feb 2025 (latest) |
| 29 | WebSearch | `nRF5340 product specification "CPU running" CoreMark 128 MHz current consumption application core` | Product-brief CoreMark snippets (not used as primary) |
| 30 | curl | https://www.nordicsemi.com/-/media/Software-and-other-downloads/Product-Briefs/nRF5340-SoC-PB.pdf | 403 (Cloudflare) |
| 31 | WebFetch (x2) | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/chapters/current_consumption/doc/current_consumption.html | OK (all current tables) |
| 32 | WebFetch (x2) | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/saadc.html | Features OK; electrical table not rendered |
| 33 | WebSearch | `nRF5340 SAADC electrical specification "tCONV" "fSAMPLE" 200 kHz ENOB` | No tCONV/ENOB values found |
| 34 | WebFetch (x3) | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/pwm.html | Counter/modes/DPPI OK; PRESCALER enumeration not rendered |
| 35 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/spim.html | OK |
| 36 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/qspi.html | OK |
| 37 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/dppi.html | OK |
| 38 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/cache.html | OK |
| 39 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf5340/page/cpu.html | 404 |
| 40 | WebSearch | `docs.nordicsemi.com ps_nrf5340 application core CPU "Cortex-M33" "CoreMark" FPU DSP network core 64 MHz` | Zephyr/TF-M pages |
| 41 | WebFetch | https://docs.zephyrproject.org/latest/boards/nordic/nrf5340dk/doc/index.html | OK |
| 42 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf54L15/page/keyfeatures_html5.html | 301 |
| 43 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf54l15/page/keyfeatures_html5.html | Table of contents only |
| 44 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf54h20/page/keyfeatures_html5.html | 404 |
| 45 | WebSearch | `nRF54L15 datasheet key features 128 MHz Cortex-M33 1.5 MB RRAM 256 KB RAM 14-bit ADC` | Datasheet mirrors (v0.7, v0.8, v1.0 listings) |
| 46 | WebSearch | `nRF54H20 datasheet key features 320 MHz application core MRAM RAM ADC` | Product page, Zephyr doc |
| 47 | curl | https://www.mouser.com/datasheet/3/926/1/nRF54L15_nRF54L10_nRF54L05_Datasheet_v1.0.pdf | Returned JavaScript, not PDF |
| 48 | curl | https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6469/NRF54L15-CAAA-R7.pdf | OK: Preliminary Datasheet v0.7 (Oct 2024) |
| 49 | WebFetch | https://www.mouser.com/datasheet/3/926/1/nRF54L15_nRF54L10_nRF54L05_Datasheet_v1.0.pdf | 503 |
| 50 | WebFetch | https://www.nordicsemi.com/Products/nRF54L15 | OK |
| 51 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf54l15/page/chapters/rev_history/rev_history.html | 404 |
| 52 | WebSearch | `"nRF54L15" datasheet revision history v1.0 2025 docs.nordicsemi.com ps_nrf54l15` | Page found but JS-rendered |
| 53 | WebFetch (x2) | https://docs.nordicsemi.com/r/bundle/ps_nrf54l15/page/rev_history.html (with and without `?contentId=GEN_5LgrpM8CQwUXtDi8IA`) | Content not rendered |
| 54 | WebFetch | https://docs.nordicsemi.com/r/bundle/ps_nrf54l15/page/saadc.html | Content not rendered |
| 55 | WebFetch | https://www.nordicsemi.com/Products/nRF54H20 | OK |
| 56 | WebFetch | https://docs.zephyrproject.org/latest/boards/nordic/nrf54h20dk/doc/index.html | OK |
| 57 | WebFetch | https://www.st.com/en/microcontrollers-microprocessors/stm32u5a5zj.html | 503 |
| 58 | WebSearch | `STM32U5A5 datasheet DS14xxx DCMI PSSI 160 MHz 4 Mbytes flash 2.5 Mbytes SRAM 14-bit ADC 2.5 Msps µA/MHz` | ST datasheet URLs |
| 59 | curl (x2) | https://www.st.com/resource/en/datasheet/stm32u5a5aj.pdf | HTTP/2 stream error; empty reply |
| 60 | WebFetch | https://www.st.com/resource/en/datasheet/stm32u5a5aj.pdf | 503 |
| 61 | WebSearch | `STM32U5A5ZJ datasheet pdf "STM32U5Axxx" DS13977 revision` | No accessible mirror |
| 62 | WebSearch | `MLPerf Tiny v1.3 results Cortex-M33 keyword spotting latency energy µJ` | MLCommons v1.3/v1.4 pages |
| 63 | WebFetch | https://mlcommons.org/benchmarks/inference-tiny/ | Links to v1.4 results sheet |
| 64 | WebFetch | https://mlcommons.org/2026/07/mlperf-tiny-v1-4-results/ | Published 7 Jul 2026 |
| 65 | curl | https://docs.google.com/spreadsheets/d/18Wwe_AIKSjjbfThMqkji5hRoG6T4BfXd/export?format=xlsx | OK (full v1.4 results; parsed locally) |
| 66 | WebFetch | https://mlcommons.org/2025/09/mlperf-tiny-v1-3-tech/ | Streaming wake-word benchmark description |
| 67 | WebFetch | https://arxiv.org/abs/2106.07597 | Citation only |
| 68 | curl | https://arxiv.org/pdf/2106.07597 | OK (v4) |
| 69 | curl | https://raw.githubusercontent.com/mlcommons/tiny/master/benchmark/training/keyword_spotting/keras_model.py ; .../kws_util.py ; .../anomaly_detection/keras_model.py | OK |
| 70 | WebSearch | `Burrello temporal convolutional network PPG heart rate STM32WB55 Cortex-M4 latency energy parameters MACs` | Q-PPG and TimePPG papers |
| 71 | WebSearch | `1D CNN inference time Cortex-M4 STM32L4 human activity recognition MACs latency ms CMSIS-NN quantized int8` | Secondary HAR results (not used) |
| 72 | curl | https://arxiv.org/pdf/2203.14907 ; https://arxiv.org/pdf/2203.04396 | OK |
| 73 | curl | https://arxiv.org/pdf/2010.08678 | OK |
| 74 | WebSearch | `CMSIS-NN Cortex-M33 benchmark cycles per MAC convolution int8 DSP extension performance measurement` | No Arm-published M33 cycles/MAC |
| 75 | curl | https://arxiv.org/pdf/1801.06601 | OK |
| 76 | curl | https://arxiv.org/pdf/1908.11263 | OK (M4/M7 values only in charts; not used) |
| 77 | WebSearch | `nRF5340 TensorFlow Lite Micro inference time ms keyword spotting benchmark Cortex-M33 128 MHz CMSIS-NN` | No nRF5340 measurement found |
| 78 | WebFetch | https://blog.tensorflow.org/2021/02/accelerated-inference-on-arm-microcontrollers-with-tensorflow-lite.html | Numbers only in images |
| 79 | curl | https://raw.githubusercontent.com/emlearn/emlearn/master/README.md ; .../LICENSE.md | OK (MIT) |
| 80 | curl | https://raw.githubusercontent.com/kraiskil/onnx2c/master/README.md ; .../LICENSE.txt | OK |
| 81 | curl | https://raw.githubusercontent.com/pytorch/executorch/main/README.md ; .../LICENSE | OK (BSD) |
| 82 | WebFetch | https://github.com/pytorch/executorch/releases/latest | v1.5.1 ("23 Sep") |
| 83 | WebFetch | https://docs.pytorch.org/executorch/main/backends/arm-cortex-m/arm-cortex-m-overview.html | OK |
| 84 | WebSearch | `ST Edge AI Core 4.0 release notes STM32 licence SLA0048 X-CUBE-AI dilation Conv1D support` | NOT EXECUTED: shared session search budget exhausted |
| 85 | WebSearch | `microTVM deprecated removed Apache TVM release notes` | NOT EXECUTED: shared session search budget exhausted |
| 86 | WebFetch (x2) | https://docs.zephyrproject.org/latest/boards/st/nucleo_u5a5zj_q/doc/index.html | OK (secondary ST feature list) |
| 87 | WebFetch | https://docs.zephyrproject.org/latest/boards/st/nucleo_wba55cg/doc/nucleo_wba55cg.html | OK |
| 88 | WebFetch | https://www.st.com/en/microcontrollers-microprocessors/stm32u5a5zj.html | 503 (second attempt) |
| 89 | WebFetch | https://developer.arm.com/Processors/Cortex-M33 | Redirect only |
| 90 | WebFetch | https://www.arm.com/products/silicon-ip-cpu/cortex-m/cortex-m33 | No power/area figures on page |
| 91 | WebFetch | https://docs.edgeimpulse.com/docs/edge-impulse-studio/deployment/eon-compiler | OK |
| 92 | curl | https://raw.githubusercontent.com/edgeimpulse/inferencing-sdk-cpp/master/LICENSE ; .../README.md | OK (BSD 3-Clause Clear) |
| 93 | curl | https://raw.githubusercontent.com/google-ai-edge/LiteRT/main/README.md | OK |
| 94 | curl | https://raw.githubusercontent.com/apache/tvm/{v0.16.0,v0.17.0,v0.18.0,v0.19.0,v0.20.0,v0.21.0,v0.22.0,main}/python/tvm/micro/__init__.py ; .../apps/microtvm/README.md ; .../src/runtime/crt/common/crt_runtime_api.c ; .../python/tvm/micro/project.py ; https://raw.githubusercontent.com/apache/tvm/main/README.md ; .../LICENSE | microTVM present to v0.18.0, absent from v0.19.0 |
| 95 | WebFetch | https://github.com/apache/tvm/releases/tag/v0.19.0 | PR #17554 "Phase out microTVM" |
| 96 | WebFetch | https://github.com/tensorflow/tflite-micro | OK (Apache-2.0, not archived) |
| 97 | curl | https://raw.githubusercontent.com/tensorflow/tensorflow/master/tensorflow/compiler/mlir/lite/transforms/dilated_conv.h | OK |
| 98 | WebFetch | https://www.tensorflow.org/api_docs/python/tf/nn/conv1d | Navigation only |
| 99 | curl | https://raw.githubusercontent.com/tensorflow/tensorflow/master/tensorflow/python/ops/nn_ops.py | OK (conv1d docstring) |
| 100 | WebFetch | https://stedgeai-dc.st.com/assets/embedded-docs/index.html | Truncated |
| 101 | curl | https://stedgeai-dc.st.com/assets/embedded-docs/{release_notes.html, supported_ops_tflite.html, supported_ops_keras.html, stm32_release_notes.html} | supported_ops_tflite OK (v4.0.0); release notes JS-only |
| 102 | WebFetch | https://docs.zephyrproject.org/latest/boards/st/nucleo_wba65ri/doc/index.html | OK |
| 103 | WebFetch | https://www.nordicsemi.com/Products/nRF5340 | OK (8 KB 2-way cache) |
| 104 | curl | https://raw.githubusercontent.com/tensorflow/tflite-micro/main/tensorflow/lite/micro/benchmarks/README.md ; .../docs/arm.md ; .../kernels/cmsis_nn/README.md ; .../tools/make/ext_libs/cmsis_nn_download.sh | OK |
| 105 | WebFetch | https://docs.nordicsemi.com/r/bundle/ncs-latest/page/nrf/app_dev/device_guides/nrf53/features_nrf53.html | 404 |
| 106 | curl | https://raw.githubusercontent.com/nrfconnect/sdk-nrf/main/doc/nrf/app_dev/device_guides/nrf53/features_nrf53.rst | OK |
| 107 | WebFetch | https://developers.google.com/edge/litert/microcontrollers/overview | OK |
| 108 | curl | https://raw.githubusercontent.com/zephyrproject-rtos/zephyr/main/soc/nordic/nrf53/Kconfig | OK |
| 109 | curl | https://raw.githubusercontent.com/ARM-software/CMSIS-NN/main/Source/ConvolutionFunctions/arm_depthwise_conv_wrapper_s8.c ; .../arm_depthwise_conv_s8.c | OK |
| 110 | curl (x2) | https://www.st.com/resource/en/datasheet/stm32u5a5zj.pdf | HTTP/2 stream error |

## 2. Critical synthesis

**MCU recommendation.** The nRF5340 is a defensible research baseline but not a comfortable one. Its application core is a Cortex-M33 with DSP and FPU at 64/128 MHz, 1 MB flash, 512 kB RAM and an 8 kB two-way cache (EML-01, EML-05). The BLE controller belongs on the 64 MHz network core, which Zephyr configures without FPU or DSP, so the NN, both control loops, the BLE host and logging all share the application core (EML-06). At 128 MHz the idle floor rises from 1.3 µA to 785 µA (EML-02). My judgement: keep the nRF5340 for the first research pen, with the NN held to about 35k MAC per step. Run the current loop on it only if hardware-timed sampling (below) meets the skew and jitter budget on the bench. If it does not, move current control to a motor-control MCU with the nRF as radio/NN co-processor. The best verified candidate is the STM32U5A5: 160 MHz M33, two 14-bit 2.5 Msps ADCs, two advanced motor-control timers and DCMI/PSSI (EML-09). That evidence is secondary, because st.com was unavailable.

For the next revision:
- Evaluate the nRF54L15: about 56 vs 183 pJ/cycle [calc], and a 10-bit 2 Msps or 12-bit 250 ksps ADC. Its data are preliminary (v0.7, EML-07).
- Evaluate the nRF54H20: 320 MHz application core, separate 256 MHz radio core and 1 MB RAM. Its peripheral timing has not been verified (EML-08).
- The STM32WBA65 is a single-chip BLE option with a motor-control timer, but it runs at only 100 MHz and has no camera interface (EML-10).

**Verified nRF5340 constraints for synchronous current and position sampling.**
- **SAADC (EML-01, EML-03).** One multiplexed SAR converter: 12-bit, up to 200 ksps and 8 channels. 14-bit is only reachable with oversampling, which must not be combined with scan mode. TACQ is 3–40 µs, and fSAMPLE < 1/(TACQ+tconv). [calc] Scanned channels are at least 5 µs apart. Three currents at 20 kHz use 60 ksps, but they are not sampled simultaneously.
- **PWM (EML-04).** 16 MHz clock, 15-bit counter, up or up/down counting, 4 instances × 4 channels, compare values fed by EasyDMA. [calc] At 20 kHz this gives 800 counts (9.6 bit) edge-aligned or 400 counts (8.6 bit) centre-aligned.
- **Synchronisation (EML-04).** PWM publishes PWMPERIODEND to DPPI (32 channels, 6 groups), SAADC SAMPLE can subscribe, and TIMERs run at 16 MHz. A PWMPERIODEND→TIMER→SAADC chain should therefore sample at fixed offsets without the CPU. This is an inference: no DPPI latency figure was retrieved.
- **Links (EML-05).** SPIM4 runs up to 32 Mbps on dedicated pins and the other SPIMs up to 8 Mbps. QSPI runs at 6–96 MHz with XIP.
- **Not verified.** SAADC tconv, INL and ENOB; the PWM prescaler table; dead-time support.

**TCN inference time [calc, EML-30].** Assumed structure: 5 residual blocks with dilations 1–16, 48 channels, kernel 3, 16 inputs and 3 outputs, run in streaming mode (one new sample per inference at 250 Hz). The efficiency assumptions come from the evidence:
- 0.5 MAC/cycle as the central case: MLPerf KWS and AD on Cortex-M33 and M4 derive to 0.46–0.57 (EML-23).
- 0.15 as the pessimistic case: a small int8 TCN on an M4 (EML-24).
- 1.0 as the optimistic case: only reached with an accelerator (EML-21).

| Variant | 128 MHz (0.15 / 0.5 / 1.0 MAC/cycle) | 64 MHz (0.15 / 0.5 / 1.0) |
|---|---|---|
| 2 conv/block: 65.4k MAC, 66k params, 0.5 s receptive field | 3.41 / 1.02 / 0.51 ms | 6.81 / 2.04 / 1.02 ms |
| 1 conv/block: 30.9k MAC, 31k params, 0.25 s receptive field | 1.61 / 0.48 / 0.24 ms | 3.22 / 0.96 / 0.48 ms |

Against the 4 ms period, the 2-conv variant uses 26% of the core at 128 MHz in the central case and is infeasible at 64 MHz in the pessimistic case. Recomputing the whole window instead of streaming would need about 8.2 M MAC per inference, so stateful streaming is mandatory. At the CoreMark-derived 183 pJ/cycle, energy is 3–20 mW at 250 Hz, which is small next to BLE TX (4.1 mA at 3 V). CPU time and jitter, not energy, bind. For the generic 1–10 M MAC/s envelope at 128 MHz: 0.8–16% load and 0.2–3.7 mW at 0.5–1.0 MAC/cycle, rising to 52% and 12 mW at 0.15 (EML-23).

**Toolchain recommendation.** Use LiteRT for Microcontrollers (repository tensorflow/tflite-micro, Apache-2.0) with CMSIS-NN kernels (Apache-2.0, v8.0.0). Pin both by commit hash (EML-11, EML-14, EML-17).
- **Quantisation (EML-15, EML-11).** int8 per-channel symmetric weights with zero-point 0, asymmetric int8 activations and int32 bias. 16×8 (int16 activations) is available on the DSP path if prediction resolution is short.
- **Dilation (EML-12, EML-16).** TFLM passes the dilation factors of CONV_2D to CMSIS-NN. Dilated layers then use the generic im2col kernel, because the 1×N fast path requires dilation = 1.
- **Conversion (EML-18).** Keras Conv1D lowers to CONV_2D, and the converter fuses SpaceToBatch/BatchToSpace emulations back into true dilation. Inspect the graph after conversion.
- **Streaming state (EML-16, EML-19).** Either VAR_HANDLE/READ_VARIABLE/ASSIGN_VARIABLE inside the model, or my preference for control firmware: application ring buffers calling CMSIS-NN directly. The direct route removes the few-percent interpreter overhead and keeps the TFLM model as a bit-exact reference.
- **Rejected or watched (EML-24 to EML-29):**
  - ST Edge AI 4.0 rejects int8 dilation, and zero-interleaving the filters costs 2.7–2.9× the MACs.
  - ExecuTorch's Cortex-M backend is beta, with symmetric int8 only and no int16.
  - Edge Impulse EON depends on a hosted service and plan-gated features.
  - microTVM was removed upstream at TVM v0.19.0.
  - emlearn has no convolution layers.
  - onnx2c is float-oriented.

**Must be benchmarked on nRF5340 hardware (FVP timing is invalid, EML-17).**
1. Cycles per layer (DWT) for d = 1 vs d > 1, int8 vs 16×8, at 64 and 128 MHz, with weights in flash (cache hit/miss counters) vs RAM.
2. End-to-end latency and worst-case jitter of the 250 Hz inference, with the 10–20 kHz current ISR, the 1–2 kHz position loop, the BLE host and QSPI logging all active.
3. Latency and jitter of the PWM→DPPI→TIMER→SAADC trigger, skew between channels, and SAADC noise and ENOB at the chosen TACQ.
4. Supply current per inference; the 128 MHz idle penalty compared with switching down to 64 MHz between inferences.
5. Numerical equivalence of streaming and offline inference, and quantisation error of the disturbance predictions.
6. Arena size (RecordingMicroInterpreter) and flash footprint.

**Open gaps.**
- No Arm-published cycles/MAC for Cortex-M33.
- No TFLM with CMSIS-NN measurement on the nRF5340 itself.
- nRF5340 SAADC electrical table not retrieved.
- STM32 data are secondary, and the ST Edge AI licence was not retrieved.
- nRF54L15 v1.0 datasheet not retrieved.
- The definition of OPs in Q-PPG is ambiguous (EML-25).
