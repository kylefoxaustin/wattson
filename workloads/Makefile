# Bounded bare-metal workloads for wattson activity extraction.
# Each ends in PSCI SYSTEM_OFF so QEMU exits cleanly and the TCG plugins flush.
CROSS   ?= aarch64-linux-gnu-
AS      := $(CROSS)as
LD      := $(CROSS)ld
OBJCOPY := $(CROSS)objcopy
ASFLAGS := -mcpu=cortex-a55

WORKLOADS := bench-alu bench-mem
BINS := $(addsuffix .bin,$(WORKLOADS))

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
