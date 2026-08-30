# wattson activity-factor profile: i.MX95 A55 path
# Cache geometry MEASURED from the target's sysfs; correction factors MEASURED
# by xcheck against the imx9_ddr0 DDR controller (2026-08-30, see
# xcheck/RESULTS.md). Factors are DERIVED bridges: activity x factor -> best
# estimate of silicon DRAM transactions.
GEOM="dcachesize=32768,dassoc=4,dblksize=64,icachesize=32768,iassoc=4,iblksize=64,l2cachesize=65536,l2assoc=4,l2blksize=64,l3=on,l3cachesize=524288,l3assoc=16,l3blksize=64,wstream=on"
LINE_BYTES=64
RD_CORRECTION=1.23   # 1/0.81, band x/1.26 (pre-X4; regenerate after X4 lands)
WR_CORRECTION=1.11   # 1/0.90, band x/1.09
