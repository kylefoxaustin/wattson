#!/bin/bash
# Multi-application power measurement, corrected window.
#
# The previous harness bounded only the LAUNCH of new iterations at t=20 s and
# let the in-flight iteration finish, while `perf stat` wrapped the whole run.
# Applications with long iterations (pacman, sgm) overran by 4-13 s, so the
# activity counters covered a two-phase run (all apps, then a pacman+sgm tail)
# while the divisor assumed a flat 20 s. Rates were inflated 1.22-1.66x.
#
# Here every application runs continuously from t=3 s to t=37 s and the 20 s
# perf window sits INSIDE that span, so counters and power describe one
# homogeneous phase. Alignment precision stops mattering once the phase is
# homogeneous, which is the property the old harness lacked.
set -u
SSH="ssh -n -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes root@10.0.1.221"
OUT=${OUT:-/tmp/multi3}; mkdir -p $OUT
APPDUR=34; WARMUP=5; WINDOW=20; CAP=40

$SSH 'for c in /sys/devices/system/cpu/cpu*/cpufreq; do echo userspace > $c/scaling_governor 2>/dev/null; echo 1800000 > $c/scaling_setspeed 2>/dev/null; done' >/dev/null 2>&1

run () {
  TAG=$1; shift
  NAPP=$#
  S="cd /tmp/xcheck50; rm -f /tmp/it.*; E=\$(( \$(date +%s) + $APPDUR ));"
  i=0
  for c in "$@"; do
    S="$S ( n=0; while [ \$(date +%s) -lt \$E ]; do taskset -c $i $c >/dev/null 2>&1; n=\$((n+1)); done; echo \$n > /tmp/it.$i ) & "
    i=$((i+1))
  done
  S="$S sleep 1; echo STARTED"
  B64=$(printf '%s' "$S" | base64 -w0)

  timeout -k 5 $CAP bcu monitor -board=imx95evk19 -nodisplay -dump=$OUT/$TAG.csv >/dev/null 2>&1 &
  BP=$!
  sleep 3
  $SSH "echo $B64 | base64 -d > /tmp/mw3.sh; setsid sh /tmp/mw3.sh >/dev/null 2>&1 < /dev/null &" >/dev/null 2>&1
  sleep $WARMUP
  $SSH "perf stat -a -e inst_retired,cpu_cycles,l3d_cache_refill -x, -- sleep $WINDOW" > $OUT/$TAG.perf 2>&1
  $SSH "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq" > $OUT/$TAG.freq 2>&1
  wait $BP 2>/dev/null
  sleep 6
  $SSH "cat /tmp/it.* 2>/dev/null | tr '\n' ' '" > $OUT/$TAG.iters 2>&1
  echo "$TAG napps=$NAPP iters=$(cat $OUT/$TAG.iters) freq=$(cat $OUT/$TAG.freq)"
}

PAC="./apps/app-pacman 6 60"
SGM="./apps/app-sgma55 ./apps/syn_left.pgm ./apps/syn_right.pgm -t 1 -n 1"
SQL="./apps/app-sqlite 40000"
NET="./apps/app-httpp 2000"
QOI="./apps/app-qoi 12"
RAY="./apps/app-render ray 25"
SHA="./apps/app-sha256 ./apps/data.bin 32"
MEM="./microbench mem 128 4"
LZ4="./apps/app-lz4 -9 -f ./apps/data.bin /dev/null"
LUA="./apps/app-lua ./apps/work.lua"
BZ2="./apps/app-bzip2 -9 -c -k ./apps/data.bin"

run e2_ai_vis "$PAC" "$SGM"
run e4_edge   "$PAC" "$SGM" "$SQL" "$NET"
run e6_edge   "$PAC" "$SGM" "$SQL" "$NET" "$QOI" "$RAY"
run n4_sha    "$SHA" "$SHA" "$SHA" "$SHA"
run n6_mix    "$SHA" "$MEM" "$LZ4" "$SQL" "$LUA" "$BZ2"

$SSH 'for c in /sys/devices/system/cpu/cpu*/cpufreq; do echo ondemand > $c/scaling_governor 2>/dev/null; done' >/dev/null 2>&1
echo MULTI3DONE
