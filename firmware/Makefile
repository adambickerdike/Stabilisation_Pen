# Stabilisation pen firmware baseline (research prototype Rev A)
#
#   make params    regenerate include/params_gen.h from config/parameters.yaml
#   make vectors   regenerate golden vectors (numba simulator, scipy, frames.py)
#   make test      host unit tests (ASan + UBSan) -> results/firmware/test_report.txt
#   make arm       nRF5340 application-core build + results/firmware/size_report.txt
#   make qemu      unit tests on qemu-system-arm -M mps2-an505 (Cortex-M33, semihosting)
#                  -> results/firmware/qemu_report.txt
#   make all       test + arm + qemu
# Use at most `make -j2` on shared machines.

FW      := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
ROOT    := $(abspath $(FW)/..)
RESULTS := $(ROOT)/results/firmware
BUILD   := $(FW)/build
PY      ?= python3

export PYTHONDONTWRITEBYTECODE := 1
export NUMBA_CACHE_DIR := $(BUILD)/numba_cache

CORE_SRC  := $(sort $(wildcard $(FW)/core/*.c))
TEST_SRC  := $(sort $(wildcard $(FW)/tests/*.c))
HOSTP_SRC := $(FW)/port/host/hal_host.c
NRF_SRC   := $(sort $(wildcard $(FW)/port/nrf5340/*.c))
QEMU_SRC  := $(sort $(wildcard $(FW)/port/qemu_an505/*.c))

WARN := -Wall -Wextra -Werror -Wdouble-promotion -Wconversion -Wsign-conversion -Wshadow \
        -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wcast-align -Wformat=2 -Wvla
INC_CORE := -I$(FW)/include
INC_TEST := $(INC_CORE) -I$(FW)/port/host -I$(FW)/tests

# ------------------------------------------------------------------ host
HOST_CC     ?= gcc
HOST_CFLAGS := -std=c11 -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined \
               -fno-sanitize-recover=all $(WARN)
HOST_BIN    := $(BUILD)/host/pen_tests
HOST_OBJ    := $(patsubst $(FW)/%.c,$(BUILD)/host/%.o,$(CORE_SRC) $(TEST_SRC) $(HOSTP_SRC))

# test sources use double precision for references: -Wno-double-promotion there only
TEST_EXTRA = $(if $(findstring /tests/,$<),-Wno-double-promotion,)

$(BUILD)/host/%.o: $(FW)/%.c $(wildcard $(FW)/include/*.h) $(wildcard $(FW)/tests/*.h) $(FW)/port/host/hal_host.h
	@mkdir -p $(dir $@)
	$(HOST_CC) $(HOST_CFLAGS) $(TEST_EXTRA) $(INC_TEST) -c $< -o $@

$(HOST_BIN): $(HOST_OBJ)
	$(HOST_CC) $(HOST_CFLAGS) $^ -lm -o $@

.PHONY: test
test: $(HOST_BIN)
	@mkdir -p $(RESULTS)
	@cd $(FW) && $(PY) tools/check_inputs.py > $(BUILD)/input_check.txt 2>&1; ic=$$?; \
	 ( echo "# Host unit tests - firmware/tests (gcc $$($(HOST_CC) -dumpfullversion), -fsanitize=address,undefined)"; \
	   echo "# Evidence status: HOST TEST (x86-64, float32 code paths); not hardware, not target timing."; \
	   echo "# params: $$(grep -m1 PEN_PARAMS_YAML_VERSION include/params_gen.h | cut -d'"' -f2) yaml sha $$(grep -m1 PEN_PARAMS_YAML_SHA16 include/params_gen.h | cut -d'"' -f2)"; \
	   cat $(BUILD)/input_check.txt; \
	   $(HOST_BIN) tests/vectors ) > $(RESULTS)/test_report.txt 2>&1; rc=$$?; \
	 cat $(RESULTS)/test_report.txt; if [ $$ic -ne 0 ]; then echo "generated inputs are STALE"; exit 1; fi; exit $$rc

# ------------------------------------------------------------------ ARM (nRF5340 application core)
ARM_CC   := arm-none-eabi-gcc
ARM_SIZE := arm-none-eabi-size
ARM_CPU  := -mcpu=cortex-m33 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=hard
ARM_CFLAGS := -std=c11 -O2 -g $(ARM_CPU) -ffunction-sections -fdata-sections -fno-common -fno-math-errno $(WARN)
ARM_OBJ  := $(patsubst $(FW)/%.c,$(BUILD)/arm/%.o,$(CORE_SRC) $(NRF_SRC))
ARM_ELF  := $(BUILD)/arm/pen_fw_nrf5340.elf
ARM_LD   := $(FW)/port/nrf5340/nrf5340_app.ld

$(BUILD)/arm/%.o: $(FW)/%.c $(wildcard $(FW)/include/*.h) $(wildcard $(FW)/port/nrf5340/*.h)
	@mkdir -p $(dir $@)
	$(ARM_CC) $(ARM_CFLAGS) $(INC_CORE) -I$(FW)/port/nrf5340 -c $< -o $@

$(ARM_ELF): $(ARM_OBJ) $(ARM_LD)
	$(ARM_CC) $(ARM_CPU) -T$(ARM_LD) -nostartfiles --specs=nano.specs --specs=nosys.specs \
	  -Wl,--gc-sections -Wl,-Map=$(BUILD)/arm/pen_fw_nrf5340.map -Wl,--print-memory-usage \
	  $(ARM_OBJ) -lm -o $@

.PHONY: arm
arm: $(ARM_ELF)
	@mkdir -p $(RESULTS)
	$(PY) $(FW)/tools/size_report.py --elf $(ARM_ELF) --map $(BUILD)/arm/pen_fw_nrf5340.map \
	  --size $(ARM_SIZE) --out $(RESULTS)/size_report.txt
	@cat $(RESULTS)/size_report.txt

# ------------------------------------------------------------------ QEMU (mps2-an505, Cortex-M33)
QEMU      := qemu-system-arm
QEMU_OBJ  := $(patsubst $(FW)/%.c,$(BUILD)/qemu/%.o,$(CORE_SRC) $(TEST_SRC) $(HOSTP_SRC) $(QEMU_SRC))
QEMU_ELF  := $(BUILD)/qemu/pen_tests_an505.elf
QEMU_LD   := $(FW)/port/qemu_an505/an505.ld
QEMU_CFLAGS := -std=c11 -O2 -g $(ARM_CPU) -ffunction-sections -fdata-sections -fno-common -fno-math-errno $(WARN) -DPEN_TARGET_QEMU=1

$(BUILD)/qemu/%.o: $(FW)/%.c $(wildcard $(FW)/include/*.h) $(wildcard $(FW)/tests/*.h)
	@mkdir -p $(dir $@)
	$(ARM_CC) $(QEMU_CFLAGS) $(TEST_EXTRA) $(INC_TEST) -c $< -o $@

$(QEMU_ELF): $(QEMU_OBJ) $(QEMU_LD)
	$(ARM_CC) $(ARM_CPU) -T$(QEMU_LD) -nostartfiles --specs=rdimon.specs -Wl,--gc-sections \
	  -Wl,-Map=$(BUILD)/qemu/pen_tests_an505.map $(QEMU_OBJ) -lm -lc -lrdimon -o $@

.PHONY: qemu
qemu: $(QEMU_ELF)
	@mkdir -p $(RESULTS)
	cd $(FW) && $(PY) tools/run_qemu.py --qemu $(QEMU) --elf $(QEMU_ELF) --out $(RESULTS)/qemu_report.txt

# ------------------------------------------------------------------ generators
.PHONY: params vectors
params:
	$(PY) $(FW)/tools/gen_params.py

vectors: $(HOST_BIN)
	$(PY) $(FW)/tools/gen_vectors.py
	cd $(FW) && $(HOST_BIN) --golden-log tests/vectors/golden_log_v1.bin
	$(PY) $(FW)/tools/pen_log.py decode $(FW)/tests/vectors/golden_log_v1.bin --json $(FW)/tests/vectors/golden_log_v1.json

.PHONY: all clean
all: test arm qemu

clean:
	rm -rf $(BUILD)
