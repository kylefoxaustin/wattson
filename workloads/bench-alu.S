/* wattson compute-bound workload: register-only integer churn (near-zero memory
   traffic), then PSCI SYSTEM_OFF. Contrasts with bench-mem in the activity vector. */
    .equ ITERS, 0x20000000             /* 512M iterations */
    .equ PSCI_SYSTEM_OFF, 0x84000008
    .section .text.startup, "ax"
    .global _start
_start:
    ldr     x1, =ITERS
    mov     x2, #0
    ldr     x3, =2654435761
.Lloop:
    mul     x2, x2, x3
    add     x2, x2, #1
    eor     x2, x2, x3
    subs    x1, x1, #1
    b.ne    .Lloop
    ldr     x0, =PSCI_SYSTEM_OFF
    smc     #0
.Lhalt:
    wfi
    b       .Lhalt
