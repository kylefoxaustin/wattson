#!/usr/bin/env bash
# Run a bare-metal image on the REAL FRDM-IMX95-PRO and capture its console.
#
#   ./run-on-frdm.sh <image.bin> [seconds-to-watch]
#
# The image must ALREADY be on the FAT boot partition; stage it over ssh while
# Linux is up:
#   scp img.bin imx95:/tmp/ && ssh imx95 'cp /tmp/img.bin /run/media/boot-mmcblk1p1/ && sync'
#
# Every step below exists because its absence cost a run. See NOTES at the end.
set -u

BIN="${1:?usage: run-on-frdm.sh <image.bin> [watch_seconds]}"
WATCH="${2:-30}"
A55=/dev/ttyACM1
SM=/dev/ttyACM2
LOAD=0x90000000
OUT="${OUT:-/tmp/frdm-run.txt}"
IMG="$(basename "$BIN")"

[ -f "$BIN" ] || { echo "no image at $BIN" >&2; exit 1; }
for d in "$A55" "$SM"; do
    [ -c "$d" ] || { echo "missing $d - is the debug USB in the FIRST USB-C port?" >&2; exit 1; }
    stty -F "$d" 115200 raw -echo 2>/dev/null
done
say(){ printf '\n=== %s ===\n' "$*"; }

# ---- 1. DRAIN. Non-negotiable, and the single biggest time sink when skipped.
say "draining the console backlog"
for i in 1 2 3 4 5 6; do
    timeout 6 cat "$A55" > /tmp/.frdm-drain 2>/dev/null
    n=$(stat -c%s /tmp/.frdm-drain 2>/dev/null || echo 0)
    echo "  pass $i: $n bytes"
    [ "$n" -lt 50 ] && break
done

# ---- 2. Capture BEFORE anything that produces output.
timeout $((WATCH + 150)) cat "$A55" > "$OUT" 2>/dev/null &
CAP=$!
trap 'kill $CAP 2>/dev/null' EXIT
sleep 1

# ---- 3. Wake the SM into monitor mode, THEN reset.
say "SM monitor mode + reset"
printf '\r' > "$SM"; sleep 1
printf '\r' > "$SM"; sleep 1
printf 'reset\r' > "$SM"

# ---- 4. Spam past BOTH countdowns, then confirm the prompt before proceeding.
say "interrupting autoboot (both boots)"
for _ in $(seq 1 150); do printf ' ' > "$A55" 2>/dev/null; sleep 0.4; done
sleep 2; printf '\r' > "$A55"; sleep 2

if ! grep -qa 'u-boot=>' "$OUT"; then
    say "NO U-BOOT PROMPT - refusing to jump"
    echo "Jumping without a confirmed fatload runs whatever garbage is at $LOAD"
    echo "and wedges the A55 (recovery = 'reset' on $SM). Not doing that."
    echo "capture: $OUT  ($(stat -c%s "$OUT") bytes)"
    say "restoring Linux"
    printf '\r' > "$SM"; sleep 1; printf 'reset\r' > "$SM"
    exit 2
fi

say "loading $IMG at $LOAD"
printf 'fatload mmc 1:1 %s %s\r' "$LOAD" "$IMG" > "$A55"
sleep 4
if ! grep -qa 'bytes read' "$OUT"; then
    say "FATLOAD DID NOT REPORT 'bytes read' - refusing to jump"
    printf '\r' > "$SM"; sleep 1; printf 'reset\r' > "$SM"
    exit 3
fi
printf 'dcache off\r' > "$A55"; sleep 2      # drops the MMU; makes $LOAD executable

say "go (watching ${WATCH}s)"
printf 'go %s\r' "$LOAD" > "$A55"
sleep "$WATCH"

say "console output"
tr -d '\r' < "$OUT" | sed -n '/Starting application/,$p' | head -40

say "restoring Linux"
printf '\r' > "$SM"; sleep 1; printf 'reset\r' > "$SM"
kill $CAP 2>/dev/null
for i in $(seq 1 10); do
    sleep 20
    if timeout 12 ssh -o ConnectTimeout=6 -o BatchMode=yes imx95 'echo SSH-OK' 2>/dev/null | grep -q SSH-OK; then
        echo "board is back on ssh after ~$((i*20))s"; break
    fi
    echo "  waiting for Linux... ${i}"
done
echo "full capture: $OUT"

: <<'NOTES'
WHY EACH STEP IS HERE - all found by losing a run to it:

1. DRAIN FIRST. ttyACM1 holds a large backlog and every read returns OLD content
   until it is emptied. Live output then looks absent: a first read once showed
   kernel timestamps ~194,973 s while the board's own uptime was 2,315,865 s,
   which reads exactly like "this is a different board" and is not.

2. CAPTURE BEFORE RESETTING. Issuing the reset in one command and starting the
   capture in the next misses U-Boot entirely - it has already scrolled past.

3. SM MONITOR MODE BEFORE `reset`. After the SM reboots it prints "Press key to
   enter monitor mode" and IGNORES commands until it gets one. A `reset` sent
   into that state does nothing, silently, and looks like a dead console.

4. AN SM RESET BOOTS THE BOARD TWICE, so a keypress that stops the first
   countdown is flushed by the second. Spam through both (~60 s).

5. NEVER `go` WITHOUT CONFIRMING THE PROMPT AND THE FATLOAD. `go` to an address
   that was never loaded executes garbage and wedges the A55; the console then
   goes silent and looks like the workload hanging. Both guards above exit
   rather than jump, because a wedged board and a hung workload are
   indistinguishable from the outside - which is precisely the confusion this
   script exists to avoid.

6. dcache off DROPS THE MMU. Without it, `go` takes esr 0x86000006 (instruction
   translation fault): U-Boot maps DRAM non-executable.

7. ping OK + ssh refused is ~60 s of normal Kinara ARA240 DDR init, not a fault.
NOTES
