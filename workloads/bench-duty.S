/* wattson duty-cycle workload: alternates a bounded ALU burst with a genuinely
   HALTED interval (WFI woken by the ARM generic timer), then PSCI SYSTEM_OFF.

   WHY WFI AND NOT A SPIN LOOP. This workload exists to test the gate-activity
   bridge, AF_app = AF_idle + (AF_max - AF_idle) * U. That model is about a core
   that is genuinely idle for (1-U) of the time. A polling loop retires
   instructions the whole way through, so it would hold the core at full duty
   while merely LOOKING like a duty sweep in the source - and it would confirm
   the model at every U by construction. The core has to actually halt.

   DUTY is set at assembly time (percent, 1..100):
       as -defsym DUTY=50 ...
   Both phases are bounded in GENERIC TIMER TICKS, so the duty cycle is exact and
   platform-independent:  U = ACTIVE_TICKS / (ACTIVE_TICKS + IDLE_TICKS).  See the
   note on ACTIVE_TICKS for why an iteration-bounded active phase was wrong. */

    .ifndef DUTY
    .equ DUTY, 100
    .endif

    /* Overridable so a smoke test can run in seconds:
           as --defsym DUTY=50 --defsym WINDOWS_OV=4 --defsym BURST_OV=4096 */
    .ifndef WINDOWS_OV
    .equ WINDOWS,       256            /* work/idle windows per run */
    .else
    .equ WINDOWS,       WINDOWS_OV
    .endif
    .ifndef BURST_OV
    .equ CHUNK,         1024           /* ALU iterations between counter checks */
    .else
    .equ CHUNK,         BURST_OV
    .endif

    /* ⚠️ THE ACTIVE PHASE IS BOUNDED BY THE COUNTER, NOT BY AN ITERATION COUNT.
       Measured on FRDM-IMX95-PRO silicon: CNTFRQ = 24 MHz, and 1M iterations of
       this loop take 85,028 ticks (3.543 ms) on an A55.

       The first version ran a FIXED ITERATION COUNT for the active phase and a
       fixed TICK COUNT for idle. That makes U a function of EXECUTION SPEED:
       on silicon the nominal 25/50/75/100 came out as 0.221/0.460/0.718/1.000,
       and under TCG - where the same iterations take far longer in wall time
       while idle still costs 4.167 ms - U would sit near 1.0 for every variant.
       The SAME BINARY would then have a different duty cycle in QEMU than on
       silicon, which is fatal for a sweep whose whole purpose is to correlate
       QEMU-side activity against silicon-side power.

       Bounding BOTH phases in timer ticks makes U exact and identical
       everywhere: U = ACTIVE_TICKS / (ACTIVE_TICKS + IDLE_TICKS), by
       construction, at any execution speed. The instruction count per window
       then differs between QEMU and silicon - which is fine, because
       instructions are measured rather than assumed. */
    .equ ACTIVE_TICKS,  100000         /* 4.167 ms at the measured 24 MHz */

    .equ PSCI_SYSTEM_OFF, 0x84000008
    /* LPUART1 = the i.MX95 console (ttyLP0), confirmed on FRDM silicon:
       /soc/bus@44000000/serial@44380000. U-Boot has already configured baud,
       so a polled write to DATA is enough - no init, nothing to get wrong. */
    .equ LPUART1_BASE,  0x44380000
    .equ LPUART_STAT,   0x14
    .equ LPUART_DATA,   0x1c
    .equ LPUART_TDRE,   23             /* STAT.TDRE: transmit register empty */
    .equ GICD_BASE,     0x48000000     /* imx95 GICv3 distributor */
    /* GIC-600 per hw/arm/fsl-imx95.c: dist 0x48000000, ITS 0x48040000,
       REDIST 0x48060000. Using 0x48040000 here poked the ITS as if it were the
       redistributor and hung on a ChildrenAsleep bit that never clears - both
       duty variants retired 28 instructions and died on the timeout. */
    .equ GICR_BASE,     0x48060000     /* redistributor 0 */
    /* We run at EL2, so the timer that belongs to us is the HYPERVISOR timer
       CNTHP_*, whose PPI is 26. Arming the EL1 physical timer (CNTP_*, PPI 30)
       from EL2 armed a timer whose interrupt never arrived: DUTY=100 (no WFI)
       completed in 0.1s while DUTY=50 executed one window and then hung on a
       WFI nothing would wake. Halting forever and idling look identical from
       outside until you check whether the run ever ends. */
    .equ PPI_TIMER,     26             /* EL2 hypervisor timer PPI */

    .section .text.startup, "ax"
    .global _start

_start:
    mov     x28, x30                   /* keep LR across puts */
    adr     x9, msg_start              /* PC-relative: see the note at msg_start */
    bl      puts
    /* ---- minimal GICv3 bring-up: enough for the timer PPI to reach the core.
       WFI wakes on a pending physical interrupt even with PSTATE.I masked, but
       the GIC still has to DELIVER it - an unconfigured GIC means WFI never
       wakes and the run hangs instead of idling. */
    ldr     x0, =GICD_BASE
    mov     w1, #3                     /* EnableGrp0 | EnableGrp1NS (ARE set below) */
    ldr     w2, [x0]                   /* GICD_CTLR */
    orr     w2, w2, #(1 << 4)          /* ARE_NS */
    str     w2, [x0]
    orr     w2, w2, w1
    str     w2, [x0]

    /* redistributor: wake it (clear ProcessorSleep, wait for ChildrenAsleep=0) */
    ldr     x0, =GICR_BASE
    ldr     w1, [x0, #0x14]            /* GICR_WAKER */
    and     w1, w1, #~(1 << 1)         /* ProcessorSleep = 0 */
    str     w1, [x0, #0x14]
.Lwake:
    ldr     w1, [x0, #0x14]
    tbnz    w1, #2, .Lwake             /* ChildrenAsleep */

    /* SGI/PPI frame is redistributor + 0x10000: enable PPI 30, set priority */
    ldr     x0, =(GICR_BASE + 0x10000)   /* SGI/PPI frame */
    mov     w1, #1
    lsl     w1, w1, #PPI_TIMER
    /* PUT THE PPI IN GROUP 1 FIRST. GICR_IGROUPR0 resets to 0 = Group 0, and we
       only enable Group 1 on the CPU interface - so an enabled, pending,
       correctly-prioritised Group 0 interrupt is simply never delivered. The
       symptom is silent: no exception, no guest error, WFI sleeps forever, and
       an -d int trace shows NOTHING because there is nothing to show. */
    ldr     w2, [x0, #0x080]           /* GICR_IGROUPR0 */
    orr     w2, w2, w1
    str     w2, [x0, #0x080]
    str     w1, [x0, #0x100]           /* GICR_ISENABLER0 */
    mov     w1, #0x80
    strb    w1, [x0, #(0x400 + PPI_TIMER)]  /* GICR_IPRIORITYR */

    /* CPU interface. QEMU starts a -kernel image on this machine at EL2, so
       this is the EL2 system-register interface, not EL1.
       ⚠️ SYMBOLIC NAMES, NOT RAW S3_<op1>_... ENCODINGS. The first version of
       this file wrote S3_6_C12_C12_5 intending ICC_SRE_EL1; op1=6 is EL3, and
       the assembler encoded exactly what it was told. It faulted as an
       Undefined Instruction at EL2 and the workload hung retiring 28
       instructions. The disassembly said `mrs x0, icc_sre_el3` in plain text -
       the tool knew the answer the whole time. Names let the assembler check
       the intent; a raw encoding only records the arithmetic. */
    mrs     x0, icc_sre_el2
    orr     x0, x0, #1                 /* SRE: system-register interface */
    orr     x0, x0, #(1 << 3)          /* Enable: lower ELs may use SRE too */
    msr     icc_sre_el2, x0
    isb
    mov     x0, #0xff
    msr     icc_pmr_el1, x0            /* unmask all priorities */
    mov     x0, #1
    msr     icc_igrpen1_el1, x0        /* enable Group 1 */
    isb

    ldr     x19, =WINDOWS
    ldr     x23, =2654435761

.Lwindow:
    /* ---- ACTIVE phase: ALU work until ACTIVE_TICKS of counter have elapsed ---- */
    mrs     x24, cntvct_el0
    ldr     x25, =ACTIVE_TICKS
    add     x24, x24, x25              /* deadline */
    mov     x21, #0
.Lactive:
    ldr     x20, =CHUNK
.Lburst:
    mul     x21, x21, x23
    add     x21, x21, #1
    eor     x21, x21, x23
    subs    x20, x20, #1
    b.ne    .Lburst
    mrs     x25, cntvct_el0
    cmp     x25, x24
    b.lo    .Lactive

    /* ---- IDLE phase: halt for (100-DUTY)/DUTY of the burst's window ----
       At DUTY=100 there is no idle phase at all, so the binary is exactly a
       shorter bench-alu and the U=1.0 point needs no special case. */
    .if DUTY < 100
    ldr     x0, =((ACTIVE_TICKS * (100 - DUTY)) / DUTY)
    msr     cnthp_tval_el2, x0
    mov     x0, #1
    msr     cnthp_ctl_el2, x0          /* ENABLE, unmasked */
    isb
    wfi
    mov     x0, #0
    msr     cnthp_ctl_el2, x0          /* disarm before the next window */
    isb
    .endif

    subs    x19, x19, #1
    b.ne    .Lwindow

    adr     x9, msg_done
    bl      puts

    ldr     x0, =PSCI_SYSTEM_OFF
    smc     #0
.Lhalt:
    wfi
    b       .Lhalt

    /* ⚠️ puts LIVES IN .text, NOT .text.startup, SO IT CANNOT LAND FIRST.
       link.ld emits *(.text.startup) at 0x80000000 and QEMU begins executing a
       flat -kernel image at exactly that address - so whatever is FIRST in that
       section is the entry point, regardless of ENTRY(_start). Defining puts
       above _start inside .text.startup silently made puts the entry point: it
       ran with a garbage x9 and took a Data Abort with FAR 0x0 before a single
       instruction of the workload executed. ENTRY() binds the ELF entry, which
       a flat binary does not carry. */
    .section .text
/* puts: x9 -> NUL-terminated string. Clobbers x9,x10,w11,x12.
   WITHOUT THIS THE TEST CANNOT DISTINGUISH ITS TWO OUTCOMES: a workload that
   completed and a workload that hung on WFI both leave a silent console. */
puts:
    ldr     x12, =LPUART1_BASE
1:  ldrb    w10, [x9], #1
    cbz     w10, 3f
2:  ldr     w11, [x12, #LPUART_STAT]
    tbz     w11, #LPUART_TDRE, 2b
    str     w10, [x12, #LPUART_DATA]
    b       1b
3:  ret


    /* ⚠️ REFER TO THESE PC-RELATIVELY (adr), NEVER `ldr =sym`.
       link.ld links at 0x80000000, but QEMU loads a flat -kernel image at
       0x80080000 - confirmed by a fault whose ELR was 0x80080054 for an
       instruction at offset 0x54. So every ABSOLUTE symbol address baked into a
       literal pool is 0x80000 too low and points at zeroed memory. `ldr =msg_start`
       therefore handed puts a pointer to a NUL byte: it printed nothing, faulted
       nothing, and the workload ran to completion looking exactly like a silent
       success. adr is load-address independent and cannot drift this way. */
    .section .rodata
msg_start:
    .asciz  "\r\n>>> WATTSON-DUTY START <<<\r\n"
msg_done:
    .asciz  "\r\n>>> WATTSON-DUTY DONE <<<\r\n"
