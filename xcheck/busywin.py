"""Busy-window power extraction from NXP BCU per-rail captures.

Replaces an earlier midpoint-threshold estimator that was wrong in two ways:
a mask-fraction guard silently fell back to the median of the WHOLE capture
(workload + ~14 s of idle, biased low), and when the guard passed, the
midpoint threshold landed inside the plateau and selected only its upper half
(biased high). 69 of 100 published rail values took the first path.

The window is derived per capture rather than hardcoded, because workload
duration varies (alu ~23 s, pacman ~29 s, some multicore mixes ~33 s).

Method: bin the TOTAL rail power to 1 s medians (robust to the ~1090 mW
spikes present on an otherwise ~590 mW plateau), threshold at
floor + 0.35*(p90 - floor), take the LONGEST contiguous above-threshold run,
then drop one bin at each edge so partial ramp bins never enter the median.
Per-rail busy power is the median of raw samples inside that window.

Returning the window itself (not just a scalar) is deliberate: activity
counters must be divided by the SAME window the power was measured over, or
the comparison is between two different experiments.
"""
import csv, statistics as st

CAPTURE_S = 34.0

def rails(path):
    rows = list(csv.reader(open(path)))
    hdr = [h.strip() for h in rows[0]]
    idx = {}
    for i, h in enumerate(hdr):
        for rail in ('vdd_arm', 'vdd_soc'):
            if h.startswith(rail + ' ') and h.endswith('voltage(V)'):
                idx[rail + 'v'] = i
            if h.startswith(rail + ' ') and h.endswith('current(mA)'):
                idx[rail + 'c'] = i
    out = {'vdd_arm': [], 'vdd_soc': []}
    for r in rows[1:]:
        if len(r) != len(hdr):
            continue
        try:
            for rail in ('vdd_arm', 'vdd_soc'):
                out[rail].append(float(r[idx[rail + 'v']]) * float(r[idx[rail + 'c']]))
        except (ValueError, KeyError, IndexError):
            continue
    return out

def window(path, frac=0.35):
    """Return (t0, t1, hz, nbins_busy) for the workload plateau, in seconds."""
    R = rails(path)
    tot = [a + s for a, s in zip(R['vdd_arm'], R['vdd_soc'])]
    n = len(tot)
    hz = n / CAPTURE_S
    nb = int(CAPTURE_S)
    bins = [st.median(tot[int(i*hz):int((i+1)*hz)]) for i in range(nb)
            if int((i+1)*hz) <= n]
    srt = sorted(bins)
    floor = srt[max(0, int(0.10 * len(srt)))]
    p90 = srt[min(len(srt)-1, int(0.90 * len(srt)))]
    thr = floor + frac * (p90 - floor)
    best = cur = None
    for i, b in enumerate(bins):
        if b > thr:
            cur = i if cur is None else cur
        else:
            if cur is not None and (best is None or i - cur > best[1] - best[0]):
                best = (cur, i)
            cur = None
    if cur is not None and (best is None or len(bins) - cur > best[1] - best[0]):
        best = (cur, len(bins))
    if best is None:
        raise ValueError(f'{path}: no busy plateau found')
    t0, t1 = best[0] + 1, best[1] - 1          # drop one ramp bin each edge
    if t1 - t0 < 3:
        t0, t1 = best                           # too short to trim
    return float(t0), float(t1), hz, best[1] - best[0]

def busy_power(path):
    """Return dict of per-rail busy power in mW, plus the window used."""
    t0, t1, hz, _ = window(path)
    R = rails(path)
    out = {'t0': t0, 't1': t1, 'T': t1 - t0}
    for rail, s in R.items():
        seg = s[int(t0*hz):int(t1*hz)]
        out[rail] = st.median(seg)
    out['sum'] = out['vdd_arm'] + out['vdd_soc']
    return out

if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        b = busy_power(p)
        print(f"{p}  win [{b['t0']:.0f},{b['t1']:.0f}]s T={b['T']:.0f}s  "
              f"arm {b['vdd_arm']:.1f}  soc {b['vdd_soc']:.1f}  sum {b['sum']:.1f}")
