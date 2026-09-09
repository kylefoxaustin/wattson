/* WFI wake diagnostic for real i.MX 95 silicon.
 *
 * bench-duty50 hangs on hardware and completes in QEMU; bench-duty100 (same GIC
 * bring-up, no WFI) completes on both. So the GIC init is not the hang and the
 * question is narrower: does a pending EL2 timer interrupt wake WFI on silicon?
 *
 * This prints EVERY answer it can get BEFORE doing anything that can hang, in
 * this order:
 *   1. the GIC/timer registers READ BACK after we write them - a value that does
 *      not stick is the single most likely cause (ATF owning PPI 26 as a Secure
 *      Group 0 interrupt would make our non-secure IGROUPR0 write vanish)
 *   2. a BOUNDED poll of CNTHP_CTL_EL2.ISTATUS - this splits the problem in
 *      half: ISTATUS set means the timer runs and only the WAKE is broken;
 *      never set means the timer itself is not running at EL2 here
 *   3. only then WFI, which may hang - by which point everything is printed
 */
    .equ PSCI_SYSTEM_OFF, 0x84000008
    .equ LPUART1_BASE,  0x44380000
    .equ LPUART_STAT,   0x14
    .equ LPUART_DATA,   0x1c
    .equ LPUART_TDRE,   23
    .equ GICD_BASE,     0x48000000
    .equ GICR_BASE,     0x48060000
    .equ GICR_SGI,      (GICR_BASE + 0x10000)
    .equ PPI_TIMER,     26
    .equ ARM_TICKS,     240000         /* 10 ms at the measured 24 MHz */
    .equ POLL_LIMIT,    0x4000000      /* bounded: must never spin forever */

    .section .text.startup, "ax"
    .global _start
_start:
    adr     x9, m_start
    bl      puts

    /* ---- GIC bring-up: identical to bench-duty ---- */
    ldr     x0, =GICD_BASE
    ldr     w2, [x0]
    orr     w2, w2, #(1 << 4)
    str     w2, [x0]
    orr     w2, w2, #3
    str     w2, [x0]

    ldr     x0, =GICR_BASE
    ldr     w1, [x0, #0x14]
    and     w1, w1, #~(1 << 1)
    str     w1, [x0, #0x14]
1:  ldr     w1, [x0, #0x14]
    tbnz    w1, #2, 1b

    ldr     x0, =GICR_SGI
    mov     w1, #1
    lsl     w1, w1, #PPI_TIMER
    ldr     w2, [x0, #0x080]
    orr     w2, w2, w1
    str     w2, [x0, #0x080]           /* IGROUPR0: PPI -> Group 1 */
    str     w1, [x0, #0x100]           /* ISENABLER0 */
    mov     w1, #0x80
    strb    w1, [x0, #(0x400 + PPI_TIMER)]

    mrs     x0, icc_sre_el2
    orr     x0, x0, #1
    orr     x0, x0, #(1 << 3)
    msr     icc_sre_el2, x0
    isb
    mov     x0, #0xff
    msr     icc_pmr_el1, x0
    mov     x0, #1
    msr     icc_igrpen1_el1, x0
    isb

    /* ---- 1. READ BACK, do not assume the writes stuck ---- */
    adr     x9, m_igrp
    bl      puts
    ldr     x0, =GICR_SGI
    ldr     w0, [x0, #0x080]
    bl      puthex
    adr     x9, m_isen
    bl      puts
    ldr     x0, =GICR_SGI
    ldr     w0, [x0, #0x100]
    bl      puthex
    adr     x9, m_grpen
    bl      puts
    mrs     x0, icc_igrpen1_el1
    bl      puthex
    adr     x9, m_sre
    bl      puts
    mrs     x0, icc_sre_el2
    bl      puthex
    adr     x9, m_freq
    bl      puts
    mrs     x0, cntfrq_el0
    bl      puthex

    /* ---- 2. BOUNDED ISTATUS POLL: does the timer fire at all? ---- */
    ldr     x0, =ARM_TICKS
    msr     cnthp_tval_el2, x0
    mov     x0, #1
    msr     cnthp_ctl_el2, x0
    isb
    ldr     x19, =POLL_LIMIT
2:  mrs     x0, cnthp_ctl_el2
    tbnz    x0, #2, 3f                 /* ISTATUS */
    subs    x19, x19, #1
    b.ne    2b
    adr     x9, m_noistat
    bl      puts
    b       4f
3:  adr     x9, m_istat
    bl      puts
4:  adr     x9, m_ctl
    bl      puts
    mrs     x0, cnthp_ctl_el2
    bl      puthex

    /* ---- 3. THE WFI ITSELF. Everything above is already printed. ---- */
    adr     x9, m_wfi
    bl      puts
    mov     x0, #0
    msr     cnthp_ctl_el2, x0          /* disarm, then re-arm cleanly */
    isb
    ldr     x0, =ARM_TICKS
    msr     cnthp_tval_el2, x0
    mov     x0, #1
    msr     cnthp_ctl_el2, x0
    isb
    wfi
    adr     x9, m_woke
    bl      puts

    adr     x9, m_done
    bl      puts
    ldr     x0, =PSCI_SYSTEM_OFF
    smc     #0
5:  wfi
    b       5b

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

/* puthex: x0 -> 16 hex digits + CRLF. Clobbers x0,x9-x14. */
puthex:
    mov     x14, x30
    ldr     x12, =LPUART1_BASE
    mov     x13, #60
1:  lsr     x10, x0, x13
    and     x10, x10, #0xf
    cmp     x10, #9
    b.hi    2f
    add     x10, x10, #'0'
    b       3f
2:  add     x10, x10, #('a' - 10)
3:  ldr     w11, [x12, #LPUART_STAT]
    tbz     w11, #LPUART_TDRE, 3b
    str     w10, [x12, #LPUART_DATA]
    subs    x13, x13, #4
    b.pl    1b
    mov     x30, x14
    adr     x9, m_crlf
    b       puts

    .section .rodata
m_start:   .asciz "\r\n>>> WFI-DIAG START <<<\r\n"
m_igrp:    .asciz "IGROUPR0   = "
m_isen:    .asciz "ISENABLER0 = "
m_grpen:   .asciz "IGRPEN1_EL1= "
m_sre:     .asciz "ICC_SRE_EL2= "
m_freq:    .asciz "CNTFRQ_EL0 = "
m_istat:   .asciz "ISTATUS    = SET (timer fires; only the WAKE is suspect)\r\n"
m_noistat: .asciz "ISTATUS    = NEVER SET (the timer itself is not running)\r\n"
m_ctl:     .asciz "CNTHP_CTL  = "
m_wfi:     .asciz "now executing WFI (a hang here means WFI never wakes)\r\n"
m_woke:    .asciz ">>> WFI WOKE <<<\r\n"
m_done:    .asciz ">>> WFI-DIAG DONE <<<\r\n"
m_crlf:    .asciz "\r\n"
