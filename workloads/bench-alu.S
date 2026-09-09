/* wattson compute-bound workload: register-only integer churn (near-zero memory
   traffic), then PSCI SYSTEM_OFF. Contrasts with bench-mem in the activity vector. */
    /* Overridable so a SILICON-sized build can exist alongside the QEMU one:
       as --defsym ITERS_OV=... . The QEMU default finishes in ~1.5 s on an A55,
       far too short for a BCU accumulation window. */
    .ifndef ITERS_OV
    .equ ITERS, 0x20000000             /* 512M iterations (QEMU size) */
    .else
    .equ ITERS, ITERS_OV
    .endif
    /* LPUART1 = the i.MX95 console. U-Boot has configured baud already, so a
       polled write to DATA is enough. Markers exist because a bare-metal
       workload that finished and one that hung both leave a silent console -
       and on silicon, under a power meter, we must know WHICH WINDOW was the
       workload. */
    .equ LPUART1_BASE,  0x44380000
    .equ LPUART_STAT,   0x14
    .equ LPUART_DATA,   0x1c
    .equ LPUART_TDRE,   23

    .equ PSCI_SYSTEM_OFF, 0x84000008
    .section .text.startup, "ax"
    .global _start
_start:
    adr     x9, m_start
    bl      puts
    ldr     x1, =ITERS
    mov     x2, #0
    ldr     x3, =2654435761
.Lloop:
    mul     x2, x2, x3
    add     x2, x2, #1
    eor     x2, x2, x3
    subs    x1, x1, #1
    b.ne    .Lloop
    adr     x9, m_done
    bl      puts
    ldr     x0, =PSCI_SYSTEM_OFF
    smc     #0
.Lhalt:
    wfi
    b       .Lhalt

    .section .text
puts:
    ldr     x12, =LPUART1_BASE
1:  ldrb    w10, [x9], #1
    cbz     w10, 3f
2:  ldr     w11, [x12, #LPUART_STAT]
    tbz     w11, #LPUART_TDRE, 2b
    str     w10, [x12, #LPUART_DATA]
    b       1b
3:  ret

    .section .rodata
m_start: .asciz "\r\n>>> BENCH-ALU START <<<\r\n"
m_done:  .asciz "\r\n>>> BENCH-ALU DONE <<<\r\n"
