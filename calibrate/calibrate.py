#!/usr/bin/env python3
"""
wattson P1 calibration (STUB until an instrumented board provides ground truth).

Fits energy-per-event coefficients so that, per power domain,

    predicted_power ≈ Σ ( coeff_e × activity_e )

matches the MEASURED per-rail silicon power for a suite of workloads, then reports
the held-out prediction error. This is the bridge that turns DERIVED activity into
a power estimate — and its coefficients are what the power team owns for a new chip
(never reuse i.MX95 coefficients for Zebra; see docs/methodology.md).

Inputs (P1, once the board + BCU are available):
  --activity  dir of wattson activity-vector JSON files (one per workload)
  --power     CSV: workload,<rail1>_mW,<rail2>_mW,...   (BCU per-rail averages)

Until then this documents the intended model and refuses to fabricate numbers.
"""
import argparse, sys, glob, json, os

# activity features -> the rail/domain each is expected to predict (see
# calibrate/power-measurement.md for the i.MX95 rail names).
FEATURE_TO_DOMAIN = {
    "cores.total_insns":            "vdd_arm",     # + vdd_soc (logic)
    "memory.dram_transactions_est": "lpd5",        # LPDDR5 group (lpd5_vdd1/2/vddq)
}


def load_activity(d):
    out = {}
    for f in glob.glob(os.path.join(d, "*.json")):
        j = json.load(open(f))
        out[j["workload"]] = j["activity"]
    return out


def feature(activity, dotted):
    node = activity
    for k in dotted.split("."):
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    return node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--activity", help="dir of activity-vector JSON files")
    ap.add_argument("--power", help="CSV of measured per-rail power (mW) per workload")
    args = ap.parse_args()

    if not (args.activity and args.power and os.path.exists(args.power)):
        print(__doc__)
        print("\n[calibrate] No measured-power CSV yet — P1 is blocked on an")
        print("            instrumented i.MX95 board (PAC1934 + BCU).")
        print("            See calibrate/power-measurement.md. Refusing to")
        print("            fabricate coefficients (Law 1).")
        sys.exit(0)

    # --- P1 implementation goes here once ground truth exists ---
    # 1. load activity vectors + measured per-rail power
    # 2. build the design matrix X (activity features) and y (measured mW per domain)
    # 3. non-negative least squares per domain -> energy-per-event coefficients
    # 4. leave-one-workload-out cross-validation -> error band
    # 5. emit coefficients + R^2 + %error, all tagged DERIVED-from-a-MEASURED-fit
    raise SystemExit("[calibrate] ground-truth path not implemented until P1 data lands")


if __name__ == "__main__":
    main()
