#!/usr/bin/env sh
# System-wide DDR-controller beats around one app run, with an idle baseline of
# equal duration for subtraction. MEASURED, but system-wide: contains everything
# the SoC did in the window, minus what an idle window contains.
# Usage: run-ddr.sh <label> -- <cmd...>
set -eu
LABEL="$1"; shift; [ "$1" = "--" ] && shift
EV="imx9_ddr0/eddrtq_pm_rd_beat_filt2/,imx9_ddr0/eddrtq_pm_wr_beat_filt/"
T0=$(date +%s.%N)
O1=$(perf stat -a -x, -e "$EV" -- taskset -c 0 "$@" 2>&1 >/dev/null)
T1=$(date +%s.%N)
DUR=$(echo "$T1 $T0" | awk '{printf "%.3f", $1-$2}')
O2=$(perf stat -a -x, -e "$EV" -- sleep "$DUR" 2>&1)
rd1=$(echo "$O1" | awk -F, '/rd_beat/{print $1}'); wr1=$(echo "$O1" | awk -F, '/wr_beat/{print $1}')
rd0=$(echo "$O2" | awk -F, '/rd_beat/{print $1}'); wr0=$(echo "$O2" | awk -F, '/wr_beat/{print $1}')
echo "{\"schema\":\"wattson/xcheck-ddr/v1\",\"workload\":\"$LABEL\",\"dur_s\":$DUR,"
echo " \"rd_beats_run\":$rd1,\"wr_beats_run\":$wr1,\"rd_beats_idle\":$rd0,\"wr_beats_idle\":$wr0,"
echo " \"rd_beats_net\":$((rd1-rd0)),\"wr_beats_net\":$((wr1-wr0))}"
