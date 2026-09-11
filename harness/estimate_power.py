#!/usr/bin/env python3
"""Join an activity vector to a power model and emit an estimate.

This is the whole contract in one place: QEMU supplies activity, the power team
supplies energy per unit of it, and neither is asked to do the other's job. The
join is deliberately strict, because every failure this campaign hit was a
quiet mismatch rather than a loud one:

  * units are compared, not assumed. A coefficient fitted against DRAM READ
    traffic names a read key; feeding it read+write totals is an error. That
    exact confusion - ARM's l3d_cache_refill counts refills (reads), QEMU's
    dram_bytes_proxy counts transactions (reads and writes) - produced a
    published "QEMU over-reports bandwidth by 2x" claim that was a unit error.

  * extrapolation past a term's valid_range is reported, never silently done.

  * provenance rides along. A GATE_ESTIMATE coefficient and a MEASURED one may
    not be presented as the same kind of number.

Usage: estimate_power.py <activity.json> <power-model.json>
"""
import json
import sys


def dig(obj, dotted):
    """Fetch a dotted path from the activity vector, or None."""
    cur = obj
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def estimate(activity, model):
    act = activity.get('activity', {})
    rows, warnings, total = [], [], 0.0

    for name, block in model['blocks'].items():
        sub = block['static_mw']
        prov = block.get('provenance') or model['provenance']
        if model['provenance'] == 'MIXED' and not block.get('provenance'):
            warnings.append(f"{name}: model is MIXED but block declares no provenance")
        rows.append((name, 'static', '', sub, prov))
        total += sub

        for term in block['terms']:
            key = term['activity_key']
            val = dig(act, key)
            if val is None:
                warnings.append(f"{name}: activity vector has no '{key}' - term skipped, "
                                f"so this estimate is INCOMPLETE for {name}")
                continue
            if isinstance(val, dict):
                warnings.append(f"{name}: '{key}' is an object, not a quantity - term skipped")
                continue

            rng = term.get('valid_range')
            if rng and not (rng[0] <= val <= rng[1]):
                warnings.append(f"{name}: {key}={val:g} {term['unit']} is OUTSIDE the fitted "
                                f"range {rng[0]:g}-{rng[1]:g}; this is EXTRAPOLATION")
            mw = term['coeff_mw_per_unit'] * val
            rows.append((name, key, f"{val:g} {term['unit']}", mw, prov))
            total += mw

    return rows, warnings, total


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    activity = json.load(open(sys.argv[1]))
    model = json.load(open(sys.argv[2]))

    if model.get('schema') != 'wattson/power-model/v1':
        sys.exit(f"not a power model: {model.get('schema')}")

    rows, warnings, total = estimate(activity, model)

    print(f"workload : {activity.get('workload', '?')}")
    print(f"part     : {model['part']}  @ {model['conditions']['freq_mhz']:.0f} MHz")
    print(f"coeffs   : {model['provenance']}\n")
    print(f"{'block':<18}{'term':<38}{'activity':>16}{'mW':>9}")
    for name, key, val, mw, _ in rows:
        print(f"{name:<18}{key:<38}{val:>16}{mw:>9.1f}")
    print(f"{'':<18}{'':<38}{'TOTAL':>16}{total:>9.1f}")

    if warnings:
        print("\nWARNINGS - the estimate above is qualified by these:")
        for w in warnings:
            print(f"  ! {w}")

    prov = model['provenance']
    print(f"\nThis is a DERIVED estimate. Activity is DERIVED from QEMU; energy "
          f"coefficients are {prov}.")
    if prov == 'GATE_ESTIMATE':
        print("Coefficients are pre-silicon estimates and have NOT been validated "
              "against measured rails.")
    print("It may not be compared against a MEASURED power number as if it were one.")


if __name__ == '__main__':
    main()
