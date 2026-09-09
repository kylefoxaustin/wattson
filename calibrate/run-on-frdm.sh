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

# ---- 1+2. ONE CONTINUOUS READER for the whole session.
#
# ⚠️ DO NOT open the port repeatedly. Each open/close of this CDC-ACM debug
# bridge toggles DTR/RTS, and a drain loop of separate `cat` invocations left
# the port silent afterwards - live boot output stopped arriving entirely. The
# one attempt that worked all evening opened the port EXACTLY ONCE; every
# attempt with a multi-open drain loop failed. So: open once, let the backlog
# flow into the same file we will capture into, and detect "drained" by the file
# going quiet rather than by reopening.
say "opening the console (single reader) and draining the backlog"
timeout $((WATCH + 260)) cat "$A55" > "$OUT" 2>/dev/null &
CAP=$!
# ⚠️ ONE PERSISTENT WRITE DESCRIPTOR TOO. `printf > /dev/ttyACM1` REOPENS the
# port on every call - the same DTR/RTS churn that broke the read side, once per
# keystroke. 150 s of spam sent that way never stopped autoboot; the board booted
# straight through to Linux with the keys apparently going nowhere.
exec 3> "$A55"
trap 'kill $CAP 2>/dev/null; exec 3>&- 2>/dev/null' EXIT

prev=-1
for i in $(seq 1 20); do
    sleep 3
    now=$(stat -c%s "$OUT" 2>/dev/null || echo 0)
    echo "  backlog: $now bytes"
    [ "$now" = "$prev" ] && { echo "  quiet after ${i} checks"; break; }
    prev=$now
done
DRAINED=$(stat -c%s "$OUT" 2>/dev/null || echo 0)   # everything before this is stale

# ---- 3. Reboot. PREFER `ssh reboot -f` when Linux is up.
#
# An SM `reset` restarts the whole SoC and the board then boots TWICE, so a
# keypress that stops the first autoboot countdown is flushed by the second.
# `reboot -f` from Linux produces ONE boot and one countdown - which is what the
# single attempt that worked all evening used. The SM path stays as the fallback
# for a wedged A55, where ssh is not available and nothing else can recover it.
if timeout 12 ssh -o ConnectTimeout=6 -o BatchMode=yes imx95 'echo up' 2>/dev/null | grep -q up; then
    say "rebooting via ssh (single boot)"
    timeout 15 ssh -o BatchMode=yes imx95 'nohup sh -c "sleep 1; reboot -f" >/dev/null 2>&1 &' >/dev/null 2>&1
    SPAM=150
else
    say "Linux is down - resetting via the System Manager (expect TWO boots)"
    # The SM ignores commands until a keypress puts it in monitor mode; a reset
    # sent into that state does nothing, silently, and looks like a dead console.
    printf '\r' > "$SM"; sleep 1
    printf '\r' > "$SM"; sleep 1
    printf 'reset\r' > "$SM"
    SPAM=210
fi

# ---- 4. Spam past BOTH countdowns, then confirm the prompt before proceeding.
# ---- 4. Spam until the prompt ACTUALLY APPEARS, not for a fixed time.
#
# A fixed window is the wrong shape: after `reboot -f` the board has to shut
# Linux down, run SPL, bring up DDR, run ATF and then U-Boot before the
# countdown appears - and a 38 s window expired while the console was still in
# SPL, so the check ran before U-Boot had printed anything to catch. Poll the
# LIVE region for the prompt instead and stop the moment it is there.
live(){ tail -c +$((DRAINED + 1)) "$OUT" 2>/dev/null; }

say "interrupting autoboot (adaptive, up to ${SPAM}s)"
GOT=0
END=$((SECONDS + SPAM))
while [ "$SECONDS" -lt "$END" ]; do
    printf ' ' >&3 2>/dev/null
    sleep 0.4
    if live | grep -qa 'u-boot=>'; then GOT=1; echo "  prompt after $((SECONDS - (END - SPAM)))s"; break; fi
done
sleep 1; printf '\r' >&3; sleep 2

if ! live | grep -qa 'u-boot=>'; then
    say "NO U-BOOT PROMPT - refusing to jump"
    echo "Jumping without a confirmed fatload runs whatever garbage is at $LOAD"
    echo "and wedges the A55 (recovery = 'reset' on $SM). Not doing that."
    echo "capture: $OUT  ($(stat -c%s "$OUT") bytes)"
    say "restoring Linux"
    printf '\r' > "$SM"; sleep 1; printf 'reset\r' > "$SM"
    exit 2
fi

say "loading $IMG at $LOAD"
printf 'fatload mmc 1:1 %s %s\r' "$LOAD" "$IMG" >&3
sleep 4
if ! live | grep -qa 'bytes read'; then
    say "FATLOAD DID NOT REPORT 'bytes read' - refusing to jump"
    printf '\r' > "$SM"; sleep 1; printf 'reset\r' > "$SM"
    exit 3
fi
printf 'dcache off\r' >&3; sleep 2      # drops the MMU; makes $LOAD executable

say "go (watching ${WATCH}s)"
printf 'go %s\r' "$LOAD" >&3
sleep "$WATCH"

say "console output"
live | tr -d '\r' | sed -n '/Starting application/,$p' | head -40

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
