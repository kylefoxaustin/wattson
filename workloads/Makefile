# Bounded bare-metal workloads for wattson activity extraction.
# Each ends in PSCI SYSTEM_OFF so QEMU exits cleanly and the TCG plugins flush.
CROSS   ?= aarch64-linux-gnu-
AS      := $(CROSS)as
LD      := $(CROSS)ld
OBJCOPY := $(CROSS)objcopy
ASFLAGS := -mcpu=cortex-a55

WORKLOADS := bench-alu bench-mem
BINS := $(addsuffix .bin,$(WORKLOADS))

# bench-duty is ONE source built at four duty cycles. The active burst is
# identical in all four, so every variant retires the same instructions and only
# the HALTED time changes - which is what makes U the only moving variable when
# the P4 bridge is fitted.
DUTIES := 25 50 75 100
DUTY_BINS := $(addprefix bench-duty,$(addsuffix .bin,$(DUTIES)))
BINS += $(DUTY_BINS)

bench-duty%.o: bench-duty.S
	$(AS) $(ASFLAGS) --defsym DUTY=$* -o $@ $<

.PHONY: all clean
all: $(BINS)

%.o: %.S
	$(AS) $(ASFLAGS) -o $@ $<
%.elf: %.o link.ld
	$(LD) -T link.ld -o $@ $<
%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f *.o *.elf
