#!/usr/bin/env python3
"""
xcheck comparison: does QEMU's activity track real-silicon PMU counters?

Takes a QEMU activity vector (from run-qemu.sh) and a HW activity record (from
run-perf.sh on the board) for the SAME workload+args, and reports correction
factors:

    insn_ratio = QEMU total_insns        / HW instructions
    dram_ratio = QEMU dram_transactions  / HW dram_transactions   <-- the key one

The DRAM ratio is what validates wattson's load-bearing assumption (cache-miss
count as a DRAM-transaction proxy). A stable ratio across workloads means QEMU's
functional cache model tracks the real hierarchy up to a constant we can correct
for; a wildly workload-dependent ratio means the proxy needs work before P1.

Usage: compare.py <qemu.json> <hw.json>
"""
import sys, json


def load(p):
    return json.load(open(p))


def ratio(q, h):
    if not h:
        return None
    return round(q / h, 4)


def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    q = load(sys.argv[1]); h = load(sys.argv[2])
    qa = q["activity"]; ha = h["activity"]

    q_insns = qa["cores"]["total_insns"]
    q_dram = qa.get("memory", {}).get("dram_transactions_est")
    h_insns = ha.get("instructions")
    h_dram = ha.get("dram_transactions")

    print(f"workload: {q['workload']}  vs  {h['workload']}")
    print(f"  QEMU provenance: {q['provenance']}")
    print(f"  HW   provenance: {h['provenance']}")
    print()
    print(f"  {'metric':<22}{'QEMU':>16}{'HW (silicon)':>16}{'QEMU/HW':>10}")
    print(f"  {'-'*22}{'-'*16:>16}{'-'*16:>16}{'-'*10:>10}")
    print(f"  {'instructions':<22}{q_insns!s:>16}{h_insns!s:>16}{ratio(q_insns,h_insns)!s:>10}")
    print(f"  {'dram_transactions':<22}{q_dram!s:>16}{h_dram!s:>16}{ratio(q_dram,h_dram)!s:>10}")
    print()
    print("  Note: instruction ratio should sit near 1.0 (both count retired insns;")
    print("  small OS/loader deltas aside). The DRAM ratio is the calibration target")
    print("  for the cache-miss proxy — track it across workloads for stability.")
    print("  Provenance (Law 1): QEMU=DERIVED, HW=MEASURED — the ratio is the labelled")
    print("  bridge, never presented as a measured silicon activity factor.")


if __name__ == "__main__":
    main()
