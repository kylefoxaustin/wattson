#!/usr/bin/env python3
"""
Parse QEMU TCG-plugin output into a wattson *activity vector*.

Consumes the stderr log from a `-d plugin` QEMU run that loaded libinsn +
libcache, and emits a JSON activity vector: per-core instruction counts and
the cache-derived memory activity (data accesses, misses = DRAM transactions,
instruction fetches). This is the ACTIVITY half only -- no energy, no watts.
Energy-per-event coefficients are supplied by the power team's model
(see docs/methodology.md, "the division of labour").

Provenance (Law 1): every field here is DERIVED from a functional emulator.
It is NOT a measured silicon activity factor. Keep the tag.
"""
import sys, re, json, argparse

# cache line size the libcache plugin models by default (bytes/line). Used to
# turn miss counts into an estimated DRAM byte volume. Override with --line.
DEFAULT_LINE_BYTES = 64


def parse(log_text, line_bytes):
    per_cpu = {}
    total_insns = None
    cache = None

    for line in log_text.splitlines():
        m = re.match(r"cpu (\d+) insns:\s+(\d+)", line)
        if m:
            per_cpu[int(m.group(1))] = int(m.group(2))
            continue
        m = re.match(r"total insns:\s+(\d+)", line)
        if m:
            total_insns = int(m.group(1))
            continue
        # libcache "sum" row:
        #   sum  <daccess> <dmiss> <dmiss%>  <iaccess> <imiss> <imiss%>
        m = re.match(r"sum\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s+(\d+)\s+([\d.]+)%", line)
        if m:
            cache = {
                "data_accesses": int(m.group(1)),
                "data_misses": int(m.group(2)),
                "dmiss_rate": float(m.group(3)) / 100.0,
                "insn_accesses": int(m.group(4)),
                "insn_misses": int(m.group(5)),
                "imiss_rate": float(m.group(6)) / 100.0,
            }

    active = {str(c): n for c, n in sorted(per_cpu.items()) if n > 0}
    vector = {
        "cores": {
            "count_seen": len(per_cpu),
            "count_active": len(active),
            "insns_by_cpu": active,          # only the cores that did work
            "total_insns": total_insns,
        },
    }
    if cache is not None:
        dram_txn = cache["data_misses"] + cache["insn_misses"]
        vector["memory"] = {
            **cache,
            # cache misses are the DRAM-transaction proxy; x line size = bytes.
            "dram_transactions_est": dram_txn,
            "dram_bytes_est": dram_txn * line_bytes,
            "line_bytes": line_bytes,
        }
    return vector


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile", help="captured QEMU -d plugin stderr log")
    ap.add_argument("--workload", required=True, help="workload name/label")
    ap.add_argument("--line", type=int, default=DEFAULT_LINE_BYTES,
                    help="cache line bytes (libcache default 64)")
    ap.add_argument("--note", default="", help="free-text provenance note")
    args = ap.parse_args()

    with open(args.logfile) as f:
        v = parse(f.read(), args.line)

    out = {
        "schema": "wattson/activity-vector/v1",
        "workload": args.workload,
        "provenance": "DERIVED (QEMU TCG functional counters; NOT measured silicon)",
        "note": args.note,
        "activity": v,
    }
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
