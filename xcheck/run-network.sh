#!/bin/bash
set -u
SSH="ssh -n -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes root@10.0.1.221"
OUT=/tmp/netpw/res; mkdir -p $OUT
$SSH 'for c in /sys/devices/system/cpu/cpu*/cpufreq; do echo userspace > $c/scaling_governor 2>/dev/null; echo 1800000 > $c/scaling_setspeed 2>/dev/null; done' >/dev/null 2>&1
run () {
  TAG=$1; MODE=$2; RATE=$3
  timeout -k 5 40 bcu monitor -board=imx95evk19 -nodisplay -dump=$OUT/$TAG.csv >/dev/null 2>&1 &
  BP=$!; sleep 3
  if [ "$MODE" != "idle" ]; then
    $SSH "python3 /tmp/board_load.py 10.0.1.150 $MODE $RATE 28" > $OUT/$TAG.out 2>&1
  else
    sleep 28; echo "mode=idle target=0Mbps actual=0.0Mbps cpu_util=0.0%" > $OUT/$TAG.out
  fi
  wait $BP 2>/dev/null; sleep 2
  echo "$TAG: $(grep -h mode= $OUT/$TAG.out | tail -1)"
}
run net_idle   idle 0
run net_tx250  tx   250
run net_tx500  tx   500
run net_tx900  tx   900
run net_rx250  rx   250
run net_rx500  rx   500
run net_rx900  rx   900
$SSH 'for c in /sys/devices/system/cpu/cpu*/cpufreq; do echo ondemand > $c/scaling_governor 2>/dev/null; done' >/dev/null 2>&1
echo NETSWEEPDONE
