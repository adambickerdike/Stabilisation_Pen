/*
 * startup_an505.c - bare-metal start-up for the unit tests on QEMU
 * `-M mps2-an505` (Cortex-M33 + SSE-200, secure state). TEST
 * INFRASTRUCTURE, not firmware: output goes through Arm semihosting (newlib
 * rdimon), and the golden vectors are read from QEMU's working directory
 * with semihosting file I/O.
 *
 * Command line (SYS_GET_CMDLINE, i.e. `-semihosting-config ...,arg=...`):
 *   pen_tests [vector_dir] [filter]    the unit tests (tests/test_main.c)
 *   pen_tests --bench                  instruction-count estimate (bench_an505.c)
 * A fault exception prints the stacked PC and the fault status registers and
 * ends QEMU with a run-time-error exit (non-zero status).
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "bench_an505.h"

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
extern void initialise_monitor_handles(void);
int main(int argc, char **argv);

void Reset_Handler(void);
void Fault_Handler(void);
void fault_report(const uint32_t *frame, uint32_t exc_return);
/* -nostartfiles drops crti/crtn: newlib's __libc_fini_array (pulled in by
 * exit()) still references _fini; there are no constructors/destructors */
void _init(void);
void _fini(void);
void _init(void) {}
void _fini(void) {}

typedef void (*vector_t)(void);

__attribute__((section(".isr_vector"), used)) const vector_t g_vectors[16] = {
    (vector_t)(uintptr_t)&_estack,
    Reset_Handler,
    Fault_Handler,   /* NMI */
    Fault_Handler,   /* HardFault */
    Fault_Handler,   /* MemManage */
    Fault_Handler,   /* BusFault */
    Fault_Handler,   /* UsageFault */
    Fault_Handler,   /* SecureFault */
    0,
    0,
    0,
    Fault_Handler,   /* SVC */
    Fault_Handler,   /* DebugMon */
    0,
    Fault_Handler,   /* PendSV */
    Fault_Handler,   /* SysTick (the bench polls it, no interrupt) */
};

#define SCB_CPACR (*(volatile uint32_t *)0xE000ED88u)
#define SCB_CFSR (*(volatile uint32_t *)0xE000ED28u)
#define SCB_HFSR (*(volatile uint32_t *)0xE000ED2Cu)
#define SCB_BFAR (*(volatile uint32_t *)0xE000ED38u)
#define SCB_ICSR (*(volatile uint32_t *)0xE000ED04u)

#define SH_SYS_WRITE0 0x04u
#define SH_SYS_GET_CMDLINE 0x15u
#define SH_SYS_EXIT 0x18u
#define ADP_STOPPED_RUNTIME_ERROR 0x20023u

static uint32_t sh_call(uint32_t op, const void *arg)
{
    register uint32_t r0 __asm__("r0") = op;
    register const void *r1 __asm__("r1") = arg;
    __asm__ volatile("bkpt 0xAB" : "+r"(r0) : "r"(r1) : "memory");
    return r0;
}

static void put_hex(char *dst, uint32_t v)
{
    static const char hex[] = "0123456789abcdef";
    for (int k = 7; k >= 0; k--) {
        dst[7 - k] = hex[(v >> (4 * k)) & 0xFu];
    }
}

void fault_report(const uint32_t *frame, uint32_t exc_return)
{
    static char msg[] = "\nFATAL: exception xxxxxxxx pc xxxxxxxx lr xxxxxxxx cfsr xxxxxxxx hfsr xxxxxxxx "
                        "bfar xxxxxxxx excret xxxxxxxx\n";
    put_hex(&msg[18], SCB_ICSR & 0x1FFu);
    put_hex(&msg[30], frame[6]);
    put_hex(&msg[42], frame[5]);
    put_hex(&msg[56], SCB_CFSR);
    put_hex(&msg[70], SCB_HFSR);
    put_hex(&msg[84], SCB_BFAR);
    put_hex(&msg[100], exc_return);
    (void)sh_call(SH_SYS_WRITE0, msg);
    for (;;) {
        (void)sh_call(SH_SYS_EXIT, (const void *)(uintptr_t)ADP_STOPPED_RUNTIME_ERROR);
    }
}

__attribute__((naked)) void Fault_Handler(void)
{
    __asm__ volatile(
        "tst lr, #4\n"
        "ite eq\n"
        "mrseq r0, msp\n"
        "mrsne r0, psp\n"
        "mov r1, lr\n"
        "b fault_report\n");
}

#define MAX_ARGS 8
static char s_cmdline[256];
static char *s_argv[MAX_ARGS + 1];

static int parse_cmdline(void)
{
    struct {
        char *buf;
        uint32_t len;
    } blk = {s_cmdline, sizeof(s_cmdline) - 1u};
    int argc = 0;
    if (sh_call(SH_SYS_GET_CMDLINE, &blk) == 0u && blk.len < sizeof(s_cmdline)) {
        s_cmdline[blk.len] = '\0';
        char *p = s_cmdline;
        while (*p != '\0' && argc < MAX_ARGS) {
            while (*p == ' ') {
                *p++ = '\0';
            }
            if (*p == '\0') {
                break;
            }
            s_argv[argc++] = p;
            while (*p != '\0' && *p != ' ') {
                p++;
            }
        }
    }
    if (argc == 0) {
        static char name[] = "pen_tests";
        s_argv[argc++] = name;
    }
    s_argv[argc] = NULL;
    return argc;
}

void Reset_Handler(void)
{
    /* FPU (CP10, CP11 full access) before any compiled code may use it */
    SCB_CPACR |= (0xFu << 20);
    __asm__ volatile("dsb\n isb" ::: "memory");
    const uint32_t *src = &_sidata;
    for (uint32_t *dst = &_sdata; dst < &_edata;) {
        *dst++ = *src++;
    }
    for (uint32_t *dst = &_sbss; dst < &_ebss;) {
        *dst++ = 0u;
    }
    initialise_monitor_handles();
    const int argc = parse_cmdline();
    int rc;
    if (argc >= 2 && strcmp(s_argv[1], "--bench") == 0) {
        rc = pen_bench_run();
    } else {
        rc = main(argc, s_argv);
    }
    exit(rc);
}
