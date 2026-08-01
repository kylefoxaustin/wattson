/* wattson memory-bound workload: stream a 256 MiB region, then PSCI SYSTEM_OFF
   so QEMU exits cleanly and TCG plugins flush their counts. */
    .equ REGION_START, 0x80200000
    .equ REGION_SIZE,  0x10000000      /* 256 MiB */
    .equ PASSES,       4
    .equ PSCI_SYSTEM_OFF, 0x84000008
    .section .text.startup, "ax"
    .global _start
_start:
    ldr     x20, =REGION_START
    ldr     x21, =REGION_SIZE
    add     x21, x20, x21
    mov     x22, #PASSES
.Louter:
    mov     x0, x20
    mov     x5, x22            /* pattern = pass index */
.Lwr:
    str     x5, [x0], #8
    cmp     x0, x21
    b.lo    .Lwr
    mov     x0, x20
    mov     x6, #0
.Lrd:
    ldr     x7, [x0], #8
    add     x6, x6, x7
    cmp     x0, x21
    b.lo    .Lrd
    subs    x22, x22, #1
    b.ne    .Louter
    ldr     x0, =PSCI_SYSTEM_OFF
    smc     #0
.Lhalt:
    wfi
    b       .Lhalt
