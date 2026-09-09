#!/usr/bin/env bash
# Run a bare-metal image on the REAL FRDM-IMX95-PRO and capture its console.
#
# Everything here was paid for by getting it wrong first; see the notes.
#
#   ./run-on-frdm.sh <image.bin> [seconds-to-watch]
#
# Leaves the board booted back into Linux and verifies ssh before exiting.
set -u

BIN="${1:?usage: run-on-frdm.sh <image.bin> [watch_seconds]}"
WATCH="${2:-60}"
A55=/dev/ttyACM1          # A55 console: U-Boot + Linux   (see asset card)
SM=/dev/ttyACM2           # System Manager CLI - the recovery path
LOAD=0x90000000           # NOT 0x80000000: U-Boot maps that DRAM non-executable
                          # and `go` there takes esr 0x86000006 (instruction
                          # translation fault). Any spare DRAM address works.
OUT="${OUT:-/tmp/frdm-run.txt}"

[ -f "$BIN" ] || { echo "no image at $BIN" >&2; exit 1; }
for d in "$A55" "$SM"; do [ -c "$d" ] || { echo "missing $d - is the debug USB in the FIRST USB-C port?" >&2; exit 1; }; done

say(){ printf '\n=== %s ===\n' "$*"; }

stty -F "$A55" 115200 raw -echo 2>/dev/null
stty -F "$SM"  115200 raw -echo 2>/dev/null

say "resetting via the System Manager"
# The SM console stays alive when Linux is down and after a U-Boot abort, which
# makes it the recovery path that needs no physical access.
printf 'reset\r' > "$SM"

timeout $((WATCH + 80)) cat "$A55" > "$OUT" 2>/dev/null &
CAP=$!

say "interrupting autoboot"
for _ in $(seq 1 80); do printf ' ' > "$A55" 2>/dev/null; sleep 0.4; done
sleep 2; printf '\r' > "$A55"; sleep 1

say "loading $(basename "$BIN") at $LOAD"
# The image must already be on the FAT boot partition; stage it over ssh while
# Linux is up, BEFORE calling this script.
printf 'fatload mmc 1:1 %s %s\r' "$LOAD" "$(basename "$BIN")" > "$A55"
sleep 4
# dcache off also drops the MMU, which is what makes the loaded region
# executable. Without it `go` aborts.
printf 'dcache off\r' > "$A55"; sleep 2

say "go (watching ${WATCH}s)"
printf 'go %s\r' "$LOAD" > "$A55"
sleep "$WATCH"
kill $CAP 2>/dev/null; wait $CAP 2>/dev/null

say "console output"
tr -d '\r' < "$OUT" | sed -n '/Starting application/,$p' | head -40

say "restoring Linux"
printf 'reset\r' > "$SM"
sleep 95
if timeout 25 ssh -o ConnectTimeout=10 -o BatchMode=yes imx95 'echo SSH-OK' 2>/dev/null | grep -q SSH-OK; then
    echo "board is back on ssh"
else
    # ping OK + ssh refused is ~60s of normal Kinara ARA240 DDR init, not a fault
    echo "ssh not up yet - the ARA240 init takes ~60s after boot; re-check before assuming a fault"
fi
echo "full capture: $OUT"
